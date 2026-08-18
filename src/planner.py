"""Le cerveau : le seul fichier du projet qui parle a Claude.

Palier 2 : on ouvre le tuyau. Une intention entre, une reponse en texte sort.
Pas encore de boucle d'outils, pas encore de format structure : c'est le palier 3.

Ce fichier est aussi la reponse a "ou sont vos cles d'API" : elles sont ici,
cote serveur, lues depuis .env. Le navigateur n'appelle jamais Anthropic.
"""

import os

from anthropic import Anthropic, AuthenticationError

MODELE = os.getenv("ANTHROPIC_MODEL", "claude-opus-5")

# Tarifs Claude Opus 5, en dollars par million de tokens.
PRIX_ENTREE_USD = 5.0
PRIX_SORTIE_USD = 25.0
# Taux de conversion fige : on affiche un ordre de grandeur, pas une facture.
USD_VERS_EUR = 0.92

PROMPT_SYSTEME = """Tu es Pennyworth, un assistant qui prepare l'arrivee des nouveaux
collaborateurs dans une entreprise.

On te donne une intention en langage naturel. Tu proposes la liste des actions
concretes a mener, numerotees, une par ligne, sans commentaire autour.

Tu ne fais rien toi-meme : tu proposes. Un humain validera chaque ligne avant
qu'elle ne soit executee.

Les actions possibles sont : creer une fiche employe, creer une tache GitHub,
envoyer un message, generer un document, poser un evenement de calendrier."""


class CleManquante(RuntimeError):
    """Levee quand aucune cle API n'est configuree."""


def _client() -> Anthropic:
    """Le client lit ANTHROPIC_API_KEY dans l'environnement.

    On verifie nous-memes plutot que de laisser remonter l'erreur du SDK :
    quelqu'un qui clone le projet sans cle doit comprendre en une phrase ce
    qui lui manque.
    """
    if not os.getenv("ANTHROPIC_API_KEY"):
        raise CleManquante(
            "Aucune cle API. Copiez .env.example en .env et renseignez "
            "ANTHROPIC_API_KEY, puis relancez le serveur."
        )
    return Anthropic()


def _cout_eur(tokens_entree: int, tokens_sortie: int) -> float:
    """Convertit une consommation de tokens en euros."""
    usd = (tokens_entree / 1_000_000) * PRIX_ENTREE_USD + \
          (tokens_sortie / 1_000_000) * PRIX_SORTIE_USD
    return round(usd * USD_VERS_EUR, 4)


def planifier(intention: str) -> dict:
    """Appelle Claude et renvoie sa proposition, avec ce qu'elle a coute.

    C'est le point de rencontre entre les deux moities du projet :
    la route de main.py appelle cette fonction, et rien d'autre.
    """
    reponse = _client().messages.create(
        model=MODELE,
        max_tokens=16000,
        system=PROMPT_SYSTEME,
        messages=[{"role": "user", "content": intention}],
    )

    # response.content est une liste de blocs. On ne garde que le texte.
    texte = "".join(bloc.text for bloc in reponse.content if bloc.type == "text")

    entree = reponse.usage.input_tokens
    sortie = reponse.usage.output_tokens

    return {
        "reponse": texte,
        "tokens_entree": entree,
        "tokens_sortie": sortie,
        "cout_eur": _cout_eur(entree, sortie),
    }
