"""Outil de lecture : recherche la fiche d'un collaborateur.

Aucun effet de bord : cette fonction ne modifie jamais rien, elle lit
uniquement les donnees de test dans seed/employes.json.
"""

import json
from pathlib import Path

CHEMIN_DONNEES = Path(__file__).parent.parent.parent / "seed" / "employes.json"

# La description est ce qui guide Claude, pas le prompt systeme : un
# prompt de 800 lignes ne rattrape jamais une description d'outil floue.
SCHEMA = {
    "name": "get_employee_info",
    "description": (
        "Cherche la fiche d'un collaborateur de l'entreprise par son nom "
        "ou une partie de son nom (recherche insensible a la casse). "
        "Renvoie sa fiche (poste, equipe, manager) si trouve, ou une "
        "reponse indiquant qu'aucun resultat n'a ete trouve. A utiliser "
        "des qu'il faut connaitre le poste, l'equipe ou le manager de "
        "quelqu'un avant de proposer une action qui le concerne."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
                "description": "Nom ou prenom de la personne recherchee.",
            }
        },
        "required": ["name"],
    },
}


def _charger() -> list:
    return json.loads(CHEMIN_DONNEES.read_text(encoding="utf-8"))


def executer(name: str) -> dict:
    """Cherche une correspondance partielle, insensible a la casse.

    Ne leve jamais : une recherche sans resultat est un resultat normal,
    pas une erreur. C'est a Claude de dire qu'il n'a rien trouve plutot
    que d'inventer une fiche.
    """
    terme = name.strip().lower()
    for employe in _charger():
        if terme and terme in employe["nom"].lower():
            return {"trouve": True, "employe": employe}
    return {
        "trouve": False,
        "message": f"Aucun collaborateur trouve pour « {name} ».",
    }
