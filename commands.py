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


def setup(bot):
    charger_etat_taches()
    global bot_instance
    bot_instance = bot
    bot.remove_command('help')
    
    @bot.command()
    async def help(ctx):
        """Affiche le menu d'aide des commandes"""
        admin_roles = [1326417422663680090, 1331346420883525682]
        user_roles = [role.id for role in ctx.author.roles]
        
        embed = discord.Embed(
            title="📚 **Menu d'Aide - LanorTrad Bot**",
            description=(
                "Bienvenue dans le menu d'aide ! Voici les commandes disponibles pour interagir avec le bot.\n\n"
                "🔹 **Commandes Générales** : Accessibles à tous.\n"
                "🎁 **Commandes Giveaway** : Pour les invitations et concours.\n"
                "🔧 **Commandes Admin** : Réservées aux administrateurs."
            ),
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        
        embed.add_field(
            name="🎮 **Commandes Générales**",
            value=(
                "• !help - Afficher ce menu d'aide\n"
                "• !info - Informations du serveur\n"
                "• !userinfo - Détails du profil utilisateur\n"
                "• !ping - Vérifier la latence\n"
                "• !avancee - Voir l'avancée des chapitres\n"
            ),
            inline=False
        )
        
        embed.add_field(
            name="🎁 **Commandes Giveaway**",
            value=(
                "• !my_invites - Voir vos statistiques d'invitations\n"
                "• !enter_giveaway <id> - Participer à un giveaway\n"
                "• !leaderboard_invites - Classement des invitations\n"
                "• !list_giveaways - Liste tous les giveaways\n"
                "• !giveaway_info <id> - Informations d'un giveaway\n"
            ),
            inline=False
        )
        
        if any(role in user_roles for role in admin_roles):
            embed.add_field(
                name="🔧 **Commandes Admin - Général**",
                value=(
                    "• !clear <nombre> - Supprimer des messages\n"
                    "• !kick @utilisateur [raison] - Expulser un membre\n"
                    "• !ban @utilisateur [raison] - Bannir un membre\n"
                    "• !unban nom_utilisateur#tag - Débannir un membre\n"
                    "• !warn @utilisateur [raison] - Avertir un membre\n"
                ),
                inline=False
            )
            
            embed.add_field(
                name="🔧 **Commandes Admin - Tâches**",
                value=(
                    "• !task <action> <manga> <chapitre> - Mettre à jour l'état d'une tâche\n"
                    "• !task_status <manga> <chapitre> - Afficher l'état des tâches\n"
                    "• !task_all - Afficher toutes les tâches en cours\n"
                    "• !delete_task <manga> <chapitre> - Supprimer les tâches d'un chapitre\n"
                    "• !actualiser <save|reload> - Enregistrer ou recharger le fichier etat_taches.json\n"
                ),
                inline=False
            )
            
            embed.add_field(
                name="🔧 **Commandes Admin - Giveaway**",
                value=(
                    "• !create_giveaway - Créer un nouveau giveaway (interactif)\n"
                    "• !end_giveaway <id> - Terminer un giveaway manuellement\n"
                    "• !delete_giveaway <id> - Supprimer un giveaway\n"
                    "• !giveaway_participants <id> - Liste des participants\n"
                    "• !add_invites @user <nombre> - Ajouter des invitations\n"
                    "• !remove_invites @user <nombre> - Retirer des invitations\n"
                    "• !reset_user_invites @user - Réinitialiser les invitations\n"
                    "• !server_invite_stats - Statistiques globales d'invitations\n"
                ),
                inline=False
            )
        
        embed.add_field(name="━━━━━━━━━━━━━━━━━━━━━━━", value="", inline=False)
        
        embed.set_footer(
            text=f"Demandé par {ctx.author.name} | LanorTrad Bot",
            icon_url=ctx.author.avatar.url if ctx.author.avatar else None
        )
        
        if ctx.guild.icon:
            embed.set_thumbnail(url=ctx.guild.icon.url)
        
        await ctx.send(embed=embed)
    
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
        
        for chapitre_str in chapitres:
            chapitre_str = chapitre_str.strip().rstrip(',')
            
            try:
                chapitre = int(chapitre_str)
                chapitre_key = f"{manga.lower()}_{chapitre}"
                
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
            reponse.append(f"✅ Tâche **{action}** mise à jour pour **{manga}** chapitres : **{', '.join(chapitres_traites)}**")
        if chapitres_erreur:
            reponse.append(f"❌ Chapitres invalides ignorés : {', '.join(chapitres_erreur)}")
        if not chapitres_traites and not chapitres_erreur:
            reponse.append("❌ Aucun chapitre valide n'a été spécifié.")
        
        await ctx.send('\n'.join(reponse))
        
        manga_nom_formate = manga.strip()
        
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
        chapitre_key = f"{manga.lower()}_{chapitre}"
        
        if chapitre_key not in etat_taches_global:
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
        chapitre_key = f"{manga.lower()}_{chapitre}"
        
        if chapitre_key in etat_taches_global:
            del etat_taches_global[chapitre_key]
            sauvegarder_etat_taches()
            await ctx.send(f"✅ Toutes les tâches pour le chapitre **{chapitre}** de **{manga}** ont été supprimées.")
        else:
            await ctx.send(f"❌ Aucune tâche trouvée pour le chapitre **{chapitre}** de **{manga}**.")
    
    @bot.command(name="avancee")
    async def avancee(ctx):
        """Affiche l'avancée des mangas de manière interactive"""
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
        
        def check(reaction, user):
            return user == ctx.author and str(reaction.emoji) in reactions
        
        try:
            reaction, user = await bot.wait_for('reaction_add', timeout=30.0, check=check)
            manga_name = manga_map[str(reaction.emoji)]
            
            manga_chapters = {}
            for key in etat_taches_global:
                if key.startswith(manga_name.lower() + "_"):
                    chapter_num = int(key.split("_")[1])
                    manga_chapters[chapter_num] = etat_taches_global[key]
            
            if not manga_chapters:
                await ctx.send(f"❌ Aucune tâche trouvée pour **{manga_name}**.")
                return
            
            progress_embed = discord.Embed(
                title=f"🎯 Avancée de {manga_name}",
                description="Voici l'état d'avancement des chapitres :",
                color=discord.Color.green(),
                timestamp=datetime.now()
            )
            
            for chapter in sorted(manga_chapters.keys()):
                tasks = manga_chapters[chapter]
                progress = sum(1 for task in tasks.values() if task == "✅ Terminé")
                progress_bar = generate_progress_bar(progress, len(tasks))
                
                # Ajouter un emoji si le chapitre est complet
                chapter_title = f"📑 Chapitre {chapter}"
                if est_chapitre_complet(tasks):
                    chapter_title += " ✅"
                
                field_value = (
                    f"{progress_bar} ({progress}/{len(tasks)})\n"
                    f"Clean: {tasks['clean']}\n"
                    f"Trad: {tasks['trad']}\n"
                    f"Check: {tasks['check']}\n"
                    f"Edit: {tasks['edit']}"
                )
                
                progress_embed.add_field(
                    name=chapter_title,
                    value=field_value,
                    inline=False
                )
            
            progress_embed.set_footer(text=f"Demandé par {ctx.author.name}")
            await message.edit(embed=progress_embed)
        
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
        
        tasks_by_manga = {}
        for chapitre_key, tasks in etat_taches_global.items():
            manga, chapitre = chapitre_key.rsplit("_", 1)
            if manga not in tasks_by_manga:
                tasks_by_manga[manga] = {}
            tasks_by_manga[manga][chapitre] = tasks
        
        embeds = []
        for manga, chapitres in tasks_by_manga.items():
            embed = discord.Embed(
                title=f"📋 Tâches en cours - {manga.capitalize()}",
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
                    f"Clean: {tasks['clean']}\n"
                    f"Trad: {tasks['trad']}\n"
                    f"Check: {tasks['check']}\n"
                    f"Edit: {tasks['edit']}"
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