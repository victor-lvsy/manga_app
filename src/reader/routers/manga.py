"""Manga-related routes"""
import os
from pathlib import Path
from fastapi import APIRouter, Request, Depends, Query, HTTPException
from fastapi.responses import HTMLResponse, FileResponse, RedirectResponse, JSONResponse
import logging

from src.reader.dependencies import (
    get_current_user,
    get_comic_repository,
    get_user_repository,
)
from src.db import User, ComicRepository, UserRepository
from src.reader.templates import templates
from src.db.manga_updater import MangaUpdater
from src.config import LOCAL_FOLDER

logger = logging.getLogger("app")
router = APIRouter()


def list_chapters(comic, comic_repo: ComicRepository):
    """List chapters for a comic using database"""
    chapters = comic_repo.get_comic_chapters(comic.id)
    # Sort chapters by number and return relative paths
    sorted_chapters = sorted(chapters, key=lambda chap: chap.number)
    return [f"{c.number}".removesuffix(".0") for c in sorted_chapters]


@router.get("/manga/{manga_id}", response_class=HTMLResponse)
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


@router.post("/manga/{manga_id}/follow", response_class=RedirectResponse, name="toggle_follow_manga")
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
                status_code=303,
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
                status_code=303,
            )


@router.get("/manga/{manga_id}/cover", response_class=FileResponse)
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

