"""Le bras : execute les actions APPROUVEES, jamais autre chose.

Aucun acces au modele. Ne recoit jamais une action en parametre depuis
l'appelant : `executer_plan` ne recoit qu'un plan_id, relit chaque
action en base et ne traite que celles a l'etat APPROUVEE. On ne peut
pas lui faire executer une action non approuvee, meme par erreur de
code.
"""

import json

from src import db
from src.executeur.handlers import HANDLERS


def _executer_une_action(action: dict) -> dict:
    """Execute une action deja APPROUVEE, avec la garantie d'idempotence.

    La reservation (INSERT dans executions, proteg par la contrainte
    UNIQUE sur cle_idempotence) est tentee AVANT l'appel au handler :
    seule la tentative qui gagne la reservation appelle le handler reel.
    Double clic, retry reseau ou rechargement de page retombent tous sur
    une reservation deja prise, et relisent le resultat existant au lieu
    de rejouer l'effet de bord.
    """
    reservation = db.reserver_execution(action["id"], action["cle_idempotence"])

    if reservation is None:
        deja = db.lire_execution_par_cle(action["cle_idempotence"])
        return {"action_id": action["id"], "deja_execute": True, "execution": deja}

    handler = HANDLERS.get(action["outil"])
    if handler is None:
        resultat = {
            "succes": False,
            "erreur": f"Outil inconnu ou non branche cote executeur : {action['outil']}",
        }
    else:
        try:
            arguments = json.loads(action["arguments"])
            resultat = handler(**arguments)
        except Exception as exc:  # le handler ne doit jamais faire tomber l'executeur
            resultat = {"succes": False, "erreur": str(exc)}

    succes = bool(resultat.get("succes"))
    statut = "SUCCES" if succes else "ECHEC"
    erreur = None if succes else resultat.get("erreur", "Echec inconnu.")

    db.finaliser_execution(
        reservation["id"], statut, json.dumps(resultat, ensure_ascii=False), erreur,
    )

    nouvel_etat = "EXECUTEE" if succes else "ECHOUEE"
    db.maj_etat_action(action["id"], nouvel_etat)

    evenement = "ACTION_EXECUTEE" if succes else "ACTION_ECHOUEE"
    db.tracer(
        action["plan_id"], evenement, "HUMAIN",
        json.dumps(resultat, ensure_ascii=False), action_id=action["id"],
    )

    return {
        "action_id": action["id"],
        "deja_execute": False,
        "etat": nouvel_etat,
        "resultat": resultat,
    }


def executer_plan(plan_id: int) -> list:
    """Execute, dans l'ordre de `position`, toutes les actions APPROUVEES
    du plan. Les actions dans un autre etat (PROPOSEE, REFUSEE, BLOQUEE,
    deja EXECUTEE...) sont ignorees.
    """
    resultats = []
    for action in db.lister_actions_du_plan(plan_id):
        if action["etat"] != "APPROUVEE":
            continue
        resultats.append(_executer_une_action(action))
    return resultats
