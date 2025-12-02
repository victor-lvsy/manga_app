"""Main FastAPI application"""
import os
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette import status as starlette_status
from starlette.responses import RedirectResponse

from src.config import RUN_MODE
from src.logger import Logger
from src.reader.routers import auth, library, manga, chapter, add_manga, admin, images
from src.reader.context_manager import get_context_manager

load_dotenv()
SECRET_KEY = os.getenv("SECRET_KEY")

logger = Logger("app")


class AuthMiddleware(BaseHTTPMiddleware):
    """Middleware to check authentication for protected routes"""
    async def dispatch(self, request, call_next):
        # Allow access to login, logout, and static files without authentication
        if RUN_MODE == "dev":
            request.scope["scheme"] = "http"
        else:
            request.scope["scheme"] = "https"
        if (request.url.path.startswith("/static")
                or request.url.path == "/login"
                or request.url.path == "/logout"):
            return await call_next(request)

        # Check if user is authenticated
        # SessionMiddleware runs first (outermost) and sets up the session
        # so it should be available when AuthMiddleware (innermost) runs
        try:
            user_id = request.session.get("user_id")
            if not user_id:
                return RedirectResponse(url="/login", status_code=starlette_status.HTTP_303_SEE_OTHER)
        except (AttributeError, KeyError, AssertionError):
            # Session not available, redirect to login
            return RedirectResponse(url="/login", status_code=starlette_status.HTTP_303_SEE_OTHER)

        return await call_next(request)


@asynccontextmanager
async def lifespan(_application: FastAPI):
    """Lifespan for the application"""
    context_manager = get_context_manager()
    context_manager.start()
    yield
    context_manager.cleanup()

app = FastAPI(title="Manga Viewer", lifespan=lifespan)


# Add authentication middleware first (innermost - runs after session is set up)
app.add_middleware(AuthMiddleware)
# Add session middleware last (outermost - runs first to set up session)
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)

app.mount("/static", StaticFiles(directory="src/reader/static"), name="static")

# Include routers
app.include_router(auth.router)
app.include_router(library.router)
app.include_router(manga.router)
app.include_router(chapter.router)
app.include_router(add_manga.router)
app.include_router(admin.router)
app.include_router(images.router)


if __name__ == "__main__":
    import uvicorn

    if RUN_MODE == "dev":
        uvicorn.run(app, host="0.0.0.0", port=8888, log_level="error")
    else:
        uvicorn.run(app, host="0.0.0.0", port=8888, log_level="error")
