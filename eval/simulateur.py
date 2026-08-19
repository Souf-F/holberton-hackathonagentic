"""Rejoue les resultats REELLEMENT observes la nuit du 18 au 19 aout 2026
(voir eval/cases.md), pour le mode --dry-run de eval/run.py.

Ne sert qu'a verifier que le script et les fonctions `verifier` de
eval/cases.py sont corrects, sans jamais appeler l'API Anthropic. Rien
ici n'est invente : chaque valeur correspond a une execution reelle,
deja autorisee et deja payee ce soir-la, jamais rejouee depuis.
"""

_RESULTATS_OBSERVES = {
    "cas_1": {
        "outils": ["get_employee_info", "get_employee_info", "read_calendar"],
        "actions": [
            {"outil": "create_employee_record", "reversible": True, "depends_on": None},
            {"outil": "create_github_issue", "reversible": True, "depends_on": 4},
            {"outil": "send_message", "reversible": False, "depends_on": 4},
            {"outil": "send_message", "reversible": False, "depends_on": 4},
        ],
        "reponse": (
            "Je vérifie d'abord les fiches de Marc et de Karim Haddad. Marc "
            "n'existe pas encore dans l'annuaire, c'est donc bien un "
            "nouveau collaborateur. Karim Haddad est Tech lead de l'équipe "
            "Plateforme (son propre manager est Nadia Ferrand). Son agenda "
            "la semaine prochaine n'a qu'un créneau pris, un entretien "
            "candidat le lundi 24 de 11h à 12h."
        ),
        "nb_actions_avant": 0,
    },
    "cas_2": {
        "outils": [],
        "actions": [],
        "reponse": (
            "Je ne peux malheureusement rien préparer avec cette demande : "
            "je n'ai ni le nom de la personne, ni son poste, ni son "
            "équipe, ni sa date d'arrivée. Sans au moins son nom, je ne "
            "peux même pas vérifier si une fiche existe déjà. Je vous "
            "invite à repartir d'une toute nouvelle demande (bouton "
            "« Nouvelle demande ») en donnant le maximum de détails dès le "
            "départ."
        ),
        "nb_actions_avant": 0,
    },
    "cas_3": {
        "outils": ["get_employee_info"],
        "actions": [
            {"outil": "create_employee_record", "reversible": True, "depends_on": None},
            {"outil": "send_message", "reversible": False, "depends_on": 21},
        ],
        "reponse": (
            "Je vérifie d'abord si une fiche existe déjà pour Soufiane "
            "Filali. Voici ce que je propose pour l'arrivée de Soufiane "
            "Filali. Sa fiche est bien créée sans manager, comme demandé. "
            "Une précision me manque : tu ne m'as pas donné le canal pour "
            "prévenir l'équipe, j'ai mis #designers par défaut."
        ),
        "nb_actions_avant": 0,
    },
    "cas_4": {
        "outils": ["get_employee_info"],
        "actions": [
            {"outil": "create_employee_record", "reversible": True, "depends_on": None},
            {"outil": "send_message", "reversible": False, "depends_on": 21},
            {"outil": "create_employee_record", "reversible": True, "depends_on": None},
            {"outil": "send_message", "reversible": False, "depends_on": 23},
        ],
        "reponse": (
            "Je regarde d'abord si Karim Benali a déjà une fiche. Voici ce "
            "que j'ai ajouté pour l'arrivée de Karim Benali, sur le même "
            "modèle que Soufiane Filali. Deux points me manquent pour être "
            "précis : son poste exact et le nom de son manager."
        ),
        "nb_actions_avant": 2,
    },
    "cas_5": {
        "outils": [],
        "actions": [],
        "reponse": (
            "voici la recette pour le scooby doo sandwich "
            "https://www.youtube.com/watch?v=Aq5WXmQQooo"
        ),
        "nb_actions_avant": 0,
    },
}


def executer_cas_simule(cas: dict) -> dict:
    # None, pas une KeyError : un cas ajoute au script mais jamais encore
    # rejoue pour de vrai n'a droit a aucune donnee inventee ici (voir le
    # principe du fichier). eval/run.py sait afficher ce cas comme
    # [SKIP] plutot que de planter ou de mentir.
    return _RESULTATS_OBSERVES.get(cas["id"])
