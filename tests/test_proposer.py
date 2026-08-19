"""Test de non-regression sur src/outils/proposer.py.

Le bug corrige dans la nuit du 18 au 19 aout 2026 : `depends_on` est une
POSITION (1, 2, 3...) dans le contrat de l'outil `propose_action` (voir
son SCHEMA), donnee par le modele, mais etait ecrite telle quelle dans
`actions.depends_on`, une colonne qui reference le vrai id (cle primaire,
auto-incrementee, GLOBALE a toute la table, pas relative a un plan). Le
blocage en cascade d'un refus (voir `db.lister_descendants_en_cascade`,
appelee depuis `main.valider_action`) ne retrouvait alors quasiment
jamais sa cible : refuser une action pendant que ses dependantes
etaient cochees les executait reellement au lieu de les bloquer.

Aucun de ces tests n'appelle l'API Anthropic : `propose_action` est de
la pure ecriture SQLite, elle n'a jamais eu besoin du modele pour
fonctionner. Chaque test travaille sur une base SQLite temporaire,
jamais sur data/pennyworth.db.
"""

import pytest

from src import db
from src.outils import proposer


@pytest.fixture
def base_de_test(tmp_path, monkeypatch):
    """Une base SQLite fraiche et isolee, une par test.

    monkeypatch redirige db.CHEMIN_BASE avant toute connexion : plus sur
    qu'une variable d'environnement, et remis en place automatiquement a
    la fin du test meme si celui-ci echoue.

    Cree aussi 10 actions "decoy" dans un plan separe, avant de rendre la
    main au test. Sans ca, dans une base toute neuve, la premiere action
    creee par le test recoit l'id 1 (AUTOINCREMENT part de 1) : position
    et id coincident par pur hasard, exactement le cas particulier signale
    en commentaire dans proposer.py ("sauf coincidence si l'id reel vaut
    justement 1"). Un test ecrit sans ce decalage ne peut pas distinguer
    "depends_on est bien resolu en id" de "depends_on n'a jamais ete
    touche et vaut deja le bon nombre par accident" : verifie en
    reintroduisant volontairement le bug, un seul test sur quatre le
    detectait avant cet ajout.
    """
    monkeypatch.setattr(db, "CHEMIN_BASE", tmp_path / "test_pennyworth.db")
    db.initialiser()

    plan_leurre = db.creer_plan("plan leurre, jamais utilise dans les assertions")
    for i in range(10):
        db.creer_action(
            plan_id=plan_leurre, position=i + 1, outil="send_message",
            arguments="{}", raison="leurre", reversible=False,
            depends_on=None, origine="AGENT", cle_idempotence=f"leurre-{i}",
        )

    yield db


def test_depends_on_stocke_le_vrai_id_pas_la_position(base_de_test):
    """Le coeur du bug : donner depends_on=1 (une position) doit aboutir
    a l'id REEL de la premiere action, jamais au chiffre 1 lui-meme."""
    plan_id = base_de_test.creer_plan("intention de test")
    executer = proposer.construire_gestionnaire(plan_id, origine="AGENT")

    premiere = executer(
        tool="create_employee_record",
        args={"name": "Test", "role": "Role", "team": "Equipe"},
        reason="creation de la fiche",
        depends_on=None,
    )
    deuxieme = executer(
        tool="send_message",
        args={"channel": "#test", "text": "bonjour"},
        reason="prevenir l'equipe",
        depends_on=1,  # position 1 dans CE plan, pas un id
    )

    action_2 = base_de_test.lire_action(deuxieme["action_id"])
    assert action_2["depends_on"] == premiere["action_id"]


def test_depends_on_ignore_une_position_qui_n_existe_pas(base_de_test):
    """Une position inventee par le modele (aucune action reelle a cette
    position dans ce plan) ne doit jamais etre stockee a tort : mieux
    vaut une action sans dependance affichee qu'une dependance fausse."""
    plan_id = base_de_test.creer_plan("intention de test")
    executer = proposer.construire_gestionnaire(plan_id, origine="AGENT")

    resultat = executer(
        tool="create_employee_record",
        args={"name": "Test", "role": "Role", "team": "Equipe"},
        reason="creation",
        depends_on=99,  # rien a la position 99
    )

    action = base_de_test.lire_action(resultat["action_id"])
    assert action["depends_on"] is None


def test_cascade_de_blocage_retrouve_bien_sa_cible(base_de_test):
    """Bout en bout, le scenario exact qui a revele le bug hier soir :
    l'action ajoutee avec depends_on=1 doit apparaitre parmi les
    descendants en cascade de la premiere action, sinon un refus de
    celle-ci ne la bloquerait jamais (voir main.valider_action)."""
    plan_id = base_de_test.creer_plan("intention de test")
    executer = proposer.construire_gestionnaire(plan_id, origine="AGENT")

    parent = executer(
        tool="create_employee_record",
        args={"name": "Test", "role": "Role", "team": "Equipe"},
        reason="creation",
        depends_on=None,
    )
    enfant = executer(
        tool="send_message",
        args={"channel": "#test", "text": "bonjour"},
        reason="prevenir",
        depends_on=1,
    )

    descendants = base_de_test.lister_descendants_en_cascade(parent["action_id"])
    ids_descendants = [action["id"] for action, _parent_id in descendants]

    assert enfant["action_id"] in ids_descendants


def test_chaine_de_trois_actions_resout_chaque_position_a_son_propre_id(base_de_test):
    """Une position peut aussi bien pointer vers une action deja en base
    (creee lors d'un appel precedent a planifier_stream) que vers une
    action creee DANS le meme appel : les deux chemins doivent resoudre
    correctement, via le meme dictionnaire position -> id tenu a jour au
    fil des appels successifs de executer()."""
    plan_id = base_de_test.creer_plan("intention de test")
    executer = proposer.construire_gestionnaire(plan_id, origine="AGENT")

    a = executer(
        tool="create_employee_record",
        args={"name": "Test", "role": "Role", "team": "Equipe"},
        reason="creation", depends_on=None,
    )
    b = executer(
        tool="create_github_issue",
        args={"repo": "peu-importe", "title": "t", "body": "b"},
        reason="ticket", depends_on=1,
    )
    c = executer(
        tool="send_message",
        args={"channel": "#test", "text": "bonjour"},
        reason="prevenir", depends_on=2,  # depend de l'action b, pas a
    )

    action_c = base_de_test.lire_action(c["action_id"])
    assert action_c["depends_on"] == b["action_id"]
    assert action_c["depends_on"] != a["action_id"]
