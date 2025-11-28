"""TODO"""
from sqlmodel import Session, select
from sqlalchemy.exc import IntegrityError

from .comic_schema import Page
from src.logger import Logger

logger = Logger("page")


class PageRepository:
    """TODO"""
    def __init__(self, session: Session):
        self.session = session

    def create_page(self, page: Page) -> Page:
        """TODO"""
        try:
            self.session.add(page)
            self.session.commit()
            self.session.refresh(page)
            return page
        except IntegrityError as e:
            self.session.rollback()
            raise e

    def get_page(self, page_id: int) -> Page:
        """TODO"""
        return self.session.exec(select(Page).where(Page.id == page_id)).first()

    def delete_page(self, page_id: int):
        """TODO"""
        try:
            page = self.get_page(page_id)
            self.session.delete(page)
            self.session.commit()
            logger.debug(f"Page deleted: {page.number}")  # pylint: disable=logging-fstring-interpolation
        except IntegrityError as e:
            self.session.rollback()
            raise e
