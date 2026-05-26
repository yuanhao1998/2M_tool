from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import inspect, text

from database import engine, Base
from routers import accounts, records, analytics, diamonds

Base.metadata.create_all(bind=engine)


def init_db():
    """Add columns that may not exist yet on existing SQLite databases."""
    inspector = inspect(engine)
    accounts_columns = [c["name"] for c in inspector.get_columns("accounts")]
    if "current_diamonds" not in accounts_columns:
        with engine.connect() as conn:
            conn.execute(
                text("ALTER TABLE accounts ADD COLUMN current_diamonds INTEGER NOT NULL DEFAULT 0")
            )
            conn.commit()

init_db()

app = FastAPI(title="Game Account Manager")

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(accounts.router, prefix="/api")
app.include_router(records.router, prefix="/api")
app.include_router(analytics.router, prefix="/api")
app.include_router(diamonds.router, prefix="/api")


@app.get("/api/health")
def health():
    return {"status": "ok"}
