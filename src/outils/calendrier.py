"""Outil de lecture : consulte le calendrier d'un collaborateur.

Aucun effet de bord : cette fonction ne modifie jamais rien, elle lit
uniquement les donnees de test dans seed/calendrier.json.
"""

import json
from datetime import date
from pathlib import Path

CHEMIN_DONNEES = Path(__file__).parent.parent.parent / "seed" / "calendrier.json"

SCHEMA = {
    "name": "read_calendar",
    "description": (
        "Lit les evenements deja poses au calendrier d'un collaborateur, "
        "entre deux dates (bornes incluses). Renvoie la liste des "
        "evenements trouves, vide si l'agenda est libre sur la periode. "
        "A utiliser avant de proposer un evenement, pour vérifier un "
        "creneau libre ou eviter un chevauchement."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "user_id": {
                "type": "string",
                "description": "Identifiant du collaborateur (ex. u001).",
            },
            "start": {
                "type": "string",
                "description": "Date de debut, au format AAAA-MM-JJ.",
            },
            "end": {
                "type": "string",
                "description": "Date de fin, au format AAAA-MM-JJ.",
            },
        },
        "required": ["user_id", "start", "end"],
    },
}


def _charger() -> dict:
    return json.loads(CHEMIN_DONNEES.read_text(encoding="utf-8"))


def executer(user_id: str, start: str, end: str) -> dict:
    """Filtre les evenements de user_id dans l'intervalle [start, end].

    Ne leve jamais : un identifiant inconnu ou un agenda vide sont des
    resultats normaux, pas des erreurs. C'est a Claude de le dire plutot
    que d'inventer un evenement.
    """
    evenements = _charger().get(user_id)
    if evenements is None:
        return {
            "trouve": False,
            "message": f"Aucun calendrier connu pour « {user_id} ».",
        }

    debut_recherche = date.fromisoformat(start)
    fin_recherche = date.fromisoformat(end)

    dans_la_periode = [
        evenement
        for evenement in evenements
        if debut_recherche <= date.fromisoformat(evenement["debut"][:10]) <= fin_recherche
    ]

    return {"trouve": True, "evenements": dans_la_periode}
