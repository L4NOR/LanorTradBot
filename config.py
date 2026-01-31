# config.py
# ═══════════════════════════════════════════════════════════════════════════════
# FICHIER DE CONFIGURATION CENTRALISÉ - TOUS LES IDS ET CONSTANTES
# ═══════════════════════════════════════════════════════════════════════════════

import os
import discord
from dotenv import load_dotenv

load_dotenv()

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION DE BASE
# ═══════════════════════════════════════════════════════════════════════════════

TOKEN = os.getenv("DISCORD_TOKEN")
PREFIX = os.getenv("COMMAND_PREFIX", "!")
PORT = int(os.getenv('PORT', 8080))

# ═══════════════════════════════════════════════════════════════════════════════
# INTENTS DISCORD
# ═══════════════════════════════════════════════════════════════════════════════

INTENTS = discord.Intents.default()
INTENTS.message_content = True
INTENTS.members = True
INTENTS.reactions = True
INTENTS.guilds = True
INTENTS.invites = True

# ═══════════════════════════════════════════════════════════════════════════════
# UTILISATEURS SPÉCIAUX
# ═══════════════════════════════════════════════════════════════════════════════

TARGET_USER_ID = 608234789564186644  # ID pour recevoir les exports de données

# ═══════════════════════════════════════════════════════════════════════════════
# RÔLES ADMIN (utilisés pour les permissions des commandes)
# ═══════════════════════════════════════════════════════════════════════════════

ADMIN_ROLES = [
    1465027983445331990,
    1465027980974620833,
    1465027978324086846
]

# ═══════════════════════════════════════════════════════════════════════════════
# IDS DES RÔLES GÉNÉRAUX
# ═══════════════════════════════════════════════════════════════════════════════

ROLES = {
    # Rôles de base
    "member": 1465027926054535324,
    "access": 1465027850120986967,
    "booster": 1335403910113923162,
    
    # Rôles manga (séparés pour clarté)
    "catenaccio": 1465027907968831541,
    "satsudou": 1465027916999032976,
    "ao_no_exorcist": 1465027919951958220,
    "tokyo_underworld": 1465027914050437184,
    "tougen_anki": 1465027911235928155,
    
    # Rôles de notification
    "partenaires_ping": 1465027864318447658,
    "annonces": 1465027871339708439,
    "evenements": 1465027869196423239,
    "giveaway": 1465027866826772785,
    "twittos": 1465027861365919756,
    "tiktok": 1465027858853527644,
    "spoilers": 1465027856508649543,
    
    # Rôles communautaires
    "artiste": 1465027899466846260,
    "collectionneurs": 1465027897336004638,
    "musique": 1465027894668689642,
    "photographie": 1465027891942129714,
    "jeux_video": 1465027882253287607,
    
    # Rôles parents (catégories)
    "manga_parent": 1465027922833440833,
    "notifications_parent": 1465027873751433520,
    "community_parent": 1465027902419636296,
}

# Mapping nom manga -> ID rôle (pour faciliter l'utilisation)
MANGA_ROLES = {
    "Catenaccio": 1465027907968831541,
    "Satsudou": 1465027916999032976,
    "Ao No Exorcist": 1465027919951958220,
    "Tokyo Underworld": 1465027914050437184,
    "Tougen Anki": 1465027911235928155,
}

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION DES RÔLES PAR CATÉGORIE (pour role_selector)
# ═══════════════════════════════════════════════════════════════════════════════

ROLE_CATEGORIES = {
    "manga": {
        "title": "📚 MANGAS",
        "description": "Recevez des notifications pour vos mangas préférés !",
        "color": 0x3498DB,
        "emoji": "📚",
        "parent_role_id": ROLES["manga_parent"],
        "roles": [
            {"name": "Ao No Exorcist", "emoji": "🔥", "id": ROLES["ao_no_exorcist"]},
            {"name": "Satsudou", "emoji": "⚔️", "id": ROLES["satsudou"]},
            {"name": "Tokyo Underworld", "emoji": "🏙️", "id": ROLES["tokyo_underworld"]},
            {"name": "Tougen Anki", "emoji": "👹", "id": ROLES["tougen_anki"]},
            {"name": "Catenaccio", "emoji": "⚽", "id": ROLES["catenaccio"]},
        ]
    },
    "notifications": {
        "title": "🔔 NOTIFICATIONS",
        "description": "Choisissez les notifications que vous souhaitez recevoir",
        "color": 0xE67E22,
        "emoji": "🔔",
        "parent_role_id": ROLES["notifications_parent"],
        "roles": [
            {"name": "Annonces", "emoji": "📢", "id": ROLES["annonces"]},
            {"name": "Événements", "emoji": "🎉", "id": ROLES["evenements"]},
            {"name": "Giveaway", "emoji": "🎁", "id": ROLES["giveaway"]},
            {"name": "Partenaires", "emoji": "💛", "id": ROLES["partenaires_ping"]},
            {"name": "Twittos", "emoji": "🐦", "id": ROLES["twittos"]},
            {"name": "Tiktok", "emoji": "🎵", "id": ROLES["tiktok"]},
            {"name": "Spoilers", "emoji": "👀", "id": ROLES["spoilers"]},
        ]
    },
    "community": {
        "title": "🎨 COMMUNAUTÉ",
        "description": "Partagez vos passions avec la communauté !",
        "color": 0x2ECC71,
        "emoji": "🎨",
        "parent_role_id": ROLES["community_parent"],
        "roles": [
            {"name": "Artiste", "emoji": "🎨", "id": ROLES["artiste"]},
            {"name": "Collectionneurs", "emoji": "📚", "id": ROLES["collectionneurs"]},
            {"name": "Musique", "emoji": "🎧", "id": ROLES["musique"]},
            {"name": "Photographie", "emoji": "📷", "id": ROLES["photographie"]},
            {"name": "Jeux vidéo", "emoji": "🎮", "id": ROLES["jeux_video"]},
        ]
    }
}

# ═══════════════════════════════════════════════════════════════════════════════
# IDS DES CANAUX
# ═══════════════════════════════════════════════════════════════════════════════

CHANNELS = {
    "rules": 1326211105332265001,
    "welcome": 1326211276732502056,
    "general": 1326230396903362759,
    "boost": 1326212624504848394,
    "chapter_announcements": 1326213946188890142,
    "partenaires_channel": 1326357401099702393,
    "mod_contact": 1332088539076104192,
    "sorties": 1326213946188890142,
    "test": 1330221808753840159,
    "roles": 1326212401036529665,
}

MANGA_CHANNELS = {
    "Tougen Anki": 1330144191816142941,
    "Tokyo Underworld": 1330143657264943266,
    "Satsudou": 1330142974646026371,
    "Ao No Exorcist": 1329589897920512020,
    "Catenaccio": 1330182024832614541,
}

# ═══════════════════════════════════════════════════════════════════════════════
# IDS DES MESSAGES
# ═══════════════════════════════════════════════════════════════════════════════

MESSAGES = {
    "rules": 1333072612527439915,
    "roles": 1465801132390482145,  # Message de sélection de rôles (dm_reminder)
}

# ═══════════════════════════════════════════════════════════════════════════════
# COULEURS
# ═══════════════════════════════════════════════════════════════════════════════

COLORS = {
    "success": 0x2ECC71,
    "error": 0xE74C3C,
    "info": 0x3498DB,
    "warning": 0xF1C40F,
    "boost": 0x9B59B6,
    "giveaway": 0xff6b6b,
}

RARITY_COLORS = {
    "common": 0x9e9e9e,
    "uncommon": 0x4caf50,
    "rare": 0x2196f3,
    "epic": 0x9c27b0,
    "legendary": 0xff9800,
}

# ═══════════════════════════════════════════════════════════════════════════════
# EMOJIS
# ═══════════════════════════════════════════════════════════════════════════════

MANGA_EMOJIS = {
    "Ao No Exorcist": "👹",
    "Satsudou": "🩸",
    "Tougen Anki": "😈",
    "Catenaccio": "⚽",
    "Tokyo Underworld": "🗼",
}

TASK_EMOJIS = {
    "clean": "🧹",
    "trad": "🌍",
    "traduire": "🌍",
    "check": "✅",
    "qcheck": "✅",
    "edit": "✏️",
}

RATING_EMOJIS = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣"]
REACTION_EMOJIS = ["🔥", "😭", "😱", "🤯", "❤️", "😂", "💀"]

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION GIVEAWAY
# ═══════════════════════════════════════════════════════════════════════════════

GIVEAWAY_EMOJI = "🎉"
GIVEAWAY_COLOR = 0xff6b6b

GIVEAWAY_ROLES = {
    "manager_role": None,  # Rôle qui peut créer des giveaways
    "bonus_role": None,    # Rôle avec entrées bonus (+1 entrée)
    "vip_role": None,      # Rôle VIP avec double entrées
}

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION SHOP
# ═══════════════════════════════════════════════════════════════════════════════

SHOP_ROLES = {
    "lecteurs_reguliers": 1465027929170776200,   # Lecteurs Réguliers
    "lecteurs_vip": 1465027932350054522,          # Lecteurs VIP
    "lecteurs_supreme": 1465027934807916695,      # Lecteurs Suprême
}

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION COMMUNAUTAIRE (POINTS) - SYSTÈME AUTOMATIQUE
# ═══════════════════════════════════════════════════════════════════════════════

POINTS = {
    # Activité de messages (passif)
    "message_min": 1,
    "message_max": 3,
    "message_cooldown": 60,  # secondes
    
    # Bonus quotidien
    "daily_min": 20,
    "daily_max": 50,
    "streak_bonus": 5,      # par jour consécutif
    "streak_max_bonus": 50, # bonus max
    
    # Réactions aux annonces
    "chapter_reaction": 10,
    
    # Vocal
    "voice_per_15min": 5,
    
    # Ancienneté (hebdomadaire)
    "seniority_base": 50,
    "seniority_max": 200,
    
    # Mini-jeux
    "trivia_easy": 20,
    "trivia_medium": 50,
    "trivia_hard": 100,
    "guess_correct": 30,
}

# Salons autorisés pour gagner des points par message
POINTS_ALLOWED_CHANNELS = [
    CHANNELS["general"],
    CHANNELS["tougen_anki"],
    CHANNELS["ao_no_exorcist"],
    CHANNELS["satsudou"],
    CHANNELS["tokyo_underworld"],
    CHANNELS["catenaccio"],
    CHANNELS["off_topic"],
]

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION DM REMINDER
# ═══════════════════════════════════════════════════════════════════════════════

DM_REMINDER_CONFIG = {
    "role_message_id": MESSAGES["roles"],
    "role_channel_id": None,  # Sera auto-détecté
    "send_hour": 12,          # Heure d'envoi des DMs (midi)
    "timezone": "Europe/Paris",
}

# ═══════════════════════════════════════════════════════════════════════════════
# AUTRES
# ═══════════════════════════════════════════════════════════════════════════════

EMBED_FOOTER = "Bot Discord LanorTrad"
PING_COOLDOWN_SECONDS = 300

# ═══════════════════════════════════════════════════════════════════════════════
# CHEMINS DES FICHIERS DE DONNÉES
# ═══════════════════════════════════════════════════════════════════════════════

DATA_DIR = "data"

DATA_FILES = {
    # Workflow
    "tasks": f"{DATA_DIR}/etat_taches.json",
    "tasks_meta": f"{DATA_DIR}/etat_taches_meta.json",
    "rappels": f"{DATA_DIR}/rappels_tasks.json",
    "rappels_meta": f"{DATA_DIR}/rappels_tasks_meta.json",
    
    # Giveaway
    "giveaways": f"{DATA_DIR}/giveaways.json",
    "invites": f"{DATA_DIR}/invites_tracker.json",
    
    # Community
    "reviews": f"{DATA_DIR}/reviews.json",
    "theories": f"{DATA_DIR}/theories.json",
    "chapters": f"{DATA_DIR}/chapters_community.json",
    "user_stats": f"{DATA_DIR}/user_stats.json",
    
    # Achievements
    "badges": f"{DATA_DIR}/user_badges.json",
    "badges_config": f"{DATA_DIR}/badges_config.json",
    
    # Shop
    "shop_inventory": f"{DATA_DIR}/shop_inventory.json",
    "shop_items": f"{DATA_DIR}/shop_items.json",
    "purchases": f"{DATA_DIR}/purchases.json",
    "lottery": f"{DATA_DIR}/lottery.json",
    
    # DM Reminder
    "dm_reminder": f"{DATA_DIR}/dm_reminder_notified.json",
    "dm_reminder_meta": f"{DATA_DIR}/dm_reminder_meta.json",
}