# JOURNAL.md

Notre travail **avec** l'IA : ce qu'on lui a demande, ce qu'elle a produit, ce qu'on a
refuse, et ce qu'on a du corriger nous-memes.

Une entree minimum par palier, six au total. Ecrites a chaud, jamais en rattrapage.

**Convention pour eviter les conflits git : on ajoute toujours une entree en bas du
fichier, jamais au milieu. Chaque entree est signee.**

---

## Entree 1, palier 1 (cadrage), Souf

**Ce qu'on a demande a l'IA.** [A COMPLETER PAR SOUF : ce que tu lui as demande pour
rediger la premiere version du SPEC, et sous quelle forme.]

**Ce qu'elle a bien fait.** [A COMPLETER]

**Ce qu'on a refuse ou corrige.** [A COMPLETER]

---

## Entree 2, palier 1 (cadrage), Adam

**Ce qu'on a demande a l'IA.** Deux choses. D'abord une analyse du sujet 03 (LE BRAS) a
partir de la page du hackathon, pour identifier ou se jouent reellement les points.
Ensuite une revue critique de la premiere version du SPEC ecrite par Souf, en comparant
avec ce qu'on avait cadre.

**Ce qu'elle a bien fait.** Elle a repere un probleme que nous n'avions pas vu : notre
tableau s'appelait "Outils de l'agent" et contenait `send_slack_message` et
`create_github_issue`. Lu litteralement par le formateur, ca dit que notre agent peut
envoyer un message, ce qui est exactement le comportement decrit comme eliminatoire dans
le sujet. Le tableau a ete scinde en deux : ce que l'agent peut appeler, et ce que seul
l'executeur peut faire apres validation.

Elle a aussi identifie un trou reel : le SPEC ne disait nulle part ce qui se passe quand
on refuse une action dont une autre dependait. Ni dans le scope, ni dans le hors scope.
On a tranche en le mettant dans le scope (champ `depends_on`, etat `BLOQUEE`), parce que
c'est ce qui rend la demo demonstrative.

**Ce qu'on a refuse ou corrige.** [A COMPLETER PAR ADAM : au moins un point ou tu n'as
pas suivi la proposition, et pourquoi. Une entree ou l'IA a toujours raison ne vaut rien
au bareme.]

**Ce qu'on retient.** L'IA a produit un document plus complet que ce qu'on aurait ecrit en
2h30. Le risque est evident et on le nomme ici : un document qu'on n'a pas ecrit est un
document qu'on ne connait pas. On a donc relu le SPEC ligne par ligne a deux avant de le
commiter, en particulier la section des choix ecartes, puisque c'est celle sur laquelle
le formateur va nous interroger.

---

## Entree 3, palier 2 (socle)

> A ecrire lundi soir, avant de rentrer.

---

## Entree 4, palier 3 (premier outil)

> A ecrire mardi matin.

---

## Entree 5, palier 4 (MVP)

> A ecrire mardi soir.

---

## Entree 6, palier 5 (durcissement)

> A ecrire mercredi matin.
