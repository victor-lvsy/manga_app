"""Context manager for the reader"""
from datetime import datetime
import time
import asyncio

from src.logger import Logger

logger = Logger("context_manager")

class ContextManager:
    """Context manager for the reader"""
    def __init__(self):
        self.start_time = time.time()
        self.active_tasks = set[asyncio.Task]()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return self

    def uptime(self):
        """Return the uptime of the reader"""
        return (datetime.now() - datetime.fromtimestamp(self.start_time))

    def add_task(self, task: asyncio.Task):
        """Add a thread to the context manager"""
        self.active_tasks.add(task)
        task.add_done_callback(self.active_tasks.discard)

    def cleanup(self):
        """Cleanup the context manager"""
        while self.active_tasks:
            task = self.active_tasks.pop()
            task.cancel()
        self.active_tasks = set[asyncio.Task]()
        logger.debug(f"Context manager cleaned up, uptime: {self.uptime()}")

global_context_manager = ContextManager()

def get_context_manager():
    """Get the context manager"""
    return global_context_manager