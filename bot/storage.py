"""
Persistance JSON simple — pour survivre aux redémarrages du bot
================================================================
Petit helper thread-safe utilisé par le starboard (mapping des messages
featurés) et le tracker de releases (historique).

Les fichiers sont stockés dans `data/` (ignoré par git).
"""
import json
import logging
import os
import threading

log = logging.getLogger("lanortrad.storage")

# Dossier de données : data/ (à la racine du projet)
DATA_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")


class JSONStore:
    """Petit stockage clé→valeur persistant dans un fichier JSON.

    Usage :
        store = JSONStore("starboard.json", default={})
        store["123"] = 456
        store.save()
    """

    def __init__(self, filename: str, default=None):
        self._lock = threading.RLock()
        self.path = os.path.join(DATA_DIR, filename)
        self.data = default if default is not None else {}
        self._load()

    def _load(self):
        os.makedirs(DATA_DIR, exist_ok=True)
        if not os.path.exists(self.path):
            return
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                self.data = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            log.warning("Lecture %s impossible (%s) — on repart d'un état vide.", self.path, e)

    def save(self):
        with self._lock:
            os.makedirs(DATA_DIR, exist_ok=True)
            tmp = self.path + ".tmp"
            try:
                with open(tmp, "w", encoding="utf-8") as f:
                    json.dump(self.data, f, ensure_ascii=False, indent=2)
                os.replace(tmp, self.path)  # écriture atomique
            except OSError as e:
                log.error("Écriture %s impossible : %s", self.path, e)

    # ─── accès dict-like ───
    def __getitem__(self, key):
        return self.data[key]

    def __setitem__(self, key, value):
        with self._lock:
            self.data[key] = value

    def __delitem__(self, key):
        with self._lock:
            del self.data[key]

    def __contains__(self, key):
        return key in self.data

    def get(self, key, default=None):
        return self.data.get(key, default)

    def pop(self, key, default=None):
        with self._lock:
            return self.data.pop(key, default)

    def setdefault(self, key, default):
        with self._lock:
            return self.data.setdefault(key, default)
