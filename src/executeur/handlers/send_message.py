"""Effet de bord assume : ecrit un fichier .eml dans outbox/ plutot que
d'envoyer un vrai message (voir SPEC.md, "implementations assumees").

La signature est celle d'un vrai service de messagerie : remplacer ce
fichier par un connecteur reel (Slack, SMTP) ne toucherait a rien
d'autre dans le systeme. C'est le seul outil irreversible du projet :
un message ecrit ici est considere comme parti, sans compensation
possible.
"""

import os
import uuid
from datetime import datetime
from email.message import EmailMessage
from email.utils import format_datetime
from pathlib import Path

NOM = "send_message"

DOSSIER_OUTBOX = Path(os.getenv("OUTBOX_DIR", "./outbox"))


def executer(channel: str, text: str) -> dict:
    """Ecrit un message au format .eml dans outbox/.

    Ne leve jamais : un dossier non inscriptible doit remonter comme un
    echec structure, pas faire planter l'executeur.
    """
    try:
        DOSSIER_OUTBOX.mkdir(parents=True, exist_ok=True)

        maintenant = datetime.now()

        message = EmailMessage()
        message["To"] = channel
        message["Subject"] = f"Message Pennyworth vers {channel}"
        message["Date"] = format_datetime(maintenant)
        message.set_content(text)

        identifiant = uuid.uuid4().hex
        nom_fichier = f"{maintenant:%Y%m%dT%H%M%S}-{identifiant[:8]}.eml"
        chemin = DOSSIER_OUTBOX / nom_fichier
        chemin.write_bytes(bytes(message))

        return {"succes": True, "message_id": identifiant, "chemin": str(chemin)}
    except OSError as exc:
        return {"succes": False, "erreur": f"Ecriture impossible dans outbox/ : {exc}"}
