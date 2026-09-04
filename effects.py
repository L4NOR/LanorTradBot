# effects.py
# ═══════════════════════════════════════════════════════════════════════════════
# SYSTÈME D'EFFETS / POWER-UPS PERSISTANTS
# ═══════════════════════════════════════════════════════════════════════════════
# Centralise :
#   • Les streaks de mini-jeux (combo + multiplicateur d'XP)
#   • Le "featured minigame" du jour (jeu vedette x2 XP)
#   • Les power-ups du shop : streak_shield, quiz_hint, challenge_skip,
#     prediction_insurance, level_freeze
#
# Les autres modules (minigames, engagement, shop) appellent ces helpers
# au lieu d'éparpiller la logique.

import logging
import random
from datetime import datetime, timedelta
from config import DATA_DIR
from utils import load_json, save_json

logger = logging.getLogger(__name__)

EFFECTS_FILE = f"{DATA_DIR}/effects.json"

# ─── Schéma par défaut ──────────────────────────────────────────────────────────
DEFAULT_EFFECTS = {
    "users": {},          # uid -> { streak: {...}, active: {...} }
    "featured": {         # jeu vedette du jour (x2 XP)
        "date": None,
        "game": None,
        "announced": None,  # "YYYY-MM-DD:game" une fois l'annonce postée
    },
}

# ─── Multiplicateurs de streak ──────────────────────────────────────────────────
# Streak = nombre de victoires consécutives en mini-jeu (gains réels d'XP).
STREAK_TIERS = [
    (10, 2.0),  # 10 wins d'affilée → x2
    (5, 1.5),   # 5 wins d'affilée → x1.5
    (3, 1.2),   # 3 wins d'affilée → x1.2
]


def _empty_user():
    return {
        "streak": {
            "count": 0,
            "best": 0,
            "shielded": False,
        },
        "active": {
            "hint_charges": 0,
            "skip_charges": 0,
            "insurance_pred_ids": [],   # liste de pred_id assurés
            "level_freeze_until": None, # iso datetime
        },
    }


# ═══════════════════════════════════════════════════════════════════════════════
# CHARGEMENT / SAUVEGARDE
# ═══════════════════════════════════════════════════════════════════════════════

_data = None


def _load():
    global _data
    if _data is not None:
        return _data
    raw = load_json(EFFECTS_FILE) or {}
    # Merge avec defaults
    for k, v in DEFAULT_EFFECTS.items():
        raw.setdefault(k, v if not isinstance(v, dict) else dict(v))
    _data = raw
    logger.info(f"📊 Effects: {len(_data.get('users', {}))} utilisateur(s) chargé(s)")
    return _data


def _save():
    if _data is None:
        return
    save_json(EFFECTS_FILE, _data)


def get_user_effects(user_id):
    d = _load()
    uid = str(user_id)
    if uid not in d["users"]:
        d["users"][uid] = _empty_user()
    return d["users"][uid]


# ═══════════════════════════════════════════════════════════════════════════════
# STREAKS DE MINI-JEUX
# ═══════════════════════════════════════════════════════════════════════════════

def get_streak_multiplier(streak_count):
    """Retourne le multiplicateur d'XP pour un streak donné."""
    for threshold, mult in STREAK_TIERS:
        if streak_count >= threshold:
            return mult
    return 1.0


def record_minigame_result(user_id, won):
    """À appeler après chaque partie de mini-jeu (gain ou perte d'XP).

    Met à jour le streak et retourne :
        (new_streak, multiplier_to_apply, was_shielded)
    """
    eff = get_user_effects(user_id)
    streak = eff["streak"]

    was_shielded = False
    if won:
        streak["count"] += 1
        streak["best"] = max(streak["best"], streak["count"])
        mult = get_streak_multiplier(streak["count"])
    else:
        if streak.get("shielded"):
            # Le bouclier protège le streak — consommé
            streak["shielded"] = False
            was_shielded = True
            mult = get_streak_multiplier(streak["count"])
        else:
            streak["count"] = 0
            mult = 1.0

    _save()
    return streak["count"], mult, was_shielded


def reset_streak(user_id):
    eff = get_user_effects(user_id)
    eff["streak"]["count"] = 0
    _save()


def get_streak(user_id):
    return get_user_effects(user_id)["streak"]


# ═══════════════════════════════════════════════════════════════════════════════
# FEATURED MINIGAME (jeu vedette du jour, x2 XP)
# ═══════════════════════════════════════════════════════════════════════════════

# Liste des jeux qui peuvent être featured (lecture seule).
FEATURED_POOL = [
    "reaction", "unscramble", "wordle", "hangman", "chain",
    "devinette", "quoteguess", "emojirebus", "anagram",
    "guessmanga", "opening", "click", "memory",
]

FEATURED_MULTIPLIER = 2.0


def get_featured_game():
    """Retourne le nom du jeu vedette aujourd'hui (tirage déterministe par jour)."""
    d = _load()
    today = datetime.now().date().isoformat()
    feat = d.get("featured", {})

    if feat.get("date") != today or feat.get("game") not in FEATURED_POOL:
        # Tirer un nouveau jeu pour aujourd'hui
        feat = {
            "date": today,
            "game": random.choice(FEATURED_POOL),
        }
        d["featured"] = feat
        _save()
        logger.info(f"⭐ Featured minigame du jour : {feat['game']}")
    return feat["game"]


def featured_already_announced():
    """True si l'annonce du jeu vedette a déjà été postée aujourd'hui.

    Le flag est persisté dans effects.json : un redémarrage du bot (pm2,
    déploiement, crash) ne provoque donc plus de doublon d'annonce.
    """
    d = _load()
    game = get_featured_game()
    today = datetime.now().date().isoformat()
    return d["featured"].get("announced") == f"{today}:{game}"


def mark_featured_announced():
    """Marque l'annonce du jour comme postée (persistée sur disque)."""
    d = _load()
    game = get_featured_game()
    today = datetime.now().date().isoformat()
    d["featured"]["announced"] = f"{today}:{game}"
    _save()


def is_featured(game_name):
    return get_featured_game() == game_name


# ═══════════════════════════════════════════════════════════════════════════════
# APPLICATION DE L'XP DE MINI-JEU (combine streak + featured + level_freeze)
# ═══════════════════════════════════════════════════════════════════════════════

def apply_minigame_xp(user_id, base_xp, won, source="minigame"):
    """Helper unique pour gérer l'XP d'un mini-jeu.

    Combine :
      • le streak (multiplicateur dynamique selon les wins consécutives)
      • le featured (x2 si le jeu est featured, source == nom du jeu)
      • le level_freeze (annule les pertes d'XP si actif)

    Retourne (final_xp, mult_total, level_up, new_level, info_dict)
    où info_dict = {
        "streak": int,
        "streak_mult": float,
        "featured": bool,
        "shielded": bool,
        "frozen": bool,  # True si une perte a été annulée
    }
    """
    from community import add_xp as comm_add_xp

    new_streak, streak_mult, was_shielded = record_minigame_result(user_id, won)
    featured = is_featured(source)
    frozen = False

    if won:
        total_mult = streak_mult * (FEATURED_MULTIPLIER if featured else 1.0)
        final_base = int(round(base_xp * total_mult))
        final, comm_mult, level_up, new_level = comm_add_xp(user_id, final_base, source)
    else:
        # Perte d'XP — vérifier le level_freeze
        if base_xp < 0 and is_level_frozen(user_id):
            frozen = True
            final, comm_mult, level_up, new_level = 0, 1.0, False, 0
        else:
            final, comm_mult, level_up, new_level = comm_add_xp(user_id, base_xp, source)
        total_mult = 1.0

    info = {
        "streak": new_streak,
        "streak_mult": streak_mult,
        "featured": featured,
        "shielded": was_shielded,
        "frozen": frozen,
    }
    return final, total_mult, level_up, new_level, info


# ═══════════════════════════════════════════════════════════════════════════════
# POWER-UPS — STREAK SHIELD
# ═══════════════════════════════════════════════════════════════════════════════

def add_streak_shield(user_id):
    """Active la protection de streak pour la prochaine défaite."""
    eff = get_user_effects(user_id)
    eff["streak"]["shielded"] = True
    _save()


def has_streak_shield(user_id):
    return bool(get_user_effects(user_id)["streak"].get("shielded"))


# ═══════════════════════════════════════════════════════════════════════════════
# POWER-UPS — QUIZ HINT
# ═══════════════════════════════════════════════════════════════════════════════

def add_hint_charge(user_id, n=1):
    eff = get_user_effects(user_id)
    eff["active"]["hint_charges"] = int(eff["active"].get("hint_charges", 0)) + n
    _save()


def has_hint(user_id):
    return get_user_effects(user_id)["active"].get("hint_charges", 0) > 0


def consume_hint(user_id):
    eff = get_user_effects(user_id)
    n = int(eff["active"].get("hint_charges", 0))
    if n <= 0:
        return False
    eff["active"]["hint_charges"] = n - 1
    _save()
    return True


# ═══════════════════════════════════════════════════════════════════════════════
# POWER-UPS — CHALLENGE SKIP
# ═══════════════════════════════════════════════════════════════════════════════

def add_skip_charge(user_id, n=1):
    eff = get_user_effects(user_id)
    eff["active"]["skip_charges"] = int(eff["active"].get("skip_charges", 0)) + n
    _save()


def has_skip(user_id):
    return get_user_effects(user_id)["active"].get("skip_charges", 0) > 0


def consume_skip(user_id):
    eff = get_user_effects(user_id)
    n = int(eff["active"].get("skip_charges", 0))
    if n <= 0:
        return False
    eff["active"]["skip_charges"] = n - 1
    _save()
    return True


# ═══════════════════════════════════════════════════════════════════════════════
# POWER-UPS — PREDICTION INSURANCE
# ═══════════════════════════════════════════════════════════════════════════════

def add_prediction_insurance(user_id, pred_id):
    eff = get_user_effects(user_id)
    lst = eff["active"].setdefault("insurance_pred_ids", [])
    pid = str(pred_id)
    if pid not in lst:
        lst.append(pid)
        _save()
        return True
    return False


def has_prediction_insurance(user_id, pred_id):
    eff = get_user_effects(user_id)
    return str(pred_id) in eff["active"].get("insurance_pred_ids", [])


def consume_prediction_insurance(user_id, pred_id):
    eff = get_user_effects(user_id)
    lst = eff["active"].setdefault("insurance_pred_ids", [])
    pid = str(pred_id)
    if pid in lst:
        lst.remove(pid)
        _save()
        return True
    return False


# ═══════════════════════════════════════════════════════════════════════════════
# POWER-UPS — LEVEL FREEZE
# ═══════════════════════════════════════════════════════════════════════════════

def set_level_freeze(user_id, hours=24):
    eff = get_user_effects(user_id)
    until = datetime.now() + timedelta(hours=hours)
    eff["active"]["level_freeze_until"] = until.isoformat()
    _save()


def is_level_frozen(user_id):
    eff = get_user_effects(user_id)
    until_iso = eff["active"].get("level_freeze_until")
    if not until_iso:
        return False
    try:
        until = datetime.fromisoformat(until_iso)
        return datetime.now() < until
    except Exception:
        return False


def get_level_freeze_remaining(user_id):
    """Retourne le temps restant en heures (float) ou 0 si pas actif."""
    eff = get_user_effects(user_id)
    until_iso = eff["active"].get("level_freeze_until")
    if not until_iso:
        return 0.0
    try:
        until = datetime.fromisoformat(until_iso)
        delta = until - datetime.now()
        return max(0.0, delta.total_seconds() / 3600.0)
    except Exception:
        return 0.0


# ═══════════════════════════════════════════════════════════════════════════════
# INIT
# ═══════════════════════════════════════════════════════════════════════════════

# Charge le fichier au premier import — évite les surprises au runtime.
_load()
