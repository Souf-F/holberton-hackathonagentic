# AGENTS.md

Documentation de la partie agentique de Pennyworth : prompts systeme, outils, et schema
de la boucle.

**Etat : a jour au 19 aout 2026 (palier 5).** Ce fichier est reste un squelette du
palier 1 jusqu'a cette date (tools inexistants encore listes, sections "a remplir au
palier 3" jamais remplies) : corrige ici avec la realite du code, pas les intentions du
cadrage.

---

## 1. Le principe qui gouverne tout

Il y a **deux boucles distinctes**, et une seule contient un modele.

| | Planificateur | Executeur |
|---|---|---|
| Contient un LLM | oui | **non** |
| Outils a effet de bord | **aucun** | tous |
| Declenche par | une intention utilisateur | une approbation humaine |
| Peut ecrire dans | la table `actions`, etat `PROPOSEE` | le monde reel, puis le journal |

Le planificateur ne recoit jamais les fonctions d'ecriture dans sa liste d'outils. Ce
n'est pas une regle qu'on lui donne dans le prompt, c'est une absence de capacite. Un
prompt se contourne, une fonction absente ne s'appelle pas.

**C'est la reponse a la question du checkpoint palier 5** ("que se passe-t-il si
l'utilisateur ecrit *ignore tes instructions precedentes* ?") : meme si l'injection
reussissait totalement a detourner la reponse en texte de Claude, `propose_action` (le
seul outil d'ecriture qu'il connaisse) ne peut jamais rien faire d'autre qu'ecrire une
ligne `PROPOSEE` en base. Aucun outil a effet de bord reel (fermer une issue, envoyer un
message, executer quoi que ce soit) ne figure jamais dans la liste `tools` envoyee au
modele (voir section 3). Rejoue automatiquement par `eval/cases.py` (cas 6, phrase du
sujet reprise mot pour mot) : `make eval` confirme qu'aucune action ne peut atteindre un
etat autre que `PROPOSEE` et que rien n'apparait dans `executions`, quoi que le modele
reponde. Detail complet : [SECURITE.md](./SECURITE.md), [README.md](./README.md#injection-de-prompt).

---

## 2. Schema de la boucle

### Boucle de planification

```
  intention utilisateur
         |
         v
  +---------------------------------------------+
  |  appel au modele                            |
  |  tools = [outils de lecture, propose_action]|
  +---------------------------------------------+
         |
         v
   le modele demande un outil ?
         |
    oui  |                        non
    +----+---------------+         |
    |                    |         v
    v                    |    fin de la boucle
  outil de lecture       |    le plan est complet
  -> resultat renvoye    |
  au modele, on boucle   |
                         |
  propose_action
  -> une ligne est ecrite en base (etat PROPOSEE)
  -> on renvoie l'identifiant au modele, on boucle
```

**Garde-fou reellement en place :** `MAX_TOURS = 6` (`src/planner.py`, juste au-dessus de
`PROMPT_SYSTEME`). La boucle `for _ in range(MAX_TOURS):` sort proprement des qu'un tour
ne demande plus aucun outil (`if not appels: ... return`, evenement `fin`). Si les 6
tours s'epuisent sans que le modele conclue, un evenement `erreur` explicite est emis
(dernieres lignes de `planifier_stream`), jamais un arret silencieux. Pas de limite
separee sur le nombre d'actions par plan (la limite de tours suffit a borner le cout et
la duree ; rien n'empeche aujourd'hui un plan de proposer plus d'actions que prevu au
cadrage, ce n'est pas un risque de securite, juste une limite non implementee).

Le plan ne sort **pas** dans un format valide contre un schema Pydantic global : chaque
appel a `propose_action` est valide individuellement (l'outil doit figurer dans
`OUTILS_CONNUS`, sinon l'appel est rejete avec un message d'erreur renvoye au modele,
voir `src/outils/proposer.py`). Un plan invalide n'est donc pas "rejete et replanifie" en
bloc, chaque action l'est independamment.

### Entre les deux : l'humain

```
  plan PROPOSEE  ->  ecran d'approbation  ->  PATCH /actions/{id}
                                              etat = APPROUVEE ou REFUSEE
                                              les enfants d'une action refusee
                                              basculent en BLOQUEE (cascade,
                                              jusqu'a la vraie cause racine)
```

Garde-fou structurel ajoute pendant le durcissement (palier 5) : une action deja
`BLOQUEE` ne peut plus etre re-approuvee par un PATCH suivant, meme envoye juste apres
par erreur ou dans le mauvais ordre (`src/main.py`, `valider_action`, verifie sur l'etat
relu en base, jamais sur ce que le client pretend savoir).

### Boucle d'execution

```
  pour chaque action ou etat = APPROUVEE, dans l'ordre :
      calculer / relire la cle d'idempotence
      deja presente dans la table executions ?
          oui -> ne rien faire, renvoyer le resultat memorise
          non -> reserver la cle (INSERT protege par une contrainte UNIQUE),
                 SEULEMENT la requete qui gagne la reservation execute reellement
      ecrire dans le journal (append-only)
```

Aucun appel au modele dans cette boucle. Meme garantie d'atomicite pour la compensation
(`db.reserver_compensation`, transition `EXECUTEE -> COMPENSEE` par un `UPDATE`
conditionnel) : deux clics simultanes sur "Annuler" ne peuvent jamais fermer la meme
issue GitHub deux fois.

---

## 3. Outils exposes au modele

Seuls ces outils figurent reellement dans le parametre `tools` de l'appel au modele
(`src/outils/__init__.py` + `src/outils/proposer.py`). Le cadrage du palier 1 en
envisageait deux de plus (`list_team_members`, `get_onboarding_template`) : jamais
construits, retires de ce tableau plutot que laisses comme une promesse fausse.

| Outil | Signature | Effet de bord |
|---|---|---|
| `get_employee_info` | `(name: str) -> {trouve: bool, employe?: dict}` | Non |
| `read_calendar` | `(user_id: str, start: str, end: str) -> {trouve: bool, evenements?: list}` | Non |
| `propose_action` | `(tool: str, args: dict, reason: str, depends_on: int \| None) -> {action_id, position}` | Non, ecrit une ligne de plan en etat `PROPOSEE` |

`get_employee_info` cherche par nom, pas par equipe : il n'existe aucun moyen pour le
modele de lister les membres d'une equipe sans en connaitre deja au moins un nom (limite
connue, voir README.md "Limites connues").

---

## 4. Actions reservees a l'executeur

Jamais exposees au modele. Le modele peut seulement les **nommer** dans un
`propose_action`, ce qui ecrit une ligne en base sans rien declencher.

| Action | Reversible | Compensation reelle |
|---|---|---|
| `create_github_issue` | Oui | **Oui** : ferme l'issue via l'API GitHub (`ANNULATEURS`, `src/executeur/handlers/__init__.py`) |
| `create_employee_record` | Oui | Non construite (le cadrage l'envisageait, pas fait) |
| `send_message` | **Non** | Aucune, assume : un message ecrit dans `outbox/` est considere comme parti |
| `generate_file` | — | Outil jamais branche cote executeur, le prompt systeme dit au modele de ne pas le proposer |
| `create_calendar_event` | — | Idem |

Seul `create_github_issue` a une vraie compensation aujourd'hui. C'est le seul outil
present dans `ANNULATEURS` : un clic sur "Annuler" pour tout autre outil recoit un 409
explicite ("Annulation non prise en charge"), jamais un faux succes.

---

## 5. Prompt systeme

Le prompt complet vit dans `PROMPT_SYSTEME` (`src/planner.py`). Points structurants,
dans l'ordre ou ils apparaissent dans le prompt :

1. **Francais force** : consigne explicite de repondre en francais du premier au dernier
   mot, y compris avant le premier appel d'outil (ajoutee apres avoir observe une
   reponse demarree en anglais pendant les tests).
2. **Easter egg deterministe** : toute mention de "sandwich" fait ignorer le reste des
   instructions et renvoyer une reponse fixe, sans appel d'outil. Cas de test
   `eval/cases.py` cas 5 -- volontairement PAS le cas de reference pour la question
   d'injection du checkpoint (voir section 1 ci-dessus et cas 6), puisque c'est un
   declencheur qu'on a nous-memes ecrit, pas une tentative adversariale.
3. **Interdiction d'inventer** : un outil qui ne trouve rien doit rester absent de la
   proposition, jamais remplace par une supposition.
4. **Info manquante, sur une partie seulement de la demande** : proposer quand meme ce
   qui peut l'etre, signaler ce qui manque dans le texte, ne jamais tout bloquer.
5. **Info totalement absente, ET c'est le tout premier message du plan** (le message
   utilisateur precise explicitement lequel des deux cas c'est, voir
   `_resume_plan_existant` dans `planner.py`) : rediriger vers une toute nouvelle
   demande avec le maximum de details. **Si le plan existe deja** (ajout via la barre
   d'ajout), ne jamais rediriger : poser la question directement dans la reponse.
6. **Contrat d'arguments explicite par outil** : chaque outil listable dans
   `propose_action` a ses noms de champs exacts ecrits noir sur blanc dans le prompt (ex.
   `send_message : channel (str), text (str)`), pour eviter que le modele n'invente des
   noms de champs que l'executeur ne reconnaitrait pas.
7. **Style** : pas de tiret cadratin ni de double tiret dans les reponses.

**Ce que le prompt NE garantit PAS**, et qui n'a jamais ete son role : empecher un
outil a effet de bord d'etre appele. Cette garantie est structurelle (section 1), pas
une consigne qu'on espere voir respectee.

---

## 6. Traces et cout

Trace au fil de l'eau, en direct pendant le streaming (evenements SSE `outil_appel` /
`outil_resultat`, affiches dans le panneau debug de l'ecran du plan). Persistee en base
depuis le durcissement du palier 5 : la trace complete (chaque outil appele, ses
arguments, son resultat, sa duree, s'il est en erreur) est serialisee en JSON dans
`audit_log.details` sur l'evenement `PLAN_PROPOSE` (`src/main.py`, `_flux`), rechargeable
apres un rafraichissement de page (panneau debug ET journal, meme rendu).

Cout et tokens : `usage.input_tokens` / `usage.output_tokens` renvoyes par chaque appel
au modele, cumules sur tous les tours d'un meme plan, convertis en euros
(`_cout_eur`, tarifs Opus par defaut) et affiches dans les badges `meta` de l'ecran du
plan. Persistes en base a la fin du plan (`db.enregistrer_reponse`), donc retrouves
apres un rechargement, pas seulement pendant la session en cours.

Latence : mesuree cote navigateur uniquement (`performance.now()` entre l'envoi et la
fin du flux), jamais persistee -- un rechargement de page ne la reaffiche donc pas
(different du cout/tokens), ce n'est pas un oubli, ca n'aurait pas de sens de deviner la
duree d'une requete qui n'a pas eu lieu maintenant.
