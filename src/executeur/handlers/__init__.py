"""Registre des outils a effet de bord, jamais donnes a Claude.

Chaque outil vit dans son propre fichier, sur le meme modele que
src/outils/ : une fonction executer(...) qui ne leve jamais d'exception
non geree. Seul src/executeur/executor.py lit ce registre, apres qu'une
action a ete approuvee par un humain.
"""
from src.executeur.handlers import create_github_issue, send_message

HANDLERS = {
    create_github_issue.NOM: create_github_issue.executer,
    send_message.NOM: send_message.executer,
}
