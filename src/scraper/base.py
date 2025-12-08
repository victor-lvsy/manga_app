"""TODO"""
import os
import uuid
import ssl
from typing import Tuple
from datetime import datetime
import bs4

import requests
from requests.adapters import HTTPAdapter, Retry
import certifi


from src.logger import Logger
from src.db import (
    DatabaseAccessLayer,
    UserRepository,
    ComicRepository,
    ChapterRepository,
    PageRepository,
    Comic,
    Chapter,
    Page,
    ScanlationGroup,
    ComicType,
    Status,
    UpdateFrequency,
    Tag,
)
from src.config import LOCAL_FOLDER

logger = Logger("base-scraper")


def validate_url(url: str) -> str:
    """TODO"""
    if not url.endswith("/"):
        url += "/"
    return url


class BaseScraper:
    """TODO"""
    def __init__(self, host: str):
        self.host = host
        self._session = self._create_requests_session()
        self.db_access_layer = DatabaseAccessLayer()
        with self.db_access_layer.managed_session() as session:
            self.user_repository = UserRepository(session)
            self.comic_repository = ComicRepository(session)
            self.chapter_repository = ChapterRepository(session)
            self.page_repository = PageRepository(session)

    def __enter__(self):
        """TODO"""
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """TODO"""
        return

    def _create_requests_session(self) -> requests.Session:
        """Create a requests session with retry strategy and SSL configuration"""
        session = requests.Session()
        retries = Retry(total=5, status_forcelist=frozenset([429, 501, 502, 503]))
        session.mount('http://', HTTPAdapter(max_retries=retries))
        session.mount('https://', HTTPAdapter(max_retries=retries))

        # Configure SSL context for better certificate handling
        try:
            # Create a custom SSL context
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = True
            ssl_context.verify_mode = ssl.CERT_REQUIRED

            # Try to load additional certificates if they exist
            custom_cert_path = 'certificat_ssl/mangafire_to.pem'
            if os.path.exists(custom_cert_path):
                try:
                    ssl_context.load_verify_locations(custom_cert_path)
                    logger.debug(f"Loaded custom certificate from {custom_cert_path}")  # pylint: disable=logging-fstring-interpolation
                except Exception as e:
                    logger.warning(f"Failed to load custom certificate: {e}")  # pylint: disable=logging-fstring-interpolation

            # Apply the SSL context to the session
            session.mount('https://', HTTPAdapter(max_retries=retries))

        except Exception as e:
            logger.warning(f"SSL context configuration failed: {e}")  # pylint: disable=logging-fstring-interpolation

        return session

    def _get_from_url(self, url: str, params: dict = None, headers: dict = None, raise_for_status: bool = True, stream: bool = False, referer: str = None) -> requests.Response:
        """Make a GET request using the session with SSL fallback options"""
        default_headers = {
            'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:143.0) Gecko/20100101 Firefox/143.0',
            'Referer': self.host,
            'Accept': 'application/json, text/javascript, */*; q=0.01'
        }

        if headers:
            default_headers.update(headers)
        if referer:
            # Add additional headers when referer is provided (for AJAX requests)
            default_headers.update({
                'Referer': referer,
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate, br, zstd',
                'DNT': '1',
                'Sec-GPC': '1',
                'Sec-Fetch-Dest': 'empty',
                'Sec-Fetch-Mode': 'cors',
                'Sec-Fetch-Site': 'same-origin',
                'Connection': 'keep-alive',
                'TE': 'trailers',
            })

        # Try multiple SSL verification approaches
        ssl_options = [
            {'verify': certifi.where(), 'description': 'Default certifi bundle'}
        ]

        for ssl_option in ssl_options:
            try:
                response = self._session.get(
                    url=url,
                    params=params,
                    timeout=10,
                    headers=default_headers,
                    stream=stream,
                    verify=ssl_option['verify']
                )

                if raise_for_status:
                    response.raise_for_status()

                return response

            except requests.exceptions.SSLError as e:
                logger.warning(f"SSL error with {ssl_option['description']}: {e}")  # pylint: disable=logging-fstring-interpolation
                if ssl_option == ssl_options[-1]:  # Last option
                    logger.error("All SSL verification methods failed")
                    raise e
                continue
            except Exception as e:
                logger.error(f"Non-SSL error: {e}")  # pylint: disable=logging-fstring-interpolation
                raise e

        # This should never be reached, but just in case
        raise requests.exceptions.RequestException("All SSL options failed")

    def _get(self, path: str, params: dict = None, headers: dict = None, raise_for_status: bool = True, stream: bool = False, referer: str = None) -> requests.Response:
        """TODO"""
        return self._get_from_url(self.host + path, params, headers, raise_for_status, stream, referer)

    def create_comic_folder(self, comic_folder_name):
        """TODO"""
        curr = LOCAL_FOLDER
        full_path = os.path.join(curr, comic_folder_name)
        if not os.path.exists(full_path):
            os.makedirs(full_path)
        return full_path

    def create_chapter_folder(self, comic_folder_name: int, chapter_folder_name: str):
        """TODO"""
        curr = LOCAL_FOLDER
        full_path = os.path.join(curr, str(comic_folder_name), str(chapter_folder_name))
        if not os.path.exists(full_path):
            os.makedirs(full_path)
        return full_path

    def create_comic(
        self,
        comic_name: str,
        comic_url: str,
        scanlation_group: ScanlationGroup,
        comic_type: ComicType | None = None,
        status: Status = Status.ONGOING,
        update_frequency: UpdateFrequency = UpdateFrequency.MONTHLY,
        tags: list[str] | None = None,
        created_by_id: int | None = None,
    ):
        """TODO"""
        comic_folder_name = comic_name.replace(" ", "_"). replace("\'", " ").lower()
        self.create_comic_folder(comic_folder_name)
        comic = Comic(
            name=comic_name,
            url=comic_url,
            local_path=comic_folder_name,
            last_updated=datetime.now(),
            scanlation_group=scanlation_group,
            comic_type=comic_type or ComicType.MANGA,
            status=status,
            update_frequency=update_frequency,
            created_by_id=created_by_id,
        )
        self.comic_repository.create_comic(comic)
        if tags:
            for tag in tags:
                if Tag.normalize(tag) not in [Tag.normalize(tag.name) for tag in self.comic_repository.get_all_tags()]:
                    self.comic_repository.create_tag(Tag.normalize(tag))
                self.comic_repository.create_comic_tag_link(comic.id, self.comic_repository.get_tag_by_name(Tag.normalize(tag)).id)
        return comic

    def create_chapter(self, comic: Comic, chapter_number: int, chapter_url: str):
        """TODO"""
        chapter_folder_name = str(chapter_number).replace(" ", "_").replace(".", "_").replace(",", "_").lower()
        self.create_chapter_folder(comic.local_path, chapter_folder_name)
        chapter = Chapter(number=chapter_number, url=chapter_url, local_path=chapter_folder_name, comic_id=comic.id)
        self.chapter_repository.create_chapter(chapter)
        return chapter

    def create_page(self, comic: Comic, chapter: Chapter, page_number: int, page_url: str):
        """TODO"""
        extention = ""
        if page_url.endswith(".jpg") or page_url.endswith(".jpeg") or page_url.endswith(".JPG"):
            extention = ".jpg"
        elif page_url.endswith(".webp"):
            extention = ".webp"
        else:
            logger.error(f"Unsupported image format: {page_url}")  # pylint: disable=logging-fstring-interpolation
            raise ValueError(f"Unsupported image format: {page_url}")
        page_path = str(uuid.uuid4().hex) + extention
        page = Page(number=page_number, url=page_url, local_path=page_path, chapter=chapter)
        self.page_repository.create_page(page)
        with open(os.path.join(LOCAL_FOLDER, str(comic.local_path), str(chapter.local_path), page_path), "wb") as f:
            f.write(self._get_from_url(page_url).content)
        return page

    def get_comics(self, scanlation_group: ScanlationGroup) -> list[Comic]:
        """TODO"""
        return self.comic_repository.get_comics_by_scanlation_group(scanlation_group)

    def save_chapter(self, comic: Comic, chapter_number: float, chapter_url: str, pages_urls: list[Tuple[int, str]]):
        """TODO"""
        chapter = self.create_chapter(comic, chapter_number, chapter_url)
        for page_number, page_url in pages_urls:
            self.create_page(comic, chapter, page_number, page_url)
        self.chapter_repository.update_chapter_downloaded(chapter.id)
        return chapter

    def validate_url_and_get_chapter_count(self, url: str) -> Tuple[bool, int, str]:
        """
        Validate if a manga exists at the given URL and return chapter count.
        Returns: (is_valid, chapter_count, error_message)
        """
        raise NotImplementedError("Subclasses must implement validate_url_and_get_chapter_count")

    async def scan_for_new_chapters(self):
        """TODO"""
        raise NotImplementedError("Subclasses must implement scan_for_new_chapters")

    async def refresh_comic(self, comic: Comic):
        """TODO"""
        raise NotImplementedError("Subclasses must implement refresh_comic")

    def get_comic_cover(self, soup: bs4.BeautifulSoup):
        """TODO"""
        raise NotImplementedError("Subclasses must implement get_comic_cover")

    def check_if_comic_cover_exists(self, comic: Comic) -> bool:
        """TODO"""
        return any(os.path.exists(os.path.join(LOCAL_FOLDER, comic.local_path, f"cover.{ext}")) for ext in ["webp", "jpg", "jpeg", "png", "gif"])

    def save_comic_cover(self, comic: Comic, cover_content: bytes, cover_url: str):
        """TODO"""
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
        elif cover_url.endswith(".gif"):
            with open(os.path.join(LOCAL_FOLDER, comic.local_path, "cover.gif"), "wb") as f:
                f.write(cover_content)
        else:
            logger.error(f"Unsupported image format: {cover_url}")  # pylint: disable=logging-fstring-interpolation
            raise ValueError(f"Unsupported image format: {cover_url}")
