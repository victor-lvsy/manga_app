"""Shared dependencies for routers"""
from fastapi import Request, Depends, HTTPException
from sqlmodel import Session
from starlette import status as starlette_status

from src.db import (
    DatabaseAccessLayer,
    ComicRepository,
    ChapterRepository,
    PageRepository,
    UserRepository,
    User,
    UserRole,
)
from src.reader.context_manager import get_context_manager

# Initialize database access layer
db_layer = DatabaseAccessLayer()
context_manager = get_context_manager()


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

    context_manager.user_interaction(user.id)
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
    context_manager.user_interaction(current_user.id)
    return current_user
