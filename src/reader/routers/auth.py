"""Authentication routes"""
from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from starlette import status as starlette_status
import bcrypt

from src.reader.dependencies import get_user_repository, UserRepository
from src.reader.templates import templates

router = APIRouter()


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, error: str | None = None):
    """Display login page"""
    return templates.TemplateResponse("login.html", {
        "request": request,
        "error": error,
    })


@router.post("/login", response_class=HTMLResponse)
async def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    user_repo: UserRepository = Depends(get_user_repository),
):
    """Handle login"""
    user = user_repo.get_user_by_username(username)

    if not user:
        return templates.TemplateResponse("login.html", {
            "request": request,
            "error": "Nom d'utilisateur ou mot de passe incorrect",
        })

    # Verify password using bcrypt
    password_valid = False
    try:
        # Check if password is already hashed (starts with $2b$)
        if user.password.startswith("$2b$"):
            # Password is hashed, verify it
            password_bytes = password.encode('utf-8')
            hashed_bytes = user.password.encode('utf-8')
            password_valid = bcrypt.checkpw(password_bytes, hashed_bytes)
        else:
            # Password is not hashed (legacy plain text), treat as invalid
            password_valid = False
    except (ValueError, AttributeError):
        # Invalid hash format or other error, treat as invalid password
        password_valid = False

    if not password_valid:
        return templates.TemplateResponse("login.html", {
            "request": request,
            "error": "Nom d'utilisateur ou mot de passe incorrect",
        })

    # Set session
    request.session["user_id"] = user.id

    # Redirect to home page
    return RedirectResponse(
        url=request.url_for("acceuil"),
        status_code=starlette_status.HTTP_303_SEE_OTHER,
    )


@router.get("/logout", response_class=HTMLResponse)
async def logout(request: Request):
    """Handle logout"""
    request.session.clear()
    return RedirectResponse(
        url=request.url_for("login_page"),
        status_code=starlette_status.HTTP_303_SEE_OTHER,
    )

