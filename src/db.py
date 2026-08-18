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
