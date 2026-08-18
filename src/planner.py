"""Le cerveau : le seul fichier du projet qui parle a Claude.

Palier 3 : la vraie boucle de tool use. Claude peut consulter de vraies
donnees (fiches employes, calendrier) avant de repondre, et decide
lui-meme quand s'en servir. On ne route jamais a sa place : aucun
`if "cherche" in intention`, c'est Claude qui choisit l'outil.

Ces outils sont TOUS en lecture seule (voir src/outils/). C'est ce fichier
qui est aussi la reponse a "ou sont vos cles d'API" : elles sont ici,
cote serveur, lues depuis .env. Le navigateur n'appelle jamais Anthropic.
"""

import json
import os
import time
from datetime import date

from anthropic import Anthropic, AuthenticationError

from src import outils

MODELE = os.getenv("ANTHROPIC_MODEL", "claude-opus-5")

# Tarifs Claude Opus 5, en dollars par million de tokens.
PRIX_ENTREE_USD = 5.0
PRIX_SORTIE_USD = 25.0
# Taux de conversion fige : on affiche un ordre de grandeur, pas une facture.
USD_VERS_EUR = 0.92

# Garde-fou : sans limite, un outil qui boucle sur lui-meme ferait tourner
# le serveur indefiniment et viderait le budget API. 6 tours suffisent
# largement pour un plan d'onboarding.
MAX_TOURS = 6

PROMPT_SYSTEME = """Tu es Pennyworth, un assistant qui prepare l'arrivee des nouveaux
collaborateurs dans une entreprise.

Tu disposes d'outils pour consulter de vraies informations (fiches
collaborateurs, calendrier). Utilise-les chaque fois qu'ils peuvent
t'aider a proposer une action plus precise, par exemple pour trouver le
manager de quelqu'un ou verifier un creneau libre.

Si un outil ne trouve rien ou renvoie une erreur, dis-le clairement dans
ta reponse. N'invente jamais une information que tu n'as pas verifiee :
un manager, un poste ou un evenement que tu n'as pas trouve doit rester
absent de ta proposition, pas remplace par une supposition.

Une fois que tu as ce qu'il te faut, propose la liste des actions
concretes a mener, numerotees, une par ligne, sans commentaire autour.

Tu ne fais rien toi-meme : tu proposes. Un humain validera chaque ligne
avant qu'elle ne soit executee.

Les actions possibles sont : creer une fiche employe, creer une tache
GitHub, envoyer un message, generer un document, poser un evenement de
calendrier."""


class CleManquante(RuntimeError):
    """Levee quand aucune cle API n'est configuree."""


class BoucleTropLongue(RuntimeError):
    """Levee quand la boucle depasse MAX_TOURS sans que Claude conclue."""


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


def _executer_outil(nom: str, arguments: dict) -> tuple:
    """Execute un outil et ne laisse jamais remonter d'exception brute.

    Si l'outil plante ou n'existe plus (on l'a "debranche" pour tester),
    on renvoie une erreur structuree que Claude peut lire, au lieu de
    faire planter tout le serveur. C'est ce que le checkpoint verifie
    explicitement.
    """
    handler = outils.HANDLERS.get(nom)
    if handler is None:
        return {"erreur": f"Outil inconnu ou debranche : {nom}"}, True
    try:
        return handler(**arguments), False
    except Exception as exc:  # l'outil ne doit jamais faire tomber le serveur
        return {"erreur": str(exc)}, True


def planifier(intention: str) -> dict:
    """Fait dialoguer Claude avec ses outils jusqu'a une reponse finale.

    C'est le point de rencontre entre les deux moities du projet : la
    route de main.py appelle cette fonction, et rien d'autre.

    A chaque tour : on envoie la conversation a Claude. S'il demande un
    outil, on l'execute et on lui renvoie le resultat, puis on reboucle.
    S'il ne demande rien, sa reponse est finale.
    """
    client = _client()
    # Sans la date du jour, Claude devine l'annee d'une date relative
    # ("le 24 aout") et se trompe. On la lui donne explicitement plutot
    # que de laisser un outil comme read_calendar recevoir un mauvais
    # argument.
    aujourdhui = f"Nous sommes le {date.today().isoformat()}."
    messages = [{"role": "user", "content": f"{aujourdhui}\n\n{intention}"}]
    trace = []
    tokens_entree_total = 0
    tokens_sortie_total = 0

    for _ in range(MAX_TOURS):
        reponse = client.messages.create(
            model=MODELE,
            max_tokens=16000,
            system=PROMPT_SYSTEME,
            tools=outils.SCHEMAS,
            messages=messages,
        )

        tokens_entree_total += reponse.usage.input_tokens
        tokens_sortie_total += reponse.usage.output_tokens

        # On garde la reponse de Claude dans l'historique avant de
        # continuer : sans ca, il "oublierait" avoir demande un outil.
        messages.append({"role": "assistant", "content": reponse.content})

        appels = [bloc for bloc in reponse.content if bloc.type == "tool_use"]

        if not appels:
            # Aucun outil demande : la reponse en texte est definitive.
            texte = "".join(
                bloc.text for bloc in reponse.content if bloc.type == "text"
            )
            return {
                "reponse": texte,
                "trace": trace,
                "tokens_entree": tokens_entree_total,
                "tokens_sortie": tokens_sortie_total,
                "cout_eur": _cout_eur(tokens_entree_total, tokens_sortie_total),
            }

        # Claude peut demander plusieurs outils dans le meme tour : on les
        # execute tous, et on renvoie TOUS les resultats dans un seul
        # message, jamais repartis sur plusieurs tours.
        resultats_pour_claude = []
        for appel in appels:
            debut = time.monotonic()
            resultat, erreur = _executer_outil(appel.name, appel.input)
            duree_ms = round((time.monotonic() - debut) * 1000)

            resultats_pour_claude.append({
                "type": "tool_result",
                "tool_use_id": appel.id,
                "content": json.dumps(resultat, ensure_ascii=False),
                "is_error": erreur,
            })

            trace.append({
                "outil": appel.name,
                "arguments": appel.input,
                "resultat": resultat,
                "erreur": erreur,
                "duree_ms": duree_ms,
            })

        messages.append({"role": "user", "content": resultats_pour_claude})

    raise BoucleTropLongue(
        f"Claude n'a pas conclu apres {MAX_TOURS} tours d'outils. "
        "Le plan n'a pas pu etre finalise."
    )
