# CHECKPOINTS.md

A cocher **avant** de traverser la salle. Un palier presente a moitie coute 20 minutes
d'attente.

Regle interne : celui qui presente n'est pas celui qui a le plus code sur ce palier.

---

## Palier 1, CADRAGE (J1 matin, 2h30)

Presente par : **Adam**

- [x] `SPEC.md` : probleme en 5 lignes
- [x] 3 user stories maximum
- [x] Hors scope, au moins 5 items (nous en avons 10)
- [x] Une ligne designee pour la carte "LE NON ARGUMENTE" (item 9 du hors scope)
- [x] Schema d'architecture : front, back, agent, outils, stockage
- [x] Liste des outils : nom, signature typee, effet de bord oui ou non
- [x] Happy path de la demo finale en 6 etapes numerotees
- [x] Partage du travail entre nous deux, ecrit
- [x] `.gitignore` avec `.env` dedans
- [x] `.env.example` commite, `.env` jamais

Ce que le formateur fait devant nous :

- [ ] Il lit notre hors scope **avant** notre scope
- [ ] Il verifie nos signatures : `recherche()` n'est pas une signature
- [ ] Il designe l'un de nous, qui explique le schema entier pendant que l'autre se tait
- [ ] Il nous fait raconter les 6 etapes de la demo comme si le projet etait fini

Repetition faite a deux : [ ]

---

## Palier 2, SOCLE (J1 apres-midi)

Presente par : **Souf**

Objectif reel : un squelette qui tourne de bout en bout, avec un appel LLM
qui s'affiche a l'ecran. Pas de fonctionnalite. Juste le tuyau, ouvert.

### Ce qu'il demande

- [x] Depot Git, premier commit dans les 30 minutes, historique lisible
- [x] Un front minimal et un back qui expose au moins une route, les deux demarrent
- [x] Un appel LLM reel qui remonte jusqu'a l'ecran
- [x] `.env.example` commite, `.env` dans le `.gitignore`
- [x] `README.md` avec un quickstart : clone, install, lancer
- [x] **CARTE BONUS +5 : deploye et ouvrable depuis un telephone**
      https://pennyworth.adamzou.fr

### Ce qu'il fait devant nous

- [ ] Il clone le depot sur SA machine et lance en suivant notre README.
      **Moins de 5 minutes, sinon le palier n'est pas valide.**
      A tester sur la machine de l'autre AVANT de traverser la salle.
- [ ] Premier oral du code : il ouvre un fichier au hasard et designe l'un de
      nous. « C'est l'IA qui l'a ecrit » n'est pas une reponse.
- [ ] Il demande ou sont nos cles d'API. La bonne reponse ne contient pas le
      mot « front ».

### Ce qui reste de notre cote

- [ ] Le clone chronometre, dans un dossier vide, sur la machine de l'autre
- [ ] Relecture croisee de 15 minutes : chacun explique le code de l'autre
- [ ] Souf a lu `src/db.py`, `src/main.py` et `src/planner.py` a voix haute
- [ ] Souf a configure son identite git (le premier commit est signe Mr.Robot)
- [ ] `JOURNAL.md` : entree du palier 2, ecrite par chacun
- [ ] `dev` fusionne dans `main` (le formateur clone `main`)

### La reponse sur les cles, a savoir dire par les deux

> En local, dans un `.env` qui est dans le `.gitignore`. En production, dans
> les variables d'environnement de l'hebergeur. Le depot n'en contient aucune,
> et le navigateur non plus : il ne parle qu'a notre serveur. Le seul fichier
> du projet qui touche a Claude est `src/planner.py`.

---

## Palier 3, LE PREMIER OUTIL (J2 matin)

Presente par : **Adam**

- [ ] Le plan est produit par le modele, plus en dur
- [ ] Sortie structuree validee, plan rejete et replanifie si invalide
- [ ] Le modele appelle reellement des outils de lecture avant de proposer
- [ ] Au moins un outil branche sur une vraie API externe (GitHub)
- [ ] Flux SSE : le plan s'affiche pendant sa construction (carte bonus "streaming")
- [ ] `AGENTS.md` : prompts systeme documentes
- [ ] `JOURNAL.md` entree du palier ecrite
- [ ] Relecture croisee faite

---

## Palier 4, LA BOUCLE FERMEE, MVP (J2 apres-midi)

Presente par : **Souf**

**Le seul palier obligatoire. Ici on ne commence rien de neuf, on termine.**

- [ ] Les 6 etapes du happy path tournent de bout en bout
- [ ] Le refus d'une action bascule ses dependantes en bloquees, visible a l'ecran
- [ ] L'irreversibilite s'affiche **avant** l'approbation
- [ ] Double clic sur executer : rien ne part en double
- [ ] Ca tourne avec les donnees du formateur, pas les notres
- [ ] Happy path rejoue deux fois d'affilee avant de traverser la salle
- [ ] `JOURNAL.md` entree du palier ecrite

---

## Palier 5, DURCISSEMENT (J3 matin)

Presente par : **Adam**

- [ ] Annulation avec compensation, cas irreversible gere proprement
- [ ] Cout et latence affiches par plan (carte bonus "cout affiche")
- [ ] Harnais d'eval : 8 a 10 intentions, verification automatique du plan produit
      (carte bonus "eval automatisee")
- [ ] Re-planification apres un refus (bonus du sujet)
- [ ] `README.md` complet
- [ ] **Quickstart chronometre reellement**, dans un dossier vide, sur une machine propre
- [ ] Section "limites connues" a jour (carte bonus "zero dette expliquee")
- [ ] `JOURNAL.md` entree du palier ecrite

---

## Palier 6, LIVRAISON (J3 13h00 a 15h30)

Presente par : **Souf**

**Plus une ligne de code.**

- [ ] `git log -p | grep -iE "sk-ant|api[_-]?key|token"` ne remonte rien
- [ ] `JOURNAL.md` : 5 entrees minimum, relues
- [ ] Tag `v1.0` pose
- [ ] Demo scriptee ecrite mot a mot : 4 min nominal, 1 min cas d'echec
- [ ] Cas d'echec choisi : le refus qui bloque une dependance
- [ ] Trois repetitions chronometrees, en alternant qui parle

---

## Les jokers

- [ ] **PANSEMENT** : 5 min avec le formateur sur un bug bloquant.
      Regle interne : bloques plus de 45 minutes sur le meme bug, on le brule. Pas de debat.
- [ ] **VIRAGE** : changer un choix technique majeur. Se declare **avant**, pas apres.
- [ ] **ESPION** : 3 min chez un autre binome, sujet different du notre.
      A faire tot. Et se faire espionner rapporte +2 points, donc on accepte toujours.
