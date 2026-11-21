"""Ponto de entrada unificado da API Calculadora RTC RFB Free Suite PY."""

from pathlib import Path

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import get_settings
from app.modules.danfse.router import router as danfse_router
from app.modules.regime_regular.router import router as regime_regular_router
from app.modules.simples.router import router as simples_router
from app.modules.tabelas_oficiais.router import router as tabelas_router


def create_app() -> FastAPI:
    """Factory da aplicação FastAPI com rotas modulares e suporte opcional ao frontend."""
    settings = get_settings()

    application = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=(
            "Suite open-source unificada para cálculos da Reforma Tributária (RTC) "
            "da Receita Federal: Simples Nacional, Regime Regular e Gerador DANFSE."
        ),
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    api_router = APIRouter(prefix=settings.api_prefix)

    @api_router.get("/health", tags=["Sistema"], summary="Healthcheck da API")
    def healthcheck() -> dict[str, str]:
        return {
            "status": "ok",
            "app": settings.app_name,
            "version": settings.app_version,
            "env": settings.app_env,
        }

    api_router.include_router(simples_router)
    api_router.include_router(regime_regular_router)
    api_router.include_router(danfse_router)
    api_router.include_router(tabelas_router)

    application.include_router(api_router)

    # Em desenvolvimento local, serve o frontend estático diretamente se disponível
    if settings.serve_frontend and settings.frontend_dir.exists():
        application.mount(
            "/",
            StaticFiles(directory=str(settings.frontend_dir), html=True),
            name="frontend",
        )

    return application


app = create_app()


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
        app_dir=str(Path(__file__).resolve().parents[1]),
    )
