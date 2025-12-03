"""API for the scraper service"""
import os
from contextlib import asynccontextmanager
from typing import Optional
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from dotenv import load_dotenv

from src.db import ScanlationGroup, ComicType, Status, UpdateFrequency, ComicRepository, DatabaseAccessLayer
from src.scraper.utils import get_scraper
from src.scraper.worker import WorkerContext

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan for the scraper API"""
    worker_context.start_worker()
    yield
    worker_context.cancel_queue()
    await worker_context.worker_task

app = FastAPI(title="Manga Scraper API", version="1.0.0", lifespan=lifespan)

worker_context = WorkerContext()


class CreateComicRequest(BaseModel):
    """Request model for creating a comic"""
    comic_name: str
    comic_url: str
    scanlation_group: str  # "mangafire_to" or "asura_scans"
    comic_type: Optional[str] = "manga"  # "manga" or "webtoon"
    status: Optional[str] = "ongoing"  # "ongoing", "completed", "hiatus"
    update_frequency: Optional[str] = "monthly"  # "weekly", "biweekly", "monthly"
    tags: Optional[list[str]] = None


class ValidateUrlRequest(BaseModel):
    """Request model for validating a URL"""
    url: str
    scanlation_group: str  # "mangafire_to" or "asura_scans"


class RefreshComicRequest(BaseModel):
    """Request model for refreshing a comic"""
    comic_id: int


class RefreshComicResponse(BaseModel):
    """Response model for refreshing a comic"""
    comic_name: str
    chapters_found: int
    message: str


@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "Manga Scraper API", "version": "1.0.0"}


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy"}


@app.post("/comics/create")
async def create_comic(request: CreateComicRequest):
    """Create a new comic"""
    try:
        # Validate scanlation group
        try:
            scan_group = ScanlationGroup(request.scanlation_group)
        except ValueError as exc:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid scanlation_group. Must be one of: {[sg.value for sg in ScanlationGroup]}"
            ) from exc

        # Validate comic type
        try:
            comic_type = ComicType(request.comic_type) if request.comic_type else ComicType.MANGA
        except ValueError as exc:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid comic_type. Must be one of: {[ct.value for ct in ComicType]}"
            ) from exc

        # Validate status
        try:
            status = Status(request.status) if request.status else Status.ONGOING
        except ValueError as exc:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status. Must be one of: {[s.value for s in Status]}"
            ) from exc

        # Validate update frequency
        try:
            update_freq = UpdateFrequency(request.update_frequency) if request.update_frequency else UpdateFrequency.MONTHLY
        except ValueError as exc:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid update_frequency. Must be one of: {[uf.value for uf in UpdateFrequency]}"
            ) from exc

        # Create scraper and comic
        with get_scraper(request.scanlation_group) as scraper:
            comic = scraper.create_comic(
                comic_name=request.comic_name,
                comic_url=request.comic_url,
                scanlation_group=scan_group,
                comic_type=comic_type,
                status=status,
                update_frequency=update_freq,
                tags=request.tags or []
            )

        return {
            "message": "Comic created successfully",
            "comic_id": comic.id,
            "comic_name": comic.name
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.post("/comics/validate-url")
async def validate_url(request: ValidateUrlRequest):
    """Validate a manga URL and get chapter count"""
    try:
        with get_scraper(request.scanlation_group) as scraper:
            is_valid, chapter_count, error_message = scraper.validate_url_and_get_chapter_count(request.url)

        return {
            "is_valid": is_valid,
            "chapter_count": chapter_count,
            "error_message": error_message if not is_valid else None
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.post("/comics/{comic_id}/refresh")
async def refresh_comic(comic_id: int):
    """Refresh a specific comic to check for new chapters"""
    try:
        db_layer = DatabaseAccessLayer()
        with db_layer.managed_session() as session:
            comic_repo = ComicRepository(session)
            comic = comic_repo.get_comic(comic_id)

            if not comic:
                raise HTTPException(status_code=404, detail=f"Comic with id {comic_id} not found")

        await worker_context.put_item(comic)

        return {
            "message": "Refresh started in background",
            "status": "processing"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.post("/scan/all")
async def scan_all_comics(background_tasks: BackgroundTasks):
    """Scan all comics for new chapters (runs in background)"""
    try:
        async def scan_task():
            """Background task to scan all comics"""
            for scan_group in ScanlationGroup:
                db_layer = DatabaseAccessLayer()
                with db_layer.managed_session() as session:
                    comic_repo = ComicRepository(session)
                    for comic in comic_repo.get_comics_by_scanlation_group(scan_group):
                        await worker_context.put_item(comic)

        background_tasks.add_task(scan_task)

        return {
            "message": "Scan started in background",
            "status": "processing"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.post("/scan/{scanlation_group}")
async def scan_scanlation_group(scanlation_group: str, background_tasks: BackgroundTasks):
    """Scan all comics from a specific scanlation group for new chapters"""
    try:
        # Validate scanlation group
        try:
            ScanlationGroup(scanlation_group)
        except ValueError as exc:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid scanlation_group. Must be one of: {[sg.value for sg in ScanlationGroup]}"
            ) from exc

        async def scan_task():
            """Background task to scan comics"""
            try:
                with get_scraper(scanlation_group) as scraper:
                    await scraper.scan_for_new_chapters()
            except Exception as e:
                print(f"Error scanning {scanlation_group}: {e}")

        background_tasks.add_task(scan_task)

        return {
            "message": f"Scan started for {scanlation_group}",
            "status": "processing"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("SCRAPER_API_PORT", "8889"))
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="error")
