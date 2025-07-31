# task_storage.py
import json
import os

TASKS_FILE = "tasks.json"

def load_tasks():
    """Charge les tâches sauvegardées depuis le fichier JSON."""
    if not os.path.exists(TASKS_FILE):
        return {}

    try:
        with open(TASKS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}

def save_tasks(tasks):
    """Sauvegarde les tâches actuelles dans le fichier JSON."""
    try:
        with open(TASKS_FILE, "w", encoding="utf-8") as f:
            json.dump(tasks, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"Erreur lors de la sauvegarde des tâches : {e}")
