"""VRF token generator for MangaFire using Playwright to intercept network requests"""
import asyncio
import random
from typing import Optional, List
from urllib.parse import urlparse, parse_qs

from src.reader.context_manager import get_context_manager
from src.scraper.vrf_telemetry import VRFGeneratorTelemetry, WaitReason
from src.logger import Logger
try:
    from playwright.async_api import async_playwright, Browser, Page, Route, Error as PlaywrightError
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

logger = Logger("vrf-generator")


class VRFGeneratorError(Exception):
    """Exception raised when VRF generator fails"""
    def __init__(self, message: str):
        super().__init__(message)


class DetectedError(Exception):
    """Exception raised when VRF generator detects a bot"""
    def __init__(self, message: str):
        super().__init__(message)


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
        self._telemetry: List[VRFGeneratorTelemetry] = []

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
                    '--disable-setuid-sandbox',
                    '--disable-web-security',
                    '--disable-features=IsolateOrigins,site-per-process',
                    '--disable-site-isolation-trials',
                    '--disable-background-timer-throttling',
                    '--disable-backgrounding-occluded-windows',
                    '--disable-renderer-backgrounding',
                    '--disable-features=TranslateUI',
                    '--disable-ipc-flooding-protection',
                ]
            )

    async def _create_fresh_context_and_page(self):
        """Create fresh context and page (like Kotlin creates fresh WebView)"""
        # Close existing context/page if any
        if self.page:
            await self.page.close()
        if self.context:
            await self.context.close()

        # Randomize viewport slightly to avoid fingerprinting
        viewport_width = random.choice([1920, 1366, 1536, 1440])
        viewport_height = random.choice([1080, 768, 864, 900])

        # Use a more recent Chrome user agent
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
        ]
        user_agent = random.choice(user_agents)

        # Create a new context with realistic settings
        self.context = await self.browser.new_context(
            viewport={'width': viewport_width, 'height': viewport_height},
            user_agent=user_agent,
            locale='en-US',
            timezone_id='America/New_York',
            permissions=['geolocation'],
            geolocation={'latitude': 40.7128, 'longitude': -74.0060},  # NYC coordinates
            color_scheme='light',
            # Set Referer header like Kotlin does
            extra_http_headers={
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Sec-Fetch-User': '?1',
                'Cache-Control': 'max-age=0',
                'Referer': f'{self.base_url}/',
            }
        )

        # Add comprehensive stealth scripts to remove webdriver traces
        await self.context.add_init_script("""
            // Remove webdriver property
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });

            // Override plugins
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });

            // Override languages
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en']
            });

            // Add chrome object
            window.chrome = {
                runtime: {},
                loadTimes: function() {},
                csi: function() {},
                app: {}
            };

            // Override permissions
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );

            // Override getBattery
            if (navigator.getBattery) {
                navigator.getBattery = () => Promise.resolve({
                    charging: true,
                    chargingTime: 0,
                    dischargingTime: Infinity,
                    level: 1
                });
            }

            // Override webdriver in window
            Object.defineProperty(window, 'navigator', {
                value: new Proxy(navigator, {
                    has: (target, key) => (key === 'webdriver' ? false : key in target),
                    get: (target, key) => (key === 'webdriver' ? undefined : target[key])
                })
            });

            // Mock missing properties
            Object.defineProperty(navigator, 'hardwareConcurrency', {
                get: () => 8
            });

            Object.defineProperty(navigator, 'deviceMemory', {
                get: () => 8
            });

            // Override toString methods
            const getParameter = WebGLRenderingContext.prototype.getParameter;
            WebGLRenderingContext.prototype.getParameter = function(parameter) {
                if (parameter === 37445) {
                    return 'Intel Inc.';
                }
                if (parameter === 37446) {
                    return 'Intel Iris OpenGL Engine';
                }
                return getParameter.call(this, parameter);
            };

            // Override canvas fingerprinting
            const toBlob = HTMLCanvasElement.prototype.toBlob;
            const toDataURL = HTMLCanvasElement.prototype.toDataURL;
            const getImageData = CanvasRenderingContext2D.prototype.getImageData;
            HTMLCanvasElement.prototype.toBlob = function(callback, type, quality) {
                const canvas = this;
                return toBlob.call(canvas, callback, type, quality);
            };
            HTMLCanvasElement.prototype.toDataURL = function(type, quality) {
                return toDataURL.call(this, type, quality);
            };
            CanvasRenderingContext2D.prototype.getImageData = function(sx, sy, sw, sh) {
                return getImageData.call(this, sx, sy, sw, sh);
            };

            // Override Notification
            const Notification = window.Notification;
            window.Notification = function(title, options) {
                return new Notification(title, options);
            };
            Object.setPrototypeOf(window.Notification, Notification);
            window.Notification.permission = 'default';
            window.Notification.requestPermission = () => Promise.resolve('default');
        """)

        self.page = await self.context.new_page()

    async def _setup_request_interception(self, target_url: str = None):
        """Setup request interception to capture URLs matching the pattern (like Kotlin WebViewHelper)"""
        self._captured_url = None

        async def handle_route(route: Route):
            """Handle intercepted requests (mimics Kotlin shouldInterceptRequest exactly)"""
            request = route.request
            url = request.url
            parsed_url_obj = urlparse(url)
            context = "request_interception"

            # Allow main page (like Kotlin line 73) - exact match only
            if target_url and url == target_url:
                self._telemetry[-1].log_allowed(url, context)
                await route.continue_()
                return

            # Allow script from their CDN (like Kotlin lines 87-90)
            # Kotlin checks: host.contains("mfcdn.cc") && pathSegments.lastOrNull().orEmpty().contains("js")
            if "mfcdn.cc" in parsed_url_obj.netloc:
                path_segments = [seg for seg in parsed_url_obj.path.split('/') if seg]
                if path_segments and "js" in path_segments[-1].lower():
                    self._telemetry[-1].log_allowed(url, context)
                    await route.continue_()
                    return

            # Allow jquery script (like Kotlin lines 104-107)
            # Kotlin checks: host.contains("cloudflare.com") && encodedPath.contains("jquery")
            if "cloudflare.com" in parsed_url_obj.netloc and "jquery" in parsed_url_obj.path:
                self._telemetry[-1].log_allowed(url, context)
                await route.continue_()
                return

            # Block all images (like Kotlin blockNetworkImage = true)
            if any(url.lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg', '.ico']):
                self._telemetry[-1].log_denied(f"(image) {url}", context)
                await route.abort()
                return

            # For chapter pages: (like Kotlin lines 304-318)
            # If host == "mangafire.to" && path contains "ajax/read":
            #   - If path contains "ajax/read/chapter" or "ajax/read/volume" -> Capture
            #   - Else -> Allow (other ajax/read calls)
            # Else -> Block
            if parsed_url_obj.netloc == "mangafire.to" and "ajax/read" in parsed_url_obj.path:
                if any(pattern in parsed_url_obj.path for pattern in ["ajax/read/chapter", "ajax/read/volume"]):
                    self._telemetry[-1].log_captured(url, context)
                    self._captured_url = url
                    await route.abort()
                    return
                else:
                    # Allow other ajax/read requests (like Kotlin line 314)
                    self._telemetry[-1].log_allowed(url, context)
                    await route.continue_()
                    return
            else:
                self._telemetry[-1].log_denied(url, context)
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
        self._telemetry.append(VRFGeneratorTelemetry(url=chapter_url))
        async with self._lock:
            if chapter_url in self._vrf_cache:
                return self._vrf_cache[chapter_url]

            await self._init_browser()
            await self._create_fresh_context_and_page()

            try:
                context = "base_url_session"
                # First, navigate to the base URL WITHOUT strict interception to establish a session
                # This allows the site to set cookies and perform bot checks
                logger.debug("Establishing session by visiting base URL first (allowing all resources)")

                try:
                    response = await self.page.goto(self.base_url, wait_until="domcontentloaded", timeout=30000)
                    if response and response.status >= 400:
                        self._telemetry[-1].record_warning(f"Base URL returned status {response.status}", context)

                    # Wait a bit for any redirects or bot checks
                    wait_time = random.uniform(2.0, 3.5)
                    self._telemetry[-1].log_wait(wait_time, WaitReason.BOT_CHECK, context)
                    await asyncio.sleep(wait_time)

                    # Check if we're still on the base URL (not redirected)
                    current_url = self.page.url
                    if current_url != self.base_url and current_url != f"{self.base_url}/":
                        self._telemetry[-1].record_warning(f"Redirected from base URL to {current_url}, trying to go back", context)
                        # If redirected, try to go back to base URL
                        if "mangafire.to" in current_url:
                            await self.page.goto(self.base_url, wait_until="domcontentloaded", timeout=30000)
                            wait_time = random.uniform(1.0, 2.0)
                            self._telemetry[-1].log_wait(wait_time, WaitReason.REDIRECT, context)
                            await asyncio.sleep(wait_time)

                    # Simulate human-like behavior: scroll a bit and interact
                    try:
                        await self.page.evaluate("""
                            window.scrollTo(0, Math.random() * 300);
                        """)
                        wait_time = random.uniform(0.8, 1.5)
                        self._telemetry[-1].log_wait(wait_time, WaitReason.SCROLL, context)
                        await asyncio.sleep(wait_time)

                        # Move mouse cursor slightly (simulates human presence)
                        await self.page.mouse.move(random.randint(100, 500), random.randint(100, 500))
                        wait_time = random.uniform(0.3, 0.7)
                        self._telemetry[-1].log_wait(wait_time, WaitReason.MOUSE_MOVE, context)
                        await asyncio.sleep(wait_time)
                    except Exception as e:
                        if "Execution context was destroyed" in str(e):
                            self._telemetry[-1].record_error(e, fatal=False, context=context)
                        else:
                            self._telemetry[-1].record_error(e, fatal=False, context=context)

                except Exception as e:
                    self._telemetry[-1].record_error(e, fatal=False, context=context)
                    wait_time = random.uniform(1.0, 2.0)
                    self._telemetry[-1].log_wait(wait_time, WaitReason.SESSION_ERROR, context)
                    await asyncio.sleep(wait_time)

                # Now set up strict request interception for chapter AJAX requests
                await self._setup_request_interception(target_url=chapter_url)

                # Load chapter page with timeout and retry logic
                context = "chapter_page_load"
                try:
                    logger.debug(f"Loading chapter page to get VRF: {chapter_url}")  # pylint: disable=W1203

                    # Now navigate to the chapter page
                    response = await self.page.goto(chapter_url, wait_until="domcontentloaded", timeout=30000)

                    if self.page.url.rstrip("/") == self.base_url.rstrip("/"):
                        error = DetectedError("Bot detected: redirected to main page")
                        self._telemetry[-1].record_error(error, fatal=True, context=context)
                        raise error

                    # Human-like delay after page load
                    wait_time = random.uniform(1.5, 3.0)
                    self._telemetry[-1].log_wait(wait_time, WaitReason.PAGE_LOAD, context)
                    await asyncio.sleep(wait_time)

                    # Simulate reading behavior: scroll down slowly
                    await self.page.evaluate("""
                        (async () => {
                            const scrollHeight = document.documentElement.scrollHeight;
                            const viewportHeight = window.innerHeight;
                            const scrollSteps = 5;
                            const stepSize = (scrollHeight - viewportHeight) / scrollSteps;

                            for (let i = 0; i < scrollSteps; i++) {
                                window.scrollTo(0, stepSize * (i + 1));
                                await new Promise(resolve => setTimeout(resolve, 200 + Math.random() * 300));
                            }
                        })();
                    """)
                except PlaywrightError as e:
                    self._telemetry[-1].record_error(e, fatal=False, context=context)
                    raise VRFGeneratorError(f"{context}: Playwright Navigation Failed")  # pylint: disable=W0707
                except Exception as e:
                    self._telemetry[-1].record_error(e, fatal=True, context=context)
                    raise e
                # Wait for page to be fully loaded
                try:
                    await self.page.wait_for_load_state("domcontentloaded", timeout=15000)
                except Exception:
                    self._telemetry[-1].record_error(Exception("Network idle timeout, continuing anyway"), fatal=False, context=context)

                # Additional wait for AJAX requests
                wait_time = random.uniform(2.0, 4.0)
                self._telemetry[-1].log_wait(wait_time, WaitReason.AJAX_REQUEST, context)
                await asyncio.sleep(wait_time)

                # Check again if we're still on the correct page
                current_url = self.page.url
                if current_url == self.base_url or current_url == f"{self.base_url}/":
                    self._telemetry[-1].record_error(DetectedError("Bot detected: redirected to main page after page load"), fatal=True, context=context)
                    raise DetectedError("Bot detected: redirected to main page after page load")

                # Extract VRF from captured URL
                if not self._captured_url:
                    error = VRFGeneratorError(f"Unable to capture AJAX request for chapter URL: {chapter_url}")
                    self._telemetry[-1].record_error(error, fatal=False, context=context)
                    raise error

                parsed_url = urlparse(self._captured_url)
                query_params = parse_qs(parsed_url.query)
                vrf = query_params.get('vrf', [None])[0]

                if not vrf:
                    error = VRFGeneratorError(f"Unable to find VRF token in captured URL: {self._captured_url}")
                    self._telemetry[-1].record_error(error, fatal=False, context=context)
                    raise error

                # Cache the result
                self._vrf_cache[chapter_url] = (parsed_url.path, vrf)
                logger.debug("Successfully obtained VRF token for chapter")
                return parsed_url.path, vrf

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
            get_context_manager().add_task(asyncio.create_task(self.close()))
        except Exception as e:
            logger.error(f"Error closing VRF generator: {e}")
            raise
        return False

    # Synchronous wrappers for async methods
    def get_chapter_vrf(self, chapter_url: str) -> str:
        """Synchronous wrapper for get_chapter_vrf_async"""
        loop = asyncio.get_event_loop()
        return get_context_manager().add_task(loop.create_task(self.get_chapter_vrf_async(chapter_url)))

    def get_chapter_vrf_sync(self, chapter_url: str) -> str:
        """Alias for get_chapter_vrf (for compatibility)"""
        return self.get_chapter_vrf(chapter_url)

    def display_telemetry(self) -> str:
        """Display the telemetry"""
        telemetry_str = ""
        for telemetry in self._telemetry:
            telemetry_str += f"{telemetry.to_dict()}\n"
        return telemetry_str
