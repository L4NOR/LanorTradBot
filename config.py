# config.py
import os
import discord
from dotenv import load_dotenv

# Charger les variables d'environnement depuis .env
load_dotenv()

# Token du bot (à définir dans un fichier .env)
TOKEN = os.getenv("DISCORD_TOKEN")

# Préfixe de commande
PREFIX = os.getenv("COMMAND_PREFIX", "!")

# Intents Discord (permissions)
INTENTS = discord.Intents.default()
INTENTS.message_content = True  # Nécessaire pour lire le contenu des messages
INTENTS.members = True  # Nécessaire pour les événements liés aux membres
INTENTS.reactions = True  # Nécessaire pour les réactions
INTENTS.guilds = True   # Nécessaire pour les événements liés aux guildes
INTENTS.invites = True  # Nécessaire pour gérer les invitations

# IDs des canaux
CHANNELS = {
    "rules": 1326211105332265001,
    "welcome": 1326211276732502056,
    "general": 1326230396903362759,
    "boost": 1326212624504848394,
    "chapter_announcements": 1326213946188890142,
    "partenaires_channel": 1326357401099702393,
    "mod_contact": 1332088539076104192,
    "sorties": 1326213946188890142
}

# IDs des messages
MESSAGES = {
    "rules": 1333072612527439915
}

# IDs des rôles
ROLES = {
    "member": 1465027926054535324,
    "access": 1465027850120986967,
    "booster": 1335403910113923162,
    "catenaccio": 1465027907968831541,
    "partenaires_ping": 1465027864318447658
}

# Port du serveur web
PORT = int(os.getenv('PORT', 8080))

# Couleurs pour les embeds
COLORS = {
    "success": 0x2ECC71,  # Vert
    "error": 0xE74C3C,    # Rouge
    "info": 0x3498DB,     # Bleu
    "warning": 0xF1C40F,  # Jaune
    "boost": 0x9B59B6     # Violet
}

# Autres configurations

EMBED_FOOTER = "Bot Discord"
