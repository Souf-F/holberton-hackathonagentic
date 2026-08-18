"""Outil de lecture : consulte le calendrier d'un collaborateur.

Aucun effet de bord : cette fonction ne modifie jamais rien, elle lit
uniquement les donnees de test dans seed/calendrier.json.
"""

import json
from datetime import datetime
from pathlib import Path

CHEMIN_DONNEES = Path(__file__).parent.parent.parent / "seed" / "calendrier.json"

# La description est ce qui guide Claude, pas le prompt systeme : un
# prompt de 800 lignes ne rattrape jamais une description d'outil floue.
SCHEMA = {
    "name": "read_calendar",
    "description": (
        "Consulte les evenements du calendrier d'un collaborateur sur une "
        "periode donnee. A utiliser pour verifier les disponibilites d'un "
        "employe (par exemple un tuteur ou un manager) avant de proposer "
        "un evenement de calendrier. Renvoie la liste des evenements "
        "existants entre les deux dates, ou une liste vide si rien n'est "
        "prevu sur cette periode ou si l'identifiant est inconnu."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "user_id": {
                "type": "string",
                "description": "Identifiant du collaborateur (ex. \"u001\").",
            },
            "start": {
                "type": "string",
                "description": "Debut de la periode, format ISO 8601 (ex. \"2026-08-24T00:00:00\").",
            },
            "end": {
                "type": "string",
                "description": "Fin de la periode, format ISO 8601.",
            },
        },
        "required": ["user_id", "start", "end"],
    },
}


def _charger() -> dict:
    return json.loads(CHEMIN_DONNEES.read_text(encoding="utf-8"))


def executer(user_id: str, start: str, end: str) -> dict:
    """Filtre les evenements d'un utilisateur sur la periode demandee.

    Ne leve jamais : un calendrier vide ou un identifiant inconnu est un
    resultat normal, pas une erreur. Une date mal formee renvoie aussi une
    liste vide plutot que de faire planter la boucle du planificateur.
    """
    try:
        donnees = _charger()
    except FileNotFoundError:
        return {"evenements": []}

    evenements = donnees.get(user_id, [])
    if not evenements:
        return {"evenements": []}

    try:
        debut_periode = datetime.fromisoformat(start)
        fin_periode = datetime.fromisoformat(end)
    except ValueError:
        return {"evenements": []}

    resultat = [
        evenement
        for evenement in evenements
        if debut_periode <= datetime.fromisoformat(evenement["debut"]) <= fin_periode
    ]
    return {"evenements": sorted(resultat, key=lambda e: e["debut"])}
