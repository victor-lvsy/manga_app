"""TODO"""

from sqlmodel import Session, select
from sqlalchemy.exc import IntegrityError

from src.logger import Logger
from .comic_schema import Chapter, Page

logger = Logger("chapter")


def get_chapter_number(chapter: Chapter) -> str:
    """TODO"""
    return str(chapter.number).rstrip("0").rstrip(".")


class ChapterRepository:
    """TODO"""
    def __init__(self, session: Session):
        self.session = session

    def create_chapter(self, chapter: Chapter) -> Chapter:
        """TODO"""
        try:
            self.session.add(chapter)
            self.session.commit()
            self.session.refresh(chapter)
            self.session.refresh(chapter.comic)
            logger.debug(f"Chapter created: {chapter.comic.name} - {get_chapter_number(chapter)}")  # pylint: disable=logging-fstring-interpolation
            return chapter
        except IntegrityError as e:
            self.session.rollback()
            raise e

    def get_chapter(self, chapter_id: int) -> Chapter:
        """TODO"""
        return self.session.exec(select(Chapter).where(Chapter.id == chapter_id)).first()

    def delete_chapter(self, chapter_id: int):
        """TODO"""
        try:
            chapter = self.get_chapter(chapter_id)
            self.session.delete(chapter)
            self.session.commit()
            logger.debug(f"Chapter deleted: {chapter.comic.name} - {get_chapter_number(chapter)}")  # pylint: disable=logging-fstring-interpolation
        except IntegrityError as e:
            self.session.rollback()
            raise e

    def get_chapter_pages(self, chapter_id: int) -> list[Page]:
        """TODO"""
        return self.session.exec(select(Page).where(Page.chapter_id == chapter_id)).all()

    def update_chapter_downloaded(self, chapter_id: int):
        """TODO"""
        try:
            chapter = self.get_chapter(chapter_id)
            chapter.downloaded = True
            self.session.add(chapter)
            self.session.commit()
            self.session.refresh(chapter)
            logger.debug(f"Chapter downloaded: {chapter.comic.name} - {get_chapter_number(chapter)}")  # pylint: disable=logging-fstring-interpolation
        except IntegrityError as e:
            self.session.rollback()
            raise e

    def get_previous_chapter(self, chapter: Chapter) -> Chapter:
        """TODO"""
        return self.session.exec(
            select(Chapter)
            .where(
                Chapter.comic_id == chapter.comic_id,
                Chapter.number < chapter.number
            )
            .order_by(Chapter.number.desc())  # pylint: disable=no-member
            .limit(1)
        ).first()

    def get_next_chapter(self, chapter: Chapter) -> Chapter | None:
        """TODO"""
        return self.session.exec(
            select(Chapter)
            .where(
                Chapter.comic_id == chapter.comic_id,
                Chapter.number > chapter.number
            )
            .order_by(Chapter.number.asc())  # pylint: disable=no-member
            .limit(1)
        ).first()
