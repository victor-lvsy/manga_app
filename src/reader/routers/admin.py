"""Admin routes"""
import asyncio
from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse
from sqlmodel import select

from src.reader.context_manager import get_context_manager
from src.reader.dependencies import (
    get_admin_user,
    get_user_repository,
    get_comic_repository,
)
from src.db import User, UserRepository, ComicRepository
from src.reader.templates import templates
from src.db import UserRole
from src.db.manga_updater import MangaUpdater
from src.logger import Logger
logger = Logger("admin")
router = APIRouter()


context_manager = get_context_manager()


@router.get("/admin", response_class=HTMLResponse, name="admin_page")
async def admin_page(
    request: Request,
    current_user: User = Depends(get_admin_user),
    user_repo: UserRepository = Depends(get_user_repository),
    update_feedback: dict | None = None,
):
    """Display admin page with user management"""
    users = user_repo.session.exec(select(User)).all()
    # Pass the server start timestamp for real-time client-side updates
    server_start_timestamp = context_manager.start_time

    return templates.TemplateResponse("admin.html", {
        "request": request,
        "users": users,
        "current_user": current_user,
        "update_feedback": update_feedback,
        "server_start_timestamp": server_start_timestamp,
    })


@router.post("/admin/user/create", response_class=HTMLResponse, name="admin_create_user")
async def admin_create_user(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    role: str = Form(...),
    current_user: User = Depends(get_admin_user),
    user_repo: UserRepository = Depends(get_user_repository),
):
    """Create a new user (admin only)"""
    logger.info(f"Creating user {username} from user {current_user.username}")
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


@router.post("/admin/user/promote", response_class=HTMLResponse, name="admin_promote_user")
async def admin_promote_user(
    request: Request,
    user_id: int = Form(...),
    current_user: User = Depends(get_admin_user),
    user_repo: UserRepository = Depends(get_user_repository),
):
    """Promote a user to admin (admin only)"""
    logger.info(f"Promoting user {user_id} from user {current_user.username}")
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


@router.post("/admin/user/demote", response_class=HTMLResponse, name="admin_demote_user")
async def admin_demote_user(
    request: Request,
    user_id: int = Form(...),
    current_user: User = Depends(get_admin_user),
    user_repo: UserRepository = Depends(get_user_repository),
):
    """Demote an admin to reader (admin only)"""
    logger.info(f"Demoting user {user_id} from user {current_user.username}")
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


@router.post("/admin/user/delete", response_class=HTMLResponse, name="admin_delete_user")
async def admin_delete_user(
    request: Request,
    user_id: int = Form(...),
    current_user: User = Depends(get_admin_user),
    user_repo: UserRepository = Depends(get_user_repository),
):
    """Delete a user (admin only)"""
    logger.info(f"Deleting user {user_id} from user {current_user.username}")
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


@router.post("/admin/update_all_mangas", response_class=HTMLResponse, name="admin_update_all_mangas")
async def admin_update_all_mangas(
    request: Request,
    current_user: User = Depends(get_admin_user),
    user_repo: UserRepository = Depends(get_user_repository),
    comic_repo: ComicRepository = Depends(get_comic_repository),
):
    """Search for new chapters for all mangas (admin only)"""
    logger.info(f"Updating all mangas from user {current_user.username}")
    try:
        manga_updater = MangaUpdater(comic_repo)
        get_context_manager().add_task(asyncio.create_task(manga_updater.force_global_update()))

        users = user_repo.session.exec(select(User)).all()
        return templates.TemplateResponse("admin.html", {
            "request": request,
            "users": users,
            "current_user": current_user,
            "update_feedback": {
                "type": "success",
                "message": "Mise à jour lancée !"
            },
        })
    except Exception as exc:  # pylint: disable=broad-except
        logger.error(f"Error updating all mangas: {exc}")  # pylint: disable=logging-fstring-interpolation
        users = user_repo.session.exec(select(User)).all()
        return templates.TemplateResponse("admin.html", {
            "request": request,
            "users": users,
            "current_user": current_user,
            "update_feedback": {
                "type": "error",
                "message": f"Erreur lors de la mise à jour de tous les mangas : {exc}"
            },
        })
