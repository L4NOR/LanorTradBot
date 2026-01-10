# commands.py
import discord
from discord.ext import commands
from datetime import datetime
from config import CHANNELS, ROLES, COLORS
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

# Dictionnaire pour mapper les mangas aux salons
MANGA_CHANNELS = {
    "Tougen Anki": 1330144191816142941,
    "Tokyo Underworld": 1330143657264943266,
    "Satsudou": 1330142974646026371,
    "Ao No Exorcist": 1329589897920512020,
    "Catenaccio": 1330182024832614541
}

# Dictionnaire pour mapper les mangas aux rôles
MANGA_ROLES = {
    "Catenaccio": 1332429989085184010,
    "Satsudou": 1326778585478070283,
    "Ao No Exorcist": 1326778473079111763,
    "Tokyo Underworld": 1326778697218392149,
    "Tougen Anki": 1326778962143215677
}

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
        "emoji": "💬",
        "name": "Communauté",
        "description": "Reviews, théories et interactions",
        "color": 0x9B59B6,
        "commands": [
            {"name": "review", "usage": "!review <manga> <chap> <1-5> [msg]", "desc": "Laisser une review sur un chapitre"},
            {"name": "my_reviews", "usage": "!my_reviews", "desc": "Voir toutes vos reviews"},
            {"name": "chapter_reviews", "usage": "!chapter_reviews <manga> <chap>", "desc": "Voir les reviews d'un chapitre"},
            {"name": "theory", "usage": "!theory <manga> <théorie>", "desc": "Poster une théorie"},
            {"name": "theories", "usage": "!theories [manga]", "desc": "Lister les théories populaires"},
            {"name": "theory_info", "usage": "!theory_info <id>", "desc": "Détails d'une théorie"},
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
            {"name": "task_all", "usage": "!task_all", "desc": "Toutes les tâches en cours"},
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
            {"name": "theory_status", "usage": "!theory_status <id> <status>", "desc": "Changer statut théorie"},
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
}


def setup(bot):
    charger_etat_taches()
    global bot_instance
    bot_instance = bot
    bot.remove_command('help')
    
    # ==================== NOUVELLE COMMANDE HELP ====================
    
    @bot.command()
    async def help(ctx, *, command_name: str = None):
        """Affiche le menu d'aide interactif"""
        admin_roles = [1326417422663680090, 1330147432847114321, 1331346420883525682]
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
        for cat_key in ["general", "community", "badges", "shop", "giveaway"]:
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
    
    @bot.command()
    @commands.has_permissions(manage_messages=True)
    async def clear(ctx, amount: int):
        """Supprime un nombre spécifié de messages"""
        if amount <= 0:
            await ctx.send("Le nombre de messages doit être > 0.")
            return
        
        deleted = await ctx.channel.purge(limit=amount + 1)
        
        embed = discord.Embed(
            title="🗑️ Messages supprimés",
            description=f'**{len(deleted)-1}** messages ont été supprimés.',
            color=discord.Color.red()
        )
        await ctx.send(embed=embed, delete_after=5)
    
    @bot.command()
    @commands.has_permissions(kick_members=True)
    async def kick(ctx, member: discord.Member, *, reason=None):
        """Expulse un membre du serveur"""
        await member.kick(reason=reason)
        
        embed = discord.Embed(
            title="👢 Membre expulsé",
            description=f"{member.mention} a été expulsé.\n**Raison:** {reason or 'Non spécifiée'}",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
    
    @bot.command()
    @commands.has_permissions(ban_members=True)
    async def ban(ctx, member: discord.Member, *, reason=None):
        """Bannit un membre du serveur"""
        await member.ban(reason=reason)
        
        embed = discord.Embed(
            title="🔨 Membre banni",
            description=f"{member.mention} a été banni.\n**Raison:** {reason or 'Non spécifiée'}",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
    
    @bot.command()
    @commands.has_permissions(ban_members=True)
    async def unban(ctx, *, member):
        """Débannit un membre du serveur"""
        banned_users = await ctx.guild.bans()
        member_name, member_discriminator = member.split('#')
        
        for ban_entry in banned_users:
            user = ban_entry.user
            if (user.name, user.discriminator) == (member_name, member_discriminator):
                await ctx.guild.unban(user)
                
                embed = discord.Embed(
                    title="🔓 Membre débanni",
                    description=f"{user.mention} a été débanni.",
                    color=discord.Color.green()
                )
                await ctx.send(embed=embed)
                return
    
    @bot.command()
    @commands.has_permissions(kick_members=True)
    async def warn(ctx, member: discord.Member, *, reason=None):
        """Avertit un membre"""
        embed = discord.Embed(
            title="⚠️ Avertissement",
            description=f"{member.mention} a reçu un avertissement.\n**Raison:** {reason or 'Non spécifiée'}",
            color=discord.Color.orange()
        )
        await ctx.send(embed=embed)
    
    @bot.command()
    async def info(ctx):
        """Affiche les informations du serveur"""
        embed = discord.Embed(
            title=f"ℹ️ {ctx.guild.name}",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        embed.add_field(name="📊 Membres", value=ctx.guild.member_count, inline=True)
        embed.add_field(name="📅 Créé le", value=ctx.guild.created_at.strftime("%d/%m/%Y"), inline=True)
        embed.add_field(name="👑 Propriétaire", value=ctx.guild.owner.mention, inline=True)
        
        if ctx.guild.icon:
            embed.set_thumbnail(url=ctx.guild.icon.url)
        
        await ctx.send(embed=embed)
    
    @bot.command()
    async def userinfo(ctx, member: discord.Member = None):
        """Affiche les informations d'un utilisateur"""
        member = member or ctx.author
        roles = [role.mention for role in member.roles if role.name != "@everyone"]
        
        embed = discord.Embed(
            title=f"ℹ️ {member.name}",
            color=member.color,
            timestamp=datetime.now()
        )
        embed.add_field(name="📅 A rejoint", value=member.joined_at.strftime("%d/%m/%Y"), inline=True)
        embed.add_field(name="🔰 Compte créé", value=member.created_at.strftime("%d/%m/%Y"), inline=True)
        embed.add_field(name="🏷️ Rôles", value=" ".join(roles[:10]) if roles else "Aucun", inline=False)
        
        if member.avatar:
            embed.set_thumbnail(url=member.avatar.url)
        
        await ctx.send(embed=embed)
    
    @bot.command()
    async def ping(ctx):
        """Vérifie la latence du bot"""
        embed = discord.Embed(
            title="🏓 Pong!",
            description=f"Latence: **{round(bot.latency * 1000)}**ms",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)
    
    @bot.command()
    @commands.has_any_role(1326417422663680090, 1330147432847114321)
    async def task(ctx, action: str, manga: str, *chapitres: str):
        """Met à jour l'état d'une tâche pour un ou plusieurs chapitres"""
        actions_valides = ["clean", "trad", "check", "edit"]
        
        if action.lower() not in actions_valides:
            await ctx.send(f"❌ Action invalide. Actions possibles : {', '.join(actions_valides)}.")
            return
        
        chapitres_traites = []
        chapitres_erreur = []
        chapitres_complets = []
        
        manga_normalized = manga.strip()
        
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
        
        reponse = []
        if chapitres_traites:
            reponse.append(f"✅ Tâche **{action}** mise à jour pour **{manga_normalized}** chapitres : **{', '.join(chapitres_traites)}**")
        if chapitres_erreur:
            reponse.append(f"❌ Chapitres invalides ignorés : {', '.join(chapitres_erreur)}")
        if not chapitres_traites and not chapitres_erreur:
            reponse.append("❌ Aucun chapitre valide n'a été spécifié.")
        
        await ctx.send('\n'.join(reponse))
        
        manga_nom_formate = manga_normalized
        
        if manga_nom_formate in MANGA_CHANNELS and manga_nom_formate in MANGA_ROLES:
            thread_id = MANGA_CHANNELS[manga_nom_formate]
            role_id = MANGA_ROLES[manga_nom_formate]
            thread_channel = bot.get_channel(thread_id)
            
            if thread_channel:
                if chapitres_complets:
                    mention_role = f"<@&{role_id}>"
                    chapitres_mention = ", ".join(chapitres_complets)
                    
                    embed = discord.Embed(
                        title="🎉 CHAPITRE(S) TERMINÉ(S) ! 🎉",
                        description=f"Le(s) chapitre(s) **{chapitres_mention}** de **{manga_nom_formate}** est/sont complet(s) !",
                        color=discord.Color.gold(),
                        timestamp=datetime.now()
                    )
                    embed.add_field(
                        name="✅ Toutes les tâches terminées",
                        value="🧹 Clean • 🌍 Trad • ✅ Check • ✏️ Edit",
                        inline=False
                    )
                    embed.set_footer(text="Excellent travail ! 💪")
                    
                    await thread_channel.send(f"{mention_role}", embed=embed)
                else:
                    message_aleatoire = random.choice(MESSAGES_ALEATOIRES)
                    await thread_channel.send(message_aleatoire)
    
    @bot.command()
    @commands.has_any_role(1326417422663680090, 1330147432847114321)
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
            await ctx.send(f"❌ Aucun état trouvé pour **{manga}** ch.**{chapitre}**.")
            return
        
        etat_taches = etat_taches_global[chapitre_key]
        
        embed = discord.Embed(
            title=f"📋 {manga} - Chapitre {chapitre}",
            color=discord.Color.gold() if est_chapitre_complet(etat_taches) else discord.Color.blue()
        )
        
        for tache, etat in etat_taches.items():
            embed.add_field(name=tache.capitalize(), value=etat, inline=True)
        
        if est_chapitre_complet(etat_taches):
            embed.add_field(name="🎉 Statut", value="✅ Chapitre complet !", inline=False)
        
        await ctx.send(embed=embed)
    
    @bot.command()
    @commands.has_any_role(1326417422663680090, 1330147432847114321)
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
            await ctx.send(f"✅ Tâches supprimées pour **{manga}** ch.**{chapitre}**.")
        else:
            await ctx.send(f"❌ Aucune tâche trouvée pour **{manga}** ch.**{chapitre}**.")
    
    @bot.command(name="fix_tasks")
    @commands.has_any_role(1326417422663680090, 1330147432847114321)
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
            title="🔧 Normalisation des Tâches",
            color=discord.Color.green(),
            timestamp=datetime.now()
        )
        embed.add_field(name="Avant", value=str(old_count), inline=True)
        embed.add_field(name="Après", value=str(len(etat_taches_global)), inline=True)
        embed.add_field(name="Corrigées", value=str(fixed_count), inline=True)
        
        await ctx.send(embed=embed)
    
    @bot.command(name="avancee")
    async def avancee(ctx):
        """Affiche l'avancée des mangas avec pagination"""
        embed = discord.Embed(
            title="📊 Avancée des Projets",
            description=(
                "Choisissez un manga !\n\n"
                "👹 Ao No Exorcist\n"
                "🩸 Satsudou\n"
                "🗼 Tokyo Underworld\n"
                "😈 Tougen Anki\n"
                "⚽ Catenaccio"
            ),
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        embed.set_footer(text="Cliquez sur une réaction")
        
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
                await ctx.send(f"❌ Aucune tâche pour **{manga_name}**.")
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
                
                page_embed = discord.Embed(
                    title=f"{manga_emoji} {manga_name}",
                    description=(
                        f"📊 **Progression:** {progress:.1f}% ({completed}/{total_tasks})\n"
                        f"📚 Chapitres {sorted_chapters[0]} → {sorted_chapters[-1]}\n"
                        f"━━━━━━━━━━━━━━━━━━━━"
                    ),
                    color=discord.Color.green(),
                    timestamp=datetime.now()
                )
                
                for chapter in page_chapters:
                    tasks = manga_chapters[chapter]
                    prog = sum(1 for t in tasks.values() if t == "✅ Terminé")
                    bar = generate_progress_bar(prog, 4)
                    
                    title = f"📑 Ch.{chapter}"
                    if est_chapitre_complet(tasks):
                        title += " ✅"
                    
                    value = (
                        f"{bar} ({prog}/4)\n"
                        f"🧹 {tasks.get('clean', '❓')}\n"
                        f"🌍 {tasks.get('trad', '❓')}\n"
                        f"✅ {tasks.get('check', '❓')}\n"
                        f"✏️ {tasks.get('edit', '❓')}"
                    )
                    
                    page_embed.add_field(name=title, value=value, inline=False)
                
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
    @commands.has_any_role(1326417422663680090, 1330147432847114321)
    async def task_all(ctx):
        """Affiche toutes les tâches en cours"""
        if not etat_taches_global:
            await ctx.send("📋 Aucune tâche en cours.")
            return
        
        tasks_by_manga = {}
        for chapitre_key, tasks in etat_taches_global.items():
            key_manga, key_chapter = extraire_manga_chapitre(chapitre_key)
            
            if key_manga and key_chapter:
                manga_display = key_manga.title()
                if manga_display not in tasks_by_manga:
                    tasks_by_manga[manga_display] = {}
                tasks_by_manga[manga_display][str(key_chapter)] = tasks
        
        embeds = []
        for manga, chapitres in tasks_by_manga.items():
            embed = discord.Embed(
                title=f"📋 {manga}",
                color=discord.Color.blue(),
                timestamp=datetime.now()
            )
            
            for chapitre, tasks in sorted(chapitres.items(), key=lambda x: int(x[0])):
                prog = sum(1 for t in tasks.values() if t == "✅ Terminé")
                bar = generate_progress_bar(prog, 4)
                
                title = f"Ch.{chapitre}"
                if est_chapitre_complet(tasks):
                    title += " ✅"
                
                value = (
                    f"{bar} ({prog}/4)\n"
                    f"Clean: {tasks.get('clean', '❓')}\n"
                    f"Trad: {tasks.get('trad', '❓')}\n"
                    f"Check: {tasks.get('check', '❓')}\n"
                    f"Edit: {tasks.get('edit', '❓')}"
                )
                
                embed.add_field(name=title, value=value, inline=False)
            
            embed.set_footer(text=f"Page {len(embeds)+1}/{len(tasks_by_manga)} │ {ctx.author.name}")
            embeds.append(embed)
        
        if not embeds:
            await ctx.send("❌ Aucune tâche trouvée.")
            return
        
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
    @commands.has_any_role(1326417422663680090, 1330147432847114321)
    async def actualiser(ctx):
        """Sauvegarder et envoyer les données"""
        TARGET_USER_ID = 608234789564186644
        
        embed_select = discord.Embed(
            title="🔄 Actualisation",
            description=(
                "📝 **Tasks** - Tâches des chapitres\n"
                "⏰ **Rappels** - Rappels\n"
                "📨 **Invitations** - Giveaway\n"
                "❌ **Annuler**"
            ),
            color=discord.Color.blue()
        )
        
        message = await ctx.send(embed=embed_select)
        
        for e in ["📝", "⏰", "📨", "❌"]:
            await message.add_reaction(e)
        
        def check(reaction, user):
            return user == ctx.author and str(reaction.emoji) in ["📝", "⏰", "📨", "❌"] and reaction.message.id == message.id
        
        try:
            reaction, user = await bot.wait_for('reaction_add', timeout=30.0, check=check)
            await message.clear_reactions()
            
            if str(reaction.emoji) == "❌":
                await ctx.send("❌ Annulé.", delete_after=5)
                return
            
            if str(reaction.emoji) == "📝":
                file_type, main_file, meta_file = "tasks", TASKS_FILE, META_FILE
                data = etat_taches_global
                sauvegarder_etat_taches()
            elif str(reaction.emoji) == "⏰":
                import rappels
                file_type = "rappels"
                main_file, meta_file = rappels.RAPPELS_FILE, rappels.RAPPELS_META_FILE
                data = rappels.rappeals_actifs
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
                await ctx.send("❌ Utilisateur introuvable.")
                return
            
            files = []
            if os.path.exists(main_file):
                files.append(discord.File(main_file))
            if os.path.exists(meta_file):
                files.append(discord.File(meta_file))
            
            embed_dm = discord.Embed(
                title=f"📁 {file_type.capitalize()}",
                description=f"**{len(data)}** éléments",
                color=discord.Color.green(),
                timestamp=datetime.now()
            )
            embed_dm.set_footer(text=f"Par {ctx.author.name} • {ctx.guild.name}")
            
            await target_user.send(embed=embed_dm, files=files)
            await ctx.send(f"✅ **{file_type.capitalize()}** envoyés à {target_user.mention}")
        
        except asyncio.TimeoutError:
            await message.clear_reactions()
            await ctx.send("⏰ Temps écoulé.")


def generate_progress_bar(progress, total, size=10):
    """Génère une barre de progression"""
    pct = progress / total if total > 0 else 0
    filled = int(size * pct)
    return '🟩' * filled + '⬜' * (size - filled)