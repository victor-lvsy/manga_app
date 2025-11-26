"""TODO"""
import asyncio
from datetime import datetime

from src.scraper.asura_scans import AsuraScansScraper
from src.scraper.mangafire_to import MangaFireToScraper
from src.logger import Logger

from .comic_schema import UpdateFrequency, ScanlationGroup, Comic, Status
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
        updated_comics = []
        for comic in self.comic_repository.get_comics():
            if comic.status == Status.ONGOING:
                days_since_last_update = (datetime.now() - comic.last_updated).days
                if days_since_last_update >= to_number_of_days(comic.update_frequency):
                    if comic.scanlation_group == ScanlationGroup.ASURA_SCANS:
                        name, count = await AsuraScansScraper().refresh_comic(comic)
                    elif comic.scanlation_group == ScanlationGroup.MANGA_FIRE:
                        with MangaFireToScraper() as scraper:
                            while True:
                                try:
                                    name, count = await scraper.refresh_comic(comic)
                                except Exception as e:
                                    if "Unable to capture AJAX request for chapter URL" in str(e):
                                        continue
                                    else:
                                        raise e
                                break
                        updated_comics.append((name, count))
                    if days_since_last_update - to_number_of_days(comic.update_frequency) > 14 and count == 0:
                        self.comic_repository.update_comic_status(comic.id, Status.HIATUS)
        logger.info(f"Update ended, {len(updated_comics)} comics updated")  # pylint: disable=logging-fstring-interpolation
        for name, count in updated_comics:
            logger.info(f"{name} - {count} new chapters found")  # pylint: disable=logging-fstring-interpolation
        return updated_comics

    async def force_update(self, comic: Comic):
        """TODO"""
        if comic.scanlation_group == ScanlationGroup.ASURA_SCANS:
            name, count = await AsuraScansScraper().refresh_comic(comic)
        elif comic.scanlation_group == ScanlationGroup.MANGA_FIRE:
            with MangaFireToScraper() as scraper:
                while True:
                    try:
                        name, count = await scraper.refresh_comic(comic)
                    except Exception as e:
                        if "Unable to capture AJAX request for chapter URL" in str(e):
                            continue
                        else:
                            raise e
                    break
        else:
            raise ValueError(f"Invalid scanlation group: {comic.scanlation_group}")

        if count > 0 and comic.status != Status.ONGOING:
            self.comic_repository.update_comic_status(comic.id, Status.ONGOING)
        return name, count

    async def force_global_update(self):
        """TODO"""
        updated_comics = []
        for comic in self.comic_repository.get_comics():
            updated_comics.append(await self.force_update(comic))
        return updated_comics


if __name__ == "__main__":
    from src.db.data_access_layer import DatabaseAccessLayer
    from src.db.comic import ComicRepository

    database_access_layer = DatabaseAccessLayer()
    with database_access_layer.managed_session() as session:
        test_comic_repository = ComicRepository(session)
        manga_updater = MangaUpdater(test_comic_repository)
        asyncio.run(manga_updater.search_for_updates())
