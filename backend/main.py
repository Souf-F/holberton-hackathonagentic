"""main.py — Pennyworth
Point 1 : le serveur demarre et repond.
Point 2 : la route POST /plans - recoit la phrase, appelle planifier(), renvoie la reponse.
Point 3 : le serveur sert aussi les fichiers du dossier web/.
"""

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import db
from pennyworth import planifier

app = FastAPI(title="Pennyworth")

WEB_DIR = Path(__file__).parent.parent / "web"


@app.on_event("startup")
def on_startup() -> None:
    db.init_db()


class PlanRequest(BaseModel):
    intention: str


class PlanResponse(BaseModel):
    plan_id: int
    intention: str
    reponse: str


@app.post("/plans", response_model=PlanResponse)
def create_plan(payload: PlanRequest) -> PlanResponse:
    reponse = planifier(payload.intention)
    plan_id = db.save_plan(intention=payload.intention, reponse=reponse)
    return PlanResponse(plan_id=plan_id, intention=payload.intention, reponse=reponse)


app.mount("/", StaticFiles(directory=WEB_DIR, html=True), name="web")
