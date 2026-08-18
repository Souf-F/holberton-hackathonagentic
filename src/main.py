"""Le serveur. Il expose l'API et sert le front.

Les routes des paliers suivants sont deja declarees ici, meme vides.
Une fois ce fichier ecrit, plus personne n'y touche : c'est le fichier le plus
chaud du projet, et le geler evite les conflits git entre nous deux.
"""

from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from anthropic import AuthenticationError
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

load_dotenv()  # avant d'importer planner : il lit la cle dans l'environnement

from src import db, planner  # noqa: E402

DOSSIER_WEB = Path(__file__).parent.parent / "web"


@asynccontextmanager
async def cycle_de_vie(app: FastAPI):
    """Cree les tables au demarrage du serveur."""
    db.initialiser()
    yield


app = FastAPI(title="Pennyworth", lifespan=cycle_de_vie)


class DemandeIntention(BaseModel):
    """Ce que le front envoie : une phrase, rien d'autre."""
    intention: str


@app.post("/api/plans")
def creer_plan(demande: DemandeIntention):
    """Recoit une intention, demande une proposition a Claude, la range en base."""
    if not demande.intention.strip():
        raise HTTPException(status_code=400, detail="L'intention est vide.")

    plan_id = db.creer_plan(demande.intention)
    db.tracer(plan_id, "PLAN_CREE", "HUMAIN", demande.intention)

    try:
        resultat = planner.planifier(demande.intention)
    except planner.CleManquante as manque:
        raise HTTPException(status_code=503, detail=str(manque))
    except AuthenticationError:
        # La cle est presente mais Claude la refuse : revoquee, mal copiee,
        # ou pas encore mise a jour sur l'hebergeur apres une rotation.
        raise HTTPException(
            status_code=503,
            detail="La cle API est refusee par Anthropic. Verifiez qu'elle "
                   "est valide et a jour, en local (.env) comme en production.",
        )

    db.enregistrer_reponse(plan_id, resultat["reponse"], resultat)
    db.tracer(plan_id, "PLAN_PROPOSE", "AGENT")

    return {"plan_id": plan_id, **resultat}


@app.get("/api/plans/{plan_id}")
def lire_plan(plan_id: int):
    """Relit un plan deja produit."""
    plan = db.lire_plan(plan_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="Plan introuvable.")
    return plan


# --- Routes des paliers suivants, cablees d'avance, volontairement vides ---

@app.patch("/api/actions/{action_id}")
def valider_action(action_id: int):
    """Palier 4 : approuver ou refuser une action."""
    raise HTTPException(status_code=501, detail="Palier 4.")


@app.post("/api/plans/{plan_id}/execute")
def executer_plan(plan_id: int):
    """Palier 4 : executer uniquement les actions approuvees."""
    raise HTTPException(status_code=501, detail="Palier 4.")


@app.post("/api/actions/{action_id}/compensate")
def annuler_action(action_id: int):
    """Palier 5 : annuler une action deja executee."""
    raise HTTPException(status_code=501, detail="Palier 5.")


# Le front est servi par le meme serveur : une seule URL, pas de CORS a gerer.
app.mount("/", StaticFiles(directory=DOSSIER_WEB, html=True), name="web")
