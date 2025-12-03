"""Context manager for the reader"""
from datetime import datetime, timedelta
import time
import asyncio

from src.logger import Logger
from src.db import UserRepository, DatabaseAccessLayer


logger = Logger("context-manager")

USER_POLL_INTERVAL = 300


class UserInteraction:
    """User interaction"""
    def __init__(self, user_id: int):
        self.user_id = user_id
        self.connection_time = datetime.now()
        self.last_activity = datetime.now()


class ContextManager:
    """Context manager for the reader"""
    def __init__(self):
        self.loop = None
        self.start_time = 0
        self.active_tasks: set[asyncio.Task] = set()
        self.active_users: set[UserInteraction] = set()
        self.poll_task: asyncio.Task | None = None
        self.data_base_access_layer = DatabaseAccessLayer()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.active_tasks.discard(self.poll_task)
        self.poll_task.cancel()
        return self

    def start(self):
        """Start the context manager"""
        self.start_time = time.time()
        self.loop = asyncio.get_event_loop()
        self.poll_task = self.loop.create_task(self.poll_users())

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
        self.active_tasks = set()
        logger.debug(f"Context manager cleaned up, uptime: {self.uptime()}")

    def user_interaction(self, user_id: int):
        """Add a user interaction to the context manager"""
        if not any(user.user_id == user_id for user in self.active_users):
            self.add_user(user_id)
        else:
            self.update_user(user_id)

    def add_user(self, user_id: int):
        """Add a user to the context manager"""
        self.active_users.add(UserInteraction(user_id))

    def update_user(self, user_id: int):
        """Update a user's last activity time"""
        for user in self.active_users:
            if user.user_id == user_id:
                user.last_activity = datetime.now()
                break

    def remove_user(self, user_id: int):
        """Remove a user from the context manager"""
        user = next((user for user in self.active_users if user.user_id == user_id), None)
        if user:
            logger.info(f"Removing user {user_id}, was active for {user.last_activity - user.connection_time}")
            self.active_users.remove(user)
        else:
            logger.warning(f"User {user_id} not found in active users")

    async def poll_users(self):
        """Poll users and remove inactive users"""
        while True:
            for user in self.active_users:
                if user.last_activity < datetime.now() - timedelta(seconds=USER_POLL_INTERVAL):
                    logger.debug(f"Removing user {user.user_id} because last activity was {user.last_activity.strftime('%d/%m/%y %H:%M:%S')}")
                    with self.data_base_access_layer.managed_session() as session:
                        UserRepository(session).update_user_activity(user.user_id, int((user.last_activity - user.connection_time).total_seconds()))
                    self.remove_user(user.user_id)
            logger.debug(f"Polling users, {len(self.active_users)} active users")
            await asyncio.sleep(USER_POLL_INTERVAL / 2)


global_context_manager = ContextManager()


def get_context_manager():
    """Get the context manager"""
    return global_context_manager
