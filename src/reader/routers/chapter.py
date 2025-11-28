"""Chapter-related routes"""
from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from src.logger import Logger

from src.reader.dependencies import (
    get_current_user,
    get_admin_user,
    get_comic_repository,
    get_chapter_repository,
    get_page_repository,
)
from src.db import User, ComicRepository, ChapterRepository, PageRepository
from src.reader.templates import templates

logger = Logger("chapter_router")
router = APIRouter()


@router.get("/{manga_id}/chapter/{chapter_number}", response_class=HTMLResponse)
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
    logger.debug(f"Viewing chapter {chapter_number} of manga {manga_id} from user {current_user.username}")
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


@router.post("/{manga_id}/chapter/{chapter_number}/delete", response_class=RedirectResponse, name="delete_chapter")
async def delete_chapter(
    request: Request,
    manga_id: str,
    chapter_number: str,
    current_user: User = Depends(get_admin_user),
    comic_repo: ComicRepository = Depends(get_comic_repository),
    chapter_repo: ChapterRepository = Depends(get_chapter_repository),
):
    """Delete a chapter (admin only)"""
    logger.info(f"Deleting chapter {chapter_number} of manga {manga_id} from user {current_user.username}")
    chapter = comic_repo.get_chapter_by_number(int(manga_id), float(chapter_number))
    if not chapter:
        raise HTTPException(status_code=404, detail="Chapter not found")

    try:
        chapter_repo.delete_chapter(chapter.id)
        return RedirectResponse(
            url=request.url_for("manga_detail", manga_id=manga_id),
            status_code=303,
        )
    except Exception as exc:  # pylint: disable=broad-except
        logger.error(f"Error deleting chapter: {exc}")  # pylint: disable=logging-fstring-interpolation
        raise HTTPException(
            status_code=500,
            detail=f"Error deleting chapter: {exc}",
        ) from exc


@router.post("/{manga_id}/chapter/{chapter_number}/blacklist_delete", response_class=RedirectResponse, name="blacklist_delete_chapter")
async def blacklist_delete_chapter(
    request: Request,
    manga_id: str,
    chapter_number: str,
    current_user: User = Depends(get_admin_user),
    comic_repo: ComicRepository = Depends(get_comic_repository),
    chapter_repo: ChapterRepository = Depends(get_chapter_repository),
):
    """Blacklist and delete a chapter (admin only)"""
    logger.info(f"Blacklisting and deleting chapter {chapter_number} of manga {manga_id} from user {current_user.username}")
    chapter = comic_repo.get_chapter_by_number(int(manga_id), float(chapter_number))
    if not chapter:
        raise HTTPException(status_code=404, detail="Chapter not found")

    try:
        # Add chapter number to blacklist
        comic_repo.add_blacklist_chapter(int(manga_id), chapter.number)
        # Delete the chapter
        chapter_repo.delete_chapter(chapter.id)
        logger.debug(f"Chapter {chapter.number} blacklisted and deleted")  # pylint: disable=logging-fstring-interpolation
        return RedirectResponse(
            url=request.url_for("manga_detail", manga_id=manga_id),
            status_code=303,
        )
    except Exception as exc:  # pylint: disable=broad-except
        logger.error(f"Error blacklisting and deleting chapter: {exc}")  # pylint: disable=logging-fstring-interpolation
        raise HTTPException(
            status_code=500,
            detail=f"Error blacklisting and deleting chapter: {exc}",
        ) from exc
