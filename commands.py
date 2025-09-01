# commands.py
import discord
from discord.ext import commands
from datetime import datetime
from config import CHANNELS, ROLES, COLORS
import logging
import asyncio
import json
import os

bot_instance = None

TASKS_FILE = "data/etat_taches.json"
os.makedirs("data", exist_ok=True)

# Dictionnaire pour stocker les chapitres planifiés
chapitres_planifies = []

# Ajout d'une structure globale pour stocker l'état des tâches
etat_taches_global = {}
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
    with open(TASKS_FILE, "w", encoding="utf-8") as f:
        json.dump(etat_taches_global, f, ensure_ascii=False, indent=4)

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

def setup(bot):
    charger_etat_taches()  # Charger les tâches depuis le fichier JSON au démarrage

    global bot_instance
    bot_instance = bot

    # Supprimer la commande d'aide par défaut
    bot.remove_command('help')

    @bot.command()
    async def help(ctx):
        """Affiche le menu d'aide des commandes"""
        # Vérifie si l'utilisateur a l'un des rôles admin
        admin_roles = [1326417422663680090, 1331346420883525682]
        user_roles = [role.id for role in ctx.author.roles]

        # Création de l'embed
        embed = discord.Embed(
            title="📚 **Menu d'Aide - LanorTrad Bot**",
            description=(
                "Bienvenue dans le menu d'aide ! Voici les commandes disponibles pour interagir avec le bot.\n\n"
                "🔹 **Commandes Générales** : Accessibles à tous.\n"
                "🔧 **Commandes Admin** : Réservées aux administrateurs."
            ),
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )

        # Ajout des commandes accessibles à tous
        embed.add_field(
            name="🎮 **Commandes Générales**",
            value=(
                "• `!help` - Afficher ce menu d'aide\n"
                "• `!info` - Informations du serveur\n"
                "• `!userinfo` - Détails du profil utilisateur\n"
                "• `!ping` - Vérifier la latence\n"
                "• `!avancee` - Voir l'avancée des chapitres\n"
            ),
            inline=False
        )

        # Si l'utilisateur a un rôle admin, ajouter les commandes admin
        if any(role in user_roles for role in admin_roles):
            embed.add_field(
                name="🔧 **Commandes Admin**",
                value=(
                    "• `!clear <nombre>` - Supprimer des messages\n"
                    "• `!kick @utilisateur [raison]` - Expulser un membre\n"
                    "• `!ban @utilisateur [raison]` - Bannir un membre\n"
                    "• `!unban nom_utilisateur#tag` - Débannir un membre\n"
                    "• `!warn @utilisateur [raison]` - Avertir un membre\n"
                    "• `!task <action> <manga> <chapitre>` - Mettre à jour l'état d'une tâche\n"
                    "• `!task_status <manga> <chapitre>` - Afficher l'état des tâches\n"
                    "• `!task_all` - Afficher toutes les tâches en cours\n"
                    "• `!delete_task <manga> <chapitre>` - Supprimer les tâches d'un chapitre\n"
                    "• `!newchapter_collab <manga> <chapitre> <lien>` - Annoncer un nouveau chapitre\n"
                ),
                inline=False
            )

        # Ajout d'une ligne de séparation
        embed.add_field(
            name="━━━━━━━━━━━━━━━━━━━━━━━",
            value="",
            inline=False
        )

        # Footer et envoi de l'embed
        embed.set_footer(
            text=f"Demandé par {ctx.author.name} | LanorTrad Bot",
            icon_url=ctx.author.avatar.url if ctx.author.avatar else None
        )

        # Ajout d'un thumbnail (icône du serveur)
        if ctx.guild.icon:
            embed.set_thumbnail(url=ctx.guild.icon.url)

        # Ajout d'une image illustrative (optionnel)
        embed.set_image(url="")  # Remplacez par une URL valide

        # Envoi de l'embed
        await ctx.send(embed=embed)

    @bot.command()
    @commands.has_permissions(manage_messages=True)
    async def clear(ctx, amount: int):
        """Supprime un nombre spécifié de messages"""
        if amount <= 0:
            await ctx.send("Le nombre de messages à supprimer doit être supérieur à 0.")
            return
            
        deleted = await ctx.channel.purge(limit=amount + 1)
        # Message de mention avant l'embed
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
        # Message de mention avant l'embed
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
        # Message de mention avant l'embed
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
                # Message de mention avant l'embed
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
        # Message de mention avant l'embed
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
        # Message de mention avant l'embed
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
        # Message de mention avant l'embed
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
        # Message de mention avant l'embed
        ping_message = f"🏓 {ctx.author.mention} a vérifié la latence du bot."
        await ctx.send(ping_message)
        
        embed = discord.Embed(
            title="🏓 Pong!",
            description=f"Latence: {round(bot.latency * 1000)}ms",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)

    @bot.command()
    @commands.has_any_role(1326417422663680090, 1331346420883525682)  # Autorise les deux rôles
    async def task(ctx, action: str, manga: str, *chapitres: str):
        """
        Met à jour l'état d'une tâche pour un ou plusieurs chapitres.
        Actions possibles : clean, trad, check, edit, release.
        Usage: !task <action> <manga> <chapitres>
        Exemple: !task trad "Catenaccio" 24 25 26
        """
        actions_valides = ["clean", "trad", "check", "edit", "release"]
        
        if action.lower() not in actions_valides:
            await ctx.send(f"❌ Action invalide. Actions possibles : {', '.join(actions_valides)}.")
            return

        # Traiter chaque chapitre fourni
        chapitres_traites = []
        chapitres_erreur = []

        for chapitre_str in chapitres:
            # Nettoyer la chaîne de caractères des virgules éventuelles
            chapitre_str = chapitre_str.strip().rstrip(',')
            
            try:
                chapitre = int(chapitre_str)
                # Initialiser l'état des tâches pour ce chapitre si non existant
                chapitre_key = f"{manga.lower()}_{chapitre}"
                if chapitre_key not in etat_taches_global:
                    etat_taches_global[chapitre_key] = {
                        "clean": "❌ Non commencé",
                        "trad": "❌ Non commencé",
                        "check": "❌ Non commencé",
                        "edit": "❌ Non commencé",
                        "release": "❌ Non commencé"
                    }

                # Mettre à jour l'état de la tâche
                etat_taches_global[chapitre_key][action.lower()] = "✅ Terminé"
                chapitres_traites.append(str(chapitre))
                
            except ValueError:
                chapitres_erreur.append(chapitre_str)
                continue

        # Sauvegarder les modifications
        sauvegarder_etat_taches()

        # Préparer le message de réponse
        reponse = []
        if chapitres_traites:
            reponse.append(f"✅ Tâche **{action}** mise à jour pour **{manga}** chapitres : **{', '.join(chapitres_traites)}**")
        
        if chapitres_erreur:
            reponse.append(f"❌ Chapitres invalides ignorés : {', '.join(chapitres_erreur)}")
        
        if not chapitres_traites and not chapitres_erreur:
            reponse.append("❌ Aucun chapitre valide n'a été spécifié.")

        await ctx.send('\n'.join(reponse))

                # ✅ Notification dans le forum pour les fans du manga
        manga_nom_formate = manga.strip()

        # Vérifie que le manga est bien défini dans les deux dictionnaires
        if manga_nom_formate in MANGA_CHANNELS and manga_nom_formate in MANGA_ROLES:
            thread_id = MANGA_CHANNELS[manga_nom_formate]
            role_id = MANGA_ROLES[manga_nom_formate]

            # Récupération du salon
            thread_channel = bot.get_channel(thread_id)
            if thread_channel:
                mention_role = f"<@&{role_id}>"
                chapitres_mention = ", ".join(chapitres_traites)
                await thread_channel.send(
                    f"{mention_role} Une nouvelle tâche **{action.upper()}** vient d'être effectuée "
                    f"pour **{manga_nom_formate}** chapitres : **{chapitres_mention}**.\n"
                    f"Utilisez la commande `!avancee` pour voir l'évolution du projet. 👀"
                )

    @bot.command()
    @commands.has_any_role(1326417422663680090, 1331346420883525682)  # Autorise les deux rôles
    async def task_status(ctx, manga: str, chapitre: int):
        """
        Affiche l'état des tâches pour un chapitre donné.
        """
        chapitre_key = f"{manga.lower()}_{chapitre}"
        if chapitre_key not in etat_taches_global:
            await ctx.send(f"❌ Aucun état trouvé pour le chapitre **{chapitre}** de **{manga}**.")
            return

        # Récupérer l'état des tâches
        etat_taches = etat_taches_global[chapitre_key]

        # Création de l'embed pour afficher l'état des tâches
        embed = discord.Embed(
            title=f"📋 État des Tâches : {manga} - Chapitre {chapitre}",
            color=discord.Color.blue()
        )
        for tache, etat in etat_taches.items():
            embed.add_field(name=tache.capitalize(), value=etat, inline=False)

        await ctx.send(embed=embed)

    @bot.command()
    @commands.has_any_role(1326417422663680090, 1331346420883525682)  # Autorise les deux rôles
    async def delete_task(ctx, manga: str, chapitre: int):
        """
        Supprime toutes les tâches associées à un chapitre donné.
        """
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
        # Création de l'embed initial
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

        # Envoyer l'embed
        message = await ctx.send(embed=embed)

        # Ajouter les réactions
        reactions = ['👹', '🩸', '🗼', '😈', '⚽']
        for reaction in reactions:
            await message.add_reaction(reaction)

        # Dictionnaire pour mapper les réactions aux noms de manga
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

            # Trouver tous les chapitres pour ce manga
            manga_chapters = {}
            for key in etat_taches_global:
                if key.startswith(manga_name.lower() + "_"):
                    chapter_num = int(key.split("_")[1])
                    manga_chapters[chapter_num] = etat_taches_global[key]

            if not manga_chapters:
                await ctx.send(f"❌ Aucune tâche trouvée pour **{manga_name}**.")
                return

            # Créer un embed pour l'avancée du manga
            progress_embed = discord.Embed(
                title=f"🎯 Avancée de {manga_name}",
                description="Voici l'état d'avancement des chapitres :",
                color=discord.Color.green(),
                timestamp=datetime.now()
            )

            # Tri des chapitres par numéro
            for chapter in sorted(manga_chapters.keys()):
                tasks = manga_chapters[chapter]
                progress = sum(1 for task in tasks.values() if task == "✅ Terminé")
                progress_bar = generate_progress_bar(progress, len(tasks))
                
                field_value = (
                    f"{progress_bar} ({progress}/{len(tasks)})\n"
                    f"Clean: {tasks['clean']}\n"
                    f"Trad: {tasks['trad']}\n"
                    f"Check: {tasks['check']}\n"
                    f"Edit: {tasks['edit']}\n"
                    f"Release: {tasks['release']}"
                )
                progress_embed.add_field(
                    name=f"📑 Chapitre {chapter}",
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

    @bot.command(name='newchapter_collab')
    @commands.has_permissions(administrator=True)
    async def announce_new_collab_chapter(ctx, manga_name: str, *chapters_and_link: str):
        """Annonce un ou plusieurs nouveaux chapitres collaboratifs"""

        manga_name_lower = manga_name.lower()

        allowed_mangas = {
            'catenaccio': 1332429989085184010,
            'uzugami': 1332430247894847529
        }

        if manga_name_lower not in allowed_mangas:
            await ctx.send("❌ Manga non reconnu. Options disponibles : `Catenaccio`, `Uzugami`")
            return

        # Le dernier argument est le lien, tout le reste ce sont les chapitres
        if len(chapters_and_link) < 2:
            await ctx.send("❌ Format invalide. Exemple : `!newchapter_collab Catenaccio 24 25 26 https://lien.com`")
            return

        *chapter_numbers, link = chapters_and_link

        role = ctx.guild.get_role(allowed_mangas[manga_name_lower])
        if not role:
            await ctx.send("❌ Le rôle spécifié n'a pas été trouvé.")
            return

        chapters_str = ", ".join([f"#{c}" for c in chapter_numbers])

        # Message d'annonce
        announcement_text = (
            f"{role.mention}\n"
            "───────────────────────\n"
            f"Nouveau(x) chapitre(s) de {manga_name.upper()} disponible(s) !\n"
            f"Chapitres : {chapters_str}\n"
            "Retrouvez tous les détails ci-dessous ⬇️"
        )

        # Embed
        embed = discord.Embed(
            title=f"🔥 NOUVEAU(x) CHAPITRE(s) DE {manga_name.upper()} 🔥",
            description="Préparez-vous à plonger dans de nouvelles aventures palpitantes !\n\n━━━━━━━━━━━━━━━━━━━━━━━",
            color=0x3498DB
        )

        embed.add_field(name="📖 Chapitres", value=chapters_str, inline=True)
        embed.add_field(name="⏰ Disponible", value="MAINTENANT !", inline=True)
        embed.add_field(name="📚 Lien de lecture", value=f"[Cliquez ici pour lire !]({link})", inline=False)

        embed.add_field(name="━━━━━━━━━━━━━━━━━━━━━━━", value="📱 Aperçu", inline=False)
        embed.add_field(name="", value=f"https://discord.com/invite/KKsp4AG8BV", inline=False)

        embed.set_footer(text="N'oubliez pas de partager vos théories et réactions ! 🎉")

        announcement = await ctx.send(announcement_text, embed=embed)

        for reaction in ['🔥', '👀', '❤️']:
            await announcement.add_reaction(reaction)

        await ctx.message.delete()


    @bot.command(name="task_all")
    @commands.has_any_role(1331345633977831496, 1331346420883525682)
    async def task_all(ctx):
        """
        Affiche toutes les tâches actuellement en cours, organisées par manga avec pagination.
        """
        if not etat_taches_global:
            await ctx.send("📋 Aucune tâche en cours actuellement.")
            return

        # Organiser les tâches par manga
        tasks_by_manga = {}
        for chapitre_key, tasks in etat_taches_global.items():
            manga, chapitre = chapitre_key.rsplit("_", 1)
            if manga not in tasks_by_manga:
                tasks_by_manga[manga] = {}
            tasks_by_manga[manga][chapitre] = tasks

        # Créer les embeds, un par manga
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

                field_value = (
                    f"{progress_bar} ({progress}/{len(tasks)})\n"
                    f"Clean: {tasks['clean']}\n"
                    f"Trad: {tasks['trad']}\n"
                    f"Check: {tasks['check']}\n"
                    f"Edit: {tasks['edit']}\n"
                    f"Release: {tasks['release']}"
                )

                embed.add_field(
                    name=f"📖 Chapitre {chapitre}",
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

        # Envoyer le premier embed
        current_page = 0
        message = await ctx.send(embed=embeds[current_page])

        # Ajouter les réactions pour la navigation
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
def generate_progress_bar(progress, total, size=10):
    """Génère une barre de progression visuelle"""
    percentage = progress / total
    filled = int(size * percentage)
    empty = size - filled

    return f"{'🟩' * filled}{'⬜' * empty}"

