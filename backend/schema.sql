-- schema.sql — Pennyworth
-- 4 tables : plans -> actions -> audit_log -> rollbacks
-- Reflete la separation cerveau (planificateur) / bras (executeur) :
-- le planificateur n'ecrit que dans plans/actions, l'executeur n'ecrit
-- que dans audit_log/rollbacks.

PRAGMA foreign_keys = ON;

-- 1. PLANS : une intention utilisateur = un plan
CREATE TABLE IF NOT EXISTS plans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    intention TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'reviewed'))
);

-- 2. ACTIONS : chaque action proposee dans un plan
CREATE TABLE IF NOT EXISTS actions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    plan_id INTEGER NOT NULL REFERENCES plans(id),
    tool_name TEXT NOT NULL,
    parameters TEXT NOT NULL,              -- JSON des parametres de l'outil
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'approved', 'rejected', 'executed', 'failed')),
    idempotency_key TEXT UNIQUE NOT NULL,  -- sha256(plan_id + index + outil + args)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. AUDIT_LOG : trace de chaque execution reelle (append-only)
CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    action_id INTEGER NOT NULL REFERENCES actions(id),
    executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    result TEXT,                           -- detail du retour de l'API appelee
    success BOOLEAN NOT NULL,
    rollback_info TEXT                     -- ce qu'il faut pour annuler (ex: id issue)
);

-- 4. ROLLBACKS : trace des annulations effectuees (append-only)
CREATE TABLE IF NOT EXISTS rollbacks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    audit_log_id INTEGER NOT NULL REFERENCES audit_log(id),
    rolled_back_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    success BOOLEAN NOT NULL,
    detail TEXT
);

-- Index utiles
CREATE INDEX IF NOT EXISTS idx_actions_plan_id ON actions(plan_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_action_id ON audit_log(action_id);
CREATE INDEX IF NOT EXISTS idx_rollbacks_audit_log_id ON rollbacks(audit_log_id);