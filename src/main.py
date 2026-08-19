"""Le serveur. Il expose l'API et sert le front.

Les routes des paliers suivants sont deja declarees ici, meme vides.
Une fois ce fichier ecrit, plus personne n'y touche : c'est le fichier le plus
chaud du projet, et le geler evite les conflits git entre nous deux.
"""

import json
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from anthropic import APIConnectionError, APIStatusError, AuthenticationError
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

load_dotenv()  # avant d'importer planner : il lit la cle dans l'environnement

from src import db, planner  # noqa: E402
from src.executeur import executor  # noqa: E402
from src.executeur import handlers as executeur_handlers  # noqa: E402

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


class DemandeEtatAction(BaseModel):
    """Ce que le front envoie pour approuver ou refuser une action."""
    etat: str


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
        # Sous-classe de APIStatusError : DOIT rester avant elle, sinon ce
        # bloc plus precis ne serait jamais atteint.
        yield _sse({
            "type": "erreur",
            "message": "La cle API est refusee par Anthropic. Verifiez "
                       "qu'elle est valide et a jour, en local (.env) "
                       "comme en production.",
        })
    except APIConnectionError:
        # Coupure reseau, timeout, connexion interrompue avant ou pendant
        # la reponse. C'est exactement le test "je coupe le reseau" du
        # palier 5 : sans ce filet, l'exception traverse ce generateur en
        # silence apres que les entetes SSE (200) sont deja partis, et le
        # navigateur reste bloque sur "Pennyworth reflechit" indefiniment.
        # Le pire spinner infini possible, sur le pire moment possible.
        yield _sse({
            "type": "erreur",
            "message": "Impossible de contacter Claude (reseau coupe ou "
                       "delai depasse). Reessayez dans un instant.",
        })
    except APIStatusError as erreur_api:
        # Tout le reste cote API Anthropic hors authentification : surcharge
        # (529), limite de debit (429), panne cote Anthropic (500/503)...
        # Le code et le message renvoyes par Anthropic sont plus utiles a
        # afficher tels quels qu'a generaliser a l'aveugle.
        yield _sse({
            "type": "erreur",
            "message": f"Anthropic a renvoye une erreur (HTTP "
                       f"{erreur_api.status_code}) : {erreur_api.message}",
        })
    except Exception as exc:
        # Filet de tout dernier recours. Le piege du palier 5 est d'avaler
        # ce genre de cas en silence pour "que ca ne plante plus" : celui-ci
        # ne l'est pas, le message reste honnete et visible a l'ecran
        # plutot que de laisser le flux s'arreter sans explication.
        yield _sse({
            "type": "erreur",
            "message": f"Erreur inattendue : {exc}",
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
    return {**plan, "actions": db.lister_actions_du_plan(plan_id)}


ETATS_VALIDABLES = ("APPROUVEE", "REFUSEE")


@app.patch("/api/actions/{action_id}")
def valider_action(action_id: int, demande: DemandeEtatAction):
    """Approuve ou refuse une action, geste humain, jamais ecrit par l'agent.

    Un refus bascule automatiquement toute la chaine des actions qui en
    dependent en BLOQUEE (enfants, petits-enfants, etc.), avec le motif
    journalise pour chacune.
    """
    if demande.etat not in ETATS_VALIDABLES:
        raise HTTPException(
            status_code=400,
            detail=f"etat doit etre {' ou '.join(ETATS_VALIDABLES)}.",
        )

    action = db.lire_action(action_id)
    if action is None:
        raise HTTPException(status_code=404, detail="Action introuvable.")

    # Garde-fou structurel : une action bloquee en cascade (dependance
    # refusee) ne peut pas etre re-approuvee par un appel PATCH suivant,
    # meme si le navigateur l'envoie juste apres. Sans ce controle, la
    # sequence "je refuse le parent, j'approuve l'enfant deja coche"
    # (l'ordre exact dans lequel la barre d'execution envoie ses PATCH)
    # effacerait silencieusement le blocage et executerait l'action pour
    # de vrai. Verifie sur l'etat relu en base, jamais sur ce que le
    # client pretend savoir.
    if demande.etat == "APPROUVEE" and action["etat"] == "BLOQUEE":
        raise HTTPException(
            status_code=409,
            detail=(
                "Action bloquee : l'action dont elle depend a ete refusee. "
                "Elle ne peut pas etre approuvee tant que ce refus n'est "
                "pas revenu en arriere."
            ),
        )

    db.maj_etat_action(action_id, demande.etat)
    evenement = "ACTION_APPROUVEE" if demande.etat == "APPROUVEE" else "ACTION_REFUSEE"
    db.tracer(action["plan_id"], evenement, "HUMAIN", action_id=action_id)

    if demande.etat == "REFUSEE":
        for enfant, parent_id in db.lister_descendants_en_cascade(action_id):
            db.maj_etat_action(enfant["id"], "BLOQUEE")
            if parent_id == action_id:
                motif = f"Bloquee : l'action dont elle depend (#{action_id}) a ete refusee."
            else:
                motif = (
                    f"Bloquee : l'action dont elle depend (#{parent_id}) "
                    f"a elle-meme ete bloquee (en cascade depuis le refus de #{action_id})."
                )
            db.tracer(
                enfant["plan_id"], "ACTION_BLOQUEE", "HUMAIN", motif,
                action_id=enfant["id"],
            )

    return db.lire_action(action_id)


@app.post("/api/plans/{plan_id}/execute")
def executer_plan(plan_id: int):
    """Execute uniquement les actions APPROUVEES du plan, dans l'ordre.

    Ne recoit que l'identifiant du plan : l'executeur relit lui-meme les
    actions et leur etat en base, il ne les recoit jamais en parametre.
    """
    plan = db.lire_plan(plan_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="Plan introuvable.")

    return {"plan_id": plan_id, "resultats": executor.executer_plan(plan_id)}


@app.get("/api/plans/{plan_id}/audit")
def lire_journal(plan_id: int):
    """Le journal d'un plan : tout l'audit_log, y compris refus et
    blocages. Lu depuis la base a chaque appel, pour survivre a un
    rechargement de page.
    """
    plan = db.lire_plan(plan_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="Plan introuvable.")

    return {"plan_id": plan_id, "evenements": db.lister_audit(plan_id)}


@app.post("/api/actions/{action_id}/compensate")
def annuler_action(action_id: int):
    """Annule (compense) une action deja EXECUTEE, pour de vrai.

    Toute la validation est ici, avant d'appeler executor.annuler_action :
    meme principe que valider_action plus haut, l'humain declenche, le
    serveur garde le dernier mot sur ce qui est permis.
    """
    action = db.lire_action(action_id)
    if action is None:
        raise HTTPException(status_code=404, detail="Action introuvable.")

    if action["etat"] != "EXECUTEE":
        raise HTTPException(
            status_code=409,
            detail=(
                f"Seule une action EXECUTEE peut etre annulee "
                f"(etat actuel : {action['etat']})."
            ),
        )

    if action["outil"] not in executeur_handlers.ANNULATEURS:
        raise HTTPException(
            status_code=409,
            detail=(
                f"Annulation non prise en charge pour l'outil "
                f"{action['outil']}."
            ),
        )

    resultat = executor.annuler_action(action)
    if not resultat.get("succes"):
        raise HTTPException(
            status_code=502,
            detail=resultat.get("erreur", "Echec de l'annulation."),
        )

    return db.lire_action(action_id)


class StaticFilesSansCache(StaticFiles):
    """Comme StaticFiles, mais force le navigateur a revalider a chaque
    chargement plutot que de servir sa propre copie en cache.

    Sans Cache-Control, le navigateur applique un cache "heuristique" et
    un simple Cmd+R peut ne rien recharger du tout, meme apres une vraie
    modification du fichier sur disque. `no-cache` ne desactive pas le
    cache : il force juste une verification (ETag) a chaque fois, qui
    renvoie un 304 si rien n'a change. Utile en dev, et raisonnable en
    prod vu la frequence de nos redeploiements.
    """

    def file_response(self, *args, **kwargs):
        reponse = super().file_response(*args, **kwargs)
        reponse.headers["Cache-Control"] = "no-cache"
        return reponse


# Le front est servi par le meme serveur : une seule URL, pas de CORS a gerer.
app.mount("/", StaticFilesSansCache(directory=DOSSIER_WEB, html=True), name="web")
