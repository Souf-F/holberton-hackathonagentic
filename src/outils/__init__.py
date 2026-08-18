"""Registre des outils de lecture donnes a l'agent.
Chaque outil vit dans son propre fichier : une description destinee a
Claude (SCHEMA) et une fonction qui l'execute reellement (executer). Ce
fichier ne fait que les rassembler, pour que deux personnes puissent
ajouter un outil chacune sans modifier la meme portion de code.
Ces outils sont TOUS en lecture seule. Aucun n'a d'effet de bord : c'est
la garantie structurelle du sujet, pas une convention qu'on pourrait
oublier.
"""
from src.outils import calendrier, employes

SCHEMAS = [
    employes.SCHEMA,
    calendrier.SCHEMA,
]
HANDLERS = {
    employes.SCHEMA["name"]: employes.executer,
    calendrier.SCHEMA["name"]: calendrier.executer,
}
