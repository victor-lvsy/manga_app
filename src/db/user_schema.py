"""TODO"""
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship


if TYPE_CHECKING:
    from .comic_schema import Comic, Chapter


class UserRole(str, Enum):
    """User role enum"""
    ADMIN = "admin"
    READER = "reader"


class UserChapterLink(SQLModel, table=True):
    """TODO"""
    __tablename__ = "UserChapterLink"
    user_id: int = Field(default=None, foreign_key="User.id", primary_key=True)
    chapter_id: int = Field(default=None, foreign_key="Chapter.id", primary_key=True)


class UserComicLink(SQLModel, table=True):
    """TODO"""
    __tablename__ = "UserComicLink"
    user_id: int = Field(default=None, foreign_key="User.id", primary_key=True)
    comic_id: int = Field(default=None, foreign_key="Comic.id", primary_key=True)


class User(SQLModel, table=True):
    """TODO"""
    __tablename__ = "User"
    id: int | None = Field(default=None, primary_key=True)
    username: str
    password: str
    activity_time: int = Field(default=0)
    last_activity: datetime = Field(default=datetime.now())
    role: UserRole = Field(default=UserRole.READER)
    followed_comics: list["Comic"] = Relationship(back_populates="user", link_model=UserComicLink)
    read_chapters: list["Chapter"] = Relationship(back_populates="user", link_model=UserChapterLink)
