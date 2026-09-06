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

DOTENV_TROUVES = []


def _load_dotenv():
    """Charge le premier .env trouvé, sans dépendance externe.

    Le code peut vivre à la racine du dépôt (bot/) ou dans un sous-dossier
    (v2/bot/) : on regarde donc plusieurs emplacements plutôt que d'en
    supposer un seul. Les variables déjà présentes dans l'environnement
    gardent toujours la priorité.
    """
    ici = os.path.dirname(os.path.abspath(__file__))          # .../bot
    parent = os.path.dirname(ici)                             # .../v2  ou racine
    candidats = [
        os.path.join(parent, ".env"),
        os.path.join(os.path.dirname(parent), ".env"),        # racine du dépôt
        os.path.join(os.getcwd(), ".env"),
    ]
    vus = set()
    for path in candidats:
        path = os.path.normpath(path)
        if path in vus or not os.path.exists(path):
            continue
        vus.add(path)
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                os.environ.setdefault(
                    key.strip(), value.strip().strip('"').strip("'"))
        DOTENV_TROUVES.append(path)


_load_dotenv()

TOKEN = os.environ.get("DISCORD_TOKEN")
if not TOKEN:
    print("ERREUR : DISCORD_TOKEN introuvable.")
    if DOTENV_TROUVES:
        print("  Fichiers .env lus : " + ", ".join(DOTENV_TROUVES))
        print("  -> aucun n'y declare DISCORD_TOKEN=...")
    else:
        print("  Aucun fichier .env trouve a cote du code ni a la racine du depot.")
    print("  -> ajoute une ligne DISCORD_TOKEN=... dans .env (voir .env.example)")
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
    1465027919951958220,   # Ao No Exorcist
    1465027907968831541,   # Catenaccio
    1465027916999032976,   # Satsudou
    1465027911235928155,   # Tougen Anki
    1465027914050437184,   # Tokyo Underworld
]

KEEP_ROLE_IDS = (
    LANORTRAD_SERIES_ROLE_IDS if SERVER.get("keep_series_roles") else []
)


# ═══════════════════════════════════════════════════════
# 📂 SALONS & RÔLES — IDs du serveur officiel
# ═══════════════════════════════════════════════════════
# Ces IDs font AUTORITÉ : tant qu'ils pointent vers quelque chose d'existant,
# le bot ne cherche rien par nom. Renommer un salon ou un rôle ne casse donc
# plus rien. Ce qui n'est pas listé ici est résolu par nom (voir resolver.py).

CHANNELS = {
    # ─── Pages de référence (cog content · /publier) ───
    "welcome":     1545537941781086268,   # 👋 bienvenue
    "rules":       1326211105332265001,   # 📜 règles
    "faq":         1545537964853952525,   # ❓ faq
    "site_links":  1545538010672795668,   # 🔗 le-site
    "site_forum":  1545538018155171940,   # 💬 forum-du-site
    "recrutement": 1545538050883584020,   # 📋 recrutement
}

ROLES = {
    # ─── Séries (rôles historiques, portés par les membres) ───
    "ping_ao":     1465027919951958220,   # Ao No Exorcist
    "ping_cat":    1465027907968831541,   # Catenaccio
    "ping_sat":    1465027916999032976,   # Satsudou
    "ping_tougen": 1465027911235928155,   # Tougen Anki
    "ping_tokyo":  1465027914050437184,   # Tokyo Underworld
    "ping_one":    1545537911309471916,   # Oneshots

    # ─── Équipe ───
    "founder":     1545537840300167168,   # Fondateur
    "moderator":   1545537850400055357,   # Modération

    # ─── Métiers (vocabulaire du site) ───
    "raw_provider": 1545537857823842305,  # Pages
    "cleaner":      1545537865495224390,  # Clean
    "translator":   1545537873737027747,  # Traduction
    "typesetter":   1545537881760731206,  # Édition
    "qc":           1545537889415335986,  # Q-check
    "trial":        1545537896717623306,  # En test

    # ─── Base & notifications ───
    "member":             1545537904095264788,   # Lecteur
    "ping_all":           1545537918561554462,   # Toutes sorties
    "ping_announcements": 1545537926321152150,   # Annonces
}

# Le cache écrit par le resolver complète ce qui n'est pas listé ci-dessus,
# sans jamais écraser un ID explicite.
_resolved = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "resolved_ids.json")
try:
    import json as _json
    with open(_resolved, encoding="utf-8") as _f:
        _cache = _json.load(_f)
    for _k, _v in _cache.get("channels", {}).items():
        CHANNELS.setdefault(_k, _v)
    for _k, _v in _cache.get("roles", {}).items():
        ROLES.setdefault(_k, _v)
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

# Roles donnes automatiquement a chaque arrivee, et attribuables en
# masse aux membres deja presents via /roles_base (cles de ROLES).
BASE_ROLES = ["member"]

# Salons ou le nouveau membre est mentionne a son arrivee, dans cet ordre.
# Chaque salon a son message : voir MESSAGES_ARRIVEE dans cogs/welcome.py.
WELCOME_PING_CHANNELS = ["welcome", "rules", "faq"]

# Minutes avant que ces messages s'effacent tout seuls (0 = ils restent).
# Utile pour que les salons de reference ne se remplissent pas d'arrivees.
WELCOME_PING_DELETE_AFTER = 0


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

# ── Dépôt du site, pour que /atelier_pousser écrive js/data/atelier.js ──
# Tout se met dans .env, jamais ici : le jeton est un secret.
#   SITE_REPO=proprietaire/depot
#   SITE_REPO_BRANCH=main
#   SITE_REPO_TOKEN=ghp_...   (droit « Contents: write » sur ce dépôt)
SITE_REPO = os.environ.get("SITE_REPO", "").strip()
SITE_REPO_BRANCH = os.environ.get("SITE_REPO_BRANCH", "main").strip()
SITE_REPO_TOKEN = (os.environ.get("SITE_REPO_TOKEN")
                   or os.environ.get("GITHUB_TOKEN") or "").strip()


# ═══════════════════════════════════════════════════════
# 📥 ATELIER — dépôt des pages RAW (cog atelier)
# ═══════════════════════════════════════════════════════

# Salon où vivent les fiches de chapitre. Repli automatique sur
# raws_archive puis workshop_chat si la clé n'existe pas sur le serveur.
ATELIER_CHANNEL = "raws_archive"

# À chaque étape validée, une ligne dans le salon ping le métier suivant.
ATELIER_ANNONCE_ETAPE = True

# Qui valide quoi. Les clés sont les étapes du site (bot/site.py · STEPS),
# les valeurs des clés de ROLES. Une étape absente d'ici n'est ouverte
# qu'aux rôles passe-partout ci-dessous.
ATELIER_ETAPE_ROLES = {
    "pages":  ("raw_provider",),
    "clean":  ("cleaner",),
    "trad":   ("translator",),
    "edit":   ("typesetter",),
    "qcheck": ("qc",),
    "sortie": ("founder", "moderator"),
}

# Peuvent valider n'importe quelle étape (et débloquer une fiche coincée).
# Ajoute "trial" ici si tu veux que les personnes en test participent
# avant d'avoir reçu leur rôle métier.
ATELIER_ROLES_JOKER = ("founder", "moderator")

# ── Relance douce ─────────────────────────────────────────────────
# Quelqu'un prend une étape puis disparaît : le bot lui écrit en privé,
# jamais dans un salon. Personne ne se fait reprendre en public.
ATELIER_RELANCE = True
ATELIER_RELANCE_JOURS = 5          # jours sans bouger avant le premier rappel
ATELIER_RELANCE_INTERVALLE = 12    # heures entre deux passages de la boucle
ATELIER_RELANCE_MAX = 2            # au-delà, on arrête d'écrire

# ── Suivi public de fabrication ──────────────────────────────────
# Les lecteurs qui prennent le rôle « 🔔 Suivi de fabrication » voient
# les chapitres avancer. Aucune note interne, aucun nom d'équipier.
ATELIER_SUIVI_PUBLIC = True
ATELIER_SUIVI_CHANNEL = "notifications"
ATELIER_SUIVI_ROLE = "ping_workshop"
ATELIER_SUIVI_ETAPES = ("clean", "trad", "edit", "qcheck", "sortie")

# ── Statut du bot ──────────────────────────────────────────────
# Le bot raconte ce qui se passe au lieu d'afficher toujours la même ligne.
PRESENCE_ENABLED = True
PRESENCE_INTERVALLE = 10           # minutes entre deux changements


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

# Salon où le bot dépose la sauvegarde hebdomadaire.
# ID explicite : le resolver ne le remplacera jamais par un salon
# trouvé par son nom. None = repli sur bot_logs puis staff_chat.
BACKUP_CHANNEL_ID = 1545538121729310892

# La boucle hebdomadaire repart à zéro à chaque démarrage du bot : sans
# ce garde-fou, dix `pm2 restart` dans la journée = dix sauvegardes.
# Nombre de jours minimum entre deux sauvegardes automatiques.
BACKUP_MIN_DAYS = 6
