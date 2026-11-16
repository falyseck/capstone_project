"""Application entry point: wires the routers together and seeds reference data on startup."""
from contextlib import asynccontextmanager

from fastapi import FastAPI

import models as m
from database import Base, SessionLocal, engine
from dependencies import get_engine
from routers import auth_routes, healthcare, screening


def seed_reference_data(db) -> None:
    if db.query(m.Facility).count() == 0:
        db.add_all([
            m.Facility(name="Centre de Sante Dakar Nord", location="Dakar"),
            m.Facility(name="Centre de Sante Pikine", location="Pikine"),
        ])
    if db.query(m.MLModel).count() == 0:
        try:
            model_name, _ = get_engine().model_metadata()
        except RuntimeError:
            model_name = "not_trained_yet"
        db.add(m.MLModel(algorithm_name=model_name, version="v1", accuracy=None))
    db.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_reference_data(db)
    finally:
        db.close()
    yield


app = FastAPI(title="PPD Risk Screening API", lifespan=lifespan)
app.include_router(auth_routes.router)
app.include_router(screening.router)
app.include_router(healthcare.router)


@app.get("/health")
def health():
    return {"status": "ok"}
