"""Registre des outils a effet de bord, jamais donnes a Claude.

Chaque outil vit dans son propre fichier, sur le meme modele que
src/outils/ : une fonction executer(...) qui ne leve jamais d'exception
non geree. Seul src/executeur/executor.py lit ce registre, apres qu'une
action a ete approuvee par un humain.
"""
from src.executeur.handlers import create_employee_record, create_github_issue, send_message

HANDLERS = {
    create_github_issue.NOM: create_github_issue.executer,
    send_message.NOM: send_message.executer,
    create_employee_record.NOM: create_employee_record.executer,
}

# Registre separe pour la compensation (l'annulation d'une action deja
# executee). Volontairement incomplet : seuls les outils dont on sait
# annuler l'effet reel pour de vrai (fermer une issue, ici) y figurent.
# Un outil absent d'ANNULATEURS n'est pas un bug, c'est assume : envoyer
# un message ou creer une fiche employe n'ont pas d'annulation sure et
# univoque, mieux vaut refuser proprement (voir executor.annuler_action)
# que d'inventer un comportement.
ANNULATEURS = {
    create_github_issue.NOM: create_github_issue.annuler,
}
