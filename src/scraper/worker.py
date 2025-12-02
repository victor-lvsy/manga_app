"""Worker context for the scraper"""
import asyncio
from typing import Optional
from src.logger import Logger
from src.db import Comic
from src.scraper.utils import get_scraper

logger = Logger("worker_context")


class WorkerContext:
    """Worker class to process the queue"""
    def __init__(self):
        self.queue = asyncio.Queue()
        self.worker_task: Optional[asyncio.Task] = None  # pylint: disable=invalid-name

    def start_worker(self):
        """Start the worker"""
        if self.worker_task is None:
            logger.info("Starting worker")
            self.worker_task = asyncio.create_task(self.worker())
            self.worker_task.add_done_callback(self.worker_cleanup)
        return self.worker_task

    async def worker(self):
        """Worker function to process the queue"""
        while True:
            item = await self.queue.get()
            if item is None:
                logger.info("Queue cancelled, breaking")
                self.queue.task_done()
                break
            await self.process_item(item)
            self.queue.task_done()

    async def process_item(self, comic: Comic):
        """Process an item from the queue"""
        logger.debug(f"Processing comic: {comic.name}")
        with get_scraper(comic.scanlation_group.value) as scraper:
            comic_name, chapters_found = await scraper.refresh_comic(comic)
        return comic_name, chapters_found

    async def put_item(self, item: Comic):
        """Put a comic into the queue"""
        await self.queue.put(item)
        logger.debug(f"Put comic: {item.name} into the queue")
        self.start_worker()

    def worker_cleanup(self, _task):
        """Cleanup the worker"""
        logger.info("Worker cleanup")
        if self.worker_task:
            self.worker_task.cancel()
            self.worker_task = None

    def cancel_queue(self):
        """Cancel the queue"""
        self.queue.put(None)
