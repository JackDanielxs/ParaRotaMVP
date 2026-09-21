"""ParaRota — MVP de Monitoramento de Tempo Parado em Roteiros.
API FastAPI implementando os casos de uso UC01-UC12 do Projeto Preliminar."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

from .database import Base, engine
from .routers import usuarios, pontos, roteiros, parametros, dashboard

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="ParaRota API",
    description="MVP de monitoramento de tempo parado em roteiros de entrega/logística.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(usuarios.router, prefix="/api")
app.include_router(pontos.router, prefix="/api")
app.include_router(roteiros.router, prefix="/api")
app.include_router(parametros.router, prefix="/api")
app.include_router(dashboard.router, prefix="/api")

FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "frontend")

if os.path.isdir(FRONTEND_DIR):
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

    @app.get("/")
    def raiz():
        return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))


@app.get("/api/health")
def health():
    return {"status": "ok", "app": "ParaRota"}
