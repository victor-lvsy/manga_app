"""Manga-related routes"""
import os
from pathlib import Path
from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse, FileResponse, RedirectResponse, JSONResponse
import requests
from src.logger import Logger
from src.reader.dependencies import (
    get_current_user,
    get_comic_repository,
    get_user_repository,
)
from src.db import User, ComicRepository, UserRepository, UpdateStatus
from src.reader.templates import templates
from src.config import LOCAL_FOLDER

logger = Logger("manga-router")
router = APIRouter()

# Get scraper API URL from environment variable
SCRAPER_API_URL = os.getenv("SCRAPER_API_URL", "http://scraper:8810")


def list_chapters(comic, comic_repo: ComicRepository):
    """List chapters for a comic using database"""
    chapters = comic_repo.get_comic_chapters(comic.id)
    # Sort chapters by number and return relative paths
    sorted_chapters = sorted(chapters, key=lambda chap: chap.number)
    return [f'{float(c.number):g}' for c in sorted_chapters]


@router.get("/manga/{manga_id}", response_class=HTMLResponse)
async def manga_detail(
    request: Request,
    manga_id: str,
    current_user: User = Depends(get_current_user),
    comic_repo: ComicRepository = Depends(get_comic_repository),
    user_repo: UserRepository = Depends(get_user_repository),
):
    """Affiche les détails d'un manga spécifique"""
    logger.debug(f"Displaying manga {manga_id} for user {current_user.username}")
    comic = comic_repo.get_comic(int(manga_id))
    if not comic:
        raise HTTPException(status_code=404, detail="Manga not found")

    chapters = list_chapters(comic, comic_repo)
    is_following = user_repo.is_following_comic(current_user.id, comic.id)

    # Get read chapters for the user
    read_chapters = user_repo.get_user_read_chapters(current_user.id, comic.id)
    # Format chapter numbers to match the format used in list_chapters
    read_chapter_numbers = {f'{float(ch.number):g}' for ch in read_chapters}

    return templates.TemplateResponse("manga_index.html", {
        "request": request,
        "manga": comic.model_dump(),
        "chapters": chapters,
        "manga_root": str(Path(comic.local_path)),
        "is_following": is_following,
        "read_chapter_numbers": read_chapter_numbers,
        "feedback": None,
    })


@router.post("/manga/{manga_id}/follow", response_class=RedirectResponse, name="toggle_follow_manga")
async def toggle_follow_manga(
    request: Request,
    manga_id: str,
    current_user: User = Depends(get_current_user),
    user_repo: UserRepository = Depends(get_user_repository),
    comic_repo: ComicRepository = Depends(get_comic_repository),
):
    """Toggle follow/unfollow a manga"""
    logger.info(f"Toggling follow/unfollow for manga {manga_id} from user {current_user.username}")
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
        status_code=303,
    )


@router.post("/manga/{manga_id}/force_update", name="force_update_manga")
async def force_update_manga(
    request: Request,
    manga_id: str,
    current_user: User = Depends(get_current_user),
    comic_repo: ComicRepository = Depends(get_comic_repository),
):
    """Force la mise à jour des chapitres d'un manga"""
    logger.info(f"Force updating manga {manga_id} from user {current_user.username}")
    comic = comic_repo.get_comic(int(manga_id))
    if not comic:
        raise HTTPException(status_code=404, detail="Manga not found")
    if comic.update_status == UpdateStatus.PENDING:
        raise HTTPException(status_code=400, detail="Manga is already being updated")
    # Check if request is AJAX
    accept_header = request.headers.get("accept", "")
    is_ajax = "application/json" in accept_header or request.headers.get("x-requested-with") == "XMLHttpRequest"

    try:
        # Call scraper API to refresh the comic
        response = requests.get(
            f"{SCRAPER_API_URL}/comics/{comic.id}/refresh",
            timeout=30.0
        )
        response.raise_for_status()

        if is_ajax:
            return JSONResponse(
                content={
                    "success": True,
                    "message": "Mise à jour lancée."
                }
            )
        else:
            return RedirectResponse(
                url=str(request.url_for("manga_detail", manga_id=manga_id)),
                status_code=303,
            )
    except requests.exceptions.HTTPError as exc:
        logger.error(f"Error forcing update: {exc}")  # pylint: disable=logging-fstring-interpolation
        error_detail = "Erreur inconnue"
        try:
            error_detail = exc.response.json().get("detail", str(exc))
        except Exception:  # pylint: disable=broad-except
            error_detail = str(exc)
        if is_ajax:
            return JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "message": f"Erreur lors de la mise à jour : {error_detail}"
                }
            )
        else:
            return RedirectResponse(
                url=str(request.url_for("manga_detail", manga_id=manga_id)),
                status_code=303,
            )
    except Exception as exc:  # pylint: disable=broad-except
        logger.error(f"Error forcing update: {exc}")  # pylint: disable=logging-fstring-interpolation
        if is_ajax:
            return JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "message": "Erreur lors de la mise à jour. Veuillez réessayer."
                }
            )
        else:
            return RedirectResponse(
                url=str(request.url_for("manga_detail", manga_id=manga_id)),
                status_code=303,
            )


@router.get("/manga/{manga_id}/status", response_class=JSONResponse)
async def get_manga_status(
    manga_id: str,
    _current_user: User = Depends(get_current_user),
    comic_repo: ComicRepository = Depends(get_comic_repository),
):
    """Returns the update status of a manga"""
    comic = comic_repo.get_comic(int(manga_id))
    if not comic:
        raise HTTPException(status_code=404, detail="Manga not found")

    return JSONResponse(
        content={
            "update_status": comic.update_status.value,
            "last_updated": comic.last_updated.strftime("%d/%m/%y, %H:%M")
        }
    )


@router.get("/manga/{manga_id}/cover", response_class=FileResponse)
async def serve_cover(
    manga_id: str,
    _current_user: User = Depends(get_current_user),
    comic_repo: ComicRepository = Depends(get_comic_repository),
):
    """Sert la couverture d'un manga"""
    comic = comic_repo.get_comic(int(manga_id))
    if not comic:
        raise HTTPException(status_code=404, detail="Manga not found")

    # Try different cover file extensions
    cover_extensions = [".webp", ".jpg", ".jpeg", ".png", ".gif"]
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
