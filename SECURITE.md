# SECURITE.md

Journal de tout le travail de securite fait sur Pennyworth, au-dela de la liste de
taches initiale ("Souf — securite, de bout en bout"). Ce document existe pour
qu'aucune de ces corrections ne se perde dans l'historique git : chaque ligne dit
quoi, pourquoi, et comment c'est verifie.

**27 ajouts au total** : 0 critique (verifie activement : ni RCE, ni SSRF, ni
desererialisation dangereuse trouvee), 1 eleve, 8 moyens, 5 mineurs, 13
verifications/documentations sans code a changer.

Rien de tout ca ne change le comportement par defaut de l'application : chaque
protection ajoutee a ete testee pour confirmer qu'elle n'introduit ni regression
ni changement de comportement pour un usage normal (voir la colonne "Verifie").

---

## Comment lire ce document

| Severite | Sens |
|---|---|
| **ELEVE** | Contourne une garantie de securite centrale du projet |
| **MOYEN** | Exploitable, impact reel mais borne |
| **MINEUR** | Incoherence, defense en profondeur, ecart entre contrat et code |
| **INFO** | Verification faite, rien a corriger, ou risque accepte documente |

---

## Eleve

### 1. Aucune autorisation sur les routes API (IDOR)

**Trouve** : `PATCH /api/actions/{id}`, `POST /api/plans/{id}/execute`,
`POST /api/actions/{id}/compensate` et les routes `GET` n'ont aucun controle
d'acces. Les identifiants sont des entiers sequentiels devinables. Le site
etant deploye publiquement (`pennyworth.adamzou.fr`), n'importe qui pouvait
approuver, executer ou lire le plan de quelqu'un d'autre, sans rien connaitre
de lui.

**Contexte** : `SPEC.md` exclut explicitement l'authentification multi-
utilisateur pour la demo ("un seul profil operateur"). Ajouter un vrai systeme
de comptes maintenant, juste avant un checkpoint, aurait pu casser le parcours
de demo (front sans ecran de connexion). La correction ci-dessous respecte ce
choix : rien ne change tant qu'on ne l'active pas explicitement.

**Corrige** : jeton d'acces optionnel, desactive par defaut.
`APP_ACCESS_TOKEN` vide en `.env` (defaut) = comportement inchange, verifie.
Rempli = chaque route `/api/...` (sauf les fichiers statiques) exige l'en-tete
`X-Access-Token`, compare avec `hmac.compare_digest` (resistant aux attaques
temporelles). Fichiers : `src/main.py` (`verifier_acces`), `.env.example`.

**Verifie** : testé serveur eteint/rallume avec et sans le jeton. Sans jeton :
toutes les routes repondent comme avant (200/404 selon le cas). Avec jeton
configure : requete sans en-tete -> 401, mauvais jeton -> 401, bon jeton -> 200.

**Limite assumee, documentee ici** : le front (`web/`) n'envoie pas encore cet
en-tete. L'activer aujourd'hui casserait l'usage normal depuis le navigateur.
C'est une option prete pour un deploiement plus expose, pas une solution
complete a elle seule (voir "Reste a faire" en bas de ce document).

---

## Moyen

### 2. Documentation OpenAPI exposee publiquement

**Trouve** (confirme par le scan externe, verifie en direct) :
`/openapi.json` renvoyait 200 avec le schema complet de l'API : toutes les
routes, tous les champs, sans le moindre effort de decouverte pour un
attaquant.

**Corrige** : `docs_url=None, redoc_url=None, openapi_url=None` sur
l'instance FastAPI. `src/main.py`.

**Verifie** : `/docs`, `/redoc`, `/openapi.json` renvoient 404 en local apres
le changement. Les deux pages front (`index.html`, `journal.html`) continuent
de repondre 200, aucune route API n'a change de comportement.

### 3. Pas de limite de debit (rate limiting)

**Trouve** : `POST /api/plans` declenche un vrai appel payant a Claude, sans
aucune limite. Un script pouvait spammer l'endpoint et consommer le budget
API, ou multiplier les creations reelles d'issues GitHub via le point 1.

**Corrige** : limiteur en memoire, par adresse IP (lecture de
`X-Forwarded-For` en priorite, repli sur l'IP directe), fenetre glissante de
60 secondes, 20 appels max. Applique uniquement aux routes couteuses ou a
effet de bord reel : `POST /api/plans`, `POST /api/plans/{id}/ajouter`,
`POST /api/plans/{id}/execute`, `POST /api/actions/{id}/compensate`.
**Volontairement pas applique** a `PATCH /api/actions/{id}` : le bouton
"Executer les taches cochees" envoie plusieurs PATCH en rafale en usage tout
a fait normal (un refus puis plusieurs approbations d'un coup), le brider
aurait casse ce flux precis. `src/main.py`.

**Verifie** : 25 appels consecutifs sur une route limitee -> les premiers
passent, le reste recoit 429 "Trop de requetes". Seuil confirme exact (20 par
fenetre). Aucune dependance ajoutee (pas de `slowapi`), coherent avec le
choix du projet de ne pas ajouter de service externe pour ca.

### 4. Compensation vulnerable a une course (TOCTOU)

**Trouve** : `POST /api/actions/{id}/compensate` verifiait l'etat
(`EXECUTEE`) puis appelait l'annulateur, sans rien entre les deux qui empeche
deux requetes concurrentes de passer toutes les deux la verification.
Contrairement a l'execution (protegee par la contrainte `UNIQUE` de la base),
la compensation n'avait qu'une verification applicative.

**Corrige** : `db.reserver_compensation()` fait la transition
`EXECUTEE -> COMPENSEE` de facon atomique via un `UPDATE ... WHERE etat =
'EXECUTEE'`, en verifiant `rowcount`. Une seule requete concurrente peut
gagner. Si l'annulation echoue ensuite pour de vrai (ex. panne GitHub),
l'etat revient a `EXECUTEE` (`executor.annuler_action`). La route distingue
maintenant un vrai echec (502) d'une course perdue (409).
`src/db.py`, `src/executeur/executor.py`, `src/main.py`.

**Verifie** : test direct de deux reservations concurrentes sur la meme
action (la premiere gagne, la deuxieme est rejetee), et test d'un annulateur
qui echoue (l'etat revient bien a `EXECUTEE`, pas bloque a `COMPENSEE`).
Testé aussi en HTTP reel : compenser une action deja compensee renvoie 409.

### 5. Pas d'en-tetes de securite

**Trouve** : aucun `Content-Security-Policy`, `X-Frame-Options`,
`X-Content-Type-Options`, `Referrer-Policy`, `Permissions-Policy` ni
`Strict-Transport-Security` sur aucune reponse. Le scan externe n'a meme pas
detecte ce manque (son test a plante silencieusement, voir point 15).

**Corrige** : middleware qui ajoute les six en-tetes sur chaque reponse,
statique et API. `src/main.py`.

**CSP choisie avec attention a ne rien casser** : `script-src 'unsafe-inline'`
est necessaire (le front est en JS inline, pas de bundler, choix assume du
projet) — sans ca, aucun script ne s'execute, page cassee. `style-src`
autorise `fonts.googleapis.com`, `font-src` autorise `fonts.gstatic.com`
(les deux polices Google utilisees). Tout le reste reste strict :
`frame-ancestors 'none'` (anti-clickjacking), `object-src 'none'`,
`connect-src 'self'` (coherent avec "pas de CORS a gerer", le front n'appelle
que sa propre API).

**Verifie** : en-tetes presents sur les pages statiques, les reponses JSON,
**et** sur le flux SSE (`POST /api/plans`, testé avec un flux reel qui
streame un evenement d'erreur) — la reponse en streaming garde bien
`content-type: text/event-stream` et tous les en-tetes de securite. HSTS ne
gene pas le dev local : les navigateurs l'ignorent quand la reponse n'arrive
pas en HTTPS, verifie dans la doc du standard.

### 6. `send_message` ne tenait pas sa propre promesse ("ne leve jamais")

**Trouve** : test manuel — un `channel` contenant un retour a la ligne fait
lever `ValueError` a `EmailMessage()` (protection anti-injection d'en-tete
deja assuree par la bibliotheque standard, bonne nouvelle en soi). Mais le
handler ne capturait que `OSError`. Son propre docstring dit pourtant
"ne leve jamais". Sans le filet de securite ajoute plus tot dans
`executor.py`, ca aurait pu remonter une exception brute.

**Corrige** : `except (OSError, ValueError)` au lieu de `except OSError`.
`src/executeur/handlers/send_message.py`.

**Verifie** : test direct avec un `channel` contenant `\r\n` : leve bien
`ValueError` au niveau de la bibliotheque standard (confirmant la protection
native), desormais capturee proprement par le handler lui-meme.

### 7. `DemandeEtatAction.etat` sans limite de taille

**Trouve** : `intention` est bornee a 2000 caracteres, mais `etat` (le corps
du `PATCH /api/actions/{id}`) ne l'etait pas. Incoherence avec la protection
deja posee ailleurs pour la meme categorie de risque.

**Corrige** : `Field(max_length=20)`, largement suffisant pour
`"APPROUVEE"`/`"REFUSEE"`. `src/main.py`.

**Verifie** : une valeur de 40 caracteres est rejetee en 422 avant meme
d'atteindre la logique metier.

### 8. Absence d'enregistrement DNS SPF

**Trouve** (verifie independamment du scan, via DNS-over-HTTPS) : aucun
enregistrement `TXT v=spf1` sur `adamzou.fr` ni son sous-domaine. N'importe
qui peut forger un email en usurpant ce domaine.

**Non corrige dans ce depot** : c'est une configuration DNS du domaine
`adamzou.fr`, geree en dehors du code de Pennyworth (chez le registrar/DNS
d'Adam). Documente ici pour ne pas se perdre, action a faire par Adam.

### 9. Absence d'enregistrement DNS DMARC

Meme situation que le point 8 : confirme (`_dmarc.adamzou.fr` -> NXDOMAIN),
meme raison de ne pas le corriger depuis ce depot.

---

## Mineur

### 10. Echappement HTML incomplet (index.html)

**Trouve** : 4 endroits utilisaient `innerHTML` avec du texte interpole sans
echappement (messages d'erreur, nom d'outil dans le panneau debug). Un seul
endroit avait ete corrige la veille (`texteVersHtmlAvecLiens`), les autres non.

**Corrige** : construction DOM (`textContent`) partout, factorisee dans
`afficherCarteErreur()` pour eviter 4 copies du meme bloc. `web/index.html`.

### 11. Echappement HTML incomplet (journal.html)

Meme categorie : 3 endroits (message d'erreur, type d'evenement, horodatage).
Meme correction, meme helper `afficherCarteErreur()`. `web/journal.html`.

### 12. `annuler_action` sans filet d'erreur (trouve avant ce document, garde ici pour la vue d'ensemble)

`_executer_une_action` capturait deja toute exception venant d'un handler,
`annuler_action` non : un annulateur qui leve aurait fait tomber la route
`/compensate` avec un 500 brut. Corrige et teste (annulateur simule qui leve,
la route repond proprement). `src/executeur/executor.py`.

### 13. Limite de taille sur `intention` (trouve avant ce document)

`DemandeIntention.intention` bornee a 2000 caracteres. Sans ca, une intention
demesuree gonflerait cout et latence de chaque appel Claude pour rien.
`src/main.py`.

### 14. Absence d'enregistrement DNS CAA

Confirme independamment (aucune reponse CAA sur le domaine ni le
sous-domaine) : n'importe quelle autorite de certification pourrait emettre
un certificat pour ce domaine. Meme remarque que les points 8-9 : configuration
DNS hors du code, a faire par Adam.

---

## Verifications faites, sans code a changer (INFO)

### 15. Le rapport de scan externe se trompait sur 2 points majeurs

- **TLS marque "invalide" (ELEVE dans le rapport)** : faux positif confirme
  par `openssl s_client` (`Verify return code: 0 (ok)`) et `curl -v`
  (`SSL certificate verify ok.`). L'erreur venait du trousseau de
  certificats local a l'outil de scan, pas du serveur.
- **"Aucun WAF/CDN detecte"** : faux, confirme par les en-tetes reels
  (`server: cloudflare`, `cf-ray`). Le module de detection du scanner a
  rate une signature pourtant explicite.

Documente pour que personne ne perde de temps a re-corriger un probleme TLS
qui n'existe pas.

### 16. Historique git audite pour des secrets deja commit

`git log -p --all` passe au crible (motifs `sk-ant-`, `ghp_`, `AIza...`,
valeurs remplies de `ANTHROPIC_API_KEY=`/`GITHUB_TOKEN=`) : rien trouve.
`.env` n'a jamais fuite dans l'historique.

### 17. `.gitignore` audite

Couvre `.env`, les bases SQLite, `data/`, `outbox/`, `artifacts/`, les caches
Python. Rien a ajouter.

### 18. Injection SQL : deja bloquee, documentee

Chaque requete de `src/db.py` passe ses valeurs en parametres (`?`), jamais
par f-string ou concatenation. Verifie mecaniquement (`grep` sur les patterns
de construction dynamique de requete : aucun trouve). Docstring ajoutee en
tete de `src/db.py` pour que ce soit visible sans avoir a le redemontrer.

### 19. Idempotence testee, pas seulement affirmee

`tests/test_idempotence.py` : deux niveaux verifies (reservation refusee au
niveau base, `executer_plan()` rejoue ne cree jamais une deuxieme execution
au niveau applicatif). Autonome, sans pytest.

### 20. Aucune cle API cote navigateur

`grep -ri "api_key\|github_token" web/` : rien. Confirme aussi que le
navigateur n'appelle que ses propres routes `/api/...`, jamais Anthropic ni
GitHub directement.

### 21. Aucun pattern de code dangereux

`grep` sur `eval(`, `exec(`, `pickle`, `subprocess`, `os.system`,
`os.popen`, `__import__` dans tout `src/` : rien trouve. Pas de vecteur
d'execution de code a distance identifiable dans le code applicatif.

### 22. Pas de SSRF dans `create_github_issue`

Le parametre `repo` propose par le modele est recu mais explicitement
ignore : l'appel API n'utilise que `GITHUB_REPO`, une valeur fixee en
environnement. Deja corrige par Adam (`0714e7e`), reverifie ici dans le cadre
de cette revue.

### 23. Pas de traversee de chemin dans les handlers a effet de bord

`send_message` genere son propre nom de fichier via `uuid4()`, jamais a
partir d'une entree utilisateur. `create_employee_record` ecrit dans un
chemin fixe. Aucun des deux ne construit un chemin a partir d'une valeur
fournie par Claude ou l'utilisateur.

### 24. Chiffrement au repos : absent, risque accepte et documente

`data/pennyworth.db` n'est pas chiffree sur disque. Pas de mot de passe ni
de donnee de paiement dans le systeme ; chiffrer une base SQLite (SQLCipher
ou equivalent) serait disproportionne pour ce projet. Documente dans
`README.md`, section Limites connues.

### 25. Hachage : seul usage est la cle d'idempotence, usage correct

`sha256(plan_id + position + outil + arguments)` sert a deduplication, pas a
proteger un secret. Aucun mot de passe n'est stocke nulle part dans le
projet : pas de risque de hachage faible a chercher ici.

### 26. Cookies : aucun utilise

Confirme par le scan externe et en direct (`curl -I` : aucun `Set-Cookie`).
Pas de session, donc pas de `HttpOnly`/`Secure`/`SameSite` a discuter.

### 27. Dependances : versions figees, a revisiter periodiquement

`requirements.txt` entierement epingle (`==`). Aucune CVE precise identifiee
avec certitude dans cet environnement (pas d'acces a une base CVE en direct
depuis ce projet) ; recommande de lancer `pip list --outdated` avant le tag
`v1.0`.

---


