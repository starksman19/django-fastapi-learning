from fastapi import FastAPI

from app.config import get_settings
from app.errors import install_exception_handlers
from app.routers import appointments, catalog


settings = get_settings()
app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description="Referencyjne API rezerwacji wizyt w FastAPI i SQLAlchemy.",
)
install_exception_handlers(app)
app.include_router(catalog.router)
app.include_router(appointments.router)


@app.get("/health", tags=["operations"])
def health():
    from sqlalchemy import text

    from app.database import engine

    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    return {"status": "ok", "service": "appointments-fastapi"}
