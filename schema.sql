-- Pennyworth : schema de la base.
-- Quatre tables. Palier 2 : seule `plans` est reellement utilisee.
-- Les trois autres sont creees maintenant pour ne pas y revenir demain.

-- Ce que l'utilisateur a demande. Une ligne par intention saisie.
CREATE TABLE IF NOT EXISTS plans (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    intention     TEXT    NOT NULL,
    etat          TEXT    NOT NULL DEFAULT 'PLANIFICATION',
    reponse       TEXT,
    cout_eur      REAL    DEFAULT 0,
    tokens_entree INTEGER DEFAULT 0,
    tokens_sortie INTEGER DEFAULT 0,
    cree_le       TEXT    NOT NULL
);

-- Les lignes du plan. Ce qu'on VEUT faire. Rien n'est execute a ce stade.
CREATE TABLE IF NOT EXISTS actions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    plan_id         INTEGER NOT NULL REFERENCES plans(id),
    position        INTEGER NOT NULL,
    outil           TEXT    NOT NULL,
    arguments       TEXT    NOT NULL,
    raison          TEXT,
    reversible      INTEGER NOT NULL DEFAULT 1,
    depends_on      INTEGER REFERENCES actions(id),
    origine         TEXT    NOT NULL DEFAULT 'AGENT',
    etat            TEXT    NOT NULL DEFAULT 'PROPOSEE',
    cle_idempotence TEXT    NOT NULL,
    cree_le         TEXT    NOT NULL
);

-- Ce qui s'est REELLEMENT passe. La contrainte UNIQUE ci-dessous est
-- ce qui rend le doublon impossible : c'est SQLite qui refuse, pas notre code.
CREATE TABLE IF NOT EXISTS executions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    action_id       INTEGER NOT NULL REFERENCES actions(id),
    cle_idempotence TEXT    NOT NULL UNIQUE,
    statut          TEXT    NOT NULL,
    resultat        TEXT,
    erreur          TEXT,
    execute_le      TEXT    NOT NULL
);

-- L'histoire complete, y compris ce qui n'est jamais parti.
-- On n'efface jamais une ligne, on en ajoute une nouvelle.
CREATE TABLE IF NOT EXISTS audit_log (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    plan_id    INTEGER NOT NULL REFERENCES plans(id),
    action_id  INTEGER REFERENCES actions(id),
    evenement  TEXT    NOT NULL,
    acteur     TEXT    NOT NULL,
    details    TEXT,
    horodatage TEXT    NOT NULL
);
