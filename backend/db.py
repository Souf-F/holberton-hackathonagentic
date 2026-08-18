"""db.py — Pennyworth
Point 4 : creation de la base et des 4 tables au demarrage.
Point 5 : enregistrer la demande et la reponse dans la table plans.
"""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "pennyworth.db"
SCHEMA_PATH = Path(__file__).parent / "schema.sql"


def init_db() -> None:
    """Cree la base et les 4 tables si elles n'existent pas."""
    schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(schema_sql)
    conn.commit()
    conn.close()


def save_plan(intention: str, reponse: str) -> int:
    """Enregistre la demande (intention) et la reponse dans la table plans.
    Retourne l'id du plan cree.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.execute(
        "INSERT INTO plans (intention, reponse) VALUES (?, ?)",
        (intention, reponse),
    )
    conn.commit()
    plan_id = cursor.lastrowid
    conn.close()
    return plan_id
