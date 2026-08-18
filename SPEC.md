# SPEC.md, Pennyworth : assistant d'onboarding agentique

> **Pennyworth**, comme Alfred Pennyworth. Il prépare tout, il pose le plateau,
> et il ne sort jamais la Batmobile sans qu'on le lui demande.
> L'agent construit le plan complet. Rien ne s'exécute sans validation humaine,
> action par action.

---

## Le problème (5 lignes)

L'onboarding d'un nouveau collaborateur repose sur une checklist manuelle répétitive :
créer un compte, assigner des tâches, envoyer des messages de bienvenue, poser des
événements calendrier. Ces tâches sont souvent oubliées, mal séquencées, ou effectuées
sans trace de qui a fait quoi. Pennyworth transforme une intention exprimée en langage
naturel ("prépare l'arrivée de Jean, stagiaire dev") en un plan d'actions concrètes,
validées une par une par un humain avant toute exécution réelle.

---

## User stories (3 maximum)

1. **En tant que** responsable RH, **je veux** décrire l'arrivée d'un collaborateur en
   langage naturel, **afin d'**obtenir automatiquement une liste d'actions d'onboarding
   pertinentes, sans avoir à retenir la checklist par cœur.

2. **En tant que** responsable RH, **je veux** approuver ou refuser chaque action
   individuellement avant qu'elle ne s'exécute, **afin de** garder le contrôle sur ce que
   l'agent fait réellement, et de voir immédiatement l'impact d'un refus sur les actions
   qui en dépendaient.

3. **En tant que** responsable RH, **je veux** consulter un journal des actions exécutées
   et pouvoir en annuler une, **afin de** corriger une erreur sans tout recommencer
   manuellement.

---

## Hors scope

1. Pas de gestion RH complète (paie, contrat, congés, dossier administratif).
2. Pas de multi-langue : l'interface et les prompts sont en français uniquement.
3. Pas d'authentification multi-utilisateur avec rôles et permissions (un seul profil
   opérateur pour la démo). Le journal d'audit suppose un opérateur unique, ce qui rend
   l'attribution des approbations triviale.
4. Pas d'annulation en cascade : annuler une action exécutée ne réannule pas
   automatiquement les actions qui en dépendaient.
5. Pas de planification d'actions différées dans le temps (tout s'exécute immédiatement
   après approbation, pas de "envoyer ce message dans 3 jours").
6. Pas de re-planification automatique après un refus. L'agent ne propose pas de plan B
   tout seul : bonus possible au palier 5, pas dans le MVP.
7. Pas de gestion des conflits si deux utilisateurs modifient le même plan en parallèle.
8. Pas de rollback transactionnel. Nous faisons de la compensation explicite, action par
   action, parce qu'un message envoyé n'est pas annulable. Nous documentons les actions
   irréversibles au lieu de prétendre les annuler.
9. **[NOTRE LIGNE POUR LA CARTE "LE NON ARGUMENTÉ"]** Pas de liste blanche
   d'auto-approbation, même pour les actions jugées sans risque. Toute exception au
   principe de validation humaine est une porte que plus personne ne referme, et c'est
   par là que ce type de système meurt en production. Le coût d'un clic de trop est
   faible, le coût d'une exception est structurel.
10. Une seule intégration externe réelle (GitHub). La messagerie et le calendrier sont
    des implémentations locales assumées, décrites en détail plus bas. Nous préférons
    prouver la chaîne complète sur une vraie API plutôt que dépenser trois heures en
    parcours OAuth qui ne sont notés nulle part.

---

## Choix techniques, et ce que nous avons écarté

**Le besoin qui commande tout :** notre plan est produit par un modèle, donc c'est une
entrée non fiable. Il nous faut une déclaration unique par outil qui serve à la fois de
signature typée, de schéma envoyé au modèle, et de validateur à l'exécution.

| Couche | Choix | Pourquoi |
|---|---|---|
| Langage | Python | Maîtrisé par les deux membres. Contrainte réelle du hackathon : l'oral du code impose que chacun explique n'importe quelle ligne sans préparation. |
| Validation | Pydantic | Une seule déclaration donne la signature, le JSON Schema envoyé au modèle, et la validation des arguments avant exécution. |
| Back | FastAPI | Flux SSE natif pour l'affichage du plan en direct. |
| Base | SQLite | Contrainte d'unicité et transactions suffisantes. Aucun service à lancer, le quickstart tient en deux commandes. |
| Front | HTML et JS vanilla | Deux écrans seulement. Aucun bundler à expliquer au checkpoint. |
| Temps réel | SSE | Le flux est unidirectionnel, serveur vers navigateur. |

**Écartés, et pourquoi :**

- **Les frameworks d'agents (LangChain, CrewAI, l'Agent SDK).** Leurs abstractions sont
  construites autour d'une boucle qui exécute les outils. Notre sujet consiste
  précisément à sortir l'exécution de la boucle. Nous passerions le hackathon à
  contourner le framework pour l'empêcher de faire ce pour quoi il existe. Notre boucle
  fait une trentaine de lignes et s'explique ligne par ligne.
- **Les helpers d'exécution automatique du SDK, pour les outils d'écriture.** Même
  raison, en plus direct : ils appellent nos fonctions automatiquement, ce qui est
  exactement le comportement éliminatoire de ce sujet.
- **PostgreSQL.** Le multi-utilisateur qui le justifierait est déjà hors scope.
- **Docker.** Un seul service et une base fichier, donc rien à orchestrer. Le besoin réel
  était la reproductibilité, couvert par une version de Python fixée et un script de
  setup unique. À reconsidérer au palier 5 seulement si le quickstart mesuré sur machine
  propre dépasse 5 minutes.
- **WebSocket.** Le flux est unidirectionnel, SSE suffit et évite la gestion de
  reconnexion.
- **Un ORM.** La partie critique est une contrainte d'unicité sur la clé d'idempotence et
  une machine à états. Les deux se lisent mieux en SQL brut, et s'expliquent mieux à
  l'oral.

---

## Architecture

Le principe : **le cerveau et le bras ne se parlent jamais directement.** Ils
communiquent par la base de données, et l'humain est entre les deux.

```
   [Utilisateur]
        │ intention en langage naturel
        ▼
   [Front : index.html]  ──POST /plans──►  [API : main.py]
                                                │
                                                ▼
                              ┌──────────────────────────────────┐
                              │  PLANIFICATEUR (agent.py)        │
                              │  boucle agentique + LLM          │
                              │                                  │
                              │  outils disponibles :            │
                              │   - lecture seule                │
                              │   - propose_action()             │
                              │                                  │
                              │  AUCUN outil à effet de bord     │
                              └────────────────┬─────────────────┘
                                               │ écrit des lignes
                                               │ état = PROPOSEE
                                               ▼
                                    ╔═══════════════════════╗
                                    ║   SQLite              ║
                                    ║   plans / actions     ║
                                    ║   executions / audit  ║
                                    ╚═══════════╤═══════════╝
                                                │
        [Front : plan.html]  ◄──SSE─────────────┤
             │ l'humain coche                   │
             └──PATCH /actions/{id}─────────────┤
                    état = APPROUVEE            │
                                                ▼
                              ┌──────────────────────────────────┐
                              │  EXECUTEUR (executor.py)         │
                              │  aucun accès au LLM              │
                              │  lit UNIQUEMENT etat=APPROUVEE   │
                              │  clé d'idempotence obligatoire   │
                              └────────────────┬─────────────────┘
                                               ▼
                              [tools.py] ──► API GitHub réelle
                                         ──► outbox/ (messagerie locale)
                                         ──► artifacts/ (fichiers, .ics)
                                               │
                                               ▼
                                    [audit.py] ──► journal append-only
                                               │
                                               ▼
                                    [Front : journal.html]
```

**Les trois propriétés que nous défendons au checkpoint :**

1. Le modèle n'a jamais les fonctions d'écriture dans la liste d'outils qu'on lui passe.
   Il ne peut pas les appeler, même en cas d'injection de prompt. Son seul moyen d'agir
   est `propose_action`, qui écrit une ligne de plan.
2. L'exécuteur ne reçoit pas d'action en paramètre depuis l'appelant : il va la relire en
   base par son identifiant, avec un filtre sur `etat = APPROUVEE`. On ne peut pas lui
   faire exécuter une action non approuvée, même par erreur de code.
3. La transition `PROPOSEE` vers `APPROUVEE` n'est écrite que par une route déclenchée
   par l'humain. Aucun code agent ne l'écrit.

---

## Les outils

### Ce que l'agent peut appeler

Ce sont les seuls outils présents dans la liste envoyée au modèle.

| Outil | Signature | Effet de bord |
|---|---|---|
| `get_employee_info` | `(name: str) -> Employee \| None` | Non |
| `list_team_members` | `(team: str) -> list[Employee]` | Non |
| `read_calendar` | `(user_id: str, start: str, end: str) -> list[Event]` | Non |
| `get_onboarding_template` | `(role: str) -> Template` | Non |
| `propose_action` | `(tool: str, args: dict, reason: str, depends_on: int \| None) -> ActionId` | Non, écrit une ligne de plan |

### Ce que seul l'exécuteur peut faire, après validation humaine

Ces fonctions ne sont jamais exposées au modèle.

| Action | Signature | Effet de bord | Réversible | Compensation |
|---|---|---|---|---|
| `create_github_issue` | `(repo: str, title: str, body: str) -> Issue` | Oui, API réelle | Oui | fermer l'issue |
| `create_employee_record` | `(payload: EmployeePayload) -> RecordId` | Oui, base locale | Oui | supprimer la fiche |
| `generate_file` | `(template: str, vars: dict) -> Path` | Oui, disque | Oui | supprimer le fichier |
| `create_calendar_event` | `(title: str, start: str, end: str, attendees: list[str]) -> EventId` | Oui, fichier .ics | Oui | supprimer l'événement |
| `send_message` | `(channel: str, text: str) -> MessageId` | Oui | **Non** | **aucune, un message parti est parti** |

`send_message` est le seul outil irréversible, et c'est volontaire : il nous sert à
démontrer que l'interface affiche l'irréversibilité **avant** l'approbation, pas après.

**Implémentations assumées.** `create_github_issue` appelle la vraie API GitHub et crée
une issue réellement visible. `send_message` écrit un fichier `.eml` dans `outbox/`.
`create_calendar_event` génère un fichier `.ics` dans `artifacts/`. Dans les deux cas la
signature est celle d'un vrai service, seule l'implémentation du transport change, et le
remplacement par un vrai connecteur ne toucherait pas au reste du système.

L'annulation n'est **pas** un outil de l'agent. C'est une route de l'API
(`POST /actions/{id}/compensate`), déclenchée par l'humain depuis le journal.

---

## Cycle de vie d'une action

```
                        refus humain
      ┌──────────────────────────────────────► REFUSEE
      │
   PROPOSEE ──── approbation humaine ────► APPROUVEE ──► EXECUTEE ──► COMPENSEE
      │                                                      │
      │  le parent a été refusé                              └──► ECHOUEE
      └──────────────────────────────────► BLOQUEE
```

Chaque action porte un champ `depends_on`. Refuser une action bascule automatiquement ses
enfants en `BLOQUEE`, avec le motif affiché à l'écran. C'est le comportement que nous
montrons en démo.

---

## Sécurité

- **Moindre privilège** : le token GitHub est limité à la création d'issues sur un dépôt
  précis. Aucun droit de suppression, aucun accès aux autres dépôts.
- **La validation humaine est un contrôle de sécurité**, pas un confort d'interface. Elle
  est appliquée par la structure du code : l'agent n'a pas les fonctions d'écriture.
- **Injection de prompt** : le contenu fourni par l'utilisateur (nom, poste, notes) est
  délimité explicitement dans le prompt système. Et même si une injection réussissait, le
  pire que l'agent puisse faire est de proposer une mauvaise action, qu'un humain verra
  avant qu'elle parte. La séparation cerveau/bras est notre défense de fond.
- **Idempotence** : chaque action reçoit une clé calculée à la planification à partir de
  son contenu (`sha256(plan_id + index + outil + arguments normalisés)`), avec une
  contrainte d'unicité en base. Rejouer une action déjà exécutée renvoie le résultat
  mémorisé au lieu de la refaire. Cas couverts : double clic, retry réseau, rechargement
  de page.
- **Audit** : le journal est append-only. Chaque entrée est horodatée et attribuée, y
  compris les refus et les annulations. Aucune ligne n'est jamais supprimée.
- **Secrets** : aucune clé en clair dans le code, `.env` jamais commité, `.env.example`
  fourni comme référence, vérification de l'historique git avant le tag v1.0.

---

## Happy path de la démo finale (6 étapes)

1. J'ouvre Pennyworth et je saisis : *"Prépare l'arrivée de Jean, stagiaire développeur,
   qui commence lundi."*

2. Le plan se construit en direct à l'écran. L'agent consulte d'abord l'équipe et le
   calendrier du tuteur, puis propose 5 actions numérotées, chacune avec l'outil concerné,
   ses arguments, et la raison invoquée.

3. Chaque ligne affiche son effet de bord et sa réversibilité. L'envoi du message de
   bienvenue est marqué **non annulable** en rouge, avant tout clic.

4. J'approuve les actions 1, 2 et 5. Je refuse l'action 3 (le message de bienvenue).
   L'action 4, qui envoyait ses identifiants et dépendait de la 3, bascule
   automatiquement en **bloquée**, avec le motif affiché.

5. Je lance l'exécution. Les trois actions approuvées partent l'une après l'autre.
   L'issue GitHub apparaît réellement, avec son URL cliquable. Le journal se remplit en
   direct, horodaté, avec le coût du plan affiché. Je clique une deuxième fois sur
   "exécuter" : rien ne part en double, la clé d'idempotence a fait son travail.

6. Depuis le journal, j'annule l'action 2. La compensation s'exécute, l'issue GitHub se
   ferme réellement, et le journal enregistre l'annulation **sans effacer** l'entrée
   d'origine.

**Cas d'échec de la minute 5 de la démo :** le refus de l'action 3 qui bloque l'action 4.
Ce n'est pas un bug, c'est notre garde-fou qui fonctionne.

---

## Partage du travail

| | Adam | Souf |
|---|---|---|
| **Domaine** | Le cerveau | Le bras |
| Back | `agent.py`, prompts, boucle agentique, sorties structurées, flux SSE | `db.py`, `executor.py`, `tools.py`, idempotence, compensation, `audit.py` |
| Front | écran de saisie, écran du plan, approbation | écran du journal, annulation, affichage du coût |
| Docs | `AGENTS.md` | `README.md` |
| Palier 5 | harnais d'éval | déploiement |

**Écrit ensemble, sur `main`, avant toute branche :** le schéma de base, les modèles
Pydantic des outils, le contrat des routes de l'API.

**Frontière :** les deux voies ne communiquent que par la table `actions`. Adam y écrit
des lignes `PROPOSEE`, Souf lit les lignes `APPROUVEE`. C'est la même frontière que celle
qui protège le produit, ce qui n'est pas un hasard.

**Présentateurs :** Adam aux paliers 1, 3 et 5. Souf aux paliers 2, 4 et 6.

**Rituel :** 15 minutes avant chaque checkpoint, tout est fusionné sur `main` et chacun
explique le code de l'autre à voix haute. Ce qui ne s'explique pas est supprimé ou
simplifié sur place.

---

## Checklist du palier 1

- [x] Problème en 5 lignes
- [x] 3 user stories maximum
- [x] Hors scope, au moins 5 items (nous en avons 10)
- [x] Une ligne désignée pour la carte "LE NON ARGUMENTÉ" (item 9)
- [x] Schéma d'architecture : front, back, agent, outils, stockage
- [x] Liste des outils avec signature typée et effet de bord
- [x] Happy path de la démo en 6 étapes numérotées
- [x] Partage du travail écrit
- [ ] `.gitignore` et `.env.example` commités sur `main`
