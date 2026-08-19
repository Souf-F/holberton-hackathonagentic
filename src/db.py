"""Acces a la base SQLite.

Un seul fichier, pas d'ORM : la partie critique du projet est une contrainte
UNIQUE et une machine a etats. Les deux se lisent mieux en SQL brut, et
s'expliquent mieux a l'oral.

Injection SQL : chaque requete de ce fichier passe ses valeurs comme
parametres (`?`), jamais par concatenation ou f-string dans le SQL
lui-meme. sqlite3 les transmet au moteur separement du texte de la
requete, qui ne peut donc jamais etre modifie par une valeur (une
intention utilisateur, un nom d'outil...), meme malveillante. C'est une
garantie structurelle : casser cette protection demanderait de
construire une requete par concatenation quelque part dans ce fichier,
ce qu'aucune fonction ci-dessous ne fait.
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


def tracer(
    plan_id: int, evenement: str, acteur: str, details: str = "",
    action_id: Optional[int] = None,
) -> None:
    """Ajoute une ligne au journal. On n'efface jamais, on ajoute."""
    with connexion() as conn:
        conn.execute(
            """INSERT INTO audit_log (plan_id, action_id, evenement, acteur, details, horodatage)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (plan_id, action_id, evenement, acteur, details,
             datetime.now().isoformat(timespec="seconds")),
        )


def lister_audit(plan_id: int) -> list:
    """Relit le journal d'un plan, dans l'ordre chronologique."""
    with connexion() as conn:
        lignes = conn.execute(
            "SELECT * FROM audit_log WHERE plan_id = ? ORDER BY id", (plan_id,)
        ).fetchall()
        return [dict(ligne) for ligne in lignes]


# --- Actions : lues par l'humain (validation) et par l'executeur ---

def lire_action(action_id: int) -> Optional[dict]:
    """Relit une action par son identifiant. None si elle n'existe pas."""
    with connexion() as conn:
        ligne = conn.execute("SELECT * FROM actions WHERE id = ?", (action_id,)).fetchone()
        return dict(ligne) if ligne else None


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


def lister_actions_du_plan(plan_id: int) -> list:
    """Relit les actions d'un plan, dans l'ordre d'affichage (position)."""
    with connexion() as conn:
        lignes = conn.execute(
            "SELECT * FROM actions WHERE plan_id = ? ORDER BY position", (plan_id,)
        ).fetchall()
        return [dict(ligne) for ligne in lignes]


def lister_actions_dependantes(action_id: int) -> list:
    """Les actions dont `depends_on` pointe vers celle-ci (un seul niveau)."""
    with connexion() as conn:
        lignes = conn.execute(
            "SELECT * FROM actions WHERE depends_on = ?", (action_id,)
        ).fetchall()
        return [dict(ligne) for ligne in lignes]


def lister_descendants_en_cascade(action_id: int) -> list:
    """Toutes les actions qui dependent de action_id, directement ou via
    une chaine de `depends_on` (enfants, petits-enfants, etc.).

    Parcours en largeur, une action deja vue n'est jamais reparcourue :
    protege contre un cycle dans les donnees (A depend de B qui depend
    de A), qui ne devrait jamais arriver mais peut etre insere a la main.
    Sans cette protection, un tel cycle ferait boucler cette fonction a
    l'infini.

    Renvoie une liste de (action, parent_id), parent_id etant l'action
    dont elle depend directement dans ce parcours precis.
    """
    vues = {action_id}
    resultat = []
    a_traiter = [action_id]
    while a_traiter:
        parent_id = a_traiter.pop(0)
        for enfant in lister_actions_dependantes(parent_id):
            if enfant["id"] in vues:
                continue
            vues.add(enfant["id"])
            resultat.append((enfant, parent_id))
            a_traiter.append(enfant["id"])
    return resultat


def maj_etat_action(action_id: int, etat: str) -> None:
    """Change l'etat d'une action. La contrainte CHECK du schema refuse
    tout etat qui ne serait pas dans la machine a etats."""
    with connexion() as conn:
        conn.execute("UPDATE actions SET etat = ? WHERE id = ?", (etat, action_id))


def reserver_compensation(action_id: int) -> bool:
    """Tente de gagner le droit de compenser cette action, atomiquement.

    Meme logique que reserver_execution, mais sans table dediee : la
    transition EXECUTEE -> COMPENSEE elle-meme sert de verrou, via un
    UPDATE conditionne sur l'etat actuel. Si deux requetes /compensate
    arrivent en meme temps sur la meme action, SQLite serialise les
    ecritures : une seule des deux UPDATE peut trouver la ligne encore a
    EXECUTEE, l'autre ne modifie rien (rowcount = 0). Renvoie True pour
    celle qui a gagne, False pour l'autre (annulation deja en cours ou
    action qui n'etait de toute facon plus EXECUTEE).

    En cas d'echec de la compensation reelle apres coup, l'appelant doit
    remettre l'etat a EXECUTEE (voir executor.annuler_action) : cette
    fonction ne fait que reserver le droit d'essayer, pas confirmer le
    resultat.
    """
    with connexion() as conn:
        curseur = conn.execute(
            "UPDATE actions SET etat = 'COMPENSEE' WHERE id = ? AND etat = 'EXECUTEE'",
            (action_id,),
        )
        return curseur.rowcount > 0


# --- Executions : la preuve, avec la garantie anti-doublon ---

def reserver_execution(action_id: int, cle_idempotence: str) -> Optional[dict]:
    """Tente de reserver le creneau d'execution pour cette cle.

    On insere une ligne provisoire (statut ECHEC par defaut, corrigee par
    `finaliser_execution` juste apres) AVANT d'appeler le handler reel :
    c'est cet INSERT, protege par la contrainte UNIQUE sur
    executions.cle_idempotence, qui empeche le handler d'etre appele deux
    fois pour la meme action (double clic, retry, rechargement). On ne
    verifie jamais "a la main" avant d'inserer : on tente, et on capture
    l'exception d'unicite si quelqu'un nous a devances.

    Renvoie la ligne inseree si la reservation reussit, None sinon.
    """
    with connexion() as conn:
        try:
            curseur = conn.execute(
                """INSERT INTO executions
                   (action_id, cle_idempotence, statut, resultat, erreur, execute_le)
                   VALUES (?, ?, 'ECHEC', NULL, 'execution en cours', ?)""",
                (action_id, cle_idempotence, datetime.now().isoformat(timespec="seconds")),
            )
            return {"id": curseur.lastrowid}
        except sqlite3.IntegrityError:
            return None


def finaliser_execution(
    execution_id: int, statut: str, resultat: Optional[str], erreur: Optional[str],
) -> None:
    """Ecrit le vrai resultat sur la reservation, une fois le handler execute."""
    with connexion() as conn:
        conn.execute(
            "UPDATE executions SET statut = ?, resultat = ?, erreur = ? WHERE id = ?",
            (statut, resultat, erreur, execution_id),
        )


def lire_execution_par_cle(cle_idempotence: str) -> Optional[dict]:
    """Relit l'execution existante pour une cle deja prise. Sert au rejeu :
    on renvoie le resultat memorise au lieu de refaire l'appel reel."""
    with connexion() as conn:
        ligne = conn.execute(
            "SELECT * FROM executions WHERE cle_idempotence = ?", (cle_idempotence,)
        ).fetchone()
        return dict(ligne) if ligne else None
