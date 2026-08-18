"""Le serveur. Il expose l'API et sert le front.

Les routes des paliers suivants sont deja declarees ici, meme vides.
Une fois ce fichier ecrit, plus personne n'y touche : c'est le fichier le plus
chaud du projet, et le geler evite les conflits git entre nous deux.
"""

import json
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from anthropic import AuthenticationError
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
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


def _sse(evenement: dict) -> str:
    """Encode un evenement au format attendu par EventSource / fetch+SSE."""
    return f"data: {json.dumps(evenement, ensure_ascii=False)}\n\n"


def _flux(intention: str, plan_id: int, origine: str):
    """Relaie planifier_stream() en evenements SSE.

    Carte bonus "streaming". Un generateur, pas une fonction async : FastAPI
    l'execute tout seul dans un thread a part, exactement comme pour les
    routes synchrones existantes, donc aucun autre fichier n'a besoin de
    changer de style pour ca.

    Les erreurs qui se produisaient avant sous forme de HTTPException ne
    peuvent plus l'etre une fois le flux ouvert : les entetes HTTP (200,
    text/event-stream) sont deja envoyes des le premier evenement. On les
    transforme donc en evenement `erreur`, que le front affiche dans sa
    carte d'erreur habituelle plutot que de lire le code HTTP.
    """
    try:
        for evenement in planner.planifier_stream(intention, plan_id, origine):
            if evenement["type"] == "fin":
                db.enregistrer_reponse(plan_id, evenement["reponse"], evenement)
                db.tracer(plan_id, "PLAN_PROPOSE", "AGENT")
            yield _sse(evenement)
    except planner.CleManquante as manque:
        yield _sse({"type": "erreur", "message": str(manque)})
    except AuthenticationError:
        # La cle est presente mais Claude la refuse : revoquee, mal copiee,
        # ou pas encore mise a jour sur l'hebergeur apres une rotation.
        yield _sse({
            "type": "erreur",
            "message": "La cle API est refusee par Anthropic. Verifiez "
                       "qu'elle est valide et a jour, en local (.env) "
                       "comme en production.",
        })


@app.post("/api/plans")
def creer_plan(demande: DemandeIntention):
    """Recoit une intention, cree le plan, stream la proposition de Claude."""
    if not demande.intention.strip():
        raise HTTPException(status_code=400, detail="L'intention est vide.")

    plan_id = db.creer_plan(demande.intention)
    db.tracer(plan_id, "PLAN_CREE", "HUMAIN", demande.intention)

    def flux_avec_debut():
        # Le front a besoin du plan_id des la premiere milliseconde, pour
        # mettre a jour l'URL avant meme que Claude ait commence a repondre.
        yield _sse({"type": "debut", "plan_id": plan_id})
        yield from _flux(demande.intention, plan_id, "AGENT")

    return StreamingResponse(flux_avec_debut(), media_type="text/event-stream")


@app.post("/api/plans/{plan_id}/ajouter")
def ajouter_au_plan(plan_id: int, demande: DemandeIntention):
    """La barre d'ajout : relance le MEME planificateur sur un plan existant.

    L'action ajoutee arrive en PROPOSEE comme les autres, jamais
    auto-approuvee sous pretexte qu'elle vient d'une demande humaine
    explicite : ce serait la premiere exception au principe de
    validation, celle que notre hors scope refuse.
    """
    if db.lire_plan(plan_id) is None:
        raise HTTPException(status_code=404, detail="Plan introuvable.")
    if not demande.intention.strip():
        raise HTTPException(status_code=400, detail="L'intention est vide.")

    return StreamingResponse(
        _flux(demande.intention, plan_id, "HUMAIN"),
        media_type="text/event-stream",
    )


@app.get("/api/plans/{plan_id}")
def lire_plan(plan_id: int):
    """Relit un plan deja produit, avec ses actions.

    C'est cette route qui rend la persistance possible : le front garde
    le plan_id dans son URL, et au chargement de la page, rappelle cette
    route pour retrouver l'etat exact la ou on l'avait laisse.
    """
    plan = db.lire_plan(plan_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="Plan introuvable.")
    return {**plan, "actions": db.lister_actions(plan_id)}


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
