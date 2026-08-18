"""Effet de bord reel : cree une issue sur un depot GitHub.

Jamais expose a Claude (voir src/outils/ pour la liste des outils de
lecture donnes au modele). Seul l'executeur appelle `executer`, apres
qu'un humain a approuve l'action. Le token lu dans GITHUB_TOKEN n'a que
le droit de creer des issues sur GITHUB_REPO (voir .env.example).
"""

import os

import requests

NOM = "create_github_issue"

TIMEOUT_SECONDES = 10


def executer(repo: str, title: str, body: str) -> dict:
    """Cree une issue via l'API GitHub.

    Ne leve jamais : un token absent, un depot inconnu ou une panne
    reseau doivent remonter comme un resultat structure, pas faire
    planter l'executeur qui a peut-etre d'autres actions a traiter
    derriere celle-ci.
    """
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        return {"succes": False, "erreur": "GITHUB_TOKEN absent de l'environnement."}

    try:
        reponse = requests.post(
            f"https://api.github.com/repos/{repo}/issues",
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
            },
            json={"title": title, "body": body},
            timeout=TIMEOUT_SECONDES,
        )
    except requests.RequestException as exc:
        return {"succes": False, "erreur": f"Appel GitHub impossible : {exc}"}

    if reponse.status_code != 201:
        return {
            "succes": False,
            "erreur": f"GitHub a refuse la creation (HTTP {reponse.status_code}) : {reponse.text}",
        }

    donnees = reponse.json()
    return {
        "succes": True,
        "numero": donnees["number"],
        "url": donnees["html_url"],
    }
