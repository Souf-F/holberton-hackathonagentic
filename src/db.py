"""Acces a la base SQLite.

Un seul fichier, pas d'ORM : la partie critique du projet est une contrainte
UNIQUE et une machine a etats. Les deux se lisent mieux en SQL brut, et
s'expliquent mieux a l'oral.
"""

import os
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

CHEMIN_BASE = Path(os.getenv("DATABASE_PATH", "./data/pennyworth.db"))
CHEMIN_SCHEMA = Path(__file__).parent.parent / "schema.sql"


def connexion() -> sqlite3.Connection:
    """Ouvre une connexion. `row_factory` permet de lire les colonnes par nom."""
    CHEMIN_BASE.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(CHEMIN_BASE)
    conn.row_factory = sqlite3.Row
    return conn


def initialiser() -> None:
    """Cree les quatre tables si elles n'existent pas. Appele au demarrage."""
    with connexion() as conn:
        conn.executescript(CHEMIN_SCHEMA.read_text(encoding="utf-8"))


def creer_plan(intention: str) -> int:
    """Enregistre une demande et renvoie son identifiant."""
    with connexion() as conn:
        curseur = conn.execute(
            "INSERT INTO plans (intention, etat, cree_le) VALUES (?, ?, ?)",
            (intention, "PLANIFICATION", datetime.now().isoformat(timespec="seconds")),
        )
        return curseur.lastrowid


def enregistrer_reponse(plan_id: int, reponse: str, usage: dict) -> None:
    """Range la reponse du modele et ce qu'elle a coute."""
    with connexion() as conn:
        conn.execute(
            """UPDATE plans
               SET reponse = ?, etat = ?, cout_eur = ?,
                   tokens_entree = ?, tokens_sortie = ?
               WHERE id = ?""",
            (
                reponse,
                "PRET",
                usage["cout_eur"],
                usage["tokens_entree"],
                usage["tokens_sortie"],
                plan_id,
            ),
        )


def lire_plan(plan_id: int) -> Optional[dict]:
    """Relit un plan par son identifiant. None s'il n'existe pas."""
    with connexion() as conn:
        ligne = conn.execute("SELECT * FROM plans WHERE id = ?", (plan_id,)).fetchone()
        return dict(ligne) if ligne else None


def tracer(plan_id: int, evenement: str, acteur: str, details: str = "") -> None:
    """Ajoute une ligne au journal. On n'efface jamais, on ajoute."""
    with connexion() as conn:
        conn.execute(
            """INSERT INTO audit_log (plan_id, evenement, acteur, details, horodatage)
               VALUES (?, ?, ?, ?, ?)""",
            (plan_id, evenement, acteur, details,
             datetime.now().isoformat(timespec="seconds")),
        )


def creer_action(
    plan_id: int,
    position: int,
    outil: str,
    arguments: str,
    raison: str,
    reversible: bool,
    depends_on: Optional[int],
    origine: str,
    cle_idempotence: str,
) -> int:
    """Ecrit une ligne d'action, en etat PROPOSEE. Renvoie son identifiant.

    Appelee par propose_action (l'agent) ou par la barre d'ajout (l'humain).
    N'execute jamais rien : c'est juste une intention enregistree.
    """
    with connexion() as conn:
        curseur = conn.execute(
            """INSERT INTO actions
               (plan_id, position, outil, arguments, raison, reversible,
                depends_on, origine, etat, cle_idempotence, cree_le)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'PROPOSEE', ?, ?)""",
            (
                plan_id, position, outil, arguments, raison,
                1 if reversible else 0, depends_on, origine,
                cle_idempotence, datetime.now().isoformat(timespec="seconds"),
            ),
        )
        return curseur.lastrowid


def lister_actions(plan_id: int) -> list:
    """Toutes les actions d'un plan, dans l'ordre d'affichage."""
    with connexion() as conn:
        lignes = conn.execute(
            "SELECT * FROM actions WHERE plan_id = ? ORDER BY position",
            (plan_id,),
        ).fetchall()
        return [dict(ligne) for ligne in lignes]


def lire_action(action_id: int) -> Optional[dict]:
    """Relit une action par son identifiant. None si elle n'existe pas."""
    with connexion() as conn:
        ligne = conn.execute(
            "SELECT * FROM actions WHERE id = ?", (action_id,)
        ).fetchone()
        return dict(ligne) if ligne else None


def changer_etat_action(action_id: int, etat: str) -> None:
    """Fait avancer une action dans sa machine a etats (voir schema.sql)."""
    with connexion() as conn:
        conn.execute(
            "UPDATE actions SET etat = ? WHERE id = ?", (etat, action_id)
        )


def actions_dependantes(action_id: int) -> list:
    """Les actions qui dependent de celle-ci (depends_on = action_id)."""
    with connexion() as conn:
        lignes = conn.execute(
            "SELECT * FROM actions WHERE depends_on = ?", (action_id,)
        ).fetchall()
        return [dict(ligne) for ligne in lignes]
