# REPARTITION.md

Qui fait quoi, palier par palier, fichier par fichier.

**Frontière :** les deux voies ne communiquent que par la table `actions`. Adam y écrit
des lignes `PROPOSEE`, Souf lit les lignes `APPROUVEE`. C'est la même frontière que celle
qui protège le produit, ce n'est pas un hasard.

**Règle d'or :** on se répartit l'écriture, jamais la compréhension. Le formateur ouvre un
fichier au hasard et désigne l'un de vous deux.

---

## Arborescence, pour que personne ne se marche dessus

```
src/
  shared/            <- ECRIT A DEUX au palier 2, gelé ensuite
    schema.sql
    models.py        <- modèles Pydantic des outils et des actions
    states.py        <- la machine à états
  planner/           <- ADAM seul
    planner.py
    prompts.py
    stream.py
  executor/          <- SOUF seul
    executor.py
    idempotency.py
    compensate.py
    handlers/        <- UN FICHIER PAR OUTIL
      create_github_issue.py
      send_message.py
      generate_file.py
      create_calendar_event.py
      create_employee_record.py
  db.py              <- SOUF
  audit.py           <- SOUF
  server/
    main.py          <- GELE après le palier 2, toutes les routes câblées d'avance
    routes_plans.py  <- ADAM
    routes_actions.py<- SOUF
web/
  index.html         <- ADAM   (écran 1, l'intention)
  plan.html          <- ADAM   (écran 2, le plan)
  journal.html       <- SOUF   (écran 3, le journal)
  style.css          <- A DEUX au palier 2, gelé ensuite
```

Un fichier par handler d'outil : c'est la différence entre "on ajoute chacun un outil sans
se croiser" et "on se marche dessus dans un bloc de 200 lignes".

---

## PALIER 2, SOCLE (J1 après-midi)

### D'abord ensemble, 1 heure, sur `main`

Personne ne branche avant que ce soit fusionné.

1. `schema.sql` : les 4 tables, avec `depends_on`, `origine`, `idempotency_key`
2. `models.py` : les modèles Pydantic des 5 outils et de l'action
3. `states.py` : PROPOSEE, APPROUVEE, REFUSEE, BLOQUEE, EXECUTEE, ECHOUEE, COMPENSEE
4. La liste des routes, écrite noir sur blanc
5. **Tous les fichiers créés vides avec leur stub, et toutes les routes déjà câblées dans
   `server/main.py`.** Après ça, plus personne ne touche à `main.py`, donc plus jamais de
   conflit sur le fichier le plus chaud du projet.
6. `style.css` : les couleurs, la typo, les classes de base

### Ensuite, Adam (branche `dev_adam`)

| # | Tâche | Fichier |
|---|---|---|
| 1 | Écran 1 : le champ unique centré, envoi vers l'API | `web/index.html` |
| 2 | Écran 2 : la liste des actions, cases **décochées**, badges réversibilité et origine | `web/plan.html` |
| 3 | `POST /plans` qui crée un plan avec **3 actions écrites en dur dans le code** | `routes_plans.py` |
| 4 | `GET /plans/{id}` qui renvoie le plan et ses actions | `routes_plans.py` |
| 5 | **Déploiement en ligne le soir même** (carte bonus "déployé tôt") | VPS |

Aucune IA au palier 2. Tu poses la place où le planificateur viendra s'asseoir au palier 3.

### Ensuite, Souf (branche `dev_souf`)

| # | Tâche | Fichier |
|---|---|---|
| 1 | Création de la base et des 4 tables, fonctions de lecture et d'écriture | `db.py` |
| 2 | `PATCH /actions/{id}` : passage en APPROUVEE ou REFUSEE | `routes_actions.py` |
| 3 | `POST /plans/{id}/execute` : lance l'exécuteur | `routes_actions.py` |
| 4 | L'exécuteur : lit **uniquement** `etat = APPROUVEE`, relu en base, jamais reçu en paramètre | `executor.py` |
| 5 | Un seul handler, le plus simple : écrire un fichier texte | `handlers/generate_file.py` |
| 6 | Le journal append-only, une ligne par événement | `audit.py` |
| 7 | Écran 3 : affichage du journal | `web/journal.html` |

### Fin de journée, ensemble

- Fusion sur `dev`, puis sur `main`
- Relecture croisée de 15 minutes : chacun explique le code de **l'autre**
- Chacun écrit son entrée dans `JOURNAL.md`
- Cocher le palier 2 dans `CHECKPOINTS.md`

---

## PALIER 3, LE PREMIER OUTIL (J2 matin)

### Adam, le cerveau arrive

| # | Tâche | Fichier |
|---|---|---|
| 1 | La boucle agentique : appel au modèle, exécution des outils de lecture, on reboucle | `planner.py` |
| 2 | Le prompt système, avec le contenu utilisateur délimité explicitement | `prompts.py` |
| 3 | Sortie structurée : le plan sort dans un format strict, validé contre le modèle Pydantic. **Un plan invalide est rejeté et replanifié, jamais rattrapé à la main** | `planner.py` |
| 4 | Les 4 outils de lecture, plus `propose_action` | `planner.py` |
| 5 | Flux SSE : les lignes du plan apparaissent une par une (carte bonus "streaming") | `stream.py` |
| 6 | L'écran 2 consomme le flux et affiche au fil de l'eau | `web/plan.html` |
| 7 | `POST /plans` branché sur le vrai planificateur, plus de plan en dur | `routes_plans.py` |

**Garde-fous à mettre dès le premier jet :** nombre maximal de tours de boucle, nombre
maximal d'actions par plan.

### Souf, les vrais outils

| # | Tâche | Fichier |
|---|---|---|
| 1 | GitHub réel : création d'issue via l'API, avec le token à portée minimale | `handlers/create_github_issue.py` |
| 2 | Messagerie locale : écrit un `.eml` dans `outbox/` | `handlers/send_message.py` |
| 3 | Calendrier : génère un `.ics` dans `artifacts/` | `handlers/create_calendar_event.py` |
| 4 | Fiche employé en base | `handlers/create_employee_record.py` |
| 5 | **L'idempotence** : clé `sha256(plan_id + index + outil + args normalisés)`, contrainte UNIQUE, rejeu qui renvoie le résultat mémorisé | `idempotency.py` |
| 6 | Le journal affiche l'URL réelle de l'issue GitHub, cliquable | `web/journal.html` |

### Ensemble

Fusion, relecture croisée, entrées de journal.

---

## PALIER 4, LA BOUCLE FERMÉE, MVP (J2 après-midi)

**Le seul palier obligatoire. On ne commence rien de neuf, on finit.**

### Adam

| # | Tâche | Fichier |
|---|---|---|
| 1 | La barre d'ajout : on relance le **même** planificateur avec le plan courant en contexte | `planner.py`, `web/plan.html` |
| 2 | Les lignes ajoutées arrivent en PROPOSEE, décochées, marquées `origine = HUMAIN` | `planner.py` |
| 3 | Le coût du plan calculé à partir de l'usage renvoyé par le modèle | `planner.py` |

### Souf

| # | Tâche | Fichier |
|---|---|---|
| 1 | Les dépendances : refuser une action bascule ses enfants en BLOQUEE avec le motif | `routes_actions.py`, `web/plan.html` |
| 2 | Exécution séquentielle, dans l'ordre, avec l'état qui remonte en direct | `executor.py` |
| 3 | Le journal complet : horodatage, origine, coût, refus affichés | `audit.py`, `web/journal.html` |

### Ensemble, la dernière heure

- Rejouer le happy path des 6 étapes **deux fois d'affilée**
- Le tester avec des intentions que vous n'avez jamais écrites vous-mêmes
- Si à 15h il manque quelque chose : **couper du périmètre, pas de la qualité.** Un plan à
  3 actions qui marche vaut mieux qu'un plan à 7 actions qui plante.

---

## PALIER 5, DURCISSEMENT (J3 matin)

### Adam

| # | Tâche |
|---|---|
| 1 | Harnais d'éval : 8 à 10 intentions, vérification automatique des actions attendues (carte bonus "éval automatisée") |
| 2 | `AGENTS.md` complété : prompts système, traces, schéma de la boucle |
| 3 | Le coût et la latence affichés dans l'interface (carte bonus "coût affiché") |

### Souf

| # | Tâche |
|---|---|
| 1 | L'annulation avec compensation, et le cas irréversible géré proprement |
| 2 | `README.md` complet |
| 3 | **Quickstart chronométré pour de vrai**, dans un dossier vide, sur une machine propre |
| 4 | Section "limites connues" à jour (carte bonus "zéro dette expliquée") |

---

## PALIER 6, LIVRAISON (J3 13h00 à 15h30)

**Plus une ligne de code. Les deux, ensemble.**

1. `git log -p | grep -iE "sk-ant|api[_-]?key|token"` ne remonte rien
2. `JOURNAL.md` : 5 entrées minimum, relues
3. Tag `v1.0`
4. Démo écrite mot à mot : 4 min de nominal, 1 min de cas d'échec
5. Cas d'échec choisi : le refus qui bloque une dépendance
6. Trois répétitions chronométrées, en alternant qui parle

---

## Le rituel, avant chaque checkpoint

Quinze minutes, tous les deux devant le même écran :

1. Tout est fusionné sur `dev`, puis sur `main`
2. **Chacun explique le code de l'autre à voix haute**, pas le sien
3. Ce qui ne s'explique pas est supprimé ou simplifié sur place

C'est une répétition du checkpoint, avec le même exercice.

## Présentateurs

| Palier | 1 | 2 | 3 | 4 | 5 | 6 |
|---|---|---|---|---|---|---|
| Qui parle | Adam | Souf | Adam | Souf | Adam | Souf |
