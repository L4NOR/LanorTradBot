"""
Configuration — LanorTradBot
==============================
Un seul fichier de réglages. Trois principes :

  • **Aucun ID à coller à la main** : salons et rôles sont résolus par leur
    nom au démarrage (voir resolver.py), puis mis en cache dans data/.
  • **Le site fait autorité** : le catalogue, le planning et l'atelier sont
    lus sur le site, jamais ressaisis ici.
  • **Le secret vit dans l'environnement** : DISCORD_TOKEN, jamais en dur.
"""
import os
import sys


# ═══════════════════════════════════════════════════════
# 🔑 TOKEN & SERVEUR
# ═══════════════════════════════════════════════════════

def _load_dotenv():
    """Charge un .env à la racine du projet, sans dépendance externe."""
    path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_dotenv()

TOKEN = os.environ.get("DISCORD_TOKEN")
if not TOKEN:
    print("ERREUR : DISCORD_TOKEN introuvable.")
    print("  -> renseigne-le dans .env (voir .env.example) ou dans l'environnement.")
    sys.exit(1)

from bot.servers import select as _select_server   # noqa: E402

SERVER = _select_server()
GUILD_ID = SERVER["id"]
SERVER_KEY = SERVER["key"]
PROFILE = "info"                 # ce bot ne sert que le serveur informatif
IS_INFO_SERVER = True


# ═══════════════════════════════════════════════════════
# 🌐 LE SITE — source de vérité
# ═══════════════════════════════════════════════════════

SITE_URL = os.environ.get("SITE_URL", "https://lanortrad.com")

SITE = {
    "accueil":   SITE_URL,
    "catalogue": f"{SITE_URL}/catalogue",
    "planning":  f"{SITE_URL}/planning",
    "forum":     f"{SITE_URL}/forum",
    "equipe":    f"{SITE_URL}/equipe",
}

DISCORD_INVITE = os.environ.get("DISCORD_INVITE") or None


# ═══════════════════════════════════════════════════════
# 📚 CATALOGUE (aligné sur le site)
# ═══════════════════════════════════════════════════════

MANGAS = {
    "tougen-anki":      {"emoji": "🗡️", "name": "Tougen Anki",
                         "role_key": "ping_tougen", "slug": "tougen-anki"},
    "ao-no-exorcist":   {"emoji": "🩸", "name": "Ao No Exorcist",
                         "role_key": "ping_ao", "slug": "ao-no-exorcist"},
    "tokyo-underworld": {"emoji": "🏙️", "name": "Tokyo Underworld",
                         "role_key": "ping_tokyo", "slug": "tokyo-underworld"},
    "catenaccio":       {"emoji": "⚽", "name": "Catenaccio",
                         "role_key": "ping_cat", "slug": "catenaccio"},
    "satsudou":         {"emoji": "🔪", "name": "Satsudou",
                         "role_key": "ping_sat", "slug": "satsudou"},
    "oneshot":          {"emoji": "📜", "name": "Oneshots",
                         "role_key": "ping_one", "slug": "catalogue"},
}

ONESHOTS = [
    ("Countdown", "🌑"), ("Gestation of Kalavinka", "🦚"), ("In the White", "🤍"),
    ("Sake to Sakana", "🍶"), ("Second Coming", "✝️"),
]


def manga_url(manga_key: str) -> str:
    """Fiche de la série sur le site."""
    slug = MANGAS.get(manga_key, {}).get("slug", "catalogue")
    return SITE["catalogue"] if slug == "catalogue" else f"{SITE_URL}/manga/{slug}"


# ═══════════════════════════════════════════════════════
# 🔒 RÔLES DE SÉRIES À CONSERVER
# ═══════════════════════════════════════════════════════
# Déjà portés par les membres : jamais recréés, jamais supprimés.
# Le bot les rattache aux séries par leur NOM au démarrage.

LANORTRAD_SERIES_ROLE_IDS = [
    1465027919951958220,
    1465027907968831541,
    1465027916999032976,
    1465027911235928155,
    1465027914050437184,
]

KEEP_ROLE_IDS = (
    LANORTRAD_SERIES_ROLE_IDS if SERVER.get("keep_series_roles") else []
)


# ═══════════════════════════════════════════════════════
# 📂 SALONS & RÔLES (résolus automatiquement)
# ═══════════════════════════════════════════════════════
# Rien à remplir : resolver.py les trouve par leur nom au démarrage et met
# le résultat en cache dans data/resolved_ids.json. Un ID écrit ici à la
# main reste prioritaire tant qu'il pointe vers quelque chose d'existant.

CHANNELS = {}
ROLES = {}

_resolved = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "resolved_ids.json")
try:
    import json as _json
    with open(_resolved, encoding="utf-8") as _f:
        _cache = _json.load(_f)
    CHANNELS.update(_cache.get("channels", {}))
    ROLES.update(_cache.get("roles", {}))
except (FileNotFoundError, ValueError, OSError):
    pass


# ═══════════════════════════════════════════════════════
# 🎨 COULEURS
# ═══════════════════════════════════════════════════════

COLOR_NEUTRAL = 0xB30000   # rouge sang LanorTrad
COLOR_FR      = 0x0055A4
COLOR_EN      = 0xC8102E
COLOR_SUCCESS = 0x2ECC71
COLOR_ERROR   = 0xE74C3C
COLOR_WARNING = 0xF1C40F


# ═══════════════════════════════════════════════════════
# 📰 SORTIES
# ═══════════════════════════════════════════════════════

RELEASE_HISTORY_MAX = 200
RELEASE_FORUM_MODE  = "auto"    # poste en forum si le salon cible en est un
RELEASE_FORUM_KEY   = None      # ex : "releases_forum" pour tout centraliser

ANNOUNCE_DEFAULT_PING = "ping_announcements"


# ═══════════════════════════════════════════════════════
# 🔄 SYNCHRO AVEC LE SITE
# ═══════════════════════════════════════════════════════

SITE_SYNC_ENABLED  = True
SITE_SYNC_INTERVAL = 15         # minutes entre deux vérifications

SITE_BOARD_PUBLIC  = "planning"   # calendrier + atelier, côté lecteurs
SITE_BOARD_STAFF   = "pipeline"   # version détaillée, côté équipe

SITE_ANNOUNCE_STEPS = True        # avancements d'étape, dans le salon équipe
SITE_AUTO_RELEASE   = True        # publie les nouveaux chapitres tout seul
SITE_STEPS_CHANNEL  = "workshop_chat"

SITE_INCIDENT_ALERTS  = True      # prévient dans #incidents si le site tombe
SITE_INCIDENT_STRIKES = 3
SITE_INCIDENT_CHANNEL = "incidents"

SITE_STALE_DAYS = 21              # relance hebdo sur les chapitres qui dorment


# ═══════════════════════════════════════════════════════
# 🎫 TICKETS
# ═══════════════════════════════════════════════════════

TICKET_TYPES = [
    ("question",    "Question",    "🆘", "Une question sur le site ou une série."),
    ("correction",  "Correction",  "✏️", "Une faute, une page manquante, un lien mort."),
    ("partenariat", "Partenariat", "🤝", "Proposition de partenariat ou de collab."),
    ("signalement", "Signalement", "🚨", "Signaler un membre ou un problème."),
]

TICKET_PING_ROLE_ID = None        # rôle staff pingé à l'ouverture (None = aucun)


# ═══════════════════════════════════════════════════════
# 📋 RECRUTEMENT (postes annoncés sur la page équipe du site)
# ═══════════════════════════════════════════════════════

RECRUIT_POSTS = [
    ("trad",   "Traducteur·rice", "💬", "translator",
     "JP vers FR ou AN vers FR, que ça sonne français"),
    ("clean",  "Cleaner",         "🧽", "cleaner",
     "Nettoyage des pages, aucune expérience requise"),
    ("edit",   "Éditeur·rice",    "✍️", "typesetter",
     "Texte dans les bulles, polices, onomatopées"),
    ("qcheck", "Q-check",         "🔍", "qc",
     "Dernier rempart : fautes, sens, cohérence"),
    ("pages",  "Pages / RAW",     "📥", "raw_provider",
     "Trouver et remettre au propre les pages japonaises"),
]

RECRUIT_TEST_FORUM = "tests_techniques"
RECRUIT_FALLBACK   = "staff_chat"
RECRUIT_STAFF_ROLE = "moderator"
RECRUIT_TEST_DELAY = 72           # heures données au candidat pour son test
RECRUIT_OPEN       = True         # False = candidatures fermées


# ═══════════════════════════════════════════════════════
# 🛡️ AUTOMOD & ANTI-RAID
# ═══════════════════════════════════════════════════════

AUTOMOD_ENABLED       = True
AUTOMOD_BLOCK_INVITES = True
AUTOMOD_MAX_MENTIONS  = 5
AUTOMOD_DELETE_DELAY  = 8

RAID_ENABLED        = True
RAID_JOIN_THRESHOLD = 6           # arrivées...
RAID_JOIN_WINDOW    = 12          # ...en X secondes -> mode raid
RAID_AUTO_LOCKDOWN  = True
RAID_LOCKDOWN_MIN   = 15

RAID_MIN_ACCOUNT_AGE_DAYS = 7
RAID_KICK_NEW_ACCOUNTS    = True
RAID_LOCK_CHANNELS = ["tickets", "recrutement"]
RAID_ALERT_ROLE    = "moderator"

RAID_SPAM_MAX_MSG     = 6
RAID_SPAM_WINDOW      = 6
RAID_SPAM_DUPLICATES  = 4
RAID_SPAM_TIMEOUT_MIN = 10


# ═══════════════════════════════════════════════════════
# ⚠️ AVERTISSEMENTS · LOGS · SAUVEGARDES
# ═══════════════════════════════════════════════════════

WARN_DM_USER = True

MSG_CACHE_ENABLED = True
MSG_CACHE_DAYS    = 14
MSG_CACHE_MAX_LEN = 3000

BACKUP_KEEP = 10
