"""TODO"""
from datetime import datetime

import bcrypt
from sqlmodel import Session, select
from sqlalchemy.exc import IntegrityError

from src.logger import Logger
from .user_schema import User, UserComicLink, UserChapterLink
from .comic_schema import Comic, Chapter

logger = Logger("user")


class UserRepository:
    """TODO"""
    def __init__(self, session: Session):
        self.session = session

    def create_user(self, user: User) -> User:
        """Create a new user with hashed password"""
        try:
            # Hash the password before storing
            if user.password and not user.password.startswith("$2b$"):  # Check if not already hashed
                # Encode password to bytes, hash it, then decode back to string
                password_bytes = user.password.encode('utf-8')
                hashed = bcrypt.hashpw(password_bytes, bcrypt.gensalt())
                user.password = hashed.decode('utf-8')
            self.session.add(user)
            self.session.commit()
            self.session.refresh(user)
            logger.debug(f"User created: {user.username}")  # pylint: disable=logging-fstring-interpolation
            return user
        except IntegrityError as e:
            self.session.rollback()
            raise e

    def get_user(self, user_id: int) -> User:
        """TODO"""
        return self.session.exec(select(User).where(User.id == user_id)).first()

    def get_user_by_username(self, username: str) -> User | None:
        """Get user by username"""
        return self.session.exec(select(User).where(User.username == username)).first()

    def delete_user(self, user_id: int):
        """TODO"""
        try:
            deleted_user = self.get_user(user_id)
            self.session.delete(deleted_user)
            self.session.commit()
            logger.debug(f"User deleted: {deleted_user.username}")  # pylint: disable=logging-fstring-interpolation
        except IntegrityError as e:
            self.session.rollback()
            raise e

    def get_user_followed_comics(self, user_id: int) -> list[Comic]:
        """TODO"""
        return self.session.exec(select(Comic).where(Comic.user_id == user_id)).all()

    def get_user_read_chapters(self, user_id: int, comic_id: int) -> list[Chapter]:
        """TODO"""
        return self.session.exec(select(Chapter).join(UserChapterLink).where(UserChapterLink.user_id == user_id, Chapter.comic_id == comic_id)).all()

    def user_mark_chapter_as_read(self, user_id: int, chapter_id: int) -> bool:
        """Mark a chapter as read for a user"""
        try:
            link = UserChapterLink(user_id=user_id, chapter_id=chapter_id)
            self.session.add(link)
            self.session.commit()
            self.session.refresh(link)
            logger.debug(f"User {user_id} marked chapter {chapter_id} as read")  # pylint: disable=logging-fstring-interpolation
            return True
        except IntegrityError as e:
            self.session.rollback()
            logger.error(f"Error marking chapter as read: {e}")  # pylint: disable=logging-fstring-interpolation
            raise e

    def is_following_comic(self, user_id: int, comic_id: int) -> bool:
        """Check if user is following a comic"""
        link = self.session.exec(
            select(UserComicLink).where(
                UserComicLink.user_id == user_id,
                UserComicLink.comic_id == comic_id
            )
        ).first()
        return link is not None

    def follow_comic(self, user_id: int, comic_id: int) -> bool:
        """Follow a comic. Returns True if followed, False if already following"""
        if self.is_following_comic(user_id, comic_id):
            return False

        try:
            link = UserComicLink(user_id=user_id, comic_id=comic_id)
            self.session.add(link)
            self.session.commit()
            logger.debug(f"User {user_id} followed comic {comic_id}")  # pylint: disable=logging-fstring-interpolation
            return True
        except IntegrityError as e:
            self.session.rollback()
            logger.error(f"Error following comic: {e}")  # pylint: disable=logging-fstring-interpolation
            raise e

    def unfollow_comic(self, user_id: int, comic_id: int) -> bool:
        """Unfollow a comic. Returns True if unfollowed, False if not following"""
        link = self.session.exec(
            select(UserComicLink).where(
                UserComicLink.user_id == user_id,
                UserComicLink.comic_id == comic_id
            )
        ).first()

        if not link:
            return False

        try:
            self.session.delete(link)
            self.session.commit()
            logger.debug(f"User {user_id} unfollowed comic {comic_id}")  # pylint: disable=logging-fstring-interpolation
            return True
        except IntegrityError as e:
            self.session.rollback()
            logger.error(f"Error unfollowing comic: {e}")  # pylint: disable=logging-fstring-interpolation
            raise e

    def update_user_activity(self, user_id: int, activity_time: int):
        """Update user activity"""
        user = self.get_user(user_id)
        user.activity_time = user.activity_time + activity_time
        user.last_activity = datetime.now()
        self.session.add(user)
        self.session.commit()
        self.session.refresh(user)

    def is_chapter_read(self, user_id: int, chapter_id: int) -> bool:
        """Check if a chapter is read by a user"""
        return self.session.exec(select(UserChapterLink).where(UserChapterLink.user_id == user_id, UserChapterLink.chapter_id == chapter_id)).first() is not None


if __name__ == "__main__":
    from src.db.data_access_layer import DatabaseAccessLayer
    db_layer = DatabaseAccessLayer()
    with db_layer.managed_session() as test_session:
        user_repo = UserRepository(test_session)
        created_user = user_repo.create_user(User(username="Victor", password="admin", role="admin"))
        print(created_user)
