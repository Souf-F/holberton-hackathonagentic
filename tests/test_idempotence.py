"""Test d'idempotence : la garantie anti-doublon tient, du plus bas
niveau (la reservation dans `executions`) jusqu'au plus haut
(l'executeur complet, rejoue deux fois sur le meme plan).

Autonome, sans pytest : `python3 tests/test_idempotence.py`. Utilise une
base SQLite et un dossier outbox temporaires, jamais les vrais.
"""

import os
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

CHEMIN_BASE_TEMP = tempfile.NamedTemporaryFile(suffix=".db", delete=False).name
DOSSIER_OUTBOX_TEMP = tempfile.mkdtemp()
os.environ["DATABASE_PATH"] = CHEMIN_BASE_TEMP
os.environ["OUTBOX_DIR"] = DOSSIER_OUTBOX_TEMP

from src import db  # noqa: E402
from src.executeur import executor  # noqa: E402


def _creer_action_approuvee(plan_id: int, cle_idempotence: str) -> int:
    with db.connexion() as conn:
        return conn.execute(
            """INSERT INTO actions
               (plan_id, position, outil, arguments, raison, reversible,
                depends_on, origine, etat, cle_idempotence, cree_le)
               VALUES (?, 1, 'send_message',
                       '{"channel": "test@example.com", "text": "test"}',
                       'test', 1, NULL, 'AGENT', 'APPROUVEE', ?, datetime('now'))""",
            (plan_id, cle_idempotence),
        ).lastrowid


def test_reservation_refuse_le_doublon():
    """La contrainte UNIQUE doit refuser une deuxieme reservation avec la meme cle."""
    plan_id = db.creer_plan("[TEST] idempotence, reservation directe")
    action_id = _creer_action_approuvee(plan_id, "cle-test-reservation")

    premiere = db.reserver_execution(action_id, "cle-test-reservation")
    deuxieme = db.reserver_execution(action_id, "cle-test-reservation")

    assert premiere is not None, "la premiere reservation doit reussir"
    assert deuxieme is None, "la deuxieme reservation (meme cle) doit etre refusee"
    print("OK : reserver_execution refuse un doublon de cle")


def test_executer_plan_deux_fois_ne_double_pas():
    """Rejouer executer_plan() sur le meme plan ne doit jamais creer une
    deuxieme ligne d'execution pour la meme action."""
    plan_id = db.creer_plan("[TEST] idempotence, executeur complet")
    action_id = _creer_action_approuvee(plan_id, "cle-test-executeur")

    premiers_resultats = executor.executer_plan(plan_id)
    assert len(premiers_resultats) == 1
    assert premiers_resultats[0]["deja_execute"] is False

    # L'action est maintenant EXECUTEE : un deuxieme appel ne doit meme
    # plus la voir, le filtre etat = APPROUVEE l'exclut.
    deuxiemes_resultats = executor.executer_plan(plan_id)
    assert deuxiemes_resultats == [], (
        "un deuxieme executer_plan() ne doit rien retraiter : l'action "
        "n'est plus APPROUVEE, elle est deja EXECUTEE"
    )

    with db.connexion() as conn:
        nb_executions = conn.execute(
            "SELECT COUNT(*) FROM executions WHERE action_id = ?", (action_id,)
        ).fetchone()[0]
    assert nb_executions == 1, "une seule ligne d'execution, jamais deux"
    print("OK : executer_plan() rejoue ne cree jamais une deuxieme execution")


if __name__ == "__main__":
    db.initialiser()
    try:
        test_reservation_refuse_le_doublon()
        test_executer_plan_deux_fois_ne_double_pas()
        print("\nTous les tests d'idempotence passent.")
    finally:
        os.unlink(CHEMIN_BASE_TEMP)
        shutil.rmtree(DOSSIER_OUTBOX_TEMP, ignore_errors=True)
