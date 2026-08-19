#!/usr/bin/env bash
# Lance le serveur en mode developpement.
#
# --reload-dir limite la surveillance a src/ et web/ : sans ca, uvicorn
# observe aussi .venv/ (des milliers de fichiers installes par pip), ce qui
# ralentit le demarrage et peut provoquer des redemarrages en boucle.
#
# --no-proxy-headers : par defaut, uvicorn fait confiance a X-Forwarded-For
# des qu'il vient de 127.0.0.1 (son reglage --forwarded-allow-ips par
# defaut), et REECRIT request.client.host avec cette valeur avant meme que
# notre code s'execute. En local, ca rend n'importe quel appel curl capable
# de se faire passer pour l'IP de son choix (verifie : la limite de debit de
# src/main.py peut etre contournee entierement de cette facon). Aucun vrai
# proxy en local : rien ne doit reecrire l'IP source ici. Voir SECURITE.md,
# section "Limite de debit", pour la nuance en production (Render).
#
# Ce script existe pour que personne n'ait a retenir ces options : une seule
# commande, toujours la meme, pour tout le monde.

exec uvicorn src.main:app --reload --reload-dir src --reload-dir web --no-proxy-headers
