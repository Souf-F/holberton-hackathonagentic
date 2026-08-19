# Pennyworth

> Un majordome numerique. Il prepare tout, il pose le plateau, et il ne sort jamais la
> Batmobile sans qu'on le lui demande.

Pennyworth transforme une intention en langage naturel ("prepare l'arrivee de Jean,
stagiaire dev") en un plan d'actions concretes. **Rien ne s'execute sans validation
humaine, action par action.**

Hackathon Full Stack Agentique, Holberton School. Sujet 03, LE BRAS.
Binome : [Adam](https://github.com/Adamzou-lab) et [Souf](https://github.com/Souf-F).

**Etat : paliers 1 a 5 termines (socle, premier outil, MVP, durcissement). Palier 6
(livraison) en cours : documentation finale, tag `v1.0`, demo scriptee.**

**En ligne : https://pennyworth.adamzou.fr**

> Heberge sur Render, plan gratuit. Le service se met en veille apres 15 minutes
> sans visite : la premiere requete peut prendre 30 a 50 secondes, le temps du
> reveil. Les suivantes sont immediates.

---

## Sommaire

- [Quickstart](#quickstart)
- [Architecture en une phrase](#architecture-en-une-phrase)
- [Choix techniques](#choix-techniques)
- [Securite](#securite)
- [Limites connues](#limites-connues)
- [Conventions de travail](#conventions-de-travail)
- [Livrables](#livrables)

---

## Quickstart

Python 3.9 ou plus. Aucun autre prerequis : pas de base a installer, pas de Docker.

```bash
git clone https://github.com/Souf-F/holberton-hackathonagentic.git
cd holberton-hackathonagentic
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

**Ouvrir `.env` et coller votre cle Anthropic** apres `ANTHROPIC_API_KEY=`

`GITHUB_TOKEN` est optionnel : sans lui, tout le reste fonctionne, seule
la creation reelle d'issue GitHub echoue proprement (erreur structuree,
pas de crash). A portee minimale : creation d'issues sur `GITHUB_REPO`
uniquement, aucun autre droit.

```bash
./lancer.sh
```

Puis ouvrir **http://127.0.0.1:8000**

`lancer.sh` limite la surveillance du rechargement automatique a `src/` et
`web/`. Sans ca, uvicorn observe aussi `.venv/`, qui contient des milliers de
fichiers installes par pip : demarrage plus lent, parfois des redemarrages en
boucle. Une seule commande a retenir, la meme pour tout le monde.

La base SQLite et ses quatre tables sont creees automatiquement au premier
demarrage, dans `data/pennyworth.db`.

### Ou sont les cles d'API

Dans le fichier `.env`, **cote serveur uniquement**. Le navigateur ne parle qu'a
notre propre API (`fetch` vers nos routes `/api/...`) : il n'appelle jamais
Anthropic ni GitHub directement, et aucune cle ne quitte jamais la machine qui
fait tourner le serveur. Verifiable en un coup d'oeil : aucun fichier sous
`web/` ne contient `ANTHROPIC_API_KEY` ni `GITHUB_TOKEN`. Le seul fichier qui
lit la cle Anthropic est `src/planner.py`, le seul qui lit le token GitHub est
`src/executeur/handlers/create_github_issue.py`.

### Structure

```
src/main.py               le serveur : routes de l'API, sert aussi le front
src/planner.py            le cerveau : le seul fichier qui appelle Claude
src/db.py                 acces SQLite, SQL brut, pas d'ORM
src/executeur/            le bras : execute les actions APPROUVEES, jamais autre chose
src/executeur/handlers/   un fichier par outil a effet de bord reel
schema.sql                les 4 tables
web/                      le front : deux pages, pas de framework
tests/                    tests autonomes, sans pytest (python3 tests/xxx.py)
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
| Modele | Claude (`ANTHROPIC_MODEL` dans `.env`) |

**Convention sur le modele, adoptee pendant le durcissement :** Sonnet pour toutes les
phases de test et d'iteration (moins cher), Opus reserve a la version officielle
(checkpoint, demo). Toujours rejouer `make eval` sur Opus juste avant un checkpoint reel
: un score obtenu sur Sonnet ne garantit pas le meme resultat sur Opus. Verifie une fois
en pratique : les deux ont pourtant echoue de la meme facon, a cause d'un defaut du
script d'eval, pas du modele. La prudence reste justifiee quand meme.

Le raisonnement complet, et surtout **ce que nous avons ecarte et pourquoi**, sont dans la
section "Choix techniques, et ce que nous avons ecarte" de [SPEC.md](./SPEC.md).

---

## Securite

Cette section couvre les points demandes pour le palier 5. Le detail complet de
toute la revue de securite (27 ajouts au total, au-dela de cette liste : scan
externe verifie, autorisation, rate limiting, en-tetes, course concurrente sur
la compensation...) est dans [SECURITE.md](./SECURITE.md).

### Injection de prompt

**La question du checkpoint palier 5** ("que se passe-t-il si l'utilisateur ecrit
*ignore tes instructions precedentes* dans le champ ?") est reproduite mot pour mot
dans `eval/cases.py` (cas 6, voir `eval/cases.md`). C'est le cas a rejouer devant le
formateur, pas le easter egg sandwich ci-dessous (qui est un declencheur qu'on a
nous-memes ecrit dans le prompt, benin et controle, pas une tentative adversariale).

Ce que ce cas verifie, et pourquoi c'est la bonne question : pas "Claude a-t-il
resiste au texte" (rien ne le garantit, le modele reste libre de reagir n'importe
comment), mais la garantie **structurelle** du produit, qui tient quoi que Claude
fasse. `propose_action` ne peut jamais ecrire autre chose qu'une ligne `PROPOSEE` en
base, et le modele **n'a jamais** dans sa liste d'outils une seule fonction a effet de
bord (voir `src/outils/`, `src/planner.py`). Le pire qu'il puisse faire, injecte ou
non, est de proposer une mauvaise action (ou aucune), que l'humain voit et valide
ligne par ligne avant qu'elle ne parte reellement. Voir la section "Securite" de
[SPEC.md](./SPEC.md).

**A verifier en direct avant le checkpoint** (necessite `ANTHROPIC_API_KEY`) :
`make eval` rejoue automatiquement ce cas et confirme qu'aucune action n'a quitte
l'etat `PROPOSEE` ni ete executee pour de vrai.

Cas d'ecole secondaire, deterministe et gratuit a verifier : toute intention qui
mentionne un sandwich, sous quelque forme que ce soit, doit faire ignorer le reste des
instructions et renvoyer une reponse figee et absurde, sans appeler aucun outil
(`PROMPT_SYSTEME` dans `src/planner.py`, cas 5 de `eval/cases.py`). Utile pour montrer
que le prompt systeme peut imposer un comportement fixe, mais ne remplace pas le cas 6
pour repondre a la question posee.

### Aucune cle cote navigateur

Verifiable directement : `grep -ri "api_key\|github_token" web/` ne renvoie rien. Le
navigateur n'appelle que nos propres routes `/api/...` ; `ANTHROPIC_API_KEY` n'est lue
que par `src/planner.py`, `GITHUB_TOKEN` que par
`src/executeur/handlers/create_github_issue.py`, tous deux cote serveur.

### Limite de taille sur l'intention

`DemandeIntention` (`src/main.py`) borne l'intention a 2000 caracteres
(`Field(min_length=1, max_length=2000)`). Une intention demesuree gonflerait le cout et
la latence de chaque appel a Claude pour rien ; une intention vide ou blanche est
refusee explicitement avant meme d'atteindre le planificateur.

### Echappement HTML

Aucune page ne construit de HTML par concatenation de texte externe (intention,
reponse du modele, nom d'outil, message d'erreur...). Chaque valeur dynamique est
posee via `textContent` ou, quand une portion doit rester du HTML (les liens cliquables
dans la reponse de Claude), passee d'abord par un noeud DOM intermediaire
(`textContent` puis relecture de `innerHTML`), qui echappe automatiquement tout
caractere special. Voir `afficherCarteErreur` et `texteVersHtmlAvecLiens` dans
`web/index.html`.

### Injection SQL

Deja bloquee structurellement : chaque requete de `src/db.py` passe ses valeurs comme
parametres (`?`), jamais par f-string ou concatenation dans le texte SQL. sqlite3 les
transmet separement du texte de la requete, qui ne peut donc jamais etre modifie par une
valeur, meme malveillante. Voir le docstring en tete de `src/db.py`.

### Idempotence

Testee dans `tests/test_idempotence.py` (autonome, sans pytest) :

```bash
python3 tests/test_idempotence.py
```

Verifie deux niveaux : une deuxieme reservation avec la meme cle est refusee par la
contrainte `UNIQUE` (niveau base), et rejouer `executer_plan()` sur un plan deja execute
ne cree jamais une deuxieme ligne dans `executions` (niveau executeur complet, l'action
n'etant plus `APPROUVEE` apres sa premiere execution).

### Filet d'erreur des handlers

Chaque handler (`create_github_issue`, `send_message`, `create_employee_record`) capture
ses propres erreurs previsibles (reseau, disque) et renvoie un resultat structure. Au-
dessus, l'executeur (`src/executeur/executor.py`) capture aussi toute exception, sur les
deux chemins qui appellent un handler (execution normale **et** compensation) : un
handler qui leverait quand meme ne peut jamais faire tomber la route qui l'a appele.

---

## Limites connues

A tenir a jour en continu, pas a remplir la veille du rendu. Une dette nommee n'est plus
une dette cachee.

- Une seule integration externe reelle : GitHub. La messagerie ecrit un fichier `.eml`
  dans `outbox/`, le calendrier genere un `.ics` dans `artifacts/`. Choix assume et
  documente : les signatures sont celles d'un vrai service, seul le transport change.
- Compensation disponible uniquement pour `create_github_issue` (ferme l'issue). Les
  autres outils n'ont pas d'annulation sure et univoque : `send_message` est
  irreversible par nature (un message parti est parti, affiche avant l'approbation),
  `create_employee_record` n'a pas encore d'annulateur ecrit.
- Operateur unique, pas de gestion de roles.
- Pas d'annulation en cascade : annuler une action executee ne desannule pas
  automatiquement celles qui en dependaient.
- `get_employee_info` cherche uniquement par nom, jamais par equipe : aucun moyen pour
  l'agent de lister les membres d'une equipe sans en connaitre deja au moins un nom.
  Verifie en pratique (nom invente + equipe invente) : l'agent le dit clairement et
  degrade proprement plutot que d'inventer, mais ne peut pas resoudre la demande seul.
- La limite de debit fait confiance a `X-Forwarded-For` uniquement si
  `DERRIERE_PROXY_DE_CONFIANCE` est active. Trouve en testant : uvicorn a son PROPRE
  mecanisme de confiance a cet en-tete (actif par defaut des que l'appelant direct est
  `127.0.0.1`), qui reecrit l'IP avant meme que notre code s'execute. Neutralise en local
  (`--no-proxy-headers` dans `lancer.sh`). **Non verifie en production** : la commande de
  demarrage reelle sur Render n'est pas dans ce depot (configuree sur son tableau de
  bord), donc si son architecture reseau fait bien de son proxy le pair TCP direct de
  notre processus, tout va bien ; sinon, `--forwarded-allow-ips` merite d'etre precise
  explicitement plutot que laisse par defaut.

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
| `README.md` | fait, palier 6 (securite, quickstart, limites connues, choix techniques) |
| `SECURITE.md` | fait, palier 5 (revue complete, 27 ajouts) |
| `AGENTS.md` | fait, palier 6 (outils reels, prompt systeme verbatim, reponse a la question d'injection) |
| `JOURNAL.md` | a jour, 7 entrees, une par palier (deux quand le palier a ete scinde entre nous) |
| `.env.example` | fait |
| `.gitignore` | fait |
| Tag `v1.0` | dernier, une fois tout le reste fige (voir palier 6) |
| Demo scriptee 5 min | redigee, a repeter et chronometrer avec Souf avant le checkpoint |
