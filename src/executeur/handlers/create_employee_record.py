"""Effet de bord reel : cree la fiche d'un nouveau collaborateur.

Jamais expose a Claude (voir src/outils/ pour la liste des outils de
lecture donnes au modele). Seul l'executeur appelle `executer`, apres
qu'un humain a approuve l'action.

Ecrit dans data/employes_crees.json plutot que dans seed/employes.json :
le seed est une fixture de test, versionnee et stable, ce fichier-ci est
une vraie ecriture a l'execution, ignoree par git comme le reste de
data/. src/outils/employes.py lit les deux, fusionnes, pour qu'une
fiche tout juste creee soit immediatement trouvable par get_employee_info.
"""

import json
import uuid
from pathlib import Path
from typing import Optional

NOM = "create_employee_record"

CHEMIN_CREES = Path(__file__).parent.parent.parent.parent / "data" / "employes_crees.json"


def _charger() -> list:
    if not CHEMIN_CREES.exists():
        return []
    return json.loads(CHEMIN_CREES.read_text(encoding="utf-8"))


def _sauvegarder(employes: list) -> None:
    CHEMIN_CREES.parent.mkdir(parents=True, exist_ok=True)
    CHEMIN_CREES.write_text(
        json.dumps(employes, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def executer(name: str, role: str, team: str, manager: Optional[str] = None) -> dict:
    """Ajoute une fiche a data/employes_crees.json.

    Ne leve jamais : une ecriture disque impossible doit remonter comme
    un echec structure, pas faire planter l'executeur.
    """
    try:
        employes = _charger()
        nouvel_id = f"nouveau-{uuid.uuid4().hex[:8]}"
        employes.append({
            "id": nouvel_id,
            "nom": name,
            "poste": role,
            "equipe": team,
            "manager": manager,
        })
        _sauvegarder(employes)
        return {"succes": True, "id": nouvel_id, "nom": name}
    except OSError as exc:
        return {"succes": False, "erreur": f"Ecriture impossible : {exc}"}
