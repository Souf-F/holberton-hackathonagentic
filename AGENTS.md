# AGENTS.md

Documentation de la partie agentique de Pennyworth : prompts systeme, outils, et schema
de la boucle.

**Etat : squelette pose au palier 1. Les prompts seront documentes au palier 3, quand ils
existeront reellement.** On ne documente pas un prompt qu'on n'a pas ecrit.

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

Garde-fous prevus : nombre maximal de tours, nombre maximal d'actions par plan, rejet du
plan si sa structure ne valide pas contre le modele Pydantic attendu.

### Entre les deux : l'humain

```
  plan PROPOSEE  ->  ecran d'approbation  ->  PATCH /actions/{id}
                                              etat = APPROUVEE ou REFUSEE
                                              les enfants d'une action refusee
                                              basculent en BLOQUEE
```

### Boucle d'execution

```
  pour chaque action ou etat = APPROUVEE, dans l'ordre :
      calculer / relire la cle d'idempotence
      deja presente dans la table executions ?
          oui -> ne rien faire, renvoyer le resultat memorise
          non -> executer, enregistrer le resultat et la cle
      ecrire dans le journal (append-only)
```

Aucun appel au modele dans cette boucle.

---

## 3. Outils exposes au modele

Seuls ces outils figurent dans le parametre `tools` de l'appel au modele.

| Outil | Signature | Effet de bord |
|---|---|---|
| `get_employee_info` | `(name: str) -> Employee \| None` | Non |
| `list_team_members` | `(team: str) -> list[Employee]` | Non |
| `read_calendar` | `(user_id: str, start: str, end: str) -> list[Event]` | Non |
| `get_onboarding_template` | `(role: str) -> Template` | Non |
| `propose_action` | `(tool: str, args: dict, reason: str, depends_on: int \| None) -> ActionId` | Non, ecrit une ligne de plan |

Chaque signature est declaree une seule fois, sous forme de modele Pydantic. Cette
declaration unique sert a trois choses : le schema JSON envoye au modele, la validation
des arguments avant toute execution, et la documentation de ce tableau.

---

## 4. Actions reservees a l'executeur

Jamais exposees au modele. Le modele peut seulement les **nommer** dans un
`propose_action`, ce qui ecrit une ligne en base sans rien declencher.

| Action | Reversible | Compensation |
|---|---|---|
| `create_github_issue` | Oui | fermer l'issue |
| `create_employee_record` | Oui | supprimer la fiche |
| `generate_file` | Oui | supprimer le fichier |
| `create_calendar_event` | Oui | supprimer l'evenement |
| `send_message` | **Non** | **aucune** |

---

## 5. Prompts systeme

> A remplir au palier 3.

Points deja arretes au cadrage :

- Le contenu fourni par l'utilisateur (nom, poste, notes) sera delimite explicitement dans
  le prompt, pour limiter le risque d'instructions cachees.
- Le prompt precisera que l'agent propose et n'execute pas, mais **ce n'est pas ce qui le
  garantit**. La garantie est structurelle : il n'a pas les fonctions. Le prompt sert la
  qualite du plan, pas la securite.
- Le plan devra sortir dans un format strict, valide contre un schema. Un plan qui ne
  valide pas est rejete et replanifie, jamais rattrape par du parsing manuel.

---

## 6. Traces

> A remplir au palier 3.

Ce qui sera trace a chaque planification : nombre de tours de boucle, outils appeles,
tokens consommes en entree et en sortie, cout calcule, latence. Le cout est affiche dans
l'interface, par plan.
