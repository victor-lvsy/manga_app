"""Library and home page routes"""
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse

from src.reader.dependencies import get_current_user, get_comic_repository, get_user_repository
from src.db import User, ComicRepository, UserRepository, Tag
from src.reader.templates import templates
from src.logger import Logger

logger = Logger("library")
router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def acceuil(
    request: Request,
    current_user: User = Depends(get_current_user),
    comic_repo: ComicRepository = Depends(get_comic_repository),
    user_repo: UserRepository = Depends(get_user_repository),
):
    """Affiche la page d'accueil avec trois listes de mangas"""
    logger.debug(f"Displaying home page for user {current_user.username}")
    all_comics = comic_repo.get_comics()

    # Helper function to format manga data
    def format_manga(manga):
        manga_dict = {**manga.model_dump(), "number_of_chapters": len(comic_repo.get_comic_chapters(manga.id))}
        manga_dict["is_followed"] = user_repo.is_following_comic(current_user.id, manga.id)
        manga_dict["tags"] = [tag.name.lower() for tag in comic_repo.get_comic_tags(manga.id)]
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


@router.get("/library", response_class=HTMLResponse)
async def library(
    request: Request,
    current_user: User = Depends(get_current_user),
    comic_repo: ComicRepository = Depends(get_comic_repository),
    user_repo: UserRepository = Depends(get_user_repository),
):
    """Affiche la bibliothèque des mangas"""
    logger.debug(f"Displaying library page for user {current_user.username}")
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
        manga_dict["tags"] = [tag.name.lower() for tag in comic_repo.get_comic_tags(manga.id)]
        manga_dict["comic_type"] = manga.comic_type.value if manga.comic_type else "manga"
        # Add timestamp for better sorting
        manga_dict["timestamp"] = int(manga.last_updated.timestamp())
        mangas_with_follow_status.append(manga_dict)

    return templates.TemplateResponse("library.html", {
        "request": request,
        "mangas": mangas_with_follow_status,
        "available_tags": [Tag.denormalize(tag.name) for tag in comic_repo.get_all_tags()],
    })
