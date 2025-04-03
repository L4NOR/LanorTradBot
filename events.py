# events.py
import discord
from discord.ext import commands
import datetime
from config import CHANNELS, MESSAGES, ROLES, COLORS
import logging

def setup(bot):
    @bot.event
    async def on_ready():
        """Événement déclenché lorsque le bot est prêt"""
        logging.info(f'Bot connecté en tant que {bot.user.name}')
        await bot.change_presence(activity=discord.Game(name="!help pour les commandes"))
        await bot.setup_webserver()
    
    @bot.event
    async def on_raw_reaction_add(payload):
        """Événement déclenché lorsqu'une réaction est ajoutée à un message"""
        if payload.message_id == MESSAGES["rules"]:
            if str(payload.emoji) == "✅":
                guild = bot.get_guild(payload.guild_id)
                member = guild.get_member(payload.user_id)
                
                # Rôles à ajouter
                first_role = guild.get_role(ROLES["member"])
                second_role = guild.get_role(ROLES["access"])
                
                if first_role and second_role:
                    try:
                        # Ajouter les deux rôles
                        await member.add_roles(first_role, second_role)
                        
                        general_channel = bot.get_channel(CHANNELS["general"])
                        embed = discord.Embed(
                            title="🎉 Nouveau membre respectueux !",
                            description=f"{member.mention} a accepté le règlement et rejoint notre communauté. Bienvenue à toi ! ✨",
                            color=discord.Color.green()
                        )
                        if member.avatar:
                            embed.set_thumbnail(url=member.avatar.url)
                        await general_channel.send(embed=embed)
                    except Exception as e:
                        logging.error(f"Erreur lors de l'ajout des rôles : {e}")
    
    @bot.event
    async def on_member_join(member):
        """Événement déclenché quand un membre rejoint le serveur"""
        welcome_channel = bot.get_channel(CHANNELS["welcome"])
        if welcome_channel:
            # Message de mention avant l'embed
            welcome_message = f"👋 Hey tout le monde ! Accueillons chaleureusement {member.mention} qui vient de nous rejoindre ! 🎉"
            await welcome_channel.send(welcome_message)
            
            embed = discord.Embed(
                title=f"🌟 Bienvenue sur {member.guild.name} !",
                description=(
                    f"Hey {member.mention}, bienvenue dans notre communauté !\n\n"
                    "🎉 **Nous sommes ravis de t'accueillir parmi nous !**\n\n"
                    "Pour bien commencer :\n"
                    f"📜 Lis le règlement dans <#{CHANNELS['rules']}>\n"
                    "🎯 Choisis tes rôles dans <#1326212401036529665>\n"
                    f"💬 Présente-toi dans <#{CHANNELS['general']}>\n"
                    "🎮 Amuse-toi et fais de belles rencontres !"
                ),
                color=discord.Color.blue()
            )
            embed.add_field(
                name="📊 Statistiques",
                value=f"Tu es notre {len(member.guild.members)} ème membre !",
                inline=True
            )
            embed.add_field(
                name="📅 Date d'arrivée",
                value=f"<t:{int(datetime.datetime.now().timestamp())}:F>",
                inline=True
            )
            if member.avatar:
                embed.set_thumbnail(url=member.avatar.url)
            embed.set_footer(text="Nous espérons que tu te plairas parmi nous ! 🎮✨")
            await welcome_channel.send(embed=embed)
    
    @bot.event
    async def on_message(message):
        """Événement déclenché à chaque message"""
        # Ignorer les messages du bot lui-même
        if message.author == bot.user:
            return
        
        # Liste des commandes à ignorer pour LanorTrad
        ignored_commands = ["!Shiki", "!Yomi", "!Kingo", "!Rin", "!Mitsuo", "!tiktok", "!twitter"]
        
        # Vérifier si le message commence par une commande ignorée et provient de LanorTrad
        if message.author.name == "LanorTrad" and any(message.content.startswith(cmd) for cmd in ignored_commands):
            return  # Ne pas traiter ces commandes spécifiques
        
        # Ignorer les autres messages du bot LanorTrad
        if message.author.name == "LanorTrad":
            return
        
        # Vérifier si le message est dans le canal spécifique
        if message.channel.id == CHANNELS["lanortrad_channel"]:
            role = message.guild.get_role(ROLES["lanortrad_ping"])
            if role:
                await message.channel.send(f"{role.mention}")
        
        # Nécessaire pour que les commandes fonctionnent également
        await bot.process_commands(message)
    
    @bot.event
    async def on_command_error(ctx, error):
        """Gestion globale des erreurs de commandes"""
        if isinstance(error, commands.CommandNotFound):
            await ctx.send(f"Commande inconnue. Utilisez `{bot.command_prefix}help` pour voir la liste des commandes.")
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"Il manque un argument requis. Utilisez `{bot.command_prefix}help {ctx.command.name}` pour plus d'informations.")
        elif isinstance(error, commands.BadArgument):
            await ctx.send("L'un des arguments fournis est invalide.")
        elif isinstance(error, commands.MissingPermissions):
            embed = discord.Embed(
                title="❌ Erreur",
                description="Vous n'avez pas les permissions nécessaires pour exécuter cette commande.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
        else:
            # Log l'erreur pour débogage
            logging.error(f"Erreur non gérée: {type(error).__name__}: {error}")
