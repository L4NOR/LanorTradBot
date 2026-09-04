"""
Lanceur de LanorTradBot v2
============================
Point d'entree PM2 pour le bot v2, dont le code vit dans `v2/bot/`.

    pm2 start run_v2.py --name LanorTradBot --interpreter ./venv/bin/python

Pourquoi un fichier separe plutot que main.py : `main.py` appartient a la v1
et reste suivi par git. Le remplacer marcherait jusqu'au premier `git pull`,
qui le reecrirait et remettrait la v1 en ligne sans prevenir.

Le dossier `v2/` est place en TETE de sys.path : meme s'il traine un ancien
dossier `bot/` a la racine, c'est bien `v2/bot/` qui est importe.
"""
import os
import sys

RACINE = os.path.dirname(os.path.abspath(__file__))
V2 = os.path.join(RACINE, "v2")

if not os.path.isdir(os.path.join(V2, "bot")):
    sys.exit(f"ERREUR : {V2}/bot introuvable — le code de la v2 est absent.")

sys.path.insert(0, V2)

from bot.main import run  # noqa: E402  (apres l'ajustement de sys.path)

if __name__ == "__main__":
    run()
