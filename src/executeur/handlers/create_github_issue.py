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

    `repo` est recu depuis les arguments proposes par le modele, mais
    jamais utilise pour l'appel : le token n'a le droit d'ecrire que sur
    UN depot, celui de GITHUB_REPO (voir .env.example). Faire confiance
    au `repo` propose par Claude reviendrait a laisser le modele choisir
    la cible reelle de l'appel API, ce que le sujet interdit justement.
    Le parametre reste dans la signature pour ne pas casser les actions
    deja proposees (qui l'ont dans leurs arguments enregistres), et parce
    que le laisser visible a l'ecran, meme ignore, garde la proposition
    lisible pour l'humain qui valide.

    Ne leve jamais : un token absent, un depot inconnu ou une panne
    reseau doivent remonter comme un resultat structure, pas faire
    planter l'executeur qui a peut-etre d'autres actions a traiter
    derriere celle-ci.
    """
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        return {"succes": False, "erreur": "GITHUB_TOKEN absent de l'environnement."}

    depot_autorise = os.getenv("GITHUB_REPO")
    if not depot_autorise:
        return {"succes": False, "erreur": "GITHUB_REPO absent de l'environnement."}

    try:
        reponse = requests.post(
            f"https://api.github.com/repos/{depot_autorise}/issues",
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


def annuler(resultat_execution: dict) -> dict:
    """Compensation reelle : ferme l'issue creee par `executer`.

    `resultat_execution` est le JSON garde dans executions.resultat au
    moment de l'execution d'origine (voir src/executeur/executor.py) :
    c'est de la qu'on relit le numero d'issue a fermer, jamais depuis les
    arguments de l'action (qui ne contiennent que repo/title/body, pas le
    numero attribue par GitHub apres coup).
    """
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        return {"succes": False, "erreur": "GITHUB_TOKEN absent de l'environnement."}

    depot_autorise = os.getenv("GITHUB_REPO")
    if not depot_autorise:
        return {"succes": False, "erreur": "GITHUB_REPO absent de l'environnement."}

    numero = resultat_execution.get("numero")
    if numero is None:
        return {
            "succes": False,
            "erreur": "Aucun numero d'issue dans le resultat d'origine, "
                      "rien a fermer.",
        }

    try:
        reponse = requests.patch(
            f"https://api.github.com/repos/{depot_autorise}/issues/{numero}",
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
            },
            json={"state": "closed"},
            timeout=TIMEOUT_SECONDES,
        )
    except requests.RequestException as exc:
        return {"succes": False, "erreur": f"Appel GitHub impossible : {exc}"}

    if reponse.status_code != 200:
        return {
            "succes": False,
            "erreur": f"GitHub a refuse la fermeture (HTTP {reponse.status_code}) : {reponse.text}",
        }

    donnees = reponse.json()
    return {"succes": True, "numero": donnees["number"], "url": donnees["html_url"]}
