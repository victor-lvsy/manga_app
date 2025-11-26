"""Templates configuration"""
from fastapi.templating import Jinja2Templates
from fastapi import Request

from src.db import UserRepository, DatabaseAccessLayer

templates = Jinja2Templates(directory="src/reader/templates")

# Initialize database access layer for template helper
db_layer = DatabaseAccessLayer()


def get_current_user_from_request(request: Request):
    """Helper function to get current user from request session for templates"""
    try:
        user_id = request.session.get("user_id")
        if not user_id:
            return None
        with db_layer.managed_session() as session:
            user_repo = UserRepository(session)
            return user_repo.get_user(user_id)
    except (AttributeError, KeyError, AssertionError):
        return None


# Add helper function to template globals
templates.env.globals["get_current_user_from_request"] = get_current_user_from_request

