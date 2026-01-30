# dm_reminder.py
# ═══════════════════════════════════════════════════════════════════════════════
# SYSTÈME DE RAPPEL DM POUR LES MEMBRES SANS RÉACTION AU MESSAGE DES RÔLES
# ═══════════════════════════════════════════════════════════════════════════════

import discord
from discord.ext import commands, tasks
from config import ADMIN_ROLES, DM_REMINDER_CONFIG, DATA_FILES, MESSAGES
from utils import load_json, save_json, save_with_meta
import datetime
import asyncio
import pytz
import logging

# Configuration depuis config.py
ROLE_MESSAGE_ID = DM_REMINDER_CONFIG["role_message_id"]
ROLE_CHANNEL_ID = DM_REMINDER_CONFIG["role_channel_id"]
SEND_HOUR = DM_REMINDER_CONFIG["send_hour"]
TIMEZONE = pytz.timezone(DM_REMINDER_CONFIG["timezone"])

# Fichiers de données
DM_REMINDER_FILE = DATA_FILES["dm_reminder"]
DM_REMINDER_META_FILE = DATA_FILES["dm_reminder_meta"]

# Structure: {"user_id": {"notified_at": "ISO_DATE", "dm_count": int}}
notified_users = {}

# Variable pour éviter d'envoyer plusieurs fois dans la même journée
last_dm_date = None


def charger_notified():
    """Charge la liste des utilisateurs déjà notifiés."""
    global notified_users
    notified_users = load_json(DM_REMINDER_FILE, {})
    logging.info(f"📬 {len(notified_users)} utilisateur(s) déjà notifié(s) chargé(s)")


def sauvegarder_notified():
    """Sauvegarde la liste des utilisateurs notifiés."""
    success = save_with_meta(DM_REMINDER_FILE, notified_users, DM_REMINDER_META_FILE)
    if success:
        logging.info(f"✅ DM Reminder sauvegardé ({len(notified_users)} utilisateurs)")


class DMReminder(commands.Cog):
    """Système de rappel DM pour les membres sans réaction au message des rôles."""
    
    def __init__(self, bot):
        self.bot = bot
        self.role_message = None
        self.role_channel = None
        charger_notified()
        self.dm_reminder_task.start()
    
    def cog_unload(self):
        """Arrête la tâche quand le cog est déchargé."""
        self.dm_reminder_task.cancel()
        sauvegarder_notified()
    
    async def get_role_message(self, guild):
        """Récupère le message des rôles (avec cache)."""
        if self.role_message:
            return self.role_message
        
        # Chercher le message dans tous les canaux textuels si ROLE_CHANNEL_ID non défini
        if ROLE_CHANNEL_ID:
            channel = guild.get_channel(ROLE_CHANNEL_ID)
            if channel:
                try:
                    self.role_message = await channel.fetch_message(ROLE_MESSAGE_ID)
                    self.role_channel = channel
                    return self.role_message
                except discord.NotFound:
                    logging.error(f"❌ Message {ROLE_MESSAGE_ID} non trouvé dans le canal {ROLE_CHANNEL_ID}")
                    return None
        
        # Recherche automatique dans tous les canaux textuels
        for channel in guild.text_channels:
            try:
                self.role_message = await channel.fetch_message(ROLE_MESSAGE_ID)
                self.role_channel = channel
                logging.info(f"✅ Message trouvé dans #{channel.name}")
                return self.role_message
            except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                continue
        
        logging.error(f"❌ Message {ROLE_MESSAGE_ID} introuvable sur le serveur")
        return None
    
    async def get_users_who_reacted(self, message):
        """Récupère tous les utilisateurs ayant réagi au message."""
        reacted_users = set()
        
        for reaction in message.reactions:
            async for user in reaction.users():
                if not user.bot:
                    reacted_users.add(user.id)
        
        return reacted_users
    
    async def send_dm_reminder(self, member):
        """Envoie un DM de rappel à un membre."""
        try:
            embed = discord.Embed(
                title="📢 Mise à jour importante sur LanorTrad !",
                description=(
                    "Salut ! 👋\n\n"
                    "Suite à une **réorganisation des rôles** sur le serveur LanorTrad, "
                    "tu as peut-être perdu certains de tes rôles de notification.\n\n"
                    "**Pas de panique !** Pour continuer à recevoir les news de tes mangas préférés, "
                    "il te suffit de **réagir au message des rôles** sur le serveur.\n\n"
                    "━━━━━━━━━━━━━━━━━━━━━━━━"
                ),
                color=discord.Color.blue(),
                timestamp=datetime.datetime.now(TIMEZONE)
            )
            
            # Lien vers le message si disponible
            if self.role_channel:
                message_link = f"https://discord.com/channels/{self.role_channel.guild.id}/{self.role_channel.id}/{ROLE_MESSAGE_ID}"
                embed.add_field(
                    name="🔗 Lien direct",
                    value=f"[Clique ici pour accéder au message des rôles]({message_link})",
                    inline=False
                )
            
            embed.add_field(
                name="📚 Mangas disponibles",
                value=(
                    "• 🔥 Ao No Exorcist\n"
                    "• ⚔️ Satsudou\n"
                    "• 🏙️ Tokyo Underworld\n"
                    "• 👹 Tougen Anki\n"
                    "• ⚽ Catenaccio"
                ),
                inline=True
            )
            
            embed.add_field(
                name="🔔 Notifications",
                value=(
                    "• 📢 Annonces\n"
                    "• 🎉 Événements\n"
                    "• 🎁 Giveaway\n"
                    "• Et plus encore !"
                ),
                inline=True
            )
            
            embed.add_field(
                name="ℹ️ Info",
                value=(
                    "Une fois que tu auras réagi au message des rôles, "
                    "tu ne recevras plus ce rappel.\n\n"
                    "Si tu ne souhaites plus recevoir de notifications, "
                    "tu peux simplement ignorer ce message. 😊"
                ),
                inline=False
            )
            
            embed.set_footer(text="LanorTrad • Ce message est automatique")
            
            await member.send(embed=embed)
            return True
            
        except discord.Forbidden:
            logging.warning(f"⚠️ Impossible d'envoyer un DM à {member.name} (DMs fermés)")
            return False
        except Exception as e:
            logging.error(f"❌ Erreur envoi DM à {member.name}: {e}")
            return False
    
    @tasks.loop(minutes=5)
    async def dm_reminder_task(self):
        """Tâche planifiée pour envoyer les rappels DM à l'heure configurée."""
        global last_dm_date
        
        now = datetime.datetime.now(TIMEZONE)
        current_date = now.date()
        
        # Vérifier si c'est l'heure et qu'on n'a pas déjà envoyé aujourd'hui
        if now.hour != SEND_HOUR or last_dm_date == current_date:
            return
        
        logging.info(f"📬 Déclenchement des rappels DM à {now.strftime('%Y-%m-%d %H:%M:%S')}")
        last_dm_date = current_date
        
        # Récupérer le premier guild du bot
        if not self.bot.guilds:
            logging.error("❌ Aucun serveur trouvé")
            return
        
        guild = self.bot.guilds[0]
        
        # Récupérer le message des rôles
        message = await self.get_role_message(guild)
        if not message:
            logging.error("❌ Impossible de trouver le message des rôles")
            return
        
        # Récupérer les utilisateurs ayant réagi
        reacted_users = await self.get_users_who_reacted(message)
        
        sent = 0
        failed = 0
        skipped = 0
        limit = 20  # Limite quotidienne
        
        for member in guild.members:
            if sent >= limit:
                break
            
            if member.bot:
                continue
            
            if member.id in reacted_users:
                continue
            
            # Vérifier si déjà notifié récemment
            user_data = notified_users.get(str(member.id), {})
            last_notified = user_data.get("last_notified")
            
            if last_notified:
                try:
                    last_date = datetime.datetime.fromisoformat(last_notified).date()
                    days_since = (current_date - last_date).days
                    
                    if days_since < 7:  # Ne pas re-notifier avant 7 jours
                        skipped += 1
                        continue
                except:
                    pass
            
            # Envoyer le DM
            success = await self.send_dm_reminder(member)
            
            if success:
                sent += 1
                notified_users[str(member.id)] = {
                    "last_notified": now.isoformat(),
                    "dm_count": user_data.get("dm_count", 0) + 1,
                    "username": member.name
                }
            else:
                failed += 1
            
            await asyncio.sleep(1.5)  # Rate limiting
        
        sauvegarder_notified()
        logging.info(f"📊 Résumé DM: {sent} envoyé(s), {failed} échoué(s), {skipped} ignoré(s)")
    
    @dm_reminder_task.before_loop
    async def before_dm_task(self):
        await self.bot.wait_until_ready()
    
    @commands.command(name="dm_reminder_status")
    @commands.has_any_role(*ADMIN_ROLES)
    async def dm_reminder_status(self, ctx):
        """Affiche le statut du système de rappel DM."""
        embed = discord.Embed(
            title="📊 Statut DM Reminder",
            color=discord.Color.blue(),
            timestamp=datetime.datetime.now(TIMEZONE)
        )
        
        # Récupérer le message
        message = await self.get_role_message(ctx.guild)
        
        if not message:
            embed.description = f"❌ Message `{ROLE_MESSAGE_ID}` introuvable."
            await ctx.send(embed=embed)
            return
        
        # Compter les réactions
        reacted_users = await self.get_users_who_reacted(message)
        
        # Compter les membres sans réaction
        members_without_reaction = sum(
            1 for member in ctx.guild.members 
            if not member.bot and member.id not in reacted_users
        )
        
        embed.add_field(
            name="📄 Message trouvé",
            value=f"Dans #{self.role_channel.name}" if self.role_channel else "Oui",
            inline=True
        )
        embed.add_field(
            name="✅ Ont réagi",
            value=f"{len(reacted_users)} membre(s)",
            inline=True
        )
        embed.add_field(
            name="❌ N'ont pas réagi",
            value=f"{members_without_reaction} membre(s)",
            inline=True
        )
        embed.add_field(
            name="📬 Déjà notifiés",
            value=f"{len(notified_users)} utilisateur(s)",
            inline=True
        )
        
        if self.role_channel:
            link = f"https://discord.com/channels/{ctx.guild.id}/{self.role_channel.id}/{ROLE_MESSAGE_ID}"
            embed.add_field(name="🔗 Lien", value=f"[Voir le message]({link})", inline=True)
        
        await ctx.send(embed=embed)
    
    @commands.command(name="dm_reminder_force")
    @commands.has_any_role(*ADMIN_ROLES)
    async def dm_reminder_force(self, ctx, limit: int = 10):
        """Force l'envoi des rappels DM maintenant (avec limite)."""
        if limit < 1:
            limit = 1
        if limit > 50:
            limit = 50
        
        embed = discord.Embed(
            title="⚡ Envoi forcé des DM",
            description=f"Envoi en cours (limite: {limit})...",
            color=discord.Color.orange()
        )
        msg = await ctx.send(embed=embed)
        
        message = await self.get_role_message(ctx.guild)
        
        if not message:
            embed.description = f"❌ Message `{ROLE_MESSAGE_ID}` introuvable."
            embed.color = discord.Color.red()
            await msg.edit(embed=embed)
            return
        
        reacted_users = await self.get_users_who_reacted(message)
        
        sent = 0
        failed = 0
        
        for member in ctx.guild.members:
            if sent >= limit:
                break
            
            if member.bot or member.id in reacted_users:
                continue
            
            success = await self.send_dm_reminder(member)
            
            if success:
                sent += 1
                notified_users[str(member.id)] = {
                    "last_notified": datetime.datetime.now(TIMEZONE).isoformat(),
                    "dm_count": notified_users.get(str(member.id), {}).get("dm_count", 0) + 1,
                    "username": member.name
                }
            else:
                failed += 1
            
            await asyncio.sleep(1.5)
        
        sauvegarder_notified()
        
        embed.title = "✅ Envoi terminé"
        embed.description = ""
        embed.color = discord.Color.green()
        embed.add_field(name="📤 Envoyés", value=str(sent), inline=True)
        embed.add_field(name="❌ Échoués", value=str(failed), inline=True)
        
        await msg.edit(embed=embed)
    
    @commands.command(name="dm_reminder_clear")
    @commands.has_any_role(*ADMIN_ROLES)
    async def dm_reminder_clear(self, ctx):
        """Réinitialise la liste des utilisateurs notifiés."""
        global notified_users
        
        count = len(notified_users)
        notified_users = {}
        sauvegarder_notified()
        
        embed = discord.Embed(
            title="🗑️ Liste réinitialisée",
            description=f"La liste des {count} utilisateur(s) notifié(s) a été vidée.",
            color=discord.Color.orange()
        )
        await ctx.send(embed=embed)


async def setup(bot):
    """Setup pour discord.py 2.0+."""
    await bot.add_cog(DMReminder(bot))
    logging.info("✅ Cog DMReminder chargé avec succès")
