# JOURNAL.md

Notre travail **avec** l'IA : ce qu'on lui a demande, ce qu'elle a produit, ce qu'on a
refuse, et ce qu'on a du corriger nous-memes.

Une entree minimum par palier. Ecrites a chaud, jamais en rattrapage.

**Convention pour eviter les conflits git : on ajoute toujours une entree en bas du
fichier, jamais au milieu. Chaque entree est signee.**

---

## Entree 1, palier 1 (cadrage), Souf

**Ce qu'on a demande a l'IA.** De rediger une premiere version du SPEC.md a partir du
scenario choisi (onboarding d'un nouveau collaborateur avec de vraies API), en incluant
les user stories, le hors scope, les signatures d'outils et le happy path en 6 etapes.

**Ce qu'elle a bien fait.** Une structure complete et conforme aux attentes du palier des
le premier jet : hors scope plus etoffe que le scope, signatures d'outils typees,
section securite qui n'etait pas demandee explicitement mais collait au critere « esprit
critique IA ».

**Ce qu'on a refuse ou corrige.** Rien de majeur a la premiere version, mais on a
retravaille ensemble le nom du projet (Alfred, puis Pennyworth) et adapte les exemples du
happy path pour qu'ils collent exactement a notre scenario d'onboarding, plutot que de
garder des exemples generiques.

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

**Ce que j'ai ecrit.** Une premiere version du schema SQL (4 tables : plans, actions,
audit_log, rollbacks) et un serveur FastAPI minimal (route POST /plans, initialisation
de la base au demarrage). J'avais separe une table `rollbacks` distincte de `audit_log`
pour garder une trace propre des annulations, separee de la trace d'execution -- mais on
a garde la version d'Adam au final, qui range ca dans `audit_log` directement via un
evenement de type annulation, plus simple et suffisant pour le besoin.

**Ce que j'ai corrige ou refuse.** J'ai commite par erreur les marqueurs de conflit
`<<<<<<<` sur le README sans les resoudre, lors d'un merge avec `dev`. Adam a fait la
correction finale (commit 83e4f66). J'ai aussi ecarte une premiere approche ou je
cherchais a recuperer les mots de passe des paliers via l'inspecteur du navigateur, avant
de comprendre que le contenu est chiffre cote serveur (AES-256-GCM) et que les mots de
passe se donnent uniquement a l'oral -- pas une piste technique valable.

---

## Entree 5, palier 3 (premier outil), Adam

**Ce qu'on a demande a l'IA.** Remplacer le plan en dur par un vrai dialogue avec des
outils : `get_employee_info` et `read_calendar` en lecture seule, `propose_action` comme
seule porte de sortie vers une action concrete, et le streaming SSE (carte bonus) pour
afficher le plan pendant sa construction plutot qu'apres 30 secondes d'attente.

**Ce qu'elle a bien fait.** La separation structurelle entre proposer et executer :
`propose_action` ecrit une ligne en base, en etat `PROPOSEE`, et c'est tout. Aucun outil
capable d'un vrai effet de bord n'est jamais donne au modele, ils vivent dans
`src/executeur/`, un module que le planificateur n'importe meme pas. Ce n'est pas une
regle de prompt qu'on espere voir respectee, c'est une impossibilite dans le code.

**Ce qu'on a du corriger nous-memes.** Plusieurs erreurs concretes, pas de la
mise au point :
- `calendrier.py` de Souf contenait du JSON colle par erreur a la place d'un module
  Python. Deplace en donnees dans `seed/calendrier.json`, module reecrit proprement.
- `get_employee_info` ne renvoyait pas d'`id`, ce qui rendait `read_calendar` inutilisable
  a la suite (aucun moyen de chainer les deux outils). Ajoute a toutes les fiches.
- Les evenements calendrier de u004 a u006 manquaient, puis ont ete perdus une seconde
  fois par une fusion qui a garde une version plus ancienne du fichier. Corrige deux fois,
  avec un commit dedie la seconde.
- Claude proposait `send_message` avec des noms de champs invente (`to`, `subject`) alors
  que le handler de Souf attendait `channel`/`text`. On a ecrit noir sur blanc, dans le
  prompt systeme, la signature exacte attendue par chaque outil : la description d'un
  outil guide mieux le modele qu'une regle generale.
- L'exemple central de notre propre SPEC (« Jean », le nouveau stagiaire sans fiche
  existante) plantait : `create_employee_record` n'avait pas de handler cote executeur,
  alors que c'est litteralement le cas qu'on met en avant dans le happy path. On l'a
  construit, et fait fusionner les fiches creees en cours de route avec l'annuaire de
  depart, sinon un collaborateur tout juste cree restait introuvable au tour suivant.

**Ce qu'on retient.** Un contrat d'arguments implicite entre le modele et l'executeur ne
tient pas : il faut l'ecrire explicitement, comme un type. Et le cas d'usage qu'on met en
avant dans sa propre demo merite d'etre le premier qu'on teste, pas le dernier.

---

## Entree 6, palier 4 (MVP), Adam

**Ce qu'on a demande a l'IA.** Un audit complet, contradictoire, du palier obligatoire :
les 6 etapes du happy path de SPEC.md rejouees en direct dans le navigateur, avec des
donnees differentes des notres a chaque fois, en cherchant explicitement a casser les
garanties qu'on annonce plutot qu'a confirmer qu'elles marchent.

**Ce qu'elle a trouve, et que la lecture du code seule n'aurait pas revele.** En testant
le refus d'une action pendant que ses dependantes etaient cochees (exactement le
scenario de demo prevu), les dependantes se sont **reellement executees** au lieu d'etre
bloquees. Cause : `depends_on` est une position (1, 2, 3...) dans le contrat de l'outil
`propose_action`, mais etait ecrite telle quelle dans une colonne qui attend l'identifiant
reel en base, global a toute la table, pas relatif a un plan. Le blocage en cascade ne
retrouvait quasiment jamais sa cible. Personne ne l'avait vu parce que le badge « bloquee »
s'affichait quand meme correctement a l'ecran (lui se base sur la meme donnee, mais dans
l'autre sens) : seul un test adversarial, pas une relecture, a mis le doigt dessus.

Deux garde-fous ajoutes en consequence, pas un seul : la traduction position -> id a
l'ecriture (`src/outils/proposer.py`), et un refus explicite (409) cote serveur si une
action deja `BLOQUEE` est approuvee malgre tout (`src/main.py`), pour que meme un
navigateur qui enverrait les requetes dans le mauvais ordre ne puisse pas contourner le
blocage.

**Ce qui manquait completement, pas juste bugue.** La compensation (etape 6 de notre
propre happy path : annuler une action executee, fermer reellement l'issue GitHub cree,
garder les deux entrees dans le journal sans rien effacer) etait un stub qui renvoyait
501. On l'a construite dans la foulee : un `annuler()` par outil compensable (un seul
pour l'instant, `create_github_issue`), une route qui verifie l'etat avant d'agir, un
bouton dans `journal.html`. Testee sur une vraie issue de notre depot : creee, verifiee,
fermee, verifiee a nouveau via l'API GitHub, pas juste en base chez nous.

**Ce qu'on a refuse ou reporte.** L'ajout d'un outil de recherche d'equipe (l'annuaire ne
cherche que par nom, pas par equipe) a ete identifie mais volontairement laisse de cote :
le systeme degrade deja proprement dans ce cas (il le dit, ne devine pas), corriger
n'etait pas urgent au regard du temps restant. On a aussi choisi, produit, de rediriger
vers une nouvelle demande plutot que de laisser l'agent demander des precisions au fil de
l'eau : plus simple a expliquer a l'oral, et ca evite un flux a deux vitesses (nouvelle
demande vs complement) qu'on aurait du justifier.

**Ce qu'on retient.** Le happy path scripte etait vert du premier coup. La faille ne s'est
vue qu'en essayant activement de le faire echouer, avec des donnees et un ordre de clics
qu'on n'avait pas prevus a l'avance. Tester ce qu'on annonce, pas seulement ce qu'on a
prepare a montrer.

---

## Entree 7, palier 5 (durcissement), Adam

**Ce qu'on a demande a l'IA.** De reprendre chaque point du palier un par un, en direct,
en cherchant a le casser plutot qu'a confirmer qu'il marche : erreurs visibles cote
utilisateur, observabilite, eval automatisee, test qui a une vraie valeur, securite de
base. Meme methode qu'au palier 4 : le happy path scripte ne suffit pas a savoir si un
critere tient, seul un test adversarial le montre.

**Ce qu'elle a trouve en cherchant vraiment a casser, pas en relisant.**
- Le flux SSE n'avait aucun delai d'inactivite : une coupure reseau silencieuse (aucune
  erreur, juste plus rien) laissait "Pennyworth reflechit" tourner indefiniment. Le vrai
  spinner infini que le sujet interdit, le seul cas qu'aucun `try/catch` ne peut
  rattraper. Corrige (45s, `Promise.race`), verifie avec un faux lecteur qui ne repond
  jamais : declenchement exact a 45002ms.
- Cinq chemins reseau sur sept affichaient "Failed to fetch", le message brut du
  navigateur en anglais, au lieu d'une phrase comprehensible. Ca remplissait la lettre du
  critere (visible) sans l'esprit (comprehensible). Trouve en simulant une panne sur
  chacun des sept points d'entree, pas en supposant que "ca doit deja marcher".
- Le badge "echec a l'execution" ne disait jamais pourquoi : il fallait ouvrir le journal
  pour le savoir. Corrige en reutilisant l'audit deja charge par ailleurs, aucun appel
  reseau de plus.
- `AGENTS.md` etait reste un squelette du palier 1, jamais mis a jour : deux sections
  disaient encore "a remplir au palier 3", et le tableau des outils listait
  `list_team_members` et `get_onboarding_template`, deux outils jamais construits. Si le
  formateur avait ouvert ce fichier pour verifier une reponse, il serait tombe sur du
  faux.

**La plus interessante : notre propre script d'eval s'est retourne contre nous, deux
fois.** Premier tour : `eval/cases.py` annoncait 5/5 sans avoir jamais ete reellement
rejoue par un script. Une fois `make eval` ecrit et lance pour de vrai, score reel :
3/5, deux fois de suite, sur Sonnet ET sur Opus. Les deux modeles echouant pareil etait
le signal : le probleme n'etait pas Claude, c'etaient nos criteres. Un cas exigeait un
nombre precis d'actions, alors que Claude a une vraie liberte sur combien il en propose ;
un autre partait d'un contexte de test trop pauvre pour que l'agent ait quoi que ce soit
a continuer. Corriges, on repasse a 5/5 reel.

Deuxieme tour, en verifiant que le cas "injection de prompt" repondait bien a la vraie
question du checkpoint : il s'appuyait en fait sur le easter egg "sandwich", qu'on avait
nous-memes ecrit dans le prompt comme une blague, pas sur "ignore tes instructions
precedentes" (la phrase exacte du sujet). Ajoute un cas 6 avec la bonne phrase : 6/6,
confirme par un vrai appel. Puis, en auditant le script lui-meme (meme reflexe que pour
l'app), trouve qu'une vraie exception (pas un evenement `erreur` propre) faisait planter
tout `make eval` d'un coup, sans le moindre score meme partiel. Corrige : chaque cas
tourne dans son propre `try/except`, verifie en simulant une panne sur les 6 cas a la
fois (score "0/6" proprement rapporte au lieu d'un crash).

**Le travail de Souf, relu et corrige a deux endroits.** Sa revue de securite (27 points,
`SECURITE.md`) est serieuse : IDOR corrige (jeton d'acces optionnel), course concurrente
sur la compensation (TOCTOU) corrigee par un `UPDATE` atomique, documentation OpenAPI
fermee. Deux choses ajustees apres coup : son cas de demo pour l'injection de prompt
utilisait le easter egg sandwich (voir plus haut) ; et sa protection sur `X-Forwarded-For`
ne suffisait pas seule, decouvert en la testant vraiment plutot qu'en la lisant : uvicorn
a son PROPRE mecanisme de confiance a cet en-tete (actif par defaut des que l'appelant
direct est `127.0.0.1`), qui reecrit l'IP AVANT meme que notre code s'execute. Verifie en
local : 25 appels avec un en-tete usurpe contournaient la limite entierement avant le
correctif (`--no-proxy-headers` sur `lancer.sh`), plus apres.

**Ce qu'on a teste pour de vrai, pas en simulant.** Les deux scenarios du checkpoint
("je coupe le reseau", "je vous fais mettre une fausse clef") joues en conditions
reelles : une vraie fausse cle contre l'API Anthropic (rejetee avant toute facturation),
une vraie tentative de connexion vers une adresse injoignable (`ANTHROPIC_BASE_URL`
redirige). Les deux ont echoue proprement, avec un message clair, sans jamais boucler.

**Ce qu'on retient.** Le meilleur reflexe de ce palier n'a pas ete d'ecrire du code, mais
de douter systematiquement de ce qui semblait deja acquis (le score d'eval, la doc, la
protection reseau de Souf) et de le reverifier en conditions reelles avant de le
declarer bon. Deux fois sur trois, le doute etait fonde.