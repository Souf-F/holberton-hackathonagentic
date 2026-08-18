# JOURNAL.md

Notre travail **avec** l'IA : ce qu'on lui a demande, ce qu'elle a produit, ce qu'on a
refuse, et ce qu'on a du corriger nous-memes.

Une entree minimum par palier. Ecrites a chaud, jamais en rattrapage.

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

**Ce qu'on a demande.** Une analyse du sujet 03 a partir de la page du hackathon, pour
reperer ou se jouent reellement les points. Puis une revue critique de la premiere
version du SPEC ecrite par Souf.

**Ce qu'elle a bien fait.** Elle a repere un probleme qu'on n'avait pas vu : notre
tableau s'appelait « Outils de l'agent » et contenait `send_slack_message` et
`create_github_issue`. Lu litteralement, ca dit que notre agent peut envoyer un message,
ce qui est exactement le comportement decrit comme eliminatoire dans le sujet. On a
scinde en deux tableaux : ce que l'agent peut appeler, et ce que seul l'executeur peut
faire apres validation.

Elle a aussi trouve un trou reel : le SPEC ne disait nulle part ce qui se passe quand on
refuse une action dont une autre dependait. Ni dans le scope, ni dans le hors scope. On
a tranche en le mettant dans le scope (`depends_on`, etat `BLOQUEE`).

**Ce qu'on a refuse.** Le script de presentation qu'elle a produit pour le checkpoint
etait inutilisable : « tranche verticale », « compensation explicite », « contrainte
d'unicite au niveau du moteur ». Du vocabulaire que je n'aurais pas pu defendre si on
m'avait coupe au milieu d'une phrase. J'ai demande une reecriture complete en termes
simples, et c'est cette version-la qu'on a apprise. La lecon vaut pour la suite : un
texte qu'on ne peut pas reformuler avec ses propres mots est un texte qu'on ne connait
pas.

J'ai aussi refuse que l'IA apparaisse en co-auteur des commits. Le travail est le notre,
c'est nous qui le defendons a l'oral.

**Ce qu'on retient.** Elle a produit un cadrage plus complet que ce qu'on aurait ecrit en
2h30. Le risque est evident et on le nomme : un document qu'on n'a pas ecrit est un
document qu'on ne connait pas. On a donc relu le SPEC ligne par ligne a deux avant de le
commiter, en particulier la section des choix ecartes.

---

## Entree 3, palier 2 (socle), Adam

**L'erreur de la journee, et elle est a nous.** On est partis coder chacun de son cote
sans avoir fixe le point de rencontre entre nous : une fonction, un nom, ce qui entre, ce
qui sort. Resultat, on a produit deux socles complets et paralleles, `src/` et
`backend/`, chacun avec son serveur, sa base et son schema. Git n'a signale aucun
conflit, parce que les dossiers portaient des noms differents. C'est le pire cas : le
depot avait deux serveurs et personne ne s'en apercevait avant de regarder.

Cinq minutes de contrat en debut d'apres-midi nous auraient evite une heure de fusion.

**Ce qu'on a garde de chacun.** Le schema de Souf etait meilleur que l'autre sur trois
points qu'on a repris tels quels : `PRAGMA foreign_keys = ON`, les contraintes `CHECK`
sur les etats (la machine a etats est appliquee par la base, pas seulement par le code),
et les index sur les cles etrangeres. On a garde `src/` pour le reste, parce qu'il
demarrait et lisait deja la cle.

**Une vraie correction technique.** La contrainte `UNIQUE` d'idempotence etait posee sur
la table `actions`. Ca empeche de **proposer** deux fois la meme action. Ce qu'on veut
empecher, c'est de l'**executer** deux fois : double clic, retry reseau, rechargement de
page. Elle est passee sur `executions`. On a verifie que SQLite refuse bien le doublon,
plutot que de le supposer.

**Ce qui n'a pas marche comme prevu.** L'hebergement prevu ne fonctionnait pas. On a
bascule sur Render en cours d'apres-midi. Deuxieme accroc : Render ne proposait pas le
depot dans sa liste, parce que je suis collaborateur et pas proprietaire. Contourne en
passant par l'URL publique du depot, au prix du redeploiement automatique qu'on fait
maintenant a la main. Choix assume : avoir l'application en ligne valait plus que
l'automatisation.

**Ce qu'on a du corriger nous-memes.** Le code genere utilisait une syntaxe Python 3.10
alors que nos machines tournent en 3.9. On a choisi d'adapter le code plutot que
d'imposer une installation : le formateur clone sur sa machine, autant viser large.
Et l'interface n'etait pas utilisable sur telephone alors qu'elle passait tres bien sur
ordinateur. Le centrage vertical rendait le haut de la page inaccessible des qu'un plan
depassait la hauteur de l'ecran. Verifie en simulant deux tailles d'ecran plutot qu'en
corrigeant a l'aveugle.

**Une erreur d'organisation a ne pas repeter.** Une reecriture de l'historique git de mon
cote a provoque un conflit chez Souf, qui a commite les marqueurs `<<<<<<<` sans les
resoudre. Le README en ligne etait casse pendant un moment. Regle ajoutee au README : on
ne reecrit pas un historique deja pousse quand on travaille a deux.

---

## Entree 4, palier 2 (socle), Souf

**Ce que j'ai ecrit.** [A COMPLETER PAR SOUF : le schema SQL, le serveur, ce que tu as
choisi et pourquoi. En particulier pourquoi tu avais separe une table `rollbacks`.]

**Ce que j'ai corrige ou refuse.** [A COMPLETER]

---

## Entree 5, palier 3 (premier outil)

> A ecrire mardi matin.

---

## Entree 6, palier 4 (MVP)

> A ecrire mardi soir.

---

## Entree 7, palier 5 (durcissement)

> A ecrire mercredi matin.
