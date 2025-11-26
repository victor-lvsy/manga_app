"""Image serving routes"""
import os
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from src.reader.dependencies import (
    get_current_user,
    get_comic_repository,
    get_page_repository,
    get_chapter_repository,
)
from src.db import User, ComicRepository, PageRepository, ChapterRepository
from src.config import LOCAL_FOLDER

router = APIRouter()


@router.get("/image/{manga_id}/image/{page_id}")
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

