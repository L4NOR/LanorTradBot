# commands.py
import discord
from discord.ext import commands
from datetime import datetime
from config import CHANNELS, ROLES, COLORS, ADMIN_ROLES, MANGA_CHANNELS, MANGA_ROLES, TASK_ROLES, TASK_EMOJIS
import logging
import asyncio
import json
import os
import random

bot_instance = None

TASKS_FILE = "data/etat_taches.json"
META_FILE = "data/etat_taches_meta.json"
os.makedirs("data", exist_ok=True)

# Dictionnaire pour stocker les chapitres planifiés
chapitres_planifies = []

# Ajout d'une structure globale pour stocker l'état des tâches
etat_taches_global = {}

# Messages aléatoires pour les tâches individuelles
MESSAGES_ALEATOIRES = [
    "Hé, psst... Si j'étais vous, j'irais voir l'avancée des chapitres ! 👀",
    "Une petite mise à jour vient d'être faite... Allez jeter un œil ! 🔍",
    "Quelque chose bouge du côté des chapitres... 🤔",
    "Tiens tiens, une tâche vient d'être complétée ! Curieux ? Utilisez !avancee 📊",
    "Psst... Il se passe des choses intéressantes ! Allez voir l'avancée ! 🎯",
    "Une nouvelle mise à jour ! N'hésitez pas à checker l'avancée des projets ! ✨",
    "Oh oh, du progrès ! Vous devriez aller voir ça... 👁️",
    "Quelqu'un a bossé dur ! Allez voir l'état d'avancement ! 💪"
]

# Charger les tâches depuis le fichier JSON au démarrage
def charger_etat_taches():
    global etat_taches_global
    if os.path.exists(TASKS_FILE):
        with open(TASKS_FILE, "r", encoding="utf-8") as f:
            etat_taches_global = json.load(f)
    else:
        etat_taches_global = {}

# Sauvegarder les tâches dans le fichier JSON
def sauvegarder_etat_taches():
    try:
        with open(TASKS_FILE, "w", encoding="utf-8") as f:
            json.dump(etat_taches_global, f, ensure_ascii=False, indent=4)
        
        meta = {
            "last_saved": datetime.utcnow().isoformat() + "Z",
            "task_count": len(etat_taches_global)
        }
        with open(META_FILE, "w", encoding="utf-8") as mf:
            json.dump(meta, mf, ensure_ascii=False, indent=4)
    except Exception as e:
        logging.error(f"Erreur lors de la sauvegarde des tâches: {e}")

# MANGA_CHANNELS et MANGA_ROLES sont importés depuis config.py

def est_chapitre_complet(tasks):
    """Vérifie si toutes les tâches (clean, trad, check, edit) sont terminées"""
    taches_requises = ["clean", "trad", "check", "edit"]
    return all(tasks.get(tache) == "✅ Terminé" for tache in taches_requises)

def normaliser_manga_name(name):
    """Normalise le nom du manga pour la comparaison"""
    return name.lower().strip()

def extraire_manga_chapitre(key):
    """Extrait le nom du manga et le numéro de chapitre d'une clé"""
    if "_" not in key:
        return None, None
    parts = key.rsplit("_", 1)
    if len(parts) != 2:
        return None, None
    manga_name = parts[0].strip()
    chapter_str = parts[1].strip()
    if chapter_str.isdigit():
        return manga_name, int(chapter_str)
    return manga_name, None


# ==================== CONFIGURATION DU MENU HELP ====================

HELP_CATEGORIES = {
    "general": {
        "emoji": "🎮",
        "name": "Général",
        "description": "Commandes de base accessibles à tous",
        "color": 0x3498DB,
        "commands": [
            {"name": "help", "usage": "!help [commande]", "desc": "Affiche ce menu d'aide interactif"},
            {"name": "info", "usage": "!info", "desc": "Informations sur le serveur"},
            {"name": "userinfo", "usage": "!userinfo [@membre]", "desc": "Détails du profil d'un membre"},
            {"name": "ping", "usage": "!ping", "desc": "Vérifie la latence du bot"},
            {"name": "avancee", "usage": "!avancee", "desc": "Voir l'avancée des chapitres manga"},
        ]
    },
    "community": {
        "emoji": "🌟",
        "name": "Communauté",
        "description": "Niveaux, XP et mini-jeux",
        "color": 0x9B59B6,
        "commands": [
            {"name": "xp", "usage": "!xp [@membre]", "desc": "Voir votre XP et niveau"},
            {"name": "profile", "usage": "!profile [@membre]", "desc": "Afficher votre profil"},
            {"name": "leaderboard", "usage": "!leaderboard [page]", "desc": "Classement XP du serveur"},
            {"name": "daily", "usage": "!daily", "desc": "Récupérer votre bonus quotidien"},
            {"name": "trivia", "usage": "!trivia [difficulté]", "desc": "Jouer au quiz"},
            {"name": "guess", "usage": "!guess", "desc": "Jeu de devinette"},
        ]
    },
    "badges": {
        "emoji": "🏆",
        "name": "Badges",
        "description": "Système de badges et récompenses",
        "color": 0xF1C40F,
        "commands": [
            {"name": "badges", "usage": "!badges [@membre]", "desc": "Voir les badges d'un membre"},
            {"name": "all_badges", "usage": "!all_badges", "desc": "Liste tous les badges disponibles"},
            {"name": "badge_info", "usage": "!badge_info <nom>", "desc": "Détails d'un badge spécifique"},
            {"name": "display_badge", "usage": "!display_badge <nom>", "desc": "Afficher un badge (max 3)"},
            {"name": "remove_badge", "usage": "!remove_badge <nom>", "desc": "Retirer un badge affiché"},
            {"name": "leaderboard_badges", "usage": "!leaderboard_badges", "desc": "Top collectionneurs de badges"},
        ]
    },
    "shop": {
        "emoji": "🛒",
        "name": "Shop",
        "description": "Boutique et système de points",
        "color": 0x2ECC71,
        "commands": [
            {"name": "shop", "usage": "!shop [catégorie]", "desc": "Parcourir la boutique"},
            {"name": "buy", "usage": "!buy <item>", "desc": "Acheter un item"},
            {"name": "inventory", "usage": "!inventory [@membre]", "desc": "Voir votre inventaire"},
            {"name": "use", "usage": "!use <item>", "desc": "Utiliser un item consommable"},
        ]
    },
    "giveaway": {
        "emoji": "🎁",
        "name": "Giveaways",
        "description": "Concours et système d'invitations",
        "color": 0xE91E63,
        "commands": [
            {"name": "my_invites", "usage": "!my_invites", "desc": "Voir vos stats d'invitations"},
            {"name": "leaderboard_invites", "usage": "!leaderboard_invites", "desc": "Classement des invitations"},
            {"name": "list_giveaways", "usage": "!list_giveaways", "desc": "Liste des giveaways actifs"},
            {"name": "giveaway_info", "usage": "!giveaway_info <id>", "desc": "Détails d'un giveaway"},
        ]
    },
    "admin_tasks": {
        "emoji": "📋",
        "name": "Tâches",
        "description": "Gestion des tâches de traduction",
        "color": 0xE74C3C,
        "admin": True,
        "commands": [
            {"name": "task", "usage": "!task <action> <manga> <chap...>", "desc": "MAJ tâche (clean/trad/check/edit)"},
            {"name": "task_status", "usage": "!task_status <manga> <chap>", "desc": "État des tâches d'un chapitre"},
            {"name": "task_all", "usage": "!task_all [manga]", "desc": "Toutes les tâches (optionnel: filtrer par manga)"},
            {"name": "delete_task", "usage": "!delete_task <manga> <chap>", "desc": "Supprimer tâches d'un chapitre"},
            {"name": "fix_tasks", "usage": "!fix_tasks", "desc": "Normaliser les clés des tâches"},
            {"name": "actualiser", "usage": "!actualiser", "desc": "Sauvegarder/exporter les données"},
        ]
    },
    "admin_rappels": {
        "emoji": "⏰",
        "name": "Rappels",
        "description": "Gestion des rappels de deadlines",
        "color": 0xFF9800,
        "admin": True,
        "commands": [
            {"name": "add_rappel", "usage": "!add_rappel", "desc": "Créer un rappel (interactif)"},
            {"name": "list_rappels", "usage": "!list_rappels", "desc": "Liste des rappels actifs"},
            {"name": "delete_rappel", "usage": "!delete_rappel <id>", "desc": "Supprimer un rappel"},
            {"name": "actualiser_rappels", "usage": "!actualiser_rappels <action>", "desc": "Save/reload rappels"},
            {"name": "test_rappel", "usage": "!test_rappel", "desc": "Tester l'envoi des rappels"},
        ]
    },
    "admin_giveaway": {
        "emoji": "🎉",
        "name": "Admin Giveaways",
        "description": "Gestion des giveaways",
        "color": 0x9C27B0,
        "admin": True,
        "commands": [
            {"name": "create_giveaway", "usage": "!create_giveaway", "desc": "Créer un giveaway (interactif)"},
            {"name": "giveaway", "usage": "!giveaway <durée> <gagnants> <prix>", "desc": "Giveaway rapide"},
            {"name": "end_giveaway", "usage": "!end_giveaway <id>", "desc": "Terminer un giveaway"},
            {"name": "delete_giveaway", "usage": "!delete_giveaway <id>", "desc": "Supprimer un giveaway"},
            {"name": "reroll", "usage": "!reroll <id> [nb]", "desc": "Retirer nouveaux gagnants"},
            {"name": "giveaway_participants", "usage": "!giveaway_participants <id>", "desc": "Liste participants"},
            {"name": "add_invites", "usage": "!add_invites @user <nb>", "desc": "Ajouter invitations"},
            {"name": "remove_invites", "usage": "!remove_invites @user <nb>", "desc": "Retirer invitations"},
            {"name": "reset_user_invites", "usage": "!reset_user_invites @user", "desc": "Reset invitations"},
            {"name": "server_invite_stats", "usage": "!server_invite_stats", "desc": "Stats globales invitations"},
        ]
    },
    "admin_community": {
        "emoji": "👥",
        "name": "Admin Communauté",
        "description": "Gestion communautaire",
        "color": 0x00BCD4,
        "admin": True,
        "commands": [
            {"name": "newchapter", "usage": "!newchapter <msg_id> <manga> <chap>", "desc": "Lier chapitre au système"},
            {"name": "stats", "usage": "!stats", "desc": "Statistiques du serveur"},
            {"name": "give_badge", "usage": "!give_badge @user <badge>", "desc": "Donner un badge"},
            {"name": "announce_chapter", "usage": "!announce_chapter", "desc": "Annoncer chapitre (interactif)"},
            {"name": "test_announce", "usage": "!test_announce", "desc": "Tester une annonce"},
        ]
    },
    "admin_shop": {
        "emoji": "💰",
        "name": "Admin Shop",
        "description": "Gestion de la boutique",
        "color": 0x4CAF50,
        "admin": True,
        "commands": [
            {"name": "shop_add", "usage": "!shop_add", "desc": "Ajouter un item (interactif)"},
            {"name": "shop_remove", "usage": "!shop_remove <item>", "desc": "Retirer un item"},
            {"name": "give_item", "usage": "!give_item @user <item>", "desc": "Donner un item"},
            {"name": "set_points", "usage": "!set_points @user <montant>", "desc": "Définir points d'un membre"},
            {"name": "add_points_admin", "usage": "!add_points_admin @user <nb>", "desc": "Ajouter/retirer points"},
        ]
    },
    "admin_mod": {
        "emoji": "🛡️",
        "name": "Modération",
        "description": "Commandes de modération",
        "color": 0x607D8B,
        "admin": True,
        "commands": [
            {"name": "clear", "usage": "!clear <nombre>", "desc": "Supprimer des messages"},
            {"name": "kick", "usage": "!kick @user [raison]", "desc": "Expulser un membre"},
            {"name": "ban", "usage": "!ban @user [raison]", "desc": "Bannir un membre"},
            {"name": "unban", "usage": "!unban nom#tag", "desc": "Débannir un membre"},
            {"name": "warn", "usage": "!warn @user [raison]", "desc": "Avertir un membre"},
            {"name": "bulk_role", "usage": "!bulk_role @role @user1 ID2...", "desc": "Assigner un rôle à plusieurs personnes"},
            {"name": "bulk_remove_role", "usage": "!bulk_remove_role @role @user1 ID2...", "desc": "Retirer un rôle à plusieurs personnes"},
            {"name": "multi_bulk_role", "usage": "!multi_bulk_role @role1 @role2 - @user1 ID2...", "desc": "Assigner plusieurs rôles à plusieurs personnes"},
            {"name": "multi_bulk_remove_role", "usage": "!multi_bulk_remove_role @role1 @role2 - @user1 ID2...", "desc": "Retirer plusieurs rôles à plusieurs personnes"},
            {"name": "bulk_role_channel", "usage": "!bulk_role_channel @role ID_CANAL", "desc": "Assigner un rôle à tous les membres d'un canal"},
            {"name": "multi_bulk_role_channel", "usage": "!multi_bulk_role_channel @role1 @role2 - ID_CANAL", "desc": "Assigner plusieurs rôles aux membres d'un canal"},
            {"name": "list_member_ids", "usage": "!list_member_ids ID_CIBLE", "desc": "Lister tous les IDs des membres d'un canal/fil/catégorie"},
        ]
    },
    "admin_data": {
        "emoji": "💾",
        "name": "Données",
        "description": "Gestion centralisée des données",
        "color": 0x795548,
        "admin": True,
        "commands": [
            {"name": "data", "usage": "!data [action] [cible]", "desc": "Gestionnaire données"},
            {"name": "data_list", "usage": "!data_list", "desc": "Liste modules de données"},
            {"name": "backup", "usage": "!backup", "desc": "Sauvegarde + export complet"},
        ]
    },
    "polls": {
        "emoji": "📊",
        "name": "Sondages",
        "description": "Système de sondages interactifs",
        "color": 0x3498DB,
        "commands": [
            {"name": "poll", "usage": "!poll Question | Opt1 | Opt2", "desc": "Créer un sondage (rapide ou interactif)"},
            {"name": "polls", "usage": "!polls", "desc": "Voir les sondages actifs"},
            {"name": "poll_results", "usage": "!poll_results <id>", "desc": "Résultats détaillés d'un sondage"},
        ]
    },
    "stats_serveur": {
        "emoji": "📈",
        "name": "Statistiques",
        "description": "Statistiques du serveur et contributeurs",
        "color": 0x1ABC9C,
        "commands": [
            {"name": "serverstats", "usage": "!serverstats", "desc": "Dashboard complet du serveur (paginé)"},
            {"name": "membercount", "usage": "!membercount", "desc": "Nombre de membres rapide"},
            {"name": "topcontrib", "usage": "!topcontrib", "desc": "Top contributeurs du projet"},
        ]
    },
    "admin_polls": {
        "emoji": "📊",
        "name": "Admin Sondages",
        "description": "Gestion des sondages",
        "color": 0x9B59B6,
        "admin": True,
        "commands": [
            {"name": "poll_close", "usage": "!poll_close <id>", "desc": "Fermer un sondage"},
            {"name": "poll_delete", "usage": "!poll_delete <id>", "desc": "Supprimer un sondage"},
        ]
    },
    "admin_tickets": {
        "emoji": "📩",
        "name": "Tickets",
        "description": "Système de tickets et candidatures",
        "color": 0xE67E22,
        "admin": True,
        "commands": [
            {"name": "setup_tickets", "usage": "!setup_tickets", "desc": "Configurer le panneau tickets/candidatures"},
            {"name": "close_ticket", "usage": "!close_ticket", "desc": "Fermer un ticket"},
            {"name": "audit_test", "usage": "!audit_test", "desc": "Tester les logs d'audit"},
        ]
    },
    "planning": {
        "emoji": "📅",
        "name": "Planning",
        "description": "Planning des sorties de chapitres",
        "color": 0x1E90FF,
        "commands": [
            {"name": "planning", "usage": "!planning [mois] [année]", "desc": "Voir le calendrier des sorties"},
            {"name": "next_release", "usage": "!next_release", "desc": "Prochaine sortie de chapitre"},
        ]
    },
    "admin_planning": {
        "emoji": "📅",
        "name": "Admin Planning",
        "description": "Gestion du planning des sorties",
        "color": 0x1E90FF,
        "admin": True,
        "commands": [
            {"name": "planning_add", "usage": "!planning_add [manga chap(s) AAAA-MM-JJ]", "desc": "Ajouter une/plusieurs sorties (ex: 220-222)"},
            {"name": "planning_status", "usage": "!planning_status <manga> <chap> <statut>", "desc": "Changer le statut d'une sortie"},
            {"name": "planning_date", "usage": "!planning_date <manga> <chap> <JJ/MM/AAAA>", "desc": "Modifier la date d'une sortie"},
            {"name": "planning_teaser", "usage": "!planning_teaser <id> <texte>", "desc": "Ajouter/modifier un teaser spoil (caché)"},
            {"name": "planning_remove", "usage": "!planning_remove <manga> <chap>", "desc": "Retirer une sortie du planning"},
            {"name": "planning_post", "usage": "!planning_post", "desc": "Poster/actualiser le planning dans le channel"},
            {"name": "planning_full", "usage": "!planning_full", "desc": "Planning complet (toutes les sorties)"},
        ]
    },
}


def setup(bot):
    charger_etat_taches()
    global bot_instance
    bot_instance = bot
    bot.remove_command('help')
    
    # ==================== NOUVELLE COMMANDE HELP ====================
    
    @bot.command()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def help(ctx, *, command_name: str = None):
        """Affiche le menu d'aide interactif"""
        admin_roles = ADMIN_ROLES
        user_roles = [role.id for role in ctx.author.roles]
        is_admin = any(role in user_roles for role in admin_roles)
        
        # Si une commande spécifique est demandée
        if command_name:
            await show_command_help(ctx, command_name, is_admin)
            return
        
        # Menu principal
        embed = create_main_help_embed(ctx, is_admin)
        message = await ctx.send(embed=embed)
        
        # Ajouter les réactions
        categories_to_show = get_available_categories(is_admin)
        
        await message.add_reaction("🏠")
        for cat_key in categories_to_show:
            cat = HELP_CATEGORIES[cat_key]
            await message.add_reaction(cat["emoji"])
        await message.add_reaction("❌")
        
        def check(reaction, user):
            return user == ctx.author and reaction.message.id == message.id
        
        while True:
            try:
                reaction, user = await bot.wait_for("reaction_add", timeout=120, check=check)
                emoji = str(reaction.emoji)
                
                await message.remove_reaction(reaction, user)
                
                if emoji == "❌":
                    await message.delete()
                    return
                
                if emoji == "🏠":
                    await message.edit(embed=create_main_help_embed(ctx, is_admin))
                    continue
                
                for cat_key, cat in HELP_CATEGORIES.items():
                    if cat["emoji"] == emoji:
                        if cat.get("admin") and not is_admin:
                            continue
                        await message.edit(embed=create_category_embed(ctx, cat_key, cat))
                        break
                
            except asyncio.TimeoutError:
                try:
                    await message.clear_reactions()
                    timeout_embed = create_main_help_embed(ctx, is_admin)
                    timeout_embed.set_footer(text="⏰ Menu expiré • !help pour réouvrir")
                    await message.edit(embed=timeout_embed)
                except:
                    pass
                break
    
    def get_available_categories(is_admin):
        """Retourne les catégories disponibles"""
        categories = []
        for cat_key, cat in HELP_CATEGORIES.items():
            if cat.get("admin") and not is_admin:
                continue
            categories.append(cat_key)
        return categories
    
    def create_main_help_embed(ctx, is_admin):
        """Crée l'embed principal du menu d'aide"""
        embed = discord.Embed(color=0x5865F2, timestamp=datetime.now())
        
        embed.set_author(
            name="📚 Centre d'Aide • LanorTrad Bot",
            icon_url=ctx.guild.icon.url if ctx.guild.icon else None
        )
        
        # Header avec ASCII art simplifié
        description = (
            "```ansi\n"
            "\u001b[1;36m╔═══════════════════════════════════════╗\u001b[0m\n"
            "\u001b[1;36m║\u001b[0m   \u001b[1;37mBienvenue dans le menu d'aide !\u001b[0m   \u001b[1;36m║\u001b[0m\n"
            "\u001b[1;36m╚═══════════════════════════════════════╝\u001b[0m\n"
            "```\n"
            "🔹 Cliquez sur un **emoji** pour voir une catégorie\n"
            "🔹 Utilisez `!help <commande>` pour des détails\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        )
        embed.description = description
        
        # Catégories publiques
        public_cats = ""
        for cat_key in ["general", "community", "badges", "shop", "giveaway", "planning"]:
            cat = HELP_CATEGORIES[cat_key]
            cmd_count = len(cat["commands"])
            public_cats += f"{cat['emoji']} **{cat['name']}** › `{cmd_count}` cmds\n"
        
        embed.add_field(
            name="🌐 __Commandes Publiques__",
            value=public_cats,
            inline=True
        )
        
        # Catégories admin
        if is_admin:
            admin_cats_1 = ""
            admin_cats_2 = ""
            admin_list = [k for k, v in HELP_CATEGORIES.items() if v.get("admin")]
            
            for i, cat_key in enumerate(admin_list):
                cat = HELP_CATEGORIES[cat_key]
                cmd_count = len(cat["commands"])
                line = f"{cat['emoji']} **{cat['name']}** › `{cmd_count}`\n"
                if i < len(admin_list) // 2 + 1:
                    admin_cats_1 += line
                else:
                    admin_cats_2 += line
            
            embed.add_field(
                name="🔧 __Administration__",
                value=admin_cats_1,
                inline=True
            )
            if admin_cats_2:
                embed.add_field(
                    name="​",  # Caractère invisible
                    value=admin_cats_2,
                    inline=True
                )
        
        # Stats
        total_cmds = sum(len(cat["commands"]) for cat in HELP_CATEGORIES.values() 
                        if not cat.get("admin") or is_admin)
        total_public = sum(len(cat["commands"]) for cat in HELP_CATEGORIES.values() 
                          if not cat.get("admin"))
        
        embed.add_field(
            name="━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            value=(
                f"📊 **{total_cmds}** commandes disponibles "
                f"({total_public} publiques)\n"
                f"🏠 `Accueil` • ❌ `Fermer`"
            ),
            inline=False
        )
        
        embed.set_footer(
            text=f"Demandé par {ctx.author.name} │ Préfixe: !",
            icon_url=ctx.author.avatar.url if ctx.author.avatar else None
        )
        
        if ctx.guild.icon:
            embed.set_thumbnail(url=ctx.guild.icon.url)
        
        return embed
    
    def create_category_embed(ctx, cat_key, cat):
        """Crée l'embed d'une catégorie"""
        embed = discord.Embed(color=cat["color"], timestamp=datetime.now())
        
        embed.set_author(
            name=f"{cat['emoji']} {cat['name']}",
            icon_url=ctx.guild.icon.url if ctx.guild.icon else None
        )
        
        if cat.get("admin"):
            embed.description = f"🔒 *Réservé aux administrateurs*\n\n{cat['description']}\n"
        else:
            embed.description = f"*{cat['description']}*\n"
        
        # Construire la liste des commandes
        cmd_list = ""
        for cmd in cat["commands"]:
            cmd_list += f"**`{cmd['usage']}`**\n"
            cmd_list += f"└ {cmd['desc']}\n\n"
        
        # Split si trop long
        if len(cmd_list) > 1024:
            mid = len(cat["commands"]) // 2
            
            first = ""
            for cmd in cat["commands"][:mid]:
                first += f"**`{cmd['usage']}`**\n└ {cmd['desc']}\n\n"
            
            second = ""
            for cmd in cat["commands"][mid:]:
                second += f"**`{cmd['usage']}`**\n└ {cmd['desc']}\n\n"
            
            embed.add_field(name="📖 Commandes", value=first.strip(), inline=False)
            embed.add_field(name="​", value=second.strip(), inline=False)
        else:
            embed.add_field(name="📖 Commandes", value=cmd_list.strip(), inline=False)
        
        embed.add_field(
            name="━━━━━━━━━━━━━━━━━━━━",
            value="🏠 `Accueil` • ❌ `Fermer`\n`!help <cmd>` pour plus de détails",
            inline=False
        )
        
        embed.set_footer(
            text=f"{len(cat['commands'])} commande(s) │ {ctx.author.name}",
            icon_url=ctx.author.avatar.url if ctx.author.avatar else None
        )
        
        return embed
    
    async def show_command_help(ctx, command_name, is_admin):
        """Aide détaillée d'une commande"""
        command_name = command_name.lower().strip().lstrip('!')
        
        found_cmd = None
        found_cat = None
        
        for cat_key, cat in HELP_CATEGORIES.items():
            if cat.get("admin") and not is_admin:
                continue
            for cmd in cat["commands"]:
                if cmd["name"].lower() == command_name:
                    found_cmd = cmd
                    found_cat = cat
                    break
            if found_cmd:
                break
        
        if not found_cmd:
            embed = discord.Embed(
                title="❌ Commande Introuvable",
                description=(
                    f"La commande `{command_name}` n'existe pas "
                    f"ou vous n'y avez pas accès.\n\n"
                    f"Utilisez `!help` pour voir toutes les commandes."
                ),
                color=discord.Color.red()
            )
            await ctx.send(embed=embed, delete_after=10)
            return
        
        embed = discord.Embed(
            title=f"📖 Commande: !{found_cmd['name']}",
            color=found_cat["color"],
            timestamp=datetime.now()
        )
        
        embed.add_field(
            name="📝 Description",
            value=found_cmd["desc"],
            inline=False
        )
        embed.add_field(
            name="⌨️ Syntaxe",
            value=f"```{found_cmd['usage']}```",
            inline=False
        )
        embed.add_field(
            name="📁 Catégorie",
            value=f"{found_cat['emoji']} {found_cat['name']}",
            inline=True
        )
        embed.add_field(
            name="🔐 Permission",
            value="🔒 Admin" if found_cat.get("admin") else "🔓 Tous",
            inline=True
        )
        
        embed.set_footer(
            text=f"Demandé par {ctx.author.name}",
            icon_url=ctx.author.avatar.url if ctx.author.avatar else None
        )
        
        await ctx.send(embed=embed)
    
    # ==================== AUTRES COMMANDES ====================
    
    # ==================== THEME COLORS ====================
    THEME_COLORS = {
        "success": 0x2ECC71,
        "error": 0xE74C3C,
        "warning": 0xF39C12,
        "info": 0x3498DB,
        "moderation": 0x9B59B6,
        "tasks": 0x1ABC9C,
        "manga": 0xE91E63,
        "gold": 0xF1C40F,
        "server": 0x5865F2
    }
    
    @bot.command()
    @commands.has_permissions(manage_messages=True)
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def clear(ctx, amount: int):
        """Supprime un nombre spécifié de messages"""
        if amount <= 0:
            embed = discord.Embed(
                description="```ansi\n\u001b[1;31m╔═══════════════════════════════════════╗\u001b[0m\n\u001b[1;31m║\u001b[0m       \u001b[1;37m❌ Nombre Invalide\u001b[0m           \u001b[1;31m║\u001b[0m\n\u001b[1;31m╚═══════════════════════════════════════╝\u001b[0m\n```\nLe nombre de messages doit être supérieur à **0**.",
                color=THEME_COLORS["error"]
            )
            await ctx.send(embed=embed, delete_after=5)
            return
        
        deleted = await ctx.channel.purge(limit=amount + 1)
        deleted_count = len(deleted) - 1
        
        embed = discord.Embed(
            color=THEME_COLORS["moderation"],
            timestamp=datetime.now()
        )
        embed.description = (
            "```ansi\n"
            "\u001b[1;35m╔═══════════════════════════════════════╗\u001b[0m\n"
            "\u001b[1;35m║\u001b[0m       \u001b[1;37m🗑️ Messages Supprimés\u001b[0m        \u001b[1;35m║\u001b[0m\n"
            "\u001b[1;35m╚═══════════════════════════════════════╝\u001b[0m\n"
            "```"
        )
        embed.add_field(name="📊 Quantité", value=f"**{deleted_count}** messages", inline=True)
        embed.add_field(name="📍 Salon", value=ctx.channel.mention, inline=True)
        embed.add_field(name="👤 Modérateur", value=ctx.author.mention, inline=True)
        embed.set_footer(text=f"Action par {ctx.author.name}", icon_url=ctx.author.avatar.url if ctx.author.avatar else None)
        
        await ctx.send(embed=embed, delete_after=5)
    
    @bot.command()
    @commands.has_permissions(kick_members=True)
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def kick(ctx, member: discord.Member, *, reason=None):
        """Expulse un membre du serveur"""
        await member.kick(reason=reason)
        
        embed = discord.Embed(
            color=THEME_COLORS["warning"],
            timestamp=datetime.now()
        )
        embed.description = (
            "```ansi\n"
            "\u001b[1;33m╔═══════════════════════════════════════╗\u001b[0m\n"
            "\u001b[1;33m║\u001b[0m       \u001b[1;37m👢 Membre Expulsé\u001b[0m            \u001b[1;33m║\u001b[0m\n"
            "\u001b[1;33m╚═══════════════════════════════════════╝\u001b[0m\n"
            "```"
        )
        embed.set_thumbnail(url=member.avatar.url if member.avatar else None)
        embed.add_field(name="👤 Membre", value=f"{member.mention}\n`{member.name}#{member.discriminator}`", inline=True)
        embed.add_field(name="🆔 ID", value=f"`{member.id}`", inline=True)
        embed.add_field(name="👮 Modérateur", value=ctx.author.mention, inline=True)
        embed.add_field(name="📝 Raison", value=reason or "*Non spécifiée*", inline=False)
        embed.add_field(name="ℹ️ Note", value="Le membre peut rejoindre à nouveau avec une invitation.", inline=False)
        embed.set_footer(text=f"Kick effectué par {ctx.author.name}", icon_url=ctx.author.avatar.url if ctx.author.avatar else None)
        
        await ctx.send(embed=embed)
    
    @bot.command()
    @commands.has_permissions(ban_members=True)
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def ban(ctx, member: discord.Member, *, reason=None):
        """Bannit un membre du serveur"""
        await member.ban(reason=reason)
        
        embed = discord.Embed(
            color=THEME_COLORS["error"],
            timestamp=datetime.now()
        )
        embed.description = (
            "```ansi\n"
            "\u001b[1;31m╔═══════════════════════════════════════╗\u001b[0m\n"
            "\u001b[1;31m║\u001b[0m       \u001b[1;37m🔨 Membre Banni\u001b[0m              \u001b[1;31m║\u001b[0m\n"
            "\u001b[1;31m╚═══════════════════════════════════════╝\u001b[0m\n"
            "```"
        )
        embed.set_thumbnail(url=member.avatar.url if member.avatar else None)
        embed.add_field(name="👤 Membre", value=f"{member.mention}\n`{member.name}#{member.discriminator}`", inline=True)
        embed.add_field(name="🆔 ID", value=f"`{member.id}`", inline=True)
        embed.add_field(name="👮 Modérateur", value=ctx.author.mention, inline=True)
        embed.add_field(name="📝 Raison", value=reason or "*Non spécifiée*", inline=False)
        embed.add_field(name="⚠️ Attention", value="Ce bannissement est **permanent**. Utilisez `!unban` pour annuler.", inline=False)
        embed.set_footer(text=f"Ban effectué par {ctx.author.name}", icon_url=ctx.author.avatar.url if ctx.author.avatar else None)
        
        await ctx.send(embed=embed)
    
    @bot.command()
    @commands.has_permissions(ban_members=True)
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def unban(ctx, *, member):
        """Débannit un membre du serveur"""
        banned_users = [entry async for entry in ctx.guild.bans()]
        member_name, member_discriminator = member.split('#')
        
        for ban_entry in banned_users:
            user = ban_entry.user
            if (user.name, user.discriminator) == (member_name, member_discriminator):
                await ctx.guild.unban(user)
                
                embed = discord.Embed(
                    color=THEME_COLORS["success"],
                    timestamp=datetime.now()
                )
                embed.description = (
                    "```ansi\n"
                    "\u001b[1;32m╔═══════════════════════════════════════╗\u001b[0m\n"
                    "\u001b[1;32m║\u001b[0m       \u001b[1;37m✅ Membre Débanni\u001b[0m            \u001b[1;32m║\u001b[0m\n"
                    "\u001b[1;32m╚═══════════════════════════════════════╝\u001b[0m\n"
                    "```"
                )
                embed.add_field(name="👤 Membre", value=f"**{user.name}**#{user.discriminator}", inline=True)
                embed.add_field(name="🆔 ID", value=f"`{user.id}`", inline=True)
                embed.add_field(name="👮 Modérateur", value=ctx.author.mention, inline=True)
                embed.add_field(name="ℹ️ Note", value="Le membre peut maintenant rejoindre à nouveau le serveur.", inline=False)
                embed.set_footer(text=f"Unban effectué par {ctx.author.name}", icon_url=ctx.author.avatar.url if ctx.author.avatar else None)
                
                await ctx.send(embed=embed)
                return
        
        # Membre non trouvé
        embed = discord.Embed(
            color=THEME_COLORS["error"],
            description=(
                "```ansi\n"
                "\u001b[1;31m╔═══════════════════════════════════════╗\u001b[0m\n"
                "\u001b[1;31m║\u001b[0m       \u001b[1;37m❌ Membre Non Trouvé\u001b[0m         \u001b[1;31m║\u001b[0m\n"
                "\u001b[1;31m╚═══════════════════════════════════════╝\u001b[0m\n"
                "```\n"
                f"Aucun utilisateur banni avec le nom `{member}` n'a été trouvé."
            )
        )
        await ctx.send(embed=embed)
    
    @bot.command()
    @commands.has_permissions(kick_members=True)
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def warn(ctx, member: discord.Member, *, reason=None):
        """Avertit un membre"""
        embed = discord.Embed(
            color=THEME_COLORS["warning"],
            timestamp=datetime.now()
        )
        embed.description = (
            "```ansi\n"
            "\u001b[1;33m╔═══════════════════════════════════════╗\u001b[0m\n"
            "\u001b[1;33m║\u001b[0m       \u001b[1;37m⚠️ Avertissement\u001b[0m             \u001b[1;33m║\u001b[0m\n"
            "\u001b[1;33m╚═══════════════════════════════════════╝\u001b[0m\n"
            "```"
        )
        embed.set_thumbnail(url=member.avatar.url if member.avatar else None)
        embed.add_field(name="👤 Membre averti", value=f"{member.mention}\n`{member.name}`", inline=True)
        embed.add_field(name="👮 Par", value=ctx.author.mention, inline=True)
        embed.add_field(name="📝 Raison", value=reason or "*Non spécifiée*", inline=False)
        embed.add_field(name="📋 Note", value="Cet avertissement a été enregistré.", inline=False)
        embed.set_footer(text=f"Warn effectué par {ctx.author.name}", icon_url=ctx.author.avatar.url if ctx.author.avatar else None)
        
        await ctx.send(embed=embed)
        
        # Optionnel : envoyer un MP au membre
        try:
            dm_embed = discord.Embed(
                title="⚠️ Vous avez reçu un avertissement",
                description=f"Vous avez reçu un avertissement sur **{ctx.guild.name}**.",
                color=THEME_COLORS["warning"]
            )
            dm_embed.add_field(name="📝 Raison", value=reason or "*Non spécifiée*", inline=False)
            dm_embed.set_footer(text="Veuillez respecter les règles du serveur.")
            await member.send(embed=dm_embed)
        except discord.Forbidden:
            pass  # MPs désactivés
    
    @bot.command()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def info(ctx):
        """Affiche les informations du serveur"""
        guild = ctx.guild
        
        # Compter les types de membres
        humans = sum(1 for m in guild.members if not m.bot)
        bots = sum(1 for m in guild.members if m.bot)
        online = sum(1 for m in guild.members if m.status != discord.Status.offline)
        
        # Compter les types de salons
        text_channels = len(guild.text_channels)
        voice_channels = len(guild.voice_channels)
        categories = len(guild.categories)
        
        embed = discord.Embed(
            color=THEME_COLORS["server"],
            timestamp=datetime.now()
        )
        embed.description = (
            "```ansi\n"
            "\u001b[1;34m╔═══════════════════════════════════════╗\u001b[0m\n"
            "\u001b[1;34m║\u001b[0m       \u001b[1;37m📊 Informations Serveur\u001b[0m       \u001b[1;34m║\u001b[0m\n"
            "\u001b[1;34m╚═══════════════════════════════════════╝\u001b[0m\n"
            "```"
        )
        
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
        if guild.banner:
            embed.set_image(url=guild.banner.url)
        
        embed.add_field(name="🏷️ Nom", value=f"**{guild.name}**", inline=True)
        embed.add_field(name="🆔 ID", value=f"`{guild.id}`", inline=True)
        embed.add_field(name="👑 Propriétaire", value=guild.owner.mention, inline=True)
        
        embed.add_field(name="━━━━━━━━━━━━━━━━━━━━", value="** **", inline=False)
        
        embed.add_field(
            name="👥 Membres",
            value=f"Total: **{guild.member_count}**\n🧑 Humains: `{humans}`\n🤖 Bots: `{bots}`\n🟢 En ligne: `{online}`",
            inline=True
        )
        embed.add_field(
            name="💬 Salons",
            value=f"📁 Catégories: `{categories}`\n💬 Textuels: `{text_channels}`\n🔊 Vocaux: `{voice_channels}`",
            inline=True
        )
        embed.add_field(
            name="✨ Autres",
            value=f"🏷️ Rôles: `{len(guild.roles)}`\n😀 Emojis: `{len(guild.emojis)}`\n🚀 Boost: Niv. `{guild.premium_tier}`",
            inline=True
        )
        
        embed.add_field(name="━━━━━━━━━━━━━━━━━━━━", value="** **", inline=False)
        
        embed.add_field(name="📅 Créé le", value=f"<t:{int(guild.created_at.timestamp())}:D>\n(<t:{int(guild.created_at.timestamp())}:R>)", inline=True)
        embed.add_field(name="🌍 Région", value=str(guild.preferred_locale), inline=True)
        embed.add_field(name="🔒 Vérification", value=str(guild.verification_level).capitalize(), inline=True)
        
        embed.set_footer(text=f"Demandé par {ctx.author.name}", icon_url=ctx.author.avatar.url if ctx.author.avatar else None)
        
        await ctx.send(embed=embed)
    
    @bot.command()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def userinfo(ctx, member: discord.Member = None):
        """Affiche les informations d'un utilisateur"""
        member = member or ctx.author
        roles = [role.mention for role in member.roles if role.name != "@everyone"]
        
        # Déterminer le statut
        status_emojis = {
            discord.Status.online: "🟢 En ligne",
            discord.Status.idle: "🟡 Absent",
            discord.Status.dnd: "🔴 Ne pas déranger",
            discord.Status.offline: "⚫ Hors ligne"
        }
        status = status_emojis.get(member.status, "⚫ Inconnu")
        
        # Position dans le serveur
        join_position = sorted(ctx.guild.members, key=lambda m: m.joined_at or datetime.min).index(member) + 1
        
        embed = discord.Embed(
            color=member.color if member.color != discord.Color.default() else THEME_COLORS["info"],
            timestamp=datetime.now()
        )
        embed.description = (
            "```ansi\n"
            "\u001b[1;34m╔═══════════════════════════════════════╗\u001b[0m\n"
            "\u001b[1;34m║\u001b[0m       \u001b[1;37m👤 Profil Utilisateur\u001b[0m         \u001b[1;34m║\u001b[0m\n"
            "\u001b[1;34m╚═══════════════════════════════════════╝\u001b[0m\n"
            "```"
        )
        
        if member.avatar:
            embed.set_thumbnail(url=member.avatar.url)
        
        embed.add_field(name="🏷️ Nom", value=f"**{member.name}**\n`{member.display_name}`", inline=True)
        embed.add_field(name="🆔 ID", value=f"`{member.id}`", inline=True)
        embed.add_field(name="📶 Statut", value=status, inline=True)
        
        embed.add_field(name="━━━━━━━━━━━━━━━━━━━━", value="** **", inline=False)
        
        # Calcul de l'âge du compte
        account_age = (datetime.now(member.created_at.tzinfo) - member.created_at).days
        
        embed.add_field(
            name="📅 Compte créé",
            value=f"<t:{int(member.created_at.timestamp())}:D>\n`{account_age}` jours",
            inline=True
        )
        embed.add_field(
            name="📥 A rejoint",
            value=f"<t:{int(member.joined_at.timestamp())}:D>\n#{join_position} membre",
            inline=True
        )
        embed.add_field(
            name="🎖️ Top Rôle",
            value=member.top_role.mention if member.top_role.name != "@everyone" else "*Aucun*",
            inline=True
        )
        
        # Afficher les rôles (max 10)
        if roles:
            roles_display = " ".join(roles[:10])
            if len(roles) > 10:
                roles_display += f"\n*...et {len(roles) - 10} autres*"
            embed.add_field(name=f"🏷️ Rôles ({len(roles)})", value=roles_display, inline=False)
        else:
            embed.add_field(name="🏷️ Rôles", value="*Aucun rôle*", inline=False)
        
        embed.set_footer(text=f"Demandé par {ctx.author.name}", icon_url=ctx.author.avatar.url if ctx.author.avatar else None)
        
        await ctx.send(embed=embed)
    
    @bot.command()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def ping(ctx):
        """Vérifie la latence du bot"""
        latency = round(bot.latency * 1000)
        
        # Déterminer la qualité de la connexion
        if latency < 100:
            quality = "🟢 Excellente"
            color = THEME_COLORS["success"]
            bar = "🟩🟩🟩🟩🟩"
        elif latency < 200:
            quality = "🟡 Bonne"
            color = THEME_COLORS["warning"]
            bar = "🟩🟩🟩🟩⬜"
        else:
            quality = "🔴 Lente"
            color = THEME_COLORS["error"]
            bar = "🟩🟩⬜⬜⬜"
        
        embed = discord.Embed(
            color=color,
            timestamp=datetime.now()
        )
        embed.description = (
            "```ansi\n"
            "\u001b[1;36m╔═══════════════════════════════════════╗\u001b[0m\n"
            "\u001b[1;36m║\u001b[0m          \u001b[1;37m🏓 Pong!\u001b[0m                 \u001b[1;36m║\u001b[0m\n"
            "\u001b[1;36m╚═══════════════════════════════════════╝\u001b[0m\n"
            "```"
        )
        embed.add_field(name="⏱️ Latence", value=f"**{latency}** ms", inline=True)
        embed.add_field(name="📊 Qualité", value=quality, inline=True)
        embed.add_field(name="📶 Signal", value=bar, inline=True)
        embed.set_footer(text=f"Demandé par {ctx.author.name}", icon_url=ctx.author.avatar.url if ctx.author.avatar else None)
        
        await ctx.send(embed=embed)
    
    @bot.command()
    @commands.has_any_role(*TASK_ROLES)
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def task(ctx, action: str, manga: str, *chapitres: str):
        """Met à jour l'état d'une tâche pour un ou plusieurs chapitres"""
        actions_valides = ["clean", "trad", "check", "edit"]
        action_emojis = {"clean": "🧹", "trad": "🌍", "check": "✅", "edit": "✏️"}
        
        if action.lower() not in actions_valides:
            embed = discord.Embed(
                color=THEME_COLORS["error"],
                description=(
                    "```ansi\n"
                    "\u001b[1;31m╔═══════════════════════════════════════╗\u001b[0m\n"
                    "\u001b[1;31m║\u001b[0m       \u001b[1;37m❌ Action Invalide\u001b[0m            \u001b[1;31m║\u001b[0m\n"
                    "\u001b[1;31m╚═══════════════════════════════════════╝\u001b[0m\n"
                    "```\n"
                    f"Actions disponibles : `{', '.join(actions_valides)}`"
                )
            )
            await ctx.send(embed=embed, delete_after=10)
            return
        
        chapitres_traites = []
        chapitres_erreur = []
        chapitres_complets = []
        
        manga_normalized = manga.strip()
        action_emoji = action_emojis[action.lower()]
        
        for chapitre_str in chapitres:
            chapitre_str = chapitre_str.strip().rstrip(',')
            
            try:
                chapitre = int(chapitre_str)
                chapitre_key = f"{manga_normalized.lower()}_{chapitre}"
                
                if chapitre_key not in etat_taches_global:
                    etat_taches_global[chapitre_key] = {
                        "clean": "❌ Non commencé",
                        "trad": "❌ Non commencé",
                        "check": "❌ Non commencé",
                        "edit": "❌ Non commencé"
                    }
                
                etat_taches_global[chapitre_key][action.lower()] = "✅ Terminé"
                chapitres_traites.append(str(chapitre))
                
                if est_chapitre_complet(etat_taches_global[chapitre_key]):
                    chapitres_complets.append(str(chapitre))
                
            except ValueError:
                chapitres_erreur.append(chapitre_str)
                continue
        
        sauvegarder_etat_taches()
        
        # Créer l'embed de réponse
        embed = discord.Embed(
            color=THEME_COLORS["tasks"],
            timestamp=datetime.now()
        )
        embed.description = (
            "```ansi\n"
            "\u001b[1;36m╔═══════════════════════════════════════╗\u001b[0m\n"
            "\u001b[1;36m║\u001b[0m       \u001b[1;37m📋 Mise à Jour Tâche\u001b[0m          \u001b[1;36m║\u001b[0m\n"
            "\u001b[1;36m╚═══════════════════════════════════════╝\u001b[0m\n"
            "```"
        )
        
        embed.add_field(name=f"{action_emoji} Action", value=f"**{action.capitalize()}**", inline=True)
        embed.add_field(name="📚 Manga", value=f"**{manga_normalized}**", inline=True)
        embed.add_field(name="👤 Par", value=ctx.author.mention, inline=True)
        
        if chapitres_traites:
            embed.add_field(
                name="✅ Chapitres mis à jour",
                value=f"`{', '.join(chapitres_traites)}`",
                inline=False
            )
        if chapitres_erreur:
            embed.add_field(
                name="❌ Chapitres ignorés",
                value=f"`{', '.join(chapitres_erreur)}`",
                inline=False
            )
        if chapitres_complets:
            embed.add_field(
                name="🎉 Chapitres terminés !",
                value=f"**{', '.join(chapitres_complets)}**",
                inline=False
            )
        
        embed.set_footer(text=f"!task {action} {manga}", icon_url=ctx.author.avatar.url if ctx.author.avatar else None)
        
        await ctx.send(embed=embed)
        
        manga_nom_formate = manga_normalized
        
        if manga_nom_formate in MANGA_CHANNELS and manga_nom_formate in MANGA_ROLES:
            thread_id = MANGA_CHANNELS[manga_nom_formate]
            role_id = MANGA_ROLES[manga_nom_formate]
            thread_channel = bot.get_channel(thread_id)
            
            if thread_channel:
                if chapitres_complets:
                    mention_role = f"<@&{role_id}>"
                    chapitres_mention = ", ".join(chapitres_complets)
                    
                    notif_embed = discord.Embed(
                        color=THEME_COLORS["gold"],
                        timestamp=datetime.now()
                    )
                    notif_embed.description = (
                        "```ansi\n"
                        "\u001b[1;33m╔═══════════════════════════════════════╗\u001b[0m\n"
                        "\u001b[1;33m║\u001b[0m    \u001b[1;37m🎉 CHAPITRE(S) TERMINÉ(S) !\u001b[0m    \u001b[1;33m║\u001b[0m\n"
                        "\u001b[1;33m╚═══════════════════════════════════════╝\u001b[0m\n"
                        "```"
                    )
                    notif_embed.add_field(
                        name="📚 Manga",
                        value=f"**{manga_nom_formate}**",
                        inline=True
                    )
                    notif_embed.add_field(
                        name="📖 Chapitre(s)",
                        value=f"**{chapitres_mention}**",
                        inline=True
                    )
                    notif_embed.add_field(
                        name="✅ Toutes les tâches terminées",
                        value="🧹 Clean • 🌍 Trad • ✅ Check • ✏️ Edit",
                        inline=False
                    )
                    notif_embed.set_footer(text="Excellent travail d'équipe ! 💪")
                    
                    await thread_channel.send(f"{mention_role}", embed=notif_embed)

                    # Envoyer aussi au channel logs/staff
                    logs_channel = bot.get_channel(CHANNELS.get("logs"))
                    if logs_channel:
                        staff_embed = discord.Embed(
                            title="🎉 Chapitre(s) terminé(s) !",
                            description=f"**{manga_nom_formate}** - Chapitres **{chapitres_mention}**\nToutes les tâches sont complètes.",
                            color=0xFFD700,
                            timestamp=datetime.now()
                        )
                        staff_embed.add_field(name="👤 Dernière action par", value=ctx.author.mention, inline=True)
                        staff_embed.set_footer(text="Notification de progression")
                        await logs_channel.send(embed=staff_embed)

                        # ══════ DM de notification aux membres qui ont contribué ══════
                        notified_users = set()
                        for chap in chapitres_complets:
                            chap_key = f"{manga_normalized}_{chap}" if chap.isdigit() else f"{manga_normalized.lower()}_{chap}"
                            # Chercher la clé exacte
                            for k in etat_taches_global:
                                if k.lower() == chap_key.lower():
                                    chap_key = k
                                    break
                            task_data = etat_taches_global.get(chap_key, {})
                            for t_name, t_val in task_data.items():
                                if isinstance(t_val, dict) and t_val.get("claimed_by"):
                                    uid = t_val["claimed_by"]
                                    if uid not in notified_users and uid != ctx.author.id:
                                        notified_users.add(uid)
                                        try:
                                            user = await bot.fetch_user(uid)
                                            dm_embed = discord.Embed(
                                                title="🎉 Chapitre terminé !",
                                                description=(
                                                    f"Le chapitre **{chap}** de **{manga_nom_formate}** est maintenant complet !\n"
                                                    f"Merci pour ta contribution en **{t_name}** ! 💪"
                                                ),
                                                color=0xFFD700
                                            )
                                            dm_embed.set_footer(text="LanorTrad • Notification de progression")
                                            await user.send(embed=dm_embed)
                                        except:
                                            pass
                else:
                    message_aleatoire = random.choice(MESSAGES_ALEATOIRES)
                    await thread_channel.send(message_aleatoire)

                    # ══════ ATTRIBUTION AUTOMATIQUE : Suggérer les tâches suivantes ══════
                    # Trouver les tâches non réclamées pour ce manga
                    unclaimed_tasks = []
                    for key, tasks_data in etat_taches_global.items():
                        m_name, _ = extraire_manga_chapitre(key)
                        if m_name and normaliser_manga_name(m_name) == normaliser_manga_name(manga_normalized):
                            for t_name in ["clean", "trad", "check", "edit"]:
                                val = tasks_data.get(t_name, "❌ Non commencé")
                                if val == "❌ Non commencé":
                                    unclaimed_tasks.append(f"• `!claim \"{m_name}\" {key.rsplit('_',1)[-1]} {t_name}`")

                    if unclaimed_tasks and len(unclaimed_tasks) <= 10:
                        suggest_embed = discord.Embed(
                            title="💡 Tâches disponibles",
                            description="Tu veux continuer ? Voici les tâches disponibles :\n" + "\n".join(unclaimed_tasks[:5]),
                            color=COLORS["info"]
                        )
                        suggest_embed.set_footer(text="Utilise !claim pour en récupérer une !")
                        await ctx.send(embed=suggest_embed, delete_after=30)

    # ==================== COMMANDES CLAIM / UNCLAIM ====================

    @bot.command()
    @commands.has_any_role(*TASK_ROLES)
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def claim(ctx, manga: str, chapitre: str, tache: str):
        """Réclame une tâche pour un chapitre (ex: !claim "Tougen Anki" 216 clean)"""
        actions_valides = ["clean", "trad", "check", "edit"]
        tache = tache.lower()

        if tache not in actions_valides:
            await ctx.send(f"❌ Tâche invalide. Choisissez parmi: `{', '.join(actions_valides)}`", delete_after=10)
            return

        try:
            chapitre_num = int(chapitre)
        except ValueError:
            await ctx.send("❌ Numéro de chapitre invalide.", delete_after=10)
            return

        manga_normalized = manga.strip()
        chapitre_key = f"{manga_normalized.lower()}_{chapitre_num}"

        if chapitre_key not in etat_taches_global:
            etat_taches_global[chapitre_key] = {
                "clean": "❌ Non commencé",
                "trad": "❌ Non commencé",
                "check": "❌ Non commencé",
                "edit": "❌ Non commencé"
            }

        current = etat_taches_global[chapitre_key].get(tache, "❌ Non commencé")

        # Vérifier si déjà terminé
        if current == "✅ Terminé":
            await ctx.send(f"⚠️ Cette tâche est déjà terminée !", delete_after=10)
            return

        # Vérifier si déjà claim par quelqu'un d'autre
        if isinstance(current, dict) and current.get("status") == "🔄 En cours":
            claimed_by = current.get("claimed_by")
            if claimed_by != ctx.author.id:
                await ctx.send(f"⚠️ Cette tâche est déjà réclamée par <@{claimed_by}>.", delete_after=10)
                return
            else:
                await ctx.send(f"ℹ️ Vous avez déjà réclamé cette tâche.", delete_after=10)
                return

        # Claim la tâche
        etat_taches_global[chapitre_key][tache] = {
            "status": "🔄 En cours",
            "claimed_by": ctx.author.id,
            "claimed_at": datetime.now().isoformat()
        }
        sauvegarder_etat_taches()

        task_emoji = TASK_EMOJIS.get(tache, "📝")
        embed = discord.Embed(
            title=f"{task_emoji} Tâche réclamée !",
            description=f"**{manga_normalized}** - Chapitre **{chapitre_num}**\nTâche: **{tache.capitalize()}**",
            color=0x3498DB,
            timestamp=datetime.now()
        )
        embed.add_field(name="👤 Réclamée par", value=ctx.author.mention, inline=True)
        embed.set_footer(text="Utilisez !task pour marquer comme terminée")
        await ctx.send(embed=embed)

    @bot.command()
    @commands.has_any_role(*TASK_ROLES)
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def unclaim(ctx, manga: str, chapitre: str, tache: str):
        """Libère une tâche réclamée (ex: !unclaim "Tougen Anki" 216 clean)"""
        actions_valides = ["clean", "trad", "check", "edit"]
        tache = tache.lower()

        if tache not in actions_valides:
            await ctx.send(f"❌ Tâche invalide. Choisissez parmi: `{', '.join(actions_valides)}`", delete_after=10)
            return

        try:
            chapitre_num = int(chapitre)
        except ValueError:
            await ctx.send("❌ Numéro de chapitre invalide.", delete_after=10)
            return

        manga_normalized = manga.strip()
        chapitre_key = f"{manga_normalized.lower()}_{chapitre_num}"

        if chapitre_key not in etat_taches_global:
            await ctx.send("❌ Ce chapitre n'existe pas dans les tâches.", delete_after=10)
            return

        current = etat_taches_global[chapitre_key].get(tache, "❌ Non commencé")

        if not isinstance(current, dict) or current.get("status") != "🔄 En cours":
            await ctx.send("⚠️ Cette tâche n'est pas réclamée.", delete_after=10)
            return

        # Vérifier que c'est le bon user ou un admin
        user_roles = [role.id for role in ctx.author.roles]
        is_admin = any(role in user_roles for role in ADMIN_ROLES)

        if current.get("claimed_by") != ctx.author.id and not is_admin:
            await ctx.send("❌ Vous ne pouvez libérer que vos propres tâches.", delete_after=10)
            return

        etat_taches_global[chapitre_key][tache] = "❌ Non commencé"
        sauvegarder_etat_taches()

        embed = discord.Embed(
            title="🔓 Tâche libérée",
            description=f"**{manga_normalized}** - Chapitre **{chapitre_num}** - **{tache.capitalize()}**",
            color=0xE67E22
        )
        await ctx.send(embed=embed)

    @bot.command()
    @commands.has_any_role(*TASK_ROLES)
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def task_status(ctx, manga: str, chapitre: int):
        """Affiche l'état des tâches pour un chapitre donné"""
        manga_normalized = normaliser_manga_name(manga)
        chapitre_key = None
        
        for key in etat_taches_global:
            key_manga, key_chap = extraire_manga_chapitre(key)
            if key_manga and normaliser_manga_name(key_manga) == manga_normalized and key_chap == chapitre:
                chapitre_key = key
                break
        
        if chapitre_key is None:
            embed = discord.Embed(
                color=THEME_COLORS["error"],
                description=(
                    "```ansi\n"
                    "\u001b[1;31m╔═══════════════════════════════════════╗\u001b[0m\n"
                    "\u001b[1;31m║\u001b[0m       \u001b[1;37m❌ Chapitre Non Trouvé\u001b[0m        \u001b[1;31m║\u001b[0m\n"
                    "\u001b[1;31m╚═══════════════════════════════════════╝\u001b[0m\n"
                    "```\n"
                    f"Aucun état trouvé pour **{manga}** ch.**{chapitre}**."
                )
            )
            await ctx.send(embed=embed)
            return
        
        etat_taches = etat_taches_global[chapitre_key]
        is_complete = est_chapitre_complet(etat_taches)
        
        # Calculer la progression
        completed_tasks = sum(1 for t in etat_taches.values() if t == "✅ Terminé")
        progress_bar = generate_progress_bar(completed_tasks, 4)
        
        embed = discord.Embed(
            color=THEME_COLORS["gold"] if is_complete else THEME_COLORS["tasks"],
            timestamp=datetime.now()
        )
        embed.description = (
            "```ansi\n"
            "\u001b[1;36m╔═══════════════════════════════════════╗\u001b[0m\n"
            "\u001b[1;36m║\u001b[0m       \u001b[1;37m📊 État des Tâches\u001b[0m            \u001b[1;36m║\u001b[0m\n"
            "\u001b[1;36m╚═══════════════════════════════════════╝\u001b[0m\n"
            "```"
        )
        
        embed.add_field(name="📚 Manga", value=f"**{manga.title()}**", inline=True)
        embed.add_field(name="📖 Chapitre", value=f"**{chapitre}**", inline=True)
        embed.add_field(name="📈 Progression", value=f"{progress_bar} `{completed_tasks}/4`", inline=True)
        
        embed.add_field(name="━━━━━━━━━━━━━━━━━━━━", value="** **", inline=False)
        
        # Afficher les tâches avec emojis
        task_emojis = {"clean": "🧹", "trad": "🌍", "check": "✅", "edit": "✏️"}
        for tache, etat in etat_taches.items():
            emoji = task_emojis.get(tache, "📌")
            status_icon = "✅" if etat == "✅ Terminé" else "⏳"
            embed.add_field(name=f"{emoji} {tache.capitalize()}", value=f"{status_icon} {etat}", inline=True)
        
        if is_complete:
            embed.add_field(name="━━━━━━━━━━━━━━━━━━━━", value="** **", inline=False)
            embed.add_field(name="🎉 Statut", value="**✅ Chapitre COMPLET !**", inline=False)
        
        embed.set_footer(text=f"Demandé par {ctx.author.name}", icon_url=ctx.author.avatar.url if ctx.author.avatar else None)
        
        await ctx.send(embed=embed)
    
    @bot.command()
    @commands.has_any_role(*TASK_ROLES)
    async def delete_task(ctx, manga: str, chapitre: int):
        """Supprime toutes les tâches d'un chapitre"""
        manga_normalized = normaliser_manga_name(manga)
        chapitre_key = None
        
        for key in etat_taches_global:
            key_manga, key_chap = extraire_manga_chapitre(key)
            if key_manga and normaliser_manga_name(key_manga) == manga_normalized and key_chap == chapitre:
                chapitre_key = key
                break
        
        if chapitre_key and chapitre_key in etat_taches_global:
            del etat_taches_global[chapitre_key]
            sauvegarder_etat_taches()
            
            embed = discord.Embed(
                color=THEME_COLORS["warning"],
                timestamp=datetime.now()
            )
            embed.description = (
                "```ansi\n"
                "\u001b[1;33m╔═══════════════════════════════════════╗\u001b[0m\n"
                "\u001b[1;33m║\u001b[0m       \u001b[1;37m🗑️ Tâches Supprimées\u001b[0m          \u001b[1;33m║\u001b[0m\n"
                "\u001b[1;33m╚═══════════════════════════════════════╝\u001b[0m\n"
                "```"
            )
            embed.add_field(name="📚 Manga", value=f"**{manga}**", inline=True)
            embed.add_field(name="📖 Chapitre", value=f"**{chapitre}**", inline=True)
            embed.add_field(name="👤 Par", value=ctx.author.mention, inline=True)
            embed.set_footer(text=f"Action par {ctx.author.name}", icon_url=ctx.author.avatar.url if ctx.author.avatar else None)
            
            await ctx.send(embed=embed)
        else:
            embed = discord.Embed(
                color=THEME_COLORS["error"],
                description=(
                    "```ansi\n"
                    "\u001b[1;31m╔═══════════════════════════════════════╗\u001b[0m\n"
                    "\u001b[1;31m║\u001b[0m       \u001b[1;37m❌ Tâche Non Trouvée\u001b[0m          \u001b[1;31m║\u001b[0m\n"
                    "\u001b[1;31m╚═══════════════════════════════════════╝\u001b[0m\n"
                    "```\n"
                    f"Aucune tâche trouvée pour **{manga}** ch.**{chapitre}**."
                )
            )
            await ctx.send(embed=embed)
    
    @bot.command(name="fix_tasks")
    @commands.has_any_role(*TASK_ROLES)
    async def fix_tasks(ctx):
        """Normalise les clés des tâches"""
        global etat_taches_global
        
        old_count = len(etat_taches_global)
        new_tasks = {}
        fixed_count = 0
        
        for key, value in etat_taches_global.items():
            key_manga, key_chap = extraire_manga_chapitre(key)
            
            if key_manga and key_chap:
                new_key = f"{key_manga}_{key_chap}"
                if new_key != key:
                    fixed_count += 1
                
                if new_key in new_tasks:
                    for task_name, task_status in value.items():
                        if task_status == "✅ Terminé":
                            new_tasks[new_key][task_name] = task_status
                else:
                    new_tasks[new_key] = value
            else:
                new_tasks[key] = value
        
        etat_taches_global = new_tasks
        sauvegarder_etat_taches()
        
        embed = discord.Embed(
            color=THEME_COLORS["success"],
            timestamp=datetime.now()
        )
        embed.description = (
            "```ansi\n"
            "\u001b[1;32m╔═══════════════════════════════════════╗\u001b[0m\n"
            "\u001b[1;32m║\u001b[0m    \u001b[1;37m🔧 Normalisation Terminée\u001b[0m        \u001b[1;32m║\u001b[0m\n"
            "\u001b[1;32m╚═══════════════════════════════════════╝\u001b[0m\n"
            "```"
        )
        embed.add_field(name="📊 Avant", value=f"`{old_count}` tâches", inline=True)
        embed.add_field(name="📊 Après", value=f"`{len(etat_taches_global)}` tâches", inline=True)
        embed.add_field(name="🔧 Corrigées", value=f"`{fixed_count}` clés", inline=True)
        embed.set_footer(text=f"Exécuté par {ctx.author.name}", icon_url=ctx.author.avatar.url if ctx.author.avatar else None)
        
        await ctx.send(embed=embed)
    
    @bot.command(name="avancee")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def avancee(ctx):
        """Affiche l'avancée des mangas avec pagination"""
        embed = discord.Embed(
            color=THEME_COLORS["manga"],
            timestamp=datetime.now()
        )
        embed.description = (
            "```ansi\n"
            "\u001b[1;35m╔═══════════════════════════════════════╗\u001b[0m\n"
            "\u001b[1;35m║\u001b[0m    \u001b[1;37m📊 Avancée des Projets\u001b[0m          \u001b[1;35m║\u001b[0m\n"
            "\u001b[1;35m╚═══════════════════════════════════════╝\u001b[0m\n"
            "```\n"
            "**Choisissez un manga !**\n\n"
            "👹 Ao No Exorcist\n"
            "🩸 Satsudou\n"
            "🗼 Tokyo Underworld\n"
            "😈 Tougen Anki\n"
            "⚽ Catenaccio"
        )
        embed.set_footer(text="Cliquez sur une réaction pour voir l'avancée", icon_url=ctx.author.avatar.url if ctx.author.avatar else None)
        
        message = await ctx.send(embed=embed)
        
        reactions = ['👹', '🩸', '🗼', '😈', '⚽']
        for r in reactions:
            await message.add_reaction(r)
        
        manga_map = {
            '👹': 'Ao No Exorcist',
            '🩸': 'Satsudou',
            '🗼': 'Tokyo Underworld',
            '😈': 'Tougen Anki',
            '⚽': 'Catenaccio'
        }
        
        def check(reaction, user):
            return user == ctx.author and str(reaction.emoji) in reactions
        
        try:
            reaction, user = await bot.wait_for('reaction_add', timeout=30.0, check=check)
            manga_name = manga_map[str(reaction.emoji)]
            manga_emoji = str(reaction.emoji)
            
            manga_chapters = {}
            manga_name_normalized = normaliser_manga_name(manga_name)
            
            for key in etat_taches_global:
                key_manga, key_chapter = extraire_manga_chapitre(key)
                if key_manga and key_chapter:
                    if normaliser_manga_name(key_manga) == manga_name_normalized:
                        manga_chapters[key_chapter] = etat_taches_global[key]
            
            if not manga_chapters:
                error_embed = discord.Embed(
                    color=THEME_COLORS["error"],
                    description=(
                        "```ansi\n"
                        "\u001b[1;31m╔═══════════════════════════════════════╗\u001b[0m\n"
                        "\u001b[1;31m║\u001b[0m       \u001b[1;37m❌ Aucune Tâche\u001b[0m               \u001b[1;31m║\u001b[0m\n"
                        "\u001b[1;31m╚═══════════════════════════════════════╝\u001b[0m\n"
                        "```\n"
                        f"Aucune tâche trouvée pour **{manga_name}**."
                    )
                )
                await ctx.send(embed=error_embed)
                return
            
            sorted_chapters = sorted(manga_chapters.keys())
            CHAPTERS_PER_PAGE = 5
            total_pages = (len(sorted_chapters) + CHAPTERS_PER_PAGE - 1) // CHAPTERS_PER_PAGE
            
            def create_page_embed(page_num):
                start_idx = page_num * CHAPTERS_PER_PAGE
                end_idx = min(start_idx + CHAPTERS_PER_PAGE, len(sorted_chapters))
                page_chapters = sorted_chapters[start_idx:end_idx]
                
                total_tasks = len(sorted_chapters) * 4
                completed = sum(1 for ch in sorted_chapters for t in manga_chapters[ch].values() if t == "✅ Terminé")
                progress = (completed / total_tasks * 100) if total_tasks > 0 else 0
                progress_bar = generate_progress_bar(int(progress / 10), 10)
                
                page_embed = discord.Embed(
                    color=THEME_COLORS["manga"],
                    timestamp=datetime.now()
                )
                page_embed.description = (
                    "```ansi\n"
                    "\u001b[1;35m╔═══════════════════════════════════════╗\u001b[0m\n"
                    f"\u001b[1;35m║\u001b[0m      \u001b[1;37m{manga_emoji} {manga_name}\u001b[0m\n"
                    "\u001b[1;35m╚═══════════════════════════════════════╝\u001b[0m\n"
                    "```\n"
                    f"📊 **Progression globale:** `{progress:.1f}%`\n"
                    f"{progress_bar} ({completed}/{total_tasks})\n"
                    f"📚 Chapitres: `{sorted_chapters[0]}` → `{sorted_chapters[-1]}`"
                )
                
                page_embed.add_field(name="━━━━━━━━━━━━━━━━━━━━", value="** **", inline=False)
                
                for chapter in page_chapters:
                    tasks = manga_chapters[chapter]
                    prog = sum(1 for t in tasks.values() if t == "✅ Terminé")
                    bar = generate_progress_bar(prog, 4)
                    
                    title = f"📑 Ch.{chapter}"
                    if est_chapitre_complet(tasks):
                        title += " ✅"
                    
                    # Format compact
                    clean_status = "✅" if tasks.get('clean') == "✅ Terminé" else "⏳"
                    trad_status = "✅" if tasks.get('trad') == "✅ Terminé" else "⏳"
                    check_status = "✅" if tasks.get('check') == "✅ Terminé" else "⏳"
                    edit_status = "✅" if tasks.get('edit') == "✅ Terminé" else "⏳"
                    
                    value = (
                        f"{bar} `{prog}/4`\n"
                        f"🧹{clean_status} 🌍{trad_status} ✅{check_status} ✏️{edit_status}"
                    )
                    
                    page_embed.add_field(name=title, value=value, inline=True)
                
                page_embed.set_footer(
                    text=f"Page {page_num + 1}/{total_pages} │ {ctx.author.name}",
                    icon_url=ctx.author.avatar.url if ctx.author.avatar else None
                )
                
                return page_embed
            
            current_page = 0
            await message.clear_reactions()
            await message.edit(embed=create_page_embed(current_page))
            
            if total_pages > 1:
                nav = ['⏮️', '⬅️', '➡️', '⏭️', '🏠']
                for n in nav:
                    await message.add_reaction(n)
                
                def nav_check(reaction, user):
                    return user == ctx.author and str(reaction.emoji) in nav and reaction.message.id == message.id
                
                while True:
                    try:
                        reaction, user = await bot.wait_for('reaction_add', timeout=120.0, check=nav_check)
                        emoji = str(reaction.emoji)
                        
                        if emoji == '⏮️':
                            current_page = 0
                        elif emoji == '⬅️':
                            current_page = max(0, current_page - 1)
                        elif emoji == '➡️':
                            current_page = min(total_pages - 1, current_page + 1)
                        elif emoji == '⏭️':
                            current_page = total_pages - 1
                        elif emoji == '🏠':
                            await message.clear_reactions()
                            await message.edit(embed=embed)
                            for r in reactions:
                                await message.add_reaction(r)
                            break
                        
                        await message.edit(embed=create_page_embed(current_page))
                        await message.remove_reaction(reaction, user)
                    
                    except asyncio.TimeoutError:
                        await message.clear_reactions()
                        break
        
        except asyncio.TimeoutError:
            await message.clear_reactions()
            embed.description += "\n\n⏰ Temps écoulé."
            await message.edit(embed=embed)
    
    @bot.command(name="task_all")
    @commands.has_any_role(*TASK_ROLES)
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def task_all(ctx, *, manga_filter: str = None):
        """Affiche toutes les tâches en cours (optionnel: spécifier un manga)"""
        if not etat_taches_global:
            embed = discord.Embed(
                color=THEME_COLORS["info"],
                description=(
                    "```ansi\n"
                    "\u001b[1;34m╔═══════════════════════════════════════╗\u001b[0m\n"
                    "\u001b[1;34m║\u001b[0m       \u001b[1;37m📋 Aucune Tâche\u001b[0m              \u001b[1;34m║\u001b[0m\n"
                    "\u001b[1;34m╚═══════════════════════════════════════╝\u001b[0m\n"
                    "```\n"
                    "Il n'y a actuellement aucune tâche en cours."
                )
            )
            await ctx.send(embed=embed)
            return
        
        tasks_by_manga = {}
        manga_emojis = {
            "Ao No Exorcist": "👹",
            "Satsudou": "🩸",
            "Tokyo Underworld": "🗼",
            "Tougen Anki": "😈",
            "Catenaccio": "⚽"
        }
        
        for chapitre_key, tasks in etat_taches_global.items():
            key_manga, key_chapter = extraire_manga_chapitre(chapitre_key)
            
            if key_manga and key_chapter:
                manga_display = key_manga.title()
                if manga_display not in tasks_by_manga:
                    tasks_by_manga[manga_display] = {}
                tasks_by_manga[manga_display][str(key_chapter)] = tasks
        
        # Si un manga est spécifié, filtrer
        if manga_filter:
            manga_filter_normalized = manga_filter.strip().lower()
            filtered_manga = None
            
            for manga_name in tasks_by_manga.keys():
                if manga_filter_normalized in manga_name.lower():
                    filtered_manga = manga_name
                    break
            
            if filtered_manga:
                tasks_by_manga = {filtered_manga: tasks_by_manga[filtered_manga]}
            else:
                # Afficher le menu de sélection si le manga n'est pas trouvé
                available_mangas = "\n".join([f"{manga_emojis.get(m, '📚')} {m}" for m in tasks_by_manga.keys()])
                embed = discord.Embed(
                    color=THEME_COLORS["error"],
                    description=(
                        "```ansi\n"
                        "\u001b[1;31m╔═══════════════════════════════════════╗\u001b[0m\n"
                        "\u001b[1;31m║\u001b[0m       \u001b[1;37m❌ Manga Non Trouvé\u001b[0m           \u001b[1;31m║\u001b[0m\n"
                        "\u001b[1;31m╚═══════════════════════════════════════╝\u001b[0m\n"
                        "```\n"
                        f"Aucun manga trouvé pour **{manga_filter}**.\n\n"
                        f"**Mangas disponibles :**\n{available_mangas}\n\n"
                        f"💡 Utilisez `!task_all` sans argument pour tout voir."
                    )
                )
                await ctx.send(embed=embed)
                return
        
        embeds = []
        CHAPTERS_PER_PAGE = 8  # Limite pour éviter de dépasser 25 fields
        
        for manga, chapitres in tasks_by_manga.items():
            manga_emoji = manga_emojis.get(manga, "📚")
            
            # Calculer la progression globale du manga
            total_tasks = len(chapitres) * 4
            completed_tasks = sum(1 for chap_tasks in chapitres.values() for t in chap_tasks.values() if t == "✅ Terminé")
            progress = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
            
            sorted_chapters = sorted(chapitres.items(), key=lambda x: int(x[0]))
            
            # Diviser en pages si nécessaire
            for page_start in range(0, len(sorted_chapters), CHAPTERS_PER_PAGE):
                page_chapters = sorted_chapters[page_start:page_start + CHAPTERS_PER_PAGE]
                page_num = page_start // CHAPTERS_PER_PAGE + 1
                total_manga_pages = (len(sorted_chapters) + CHAPTERS_PER_PAGE - 1) // CHAPTERS_PER_PAGE
                
                embed = discord.Embed(
                    color=THEME_COLORS["tasks"],
                    timestamp=datetime.now()
                )
                
                page_info = f" ({page_num}/{total_manga_pages})" if total_manga_pages > 1 else ""
                embed.description = (
                    "```ansi\n"
                    "\u001b[1;36m╔═══════════════════════════════════════╗\u001b[0m\n"
                    f"\u001b[1;36m║\u001b[0m      \u001b[1;37m{manga_emoji} {manga}\u001b[0m{page_info}\n"
                    "\u001b[1;36m╚═══════════════════════════════════════╝\u001b[0m\n"
                    "```\n"
                    f"📊 **Progression:** `{progress:.1f}%` ({completed_tasks}/{total_tasks})\n"
                    f"📚 **Chapitres:** `{len(chapitres)}`"
                )
                
                for chapitre, tasks in page_chapters:
                    prog = sum(1 for t in tasks.values() if t == "✅ Terminé")
                    bar = generate_progress_bar(prog, 4)
                    
                    title = f"📑 Ch.{chapitre}"
                    if est_chapitre_complet(tasks):
                        title += " ✅"
                    
                    # Format compact
                    clean_status = "✅" if tasks.get('clean') == "✅ Terminé" else "⏳"
                    trad_status = "✅" if tasks.get('trad') == "✅ Terminé" else "⏳"
                    check_status = "✅" if tasks.get('check') == "✅ Terminé" else "⏳"
                    edit_status = "✅" if tasks.get('edit') == "✅ Terminé" else "⏳"
                    
                    value = (
                        f"{bar} `{prog}/4`\n"
                        f"🧹{clean_status} 🌍{trad_status} ✅{check_status} ✏️{edit_status}"
                    )
                    
                    embed.add_field(name=title, value=value, inline=True)
                
                embeds.append(embed)
        
        if not embeds:
            embed = discord.Embed(
                color=THEME_COLORS["error"],
                description="❌ Aucune tâche trouvée."
            )
            await ctx.send(embed=embed)
            return
        
        # Mettre à jour les footers avec le compte total de pages
        for i, embed in enumerate(embeds):
            embed.set_footer(
                text=f"Page {i+1}/{len(embeds)} │ {ctx.author.name}",
                icon_url=ctx.author.avatar.url if ctx.author.avatar else None
            )
        
        current_page = 0
        message = await ctx.send(embed=embeds[current_page])
        
        if len(embeds) > 1:
            await message.add_reaction('⬅️')
            await message.add_reaction('➡️')
            
            def check(reaction, user):
                return user == ctx.author and str(reaction.emoji) in ['⬅️', '➡️'] and reaction.message.id == message.id
            
            while True:
                try:
                    reaction, user = await bot.wait_for('reaction_add', timeout=60.0, check=check)
                    
                    if str(reaction.emoji) == '⬅️' and current_page > 0:
                        current_page -= 1
                        await message.edit(embed=embeds[current_page])
                    elif str(reaction.emoji) == '➡️' and current_page < len(embeds) - 1:
                        current_page += 1
                        await message.edit(embed=embeds[current_page])
                    
                    await message.remove_reaction(reaction, user)
                
                except asyncio.TimeoutError:
                    await message.clear_reactions()
                    break
    
    @bot.command(name="actualiser")
    @commands.has_any_role(*TASK_ROLES)
    @commands.cooldown(1, 30, commands.BucketType.user)
    async def actualiser(ctx):
        """Sauvegarder et envoyer les données"""
        TARGET_USER_ID = 608234789564186644
        
        embed_select = discord.Embed(
            color=THEME_COLORS["info"],
            timestamp=datetime.now()
        )
        embed_select.description = (
            "```ansi\n"
            "\u001b[1;34m╔═══════════════════════════════════════╗\u001b[0m\n"
            "\u001b[1;34m║\u001b[0m       \u001b[1;37m🔄 Actualisation\u001b[0m             \u001b[1;34m║\u001b[0m\n"
            "\u001b[1;34m╚═══════════════════════════════════════╝\u001b[0m\n"
            "```\n"
            "**Choisissez le type de données à exporter :**\n\n"
            "📝 **Tasks** - Tâches des chapitres\n"
            "⏰ **Rappels** - Rappels planifiés\n"
            "📨 **Invitations** - Données giveaway\n"
            "❌ **Annuler**"
        )
        embed_select.set_footer(text="Sélectionnez une option", icon_url=ctx.author.avatar.url if ctx.author.avatar else None)
        
        message = await ctx.send(embed=embed_select)
        
        for e in ["📝", "⏰", "📨", "❌"]:
            await message.add_reaction(e)
        
        def check(reaction, user):
            return user == ctx.author and str(reaction.emoji) in ["📝", "⏰", "📨", "❌"] and reaction.message.id == message.id
        
        try:
            reaction, user = await bot.wait_for('reaction_add', timeout=30.0, check=check)
            await message.clear_reactions()
            
            if str(reaction.emoji) == "❌":
                cancel_embed = discord.Embed(
                    color=THEME_COLORS["error"],
                    description="❌ **Opération annulée.**"
                )
                await message.edit(embed=cancel_embed)
                return
            
            if str(reaction.emoji) == "📝":
                file_type, main_file, meta_file = "tasks", TASKS_FILE, META_FILE
                data = etat_taches_global
                sauvegarder_etat_taches()
            elif str(reaction.emoji) == "⏰":
                import rappels
                file_type = "rappels"
                main_file, meta_file = rappels.RAPPELS_FILE, rappels.RAPPELS_META_FILE
                data = rappels.rappels_actifs
                rappels.sauvegarder_rappels()
            else:
                import giveaway
                file_type = "invitations"
                main_file = giveaway.INVITES_FILE
                meta_file = "data/invites_tracker_meta.json"
                data = giveaway.invites_tracker
                giveaway.sauvegarder_invites()
            
            target_user = await bot.fetch_user(TARGET_USER_ID)
            if not target_user:
                error_embed = discord.Embed(
                    color=THEME_COLORS["error"],
                    description="❌ **Utilisateur cible introuvable.**"
                )
                await message.edit(embed=error_embed)
                return
            
            files = []
            if os.path.exists(main_file):
                files.append(discord.File(main_file))
            if os.path.exists(meta_file):
                files.append(discord.File(meta_file))
            
            embed_dm = discord.Embed(
                color=THEME_COLORS["success"],
                timestamp=datetime.now()
            )
            embed_dm.description = (
                "```ansi\n"
                "\u001b[1;32m╔═══════════════════════════════════════╗\u001b[0m\n"
                "\u001b[1;32m║\u001b[0m       \u001b[1;37m📁 Export de Données\u001b[0m          \u001b[1;32m║\u001b[0m\n"
                "\u001b[1;32m╚═══════════════════════════════════════╝\u001b[0m\n"
                "```"
            )
            embed_dm.add_field(name="📊 Type", value=f"**{file_type.capitalize()}**", inline=True)
            embed_dm.add_field(name="📈 Éléments", value=f"`{len(data)}`", inline=True)
            embed_dm.add_field(name="👤 Par", value=ctx.author.mention, inline=True)
            embed_dm.set_footer(text=f"{ctx.guild.name}")
            
            await target_user.send(embed=embed_dm, files=files)
            
            # Message de confirmation
            success_embed = discord.Embed(
                color=THEME_COLORS["success"],
                timestamp=datetime.now()
            )
            success_embed.description = (
                "```ansi\n"
                "\u001b[1;32m╔═══════════════════════════════════════╗\u001b[0m\n"
                "\u001b[1;32m║\u001b[0m       \u001b[1;37m✅ Export Réussi\u001b[0m              \u001b[1;32m║\u001b[0m\n"
                "\u001b[1;32m╚═══════════════════════════════════════╝\u001b[0m\n"
                "```"
            )
            success_embed.add_field(name="📊 Type", value=f"**{file_type.capitalize()}**", inline=True)
            success_embed.add_field(name="📈 Éléments", value=f"`{len(data)}`", inline=True)
            success_embed.add_field(name="📬 Envoyé à", value=target_user.mention, inline=True)
            success_embed.set_footer(text=f"Exporté par {ctx.author.name}", icon_url=ctx.author.avatar.url if ctx.author.avatar else None)
            
            await message.edit(embed=success_embed)
        
        except asyncio.TimeoutError:
            await message.clear_reactions()
            timeout_embed = discord.Embed(
                color=THEME_COLORS["warning"],
                description="⏰ **Temps écoulé.** L'opération a été annulée."
            )
            await message.edit(embed=timeout_embed)


    @bot.command(name="bulk_role", aliases=["assign_roles"])
    @commands.has_any_role(*ADMIN_ROLES)
    async def bulk_role(ctx, role: discord.Role, *users):
        """
        Assigne un rôle à plusieurs utilisateurs en une seule commande.
        
        Usage: !bulk_role @Role @user1 @user2 ID3 ID4 ...
        
        Exemples:
        - !bulk_role @Membre @John @Jane
        - !bulk_role @Traducteur 123456789 987654321
        - !bulk_role @Éditeur @User1 123456789 @User2
        """
        if not users:
            embed = discord.Embed(
                color=THEME_COLORS["error"],
                timestamp=datetime.now()
            )
            embed.description = (
                "```ansi\n"
                "\u001b[1;31m╔═══════════════════════════════════════╗\u001b[0m\n"
                "\u001b[1;31m║\u001b[0m       \u001b[1;37m❌ Erreur de Syntaxe\u001b[0m          \u001b[1;31m║\u001b[0m\n"
                "\u001b[1;31m╚═══════════════════════════════════════╝\u001b[0m\n"
                "```\n"
                "**Vous devez spécifier au moins un utilisateur !**\n\n"
                "**Usage:** `!bulk_role @Rôle @user1 @user2 ID3`\n"
                "**Exemples:**\n"
                "• `!bulk_role @Membre @John @Jane`\n"
                "• `!bulk_role @Traducteur 123456789 987654321`"
            )
            embed.set_footer(text=f"Demandé par {ctx.author.name}", icon_url=ctx.author.avatar.url if ctx.author.avatar else None)
            await ctx.send(embed=embed)
            return
        
        # Message de traitement
        processing_embed = discord.Embed(
            color=THEME_COLORS["info"],
            timestamp=datetime.now()
        )
        processing_embed.description = (
            "```ansi\n"
            "\u001b[1;34m╔═══════════════════════════════════════╗\u001b[0m\n"
            "\u001b[1;34m║\u001b[0m       \u001b[1;37m⏳ Traitement en cours\u001b[0m         \u001b[1;34m║\u001b[0m\n"
            "\u001b[1;34m╚═══════════════════════════════════════╝\u001b[0m\n"
            "```\n"
            f"Attribution du rôle {role.mention} en cours..."
        )
        processing_msg = await ctx.send(embed=processing_embed)
        
        # Listes pour suivre les résultats
        success_list = []
        already_have = []
        not_found = []
        errors = []
        
        for user_identifier in users:
            try:
                # Essayer de récupérer l'utilisateur
                member = None
                
                # Si c'est une mention
                if user_identifier.startswith('<@') and user_identifier.endswith('>'):
                    user_id = int(user_identifier.strip('<@!>'))
                    member = ctx.guild.get_member(user_id)
                # Si c'est un ID numérique
                elif user_identifier.isdigit():
                    member = ctx.guild.get_member(int(user_identifier))
                # Sinon, essayer de chercher par nom
                else:
                    member = discord.utils.get(ctx.guild.members, name=user_identifier)
                
                if member is None:
                    not_found.append(user_identifier)
                    continue
                
                # Vérifier si le membre a déjà le rôle
                if role in member.roles:
                    already_have.append(member)
                    continue
                
                # Ajouter le rôle
                await member.add_roles(role)
                success_list.append(member)
                
                # Petit délai pour éviter le rate limiting
                await asyncio.sleep(0.5)
                
            except ValueError:
                not_found.append(user_identifier)
            except discord.Forbidden:
                errors.append(f"{user_identifier} (permissions insuffisantes)")
            except Exception as e:
                errors.append(f"{user_identifier} ({str(e)})")
        
        # Créer l'embed de résultat
        result_embed = discord.Embed(
            color=THEME_COLORS["success"] if success_list else THEME_COLORS["warning"],
            timestamp=datetime.now()
        )
        
        result_embed.description = (
            "```ansi\n"
            "\u001b[1;32m╔═══════════════════════════════════════╗\u001b[0m\n"
            "\u001b[1;32m║\u001b[0m       \u001b[1;37m✅ Attribution Terminée\u001b[0m        \u001b[1;32m║\u001b[0m\n"
            "\u001b[1;32m╚═══════════════════════════════════════╝\u001b[0m\n"
            "```"
        )
        
        result_embed.add_field(
            name=f"🎯 Rôle attribué",
            value=role.mention,
            inline=False
        )
        
        # Résumé statistique
        stats_text = (
            f"✅ **Succès:** `{len(success_list)}`\n"
            f"⚠️ **Déjà possédé:** `{len(already_have)}`\n"
            f"❌ **Non trouvés:** `{len(not_found)}`\n"
            f"🚫 **Erreurs:** `{len(errors)}`"
        )
        result_embed.add_field(name="📊 Statistiques", value=stats_text, inline=False)
        
        # Détails des succès
        if success_list:
            success_text = "\n".join([f"• {m.mention}" for m in success_list[:10]])
            if len(success_list) > 10:
                success_text += f"\n*... et {len(success_list) - 10} autre(s)*"
            result_embed.add_field(name="✅ Rôle ajouté à", value=success_text, inline=True)
        
        # Détails des membres ayant déjà le rôle
        if already_have:
            already_text = "\n".join([f"• {m.mention}" for m in already_have[:10]])
            if len(already_have) > 10:
                already_text += f"\n*... et {len(already_have) - 10} autre(s)*"
            result_embed.add_field(name="⚠️ Possédaient déjà", value=already_text, inline=True)
        
        # Détails des non trouvés
        if not_found:
            not_found_text = "\n".join([f"• `{u}`" for u in not_found[:10]])
            if len(not_found) > 10:
                not_found_text += f"\n*... et {len(not_found) - 10} autre(s)*"
            result_embed.add_field(name="❌ Non trouvés", value=not_found_text, inline=True)
        
        # Détails des erreurs
        if errors:
            errors_text = "\n".join([f"• {e}" for e in errors[:5]])
            if len(errors) > 5:
                errors_text += f"\n*... et {len(errors) - 5} autre(s)*"
            result_embed.add_field(name="🚫 Erreurs", value=errors_text, inline=True)
        
        result_embed.set_footer(
            text=f"Exécuté par {ctx.author.name}",
            icon_url=ctx.author.avatar.url if ctx.author.avatar else None
        )
        
        await processing_msg.edit(embed=result_embed)
        
        # Log l'action
        logging.info(f"Bulk role assignment: {role.name} to {len(success_list)} users by {ctx.author.name}")

    @bot.command(name="multi_bulk_role", aliases=["assign_multi_roles"])
    @commands.has_any_role(*ADMIN_ROLES)
    async def multi_bulk_role(ctx, *args):
        """
        Assigne plusieurs rôles à plusieurs utilisateurs en une seule commande.
        
        Usage: !multi_bulk_role @Role1 @Role2 @Role3 - @user1 @user2 ID3 ID4 ...
        
        Le séparateur "-" (tiret) est obligatoire pour séparer les rôles des utilisateurs.
        
        Exemples:
        - !multi_bulk_role @Membre @Traducteur - @John @Jane
        - !multi_bulk_role @Role1 @Role2 @Role3 - 123456789 987654321
        - !multi_bulk_role @Éditeur @Correcteur - @User1 123456789 @User2
        """
        if not args or '-' not in args:
            embed = discord.Embed(
                color=THEME_COLORS["error"],
                timestamp=datetime.now()
            )
            embed.description = (
                "```ansi\n"
                "\u001b[1;31m╔═══════════════════════════════════════╗\u001b[0m\n"
                "\u001b[1;31m║\u001b[0m       \u001b[1;37m❌ Erreur de Syntaxe\u001b[0m          \u001b[1;31m║\u001b[0m\n"
                "\u001b[1;31m╚═══════════════════════════════════════╝\u001b[0m\n"
                "```\n"
                "**Vous devez utiliser le séparateur `-` (tiret) !**\n\n"
                "**Usage:** `!multi_bulk_role @Role1 @Role2 - @user1 @user2`\n"
                "**Exemples:**\n"
                "• `!multi_bulk_role @Membre @Traducteur - @John @Jane`\n"
                "• `!multi_bulk_role @Role1 @Role2 @Role3 - 123456789 987654321`"
            )
            embed.set_footer(text=f"Demandé par {ctx.author.name}", icon_url=ctx.author.avatar.url if ctx.author.avatar else None)
            await ctx.send(embed=embed)
            return
        
        # Séparer les rôles et les utilisateurs
        separator_index = args.index('-')
        role_args = args[:separator_index]
        user_args = args[separator_index + 1:]
        
        if not role_args:
            embed = discord.Embed(
                color=THEME_COLORS["error"],
                timestamp=datetime.now()
            )
            embed.description = "❌ **Aucun rôle spécifié avant le séparateur `-` !**"
            await ctx.send(embed=embed)
            return
        
        if not user_args:
            embed = discord.Embed(
                color=THEME_COLORS["error"],
                timestamp=datetime.now()
            )
            embed.description = "❌ **Aucun utilisateur spécifié après le séparateur `-` !**"
            await ctx.send(embed=embed)
            return
        
        # Récupérer les rôles
        roles = []
        invalid_roles = []
        for role_arg in role_args:
            # Essayer de récupérer le rôle
            role = None
            if role_arg.startswith('<@&') and role_arg.endswith('>'):
                role_id = int(role_arg.strip('<@&>'))
                role = ctx.guild.get_role(role_id)
            elif role_arg.isdigit():
                role = ctx.guild.get_role(int(role_arg))
            else:
                role = discord.utils.get(ctx.guild.roles, name=role_arg)
            
            if role:
                roles.append(role)
            else:
                invalid_roles.append(role_arg)
        
        if invalid_roles:
            embed = discord.Embed(
                color=THEME_COLORS["error"],
                timestamp=datetime.now()
            )
            embed.description = f"❌ **Rôle(s) invalide(s) :** {', '.join(f'`{r}`' for r in invalid_roles)}"
            await ctx.send(embed=embed)
            return
        
        if not roles:
            embed = discord.Embed(
                color=THEME_COLORS["error"],
                timestamp=datetime.now()
            )
            embed.description = "❌ **Aucun rôle valide trouvé !**"
            await ctx.send(embed=embed)
            return
        
        # Message de traitement
        processing_embed = discord.Embed(
            color=THEME_COLORS["info"],
            timestamp=datetime.now()
        )
        role_mentions = ", ".join([r.mention for r in roles])
        processing_embed.description = (
            "```ansi\n"
            "\u001b[1;34m╔═══════════════════════════════════════╗\u001b[0m\n"
            "\u001b[1;34m║\u001b[0m       \u001b[1;37m⏳ Traitement en cours\u001b[0m         \u001b[1;34m║\u001b[0m\n"
            "\u001b[1;34m╚═══════════════════════════════════════╝\u001b[0m\n"
            "```\n"
            f"Attribution des rôles {role_mentions} en cours..."
        )
        processing_msg = await ctx.send(embed=processing_embed)
        
        # Listes pour suivre les résultats
        success_list = []
        partial_success = []  # Utilisateurs qui avaient déjà certains rôles
        already_have_all = []
        not_found = []
        errors = []
        
        for user_identifier in user_args:
            try:
                # Essayer de récupérer l'utilisateur
                member = None
                
                if user_identifier.startswith('<@') and user_identifier.endswith('>'):
                    user_id = int(user_identifier.strip('<@!>'))
                    member = ctx.guild.get_member(user_id)
                elif user_identifier.isdigit():
                    member = ctx.guild.get_member(int(user_identifier))
                else:
                    member = discord.utils.get(ctx.guild.members, name=user_identifier)
                
                if member is None:
                    not_found.append(user_identifier)
                    continue
                
                # Vérifier quels rôles le membre possède déjà
                roles_to_add = [r for r in roles if r not in member.roles]
                roles_already_had = [r for r in roles if r in member.roles]
                
                if not roles_to_add:
                    # Le membre a déjà tous les rôles
                    already_have_all.append(member)
                    continue
                
                # Ajouter les rôles manquants
                await member.add_roles(*roles_to_add)
                
                if roles_already_had:
                    partial_success.append((member, len(roles_to_add), len(roles_already_had)))
                else:
                    success_list.append(member)
                
                # Petit délai pour éviter le rate limiting
                await asyncio.sleep(0.5)
                
            except ValueError:
                not_found.append(user_identifier)
            except discord.Forbidden:
                errors.append(f"{user_identifier} (permissions insuffisantes)")
            except Exception as e:
                errors.append(f"{user_identifier} ({str(e)})")
        
        # Créer l'embed de résultat
        result_embed = discord.Embed(
            color=THEME_COLORS["success"] if (success_list or partial_success) else THEME_COLORS["warning"],
            timestamp=datetime.now()
        )
        
        result_embed.description = (
            "```ansi\n"
            "\u001b[1;32m╔═══════════════════════════════════════╗\u001b[0m\n"
            "\u001b[1;32m║\u001b[0m       \u001b[1;37m✅ Attribution Terminée\u001b[0m        \u001b[1;32m║\u001b[0m\n"
            "\u001b[1;32m╚═══════════════════════════════════════╝\u001b[0m\n"
            "```"
        )
        
        result_embed.add_field(
            name=f"🎯 Rôles attribués ({len(roles)})",
            value=role_mentions,
            inline=False
        )
        
        # Résumé statistique
        stats_text = (
            f"✅ **Succès complet:** `{len(success_list)}`\n"
            f"⚠️ **Succès partiel:** `{len(partial_success)}`\n"
            f"🔵 **Déjà tous les rôles:** `{len(already_have_all)}`\n"
            f"❌ **Non trouvés:** `{len(not_found)}`\n"
            f"🚫 **Erreurs:** `{len(errors)}`"
        )
        result_embed.add_field(name="📊 Statistiques", value=stats_text, inline=False)
        
        # Détails des succès complets
        if success_list:
            success_text = "\n".join([f"• {m.mention} (+{len(roles)} rôles)" for m in success_list[:10]])
            if len(success_list) > 10:
                success_text += f"\n*... et {len(success_list) - 10} autre(s)*"
            result_embed.add_field(name="✅ Succès complet", value=success_text, inline=True)
        
        # Détails des succès partiels
        if partial_success:
            partial_text = "\n".join([f"• {m.mention} (+{added}, avait {had})" for m, added, had in partial_success[:10]])
            if len(partial_success) > 10:
                partial_text += f"\n*... et {len(partial_success) - 10} autre(s)*"
            result_embed.add_field(name="⚠️ Succès partiel", value=partial_text, inline=True)
        
        # Détails des membres ayant déjà tous les rôles
        if already_have_all:
            already_text = "\n".join([f"• {m.mention}" for m in already_have_all[:10]])
            if len(already_have_all) > 10:
                already_text += f"\n*... et {len(already_have_all) - 10} autre(s)*"
            result_embed.add_field(name="🔵 Avaient déjà tout", value=already_text, inline=True)
        
        # Détails des non trouvés
        if not_found:
            not_found_text = "\n".join([f"• `{u}`" for u in not_found[:10]])
            if len(not_found) > 10:
                not_found_text += f"\n*... et {len(not_found) - 10} autre(s)*"
            result_embed.add_field(name="❌ Non trouvés", value=not_found_text, inline=True)
        
        # Détails des erreurs
        if errors:
            errors_text = "\n".join([f"• {e}" for e in errors[:5]])
            if len(errors) > 5:
                errors_text += f"\n*... et {len(errors) - 5} autre(s)*"
            result_embed.add_field(name="🚫 Erreurs", value=errors_text, inline=True)
        
        result_embed.set_footer(
            text=f"Exécuté par {ctx.author.name}",
            icon_url=ctx.author.avatar.url if ctx.author.avatar else None
        )
        
        await processing_msg.edit(embed=result_embed)
        
        # Log l'action
        roles_names = ", ".join([r.name for r in roles])
        total_success = len(success_list) + len(partial_success)
        logging.info(f"Multi bulk role assignment: {roles_names} to {total_success} users by {ctx.author.name}")

    @bot.command(name="bulk_remove_role", aliases=["remove_roles"])
    @commands.has_any_role(*ADMIN_ROLES)
    async def bulk_remove_role(ctx, role: discord.Role, *users):
        """
        Retire un rôle à plusieurs utilisateurs en une seule commande.
        
        Usage: !bulk_remove_role @Role @user1 @user2 ID3 ID4 ...
        
        Exemples:
        - !bulk_remove_role @Membre @John @Jane
        - !bulk_remove_role @Traducteur 123456789 987654321
        - !bulk_remove_role @Éditeur @User1 123456789 @User2
        """
        if not users:
            embed = discord.Embed(
                color=THEME_COLORS["error"],
                timestamp=datetime.now()
            )
            embed.description = (
                "```ansi\n"
                "\u001b[1;31m╔═══════════════════════════════════════╗\u001b[0m\n"
                "\u001b[1;31m║\u001b[0m       \u001b[1;37m❌ Erreur de Syntaxe\u001b[0m          \u001b[1;31m║\u001b[0m\n"
                "\u001b[1;31m╚═══════════════════════════════════════╝\u001b[0m\n"
                "```\n"
                "**Vous devez spécifier au moins un utilisateur !**\n\n"
                "**Usage:** `!bulk_remove_role @Rôle @user1 @user2 ID3`\n"
                "**Exemples:**\n"
                "• `!bulk_remove_role @Membre @John @Jane`\n"
                "• `!bulk_remove_role @Traducteur 123456789 987654321`"
            )
            embed.set_footer(text=f"Demandé par {ctx.author.name}", icon_url=ctx.author.avatar.url if ctx.author.avatar else None)
            await ctx.send(embed=embed)
            return
        
        # Message de traitement
        processing_embed = discord.Embed(
            color=THEME_COLORS["info"],
            timestamp=datetime.now()
        )
        processing_embed.description = (
            "```ansi\n"
            "\u001b[1;34m╔═══════════════════════════════════════╗\u001b[0m\n"
            "\u001b[1;34m║\u001b[0m       \u001b[1;37m⏳ Traitement en cours\u001b[0m         \u001b[1;34m║\u001b[0m\n"
            "\u001b[1;34m╚═══════════════════════════════════════╝\u001b[0m\n"
            "```\n"
            f"Retrait du rôle {role.mention} en cours..."
        )
        processing_msg = await ctx.send(embed=processing_embed)
        
        # Listes pour suivre les résultats
        success_list = []
        dont_have = []
        not_found = []
        errors = []
        
        for user_identifier in users:
            try:
                # Essayer de récupérer l'utilisateur
                member = None
                
                # Si c'est une mention
                if user_identifier.startswith('<@') and user_identifier.endswith('>'):
                    user_id = int(user_identifier.strip('<@!>'))
                    member = ctx.guild.get_member(user_id)
                # Si c'est un ID numérique
                elif user_identifier.isdigit():
                    member = ctx.guild.get_member(int(user_identifier))
                # Sinon, essayer de chercher par nom
                else:
                    member = discord.utils.get(ctx.guild.members, name=user_identifier)
                
                if member is None:
                    not_found.append(user_identifier)
                    continue
                
                # Vérifier si le membre a le rôle
                if role not in member.roles:
                    dont_have.append(member)
                    continue
                
                # Retirer le rôle
                await member.remove_roles(role)
                success_list.append(member)
                
                # Petit délai pour éviter le rate limiting
                await asyncio.sleep(0.5)
                
            except ValueError:
                not_found.append(user_identifier)
            except discord.Forbidden:
                errors.append(f"{user_identifier} (permissions insuffisantes)")
            except Exception as e:
                errors.append(f"{user_identifier} ({str(e)})")
        
        # Créer l'embed de résultat
        result_embed = discord.Embed(
            color=THEME_COLORS["success"] if success_list else THEME_COLORS["warning"],
            timestamp=datetime.now()
        )
        
        result_embed.description = (
            "```ansi\n"
            "\u001b[1;32m╔═══════════════════════════════════════╗\u001b[0m\n"
            "\u001b[1;32m║\u001b[0m       \u001b[1;37m✅ Retrait Terminé\u001b[0m             \u001b[1;32m║\u001b[0m\n"
            "\u001b[1;32m╚═══════════════════════════════════════╝\u001b[0m\n"
            "```"
        )
        
        result_embed.add_field(
            name=f"🎯 Rôle retiré",
            value=role.mention,
            inline=False
        )
        
        # Résumé statistique
        stats_text = (
            f"✅ **Succès:** `{len(success_list)}`\n"
            f"⚠️ **N'avaient pas:** `{len(dont_have)}`\n"
            f"❌ **Non trouvés:** `{len(not_found)}`\n"
            f"🚫 **Erreurs:** `{len(errors)}`"
        )
        result_embed.add_field(name="📊 Statistiques", value=stats_text, inline=False)
        
        # Détails des succès
        if success_list:
            success_text = "\n".join([f"• {m.mention}" for m in success_list[:10]])
            if len(success_list) > 10:
                success_text += f"\n*... et {len(success_list) - 10} autre(s)*"
            result_embed.add_field(name="✅ Rôle retiré à", value=success_text, inline=True)
        
        # Détails des membres n'ayant pas le rôle
        if dont_have:
            dont_have_text = "\n".join([f"• {m.mention}" for m in dont_have[:10]])
            if len(dont_have) > 10:
                dont_have_text += f"\n*... et {len(dont_have) - 10} autre(s)*"
            result_embed.add_field(name="⚠️ N'avaient pas", value=dont_have_text, inline=True)
        
        # Détails des non trouvés
        if not_found:
            not_found_text = "\n".join([f"• `{u}`" for u in not_found[:10]])
            if len(not_found) > 10:
                not_found_text += f"\n*... et {len(not_found) - 10} autre(s)*"
            result_embed.add_field(name="❌ Non trouvés", value=not_found_text, inline=True)
        
        # Détails des erreurs
        if errors:
            errors_text = "\n".join([f"• {e}" for e in errors[:5]])
            if len(errors) > 5:
                errors_text += f"\n*... et {len(errors) - 5} autre(s)*"
            result_embed.add_field(name="🚫 Erreurs", value=errors_text, inline=True)
        
        result_embed.set_footer(
            text=f"Exécuté par {ctx.author.name}",
            icon_url=ctx.author.avatar.url if ctx.author.avatar else None
        )
        
        await processing_msg.edit(embed=result_embed)
        
        # Log l'action
        logging.info(f"Bulk role removal: {role.name} from {len(success_list)} users by {ctx.author.name}")


    @bot.command(name="bulk_role_channel", aliases=["assign_role_channel"])
    @commands.has_any_role(*ADMIN_ROLES)
    async def bulk_role_channel(ctx, role: discord.Role, channel_id: str):
        """
        Assigne un rôle à tous les membres d'un canal qui ne l'ont pas encore.
        
        Usage: !bulk_role_channel @Role ID_DU_CANAL
        
        Exemples:
        - !bulk_role_channel @Traducteur 1234567890123456789
        - !bulk_role_channel @Membre 9876543210987654321
        """
        # Convertir l'ID en entier
        try:
            channel_id_int = int(channel_id)
        except ValueError:
            embed = discord.Embed(
                color=THEME_COLORS["error"],
                timestamp=datetime.now()
            )
            embed.description = (
                "```ansi\n"
                "\u001b[1;31m╔═══════════════════════════════════════╗\u001b[0m\n"
                "\u001b[1;31m║\u001b[0m       \u001b[1;37m❌ ID de canal invalide\u001b[0m        \u001b[1;31m║\u001b[0m\n"
                "\u001b[1;31m╚═══════════════════════════════════════╝\u001b[0m\n"
                "```\n"
                f"**L'ID `{channel_id}` n'est pas valide !**\n\n"
                "L'ID d'un canal doit être une série de chiffres.\n"
                "**Exemple:** `!bulk_role_channel @Role 1234567890123456789`"
            )
            embed.set_footer(text=f"Demandé par {ctx.author.name}", icon_url=ctx.author.avatar.url if ctx.author.avatar else None)
            await ctx.send(embed=embed)
            return
        
        # Récupérer le canal ou le thread (fil)
        channel = ctx.guild.get_channel(channel_id_int)
        if not channel:
            # Essayer de récupérer comme un thread/fil
            channel = ctx.guild.get_thread(channel_id_int)
        
        if not channel:
            embed = discord.Embed(
                color=THEME_COLORS["error"],
                timestamp=datetime.now()
            )
            embed.description = (
                "```ansi\n"
                "\u001b[1;31m╔═══════════════════════════════════════╗\u001b[0m\n"
                "\u001b[1;31m║\u001b[0m       \u001b[1;37m❌ Canal/Fil introuvable\u001b[0m       \u001b[1;31m║\u001b[0m\n"
                "\u001b[1;31m╚═══════════════════════════════════════╝\u001b[0m\n"
                "```\n"
                f"**Le canal ou fil avec l'ID `{channel_id}` est introuvable !**\n\n"
                "Vérifiez que :\n"
                "• L'ID est correct\n"
                "• Le canal/fil existe sur ce serveur\n"
                "• Le bot a accès au canal/fil"
            )
            await ctx.send(embed=embed)
            return
        
        # Message de traitement
        processing_embed = discord.Embed(
            color=THEME_COLORS["info"],
            timestamp=datetime.now()
        )
        processing_embed.description = (
            "```ansi\n"
            "\u001b[1;34m╔═══════════════════════════════════════╗\u001b[0m\n"
            "\u001b[1;34m║\u001b[0m       \u001b[1;37m⏳ Analyse en cours\u001b[0m            \u001b[1;34m║\u001b[0m\n"
            "\u001b[1;34m╚═══════════════════════════════════════╝\u001b[0m\n"
            "```\n"
            f"Analyse des membres du canal **#{channel.name}**...\n"
            f"Attribution du rôle {role.mention} en cours..."
        )
        processing_msg = await ctx.send(embed=processing_embed)
        
        # Récupérer tous les membres qui peuvent voir le canal/fil
        members_in_channel = []
        
        # Pour les threads, récupérer les membres différemment
        if isinstance(channel, discord.Thread):
            # Pour les threads, on récupère les membres qui peuvent voir le canal parent
            parent_channel = channel.parent
            if parent_channel:
                for member in ctx.guild.members:
                    if not member.bot and parent_channel.permissions_for(member).view_channel:
                        members_in_channel.append(member)
            else:
                # Si pas de parent (ne devrait pas arriver), on prend tous les membres non-bots
                members_in_channel = [m for m in ctx.guild.members if not m.bot]
        else:
            # Pour les canaux normaux
            for member in ctx.guild.members:
                if not member.bot and channel.permissions_for(member).view_channel:
                    members_in_channel.append(member)
        
        # Filtrer ceux qui n'ont pas le rôle
        members_without_role = [m for m in members_in_channel if role not in m.roles]
        
        if not members_without_role:
            embed = discord.Embed(
                color=THEME_COLORS["warning"],
                timestamp=datetime.now()
            )
            embed.description = (
                "```ansi\n"
                "\u001b[1;33m╔═══════════════════════════════════════╗\u001b[0m\n"
                "\u001b[1;33m║\u001b[0m       \u001b[1;37m⚠️ Aucun membre à traiter\u001b[0m      \u001b[1;33m║\u001b[0m\n"
                "\u001b[1;33m╚═══════════════════════════════════════╝\u001b[0m\n"
                "```\n"
                f"**Tous les membres de #{channel.name} ont déjà le rôle {role.mention} !**\n\n"
                f"📊 **Membres du canal:** {len(members_in_channel)}\n"
                f"✅ **Ont déjà le rôle:** {len(members_in_channel)}\n"
                f"❌ **Sans le rôle:** 0"
            )
            await processing_msg.edit(embed=embed)
            return
        
        # Attribuer le rôle
        success_list = []
        errors = []
        
        for member in members_without_role:
            try:
                await member.add_roles(role)
                success_list.append(member)
                await asyncio.sleep(0.5)
            except discord.Forbidden:
                errors.append(f"{member.mention} (permissions insuffisantes)")
            except Exception as e:
                errors.append(f"{member.mention} ({str(e)})")
        
        # Créer l'embed de résultat
        result_embed = discord.Embed(
            color=THEME_COLORS["success"] if success_list else THEME_COLORS["warning"],
            timestamp=datetime.now()
        )
        
        result_embed.description = (
            "```ansi\n"
            "\u001b[1;32m╔═══════════════════════════════════════╗\u001b[0m\n"
            "\u001b[1;32m║\u001b[0m       \u001b[1;37m✅ Attribution Terminée\u001b[0m        \u001b[1;32m║\u001b[0m\n"
            "\u001b[1;32m╚═══════════════════════════════════════╝\u001b[0m\n"
            "```"
        )
        
        result_embed.add_field(
            name=f"📺 Canal",
            value=f"#{channel.name} (`{channel.id}`)",
            inline=False
        )
        
        result_embed.add_field(
            name=f"🎯 Rôle attribué",
            value=role.mention,
            inline=False
        )
        
        # Résumé statistique
        already_had = len(members_in_channel) - len(members_without_role)
        stats_text = (
            f"📊 **Total membres du canal:** `{len(members_in_channel)}`\n"
            f"✅ **Rôle ajouté:** `{len(success_list)}`\n"
            f"🔵 **Avaient déjà:** `{already_had}`\n"
            f"🚫 **Erreurs:** `{len(errors)}`"
        )
        result_embed.add_field(name="📊 Statistiques", value=stats_text, inline=False)
        
        # Détails des succès
        if success_list:
            success_text = "\n".join([f"• {m.mention}" for m in success_list[:15]])
            if len(success_list) > 15:
                success_text += f"\n*... et {len(success_list) - 15} autre(s)*"
            result_embed.add_field(name="✅ Rôle ajouté à", value=success_text, inline=True)
        
        # Détails des erreurs
        if errors:
            errors_text = "\n".join([f"• {e}" for e in errors[:5]])
            if len(errors) > 5:
                errors_text += f"\n*... et {len(errors) - 5} autre(s)*"
            result_embed.add_field(name="🚫 Erreurs", value=errors_text, inline=True)
        
        result_embed.set_footer(
            text=f"Exécuté par {ctx.author.name}",
            icon_url=ctx.author.avatar.url if ctx.author.avatar else None
        )
        
        await processing_msg.edit(embed=result_embed)
        
        # Log l'action
        logging.info(f"Bulk role channel: {role.name} to {len(success_list)} members of #{channel.name} by {ctx.author.name}")

    @bot.command(name="list_member_ids", aliases=["get_ids", "member_ids"])
    @commands.has_any_role(*ADMIN_ROLES)
    async def list_member_ids(ctx, target_id: str):
        """
        Liste tous les IDs des membres d'un canal, fil ou catégorie.
        
        Usage: !list_member_ids ID_CIBLE
        
        Exemples:
        - !list_member_ids 1234567890123456789  (canal)
        - !list_member_ids 9876543210987654321  (fil/thread)
        - !list_member_ids 5555555555555555555  (catégorie)
        """
        # Convertir l'ID en entier
        try:
            target_id_int = int(target_id)
        except ValueError:
            embed = discord.Embed(
                color=THEME_COLORS["error"],
                timestamp=datetime.now()
            )
            embed.description = (
                "```ansi\n"
                "\u001b[1;31m╔═══════════════════════════════════════╗\u001b[0m\n"
                "\u001b[1;31m║\u001b[0m       \u001b[1;37m❌ ID invalide\u001b[0m                 \u001b[1;31m║\u001b[0m\n"
                "\u001b[1;31m╚═══════════════════════════════════════╝\u001b[0m\n"
                "```\n"
                f"**L'ID `{target_id}` n'est pas valide !**\n\n"
                "L'ID doit être une série de chiffres.\n"
                "**Exemple:** `!list_member_ids 1234567890123456789`"
            )
            embed.set_footer(text=f"Demandé par {ctx.author.name}", icon_url=ctx.author.avatar.url if ctx.author.avatar else None)
            await ctx.send(embed=embed)
            return
        
        # Message de traitement
        processing_embed = discord.Embed(
            color=THEME_COLORS["info"],
            timestamp=datetime.now()
        )
        processing_embed.description = (
            "```ansi\n"
            "\u001b[1;34m╔═══════════════════════════════════════╗\u001b[0m\n"
            "\u001b[1;34m║\u001b[0m       \u001b[1;37m⏳ Analyse en cours\u001b[0m            \u001b[1;34m║\u001b[0m\n"
            "\u001b[1;34m╚═══════════════════════════════════════╝\u001b[0m\n"
            "```\n"
            f"Recherche des membres pour l'ID `{target_id}`..."
        )
        processing_msg = await ctx.send(embed=processing_embed)
        
        # Essayer de récupérer comme canal, thread ou catégorie
        target = None
        target_type = None
        target_name = None
        
        # Essayer canal
        target = ctx.guild.get_channel(target_id_int)
        if target:
            if isinstance(target, discord.CategoryChannel):
                target_type = "Catégorie"
            else:
                target_type = "Canal"
            target_name = target.name
        
        # Essayer thread si pas trouvé
        if not target:
            target = ctx.guild.get_thread(target_id_int)
            if target:
                target_type = "Fil"
                target_name = target.name
        
        if not target:
            embed = discord.Embed(
                color=THEME_COLORS["error"],
                timestamp=datetime.now()
            )
            embed.description = (
                "```ansi\n"
                "\u001b[1;31m╔═══════════════════════════════════════╗\u001b[0m\n"
                "\u001b[1;31m║\u001b[0m       \u001b[1;37m❌ Cible introuvable\u001b[0m           \u001b[1;31m║\u001b[0m\n"
                "\u001b[1;31m╚═══════════════════════════════════════╝\u001b[0m\n"
                "```\n"
                f"**Le canal, fil ou catégorie avec l'ID `{target_id}` est introuvable !**\n\n"
                "Vérifiez que :\n"
                "• L'ID est correct\n"
                "• L'élément existe sur ce serveur\n"
                "• Le bot a accès à l'élément"
            )
            await processing_msg.edit(embed=embed)
            return
        
        # Récupérer les membres selon le type
        members_list = []
        
        if isinstance(target, discord.CategoryChannel):
            # Pour une catégorie, récupérer tous les membres qui peuvent voir au moins un canal de la catégorie
            member_set = set()
            for channel in target.channels:
                for member in ctx.guild.members:
                    if not member.bot and channel.permissions_for(member).view_channel:
                        member_set.add(member)
            members_list = list(member_set)
        
        elif isinstance(target, discord.Thread):
            # Pour un thread, récupérer les membres qui peuvent voir le canal parent
            parent_channel = target.parent
            if parent_channel:
                for member in ctx.guild.members:
                    if not member.bot and parent_channel.permissions_for(member).view_channel:
                        members_list.append(member)
            else:
                members_list = [m for m in ctx.guild.members if not m.bot]
        
        else:
            # Pour un canal normal
            for member in ctx.guild.members:
                if not member.bot and target.permissions_for(member).view_channel:
                    members_list.append(member)
        
        if not members_list:
            embed = discord.Embed(
                color=THEME_COLORS["warning"],
                timestamp=datetime.now()
            )
            embed.description = (
                "```ansi\n"
                "\u001b[1;33m╔═══════════════════════════════════════╗\u001b[0m\n"
                "\u001b[1;33m║\u001b[0m       \u001b[1;37m⚠️ Aucun membre trouvé\u001b[0m         \u001b[1;33m║\u001b[0m\n"
                "\u001b[1;33m╚═══════════════════════════════════════╝\u001b[0m\n"
                "```\n"
                f"**Aucun membre (hors bots) trouvé pour {target_type.lower()} `{target_name}` !**"
            )
            await processing_msg.edit(embed=embed)
            return
        
        # Trier par nom d'affichage pour faciliter la lecture
        members_list.sort(key=lambda m: m.display_name.lower())
        
        # Créer la liste des IDs
        ids_list = [str(m.id) for m in members_list]
        
        # Créer l'embed de résultat avec un style amélioré
        result_embed = discord.Embed(
            color=THEME_COLORS["success"],
            timestamp=datetime.now()
        )
        
        result_embed.description = (
            "```ansi\n"
            "\u001b[1;32m╔═══════════════════════════════════════╗\u001b[0m\n"
            "\u001b[1;32m║\u001b[0m       \u001b[1;37m✅ Liste des membres\u001b[0m           \u001b[1;32m║\u001b[0m\n"
            "\u001b[1;32m╚═══════════════════════════════════════╝\u001b[0m\n"
            "```"
        )
        
        # Ajouter la photo de profil du premier membre comme thumbnail
        if members_list:
            result_embed.set_thumbnail(url=members_list[0].display_avatar.url)
        
        result_embed.add_field(
            name=f"📺 {target_type}",
            value=f"**{target_name}** (`{target_id}`)",
            inline=False
        )
        
        result_embed.add_field(
            name="📊 Total",
            value=f"`{len(members_list)}` membre(s) (hors bots)",
            inline=False
        )
        
        # Afficher les premiers membres avec leurs pseudos Discord et IDs (max 15)
        if members_list:
            preview_lines = []
            for member in members_list[:15]:
                # Utiliser display_name (le pseudo Discord affiché)
                display = member.display_name
                # Si le pseudo est différent du nom d'utilisateur, montrer les deux
                if display != member.name:
                    preview_lines.append(f"• **{display}** (@{member.name}) → `{member.id}`")
                else:
                    preview_lines.append(f"• **{display}** → `{member.id}`")
            
            preview_text = "\n".join(preview_lines)
            if len(members_list) > 15:
                preview_text += f"\n\n*... et {len(members_list) - 15} autre(s)*"
            
            result_embed.add_field(
                name="👥 Aperçu des membres", 
                value=preview_text, 
                inline=False
            )
        
        # Format copier-coller pour les commandes
        ids_formatted = " ".join(ids_list)
        
        # Si la liste est trop longue, créer un fichier
        if len(ids_formatted) > 1000:
            # Créer un fichier texte
            file_content = f"# Liste des IDs des membres de {target_name}\n"
            file_content += f"# Type: {target_type}\n"
            file_content += f"# ID: {target_id}\n"
            file_content += f"# Total: {len(members_list)} membre(s)\n"
            file_content += f"# Généré le: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            
            file_content += "# Format liste détaillée (un par ligne avec pseudos)\n"
            for member in members_list:
                display = member.display_name
                if display != member.name:
                    file_content += f"{member.id}  # {display} (@{member.name})\n"
                else:
                    file_content += f"{member.id}  # {display}\n"
            
            file_content += f"\n# Format commande (tous sur une ligne)\n"
            file_content += ids_formatted + "\n"
            
            file_content += f"\n# Format pour bulk_role\n"
            file_content += f"!bulk_role @ROLE {ids_formatted}\n"
            
            file_content += f"\n# Format pour multi_bulk_role\n"
            file_content += f"!multi_bulk_role @ROLE1 @ROLE2 - {ids_formatted}\n"
            
            # Sauvegarder le fichier
            filename = f"member_ids_{target_id}.txt"
            filepath = f"/home/claude/{filename}"
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(file_content)
            
            result_embed.add_field(
                name="📄 Fichier généré",
                value=f"La liste complète est disponible dans le fichier ci-dessous.\n"
                      f"✅ Contient les pseudos Discord complets\n"
                      f"✅ Inclut les exemples de commandes",
                inline=False
            )
            
            # Ajouter une petite galerie de photos de profil (max 5 membres)
            gallery_text = "**Aperçu des membres :**\n"
            for member in members_list[:5]:
                gallery_text += f"[{member.display_name}]({member.display_avatar.url}) "
            if len(members_list) > 5:
                gallery_text += f"\n*... et {len(members_list) - 5} autre(s)*"
            
            result_embed.add_field(
                name="🖼️ Photos de profil",
                value=gallery_text,
                inline=False
            )
            
            result_embed.set_footer(
                text=f"Exécuté par {ctx.author.name}",
                icon_url=ctx.author.avatar.url if ctx.author.avatar else None
            )
            
            await processing_msg.edit(embed=result_embed)
            await ctx.send(file=discord.File(filepath, filename=filename))
        
        else:
            # Afficher directement dans l'embed
            result_embed.add_field(
                name="📋 Format copier-coller",
                value=f"```\n{ids_formatted}\n```",
                inline=False
            )
            
            # Exemples de commandes avec aperçu visuel
            examples_text = (
                f"**Exemples d'utilisation :**\n"
                f"```\n"
                f"!bulk_role @ROLE {ids_formatted[:50]}...\n"
                f"!multi_bulk_role @ROLE1 @ROLE2 - {ids_formatted[:50]}...\n"
                f"```"
            )
            result_embed.add_field(name="💡 Utilisation", value=examples_text, inline=False)
            
            # Ajouter une petite galerie de photos de profil
            if len(members_list) <= 10:
                gallery_text = "**Aperçu des membres :**\n"
                for member in members_list:
                    gallery_text += f"[{member.display_name}]({member.display_avatar.url}) "
                
                result_embed.add_field(
                    name="🖼️ Photos de profil",
                    value=gallery_text,
                    inline=False
                )
            
            result_embed.set_footer(
                text=f"Exécuté par {ctx.author.name} • {len(members_list)} membre(s) trouvé(s)",
                icon_url=ctx.author.avatar.url if ctx.author.avatar else None
            )
            
            await processing_msg.edit(embed=result_embed)
        
        # Log l'action
        logging.info(f"List member IDs: {target_type} {target_name} ({len(members_list)} members) by {ctx.author.name}")

    @bot.command(name="multi_bulk_remove_role", aliases=["remove_multi_roles"])
    @commands.has_any_role(*ADMIN_ROLES)
    async def multi_bulk_remove_role(ctx, *args):
        """
        Retire plusieurs rôles à plusieurs utilisateurs en une seule commande.
        
        Usage: !multi_bulk_remove_role @Role1 @Role2 @Role3 - @user1 @user2 ID3 ID4 ...
        
        Le séparateur "-" (tiret) est obligatoire pour séparer les rôles des utilisateurs.
        
        Exemples:
        - !multi_bulk_remove_role @Membre @Traducteur - @John @Jane
        - !multi_bulk_remove_role @Role1 @Role2 @Role3 - 123456789 987654321
        - !multi_bulk_remove_role @Éditeur @Correcteur - @User1 123456789 @User2
        """
        if not args or '-' not in args:
            embed = discord.Embed(
                color=THEME_COLORS["error"],
                timestamp=datetime.now()
            )
            embed.description = (
                "```ansi\n"
                "\u001b[1;31m╔═══════════════════════════════════════╗\u001b[0m\n"
                "\u001b[1;31m║\u001b[0m       \u001b[1;37m❌ Erreur de Syntaxe\u001b[0m          \u001b[1;31m║\u001b[0m\n"
                "\u001b[1;31m╚═══════════════════════════════════════╝\u001b[0m\n"
                "```\n"
                "**Vous devez utiliser le séparateur `-` (tiret) !**\n\n"
                "**Usage:** `!multi_bulk_remove_role @Role1 @Role2 - @user1 @user2`\n"
                "**Exemples:**\n"
                "• `!multi_bulk_remove_role @Membre @Traducteur - @John @Jane`\n"
                "• `!multi_bulk_remove_role @Role1 @Role2 @Role3 - 123456789 987654321`"
            )
            embed.set_footer(text=f"Demandé par {ctx.author.name}", icon_url=ctx.author.avatar.url if ctx.author.avatar else None)
            await ctx.send(embed=embed)
            return
        
        # Séparer les rôles et les utilisateurs
        separator_index = args.index('-')
        role_args = args[:separator_index]
        user_args = args[separator_index + 1:]
        
        if not role_args:
            embed = discord.Embed(
                color=THEME_COLORS["error"],
                timestamp=datetime.now()
            )
            embed.description = "❌ **Aucun rôle spécifié avant le séparateur `-` !**"
            await ctx.send(embed=embed)
            return
        
        if not user_args:
            embed = discord.Embed(
                color=THEME_COLORS["error"],
                timestamp=datetime.now()
            )
            embed.description = "❌ **Aucun utilisateur spécifié après le séparateur `-` !**"
            await ctx.send(embed=embed)
            return
        
        # Récupérer les rôles
        roles = []
        invalid_roles = []
        for role_arg in role_args:
            role = None
            if role_arg.startswith('<@&') and role_arg.endswith('>'):
                role_id = int(role_arg.strip('<@&>'))
                role = ctx.guild.get_role(role_id)
            elif role_arg.isdigit():
                role = ctx.guild.get_role(int(role_arg))
            else:
                role = discord.utils.get(ctx.guild.roles, name=role_arg)
            
            if role:
                roles.append(role)
            else:
                invalid_roles.append(role_arg)
        
        if invalid_roles:
            embed = discord.Embed(
                color=THEME_COLORS["error"],
                timestamp=datetime.now()
            )
            embed.description = f"❌ **Rôle(s) invalide(s) :** {', '.join(f'`{r}`' for r in invalid_roles)}"
            await ctx.send(embed=embed)
            return
        
        if not roles:
            embed = discord.Embed(
                color=THEME_COLORS["error"],
                timestamp=datetime.now()
            )
            embed.description = "❌ **Aucun rôle valide trouvé !**"
            await ctx.send(embed=embed)
            return
        
        # Message de traitement
        processing_embed = discord.Embed(
            color=THEME_COLORS["info"],
            timestamp=datetime.now()
        )
        role_mentions = ", ".join([r.mention for r in roles])
        processing_embed.description = (
            "```ansi\n"
            "\u001b[1;34m╔═══════════════════════════════════════╗\u001b[0m\n"
            "\u001b[1;34m║\u001b[0m       \u001b[1;37m⏳ Traitement en cours\u001b[0m         \u001b[1;34m║\u001b[0m\n"
            "\u001b[1;34m╚═══════════════════════════════════════╝\u001b[0m\n"
            "```\n"
            f"Retrait des rôles {role_mentions} en cours..."
        )
        processing_msg = await ctx.send(embed=processing_embed)
        
        # Listes pour suivre les résultats
        success_list = []
        partial_success = []  # Utilisateurs qui n'avaient pas certains rôles
        dont_have_any = []
        not_found = []
        errors = []
        
        for user_identifier in user_args:
            try:
                # Essayer de récupérer l'utilisateur
                member = None
                
                if user_identifier.startswith('<@') and user_identifier.endswith('>'):
                    user_id = int(user_identifier.strip('<@!>'))
                    member = ctx.guild.get_member(user_id)
                elif user_identifier.isdigit():
                    member = ctx.guild.get_member(int(user_identifier))
                else:
                    member = discord.utils.get(ctx.guild.members, name=user_identifier)
                
                if member is None:
                    not_found.append(user_identifier)
                    continue
                
                # Vérifier quels rôles le membre possède
                roles_to_remove = [r for r in roles if r in member.roles]
                roles_didnt_have = [r for r in roles if r not in member.roles]
                
                if not roles_to_remove:
                    # Le membre n'a aucun de ces rôles
                    dont_have_any.append(member)
                    continue
                
                # Retirer les rôles
                await member.remove_roles(*roles_to_remove)
                
                if roles_didnt_have:
                    partial_success.append((member, len(roles_to_remove), len(roles_didnt_have)))
                else:
                    success_list.append(member)
                
                # Petit délai pour éviter le rate limiting
                await asyncio.sleep(0.5)
                
            except ValueError:
                not_found.append(user_identifier)
            except discord.Forbidden:
                errors.append(f"{user_identifier} (permissions insuffisantes)")
            except Exception as e:
                errors.append(f"{user_identifier} ({str(e)})")
        
        # Créer l'embed de résultat
        result_embed = discord.Embed(
            color=THEME_COLORS["success"] if (success_list or partial_success) else THEME_COLORS["warning"],
            timestamp=datetime.now()
        )
        
        result_embed.description = (
            "```ansi\n"
            "\u001b[1;32m╔═══════════════════════════════════════╗\u001b[0m\n"
            "\u001b[1;32m║\u001b[0m       \u001b[1;37m✅ Retrait Terminé\u001b[0m             \u001b[1;32m║\u001b[0m\n"
            "\u001b[1;32m╚═══════════════════════════════════════╝\u001b[0m\n"
            "```"
        )
        
        result_embed.add_field(
            name=f"🎯 Rôles retirés ({len(roles)})",
            value=role_mentions,
            inline=False
        )
        
        # Résumé statistique
        stats_text = (
            f"✅ **Succès complet:** `{len(success_list)}`\n"
            f"⚠️ **Succès partiel:** `{len(partial_success)}`\n"
            f"🔵 **N'avaient aucun rôle:** `{len(dont_have_any)}`\n"
            f"❌ **Non trouvés:** `{len(not_found)}`\n"
            f"🚫 **Erreurs:** `{len(errors)}`"
        )
        result_embed.add_field(name="📊 Statistiques", value=stats_text, inline=False)
        
        # Détails des succès complets
        if success_list:
            success_text = "\n".join([f"• {m.mention} (-{len(roles)} rôles)" for m in success_list[:10]])
            if len(success_list) > 10:
                success_text += f"\n*... et {len(success_list) - 10} autre(s)*"
            result_embed.add_field(name="✅ Succès complet", value=success_text, inline=True)
        
        # Détails des succès partiels
        if partial_success:
            partial_text = "\n".join([f"• {m.mention} (-{removed}, n'avait pas {didnt})" for m, removed, didnt in partial_success[:10]])
            if len(partial_success) > 10:
                partial_text += f"\n*... et {len(partial_success) - 10} autre(s)*"
            result_embed.add_field(name="⚠️ Succès partiel", value=partial_text, inline=True)
        
        # Détails des membres n'ayant aucun rôle
        if dont_have_any:
            dont_have_text = "\n".join([f"• {m.mention}" for m in dont_have_any[:10]])
            if len(dont_have_any) > 10:
                dont_have_text += f"\n*... et {len(dont_have_any) - 10} autre(s)*"
            result_embed.add_field(name="🔵 N'avaient aucun rôle", value=dont_have_text, inline=True)
        
        # Détails des non trouvés
        if not_found:
            not_found_text = "\n".join([f"• `{u}`" for u in not_found[:10]])
            if len(not_found) > 10:
                not_found_text += f"\n*... et {len(not_found) - 10} autre(s)*"
            result_embed.add_field(name="❌ Non trouvés", value=not_found_text, inline=True)
        
        # Détails des erreurs
        if errors:
            errors_text = "\n".join([f"• {e}" for e in errors[:5]])
            if len(errors) > 5:
                errors_text += f"\n*... et {len(errors) - 5} autre(s)*"
            result_embed.add_field(name="🚫 Erreurs", value=errors_text, inline=True)
        
        result_embed.set_footer(
            text=f"Exécuté par {ctx.author.name}",
            icon_url=ctx.author.avatar.url if ctx.author.avatar else None
        )
        
        await processing_msg.edit(embed=result_embed)
        
        # Log l'action
        roles_names = ", ".join([r.name for r in roles])
        total_success = len(success_list) + len(partial_success)
        logging.info(f"Multi bulk role removal: {roles_names} from {total_success} users by {ctx.author.name}")


    @bot.command(name="multi_bulk_role_channel", aliases=["assign_multi_roles_channel"])
    @commands.has_any_role(*ADMIN_ROLES)
    async def multi_bulk_role_channel(ctx, *args):
        """
        Assigne plusieurs rôles à tous les membres d'un canal qui ne les ont pas encore.
        
        Usage: !multi_bulk_role_channel @Role1 @Role2 @Role3 - ID_DU_CANAL
        
        Le séparateur "-" (tiret) est obligatoire pour séparer les rôles de l'ID du canal.
        
        Exemples:
        - !multi_bulk_role_channel @Traducteur @Membre - 1234567890123456789
        - !multi_bulk_role_channel @Role1 @Role2 @Role3 - 9876543210987654321
        """
        if not args or '-' not in args:
            embed = discord.Embed(
                color=THEME_COLORS["error"],
                timestamp=datetime.now()
            )
            embed.description = (
                "```ansi\n"
                "\u001b[1;31m╔═══════════════════════════════════════╗\u001b[0m\n"
                "\u001b[1;31m║\u001b[0m       \u001b[1;37m❌ Erreur de Syntaxe\u001b[0m          \u001b[1;31m║\u001b[0m\n"
                "\u001b[1;31m╚═══════════════════════════════════════╝\u001b[0m\n"
                "```\n"
                "**Vous devez utiliser le séparateur `-` (tiret) !**\n\n"
                "**Usage:** `!multi_bulk_role_channel @Role1 @Role2 - ID_CANAL`\n"
                "**Exemples:**\n"
                "• `!multi_bulk_role_channel @Membre @Traducteur - 1234567890`\n"
                "• `!multi_bulk_role_channel @Role1 @Role2 @Role3 - 9876543210`"
            )
            embed.set_footer(text=f"Demandé par {ctx.author.name}", icon_url=ctx.author.avatar.url if ctx.author.avatar else None)
            await ctx.send(embed=embed)
            return
        
        # Séparer les rôles et l'ID du canal
        separator_index = args.index('-')
        role_args = args[:separator_index]
        channel_args = args[separator_index + 1:]
        
        if not role_args:
            embed = discord.Embed(
                color=THEME_COLORS["error"],
                timestamp=datetime.now()
            )
            embed.description = "❌ **Aucun rôle spécifié avant le séparateur `-` !**"
            await ctx.send(embed=embed)
            return
        
        if not channel_args:
            embed = discord.Embed(
                color=THEME_COLORS["error"],
                timestamp=datetime.now()
            )
            embed.description = "❌ **Aucun ID de canal spécifié après le séparateur `-` !**"
            await ctx.send(embed=embed)
            return
        
        # Récupérer l'ID du canal (premier argument après le -)
        channel_id_str = channel_args[0]
        
        # Convertir l'ID en entier
        try:
            channel_id_int = int(channel_id_str)
        except ValueError:
            embed = discord.Embed(
                color=THEME_COLORS["error"],
                timestamp=datetime.now()
            )
            embed.description = f"❌ **L'ID de canal `{channel_id_str}` n'est pas valide !**"
            await ctx.send(embed=embed)
            return
        
        # Récupérer le canal ou le thread (fil)
        channel = ctx.guild.get_channel(channel_id_int)
        if not channel:
            # Essayer de récupérer comme un thread/fil
            channel = ctx.guild.get_thread(channel_id_int)
        
        if not channel:
            embed = discord.Embed(
                color=THEME_COLORS["error"],
                timestamp=datetime.now()
            )
            embed.description = f"❌ **Le canal ou fil avec l'ID `{channel_id_str}` est introuvable !**"
            await ctx.send(embed=embed)
            return
        
        # Récupérer les rôles
        roles = []
        invalid_roles = []
        for role_arg in role_args:
            role = None
            if role_arg.startswith('<@&') and role_arg.endswith('>'):
                role_id = int(role_arg.strip('<@&>'))
                role = ctx.guild.get_role(role_id)
            elif role_arg.isdigit():
                role = ctx.guild.get_role(int(role_arg))
            else:
                role = discord.utils.get(ctx.guild.roles, name=role_arg)
            
            if role:
                roles.append(role)
            else:
                invalid_roles.append(role_arg)
        
        if invalid_roles:
            embed = discord.Embed(
                color=THEME_COLORS["error"],
                timestamp=datetime.now()
            )
            embed.description = f"❌ **Rôle(s) invalide(s) :** {', '.join(f'`{r}`' for r in invalid_roles)}"
            await ctx.send(embed=embed)
            return
        
        if not roles:
            embed = discord.Embed(
                color=THEME_COLORS["error"],
                timestamp=datetime.now()
            )
            embed.description = "❌ **Aucun rôle valide trouvé !**"
            await ctx.send(embed=embed)
            return
        
        # Message de traitement
        processing_embed = discord.Embed(
            color=THEME_COLORS["info"],
            timestamp=datetime.now()
        )
        role_mentions = ", ".join([r.mention for r in roles])
        processing_embed.description = (
            "```ansi\n"
            "\u001b[1;34m╔═══════════════════════════════════════╗\u001b[0m\n"
            "\u001b[1;34m║\u001b[0m       \u001b[1;37m⏳ Analyse en cours\u001b[0m            \u001b[1;34m║\u001b[0m\n"
            "\u001b[1;34m╚═══════════════════════════════════════╝\u001b[0m\n"
            "```\n"
            f"Analyse des membres du canal **#{channel.name}**...\n"
            f"Attribution des rôles {role_mentions} en cours..."
        )
        processing_msg = await ctx.send(embed=processing_embed)
        
        # Récupérer tous les membres qui peuvent voir le canal/fil
        members_in_channel = []
        
        # Pour les threads, récupérer les membres différemment
        if isinstance(channel, discord.Thread):
            # Pour les threads, on récupère les membres qui peuvent voir le canal parent
            parent_channel = channel.parent
            if parent_channel:
                for member in ctx.guild.members:
                    if not member.bot and parent_channel.permissions_for(member).view_channel:
                        members_in_channel.append(member)
            else:
                # Si pas de parent (ne devrait pas arriver), on prend tous les membres non-bots
                members_in_channel = [m for m in ctx.guild.members if not m.bot]
        else:
            # Pour les canaux normaux
            for member in ctx.guild.members:
                if not member.bot and channel.permissions_for(member).view_channel:
                    members_in_channel.append(member)
        
        # Listes pour suivre les résultats
        success_list = []
        partial_success = []
        already_have_all = []
        errors = []
        
        for member in members_in_channel:
            try:
                # Vérifier quels rôles le membre possède déjà
                roles_to_add = [r for r in roles if r not in member.roles]
                roles_already_had = [r for r in roles if r in member.roles]
                
                if not roles_to_add:
                    # Le membre a déjà tous les rôles
                    already_have_all.append(member)
                    continue
                
                # Ajouter les rôles manquants
                await member.add_roles(*roles_to_add)
                
                if roles_already_had:
                    partial_success.append((member, len(roles_to_add), len(roles_already_had)))
                else:
                    success_list.append(member)
                
                await asyncio.sleep(0.5)
                
            except discord.Forbidden:
                errors.append(f"{member.mention} (permissions insuffisantes)")
            except Exception as e:
                errors.append(f"{member.mention} ({str(e)})")
        
        # Créer l'embed de résultat
        result_embed = discord.Embed(
            color=THEME_COLORS["success"] if (success_list or partial_success) else THEME_COLORS["warning"],
            timestamp=datetime.now()
        )
        
        result_embed.description = (
            "```ansi\n"
            "\u001b[1;32m╔═══════════════════════════════════════╗\u001b[0m\n"
            "\u001b[1;32m║\u001b[0m       \u001b[1;37m✅ Attribution Terminée\u001b[0m        \u001b[1;32m║\u001b[0m\n"
            "\u001b[1;32m╚═══════════════════════════════════════╝\u001b[0m\n"
            "```"
        )
        
        result_embed.add_field(
            name=f"📺 Canal",
            value=f"#{channel.name} (`{channel.id}`)",
            inline=False
        )
        
        result_embed.add_field(
            name=f"🎯 Rôles attribués ({len(roles)})",
            value=role_mentions,
            inline=False
        )
        
        # Résumé statistique
        stats_text = (
            f"📊 **Total membres du canal:** `{len(members_in_channel)}`\n"
            f"✅ **Succès complet:** `{len(success_list)}`\n"
            f"⚠️ **Succès partiel:** `{len(partial_success)}`\n"
            f"🔵 **Avaient tous les rôles:** `{len(already_have_all)}`\n"
            f"🚫 **Erreurs:** `{len(errors)}`"
        )
        result_embed.add_field(name="📊 Statistiques", value=stats_text, inline=False)
        
        # Détails des succès complets
        if success_list:
            success_text = "\n".join([f"• {m.mention} (+{len(roles)} rôles)" for m in success_list[:10]])
            if len(success_list) > 10:
                success_text += f"\n*... et {len(success_list) - 10} autre(s)*"
            result_embed.add_field(name="✅ Succès complet", value=success_text, inline=True)
        
        # Détails des succès partiels
        if partial_success:
            partial_text = "\n".join([f"• {m.mention} (+{added}, avait {had})" for m, added, had in partial_success[:10]])
            if len(partial_success) > 10:
                partial_text += f"\n*... et {len(partial_success) - 10} autre(s)*"
            result_embed.add_field(name="⚠️ Succès partiel", value=partial_text, inline=True)
        
        # Détails des erreurs
        if errors:
            errors_text = "\n".join([f"• {e}" for e in errors[:5]])
            if len(errors) > 5:
                errors_text += f"\n*... et {len(errors) - 5} autre(s)*"
            result_embed.add_field(name="🚫 Erreurs", value=errors_text, inline=True)
        
        result_embed.set_footer(
            text=f"Exécuté par {ctx.author.name}",
            icon_url=ctx.author.avatar.url if ctx.author.avatar else None
        )
        
        await processing_msg.edit(embed=result_embed)
        
        # Log l'action
        roles_names = ", ".join([r.name for r in roles])
        total_success = len(success_list) + len(partial_success)
        logging.info(f"Multi bulk role channel: {roles_names} to {total_success} members of #{channel.name} by {ctx.author.name}")


def generate_progress_bar(progress, total, size=10):
    """Génère une barre de progression"""
    pct = progress / total if total > 0 else 0
    filled = int(size * pct)
    return '🟩' * filled + '⬜' * (size - filled)