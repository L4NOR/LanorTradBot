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

# Fonction pour vérifier si un chapitre est complet
def est_chapitre_complet(tasks):
    """Vérifie si toutes les tâches (clean, trad, check, edit) sont terminées"""
    taches_requises = ["clean", "trad", "check", "edit"]
    return all(tasks.get(tache) == "✅ Terminé" for tache in taches_requises)


# Fonction helper pour normaliser le nom du manga (pour la recherche)
def normaliser_manga_name(name):
    """Normalise le nom du manga pour la comparaison"""
    return name.lower().strip()


# Fonction helper pour extraire manga et chapitre d'une clé
def extraire_manga_chapitre(key):
    """Extrait le nom du manga et le numéro de chapitre d'une clé"""
    if "_" not in key:
        return None, None
    
    # Utiliser rsplit pour gérer les noms avec underscores
    parts = key.rsplit("_", 1)
    if len(parts) != 2:
        return None, None
    
    manga_name = parts[0].strip()
    chapter_str = parts[1].strip()
    
    if chapter_str.isdigit():
        return manga_name, int(chapter_str)
    return manga_name, None


def setup(bot):
    charger_etat_taches()
    global bot_instance
    bot_instance = bot
    bot.remove_command('help')
    
@bot.command()
    async def help(ctx):
        """Affiche le menu d'aide interactif avec pagination"""
        admin_roles = [1326417422663680090, 1331346420883525682]
        user_roles = [role.id for role in ctx.author.roles]
        is_admin = any(role in user_roles for role in admin_roles)
        
        # Page 1: Menu Principal
        embed_main = discord.Embed(
            title="📚 Centre d'Aide LanorTrad",
            description=(
                "Bienvenue dans le système d'aide interactif !\n"
                "Naviguez entre les pages avec les réactions ci-dessous.\n\n"
                "**Catégories disponibles:**"
            ),
            color=discord.Color.from_rgb(88, 101, 242),
            timestamp=datetime.now()
        )
        
        embed_main.add_field(
            name="1️⃣ Commandes Générales",
            value="Informations, progression, profil",
            inline=True
        )
        embed_main.add_field(
            name="2️⃣ Communauté",
            value="Reviews, théories, interactions",
            inline=True
        )
        embed_main.add_field(
            name="3️⃣ Shop & Économie",
            value="Achats, inventaire, points",
            inline=True
        )
        embed_main.add_field(
            name="4️⃣ Giveaways",
            value="Concours et invitations",
            inline=True
        )
        embed_main.add_field(
            name="5️⃣ Badges",
            value="Achievements et collections",
            inline=True
        )
        
        if is_admin:
            embed_main.add_field(
                name="🔧 Admin",
                value="Commandes administrateur",
                inline=True
            )
        
        embed_main.set_thumbnail(url=ctx.guild.icon.url if ctx.guild.icon else None)
        embed_main.set_footer(text="Page 1 | Utilisez les réactions pour naviguer")
        
        # Page 2: Commandes Générales
        embed_general = discord.Embed(
            title="1️⃣ Commandes Générales",
            description="Commandes accessibles à tous les membres",
            color=discord.Color.from_rgb(87, 242, 135),
            timestamp=datetime.now()
        )
        
        embed_general.add_field(
            name="ℹ️ Informations",
            value=(
                "`!help` - Affiche ce menu d'aide\n"
                "`!info` - Informations du serveur\n"
                "`!userinfo [@user]` - Profil d'un membre\n"
                "`!ping` - Latence du bot"
            ),
            inline=False
        )
        
        embed_general.add_field(
            name="📊 Progression",
            value=(
                "`!avancee` - Voir l'avancée des projets\n"
                "`!task_status <manga> <ch>` - État d'un chapitre"
            ),
            inline=False
        )
        
        embed_general.set_footer(text="Page 2 | 1️⃣ Général")
        
        # Page 3: Communauté
        embed_community = discord.Embed(
            title="2️⃣ Commandes Communauté",
            description="Interagissez avec la communauté !",
            color=discord.Color.from_rgb(254, 231, 92),
            timestamp=datetime.now()
        )
        
        embed_community.add_field(
            name="⭐ Reviews",
            value=(
                "`!review <manga> <ch> <note 1-5> [comm]` - Laisser une review\n"
                "`!chapter_reviews <manga> <ch>` - Voir les reviews\n"
                "`!my_reviews` - Vos reviews"
            ),
            inline=False
        )
        
        embed_community.add_field(
            name="💭 Théories",
            value=(
                "`!theory <manga> <théorie>` - Poster une théorie\n"
                "`!theories [manga]` - Liste des théories\n"
                "`!theory_info <id>` - Détails d'une théorie"
            ),
            inline=False
        )
        
        embed_community.set_footer(text="Page 3 | 2️⃣ Communauté")
        
        # Page 4: Shop
        embed_shop = discord.Embed(
            title="3️⃣ Shop & Économie",
            description="Dépensez vos points durement gagnés !",
            color=discord.Color.from_rgb(235, 69, 158),
            timestamp=datetime.now()
        )
        
        embed_shop.add_field(
            name="🛒 Shopping",
            value=(
                "`!shop [catégorie]` - Voir le shop\n"
                "`!buy <item>` - Acheter un item\n"
                "`!inventory [@user]` - Voir l'inventaire\n"
                "`!use <item>` - Utiliser un item"
            ),
            inline=False
        )
        
        embed_shop.set_footer(text="Page 4 | 3️⃣ Shop")
        
        # Page 5: Giveaways
        embed_giveaway = discord.Embed(
            title="4️⃣ Giveaways & Invitations",
            description="Participez aux concours !",
            color=discord.Color.from_rgb(255, 115, 66),
            timestamp=datetime.now()
        )
        
        embed_giveaway.add_field(
            name="🎁 Giveaways",
            value=(
                "`!list_giveaways` - Liste des giveaways actifs\n"
                "`!giveaway_info <id>` - Infos d'un giveaway\n"
                "Réagissez avec 🎉 pour participer !"
            ),
            inline=False
        )
        
        embed_giveaway.add_field(
            name="📨 Invitations",
            value=(
                "`!my_invites` - Vos statistiques d'invites\n"
                "`!leaderboard_invites` - Top invitations"
            ),
            inline=False
        )
        
        embed_giveaway.set_footer(text="Page 5 | 4️⃣ Giveaways")
        
        # Page 6: Badges
        embed_badges = discord.Embed(
            title="5️⃣ Badges & Achievements",
            description="Collectionnez tous les badges !",
            color=discord.Color.from_rgb(153, 170, 181),
            timestamp=datetime.now()
        )
        
        embed_badges.add_field(
            name="🏆 Badges",
            value=(
                "`!badges [@user]` - Voir les badges\n"
                "`!all_badges` - Tous les badges disponibles\n"
                "`!badge_info <nom>` - Détails d'un badge\n"
                "`!display_badge <nom>` - Afficher un badge (max 3)\n"
                "`!remove_badge <nom>` - Retirer de l'affichage\n"
                "`!leaderboard_badges` - Top badges"
            ),
            inline=False
        )
        
        embed_badges.set_footer(text="Page 6 | 5️⃣ Badges")
        
        pages = [embed_main, embed_general, embed_community, embed_shop, embed_giveaway, embed_badges]
        
        # Pages Admin
        if is_admin:
            embed_admin1 = discord.Embed(
                title="🔧 Commandes Admin - Modération",
                description="Gestion du serveur et des membres",
                color=discord.Color.from_rgb(237, 66, 69),
                timestamp=datetime.now()
            )
            
            embed_admin1.add_field(
                name="⚖️ Modération",
                value=(
                    "`!clear <nb>` - Supprimer des messages\n"
                    "`!kick @user [raison]` - Expulser\n"
                    "`!ban @user [raison]` - Bannir\n"
                    "`!unban user#tag` - Débannir\n"
                    "`!warn @user [raison]` - Avertir"
                ),
                inline=False
            )
            
            embed_admin1.add_field(
                name="📝 Annonces",
                value=(
                    "`!announce_chapter` - Annoncer un chapitre (interactif)\n"
                    "`!test_announce` - Test d'annonce"
                ),
                inline=False
            )
            
            embed_admin1.set_footer(text="Page Admin 1 | 🔧 Modération")
            
            embed_admin2 = discord.Embed(
                title="🔧 Commandes Admin - Tâches",
                description="Gestion des projets et chapitres",
                color=discord.Color.from_rgb(237, 66, 69),
                timestamp=datetime.now()
            )
            
            embed_admin2.add_field(
                name="📋 Gestion des Tâches",
                value=(
                    "`!task <action> <manga> <ch...>` - Mettre à jour\n"
                    "`!task_status <manga> <ch>` - Voir l'état\n"
                    "`!task_all` - Toutes les tâches\n"
                    "`!delete_task <manga> <ch>` - Supprimer\n"
                    "`!fix_tasks` - Normaliser les clés"
                ),
                inline=False
            )
            
            embed_admin2.add_field(
                name="⏰ Rappels",
                value=(
                    "`!add_rappel` - Créer un rappel (interactif)\n"
                    "`!list_rappels` - Liste des rappels\n"
                    "`!delete_rappel <id>` - Supprimer un rappel\n"
                    "`!test_rappel` - Tester l'envoi"
                ),
                inline=False
            )
            
            embed_admin2.set_footer(text="Page Admin 2 | 🔧 Tâches & Rappels")
            
            embed_admin3 = discord.Embed(
                title="🔧 Commandes Admin - Giveaways",
                description="Gestion des concours",
                color=discord.Color.from_rgb(237, 66, 69),
                timestamp=datetime.now()
            )
            
            embed_admin3.add_field(
                name="🎁 Gestion Giveaways",
                value=(
                    "`!create_giveaway` - Créer (interactif)\n"
                    "`!giveaway <durée> <gagnants> <prix>` - Créer rapide\n"
                    "`!end_giveaway <id>` - Terminer\n"
                    "`!delete_giveaway <id>` - Supprimer\n"
                    "`!reroll <id> [count]` - Retirer des gagnants\n"
                    "`!giveaway_participants <id>` - Liste participants"
                ),
                inline=False
            )
            
            embed_admin3.add_field(
                name="📨 Invitations",
                value=(
                    "`!add_invites @user <nb>` - Ajouter\n"
                    "`!remove_invites @user <nb>` - Retirer\n"
                    "`!reset_user_invites @user` - Reset\n"
                    "`!server_invite_stats` - Stats globales"
                ),
                inline=False
            )
            
            embed_admin3.set_footer(text="Page Admin 3 | 🔧 Giveaways")
            
            embed_admin4 = discord.Embed(
                title="🔧 Commandes Admin - Communauté",
                description="Gestion badges, shop et chapitres",
                color=discord.Color.from_rgb(237, 66, 69),
                timestamp=datetime.now()
            )
            
            embed_admin4.add_field(
                name="📚 Chapitres",
                value=(
                    "`!newchapter <msg_id> <manga> <ch>` - Lier un chapitre"
                ),
                inline=False
            )
            
            embed_admin4.add_field(
                name="🏆 Badges",
                value=(
                    "`!give_badge @user <badge>` - Donner un badge"
                ),
                inline=False
            )
            
            embed_admin4.add_field(
                name="🛒 Shop",
                value=(
                    "`!shop_add` - Ajouter un item (interactif)\n"
                    "`!shop_remove <item>` - Retirer un item\n"
                    "`!give_item @user <item>` - Donner un item\n"
                    "`!set_points @user <nb>` - Définir les points\n"
                    "`!add_points_admin @user <nb>` - Ajouter des points"
                ),
                inline=False
            )
            
            embed_admin4.add_field(
                name="💭 Théories",
                value=(
                    "`!theory_status <id> <status>` - Changer statut\n"
                    "Status: confirmed, debunked, active"
                ),
                inline=False
            )
            
            embed_admin4.set_footer(text="Page Admin 4 | 🔧 Communauté & Shop")
            
            embed_admin5 = discord.Embed(
                title="🔧 Commandes Admin - Données",
                description="Gestion et sauvegarde des données",
                color=discord.Color.from_rgb(237, 66, 69),
                timestamp=datetime.now()
            )
            
            embed_admin5.add_field(
                name="💾 Gestionnaire de Données",
                value=(
                    "`!data` - Menu interactif\n"
                    "`!data save <cible>` - Sauvegarder\n"
                    "`!data reload <cible>` - Recharger\n"
                    "`!data export <cible>` - Exporter en MP\n"
                    "`!data status` - Statut des modules\n"
                    "`!data_list` - Liste des modules"
                ),
                inline=False
            )
            
            embed_admin5.add_field(
                name="📦 Cibles Disponibles",
                value=(
                    "`all` - Tout\n"
                    "`community` - Communauté\n"
                    "`achievements` - Badges\n"
                    "`shop` - Shop\n"
                    "`giveaway` - Giveaways\n"
                    "`workflow` - Tâches & rappels"
                ),
                inline=False
            )
            
            embed_admin5.add_field(
                name="⚡ Raccourcis",
                value=(
                    "`!backup` - Sauvegarde + Export complet\n"
                    "`!actualiser [save|reload]` - Tâches/Rappels (legacy)"
                ),
                inline=False
            )
            
            embed_admin5.set_footer(text="Page Admin 5 | 🔧 Données")
            
            pages.extend([embed_admin1, embed_admin2, embed_admin3, embed_admin4, embed_admin5])
        
        # Envoyer et gérer la pagination
        current_page = 0
        message = await ctx.send(embed=pages[current_page])
        
        # Ajouter les réactions
        reactions = ['⬅️', '➡️', '🏠', '❌']
        for reaction in reactions:
            await message.add_reaction(reaction)
        
        def check(reaction, user):
            return user == ctx.author and str(reaction.emoji) in reactions and reaction.message.id == message.id
        
        while True:
            try:
                reaction, user = await bot.wait_for('reaction_add', timeout=120.0, check=check)
                
                if str(reaction.emoji) == '⬅️':
                    if current_page > 0:
                        current_page -= 1
                        await message.edit(embed=pages[current_page])
                elif str(reaction.emoji) == '➡️':
                    if current_page < len(pages) - 1:
                        current_page += 1
                        await message.edit(embed=pages[current_page])
                elif str(reaction.emoji) == '🏠':
                    current_page = 0
                    await message.edit(embed=pages[current_page])
                elif str(reaction.emoji) == '❌':
                    await message.clear_reactions()
                    break
                
                await message.remove_reaction(reaction, user)
            
            except asyncio.TimeoutError:
                await message.clear_reactions()
                break
    
    @bot.command()
    @commands.has_permissions(manage_messages=True)
    async def clear(ctx, amount: int):
        """Supprime un nombre spécifié de messages"""
        if amount <= 0:
            await ctx.send("Le nombre de messages à supprimer doit être supérieur à 0.")
            return
        
        deleted = await ctx.channel.purge(limit=amount + 1)
        clear_message = f"🗑️ {ctx.author.mention} a supprimé des messages dans ce salon."
        await ctx.send(clear_message, delete_after=5)
        
        embed = discord.Embed(
            title="🗑️ Messages supprimés",
            description=f'{len(deleted)-1} messages ont été supprimés.',
            color=discord.Color.red()
        )
        await ctx.send(embed=embed, delete_after=5)
    
    @bot.command()
    @commands.has_permissions(kick_members=True)
    async def kick(ctx, member: discord.Member, *, reason=None):
        """Expulse un membre du serveur"""
        kick_message = f"👢 {ctx.author.mention} a expulsé {member.mention} du serveur."
        await ctx.send(kick_message)
        await member.kick(reason=reason)
        
        embed = discord.Embed(
            title="👢 Membre expulsé",
            description=f"{member.mention} a été expulsé par {ctx.author.mention}.\nRaison: {reason or 'Aucune raison spécifiée'}",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
    
    @bot.command()
    @commands.has_permissions(ban_members=True)
    async def ban(ctx, member: discord.Member, *, reason=None):
        """Bannit un membre du serveur"""
        ban_message = f"🔨 {ctx.author.mention} a banni {member.mention} du serveur."
        await ctx.send(ban_message)
        await member.ban(reason=reason)
        
        embed = discord.Embed(
            title="🔨 Membre banni",
            description=f"{member.mention} a été banni par {ctx.author.mention}.\nRaison: {reason or 'Aucune raison spécifiée'}",
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
                unban_message = f"🔓 {ctx.author.mention} a débanni {user.mention}."
                await ctx.send(unban_message)
                
                embed = discord.Embed(
                    title="🔓 Membre débanni",
                    description=f"{user.mention} a été débanni par {ctx.author.mention}.",
                    color=discord.Color.green()
                )
                await ctx.send(embed=embed)
                return
    
    @bot.command()
    @commands.has_permissions(kick_members=True)
    async def warn(ctx, member: discord.Member, *, reason=None):
        """Avertit un membre"""
        warn_message = f"⚠️ {ctx.author.mention} a averti {member.mention}."
        await ctx.send(warn_message)
        
        embed = discord.Embed(
            title="⚠️ Avertissement",
            description=f"{member.mention} a reçu un avertissement de {ctx.author.mention}.\nRaison: {reason or 'Aucune raison spécifiée'}",
            color=discord.Color.orange()
        )
        await ctx.send(embed=embed)
    
    @bot.command()
    async def info(ctx):
        """Affiche les informations du serveur"""
        info_message = f"ℹ️ {ctx.author.mention} a demandé les informations du serveur."
        await ctx.send(info_message)
        
        embed = discord.Embed(
            title=f"ℹ️ Informations sur {ctx.guild.name}",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        embed.add_field(name="📊 Membres", value=ctx.guild.member_count)
        embed.add_field(name="📅 Créé le", value=ctx.guild.created_at.strftime("%d/%m/%Y"))
        embed.add_field(name="👑 Propriétaire", value=ctx.guild.owner.mention)
        
        if ctx.guild.icon:
            embed.set_thumbnail(url=ctx.guild.icon.url)
        
        await ctx.send(embed=embed)
    
    @bot.command()
    async def userinfo(ctx, member: discord.Member = None):
        """Affiche les informations d'un utilisateur"""
        member = member or ctx.author
        userinfo_message = f"ℹ️ {ctx.author.mention} a demandé les informations de {member.mention}."
        await ctx.send(userinfo_message)
        
        roles = [role.mention for role in member.roles if role.name != "@everyone"]
        
        embed = discord.Embed(
            title=f"ℹ️ Informations sur {member.name}",
            color=member.color,
            timestamp=datetime.now()
        )
        embed.add_field(name="📅 A rejoint le", value=member.joined_at.strftime("%d/%m/%Y"))
        embed.add_field(name="🔰 Compte créé le", value=member.created_at.strftime("%d/%m/%Y"))
        embed.add_field(name="🏷️ Rôles", value=" ".join(roles) if roles else "Aucun rôle", inline=False)
        
        if member.avatar:
            embed.set_thumbnail(url=member.avatar.url)
        
        await ctx.send(embed=embed)
    
    @bot.command()
    async def ping(ctx):
        """Vérifie la latence du bot"""
        ping_message = f"🏓 {ctx.author.mention} a vérifié la latence du bot."
        await ctx.send(ping_message)
        
        embed = discord.Embed(
            title="🏓 Pong!",
            description=f"Latence: {round(bot.latency * 1000)}ms",
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
        
        # CORRECTION: Normaliser le nom du manga (enlever les espaces en trop)
        manga_normalized = manga.strip()
        
        for chapitre_str in chapitres:
            chapitre_str = chapitre_str.strip().rstrip(',')
            
            try:
                chapitre = int(chapitre_str)
                # CORRECTION: Utiliser le nom normalisé pour la clé
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
                
                # Vérifier si le chapitre est maintenant complet
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
                # Si des chapitres sont complets, envoyer une notification avec mention
                if chapitres_complets:
                    mention_role = f"<@&{role_id}>"
                    chapitres_mention = ", ".join(chapitres_complets)
                    
                    embed = discord.Embed(
                        title="🎉 CHAPITRE(S) TERMINÉ(S) ! 🎉",
                        description=f"Le(s) chapitre(s) **{chapitres_mention}** de **{manga_nom_formate}** est/sont maintenant complet(s) !",
                        color=discord.Color.gold(),
                        timestamp=datetime.now()
                    )
                    embed.add_field(
                        name="✅ Toutes les tâches terminées",
                        value="🧹 Clean\n🌍 Traduction\n✅ Check\n✏️ Edit",
                        inline=False
                    )
                    embed.add_field(
                        name="📊 Voir l'avancée complète",
                        value="Utilisez la commande `!avancee` pour voir tous les projets !",
                        inline=False
                    )
                    embed.set_footer(text="Excellent travail à toute l'équipe ! 💪")
                    
                    await thread_channel.send(f"{mention_role}", embed=embed)
                
                # Sinon, envoyer un message aléatoire sans mention
                else:
                    message_aleatoire = random.choice(MESSAGES_ALEATOIRES)
                    await thread_channel.send(message_aleatoire)
    
    @bot.command()
    @commands.has_any_role(1326417422663680090, 1330147432847114321)
    async def task_status(ctx, manga: str, chapitre: int):
        """Affiche l'état des tâches pour un chapitre donné"""
        # CORRECTION: Normaliser et chercher avec flexibilité
        manga_normalized = normaliser_manga_name(manga)
        chapitre_key = None
        
        # Chercher la clé correspondante
        for key in etat_taches_global:
            key_manga, key_chap = extraire_manga_chapitre(key)
            if key_manga and normaliser_manga_name(key_manga) == manga_normalized and key_chap == chapitre:
                chapitre_key = key
                break
        
        if chapitre_key is None:
            await ctx.send(f"❌ Aucun état trouvé pour le chapitre **{chapitre}** de **{manga}**.")
            return
        
        etat_taches = etat_taches_global[chapitre_key]
        
        embed = discord.Embed(
            title=f"📋 État des Tâches : {manga} - Chapitre {chapitre}",
            color=discord.Color.blue()
        )
        
        for tache, etat in etat_taches.items():
            embed.add_field(name=tache.capitalize(), value=etat, inline=False)
        
        # Ajouter un indicateur si le chapitre est complet
        if est_chapitre_complet(etat_taches):
            embed.add_field(name="🎉 Statut", value="✅ Chapitre complet !", inline=False)
            embed.color = discord.Color.gold()
        
        await ctx.send(embed=embed)
    
    @bot.command()
    @commands.has_any_role(1326417422663680090, 1330147432847114321)
    async def delete_task(ctx, manga: str, chapitre: int):
        """Supprime toutes les tâches associées à un chapitre donné"""
        # CORRECTION: Normaliser et chercher avec flexibilité
        manga_normalized = normaliser_manga_name(manga)
        chapitre_key = None
        
        # Chercher la clé correspondante
        for key in etat_taches_global:
            key_manga, key_chap = extraire_manga_chapitre(key)
            if key_manga and normaliser_manga_name(key_manga) == manga_normalized and key_chap == chapitre:
                chapitre_key = key
                break
        
        if chapitre_key and chapitre_key in etat_taches_global:
            del etat_taches_global[chapitre_key]
            sauvegarder_etat_taches()
            await ctx.send(f"✅ Toutes les tâches pour le chapitre **{chapitre}** de **{manga}** ont été supprimées.")
        else:
            await ctx.send(f"❌ Aucune tâche trouvée pour le chapitre **{chapitre}** de **{manga}**.")
    
    @bot.command(name="fix_tasks")
    @commands.has_any_role(1326417422663680090, 1330147432847114321)
    async def fix_tasks(ctx):
        """Normalise les clés des tâches (corrige les espaces)"""
        global etat_taches_global
        
        old_count = len(etat_taches_global)
        new_tasks = {}
        fixed_count = 0
        
        for key, value in etat_taches_global.items():
            # Extraire manga et chapitre
            key_manga, key_chap = extraire_manga_chapitre(key)
            
            if key_manga and key_chap:
                # Créer la nouvelle clé normalisée
                new_key = f"{key_manga}_{key_chap}"
                
                if new_key != key:
                    fixed_count += 1
                
                # Si la clé existe déjà, fusionner (garder les tâches terminées)
                if new_key in new_tasks:
                    for task_name, task_status in value.items():
                        if task_status == "✅ Terminé":
                            new_tasks[new_key][task_name] = task_status
                else:
                    new_tasks[new_key] = value
            else:
                # Garder les clés non reconnues telles quelles
                new_tasks[key] = value
        
        etat_taches_global = new_tasks
        sauvegarder_etat_taches()
        
        embed = discord.Embed(
            title="🔧 Normalisation des Tâches",
            description=f"Les clés des tâches ont été normalisées !",
            color=discord.Color.green(),
            timestamp=datetime.now()
        )
        embed.add_field(name="📊 Tâches avant", value=str(old_count), inline=True)
        embed.add_field(name="📊 Tâches après", value=str(len(etat_taches_global)), inline=True)
        embed.add_field(name="🔧 Clés corrigées", value=str(fixed_count), inline=True)
        
        await ctx.send(embed=embed)
    
    @bot.command(name="avancee")
    async def avancee(ctx):
        """Affiche l'avancée des mangas de manière interactive avec pagination"""
        embed = discord.Embed(
            title="📊 Avancée des Projets Manga",
            description=(
                "Choisissez un manga pour voir son avancée !\n\n"
                "👹 **Ao No Exorcist**\n"
                "🩸 **Satsudou**\n"
                "🗼 **Tokyo Underworld**\n"
                "😈 **Tougen Anki**\n"
                "⚽ **Catenaccio**"
            ),
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        embed.set_footer(text="Cliquez sur une réaction pour voir l'avancée du manga !")
        
        message = await ctx.send(embed=embed)
        
        reactions = ['👹', '🩸', '🗼', '😈', '⚽']
        for reaction in reactions:
            await message.add_reaction(reaction)
        
        manga_map = {
            '👹': 'Ao No Exorcist',
            '🩸': 'Satsudou',
            '🗼': 'Tokyo Underworld',
            '😈': 'Tougen Anki',
            '⚽': 'Catenaccio'
        }
        
        manga_emoji_map = {
            'Ao No Exorcist': '👹',
            'Satsudou': '🩸',
            'Tokyo Underworld': '🗼',
            'Tougen Anki': '😈',
            'Catenaccio': '⚽'
        }
        
        def check(reaction, user):
            return user == ctx.author and str(reaction.emoji) in reactions
        
        try:
            reaction, user = await bot.wait_for('reaction_add', timeout=30.0, check=check)
            manga_name = manga_map[str(reaction.emoji)]
            manga_emoji = manga_emoji_map.get(manga_name, '📚')
            
            # Récupérer tous les chapitres du manga
            manga_chapters = {}
            manga_name_normalized = normaliser_manga_name(manga_name)
            
            for key in etat_taches_global:
                key_manga, key_chapter = extraire_manga_chapitre(key)
                
                if key_manga and key_chapter:
                    if normaliser_manga_name(key_manga) == manga_name_normalized:
                        manga_chapters[key_chapter] = etat_taches_global[key]
            
            if not manga_chapters:
                await ctx.send(f"❌ Aucune tâche trouvée pour **{manga_name}**.")
                return
            
            # Trier les chapitres
            sorted_chapters = sorted(manga_chapters.keys())
            
            # Nombre de chapitres par page (5 pour éviter de dépasser la limite Discord)
            CHAPTERS_PER_PAGE = 5
            total_pages = (len(sorted_chapters) + CHAPTERS_PER_PAGE - 1) // CHAPTERS_PER_PAGE
            
            # Fonction pour créer un embed de page
            def create_page_embed(page_num):
                start_idx = page_num * CHAPTERS_PER_PAGE
                end_idx = min(start_idx + CHAPTERS_PER_PAGE, len(sorted_chapters))
                page_chapters = sorted_chapters[start_idx:end_idx]
                
                # Calculer les statistiques globales
                total_tasks = len(sorted_chapters) * 4  # 4 tâches par chapitre
                completed_tasks = sum(
                    1 for ch in sorted_chapters 
                    for task in manga_chapters[ch].values() 
                    if task == "✅ Terminé"
                )
                global_progress = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
                
                progress_embed = discord.Embed(
                    title=f"{manga_emoji} Avancée de {manga_name}",
                    description=(
                        f"📊 **Progression globale:** {global_progress:.1f}% ({completed_tasks}/{total_tasks} tâches)\n"
                        f"📚 **Chapitres:** {sorted_chapters[0]} → {sorted_chapters[-1]} ({len(sorted_chapters)} chapitres)\n"
                        f"━━━━━━━━━━━━━━━━━━━━━━━━"
                    ),
                    color=discord.Color.green(),
                    timestamp=datetime.now()
                )
                
                for chapter in page_chapters:
                    tasks = manga_chapters[chapter]
                    progress = sum(1 for task in tasks.values() if task == "✅ Terminé")
                    progress_bar = generate_progress_bar(progress, len(tasks))
                    
                    # Ajouter un emoji si le chapitre est complet
                    chapter_title = f"📑 Chapitre {chapter}"
                    if est_chapitre_complet(tasks):
                        chapter_title += " ✅"
                    
                    field_value = (
                        f"{progress_bar} ({progress}/{len(tasks)})\n"
                        f"🧹 Clean: {tasks.get('clean', '❓ Inconnu')}\n"
                        f"🌍 Trad: {tasks.get('trad', '❓ Inconnu')}\n"
                        f"✅ Check: {tasks.get('check', '❓ Inconnu')}\n"
                        f"✏️ Edit: {tasks.get('edit', '❓ Inconnu')}"
                    )
                    
                    progress_embed.add_field(
                        name=chapter_title,
                        value=field_value,
                        inline=False
                    )
                
                progress_embed.set_footer(
                    text=f"Page {page_num + 1}/{total_pages} | Chapitres {page_chapters[0]}-{page_chapters[-1]} | Demandé par {ctx.author.name}",
                    icon_url=ctx.author.avatar.url if ctx.author.avatar else None
                )
                
                return progress_embed
            
            # Afficher la première page
            current_page = 0
            await message.clear_reactions()
            await message.edit(embed=create_page_embed(current_page))
            
            # Si plusieurs pages, ajouter les réactions de navigation
            if total_pages > 1:
                nav_reactions = ['⏮️', '⬅️', '➡️', '⏭️', '🏠']
                for nav_reaction in nav_reactions:
                    await message.add_reaction(nav_reaction)
                
                def nav_check(reaction, user):
                    return user == ctx.author and str(reaction.emoji) in nav_reactions and reaction.message.id == message.id
                
                while True:
                    try:
                        reaction, user = await bot.wait_for('reaction_add', timeout=120.0, check=nav_check)
                        emoji = str(reaction.emoji)
                        
                        if emoji == '⏮️':  # Première page
                            current_page = 0
                        elif emoji == '⬅️':  # Page précédente
                            current_page = max(0, current_page - 1)
                        elif emoji == '➡️':  # Page suivante
                            current_page = min(total_pages - 1, current_page + 1)
                        elif emoji == '⏭️':  # Dernière page
                            current_page = total_pages - 1
                        elif emoji == '🏠':  # Retour au menu principal
                            await message.clear_reactions()
                            await message.edit(embed=embed)
                            for r in reactions:
                                await message.add_reaction(r)
                            # Réinitialiser pour permettre une nouvelle sélection
                            try:
                                reaction, user = await bot.wait_for('reaction_add', timeout=30.0, check=check)
                                manga_name = manga_map[str(reaction.emoji)]
                                # Relancer la logique... (simplifié ici)
                            except asyncio.TimeoutError:
                                await message.clear_reactions()
                            break
                        
                        await message.edit(embed=create_page_embed(current_page))
                        await message.remove_reaction(reaction, user)
                    
                    except asyncio.TimeoutError:
                        await message.clear_reactions()
                        break
        
        except asyncio.TimeoutError:
            await message.clear_reactions()
            timeout_embed = embed.copy()
            timeout_embed.description += "\n\n⏰ Le temps de sélection est écoulé."
            await message.edit(embed=timeout_embed)
    
    @bot.command(name="task_all")
    @commands.has_any_role(1326417422663680090, 1330147432847114321)
    async def task_all(ctx):
        """Affiche toutes les tâches actuellement en cours, organisées par manga avec pagination"""
        if not etat_taches_global:
            await ctx.send("📋 Aucune tâche en cours actuellement.")
            return
        
        # CORRECTION: Utiliser la nouvelle logique d'extraction
        tasks_by_manga = {}
        for chapitre_key, tasks in etat_taches_global.items():
            key_manga, key_chapter = extraire_manga_chapitre(chapitre_key)
            
            if key_manga and key_chapter:
                # Normaliser le nom du manga pour le regroupement
                manga_display = key_manga.title()  # Mettre en majuscule proprement
                if manga_display not in tasks_by_manga:
                    tasks_by_manga[manga_display] = {}
                tasks_by_manga[manga_display][str(key_chapter)] = tasks
        
        embeds = []
        for manga, chapitres in tasks_by_manga.items():
            embed = discord.Embed(
                title=f"📋 Tâches en cours - {manga}",
                color=discord.Color.blue(),
                timestamp=datetime.now()
            )
            
            for chapitre, tasks in sorted(chapitres.items(), key=lambda x: int(x[0])):
                progress = sum(1 for task in tasks.values() if task == "✅ Terminé")
                progress_bar = generate_progress_bar(progress, len(tasks))
                
                # Ajouter un emoji si le chapitre est complet
                chapter_title = f"📖 Chapitre {chapitre}"
                if est_chapitre_complet(tasks):
                    chapter_title += " ✅"
                
                field_value = (
                    f"{progress_bar} ({progress}/{len(tasks)})\n"
                    f"Clean: {tasks.get('clean', '❓ Inconnu')}\n"
                    f"Trad: {tasks.get('trad', '❓ Inconnu')}\n"
                    f"Check: {tasks.get('check', '❓ Inconnu')}\n"
                    f"Edit: {tasks.get('edit', '❓ Inconnu')}"
                )
                
                embed.add_field(
                    name=chapter_title,
                    value=field_value,
                    inline=False
                )
            
            embed.set_footer(
                text=f"Page {len(embeds) + 1}/{len(tasks_by_manga)} | Demandé par {ctx.author.name}",
                icon_url=ctx.author.avatar.url if ctx.author.avatar else None
            )
            embeds.append(embed)
        
        if not embeds:
            await ctx.send("❌ Aucune tâche trouvée.")
            return
        
        current_page = 0
        message = await ctx.send(embed=embeds[current_page])
        
        reactions = ['⬅️', '➡️']
        for reaction in reactions:
            await message.add_reaction(reaction)
        
        def check(reaction, user):
            return user == ctx.author and str(reaction.emoji) in reactions and reaction.message.id == message.id
        
        while True:
            try:
                reaction, user = await ctx.bot.wait_for('reaction_add', timeout=60.0, check=check)
                
                if str(reaction.emoji) == '⬅️':
                    if current_page > 0:
                        current_page -= 1
                        await message.edit(embed=embeds[current_page])
                elif str(reaction.emoji) == '➡️':
                    if current_page < len(embeds) - 1:
                        current_page += 1
                        await message.edit(embed=embeds[current_page])
                
                await message.remove_reaction(reaction, user)
            
            except asyncio.TimeoutError:
                await message.clear_reactions()
                break
    
    @bot.command(name="actualiser")
    @commands.has_any_role(1326417422663680090, 1330147432847114321)
    async def actualiser(ctx):
        """Commande d'administration pour sauvegarder et envoyer les fichiers de tâches ou rappels"""
        # ID de l'utilisateur qui recevra les fichiers
        TARGET_USER_ID = 608234789564186644
        
        # Embed de sélection
        embed_select = discord.Embed(
            title="🔄 Actualisation des Données",
            description="Que souhaitez-vous actualiser et recevoir ?",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        embed_select.add_field(
            name="📋 Options disponibles",
            value=(
                "📝 **Tasks** - Fichiers de tâches des chapitres\n"
                "⏰ **Rappels** - Fichiers de rappels\n"
                "📨 **Invitations** - Fichiers d'invitations du giveaway\n"
                "❌ **Annuler** - Annuler l'opération"
            ),
            inline=False
        )
        embed_select.set_footer(text="Réagissez avec l'emoji correspondant")
        
        message = await ctx.send(embed=embed_select)
        
        # Ajouter les réactions
        await message.add_reaction("📝")
        await message.add_reaction("⏰")
        await message.add_reaction("📨")
        await message.add_reaction("❌")
        
        def check(reaction, user):
            return user == ctx.author and str(reaction.emoji) in ["📝", "⏰", "📨", "❌"] and reaction.message.id == message.id
        
        try:
            reaction, user = await bot.wait_for('reaction_add', timeout=30.0, check=check)
            await message.clear_reactions()
            
            if str(reaction.emoji) == "❌":
                embed_cancel = discord.Embed(
                    title="❌ Opération Annulée",
                    description="L'actualisation a été annulée.",
                    color=discord.Color.red()
                )
                await ctx.send(embed=embed_cancel, delete_after=5)
                return
            
            # Déterminer quel type de fichier envoyer
            if str(reaction.emoji) == "📝":
                file_type = "tasks"
                main_file = TASKS_FILE
                meta_file = META_FILE
                data = etat_taches_global
                emoji = "📋"
            elif str(reaction.emoji) == "⏰":
                file_type = "rappels"
                # Import des données de rappels depuis rappels.py
                import rappels
                main_file = rappels.RAPPELS_FILE
                meta_file = rappels.RAPPELS_META_FILE
                data = rappels.rappeals_actifs
                emoji = "⏰"
            else:  # 📨 Invitations
                file_type = "invitations"
                # Import des données d'invitations depuis giveaway.py
                import giveaway
                main_file = giveaway.INVITES_FILE
                # Créer un fichier meta pour les invitations
                meta_file = "data/invites_tracker_meta.json"
                data = giveaway.invites_tracker
                emoji = "📨"
            
            # Sauvegarder les données actuelles
            if file_type == "tasks":
                sauvegarder_etat_taches()
            elif file_type == "rappels":
                rappels.sauvegarder_rappels()
            else:  # invitations
                giveaway.sauvegarder_invites()
                # Créer le fichier meta pour les invitations
                import json
                meta = {
                    "last_saved": datetime.utcnow().isoformat() + "Z",
                    "invite_count": len(giveaway.invites_tracker),
                    "total_invites": sum(inv['real'] for inv in giveaway.invites_tracker.values())
                }
                with open(meta_file, "w", encoding="utf-8") as mf:
                    json.dump(meta, mf, ensure_ascii=False, indent=4)
            
            # Récupérer l'utilisateur cible
            target_user = await bot.fetch_user(TARGET_USER_ID)
            if not target_user:
                await ctx.send("❌ Impossible de trouver l'utilisateur cible.")
                return
            
            # Créer l'embed de confirmation
            embed_sending = discord.Embed(
                title=f"{emoji} Envoi en cours...",
                description=f"Préparation et envoi des fichiers **{file_type}** à {target_user.mention}",
                color=discord.Color.gold()
            )
            await message.edit(embed=embed_sending)
            
            # Préparer les fichiers à envoyer
            files_to_send = []
            
            # Fichier principal
            if os.path.exists(main_file):
                files_to_send.append(discord.File(main_file))
            
            # Fichier meta
            if os.path.exists(meta_file):
                files_to_send.append(discord.File(meta_file))
            
            # Créer l'embed pour le MP
            embed_dm = discord.Embed(
                title=f"{emoji} Actualisation des {file_type.capitalize()}",
                description=f"Fichiers mis à jour le {datetime.now().strftime('%d/%m/%Y à %H:%M:%S')}",
                color=discord.Color(COLORS.get("success", 0x2ECC71)),
                timestamp=datetime.now()
            )
            embed_dm.add_field(
                name="📊 Statistiques",
                value=f"**{len(data)}** élément(s) dans le fichier",
                inline=True
            )
            embed_dm.add_field(
                name="📁 Fichiers joints",
                value=f"• {os.path.basename(main_file)}\n• {os.path.basename(meta_file)}",
                inline=False
            )
            embed_dm.set_footer(
                text=f"Demandé par {ctx.author.name} depuis {ctx.guild.name}",
                icon_url=ctx.author.avatar.url if ctx.author.avatar else None
            )
            
            # Envoyer en MP
            try:
                await target_user.send(embed=embed_dm, files=files_to_send)
                
                # Confirmation dans le salon
                embed_success = discord.Embed(
                    title=f"✅ {file_type.capitalize()} Actualisés",
                    description=f"Les fichiers ont été sauvegardés et envoyés avec succès !",
                    color=discord.Color(COLORS.get("success", 0x2ECC71)),
                    timestamp=datetime.now()
                )
                embed_success.add_field(
                    name="📊 Éléments sauvegardés",
                    value=f"**{len(data)}** élément(s)",
                    inline=True
                )
                embed_success.add_field(
                    name="📨 Envoyé à",
                    value=target_user.mention,
                    inline=True
                )
                embed_success.set_footer(text=f"Demandé par {ctx.author.name}")
                await message.edit(embed=embed_success)
            
            except discord.Forbidden:
                embed_error = discord.Embed(
                    title="❌ Erreur d'Envoi",
                    description=f"Impossible d'envoyer un MP à {target_user.mention}. Ses MPs sont peut-être désactivés.",
                    color=discord.Color.red()
                )
                await message.edit(embed=embed_error)
        
        except asyncio.TimeoutError:
            await message.clear_reactions()
            embed_timeout = discord.Embed(
                title="⏰ Temps Écoulé",
                description="L'opération a été annulée (temps d'attente dépassé).",
                color=discord.Color.orange()
            )
            await message.edit(embed=embed_timeout)

def generate_progress_bar(progress, total, size=10):
    """Génère une barre de progression visuelle"""
    percentage = progress / total
    filled = int(size * percentage)
    empty = size - filled
    return f"{'🟩' * filled}{'⬜' * empty}"