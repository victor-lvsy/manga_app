"""TODO"""
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Optional, TYPE_CHECKING, List
from sqlmodel import SQLModel, Field, Relationship, Column
from sqlalchemy import JSON

from .user_schema import UserComicLink, UserChapterLink

if TYPE_CHECKING:
    from .user_schema import User


class ComicType(str, Enum):
    """TODO"""
    WEBTOON = "webtoon"
    MANGA = "manga"


class Status(str, Enum):
    """TODO"""
    ONGOING = "ongoing"
    COMPLETED = "completed"
    HIATUS = "hiatus"


class ScanlationGroup(str, Enum):
    """TODO"""
    ASURA_SCANS = "asura_scans"
    MANGA_FIRE = "mangafire_to"


class UpdateFrequency(str, Enum):
    """TODO"""
    WEEKLY = "weekly"
    BIWEEKLY = "biweekly"
    MONTHLY = "monthly"


class UpdateStatus(str, Enum):
    """TODO"""
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"

class Page(SQLModel, table=True):
    """TODO"""
    __tablename__ = "Page"
    id: int | None = Field(default=None, primary_key=True)
    number: int
    url: str
    local_path: str

    chapter_id: int = Field(default=None, foreign_key="Chapter.id", ondelete="CASCADE")
    chapter: "Chapter" = Relationship(back_populates="pages")


class Chapter(SQLModel, table=True):
    """TODO"""
    __tablename__ = "Chapter"
    id: int | None = Field(default=None, primary_key=True)
    number: Decimal = Field(default=0, max_digits=10, decimal_places=3)
    url: str
    local_path: str
    downloaded: bool = Field(default=False)

    pages: list[Page] = Relationship(back_populates="chapter", cascade_delete=True)
    comic_id: int = Field(default=None, foreign_key="Comic.id", ondelete="CASCADE")
    comic: "Comic" = Relationship(back_populates="chapters")
    user: Optional["User"] = Relationship(back_populates="read_chapters", link_model=UserChapterLink)


class Comic(SQLModel, table=True):
    """TODO"""
    __tablename__ = "Comic"
    id: int | None = Field(default=None, primary_key=True)
    name: str
    url: str
    local_path: str
    last_updated: datetime
    update_status: UpdateStatus = Field(default=UpdateStatus.SUCCESS)
    scanlation_group: ScanlationGroup
    comic_type: ComicType
    status: Status = Field(default=Status.ONGOING)
    update_frequency: UpdateFrequency = Field(default=UpdateFrequency.MONTHLY)
    tags: List = Field(sa_column=Column(JSON), default_factory=list)
    blacklist_chapters: List = Field(sa_column=Column[float](JSON), default_factory=list)

    chapters: list[Chapter] = Relationship(back_populates="comic", cascade_delete=True)
    user: Optional["User"] = Relationship(back_populates="followed_comics", link_model=UserComicLink)

    def model_dump(self, *args, **kwargs):
        """TODO"""
        data = super().model_dump(*args, **kwargs)
        data["update_status"] = self.update_status.value.replace("_", " ").title()
        data["last_updated"] = self.last_updated.strftime("%d/%m/%y, %H:%M")
        data["scanlation_group"] = self.scanlation_group.value.replace("_", " ").title()
        data["comic_type"] = self.comic_type.value.replace("_", " ").title()
        data["update_frequency"] = self.update_frequency.value.replace("_", " ").title()  # pylint: disable=no-member
        return data
