#!/usr/bin/env bash
# Lance le serveur en mode developpement.
#
# --reload-dir limite la surveillance a src/ et web/ : sans ca, uvicorn
# observe aussi .venv/ (des milliers de fichiers installes par pip), ce qui
# ralentit le demarrage et peut provoquer des redemarrages en boucle.
#
# Ce script existe pour que personne n'ait a retenir ces options : une seule
# commande, toujours la meme, pour tout le monde.

exec uvicorn src.main:app --reload --reload-dir src --reload-dir web
