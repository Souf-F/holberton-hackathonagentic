"""Test d'idempotence : la garantie anti-doublon tient, du plus bas
niveau (la reservation dans `executions`) jusqu'au plus haut
(l'executeur complet, rejoue deux fois sur le meme plan).

Meme pattern que tests/test_proposer.py : fixture pytest avec base
SQLite temporaire (tmp_path/monkeypatch), jamais data/pennyworth.db.
"""

import pytest

from src import db
from src.executeur import executor
from src.executeur.handlers import send_message


@pytest.fixture
def base_de_test(tmp_path, monkeypatch):
    """Une base SQLite fraiche et isolee, et un outbox/ temporaire pour
    que send_message (declenche par executer_plan) n'ecrive jamais dans
    le vrai dossier outbox/ du depot."""
    monkeypatch.setattr(db, "CHEMIN_BASE", tmp_path / "test_pennyworth.db")
    monkeypatch.setattr(send_message, "DOSSIER_OUTBOX", tmp_path / "outbox")
    db.initialiser()
    yield db


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


def test_reservation_refuse_le_doublon(base_de_test):
    """La contrainte UNIQUE doit refuser une deuxieme reservation avec la meme cle.

    C'est CE test-ci, pas le suivant, qui protege le vrai cas dangereux :
    deux requetes HTTP simultanees (double-clic reel, pas un rechargement
    sequentiel) peuvent toutes les deux lire l'action a l'etat APPROUVEE
    avant qu'aucune des deux n'ait ecrit EXECUTEE (TOCTOU). Le filtre
    `etat = APPROUVEE` de executer_plan (teste plus bas) ne protege que le
    cas sequentiel, ou le premier appel a deja fini et change l'etat avant
    que le second ne commence. Verifie en pratique : en cassant
    volontairement reserver_execution (INSERT OR IGNORE au lieu du INSERT
    protege par la contrainte UNIQUE), ce test echoue immediatement,
    tandis que test_executer_plan_deux_fois_ne_double_pas continue de
    passer sans rien remarquer, puisqu'il n'exerce jamais le chemin
    concurrent.
    """
    plan_id = base_de_test.creer_plan("[TEST] idempotence, reservation directe")
    action_id = _creer_action_approuvee(plan_id, "cle-test-reservation")

    premiere = base_de_test.reserver_execution(action_id, "cle-test-reservation")
    deuxieme = base_de_test.reserver_execution(action_id, "cle-test-reservation")

    assert premiere is not None, "la premiere reservation doit reussir"
    assert deuxieme is None, "la deuxieme reservation (meme cle) doit etre refusee"


def test_executer_plan_deux_fois_ne_double_pas(base_de_test):
    """Rejouer executer_plan() sur le meme plan ne doit jamais creer une
    deuxieme ligne d'execution pour la meme action."""
    plan_id = base_de_test.creer_plan("[TEST] idempotence, executeur complet")
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

    with base_de_test.connexion() as conn:
        nb_executions = conn.execute(
            "SELECT COUNT(*) FROM executions WHERE action_id = ?", (action_id,)
        ).fetchone()[0]
    assert nb_executions == 1, "une seule ligne d'execution, jamais deux"
