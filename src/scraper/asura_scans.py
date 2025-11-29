"""TODO"""
import re
import json
from typing import Tuple
import bs4

from src.logger import Logger
from src.db import Comic, ScanlationGroup
from .base import BaseScraper

logger = Logger("asura_scans")


class AsuraScansScraper(BaseScraper):
    """TODO"""
    def __init__(self):
        super().__init__(host="https://asuracomic.net/")

    def extract_chapters(self, urls: list[str]):
        """TODO"""
        chapters = []
        for url in urls:
            match = re.search(r'/chapter/(\d+(?:.\d+)?)', url.rstrip('/'))
            if match:
                s = match.group(1)
                chapters.append(int(s) if s.isdigit() else float(s))
        return chapters

    def get_chapter_links(self, soup: bs4.BeautifulSoup):
        """TODO"""
        url = soup.find("meta", property="og:url").get("content")
        # Extract series identifier from URL (e.g., "return-of-the-mount-hua-sect-a735efa1")
        series_id = url.split("/series/")[-1].rstrip("/")

        # Find all chapter links for the specific manga using dynamic pattern
        chapter_pattern = f"^{re.escape(series_id)}/chapter/\\d+(?:\\.\\d+)?$"
        chapter_links = [link.get("href") for link in soup.find_all("a", href=re.compile(chapter_pattern))]
        return chapter_links

    def get_comic_cover(self, soup: bs4.BeautifulSoup):
        """TODO"""
        logger.debug("Getting comic cover, Downloading...")
        images = soup.find_all("img")
        cover_url = next((image.get("src") for image in images if image.get("alt") == "poster"), None)
        print(cover_url)
        if not cover_url:
            for image in images:
                print(image)
        response = self._get_from_url(cover_url)
        return response.content, cover_url

    def validate_url_and_get_chapter_count(self, url: str):
        """Validate if a manga exists at the given URL and return chapter count"""
        try:
            response = self._get_from_url(url)
            soup = bs4.BeautifulSoup(response.content, "html.parser")
            chapter_links = self.get_chapter_links(soup)
            chapters = self.extract_chapters(chapter_links)
            return True, len(chapters), ""
        except Exception as e:  # pylint: disable=broad-except
            return False, 0, str(e)

    async def scan_for_new_chapters(self):
        """TODO"""
        for comic in self.get_comics(ScanlationGroup.ASURA_SCANS):
            await self.refresh_comic(comic)

    async def refresh_comic(self, comic: Comic) -> Tuple[str, int]:
        """TODO"""
        response = self._get_from_url(comic.url)
        soup = bs4.BeautifulSoup(response.content, "html.parser")
        if not self.check_if_comic_cover_exists(comic):
            cover_content, cover_url = self.get_comic_cover(soup)
            self.save_comic_cover(comic, cover_content, cover_url)

        chapter_links = self.get_chapter_links(soup)
        chapters = self.extract_chapters(chapter_links)
        count = 0
        for chapter in chapters:
            existing_chapters = self.comic_repository.get_comic_chapters(comic.id)
            existing_chapters_numbers = [c.number for c in existing_chapters] if existing_chapters else []
            blacklist_chapters = self.comic_repository.get_comic(comic.id).blacklist_chapters if self.comic_repository.get_comic(comic.id).blacklist_chapters else []
            if (
                float(chapter) not in existing_chapters_numbers
                and float(chapter) not in blacklist_chapters
            ):
                count += 1
                logger.debug(f"{comic.name} - Found new chapter {chapter} - Downloading...")  # pylint: disable=logging-fstring-interpolation
                await self.save_asura_chapter(comic, chapter, comic.url)

        logger.debug(f"{comic.name} - Found {count} new chapters")  # pylint: disable=logging-fstring-interpolation

        return comic.name, count

    def remove_duplicates(self, img_list):
        """TODO"""
        return list(set(img_list))

    async def get_img_list(self, soup: bs4.BeautifulSoup):
        """TODO"""
        img_list = []
        pattern = re.compile(r"([^[\[\{]*)(.*)")
        ns_data = [""]
        target_script_text = None

        for s in soup.find_all("script"):
            txt = s.string or s.text or ""
            if txt.startswith("self.__next_f.push("):
                target_script_text = txt.replace("self.__next_f.push(", "").rstrip(")")
            else:
                target_script_text = None
            if target_script_text:
                data_string = json.loads(target_script_text)[1]
                if data_string:
                    ns_data[-1] += data_string
                    if data_string.endswith("\n"):
                        ns_data.append("")

        for data in ns_data:
            split_data = data.split("\n")
            for d in split_data:
                match = re.match(pattern, d)
                if match:
                    if match.group(2):
                        data_dict = json.loads(match.group(2))
                        if isinstance(data_dict, dict):
                            if list(data_dict.keys()) == ["order", "url"]:
                                img_list.append(data_dict)
        return img_list

    async def save_asura_chapter(self, comic: Comic, chapter: float, comic_url_up_to_chapter: str):
        """TODO"""
        full_chapter_url = comic_url_up_to_chapter + ("/chapter/" if not comic_url_up_to_chapter.endswith("/") else "chapter/") + str(chapter)
        img_list = []
        response = self._get_from_url(full_chapter_url)
        soup = bs4.BeautifulSoup(response.content, "html.parser")

        img_list = await self.get_img_list(soup)

        if len(img_list) == 0:
            logger.warning("chapter not found, trying chapters")  # pylint: disable=logging-fstring-interpolation
            response = self._get_from_url(full_chapter_url)

            img_list = await self.get_img_list(soup)

        if len(img_list) < 8:
            logger.debug(f"{comic.name}, chapter {chapter} - Probably missing images, ({len(img_list)} pages)")  # pylint: disable=logging-fstring-interpolation
        else:
            logger.debug(f"{comic.name}, chapter {chapter} - Downloading {len(img_list)} images")  # pylint: disable=logging-fstring-interpolation

        self.save_chapter(comic, chapter, full_chapter_url, [(img["order"], img["url"]) for img in img_list])


if __name__ == "__main__":
    with AsuraScansScraper() as scraper:
        scraper.scan_for_new_chapters()
