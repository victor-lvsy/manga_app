"""Context manager for the reader"""
from datetime import datetime, timedelta
import time
import asyncio
from typing import Dict

from src.logger import Logger

logger = Logger("context_manager")

USER_POLL_INTERVAL = 600


class ContextManager:
    """Context manager for the reader"""
    def __init__(self):
        loop = asyncio.get_event_loop()
        self.start_time = time.time()
        self.active_tasks = set[asyncio.Task]()
        self.active_users: Dict[int, datetime] = {}
        self.poll_task = loop.create_task(self.poll_users())

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.active_tasks.discard(self.poll_task)
        self.poll_task.cancel()
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

    def user_interaction(self, user_id: int):
        """Add a user interaction to the context manager"""
        if user_id not in self.active_users:
            self.add_user(user_id)
        else:
            self.update_user(user_id)

    def add_user(self, user_id: int):
        """Add a user to the context manager"""
        self.active_users.setdefault(user_id, datetime.now())

    def update_user(self, user_id: int):
        """Update a user's last activity time"""
        self.active_users[user_id] = datetime.now()

    def remove_user(self, user_id: int):
        """Remove a user from the context manager"""
        self.active_users.pop(user_id, None)

    async def poll_users(self):
        """Poll users and remove inactive users"""
        while True:
            logger.debug(f"Polling users, {len(self.active_users)} active users")
            for user_id, last_activity in self.active_users.items():
                if last_activity < datetime.now() - timedelta(minutes=USER_POLL_INTERVAL):
                    logger.debug(f"Removing user {user_id} because last activity was {last_activity.strftime('%d/%m/%y %H:%M:%S')}")
                    self.remove_user(user_id)
            await asyncio.sleep(USER_POLL_INTERVAL / 2)


global_context_manager = ContextManager()


def get_context_manager():
    """Get the context manager"""
    return global_context_manager
