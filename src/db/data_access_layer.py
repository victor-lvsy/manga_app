"""Database access layer for managing SQL database connections and sessions."""
import logging
from contextlib import contextmanager
from sqlmodel import SQLModel, create_engine, Session
import coloredlogs
# from sqlalchemy import event
# from sqlalchemy.pool import Pool


logger = logging.getLogger("db-access-layer")
coloredlogs.install(level=logging.INFO)


class DatabaseAccessLayer:
    """Class for managing database connections."""

    def __init__(self):
        """Initialize the database connection with environment variables."""
        logger.info("Initializing database connection")
        self.username = "root"
        self.password = "pwd"
        self.host = "localhost"
        self.port = 3306  # Default MySQL port
        self.db_name = "manga_reader"

        self.url = f'mysql+pymysql://{self.username}:{self.password}@{self.host}:{self.port}/{self.db_name}'
        self.engine = create_engine(
            self.url,
            pool_size=20,  # Maximum number of connections in the pool
            max_overflow=10,  # Maximum number of connections that can be created beyond pool_size
            pool_timeout=30,  # Seconds to wait before giving up on getting a connection
            pool_recycle=3600,  # Recycle connections after 1 hour
            pool_pre_ping=True,  # Enable connection health checks
            echo=False  # Set to True for debugging SQL queries
        )
        # Ensure the tables are created in the database
        SQLModel.metadata.create_all(self.engine)

        # Add connection pool event listeners
        # @event.listens_for(Pool, "checkout")
        # def on_checkout(dbapi_connection, connection_record, connection_proxy):
        #     """Log when a connection is checked out from the pool."""
        #     logger.info("Connection checked out from pool")

        # @event.listens_for(Pool, "checkin")
        # def on_checkin(dbapi_connection, connection_record):
        #     """Log when a connection is returned to the pool."""
        #     logger.info("Connection returned to pool")

        # @event.listens_for(Pool, "connect")
        # def on_connect(dbapi_connection, connection_record):
        #     """Log when a new connection is created."""
        #     logger.info("New connection created")

    @contextmanager
    def managed_session(self):
        """Context manager for handling database sessions.

        Yields:
            Session: A database session that is automatically closed after use
        """
        session = Session(self.engine)
        try:
            yield session
        finally:
            session.close()

    def get_session(self):
        """Get a new database session.

        Returns:
            Session: A new SQLModel session
        """
        session = Session(self.engine)
        try:
            yield session
        finally:
            session.close()
