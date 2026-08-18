# Pennyworth

> Un majordome numerique. Il prepare tout, il pose le plateau, et il ne sort jamais la
> Batmobile sans qu'on le lui demande.

Pennyworth transforme une intention en langage naturel ("prepare l'arrivee de Jean,
stagiaire dev") en un plan d'actions concretes. **Rien ne s'execute sans validation
humaine, action par action.**

Hackathon Full Stack Agentique, Holberton School. Sujet 03, LE BRAS.
Binome : [Adam](https://github.com/Adamzou-lab) et [Souf](https://github.com/Souf-F).

**Etat : palier 2 (socle). Le tuyau est ouvert : une intention entre, Claude repond, ca s'affiche.**

---

## Quickstart

Python 3.9 ou plus. Aucun autre prerequis : pas de base a installer, pas de Docker.

```bash
git clone https://github.com/Souf-F/holberton-hackathonagentic.git
cd holberton-hackathonagentic
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # puis renseigner ANTHROPIC_API_KEY
uvicorn src.main:app --reload
```

Puis ouvrir **http://127.0.0.1:8000**

La base SQLite et ses quatre tables sont creees automatiquement au premier
demarrage, dans `data/pennyworth.db`.

### Ou sont les cles d'API

Dans le fichier `.env`, **cote serveur uniquement**. Le navigateur ne parle qu'a
notre propre API : il n'appelle jamais Anthropic, et la cle ne quitte jamais la
machine qui fait tourner le serveur. Le seul fichier du projet qui touche a
Claude est `src/planner.py`.

### Structure

```
src/main.py      le serveur : routes de l'API, sert aussi le front
src/planner.py   le cerveau : le seul fichier qui appelle Claude
src/db.py        acces SQLite, SQL brut, pas d'ORM
schema.sql       les 4 tables
web/             le front : une page, pas de framework
```

## Architecture en une phrase

Le cerveau et le bras ne se parlent jamais directement. Ils communiquent par la base de
donnees, et l'humain est entre les deux.

```
intention  ->  PLANIFICATEUR (LLM + outils lecture seule)  ->  plan en base
                                                                    |
                                                          validation humaine
                                                                    |
                                                                    v
                              journal  <-  EXECUTEUR (aucun acces au LLM)
```

Le planificateur n'a **aucune** fonction a effet de bord dans la liste d'outils qu'on lui
passe. Son seul moyen d'agir sur le monde est d'ecrire une ligne de plan. L'executeur ne
lit que les lignes marquees approuvees, qu'il relit lui-meme en base.

Schema detaille, cycle de vie d'une action et signatures d'outils : voir [SPEC.md](./SPEC.md).

---

## Choix techniques

| Couche | Choix |
|---|---|
| Langage | Python 3.9+ |
| Validation | Pydantic |
| Back | FastAPI, flux SSE |
| Base | SQLite |
| Front | HTML et JS vanilla |
| Modele | Claude |

Le raisonnement complet, et surtout **ce que nous avons ecarte et pourquoi**, sont dans la
section "Choix techniques, et ce que nous avons ecarte" de [SPEC.md](./SPEC.md).

---

## Limites connues

A tenir a jour en continu, pas a remplir la veille du rendu. Une dette nommee n'est plus
une dette cachee.

- Une seule integration externe reelle : GitHub. La messagerie ecrit un fichier `.eml`
  dans `outbox/`, le calendrier genere un `.ics` dans `artifacts/`. Choix assume et
  documente : les signatures sont celles d'un vrai service, seul le transport change.
- `send_message` est irreversible. Aucune compensation possible, l'interface l'affiche
  avant l'approbation.
- Operateur unique, pas de gestion de roles.
- Pas d'annulation en cascade apres execution.

Liste complete des exclusions : section "Hors scope" de [SPEC.md](./SPEC.md).

---

## Conventions de travail

### Branches

| Branche | Role |
|---|---|
| `main` | Etat presentable. On y fusionne `dev` **avant chaque checkpoint**. |
| `dev` | Integration continue au fil de la journee. |
| `dev_adam` / `dev_souf` | Travail personnel. Une branche par tache, duree de vie maximale une demi-journee. |

### Commits

Convention Conventional Commits : `feat:`, `fix:`, `docs:`, `chore:`, `refactor:`, `test:`.
Un scope quand c'est utile, pour que `git log` raconte la progression :
`feat(executor): idempotence par cle unique`.

**Ne jamais commiter les marqueurs de conflit.** Un fichier contenant `<<<<<<<` ou
`>>>>>>>` est un fichier casse. On resout, on relit, puis on commite.

Avant chaque push : `git pull --rebase origin dev`. Pas de rebase interactif, pas de force push.

### Rituel des 15 minutes

Quinze minutes avant chaque checkpoint :

1. Tout est fusionne sur `dev`, puis sur `main`.
2. **Chacun explique le code de l'autre a voix haute**, pas le sien.
3. Ce qui ne s'explique pas est supprime ou simplifie sur place.

C'est une repetition du checkpoint, avec le meme exercice.

### Regle sur les conflits

On ne resout jamais un conflit dans du code qu'on ne comprend pas. Celui qui fusionne en
second appelle l'autre s'il ne sait pas quelle version garder.

### Dependances

Toutes les dependances sont decidees ensemble. Une seule personne les ajoute, et elle le
dit avant, pour eviter les conflits sur le fichier de dependances.

---

## Livrables

| Livrable | Etat |
|---|---|
| `SPEC.md` | fait, palier 1 |
| `README.md` | en cours |
| `AGENTS.md` | squelette, a remplir au palier 3 |
| `JOURNAL.md` | en cours, une entree par palier |
| `.env.example` | fait |
| `.gitignore` | fait |
| Tag `v1.0` | palier 6 |
| Demo scriptee 5 min | palier 6 |
