"""
Lanceur de LanorTradBot
=========================
Point d'entree PM2 :

    pm2 start run_v2.py --name LanorTradBot --interpreter ./venv/bin/python

Le code du bot est dans `bot/`. Ce lanceur tolere aussi l'ancienne
disposition (`v2/bot/`), pour qu'un deplacement du code ne mette jamais
la production hors ligne.
"""
import os
import sys

RACINE = os.path.dirname(os.path.abspath(__file__))

for candidat in (RACINE, os.path.join(RACINE, "v2")):
    if os.path.isdir(os.path.join(candidat, "bot")):
        sys.path.insert(0, candidat)
        break
else:
    sys.exit("ERREUR : dossier `bot/` introuvable — le code du bot est absent.")

from bot.main import run  # noqa: E402  (apres l'ajustement de sys.path)

if __name__ == "__main__":
    run()
