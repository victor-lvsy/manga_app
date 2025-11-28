"""Add manga routes"""
from fastapi import APIRouter, Request, Depends, Form, Query
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from src.logger import Logger
from src.reader.context_manager import get_context_manager

from src.reader.dependencies import get_current_user, get_comic_repository
from src.db import User, ComicRepository
from src.reader.templates import templates
from src.db import ScanlationGroup, ComicType, Status, UpdateFrequency
from src.scraper.base import BaseScraper
from src.scraper.asura_scans import AsuraScansScraper
from src.scraper.mangafire_to import MangaFireToScraper
from src.db.tags import get_tags, add_tag

logger = Logger("add_manga")
router = APIRouter()

SCRAPER_FACTORIES: dict[ScanlationGroup, type[BaseScraper]] = {
    ScanlationGroup.ASURA_SCANS: AsuraScansScraper,
    ScanlationGroup.MANGA_FIRE: MangaFireToScraper,
}

context_manager = get_context_manager()


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


@router.get("/add_manga", response_class=HTMLResponse)
async def add_manga(request: Request, current_user: User = Depends(get_current_user)):
    """Affiche le formulaire d'ajout de manga"""
    return templates.TemplateResponse("add_manga.html", add_manga_context(request))


@router.get("/add_manga/validate", response_class=JSONResponse)
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
        logger.error("Erreur de validation des valeurs: %s", exc)
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
        logger.debug("Création du manga...")
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
        status_code=303,
    )


@router.post("/add_manga/tag", response_class=HTMLResponse, name="create_tag")
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

