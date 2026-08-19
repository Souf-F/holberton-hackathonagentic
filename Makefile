.PHONY: eval eval-dry test

# Carte bonus "eval automatisee" du palier 5. eval-dry ne coute rien
# (zero appel API, rejoue des resultats deja observes) ; eval consomme un
# vrai appel Anthropic par cas dans eval/cases.py, a lancer sciemment.
eval:
	.venv/bin/python3 eval/run.py

eval-dry:
	.venv/bin/python3 eval/run.py --dry-run

# Tests automatises, aucun appel API (voir tests/).
test:
	.venv/bin/python3 -m pytest tests/ -v
