"""Cas d'evaluation structures, source de verite executable pour eval/run.py.

eval/cases.md est la version humaine (pourquoi chaque cas existe, avec le
dernier resultat observe en clair). Ce fichier est la version executable
(comment on le verifie automatiquement, sans un humain qui relit chaque
fois). Les deux doivent rester coherents : si un cas change ici, mettre a
jour cases.md, et inversement.

Chaque `verifier` recoit le dict renvoye par eval.run.executer_plan (ou
eval.simulateur en mode --dry-run) et renvoie (succes: bool, detail: str).
"""


def _contient(texte: str, motif: str) -> bool:
    return motif.lower() in (texte or "").lower()


def _verifier_cas_1(resultat: dict) -> tuple:
    """Ce cas verifie l'ITERATION multi-tours, rien d'autre. Deux versions
    anterieures de ce critere exigeaient aussi un nombre precis d'actions
    (>=3 puis >=2) et un send_message irreversible : rejoue plusieurs fois
    a l'identique (memes mots, Opus ET Sonnet), la meme scene a produit
    tantot 4 actions, tantot 2, tantot 1 seule -- avec une explication
    parfaitement valable a chaque fois (ex. Claude refuse a raison de
    proposer create_calendar_event, cet outil n'etant pas branche). Ce que
    Claude CHOISIT de proposer varie legitimement ; la sequence d'appels
    d'outils qui l'y amene, elle, ne devrait jamais varier."""
    outils = resultat["outils"]

    nb_recherches = outils.count("get_employee_info")
    if nb_recherches < 2:
        return False, f"attendu >= 2 appels a get_employee_info, obtenu {nb_recherches}"
    if "read_calendar" not in outils:
        return False, "read_calendar jamais appele"
    if outils.index("read_calendar") < outils.index("get_employee_info"):
        return False, "read_calendar appele avant la premiere recherche d'employe"
    return True, ""


def _verifier_cas_2(resultat: dict) -> tuple:
    if resultat["actions"]:
        return False, f"attendu 0 action, obtenu {len(resultat['actions'])}"
    if not _contient(resultat["reponse"], "nouvelle demande"):
        return False, "la reponse ne redirige pas vers une nouvelle demande"
    return True, ""


def _verifier_cas_3(resultat: dict) -> tuple:
    if not resultat["actions"]:
        return False, "aucune action proposee malgre une info partielle exploitable"
    if _contient(resultat["reponse"], "nouvelle demande"):
        return False, "redirige a tort vers une nouvelle demande"
    return True, ""


def _verifier_cas_4(resultat: dict) -> tuple:
    """Ce cas verifie UNE chose : qu'on ne redirige jamais vers une
    nouvelle demande sur un plan qui existe deja, meme si Claude decide de
    ne rien ajouter cette fois-ci (ex. il pose une question au lieu de
    proposer une action, ce qui est un comportement tout a fait correct,
    pas un echec). Une premiere version de ce critere exigeait aussi
    qu'une action soit ajoutee : ca melangeait deux choses differentes, et
    ca a fait echouer le test sur une reponse de Claude par ailleurs
    parfaitement honnete ("il me manque le nom de l'equipe, precise-le")."""
    if _contient(resultat["reponse"], "nouvelle demande"):
        return False, "redirige a tort alors que le plan existait deja"
    if not (resultat["reponse"] or "").strip():
        return False, "reponse vide : le plan existant n'a produit aucune reaction"
    return True, ""


def _verifier_cas_5(resultat: dict) -> tuple:
    attendu = (
        "voici la recette pour le scooby doo sandwich "
        "https://www.youtube.com/watch?v=Aq5WXmQQooo"
    )
    if (resultat["reponse"] or "").strip() != attendu:
        return False, f"reponse differente du texte fixe attendu : {resultat['reponse']!r}"
    if resultat["outils"]:
        return False, f"outils appeles alors qu'aucun ne devrait l'etre : {resultat['outils']}"
    if resultat["actions"]:
        return False, "actions proposees alors qu'aucune ne devrait l'etre"
    return True, ""


CAS = [
    {
        "id": "cas_1",
        "nom": "Nominal, chemin multi-tours",
        "intention": (
            "Prépare l'arrivée de Marc, stagiaire qui rejoint l'équipe de "
            "Karim Haddad, et vérifie un créneau libre chez son manager la "
            "semaine prochaine pour un point d'accueil"
        ),
        "verifier": _verifier_cas_1,
    },
    {
        "id": "cas_2",
        "nom": "Info totalement absente -> redirection",
        "intention": "prépare l'arrivée de quelqu'un",
        "verifier": _verifier_cas_2,
    },
    {
        "id": "cas_3",
        "nom": "Info partielle -> pas de redirection",
        "intention": (
            "créer une fiche employé pour Soufiane Filali, Designer et qui "
            "n'a pas de manager et qui fait partie de l'équipe des "
            "Designers, et préviens l'équipe de son arrivée"
        ),
        "verifier": _verifier_cas_3,
    },
    {
        "id": "cas_4",
        "nom": "Barre d'ajout -> jamais de redirection",
        # Meme intention de depart que le cas 3, PAS du texte factice generique :
        # sur un premier essai, "Test Un, Role Test, equipe Test" ne donnait a
        # Claude rien d'assez concret pour proposer quoi que ce soit a l'ajout
        # suivant. Un plan prealable pauvre invalide ce que ce cas est cense
        # tester (une vraie continuation), pas le comportement de l'agent.
        "plan_prealable": (
            "créer une fiche employé pour Soufiane Filali, Designer et qui "
            "n'a pas de manager et qui fait partie de l'équipe des Designers"
        ),
        "intention": "prépare aussi l'arrivée de Karim Benali dans la même équipe",
        "verifier": _verifier_cas_4,
    },
    {
        "id": "cas_5",
        "nom": "Easter egg deterministe (sandwich)",
        "intention": "prépare-moi un bon sandwich pour ce midi",
        "verifier": _verifier_cas_5,
    },
]
