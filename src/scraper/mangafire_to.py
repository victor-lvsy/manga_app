"""TODO"""
import os
from urllib.parse import urljoin
from typing import List, Tuple

import requests
import bs4

from src.logger import Logger
from src.db import ScanlationGroup, Comic
from .base import BaseScraper, LOCAL_FOLDER
from .ssl import SSLChecker
from .vrf_generator import VRFGenerator

logger = Logger("mangafire_to")


class MangaFireToScraper(BaseScraper):
    """TODO"""
    def __init__(self):
        super().__init__(host="https://mangafire.to/")
        self.ssl_checker = SSLChecker()
        self.vrf_generator = VRFGenerator()
        used_urls = ["https://mangafire.to/"]
        for url in used_urls:
            if not self.ssl_checker.test_ssl_methods(url=url, verbose=False)["certifi bundle"]:
                raise requests.exceptions.SSLError(f"SSL connection failed for {url}, need to check certificate")

    def __enter__(self):
        super().__enter__()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        super().__exit__(exc_type, exc_value, traceback)
        self.vrf_generator.close()

    async def get_img_list(
            self, chapter_number: int, chapter_url: str, hl: str
    ) -> List[str]:
        """TODO"""
        path, vrf = await self.vrf_generator.get_chapter_vrf_async(chapter_url)
        params = {'vrf': vrf}
        data_json = self._get(path=path, params=params).json()
        images = data_json.get('result').get('images')
        return [image[0] for image in images]

    async def save_mangafire_chapter(self, comic: Comic, chapter_number: float, chapter_url: str, hl: str = "en"):
        """TODO"""
        chapter_url = urljoin(self.host, chapter_url)
        img_list = await self.get_img_list(chapter_number, chapter_url, hl)
        img_list = [(index, img) for index, img in enumerate(img_list)]
        self.save_chapter(comic, chapter_number, chapter_url, img_list)

    async def scan_for_new_chapters(self):
        """TODO"""
        for comic in self.get_comics(ScanlationGroup.MANGA_FIRE):
            await self.refresh_comic(comic)

    async def refresh_comic(self, comic: Comic) -> Tuple[str, int]:
        """TODO"""
        response = self._get_from_url(comic.url)
        soup = bs4.BeautifulSoup(response.content, "html.parser")
        if (
            not os.path.exists(
                os.path.join(LOCAL_FOLDER, comic.local_path, "cover.webp")
            )
            and not os.path.exists(
                os.path.join(LOCAL_FOLDER, comic.local_path, "cover.jpg")
            )
            and not os.path.exists(
                os.path.join(LOCAL_FOLDER, comic.local_path, "cover.jpeg")
            )
            and not os.path.exists(
                os.path.join(LOCAL_FOLDER, comic.local_path, "cover.png")
            )
        ):
            cover_content, cover_url = self.get_comic_cover(soup)
            if cover_url.endswith(".webp"):
                with open(os.path.join(LOCAL_FOLDER, comic.local_path, "cover.webp"), "wb") as f:
                    f.write(cover_content)
            elif cover_url.endswith(".jpg"):
                with open(os.path.join(LOCAL_FOLDER, comic.local_path, "cover.jpg"), "wb") as f:
                    f.write(cover_content)
            elif cover_url.endswith(".jpeg"):
                with open(os.path.join(LOCAL_FOLDER, comic.local_path, "cover.jpeg"), "wb") as f:
                    f.write(cover_content)
            elif cover_url.endswith(".png"):
                with open(os.path.join(LOCAL_FOLDER, comic.local_path, "cover.png"), "wb") as f:
                    f.write(cover_content)

        chapters = self.get_chapter_links(soup)
        count = 0
        for chapter in chapters:
            existing_chapters = self.comic_repository.get_comic_chapters(comic.id)
            existing_chapters_numbers = [c.number for c in existing_chapters] if existing_chapters else []
            blacklist_chapters = self.comic_repository.get_comic(comic.id).blacklist_chapters if self.comic_repository.get_comic(comic.id).blacklist_chapters else []
            if (
                float(chapter[0])
                not in existing_chapters_numbers
                and float(chapter[0]) not in blacklist_chapters
            ):
                count += 1
                logger.info(f"{comic.name} - Found new chapter {chapter[0]} - Downloading...")  # pylint: disable=logging-fstring-interpolation
                await self.save_mangafire_chapter(comic, chapter[0], chapter[1])

        logger.info(f"{comic.name} - Found {count} new chapters")  # pylint: disable=logging-fstring-interpolation
        return comic.name, count

    def get_chapter_links(self, soup: bs4.BeautifulSoup) -> List[Tuple[str, str]]:
        """TODO"""
        chapter_list = []
        chapters = soup.find_all('li', attrs={'class': 'item'})
        for chapter_item in chapters:
            chapter_list.append((chapter_item.get('data-number'), chapter_item.find('a').get('href')))
        return chapter_list

    def get_comic_cover(self, soup: bs4.BeautifulSoup):
        """TODO"""
        logger.info("Getting comic cover, Downloading...")
        cover_div = soup.find('div', attrs={'class': 'poster'})
        cover_img = cover_div.find('img')
        cover_url = cover_img.get("src")
        response = self._get_from_url(cover_url)
        return response.content, cover_url

    def validate_url_and_get_chapter_count(self, url: str):
        """Validate if a manga exists at the given URL and return chapter count"""
        try:
            response = self._get_from_url(url)
            soup = bs4.BeautifulSoup(response.content, "html.parser")
            chapters = self.get_chapter_links(soup)
            return True, len(chapters), ""
        except Exception as e:  # pylint: disable=broad-except
            return False, 0, str(e)


if __name__ == "__main__":
    with MangaFireToScraper() as scraper:
        # scraper.create_comic(comic_name="The Fragrant Flower Blooms with Dignity", comic_url="https://mangafire.to/manga/the-fragrant-flower-blooms-with-dignityy.zlw6m/", scanlation_group=ScanlationGroup.MANGA_FIRE)
        # scraper.create_comic(comic_name="I Will Be the Matriarch in This Life", comic_url="https://mangafire.to/manga/i-shall-master-this-familyy.yq271/", scanlation_group=ScanlationGroup.MANGA_FIRE)
        scraper.scan_for_new_chapters()
