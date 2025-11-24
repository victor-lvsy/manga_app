"""TODO"""
import os
from pathlib import Path
import re
import logging

import coloredlogs

from fastapi import FastAPI, Request, HTTPException, Depends, Form, Query
from fastapi.responses import HTMLResponse, FileResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette import status as starlette_status
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from sqlmodel import Session, select
import bcrypt
from dotenv import load_dotenv

from src.db import (
    DatabaseAccessLayer,
    ComicRepository,
    ChapterRepository,
    PageRepository,
    UserRepository,
    User,
    UserRole,
    Comic,
    ScanlationGroup,
    ComicType,
    Status,
    UpdateFrequency,
)
from src.db.manga_updater import MangaUpdater
from src.config import LOCAL_FOLDER
from src.scraper.base import BaseScraper
from src.scraper.asura_scans import AsuraScansScraper
from src.scraper.mangafire_to import MangaFireToScraper
from src.db.tags import get_tags, add_tag

load_dotenv()
SECRET_KEY = os.getenv("SECRET_KEY")

# Initialize database access layer
db_layer = DatabaseAccessLayer()

logger = logging.getLogger("app")
coloredlogs.install(level=logging.INFO)


class AuthMiddleware(BaseHTTPMiddleware):
    """Middleware to check authentication for protected routes"""
    async def dispatch(self, request: Request, call_next):
        # Allow access to login, logout, and static files without authentication
        if (request.url.path.startswith("/static")
                or request.url.path == "/login"
                or request.url.path == "/logout"):
            return await call_next(request)

        # Check if user is authenticated
        # SessionMiddleware runs first (outermost) and sets up the session
        # so it should be available when AuthMiddleware (innermost) runs
        try:
            user_id = request.session.get("user_id")
            if not user_id:
                return RedirectResponse(url="/login", status_code=starlette_status.HTTP_303_SEE_OTHER)
        except (AttributeError, KeyError, AssertionError):
            # Session not available, redirect to login
            return RedirectResponse(url="/login", status_code=starlette_status.HTTP_303_SEE_OTHER)

        return await call_next(request)


app = FastAPI(title="Manga Viewer")
templates = Jinja2Templates(directory="src/reader/templates")


def get_current_user_from_request(request: Request) -> User | None:
    """Helper function to get current user from request session for templates"""
    try:
        user_id = request.session.get("user_id")
        if not user_id:
            return None
        with db_layer.managed_session() as session:
            user_repo = UserRepository(session)
            return user_repo.get_user(user_id)
    except (AttributeError, KeyError, AssertionError):
        return None


# Add helper function to template globals
templates.env.globals["get_current_user_from_request"] = get_current_user_from_request

# Add authentication middleware first (innermost - runs after session is set up)
app.add_middleware(AuthMiddleware)
# Add session middleware last (outermost - runs first to set up session)
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)

app.mount("/static", StaticFiles(directory="src/reader/static"), name="static")


def get_db_session():
    """Dependency to get database session"""
    with db_layer.managed_session() as session:
        yield session


def get_user_repository(session: Session = Depends(get_db_session)) -> UserRepository:
    """Dependency to get user repository"""
    return UserRepository(session)


def get_comic_repository(session: Session = Depends(get_db_session)) -> ComicRepository:
    """Dependency to get comic repository"""
    return ComicRepository(session)


def get_chapter_repository(session: Session = Depends(get_db_session)) -> ChapterRepository:
    """Dependency to get chapter repository"""
    return ChapterRepository(session)


def get_page_repository(session: Session = Depends(get_db_session)) -> PageRepository:
    """Dependency to get page repository"""
    return PageRepository(session)


async def get_current_user(
    request: Request,
    user_repo: UserRepository = Depends(get_user_repository),
) -> User:
    """Dependency to get current authenticated user"""
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(
            status_code=starlette_status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    user = user_repo.get_user(user_id)
    if not user:
        # User was deleted but session still exists
        request.session.clear()
        raise HTTPException(
            status_code=starlette_status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    return user


async def get_admin_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Dependency to ensure current user is an admin"""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=starlette_status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user

SCRAPER_FACTORIES: dict[ScanlationGroup, type[BaseScraper]] = {
    ScanlationGroup.ASURA_SCANS: AsuraScansScraper,
    ScanlationGroup.MANGA_FIRE: MangaFireToScraper,
}


def natural_key(s: str):
    """TODO"""
    # Natural sort (so 2 < 10), case-insensitive
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", s)]


def list_chapters(comic: Comic, comic_repo: ComicRepository):
    """List chapters for a comic using database"""
    chapters = comic_repo.get_comic_chapters(comic.id)
    # Sort chapters by number and return relative paths
    sorted_chapters = sorted(chapters, key=lambda chap: chap.number)
    return [f"{c.number}".removesuffix(".0") for c in sorted_chapters]


def add_manga_context(request: Request, feedback: dict | None = None, tag_feedback: dict | None = None):
    """Prepare base context for the add manga page"""
    return {
        "request": request,
        "scanlation_groups": list(ScanlationGroup),
        "comic_types": list(ComicType),
        "statuses": list(Status),
        "update_frequencies": list(UpdateFrequency),
        "available_tags": get_tags(),
        "feedback": feedback,
        "tag_feedback": tag_feedback,
    }


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, error: str | None = None):
    """Display login page"""
    return templates.TemplateResponse("login.html", {
        "request": request,
        "error": error,
    })


@app.post("/login", response_class=HTMLResponse)
async def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    user_repo: UserRepository = Depends(get_user_repository),
):
    """Handle login"""
    user = user_repo.get_user_by_username(username)

    if not user:
        return templates.TemplateResponse("login.html", {
            "request": request,
            "error": "Nom d'utilisateur ou mot de passe incorrect",
        })

    # Verify password using bcrypt
    password_valid = False
    try:
        # Check if password is already hashed (starts with $2b$)
        if user.password.startswith("$2b$"):
            # Password is hashed, verify it
            password_bytes = password.encode('utf-8')
            hashed_bytes = user.password.encode('utf-8')
            password_valid = bcrypt.checkpw(password_bytes, hashed_bytes)
        else:
            # Password is not hashed (legacy plain text), treat as invalid
            password_valid = False
    except (ValueError, AttributeError):
        # Invalid hash format or other error, treat as invalid password
        password_valid = False

    if not password_valid:
        return templates.TemplateResponse("login.html", {
            "request": request,
            "error": "Nom d'utilisateur ou mot de passe incorrect",
        })

    # Set session
    request.session["user_id"] = user.id

    # Redirect to home page
    return RedirectResponse(
        url=request.url_for("acceuil"),
        status_code=starlette_status.HTTP_303_SEE_OTHER,
    )


@app.get("/logout", response_class=HTMLResponse)
async def logout(request: Request):
    """Handle logout"""
    request.session.clear()
    return RedirectResponse(
        url=request.url_for("login_page"),
        status_code=starlette_status.HTTP_303_SEE_OTHER,
    )


@app.get("/image/{manga_id}/image/{page_id}")
async def serve_page(
    manga_id: str,
    page_id: str,
    current_user: User = Depends(get_current_user),
    comic_repo: ComicRepository = Depends(get_comic_repository),
    page_repo: PageRepository = Depends(get_page_repository),
    chapter_repo: ChapterRepository = Depends(get_chapter_repository),
):
    """Sert les images des mangas de manière sécurisée"""
    comic = comic_repo.get_comic(int(manga_id))
    if not comic:
        raise HTTPException(status_code=404, detail="Manga not found")

    page = page_repo.get_page(int(page_id))
    if not page:
        raise HTTPException(status_code=404, detail="Manga not found")

    chapter = chapter_repo.get_chapter(page.chapter_id)
    if not chapter:
        raise HTTPException(status_code=404, detail="Chapter not found")

    image_file = os.path.join(LOCAL_FOLDER, comic.local_path, chapter.local_path, page.local_path)
    image_file = Path(image_file)

    # Sécurité: vérifier que le fichier est dans le répertoire du manga
    if not image_file.is_file():
        raise HTTPException(status_code=404, detail="Image not found")

    return FileResponse(image_file)


@app.get("/", response_class=HTMLResponse)
async def acceuil(
    request: Request,
    current_user: User = Depends(get_current_user),
    comic_repo: ComicRepository = Depends(get_comic_repository),
    user_repo: UserRepository = Depends(get_user_repository),
):
    """Affiche la page d'accueil avec trois listes de mangas"""
    all_comics = comic_repo.get_comics()

    # Helper function to format manga data
    def format_manga(manga: Comic) -> dict:
        manga_dict = {**manga.model_dump(), "number_of_chapters": len(comic_repo.get_comic_chapters(manga.id))}
        manga_dict["is_followed"] = user_repo.is_following_comic(current_user.id, manga.id)
        manga_dict["tags"] = [tag.lower() for tag in manga.tags] if manga.tags else []
        manga_dict["comic_type"] = manga.comic_type.value if manga.comic_type else "manga"
        manga_dict["timestamp"] = int(manga.last_updated.timestamp())
        return manga_dict

    # Sorti récemment: triés par last_updated descendant (les plus récents en premier)
    recently_released = sorted(
        all_comics,
        key=lambda c: (-int(c.last_updated.timestamp()), c.name.lower())
    )[:15]  # Limiter à 15 mangas

    # Suivi: mangas suivis par l'utilisateur, triés par last_updated descendant
    followed_comics = [
        comic for comic in all_comics
        if user_repo.is_following_comic(current_user.id, comic.id)
    ]
    followed_sorted = sorted(
        followed_comics,
        key=lambda c: (-int(c.last_updated.timestamp()), c.name.lower())
    )[:15]  # Limiter à 15 mangas

    # Nouveauté: triés par ID descendant (les plus récents ajoutés en premier)
    # Si pas de date de création, on utilise l'ID comme proxy
    nouveautes = sorted(
        all_comics,
        key=lambda c: (-c.id if c.id else 0, -int(c.last_updated.timestamp()))
    )[:15]  # Limiter à 15 mangas

    # Formater les données
    recently_released_formatted = [format_manga(m) for m in recently_released]
    followed_formatted = [format_manga(m) for m in followed_sorted]
    nouveautes_formatted = [format_manga(m) for m in nouveautes]

    return templates.TemplateResponse("index.html", {
        "request": request,
        "recently_released": recently_released_formatted,
        "followed": followed_formatted,
        "nouveautes": nouveautes_formatted,
    })


@app.get("/library", response_class=HTMLResponse)
async def library(
    request: Request,
    current_user: User = Depends(get_current_user),
    comic_repo: ComicRepository = Depends(get_comic_repository),
    user_repo: UserRepository = Depends(get_user_repository),
):
    """Affiche la bibliothèque des mangas"""
    comics = comic_repo.get_comics()
    comics_sorted = sorted(
        comics,
        key=lambda c: (-int(c.last_updated.timestamp()), c.name.lower())
    )

    # Add follow status for each manga
    mangas_with_follow_status = []
    for manga in comics_sorted:
        manga_dict = {**manga.model_dump(), "number_of_chapters": len(comic_repo.get_comic_chapters(manga.id))}
        manga_dict["is_followed"] = user_repo.is_following_comic(current_user.id, manga.id)
        # Ensure tags and comic_type are included
        manga_dict["tags"] = [tag.lower() for tag in manga.tags] if manga.tags else []
        manga_dict["comic_type"] = manga.comic_type.value if manga.comic_type else "manga"
        # Add timestamp for better sorting
        manga_dict["timestamp"] = int(manga.last_updated.timestamp())
        mangas_with_follow_status.append(manga_dict)

    return templates.TemplateResponse("library.html", {
        "request": request,
        "mangas": mangas_with_follow_status,
        "available_tags": get_tags(),
    })


@app.get("/manga/{manga_id}", response_class=HTMLResponse)
async def manga_detail(
    request: Request,
    manga_id: str,
    current_user: User = Depends(get_current_user),
    comic_repo: ComicRepository = Depends(get_comic_repository),
    user_repo: UserRepository = Depends(get_user_repository),
    chapters_found: int | None = Query(None, alias="chapters_found"),
):
    """Affiche les détails d'un manga spécifique"""
    comic = comic_repo.get_comic(int(manga_id))
    if not comic:
        raise HTTPException(status_code=404, detail="Manga not found")

    chapters = list_chapters(comic, comic_repo)
    is_following = user_repo.is_following_comic(current_user.id, comic.id)

    feedback = None
    if chapters_found is not None:
        if chapters_found == -1:
            feedback = {"type": "error", "message": "Erreur lors de la mise à jour. Veuillez réessayer."}
        elif chapters_found > 0:
            feedback = {"type": "success", "message": f"Mise à jour réussie ! {chapters_found} nouveau(x) chapitre(s) trouvé(s)."}
        else:
            feedback = {"type": "success", "message": "Mise à jour effectuée. Aucun nouveau chapitre trouvé."}

    return templates.TemplateResponse("manga_index.html", {
        "request": request,
        "manga": comic.model_dump(),
        "chapters": chapters,
        "manga_root": str(Path(comic.local_path)),
        "is_following": is_following,
        "feedback": feedback,
    })


@app.post("/manga/{manga_id}/follow", response_class=RedirectResponse, name="toggle_follow_manga")
async def toggle_follow_manga(
    request: Request,
    manga_id: str,
    current_user: User = Depends(get_current_user),
    user_repo: UserRepository = Depends(get_user_repository),
    comic_repo: ComicRepository = Depends(get_comic_repository),
):
    """Toggle follow/unfollow a manga"""
    comic = comic_repo.get_comic(int(manga_id))
    if not comic:
        raise HTTPException(status_code=404, detail="Manga not found")

    is_following = user_repo.is_following_comic(current_user.id, comic.id)

    if is_following:
        user_repo.unfollow_comic(current_user.id, comic.id)
    else:
        user_repo.follow_comic(current_user.id, comic.id)

    return RedirectResponse(
        url=request.url_for("manga_detail", manga_id=manga_id),
        status_code=starlette_status.HTTP_303_SEE_OTHER,
    )


@app.post("/manga/{manga_id}/force_update", name="force_update_manga")
async def force_update_manga(
    request: Request,
    manga_id: str,
    current_user: User = Depends(get_current_user),
    comic_repo: ComicRepository = Depends(get_comic_repository),
):
    """Force la mise à jour des chapitres d'un manga"""
    comic = comic_repo.get_comic(int(manga_id))
    if not comic:
        raise HTTPException(status_code=404, detail="Manga not found")

    # Check if request is AJAX
    accept_header = request.headers.get("accept", "")
    is_ajax = "application/json" in accept_header or request.headers.get("x-requested-with") == "XMLHttpRequest"

    try:
        manga_updater = MangaUpdater(comic_repo)
        _, count = await manga_updater.force_update(comic)

        if is_ajax:
            return JSONResponse(
                content={
                    "success": True,
                    "chapters_found": count,
                    "message": f"{count} nouveau(x) chapitre(s) trouvé(s)." if count > 0 else "Aucun nouveau chapitre trouvé."
                }
            )
        else:
            return RedirectResponse(
                url=str(request.url_for("manga_detail", manga_id=manga_id)) + f"?chapters_found={count}",
                status_code=starlette_status.HTTP_303_SEE_OTHER,
            )
    except Exception as exc:  # pylint: disable=broad-except
        logger.error(f"Error forcing update: {exc}")  # pylint: disable=logging-fstring-interpolation
        if is_ajax:
            return JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "chapters_found": -1,
                    "message": "Erreur lors de la mise à jour. Veuillez réessayer."
                }
            )
        else:
            return RedirectResponse(
                url=str(request.url_for("manga_detail", manga_id=manga_id)) + "?chapters_found=-1",
                status_code=starlette_status.HTTP_303_SEE_OTHER,
            )


@app.get("/manga/{manga_id}/cover", response_class=FileResponse)
async def serve_cover(
    manga_id: str,
    current_user: User = Depends(get_current_user),
    comic_repo: ComicRepository = Depends(get_comic_repository),
):
    """Sert la couverture d'un manga"""
    comic = comic_repo.get_comic(int(manga_id))
    if not comic:
        raise HTTPException(status_code=404, detail="Manga not found")

    # Try different cover file extensions
    cover_extensions = [".webp", ".jpg", ".jpeg", ".png"]
    cover_path = None

    for ext in cover_extensions:
        potential_path = Path(LOCAL_FOLDER, comic.local_path) / f"cover{ext}"
        if potential_path.exists():
            cover_path = potential_path
            break

    if not cover_path:
        # Fallback to placeholder if no cover found
        raise HTTPException(status_code=404, detail="Cover not found")

    return FileResponse(cover_path)


@app.get("/{manga_id}/chapter/{chapter_number}", response_class=HTMLResponse)
async def view_chapter(
    request: Request,
    manga_id: str,
    chapter_number: str,
    current_user: User = Depends(get_current_user),
    comic_repo: ComicRepository = Depends(get_comic_repository),
    chapter_repo: ChapterRepository = Depends(get_chapter_repository),
    page_repo: PageRepository = Depends(get_page_repository),
):
    """TODO"""

    chapter = comic_repo.get_chapter_by_number(int(manga_id), float(chapter_number))
    if not chapter:
        raise HTTPException(status_code=404, detail="Chapter not found")

    pages = [page.id for page in chapter_repo.get_chapter_pages(chapter.id)]
    if not pages:
        raise HTTPException(status_code=404, detail="No images found in this chapter")

    prev_chapter = chapter_repo.get_previous_chapter(chapter)
    next_chapter = chapter_repo.get_next_chapter(chapter)

    return templates.TemplateResponse(
        "chapter.html",
        {
            "request": request,
            "manga_id": manga_id,
            "chapter": chapter.number,
            "chapter_id": chapter.id,
            "pages": pages,
            "prev_chapter": prev_chapter.number if prev_chapter else None,
            "next_chapter": next_chapter.number if next_chapter else None,
            "current_user": current_user,
        },
    )


@app.post("/{manga_id}/chapter/{chapter_number}/delete", response_class=RedirectResponse, name="delete_chapter")
async def delete_chapter(
    request: Request,
    manga_id: str,
    chapter_number: str,
    current_user: User = Depends(get_admin_user),
    comic_repo: ComicRepository = Depends(get_comic_repository),
    chapter_repo: ChapterRepository = Depends(get_chapter_repository),
):
    """Delete a chapter (admin only)"""
    chapter = comic_repo.get_chapter_by_number(int(manga_id), float(chapter_number))
    if not chapter:
        raise HTTPException(status_code=404, detail="Chapter not found")

    try:
        chapter_repo.delete_chapter(chapter.id)
        return RedirectResponse(
            url=request.url_for("manga_detail", manga_id=manga_id),
            status_code=starlette_status.HTTP_303_SEE_OTHER,
        )
    except Exception as exc:  # pylint: disable=broad-except
        logger.error(f"Error deleting chapter: {exc}")  # pylint: disable=logging-fstring-interpolation
        raise HTTPException(
            status_code=500,
            detail=f"Error deleting chapter: {exc}",
        ) from exc


@app.post("/{manga_id}/chapter/{chapter_number}/blacklist_delete", response_class=RedirectResponse, name="blacklist_delete_chapter")
async def blacklist_delete_chapter(
    request: Request,
    manga_id: str,
    chapter_number: str,
    current_user: User = Depends(get_admin_user),
    comic_repo: ComicRepository = Depends(get_comic_repository),
    chapter_repo: ChapterRepository = Depends(get_chapter_repository),
):
    """Blacklist and delete a chapter (admin only)"""
    chapter = comic_repo.get_chapter_by_number(int(manga_id), float(chapter_number))
    if not chapter:
        raise HTTPException(status_code=404, detail="Chapter not found")

    try:
        # Add chapter number to blacklist
        comic_repo.add_blacklist_chapter(int(manga_id), chapter.number)
        # Delete the chapter
        chapter_repo.delete_chapter(chapter.id)
        logger.info(f"Chapter {chapter.number} blacklisted and deleted")  # pylint: disable=logging-fstring-interpolation
        return RedirectResponse(
            url=request.url_for("manga_detail", manga_id=manga_id),
            status_code=starlette_status.HTTP_303_SEE_OTHER,
        )
    except Exception as exc:  # pylint: disable=broad-except
        logger.error(f"Error blacklisting and deleting chapter: {exc}")  # pylint: disable=logging-fstring-interpolation
        raise HTTPException(
            status_code=500,
            detail=f"Error blacklisting and deleting chapter: {exc}",
        ) from exc


@app.get("/add_manga", response_class=HTMLResponse)
async def add_manga(request: Request, current_user: User = Depends(get_current_user)):
    """Affiche le formulaire d'ajout de manga"""
    return templates.TemplateResponse("add_manga.html", add_manga_context(request))


@app.get("/add_manga/validate", response_class=JSONResponse)
async def validate_manga_url(
    url: str = Query(...),
    scanlation_group: str = Query(...),
    current_user: User = Depends(get_current_user),
):
    """Valide une URL de manga et retourne le nombre de chapitres"""
    try:
        scanlation = ScanlationGroup(scanlation_group)
    except ValueError:
        return JSONResponse(
            status_code=400,
            content={"valid": False, "chapter_count": 0, "error": "Scanlation group invalide"}
        )

    scraper_factory = SCRAPER_FACTORIES.get(scanlation)
    if not scraper_factory:
        return JSONResponse(
            status_code=400,
            content={"valid": False, "chapter_count": 0, "error": "Scanlation non supportée"}
        )

    try:
        with scraper_factory() as scraper:
            is_valid, chapter_count, error_message = scraper.validate_url_and_get_chapter_count(url)
            if is_valid:
                return JSONResponse(
                    content={"valid": True, "chapter_count": chapter_count, "error": None}
                )
            else:
                return JSONResponse(
                    status_code=400,
                    content={"valid": False, "chapter_count": 0, "error": error_message or "URL invalide"}
                )
    except Exception as exc:  # pylint: disable=broad-except
        return JSONResponse(
            status_code=500,
            content={"valid": False, "chapter_count": 0, "error": str(exc)}
        )


@app.post("/add_manga", response_class=HTMLResponse)
async def create_manga(
    request: Request,
    current_user: User = Depends(get_current_user),
    comic_repo: ComicRepository = Depends(get_comic_repository),
    name: str = Form(...),
    url: str = Form(...),
    scanlation_group: str = Form(...),
    comic_type: str = Form(...),
    status: str = Form(...),
    update_frequency: str = Form(...),
    tags: str = Form(""),
):
    """Crée un nouveau manga sans chapitres"""
    try:
        scanlation = ScanlationGroup(scanlation_group)
        comic_type_value = ComicType(comic_type)
        status_enum = Status(status)
        update_frequency_enum = UpdateFrequency(update_frequency)
        tags_list = [tag.strip() for tag in tags.split(",") if tag.strip()]
        for tag in tags_list:
            if tag not in get_tags():
                raise ValueError(f"Tag {tag} non trouvé.")
    except ValueError as exc:
        print("Erreur de validation des valeurs:", exc)
        feedback = {"type": "error", "message": "Valeurs envoyées invalides. " + str(exc)}
        return templates.TemplateResponse("add_manga.html", add_manga_context(request, feedback))

    if comic_repo.get_comic_by_name(name):
        feedback = {"type": "error", "message": "Un manga avec ce nom existe déjà."}
        return templates.TemplateResponse("add_manga.html", add_manga_context(request, feedback))

    if comic_repo.get_comic_by_url(url):
        feedback = {"type": "error", "message": "Un manga avec cette URL existe déjà."}
        return templates.TemplateResponse("add_manga.html", add_manga_context(request, feedback))

    scraper_factory = SCRAPER_FACTORIES.get(scanlation)
    if not scraper_factory:
        feedback = {"type": "error", "message": "Scanlation non supportée."}
        return templates.TemplateResponse("add_manga.html", add_manga_context(request, feedback))

    # Validate URL before creating
    try:
        with scraper_factory() as scraper:
            is_valid, _, error_message = scraper.validate_url_and_get_chapter_count(url)
            if not is_valid:
                feedback = {"type": "error", "message": f"URL invalide : {error_message}"}
                return templates.TemplateResponse("add_manga.html", add_manga_context(request, feedback))
    except Exception as exc:  # pylint: disable=broad-except
        feedback = {"type": "error", "message": f"Erreur lors de la validation de l'URL : {exc}"}
        return templates.TemplateResponse("add_manga.html", add_manga_context(request, feedback))

    try:
        print("Création du manga...")
        with scraper_factory() as scraper:
            comic = scraper.create_comic(
                comic_name=name,
                comic_url=url,
                scanlation_group=scanlation,
                comic_type=comic_type_value,
                status=status_enum,
                update_frequency=update_frequency_enum,
                tags=tags_list,
            )
    except Exception as exc:  # pylint: disable=broad-except
        feedback = {
            "type": "error",
            "message": f"Impossible de créer le manga : {exc}",
        }
        return templates.TemplateResponse("add_manga.html", add_manga_context(request, feedback))

    return RedirectResponse(
        request.url_for("manga_detail", manga_id=comic.id),
        status_code=starlette_status.HTTP_303_SEE_OTHER,
    )


@app.post("/add_manga/tag", response_class=HTMLResponse, name="create_tag")
async def create_tag(
    request: Request,
    new_tag: str = Form(...),
    current_user: User = Depends(get_current_user),
):
    """Ajoute un nouveau tag disponible pour les mangas"""
    candidate = new_tag.strip()
    if not candidate:
        tag_feedback = {"type": "error", "message": "Le tag ne peut pas être vide."}
        return templates.TemplateResponse("add_manga.html", add_manga_context(request, tag_feedback=tag_feedback))

    existing_tags = get_tags()
    if any(tag.lower() == candidate.lower() for tag in existing_tags):
        tag_feedback = {"type": "error", "message": "Ce tag existe déjà."}
        return templates.TemplateResponse("add_manga.html", add_manga_context(request, tag_feedback=tag_feedback))

    add_tag(candidate)
    tag_feedback = {"type": "success", "message": f'Tag "{candidate}" ajouté avec succès.'}
    return templates.TemplateResponse("add_manga.html", add_manga_context(request, tag_feedback=tag_feedback))


@app.get("/admin", response_class=HTMLResponse, name="admin_page")
async def admin_page(
    request: Request,
    current_user: User = Depends(get_admin_user),
    user_repo: UserRepository = Depends(get_user_repository),
):
    """Display admin page with user management"""
    users = user_repo.session.exec(select(User)).all()
    return templates.TemplateResponse("admin.html", {
        "request": request,
        "users": users,
        "current_user": current_user,
    })


@app.post("/admin/user/create", response_class=HTMLResponse, name="admin_create_user")
async def admin_create_user(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    role: str = Form(...),
    current_user: User = Depends(get_admin_user),
    user_repo: UserRepository = Depends(get_user_repository),
):
    """Create a new user (admin only)"""
    try:
        user_role = UserRole(role)
    except ValueError:
        users = user_repo.session.exec(select(User)).all()
        return templates.TemplateResponse("admin.html", {
            "request": request,
            "users": users,
            "current_user": current_user,
            "feedback": {"type": "error", "message": "Rôle invalide."},
        })

    # Check if username already exists
    if user_repo.get_user_by_username(username):
        users = user_repo.session.exec(select(User)).all()
        return templates.TemplateResponse("admin.html", {
            "request": request,
            "users": users,
            "current_user": current_user,
            "feedback": {"type": "error", "message": "Ce nom d'utilisateur existe déjà."},
        })

    try:
        new_user = User(username=username, password=password, role=user_role)
        user_repo.create_user(new_user)
        users = user_repo.session.exec(select(User)).all()
        return templates.TemplateResponse("admin.html", {
            "request": request,
            "users": users,
            "current_user": current_user,
            "feedback": {"type": "success", "message": f"Utilisateur '{username}' créé avec succès."},
        })
    except Exception as exc:  # pylint: disable=broad-except
        users = user_repo.session.exec(select(User)).all()
        return templates.TemplateResponse("admin.html", {
            "request": request,
            "users": users,
            "current_user": current_user,
            "feedback": {"type": "error", "message": f"Erreur lors de la création: {exc}"},
        })


@app.post("/admin/user/promote", response_class=HTMLResponse, name="admin_promote_user")
async def admin_promote_user(
    request: Request,
    user_id: int = Form(...),
    current_user: User = Depends(get_admin_user),
    user_repo: UserRepository = Depends(get_user_repository),
):
    """Promote a user to admin (admin only)"""
    user = user_repo.get_user(user_id)
    if not user:
        users = user_repo.session.exec(select(User)).all()
        return templates.TemplateResponse("admin.html", {
            "request": request,
            "users": users,
            "current_user": current_user,
            "feedback": {"type": "error", "message": "Utilisateur non trouvé."},
        })

    user.role = UserRole.ADMIN
    user_repo.session.add(user)
    user_repo.session.commit()
    user_repo.session.refresh(user)

    users = user_repo.session.exec(select(User)).all()
    return templates.TemplateResponse("admin.html", {
        "request": request,
        "users": users,
        "current_user": current_user,
        "feedback": {"type": "success", "message": f"Utilisateur '{user.username}' promu administrateur."},
    })


@app.post("/admin/user/demote", response_class=HTMLResponse, name="admin_demote_user")
async def admin_demote_user(
    request: Request,
    user_id: int = Form(...),
    current_user: User = Depends(get_admin_user),
    user_repo: UserRepository = Depends(get_user_repository),
):
    """Demote an admin to reader (admin only)"""
    user = user_repo.get_user(user_id)
    if not user:
        users = user_repo.session.exec(select(User)).all()
        return templates.TemplateResponse("admin.html", {
            "request": request,
            "users": users,
            "current_user": current_user,
            "feedback": {"type": "error", "message": "Utilisateur non trouvé."},
        })

    # Prevent demoting yourself
    if user.id == current_user.id:
        users = user_repo.session.exec(select(User)).all()
        return templates.TemplateResponse("admin.html", {
            "request": request,
            "users": users,
            "current_user": current_user,
            "feedback": {"type": "error", "message": "Vous ne pouvez pas vous rétrograder vous-même."},
        })

    user.role = UserRole.READER
    user_repo.session.add(user)
    user_repo.session.commit()
    user_repo.session.refresh(user)

    users = user_repo.session.exec(select(User)).all()
    return templates.TemplateResponse("admin.html", {
        "request": request,
        "users": users,
        "current_user": current_user,
        "feedback": {"type": "success", "message": f"Utilisateur '{user.username}' rétrogradé lecteur."},
    })


@app.post("/admin/user/delete", response_class=HTMLResponse, name="admin_delete_user")
async def admin_delete_user(
    request: Request,
    user_id: int = Form(...),
    current_user: User = Depends(get_admin_user),
    user_repo: UserRepository = Depends(get_user_repository),
):
    """Delete a user (admin only)"""
    user = user_repo.get_user(user_id)
    if not user:
        users = user_repo.session.exec(select(User)).all()
        return templates.TemplateResponse("admin.html", {
            "request": request,
            "users": users,
            "current_user": current_user,
            "feedback": {"type": "error", "message": "Utilisateur non trouvé."},
        })

    # Prevent deleting yourself
    if user.id == current_user.id:
        users = user_repo.session.exec(select(User)).all()
        return templates.TemplateResponse("admin.html", {
            "request": request,
            "users": users,
            "current_user": current_user,
            "feedback": {"type": "error", "message": "Vous ne pouvez pas supprimer votre propre compte."},
        })

    try:
        user_repo.delete_user(user_id)
        users = user_repo.session.exec(select(User)).all()
        return templates.TemplateResponse("admin.html", {
            "request": request,
            "users": users,
            "current_user": current_user,
            "feedback": {"type": "success", "message": f"Utilisateur '{user.username}' supprimé."},
        })
    except Exception as exc:  # pylint: disable=broad-except
        users = user_repo.session.exec(select(User)).all()
        return templates.TemplateResponse("admin.html", {
            "request": request,
            "users": users,
            "current_user": current_user,
            "feedback": {"type": "error", "message": f"Erreur lors de la suppression: {exc}"},
        })

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8888)
