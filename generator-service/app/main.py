from fastapi import FastAPI
from app.db import Base, engine
from app.routers.timetable_router import router as timetable_router
from app.routers.task_router import router as tasks_router
from fastapi.middleware.cors import CORSMiddleware

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Timetable API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(tasks_router)

app.include_router(timetable_router)