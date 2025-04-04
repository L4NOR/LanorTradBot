# commands.py
import discord
from discord.ext import commands
from datetime import datetime
from config import CHANNELS, ROLES, COLORS
import logging

def setup(bot):
    # Supprimer la commande d'aide par défaut
    bot.remove_command('help')
    
    @bot.command()
    async def help(ctx):
        """Affiche le menu d'aide des commandes"""
        embed = discord.Embed(
            title="🤖 Guide des Commandes",
            description="Découvrez les commandes disponibles sur notre serveur",
            color=0x5865F2,  # Bleu Discord
            timestamp=datetime.now()
        )
        
        embed.add_field(
            name="🎮 Interaction Serveur",
            value="""
    ```
    !help     - Afficher ce menu d'aide
    !info     - Informations du serveur
    !userinfo - Détails du profil utilisateur
    !avatar   - Afficher l'avatar
    !ping     - Vérifier la latence
    !poll     - Créer un sondage
    !manga    - Rechercher les informations d'un manga 
    ```
    """,
            inline=False
        )
        
        embed.set_footer(
            text=f"Demandé par {ctx.author.name} | Utilisez !help pour plus d'infos",
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
    async def manga(ctx, *, title=None):
    """Rechercher les informations d'un manga"""
    if not title:
        embed = discord.Embed(
            title="❌ Titre manquant",
            description="Veuillez spécifier un titre de manga. Exemple: `!manga One Piece`",
            color=discord.Color.red()
        )
        return await ctx.send(embed=embed)
    
    # Message de mention avant l'embed
    manga_message = f"📚 {ctx.author.mention} a recherché des informations sur le manga \"{title}\"."
    await ctx.send(manga_message)
    
    # Simuler une recherche (à remplacer par une API réelle)
    embed = discord.Embed(
        title=f"📚 Informations sur {title}",
        description=f"Voici les informations disponibles sur ce manga:",
        color=COLORS["info"]
    )
    
    # Ajouter des champs fictifs (à remplacer par des données réelles)
    embed.add_field(name="Titre", value=title, inline=True)
    embed.add_field(name="Status", value="En cours", inline=True)
    embed.add_field(name="Auteur", value="Information non disponible", inline=True)
    embed.add_field(name="Genres", value="Information non disponible", inline=False)
    embed.add_field(name="Synopsis", value="Aucune information disponible pour le moment. Cette commande sera améliorée pour fournir des données réelles depuis une API de manga.", inline=False)
    
    # Ajouter une note sur la future amélioration
    embed.set_footer(text="Note: Cette commande affiche actuellement des données fictives et sera connectée à une API de manga prochainement.")
    
    await ctx.send(embed=embed)
