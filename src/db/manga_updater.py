"""TODO"""
import asyncio
from datetime import datetime

from src.scraper.asura_scans import AsuraScansScraper
from src.scraper.mangafire_to import MangaFireToScraper
from src.logger import Logger
from src.reader.context_manager import get_context_manager

from .comic_schema import UpdateFrequency, ScanlationGroup, Comic, Status, UpdateStatus
from .comic import ComicRepository

logger = Logger("manga_updater")


def to_number_of_days(update_frequency: UpdateFrequency) -> int:
    """TODO"""
    if update_frequency == UpdateFrequency.WEEKLY:
        return 7
    elif update_frequency == UpdateFrequency.BIWEEKLY:
        return 14
    elif update_frequency == UpdateFrequency.MONTHLY:
        return 30
    else:
        raise ValueError(f"Invalid update frequency: {update_frequency}")


class MangaUpdater:
    """TODO"""
    def __init__(self, comic_repository: ComicRepository):
        self.comic_repository = comic_repository

    async def search_for_updates(self):
        """TODO"""
        for comic in self.comic_repository.get_comics():
            if comic.status == Status.ONGOING:
                days_since_last_update = (datetime.now() - comic.last_updated).days
                if days_since_last_update >= to_number_of_days(comic.update_frequency):
                    get_context_manager().add_task(asyncio.create_task(self.force_update(comic)))
                    if days_since_last_update - to_number_of_days(comic.update_frequency) > 14:
                        self.comic_repository.update_comic_status(comic.id, Status.HIATUS)

    async def force_update(self, comic: Comic):
        """TODO"""
        try:
            logger.info(f"Updating {comic.name}")  # pylint: disable=logging-fstring-interpolation
            if comic.update_status == UpdateStatus.PENDING:
                logger.info(f"Comic {comic.name} is already being updated")  # pylint: disable=logging-fstring-interpolation
                return
            self.comic_repository.update_comic_update_status(comic.id, UpdateStatus.PENDING)
            if comic.scanlation_group == ScanlationGroup.ASURA_SCANS:
                name, count = await AsuraScansScraper().refresh_comic(comic)
            elif comic.scanlation_group == ScanlationGroup.MANGA_FIRE:
                name, count = await MangaFireToScraper().refresh_comic(comic)
            else:
                raise ValueError(f"Invalid scanlation group: {comic.scanlation_group}")

            if count > 0 and comic.status != Status.ONGOING:
                self.comic_repository.update_comic_status(comic.id, Status.ONGOING)
            self.comic_repository.update_comic_update_status(comic.id, UpdateStatus.SUCCESS)
            return name, count
        except Exception as e:
            self.comic_repository.update_comic_update_status(comic.id, UpdateStatus.FAILED)
            raise e

    async def force_global_update(self):
        """TODO"""
        for comic in self.comic_repository.get_comics():
            get_context_manager().add_task(asyncio.create_task(self.force_update(comic)))


if __name__ == "__main__":
    from src.db.data_access_layer import DatabaseAccessLayer
    from src.db.comic import ComicRepository

    database_access_layer = DatabaseAccessLayer()
    with database_access_layer.managed_session() as session:
        test_comic_repository = ComicRepository(session)
        manga_updater = MangaUpdater(test_comic_repository)
        asyncio.run(manga_updater.search_for_updates())
