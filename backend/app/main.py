from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from sqlalchemy import select
from app.config import settings
from app.database import engine, Base
from app.api import projects, urls, credits, users, admin, auth_routes, notifications
from app.models import URL
from app.services.indexing.sitemap_ping import generate_sitemap
from app.services.indexing.social_signals import generate_rss_feed
from app.rate_limit import limiter

app = FastAPI(
    title="Indexing Service API",
    description="SEO Indexation Service — Submit URLs and track indexation",
    version="1.0.0",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_routes.router)
app.include_router(users.router)
app.include_router(projects.router)
app.include_router(urls.router)
app.include_router(credits.router)
app.include_router(admin.router)
app.include_router(notifications.router)


@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    Path(settings.SITEMAPS_DIR).mkdir(parents=True, exist_ok=True)


@app.get("/")
async def root():
    return {"service": "Indexing Service", "version": "1.0.0", "docs": "/docs"}


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/sitemaps/{project_id}.xml")
async def serve_sitemap(project_id: str):
    from app.database import async_session

    async with async_session() as db:
        result = await db.execute(select(URL).where(URL.project_id == project_id))
        url_objects = result.scalars().all()

    if not url_objects:
        return Response(content="<urlset/>", media_type="application/xml", status_code=404)

    sitemap_path = Path(settings.SITEMAPS_DIR) / f"{project_id}.xml"
    generate_sitemap([u.url for u in url_objects], str(sitemap_path))
    return Response(content=sitemap_path.read_text(), media_type="application/xml")


@app.get("/feeds/{project_id}/rss.xml")
async def serve_rss(project_id: str):
    from app.database import async_session

    async with async_session() as db:
        result = await db.execute(select(URL).where(URL.project_id == project_id))
        url_objects = result.scalars().all()

    if not url_objects:
        return Response(content="<rss/>", media_type="application/xml", status_code=404)

    feed_url = f"{settings.BASE_URL}/feeds/{project_id}/rss.xml"
    rss_content = generate_rss_feed([u.url for u in url_objects], feed_url)
    return Response(content=rss_content, media_type="application/xml")
