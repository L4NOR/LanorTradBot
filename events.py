# events.py
# ═══════════════════════════════════════════════════════════════════════════════
# GESTIONNAIRES D'ÉVÉNEMENTS DISCORD
# ═══════════════════════════════════════════════════════════════════════════════

import discord
from discord.ext import commands
import datetime
import logging
import asyncio
from config import CHANNELS, MESSAGES, ROLES, COLORS, PING_COOLDOWN_SECONDS

# Dictionnaire pour stocker le dernier ping par canal (cooldown)
last_ping_time = {}


def setup(bot):
    """Configure les événements du bot."""
    
    @bot.event
    async def on_ready():
        """Événement déclenché lorsque le bot est prêt."""
        logging.info(f'Bot connecté en tant que {bot.user.name}')
        await bot.change_presence(activity=discord.Game(name="!help pour les commandes"))
    
    @bot.event
    async def on_raw_reaction_add(payload):
        """Événement déclenché lorsqu'une réaction est ajoutée à un message."""
        # Vérifier si c'est le message des règles
        if payload.message_id == MESSAGES["rules"]:
            if str(payload.emoji) == "✅":
                guild = bot.get_guild(payload.guild_id)
                member = guild.get_member(payload.user_id)
                
                if member is None or member.bot:
                    return

                # Rôles à ajouter
                first_role = guild.get_role(ROLES["member"])
                second_role = guild.get_role(ROLES["access"])

                if first_role and second_role:
                    # Ne rien faire si le membre a déjà les rôles (évite les doublons)
                    if first_role in member.roles and second_role in member.roles:
                        return

                    try:
                        # Ajouter les deux rôles
                        await member.add_roles(first_role, second_role)

                        general_channel = bot.get_channel(CHANNELS["general"])
                        if general_channel:
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
        """Événement déclenché quand un membre rejoint le serveur."""
        welcome_channel = bot.get_channel(CHANNELS["welcome"])
        if not welcome_channel:
            return

        embed = discord.Embed(
            title=f"🌟 Bienvenue sur {member.guild.name} !",
            description=(
                f"Hey {member.mention}, bienvenue dans notre communauté !\n\n"
                "🎉 **Nous sommes ravis de t'accueillir parmi nous !**\n\n"
                "Pour bien commencer :\n"
                f"📜 Lis le règlement dans <#{CHANNELS['rules']}>\n"
                f"🎯 Choisis tes rôles dans <#{CHANNELS.get('roles', 1326212401036529665)}>\n"
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

        # Un seul message : mention + embed (au lieu de deux)
        await welcome_channel.send(
            content=f"👋 {member.mention} vient de nous rejoindre ! 🎉",
            embed=embed,
        )
    
    @bot.event
    async def on_message(message):
        """Événement déclenché à chaque message."""
        global last_ping_time
        
        # Ignorer les messages du bot lui-même
        if message.author == bot.user:
            return
        
        # Vérifier si le message est dans le canal des partenaires
        if message.channel.id == CHANNELS["partenaires_channel"]:
            # Ne pas pinger pour les messages du bot lui-même ou de LanorTrad
            if message.author.name != "LanorTrad":
                try:
                    # Vérifier le cooldown
                    current_time = datetime.datetime.now()
                    channel_id = message.channel.id
                    
                    # Si le canal a déjà été pingé récemment, vérifier le cooldown
                    if channel_id in last_ping_time:
                        time_since_last_ping = (current_time - last_ping_time[channel_id]).total_seconds()
                        
                        # Si le cooldown n'est pas écoulé, ne pas pinger
                        if time_since_last_ping < PING_COOLDOWN_SECONDS:
                            logging.info(f"Cooldown actif pour le canal {message.channel.name}. "
                                       f"Temps restant: {PING_COOLDOWN_SECONDS - time_since_last_ping:.0f}s")
                            # Traiter quand même les commandes
                            await bot.process_commands(message)
                            return
                    
                    # Envoyer le ping si le cooldown est écoulé ou si c'est le premier ping
                    role = message.guild.get_role(ROLES["partenaires_ping"])
                    if role:
                        logging.info(f"Envoi d'un ping pour le rôle {role.name} dans le canal {message.channel.name}")
                        await message.channel.send(f"{role.mention}")
                        # Mettre à jour le dernier temps de ping
                        last_ping_time[channel_id] = current_time
                except Exception as e:
                    logging.error(f"Erreur lors de l'envoi du ping pour les partenaires : {e}")
        
        # CORRECTION CRITIQUE : Nécessaire pour que les commandes fonctionnent
        await bot.process_commands(message)
    
    @bot.event
    async def on_command_error(ctx, error):
        """Gestion globale des erreurs de commandes."""
        if isinstance(error, commands.CommandNotFound):
            return  # silencieux : ne pas polluer le chat sur frappe libre
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
        elif isinstance(error, commands.MissingAnyRole):
            embed = discord.Embed(
                title="❌ Erreur",
                description="Vous n'avez pas le rôle requis pour exécuter cette commande.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
        elif isinstance(error, commands.CommandOnCooldown):
            remaining = float(error.retry_after)
            total = float(getattr(error.cooldown, "per", remaining)) if getattr(error, "cooldown", None) else remaining
            if total <= 0:
                total = remaining

            # Barre de progression visuelle
            bar_length = 12
            elapsed = max(0.0, total - remaining)
            filled = int(round(bar_length * (elapsed / total))) if total > 0 else 0
            filled = max(0, min(bar_length, filled))
            bar = "🟩" * filled + "⬜" * (bar_length - filled)
            pct = int((elapsed / total) * 100) if total > 0 else 0

            # Temps restant formaté
            if remaining >= 60:
                mins = int(remaining // 60)
                secs = int(remaining % 60)
                time_txt = f"{mins}m {secs:02d}s"
            else:
                time_txt = f"{remaining:.1f}s"

            # Timestamp absolu pour l'affichage dynamique de Discord
            retry_at = int(datetime.datetime.now().timestamp() + remaining)

            embed = discord.Embed(
                title="⏳ Commande en cooldown",
                description=(
                    f"`{bar}` **{pct}%**\n"
                    f"⏱️ Temps restant : **{time_txt}** "
                    f"(prêt <t:{retry_at}:R>)"
                ),
                color=discord.Color.orange(),
            )
            cmd_name = getattr(ctx.command, "name", None)
            if cmd_name:
                embed.set_footer(text=f"Commande : !{cmd_name}")
            try:
                await ctx.send(embed=embed, delete_after=min(10, max(3, int(remaining))))
            except Exception:
                pass
        elif isinstance(error, commands.CommandInvokeError) and isinstance(error.original, discord.HTTPException):
            if error.original.status == 429:
                retry_after = getattr(error.original, 'retry_after', 5)
                # Ajouter un buffer de sécurité au retry_after
                wait_time = (retry_after if retry_after else 5) + 2
                logging.warning(
                    f"⚠️ RATE LIMITED 429 ! Commande: {ctx.command}, "
                    f"User: {ctx.author}, Attente de {wait_time:.1f}s"
                )
                await asyncio.sleep(wait_time)
                # Informer l'utilisateur
                try:
                    embed = discord.Embed(
                        title="⚠️ Rate Limit Discord",
                        description=(
                            f"Le bot a été temporairement limité par Discord.\n"
                            f"Réessayez dans **{int(wait_time)}** secondes."
                        ),
                        color=discord.Color.orange()
                    )
                    await ctx.send(embed=embed, delete_after=10)
                except:
                    pass
            else:
                logging.error(f"HTTPException {error.original.status}: {error.original}")
        else:
            # Log l'erreur pour débogage
            logging.error(f"Erreur non gérée: {type(error).__name__}: {error}")
