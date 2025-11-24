"""VRF token generator for MangaFire using Playwright to intercept network requests"""
import asyncio
import logging
import random
import time
from typing import Optional
from urllib.parse import urlparse, parse_qs

try:
    from playwright.async_api import async_playwright, Browser, Page, Route
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

logger = logging.getLogger("vrf_generator")
coloredlogs = None
try:
    import coloredlogs
    coloredlogs.install(level=logging.INFO)
except ImportError:
    pass


class VRFGenerator:
    """Generates VRF tokens by intercepting AJAX requests using Playwright"""

    def __init__(self, base_url: str = "https://mangafire.to"):
        self.base_url = base_url
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.context = None
        self._vrf_cache = {}  # Simple cache for VRF tokens
        self._playwright = None
        self._captured_url: Optional[str] = None
        self._lock = asyncio.Lock()

    async def _init_browser(self):
        """Initialize Playwright browser (create fresh instance each time like Kotlin WebView)"""
        if not PLAYWRIGHT_AVAILABLE:
            raise ImportError(
                "Playwright is not installed. Install it with: pip install playwright && playwright install chromium"
            )

        # Always create fresh browser/context like Kotlin creates fresh WebView
        if self._playwright is None:
            self._playwright = await async_playwright().start()

        # Use Chromium with stealth settings
        if self.browser is None:
            self.browser = await self._playwright.chromium.launch(
                headless=True,  # Headless is easier to detect
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-dev-shm-usage',
                    '--no-sandbox',
                ]
            )

    async def _create_fresh_context_and_page(self):
        """Create fresh context and page (like Kotlin creates fresh WebView)"""
        # Close existing context/page if any
        if self.page:
            await self.page.close()
        if self.context:
            await self.context.close()

        # Create a new context with realistic settings
        self.context = await self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            locale='en-US',
            timezone_id='America/New_York',
            # Set Referer header like Kotlin does
            extra_http_headers={
                'Referer': f'{self.base_url}/',
            }
        )

        # Add stealth scripts to remove webdriver traces
        await self.context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });

            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });

            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en']
            });

            window.chrome = {
                runtime: {}
            };
        """)

        self.page = await self.context.new_page()

    async def _setup_request_interception(self, url_pattern: str, capture_only: bool = True, target_url: str = None):
        """Setup request interception to capture URLs matching the pattern (like Kotlin WebViewHelper)"""
        self._captured_url = None

        async def handle_route(route: Route):
            """Handle intercepted requests (mimics Kotlin shouldInterceptRequest exactly)"""
            request = route.request
            url = request.url
            parsed_url_obj = urlparse(url)

            # Allow main page (like Kotlin line 73) - exact match only
            if target_url and url == target_url:
                logger.debug(f"allowed: {url}")  # pylint: disable=W1203
                await route.continue_()
                return

            # Allow script from their CDN (like Kotlin lines 87-90)
            # Kotlin checks: host.contains("mfcdn.cc") && pathSegments.lastOrNull().orEmpty().contains("js")
            if "mfcdn.cc" in parsed_url_obj.netloc:
                path_segments = [seg for seg in parsed_url_obj.path.split('/') if seg]
                if path_segments and "js" in path_segments[-1].lower():
                    logger.debug(f"allowed: {url}")  # pylint: disable=W1203
                    await route.continue_()
                    return

            # Allow jquery script (like Kotlin lines 104-107)
            # Kotlin checks: host.contains("cloudflare.com") && encodedPath.contains("jquery")
            if "cloudflare.com" in parsed_url_obj.netloc and "jquery" in parsed_url_obj.path:
                logger.debug(f"allowed: {url}")  # pylint: disable=W1203
                await route.continue_()
                return

            # Block all images (like Kotlin blockNetworkImage = true)
            if any(url.lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg', '.ico']):
                logger.debug(f"denied (image): {url}")  # pylint: disable=W1203
                await route.abort()
                return

            # Now apply requestIntercept logic (like Kotlin lines 120-146)
            if capture_only:
                # For search: if contains "ajax/manga/search" -> Capture, else -> Block
                # (like Kotlin lines 136-143)
                if url_pattern in url:
                    logger.debug(f"captured: {url}")  # pylint: disable=W1203
                    self._captured_url = url
                    await route.abort()
                    return
                else:
                    logger.debug(f"denied: {url}")  # pylint: disable=W1203
                    await route.abort()
                    return
            else:
                # For chapter pages: (like Kotlin lines 304-318)
                # If host == "mangafire.to" && path contains "ajax/read":
                #   - If path contains "ajax/read/chapter" or "ajax/read/volume" -> Capture
                #   - Else -> Allow (other ajax/read calls)
                # Else -> Block
                if parsed_url_obj.netloc == "mangafire.to" and "ajax/read" in parsed_url_obj.path:
                    if any(pattern in parsed_url_obj.path for pattern in ["ajax/read/chapter", "ajax/read/volume"]):
                        logger.debug(f"captured: {url}")  # pylint: disable=W1203
                        self._captured_url = url
                        await route.abort()
                        return
                    else:
                        # Allow other ajax/read requests (like Kotlin line 314)
                        logger.debug(f"allowed: {url}")  # pylint: disable=W1203
                        await route.continue_()
                        return
                else:
                    logger.debug(f"denied: {url}")  # pylint: disable=W1203
                    await route.abort()
                    return

        await self.page.route("**/*", handle_route)

    async def get_chapter_vrf_async(self, chapter_url: str) -> str:
        """Get VRF token for chapter/page requests

        Args:
            chapter_url: Full URL to the chapter page

        Returns:
            VRF token string

        Raises:
            Exception: If VRF token cannot be found
        """
        async with self._lock:
            # Check cache first (use URL as key)
            if chapter_url in self._vrf_cache:
                return self._vrf_cache[chapter_url]

            await self._init_browser()
            # Create fresh context/page like Kotlin creates fresh WebView
            await self._create_fresh_context_and_page()

            try:
                # Setup request interception for chapter AJAX requests (like Kotlin lines 304-318)
                await self._setup_request_interception("ajax/read", capture_only=False, target_url=chapter_url)

                # Load chapter page
                logger.info(f"Loading chapter page to get VRF: {chapter_url}")  # pylint: disable=W1203
                await self.page.goto(chapter_url, wait_until="networkidle")

                # Human-like delay after page load
                await asyncio.sleep(random.uniform(1.0, 2.5))

                # Wait for page to be fully loaded
                await self.page.wait_for_load_state("networkidle", timeout=10000)

                # Additional wait for AJAX requests
                await asyncio.sleep(random.uniform(2.0, 4.0))

                # Extract VRF from captured URL
                if not self._captured_url:
                    raise Exception(f"Unable to capture AJAX request for chapter URL: {chapter_url}")  # pylint: disable=W0719

                parsed_url = urlparse(self._captured_url)
                path = parsed_url.path
                query_params = parse_qs(parsed_url.query)
                vrf = query_params.get('vrf', [None])[0]

                if not vrf:
                    raise Exception(f"Unable to find VRF token in captured URL: {self._captured_url}")  # pylint: disable=W0719

                # Cache the result
                self._vrf_cache[chapter_url] = (path, vrf)
                logger.info("Successfully obtained VRF token for chapter")
                return path, vrf

            except Exception as e:
                logger.error(f"Error getting chapter VRF token: {e}")  # pylint: disable=W1203
                raise
            finally:
                # Cleanup: close page/context like Kotlin destroys WebView
                if self.page:
                    await self.page.close()
                if self.context:
                    await self.context.close()
                self.page = None
                self.context = None

    async def close(self):
        """Close the browser and cleanup (like Kotlin cleanup function)"""
        if self.page:
            await self.page.close()
            self.page = None
        if self.context:
            await self.context.close()
            self.context = None
        if self.browser:
            await self.browser.close()
            self.browser = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None

    def __enter__(self):
        """Context manager entry"""
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """Context manager exit"""
        # Run async close in sync context
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If loop is already running, schedule close
                asyncio.create_task(self.close())
            else:
                loop.run_until_complete(self.close())
        except RuntimeError:
            # No event loop, create one
            asyncio.run(self.close())
        return False

    # Synchronous wrappers for async methods
    def get_chapter_vrf(self, chapter_url: str) -> str:
        """Synchronous wrapper for get_chapter_vrf_async"""
        return asyncio.run(self.get_chapter_vrf_async(chapter_url))

    def get_chapter_vrf_sync(self, chapter_url: str) -> str:
        """Alias for get_chapter_vrf (for compatibility)"""
        return self.get_chapter_vrf(chapter_url)
