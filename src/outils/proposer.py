"""L'outil propose_action : la seule facon pour l'agent d'agir sur le monde.

Contrairement aux autres outils du dossier, celui-ci ECRIT : il ajoute une
ligne dans la table `actions`, en etat PROPOSEE. Mais ce n'est PAS un effet de
bord au sens du sujet : il ne fait qu'enregistrer une intention, rien ne part
reellement tant qu'un humain n'a pas approuve, puis que l'executeur (qui n'a
jamais acces au modele) ne l'a pas execute.

Contrairement a employes.py et calendrier.py, cet outil a besoin de connaitre
le plan en cours, que Claude ne fournit pas lui-meme. Il est donc construit
au cas par cas, une fois par requete, par `construire_gestionnaire` ci-dessous,
plutot que d'etre un simple couple SCHEMA/executer statique dans le registre.
"""

import hashlib
import json
from datetime import datetime
from typing import Optional

from src import db

# La reversibilite est un FAIT sur l'outil, decide par nous une bonne fois,
# jamais une opinion que le modele pourrait donner ou changer d'un appel a
# l'autre. Si Claude propose un outil hors de cette liste, propose_action le
# refuse : voir _executer plus bas.
OUTILS_CONNUS = {
    "create_github_issue": True,
    "create_employee_record": True,
    "generate_file": True,
    "create_calendar_event": True,
    "send_message": False,  # un message envoye est irreversible
}

SCHEMA = {
    "name": "propose_action",
    "description": (
        "Ajoute une action au plan propose a l'utilisateur. C'est la SEULE "
        "facon d'agir : cette action ne s'executera qu'apres validation "
        "humaine explicite, jamais automatiquement. Appelle cet outil une "
        "fois par action concrete, apres avoir rassemble les informations "
        "necessaires avec les outils de lecture. Les outils valides pour "
        "le champ 'tool' sont : create_github_issue, create_employee_record, "
        "generate_file, create_calendar_event, send_message."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "tool": {
                "type": "string",
                "description": "Nom de l'action, un des cinq outils valides.",
            },
            "args": {
                "type": "object",
                "description": (
                    "Arguments de l'action, propres a l'outil choisi "
                    "(ex. repo/title/body pour create_github_issue)."
                ),
            },
            "reason": {
                "type": "string",
                "description": "Une phrase expliquant pourquoi cette action est utile.",
            },
            "depends_on": {
                "type": ["integer", "null"],
                "description": (
                    "Position (1, 2, 3...) d'une action proposee plus tot "
                    "dans CE plan, si celle-ci n'a de sens qu'apres elle. "
                    "null si aucune dependance."
                ),
            },
        },
        "required": ["tool", "args", "reason"],
    },
}


def _cle_idempotence(plan_id: int, position: int, outil: str, args: dict) -> str:
    """Cle deterministe : memes entrees, meme cle, toujours.

    Calculee ici, a la PROPOSITION, pas a l'execution : c'est ce qui permet
    a l'executeur de detecter un rejeu sans avoir a raisonner lui-meme sur
    ce qui a change.
    """
    args_normalises = json.dumps(args, sort_keys=True, ensure_ascii=True)
    brut = f"{plan_id}:{position}:{outil}:{args_normalises}"
    return hashlib.sha256(brut.encode("utf-8")).hexdigest()


def construire_gestionnaire(plan_id: int, origine: str = "AGENT"):
    """Cree une fonction executer() liee a un plan precis.

    `origine` vaut AGENT quand c'est Claude qui propose de lui-meme,
    HUMAIN quand l'action vient de la barre d'ajout (meme mecanique, un
    humain peut aussi "proposer" une action qui devra etre approuvee).
    """
    compteur = {"position": len(db.lister_actions_du_plan(plan_id))}

    def executer(tool: str, args: dict, reason: str,
                 depends_on: Optional[int] = None) -> dict:
        if tool not in OUTILS_CONNUS:
            return {
                "erreur": (
                    f"Outil inconnu : {tool}. Choisis parmi "
                    f"{sorted(OUTILS_CONNUS)}."
                )
            }

        compteur["position"] += 1
        position = compteur["position"]
        cle = _cle_idempotence(plan_id, position, tool, args)

        action_id = db.creer_action(
            plan_id=plan_id,
            position=position,
            outil=tool,
            arguments=json.dumps(args, ensure_ascii=False),
            raison=reason,
            reversible=OUTILS_CONNUS[tool],
            depends_on=depends_on,
            origine=origine,
            cle_idempotence=cle,
        )
        db.tracer(plan_id, "ACTION_PROPOSEE", origine,
                  f"{tool} (position {position})")

        return {"action_id": action_id, "position": position}

    return executer
