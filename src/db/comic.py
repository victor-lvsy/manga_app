"""TODO"""
from datetime import datetime
import json
from sqlmodel import Session, select
from sqlalchemy.exc import IntegrityError

from src.logger import Logger
from .comic_schema import Comic, Chapter, Status, ScanlationGroup, ComicType, UpdateStatus, ComicTagLink, Tag

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
            logger.debug(f"Comic created: {comic.name}")  # pylint: disable=logging-fstring-interpolation
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
            logger.debug(f"Comic last updated: {comic.name}")  # pylint: disable=logging-fstring-interpolation
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
            logger.debug(f"Comic status updated: {comic.name}")  # pylint: disable=logging-fstring-interpolation
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
            logger.debug(f"Comic deleted: {comic.name}")  # pylint: disable=logging-fstring-interpolation
        except IntegrityError as e:
            self.session.rollback()
            raise e

    def get_comic_chapters(self, comic_id: int) -> list[Chapter]:
        """TODO"""
        return self.session.exec(select(Chapter).where(Chapter.comic_id == comic_id)).all()

    def get_chapter_by_number(self, comic_id: int, chapter_number: float) -> Chapter:
        """TODO"""
        logger.debug(f"Getting chapter by number: {comic_id} - {chapter_number:g}")  # pylint: disable=logging-fstring-interpolation
        chapter = self.session.exec(select(Chapter).where(Chapter.comic_id == comic_id, Chapter.number == chapter_number)).first()
        return chapter

    def filter_comics(self, _tags: list[str] | None = None, comic_type: ComicType | None = None) -> list[Comic]:
        """TODO"""
        if comic_type:
            comic_type_query = Comic.comic_type == comic_type
        else:
            comic_type_query = True
        # if tags:
        #     return self.session.exec(select(Comic).where(comic_type_query).filter(Comic.tags.contains(tags))).all()  # pylint: disable=no-member
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
            logger.debug(f"Blacklist chapter added: {comic.name} - {chapter_number}")  # pylint: disable=logging-fstring-interpolation
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
            logger.debug(f"Blacklist chapter removed: {comic.name} - {chapter_number}")  # pylint: disable=logging-fstring-interpolation
            return comic
        except IntegrityError as e:
            self.session.rollback()
            raise e

    def update_comic_update_status(self, comic_id: int, update_status: UpdateStatus):
        """TODO"""
        try:
            comic = self.get_comic(comic_id)
            comic.update_status = update_status
            self.session.add(comic)
            self.session.commit()
            self.session.refresh(comic)
            logger.debug(f"Comic update status updated: {comic.name}")  # pylint: disable=logging-fstring-interpolation
            return comic
        except IntegrityError as e:
            self.session.rollback()
            raise e

    def create_tag(self, name: str):
        """TODO"""
        try:
            tag = Tag(name=name)
            self.session.add(tag)
            self.session.commit()
            self.session.refresh(tag)
            logger.debug(f"Tag created: {tag.name}")  # pylint: disable=logging-fstring-interpolation
            return tag
        except IntegrityError as e:
            self.session.rollback()
            raise e

    def get_tag_by_name(self, name: str) -> Tag | None:
        """TODO"""
        return self.session.exec(select(Tag).where(Tag.name == name)).first()

    def create_comic_tag_link(self, comic_id: int, tag_id: int):
        """TODO"""
        try:
            comic_tag_link = ComicTagLink(comic_id=comic_id, tag_id=tag_id)
            self.session.add(comic_tag_link)
            self.session.commit()
            self.session.refresh(comic_tag_link)
            logger.debug(f"Comic tag link created: {comic_id} - {tag_id}")  # pylint: disable=logging-fstring-interpolation
            return comic_tag_link
        except IntegrityError as e:
            self.session.rollback()
            raise e
