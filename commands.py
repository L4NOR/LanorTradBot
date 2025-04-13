# commands.py
import discord
from discord.ext import commands
from datetime import datetime
from config import CHANNELS, ROLES, COLORS
import logging
import asyncio

# Dictionnaire pour stocker les chapitres planifiés
chapitres_planifies = []

# Dictionnaire pour stocker les scores de bump
bump_scores = []

# Ajout d'une structure globale pour stocker l'état des tâches
etat_taches_global = {}

def setup(bot):
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
                "• `!avatar` - Afficher l'avatar\n"
                "• `!ping` - Vérifier la latence\n"
                "• `!poll` - Créer un sondage\n"
                "• `!avancee` - Voir l'avancée des chapitres\n" 
            ),
            inline=False
        )

        # Si l'utilisateur a un rôle admin, ajouter les commandes admin
        if any(role in user_roles for role in admin_roles):
            embed.add_field(
                name="🔧 **Commandes Admin**",
                value=(
                    "• `!planifier` - Planifier un chapitre\n"
                    "• `!supprimer_chapitre` - Supprimer un chapitre planifié\n"
                    "• `!calendrier` - Afficher les chapitres planifiés\n"
                    "• `!task` - Mettre à jour l'état d'une tâche\n"
                    "• `!task_status` - Afficher l'état des tâches\n"
                    "• `!delete_task` - Supprimer toutes les tâches d'un chapitre"
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
    async def poll(ctx, *, poll_input=None):
        """Crée un sondage"""
        if not poll_input:
            embed = discord.Embed(
                title="❌ Erreur de création de sondage",
                description=(
                    "Utilisation correcte : `!poll \"Votre question\" Option1 Option2 Option3...`\n\n"
                    "Règles :\n"
                    "• Mettez la question entre guillemets\n"
                    "• Ajoutez 2-10 options séparées par des espaces\n"
                    "• Exemple : `!poll \"Quel est votre jeu préféré ?\" Minecraft Fortnite Roblox`"
                ),
                color=discord.Color.red()
            )
            return await ctx.send(embed=embed)
        
        # Split the input, first part is the question (in quotes), rest are options
        try:
            parts = poll_input.split('"')
            question = parts[1].strip()
            options = parts[2].strip().split()
        except (IndexError, ValueError):
            embed = discord.Embed(
                title="❌ Format de sondage incorrect",
                description="Assurez-vous de mettre la question entre guillemets.",
                color=discord.Color.red()
            )
            return await ctx.send(embed=embed)

        # Validate options
        if len(options) < 2:
            embed = discord.Embed(
                title="❌ Pas assez d'options",
                description="Un sondage nécessite au moins 2 options.",
                color=discord.Color.red()
            )
            return await ctx.send(embed=embed)

        if len(options) > 10:
            embed = discord.Embed(
                title="❌ Trop d'options",
                description="Un sondage ne peut pas avoir plus de 10 options.",
                color=discord.Color.red()
            )
            return await ctx.send(embed=embed)
        
        # Emoji for reactions
        reactions = ['1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣', '6️⃣', '7️⃣', '8️⃣', '9️⃣', '🔟']
        
        # Prepare poll description
        description = []
        for i, option in enumerate(options):
            description.append(f"{reactions[i]} {option}")
        
        # Create poll embed
        embed = discord.Embed(
            title=f"📊 Sondage : {question}",
            description='\n'.join(description),
            color=discord.Color.blue()
        )
        embed.set_footer(text=f"Sondage créé par {ctx.author.name}")
        
        # Send poll message
        poll_msg = await ctx.send(embed=embed)
        
        # Add reaction emojis
        for i in range(len(options)):
            await poll_msg.add_reaction(reactions[i])

    @bot.command()
    async def avatar(ctx, member: discord.Member = None):
        """Affiche l'avatar d'un utilisateur"""
        member = member or ctx.author
        
        embed = discord.Embed(
            title=f"Avatar de {member.name}",
            color=member.color
        )
        if member.avatar:
            embed.set_image(url=member.avatar.url)
        
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
    async def planifier(ctx, manga: str, chapitre: int, date: str):
        """Planifie un chapitre pour une date donnée"""
        try:
            # Vérifier si la date est valide
            datetime.strptime(date, "%d/%m/%Y")
        except ValueError:
            await ctx.send("❌ Format de date invalide. Utilisez le format `JJ/MM/AAAA`.")
            return

        # Ajouter le chapitre au dictionnaire
        chapitres_planifies.append({"manga": manga, "chapitre": chapitre, "date": date})
        await ctx.send(f"✅ Chapitre **{chapitre}** de **{manga}** planifié pour le **{date}**.")

    @bot.command()
    async def supprimer_chapitre(ctx, manga: str, chapitre: int):
        """Supprime un chapitre planifié"""
        global chapitres_planifies
        for chapitre_planifie in chapitres_planifies:
            if chapitre_planifie["manga"] == manga and chapitre_planifie["chapitre"] == chapitre:
                chapitres_planifies.remove(chapitre_planifie)
                await ctx.send(f"✅ Chapitre **{chapitre}** de **{manga}** supprimé du planning.")
                return

        await ctx.send(f"❌ Aucun chapitre **{chapitre}** de **{manga}** trouvé dans le planning.")

    @bot.command()
    async def calendrier(ctx):
        """Affiche les chapitres planifiés"""
        if not chapitres_planifies:
            await ctx.send("📅 Aucun chapitre n'est actuellement planifié.")
            return

        # Création de l'embed
        embed = discord.Embed(
            title="📅 **Calendrier des Prochains Chapitres**",
            description="Voici les chapitres planifiés :",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )

        # Ajout des chapitres au contenu de l'embed
        for chapitre in chapitres_planifies:
            embed.add_field(
                name=f"📖 **{chapitre['manga']}** - Chapitre **{chapitre['chapitre']}**",
                value=f" **Sortie prévue** : {chapitre['date']}",
                inline=False
            )

        # Footer et envoi de l'embed
        embed.set_footer(
            text=f"Demandé par {ctx.author.name} • Team LanorTrad",
            icon_url=ctx.author.avatar.url if ctx.author.avatar else None
        )
        await ctx.send(embed=embed)

    @bot.command()
    @commands.has_any_role(1331345633977831496, 1331346420883525682)  # Autorise les deux rôles
    async def task(ctx, action: str, manga: str, chapitre: int):
        """
        Met à jour l'état d'une tâche pour un chapitre.
        Actions possibles : clean, trad, check, edit, release.
        """
        actions_valides = ["clean", "trad", "check", "edit", "release"]
        
        if action.lower() not in actions_valides:
            await ctx.send(f"❌ Action invalide. Actions possibles : {', '.join(actions_valides)}.")
            return

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
        await ctx.send(f"✅ Tâche **{action}** pour le chapitre **{chapitre}** de **{manga}** mise à jour avec succès !")

    @bot.command()
    @commands.has_any_role(1331345633977831496, 1331346420883525682)  # Autorise les deux rôles
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
    @commands.has_any_role(1331345633977831496, 1331346420883525682)  # Autorise les deux rôles
    async def delete_task(ctx, manga: str, chapitre: int):
        """
        Supprime toutes les tâches associées à un chapitre donné.
        """
        chapitre_key = f"{manga.lower()}_{chapitre}"
        if chapitre_key in etat_taches_global:
            del etat_taches_global[chapitre_key]
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

# Commande pour annoncer un nouveau chapitre collaboratif
    @bot.command(name='newchapter_collab')
    @commands.has_permissions(administrator=True)
    async def announce_new_collab_chapter(ctx, manga_name: str, chapter_number: str, link: str):
        """Annonce un nouveau chapitre collaboratif"""
        
        manga_name_lower = manga_name.lower()
        
        allowed_mangas = {
            'catenaccio': 1332429989085184010,
            'uzugami': 1332430247894847529
        }

        if manga_name_lower not in allowed_mangas:
            await ctx.send("❌ Manga non reconnu. Options disponibles : `Catenaccio`, `Uzugami`")
            return

        role = ctx.guild.get_role(allowed_mangas[manga_name_lower])
        if not role:
            await ctx.send("❌ Le rôle spécifié n'a pas été trouvé.")
            return

        # Message d'annonce modifié
        announcement_text = (
            f"{role.mention}\n"
            "───────────────────────\n"
            f"Un nouveau chapitre de {manga_name.upper()} vient d'être publié !\n"
            "Retrouvez tous les détails ci-dessous ⬇️"
        )

        # Embed modifié avec plus de détails
        embed = discord.Embed(
            title=f"🔥 NOUVEAU CHAPITRE DE {manga_name.upper()} 🔥",
            description=(
                "Un nouveau chapitre vient d'arriver ! Préparez-vous à plonger dans de nouvelles "
                "aventures palpitantes !\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━━\n"
            ),
            color=0x3498DB
        )

        # Champs modifiés avec emojis et formatage
        embed.add_field(
            name="📖 Chapitre",
            value=f"#{chapter_number}",
            inline=True
        )

        embed.add_field(
            name="⏰ Disponible",
            value="MAINTENANT !",
            inline=True
        )

        embed.add_field(
            name="📚 Lien de lecture",
            value=f"[Cliquez ici pour lire le chapitre !]({link})",
            inline=False
        )

        embed.add_field(
            name="━━━━━━━━━━━━━━━━━━━━━━━",
            value="📱 Aperçu",
            inline=False
        )

        # Aperçu avec lien Discord (comme dans l'image)
        embed.add_field(
            name="",
            value=f"[https://discord.com/invite/KKsp4AG8BV]({link})",
            inline=False
        )

        # Footer modifié
        embed.set_footer(
            text="N'oubliez pas de partager vos théories et réactions sur twitter et discord ! Bonne lecture à tous ! 🎉"
        )

        # Envoi du message
        announcement = await ctx.send(announcement_text, embed=embed)

        # Réactions modifiées pour correspondre à l'image
        reactions = ['🔥', '👀', '❤️']
        for reaction in reactions:
            await announcement.add_reaction(reaction)

        # Supprimer la commande
        await ctx.message.delete()

def generate_progress_bar(progress, total, size=10):
    """Génère une barre de progression visuelle"""
    percentage = progress / total
    filled = int(size * percentage)
    empty = size - filled
    return f"{'🟩' * filled}{'⬜' * empty}"
