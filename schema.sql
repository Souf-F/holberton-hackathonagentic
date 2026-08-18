-- Pennyworth : schema de la base.
--
-- Quatre tables, et la separation reflete celle du produit :
--   le planificateur n'ecrit que dans plans et actions,
--   l'executeur n'ecrit que dans executions et audit_log.
--
-- Palier 2 : seule `plans` est reellement utilisee. Les trois autres sont
-- creees des maintenant pour ne pas y revenir demain.

PRAGMA foreign_keys = ON;


-- 1. PLANS : une intention utilisateur = un plan.
CREATE TABLE IF NOT EXISTS plans (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    intention     TEXT    NOT NULL,
    reponse       TEXT,
    etat          TEXT    NOT NULL DEFAULT 'PLANIFICATION'
                  CHECK (etat IN ('PLANIFICATION', 'PRET', 'EXECUTE')),
    cout_eur      REAL    DEFAULT 0,
    tokens_entree INTEGER DEFAULT 0,
    tokens_sortie INTEGER DEFAULT 0,
    cree_le       TEXT    NOT NULL
);


-- 2. ACTIONS : les lignes du plan. Ce qu'on VEUT faire.
-- Rien n'est execute a ce stade : une action est une intention, pas un fait.
CREATE TABLE IF NOT EXISTS actions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    plan_id         INTEGER NOT NULL REFERENCES plans(id),
    position        INTEGER NOT NULL,        -- ordre d'affichage a l'ecran
    outil           TEXT    NOT NULL,
    arguments       TEXT    NOT NULL,        -- JSON des parametres de l'outil
    raison          TEXT,                    -- pourquoi l'agent la propose
    reversible      INTEGER NOT NULL DEFAULT 1,
    depends_on      INTEGER REFERENCES actions(id),
    origine         TEXT    NOT NULL DEFAULT 'AGENT'
                    CHECK (origine IN ('AGENT', 'HUMAIN')),
    etat            TEXT    NOT NULL DEFAULT 'PROPOSEE'
                    CHECK (etat IN ('PROPOSEE', 'APPROUVEE', 'REFUSEE',
                                    'BLOQUEE', 'EXECUTEE', 'ECHOUEE',
                                    'COMPENSEE')),
    cle_idempotence TEXT    NOT NULL,        -- sha256(plan_id + position + outil + args)
    cree_le         TEXT    NOT NULL
);


-- 3. EXECUTIONS : ce qui s'est REELLEMENT passe. La preuve.
--
-- La contrainte UNIQUE ci-dessous est le coeur du sujet. Elle est ici et pas
-- sur `actions` : sur actions, elle empecherait de PROPOSER deux fois la meme
-- chose. Ce qu'on veut empecher, c'est de l'EXECUTER deux fois. Double clic,
-- retry reseau, rechargement de page : la deuxieme tentative est refusee par
-- SQLite, pas par notre code.
CREATE TABLE IF NOT EXISTS executions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    action_id       INTEGER NOT NULL REFERENCES actions(id),
    cle_idempotence TEXT    NOT NULL UNIQUE,
    statut          TEXT    NOT NULL CHECK (statut IN ('SUCCES', 'ECHEC')),
    resultat        TEXT,                    -- JSON du retour de l'API appelee.
                                             -- Sert aussi a l'annulation : on y
                                             -- relit l'id de l'issue a fermer.
    erreur          TEXT,
    execute_le      TEXT    NOT NULL
);


-- 4. AUDIT_LOG : l'histoire complete, y compris ce qui n'est jamais parti.
-- Append-only : on n'efface jamais une ligne, on en ajoute une nouvelle.
-- C'est la seule table qui garde la trace des refus et des blocages.
CREATE TABLE IF NOT EXISTS audit_log (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    plan_id    INTEGER NOT NULL REFERENCES plans(id),
    action_id  INTEGER REFERENCES actions(id),
    evenement  TEXT    NOT NULL,             -- ACTION_REFUSEE, ACTION_EXECUTEE...
    acteur     TEXT    NOT NULL CHECK (acteur IN ('AGENT', 'HUMAIN')),
    details    TEXT,
    horodatage TEXT    NOT NULL
);


CREATE INDEX IF NOT EXISTS idx_actions_plan_id      ON actions(plan_id);
CREATE INDEX IF NOT EXISTS idx_executions_action_id ON executions(action_id);
CREATE INDEX IF NOT EXISTS idx_audit_plan_id        ON audit_log(plan_id);
CREATE INDEX IF NOT EXISTS idx_audit_action_id      ON audit_log(action_id);
