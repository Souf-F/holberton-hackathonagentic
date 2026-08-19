#!/usr/bin/env python3
"""Rejoue les cas de eval/cases.py et affiche un score chiffre.

Carte bonus "eval automatisee" du palier 5. Les criteres de succes vivent
en code (eval/cases.py), pas seulement en prose (eval/cases.md) : c'est
ce qui les rend rejouables sans qu'un humain ne relise chaque resultat a
la main.

ATTENTION : le mode reel fait un vrai appel a l'API Anthropic par cas
(5 cas = 5 appels factures). Ne pas lancer `make eval` sans y avoir
reflechi. `--dry-run` verifie le script et les criteres sur les
resultats DEJA observes (voir eval/simulateur.py), sans jamais toucher
au reseau ni a la cle API : c'est le mode a utiliser pour tester le
script lui-meme.

Usage :
    python eval/run.py --dry-run   # zero appel API, verifie le script
    python eval/run.py             # execution reelle, consomme des tokens
    make eval                      # raccourci pour la ligne du dessus
    make eval-dry                  # raccourci pour --dry-run
"""

import argparse
import sys
from pathlib import Path

RACINE = Path(__file__).parent.parent
sys.path.insert(0, str(RACINE))

from eval.cases import CAS  # noqa: E402


def executer_plan(intention: str, plan_id: int, origine: str) -> dict:
    """Fait tourner planifier_stream() jusqu'au bout et resume ce qui
    compte pour l'evaluation : outils appeles, actions proposees, texte
    final. N'existe qu'en mode reel (import differe, voir plus bas) :
    importer `src.planner` charge le SDK Anthropic, inutile en dry-run.
    """
    from src import db, planner

    outils_appeles = []
    reponse = ""
    erreur = None
    for evenement in planner.planifier_stream(intention, plan_id, origine):
        if evenement["type"] == "outil_appel":
            outils_appeles.append(evenement["outil"])
        elif evenement["type"] == "fin":
            reponse = evenement["reponse"]
            # _flux (src/main.py) fait ca normalement ; ce script appelle
            # planifier_stream() directement, donc sans ca la reponse et
            # le cout restaient invisibles en base (plans.reponse = NULL)
            # pour tout run reel, meme reussi.
            db.enregistrer_reponse(plan_id, evenement["reponse"], evenement)
        elif evenement["type"] == "erreur":
            # Avant ce correctif, ce cas etait ignore en silence : les
            # actions deja proposees avant la coupure restaient dans le
            # resultat, sans aucun signe que planifier_stream n'avait pas
            # conclu normalement. Exactement le piege que le sujet
            # interdit ("avaler une exception pour que ca ne plante
            # plus") : le fait ici, mais dans le sens inverse (on le
            # rend visible au lieu de le cacher).
            erreur = evenement["message"]

    actions = [
        {
            "outil": a["outil"],
            "etat": a["etat"],
            "reversible": bool(a["reversible"]),
            "depends_on": a["depends_on"],
        }
        for a in db.lister_actions_du_plan(plan_id)
    ]
    # Pour le cas d'injection de prompt : la garantie structurelle a
    # verifier n'est pas "Claude a-t-il resiste au texte", c'est "rien ne
    # s'est execute pour de vrai sans approbation humaine". Une ligne dans
    # `executions` ne peut exister qu'apres un vrai POST /execute, jamais
    # depuis planifier_stream lui-meme.
    executions = [
        dict(e) for a in db.lister_actions_du_plan(plan_id)
        for e in [db.lire_execution_par_cle(a["cle_idempotence"])] if e
    ]
    return {
        "outils": outils_appeles,
        "actions": actions,
        "reponse": reponse,
        "erreur": erreur,
        "executions": executions,
    }


def executer_cas_reel(cas: dict) -> dict:
    from src import db

    if cas.get("plan_prealable"):
        plan_id = db.creer_plan(cas["plan_prealable"])
        avant = executer_plan(cas["plan_prealable"], plan_id, "AGENT")
        resultat = executer_plan(cas["intention"], plan_id, "HUMAIN")
        resultat["nb_actions_avant"] = len(avant["actions"])
        # Une erreur sur le plan prealable compte aussi : le cas entier
        # part sur une base deja compromise, pas seulement l'ajout.
        if avant["erreur"] and not resultat["erreur"]:
            resultat["erreur"] = f"(plan prealable) {avant['erreur']}"
    else:
        plan_id = db.creer_plan(cas["intention"])
        resultat = executer_plan(cas["intention"], plan_id, "AGENT")
        resultat["nb_actions_avant"] = 0
    return resultat


def main() -> None:
    analyseur = argparse.ArgumentParser(description=__doc__)
    analyseur.add_argument(
        "--dry-run", action="store_true",
        help="Verifie le script sur des resultats deja observes, zero appel API.",
    )
    arguments = analyseur.parse_args()

    if arguments.dry_run:
        from eval.simulateur import executer_cas_simule as executer
        print("Mode --dry-run : resultats deja observes, aucun appel API.\n")
    else:
        import os
        from dotenv import load_dotenv
        load_dotenv(RACINE / ".env")
        if not os.getenv("ANTHROPIC_API_KEY"):
            print("ANTHROPIC_API_KEY absent : impossible de lancer une eval reelle.")
            print("(utilisez --dry-run pour verifier le script sans cle)")
            sys.exit(1)
        from src import db
        db.initialiser()
        executer = executer_cas_reel
        print("Mode reel : chaque cas consomme un appel a l'API Anthropic.\n")

    reussis = 0
    notes = 0
    for cas in CAS:
        resultat = executer(cas)

        # Un cas ajoute au script mais jamais encore rejoue pour de vrai
        # n'a pas de resultat simule disponible : le signaler comme tel
        # en dry-run plutot que de faire semblant avec une donnee
        # inventee (voir le principe du fichier : aucun resultat qui n'a
        # pas ete reellement observe).
        if resultat is None:
            print(f"[SKIP] {cas['id']} — {cas['nom']}")
            print("         pas encore execute pour de vrai, aucune donnee simulee")
            continue
        notes += 1

        # Une erreur cote planificateur (garde-fou MAX_TOURS epuise, panne
        # API...) est un echec en soi, avant meme de regarder les criteres
        # du cas : un plan qui n'a pas pu conclure ne prouve rien, meme
        # si les quelques actions deja proposees avant la coupure
        # satisfont par accident les criteres.
        if resultat.get("erreur"):
            print(f"[FAIL] {cas['id']} — {cas['nom']}")
            print(f"         planifier_stream n'a pas conclu : {resultat['erreur']}")
            continue

        ok, detail = cas["verifier"](resultat)
        statut = "PASS" if ok else "FAIL"
        print(f"[{statut}] {cas['id']} — {cas['nom']}")
        if not ok:
            print(f"         {detail}")
            # Diagnostic complet uniquement sur un echec : voir ce que
            # Claude a vraiment fait, pas juste le chiffre qui a fait
            # echouer le critere. Inutile de l'afficher quand ca passe.
            print(f"         outils appeles : {resultat['outils']}")
            print(f"         actions ({len(resultat['actions'])}) :")
            for a in resultat["actions"]:
                print(f"           - {a['outil']} (depends_on={a['depends_on']})")
            print(f"         reponse complete :")
            print(f"           {resultat['reponse']!r}")
        reussis += int(ok)

    ignores = len(CAS) - notes
    suffixe = f" ({ignores} non teste(s) en dry-run)" if ignores else ""
    print(f"\nScore : {reussis} / {notes}{suffixe}")
    sys.exit(0 if reussis == notes else 1)


if __name__ == "__main__":
    main()
