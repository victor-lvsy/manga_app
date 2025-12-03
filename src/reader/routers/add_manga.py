"""Add manga routes"""
import os
from fastapi import APIRouter, Request, Depends, Form, Query
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
import requests
from src.logger import Logger

from src.reader.dependencies import get_current_user, get_comic_repository
from src.db import User, ComicRepository
from src.reader.templates import templates
from src.db import ScanlationGroup, ComicType, Status, UpdateFrequency
from src.db.comic_schema import Tag
from src.scraper.base import BaseScraper
from src.scraper.asura_scans import AsuraScansScraper
from src.scraper.mangafire_to import MangaFireToScraper

logger = Logger("add-manga")
router = APIRouter()

SCRAPER_FACTORIES: dict[ScanlationGroup, type[BaseScraper]] = {
    ScanlationGroup.ASURA_SCANS: AsuraScansScraper,
    ScanlationGroup.MANGA_FIRE: MangaFireToScraper,
}

# Get scraper API URL from environment variable
SCRAPER_API_URL = os.getenv("SCRAPER_API_URL", "http://scraper:8810")


def add_manga_context(request: Request, comic_repo: ComicRepository, feedback: dict | None = None, tag_feedback: dict | None = None):
    """Prepare base context for the add manga page"""
    return {
        "request": request,
        "scanlation_groups": list(ScanlationGroup),
        "comic_types": list(ComicType),
        "statuses": list(Status),
        "update_frequencies": list(UpdateFrequency),
        "available_tags": [Tag.denormalize(tag.name) for tag in comic_repo.get_all_tags()],
        "feedback": feedback,
        "tag_feedback": tag_feedback,
    }


@router.get("/add_manga", response_class=HTMLResponse)
async def add_manga(request: Request, comic_repo: ComicRepository = Depends(get_comic_repository), _current_user: User = Depends(get_current_user)):
    """Affiche le formulaire d'ajout de manga"""
    return templates.TemplateResponse("add_manga.html", add_manga_context(request, comic_repo))


@router.get("/add_manga/validate", response_class=JSONResponse)
async def validate_manga_url(
    url: str = Query(...),
    scanlation_group: str = Query(...),
    _current_user: User = Depends(get_current_user),
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
            if scraper.host not in url:
                return JSONResponse(
                    status_code=400,
                    content={"valid": False, "chapter_count": 0, "error": "URL invalide"}
                )
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


@router.post("/add_manga", response_class=HTMLResponse)
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
    logger.info(f"Creating comic {name} from user {current_user.username}")
    try:
        scanlation = ScanlationGroup(scanlation_group)
        comic_type_value = ComicType(comic_type)
        status_enum = Status(status)
        update_frequency_enum = UpdateFrequency(update_frequency)
        tags_list = [tag.strip() for tag in tags.split(",") if tag.strip()]
    except ValueError as exc:
        logger.error("Erreur de validation des valeurs: %s", exc)
        feedback = {"type": "error", "message": "Valeurs envoyées invalides. " + str(exc)}
        return templates.TemplateResponse("add_manga.html", add_manga_context(request, comic_repo, feedback))

    if comic_repo.get_comic_by_name(name):
        feedback = {"type": "error", "message": "Un manga avec ce nom existe déjà."}
        return templates.TemplateResponse("add_manga.html", add_manga_context(request, comic_repo, feedback))

    if comic_repo.get_comic_by_url(url):
        feedback = {"type": "error", "message": "Un manga avec cette URL existe déjà."}
        return templates.TemplateResponse("add_manga.html", add_manga_context(request, comic_repo, feedback))

    scraper_factory = SCRAPER_FACTORIES.get(scanlation)
    if not scraper_factory:
        feedback = {"type": "error", "message": "Scanlation non supportée."}
        return templates.TemplateResponse("add_manga.html", add_manga_context(request, comic_repo, feedback))

    # Validate URL before creating
    try:
        with scraper_factory() as scraper:
            is_valid, _, error_message = scraper.validate_url_and_get_chapter_count(url)
            if not is_valid:
                feedback = {"type": "error", "message": f"URL invalide : {error_message}"}
                return templates.TemplateResponse("add_manga.html", add_manga_context(request, comic_repo, feedback))
    except Exception as exc:  # pylint: disable=broad-except
        feedback = {"type": "error", "message": f"Erreur lors de la validation de l'URL : {exc}"}
        return templates.TemplateResponse("add_manga.html", add_manga_context(request, comic_repo, feedback))

    try:
        response = requests.post(
            f"{SCRAPER_API_URL}/comics/create",
            json={
                "comic_name": name,
                "comic_url": url,
                "scanlation_group": scanlation.value,
                "comic_type": comic_type_value.value,
                "status": status_enum.value,
                "update_frequency": update_frequency_enum.value,
                "tags": tags_list,
            },
            timeout=30.0
        )
        response.raise_for_status()
        result = response.json()
        comic_id = result["comic_id"]
    except requests.exceptions.HTTPError as exc:
        error_detail = "Erreur inconnue"
        try:
            error_detail = exc.response.json().get("detail", str(exc))
        except Exception:  # pylint: disable=broad-except
            error_detail = str(exc)
        feedback = {
            "type": "error",
            "message": f"Impossible de créer le manga : {error_detail}",
        }
        return templates.TemplateResponse("add_manga.html", add_manga_context(request, comic_repo, feedback))
    except Exception as exc:  # pylint: disable=broad-except
        feedback = {
            "type": "error",
            "message": f"Impossible de créer le manga : {exc}",
        }
        return templates.TemplateResponse("add_manga.html", add_manga_context(request, comic_repo, feedback))

    return RedirectResponse(
        request.url_for("manga_detail", manga_id=comic_id),
        status_code=303,
    )


@router.post("/add_manga/tag", response_class=HTMLResponse, name="create_tag")
async def create_tag(
    request: Request,
    new_tag: str = Form(...),
    current_user: User = Depends(get_current_user),
    comic_repo: ComicRepository = Depends(get_comic_repository),
):
    """Ajoute un nouveau tag disponible pour les mangas"""
    logger.info(f"Creating tag {new_tag} from user {current_user.username}")
    candidate = new_tag.strip()
    if not candidate:
        tag_feedback = {"type": "error", "message": "Le tag ne peut pas être vide."}
        return templates.TemplateResponse("add_manga.html", add_manga_context(request, comic_repo, tag_feedback=tag_feedback))

    existing_tags = [tag.name for tag in comic_repo.get_all_tags()]
    if any(tag == Tag.normalize(candidate) for tag in existing_tags):
        tag_feedback = {"type": "error", "message": "Ce tag existe déjà."}
        return templates.TemplateResponse("add_manga.html", add_manga_context(request, comic_repo, tag_feedback=tag_feedback))

    comic_repo.create_tag(candidate)
    tag_feedback = {"type": "success", "message": f'Tag "{candidate}" ajouté avec succès.'}
    return templates.TemplateResponse("add_manga.html", add_manga_context(request, comic_repo, tag_feedback=tag_feedback))
