from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from starlette.middleware.base import BaseHTTPMiddleware

from backend.app.api.routes import router
from backend.app.core.config import get_settings
from backend.app.core.database import SessionLocal, init_db
from backend.app.services.wallet_service import bootstrap_admin, ensure_system_user

REQUESTS = Counter("paykotha_http_requests_total", "HTTP requests", ["method", "path", "status"])
LATENCY = Histogram("paykotha_http_request_seconds", "Request latency", ["method", "path"])


class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        # collapse ids
        label_path = path if path.count("/") < 5 else "/".join(path.split("/")[:4])
        with LATENCY.labels(request.method, label_path).time():
            response: Response = await call_next(request)
        REQUESTS.labels(request.method, label_path, str(response.status_code)).inc()
        return response


@asynccontextmanager
async def lifespan(_: FastAPI):
    Path("data").mkdir(exist_ok=True)
    Path("data/exports").mkdir(parents=True, exist_ok=True)
    init_db()
    settings = get_settings()
    db = SessionLocal()
    try:
        ensure_system_user(db)
        bootstrap_admin(db)
        if settings.seed_demo:
            from backend.app.services.demo_seed import seed_demo_users

            seed_demo_users(db)
    finally:
        db.close()
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        description=(
            "Sandbox core-banking wallet API with double-entry ledger, KYC tiers, "
            "OTP step-up, maker-checker reversals, EOD settlement, and payment-rail adapters. "
            "Not a licensed MFS — architecture-grade simulation for engineering portfolios."
        ),
        version="3.0.0",
        lifespan=lifespan,
    )
    origins = settings.origins
    if settings.app_env != "production" or "*" in origins:
        allow_origins = ["*"] if "*" in origins else origins + ["*"]
        allow_credentials = "*" not in allow_origins
    else:
        allow_origins = origins
        allow_credentials = True
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allow_origins,
        allow_credentials=allow_credentials,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(MetricsMiddleware)
    app.include_router(router, prefix="/api/v1")

    @app.get("/metrics")
    def metrics():
        return PlainTextResponse(generate_latest(), media_type=CONTENT_TYPE_LATEST)

    # parents[0]=app, [1]=backend, [2]=repo root → web/dist (also /app/web/dist in Docker)
    web_dist = Path(__file__).resolve().parents[2] / "web" / "dist"
    if web_dist.exists():
        assets = web_dist / "assets"
        if assets.exists():
            app.mount("/assets", StaticFiles(directory=assets), name="assets")

        index = web_dist / "index.html"

        @app.get("/")
        def spa_index():
            return FileResponse(index)

        @app.get("/{full_path:path}")
        def spa_fallback(full_path: str):
            # Never shadow API / metrics
            if full_path.startswith("api/") or full_path == "metrics":
                from fastapi import HTTPException

                raise HTTPException(status_code=404, detail="Not found")
            candidate = web_dist / full_path
            if candidate.is_file():
                return FileResponse(candidate)
            return FileResponse(index)

    return app


app = create_app()
