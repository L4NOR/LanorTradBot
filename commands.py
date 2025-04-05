# commands.py
import discord
from discord.ext import commands
from datetime import datetime
from config import CHANNELS, ROLES, COLORS
import logging

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
                    "• `!task_status` - Afficher l'état des tâches"
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
                value=f" *Sortie prévue** : {chapitre['date']}",
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
