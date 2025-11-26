"""TODO"""
from datetime import datetime

from sqlmodel import Session, select
from sqlalchemy.exc import IntegrityError

from src.logger import Logger
from .comic_schema import Comic, Chapter, Status, ScanlationGroup, ComicType

logger = Logger("comic")


class ComicRepository:
    """TODO"""
    def __init__(self, session: Session):
        self.session = session

    def create_comic(self, comic: Comic) -> Comic:
        """TODO"""
        try:
            self.session.add(comic)
            self.session.commit()
            self.session.refresh(comic)
            logger.info(f"Comic created: {comic.name}")  # pylint: disable=logging-fstring-interpolation
            return comic
        except IntegrityError as e:
            self.session.rollback()
            raise e

    def get_comic(self, comic_id: int) -> Comic:
        """TODO"""
        return self.session.exec(select(Comic).where(Comic.id == comic_id)).first()

    def get_comic_by_name(self, name: str) -> Comic | None:
        """TODO"""
        return self.session.exec(select(Comic).where(Comic.name == name)).first()

    def get_comic_by_url(self, url: str) -> Comic | None:
        """TODO"""
        return self.session.exec(select(Comic).where(Comic.url == url)).first()

    def get_comics_by_scanlation_group(self, scanlation_group: ScanlationGroup) -> Comic:
        """TODO"""
        return self.session.exec(select(Comic).where(Comic.scanlation_group == scanlation_group))

    def get_comics(self) -> list[Comic]:
        """TODO"""
        return self.session.exec(select(Comic)).all()

    def update_comic_last_updated(self, comic_id: int):
        """TODO"""
        try:
            comic = self.get_comic(comic_id)
            comic.last_updated = datetime.now()
            self.session.add(comic)
            self.session.commit()
            self.session.refresh(comic)
            logger.info(f"Comic last updated: {comic.name}")  # pylint: disable=logging-fstring-interpolation
            return comic
        except IntegrityError as e:
            self.session.rollback()
            raise e

    def update_comic_status(self, comic_id: int, status: Status):
        """TODO"""
        try:
            comic = self.get_comic(comic_id)
            comic.status = status
            self.session.add(comic)
            self.session.commit()
            self.session.refresh(comic)
            logger.info(f"Comic status updated: {comic.name}")  # pylint: disable=logging-fstring-interpolation
            return comic
        except IntegrityError as e:
            self.session.rollback()
            raise e

    def delete_comic(self, comic_id: int):
        """TODO"""
        try:
            comic = self.get_comic(comic_id)
            self.session.delete(comic)
            self.session.commit()
            logger.info(f"Comic deleted: {comic.name}")  # pylint: disable=logging-fstring-interpolation
        except IntegrityError as e:
            self.session.rollback()
            raise e

    def create_chapter(self, chapter: Chapter):
        """TODO"""
        try:
            self.session.add(chapter)
            self.session.commit()
            self.session.refresh(chapter)
            if chapter.comic_id:
                comic = self.get_comic(chapter.comic_id)
                if comic:
                    self.session.refresh(comic)
            logger.info(f"Chapter created: {chapter.number}")  # pylint: disable=logging-fstring-interpolation
            return chapter
        except IntegrityError as e:
            self.session.rollback()
            raise e

    def get_comic_chapters(self, comic_id: int) -> list[Chapter]:
        """TODO"""
        return self.session.exec(select(Chapter).where(Chapter.comic_id == comic_id)).all()

    def get_chapter_by_number(self, comic_id: int, chapter_number: float) -> Chapter:
        """TODO"""
        return self.session.exec(select(Chapter).where(Chapter.comic_id == comic_id, Chapter.number == chapter_number)).first()

    def update_comic_tags(self, comic_id: int, tags: list[str]):
        """TODO"""
        try:
            comic = self.get_comic(comic_id)
            comic.tags = tags
            self.session.add(comic)
            self.session.commit()
            self.session.refresh(comic)
            logger.info(f"Comic tags updated: {comic.name}")  # pylint: disable=logging-fstring-interpolation
            return comic
        except IntegrityError as e:
            self.session.rollback()
            raise e

    def filter_comics(self, tags: list[str] | None = None, comic_type: ComicType | None = None) -> list[Comic]:
        """TODO"""
        if comic_type:
            comic_type_query = Comic.comic_type == comic_type
        else:
            comic_type_query = True
        if tags:
            return self.session.exec(select(Comic).where(comic_type_query).filter(Comic.tags.contains(tags))).all()  # pylint: disable=no-member
        return self.session.exec(select(Comic).where(comic_type_query)).all()

    def add_blacklist_chapter(self, comic_id: int, chapter_number: float):
        """TODO"""
        try:
            comic = self.get_comic(comic_id)
            if chapter_number not in comic.blacklist_chapters:
                print(f"Adding chapter {chapter_number} to blacklist")
                comic.blacklist_chapters = [*comic.blacklist_chapters, chapter_number]
            self.session.add(comic)
            self.session.commit()
            self.session.refresh(comic)
            logger.info(f"Blacklist chapter added: {chapter_number}")  # pylint: disable=logging-fstring-interpolation
            return comic
        except IntegrityError as e:
            self.session.rollback()
            raise e

    def remove_blacklist_chapter(self, comic_id: int, chapter_number: float):
        """TODO"""
        try:
            comic = self.get_comic(comic_id)
            if chapter_number in comic.blacklist_chapters:
                comic.blacklist_chapters.remove(chapter_number)
            self.session.add(comic)
            self.session.commit()
            self.session.refresh(comic)
            logger.info(f"Blacklist chapter removed: {chapter_number}")  # pylint: disable=logging-fstring-interpolation
            return comic
        except IntegrityError as e:
            self.session.rollback()
            raise e
