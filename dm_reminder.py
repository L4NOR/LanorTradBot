# dm_reminder.py
# Système de rappel DM pour les membres n'ayant pas réagi au message des rôles
import discord
from discord.ext import commands, tasks
from config import ADMIN_ROLES
from utils import load_json, save_json
import datetime
import asyncio
import pytz
import logging
import os

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

# Message auquel les membres doivent réagir
ROLE_MESSAGE_ID = 1465801132390482145

# Canal où se trouve le message (à définir - nécessaire pour fetch le message)
ROLE_CHANNEL_ID = None  # Sera auto-détecté ou peut être défini manuellement

# Fichier de stockage des utilisateurs déjà notifiés
DM_REMINDER_FILE = "data/dm_reminder_notified.json"
DM_REMINDER_META_FILE = "data/dm_reminder_meta.json"

# Fuseau horaire
TIMEZONE = pytz.timezone('Europe/Paris')

# Heure d'envoi des DMs (12h = midi)
SEND_HOUR = 12

os.makedirs("data", exist_ok=True)


# ═══════════════════════════════════════════════════════════════════════════════
# DONNÉES
# ═══════════════════════════════════════════════════════════════════════════════

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
    try:
        save_json(DM_REMINDER_FILE, notified_users)
        
        meta = {
            "last_saved": datetime.datetime.now(TIMEZONE).isoformat(),
            "notified_count": len(notified_users),
        }
        save_json(DM_REMINDER_META_FILE, meta)
        
        logging.info(f"✅ DM Reminder sauvegardé ({len(notified_users)} utilisateurs)")
    except Exception as e:
        logging.error(f"❌ Erreur sauvegarde DM Reminder: {e}")


# ═══════════════════════════════════════════════════════════════════════════════
# COG PRINCIPAL
# ═══════════════════════════════════════════════════════════════════════════════

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
        """Tâche planifiée pour envoyer les rappels DM à midi."""
        global last_dm_date
        
        now = datetime.datetime.now(TIMEZONE)
        current_date = now.date()
        
        # Vérifier si c'est l'heure (12h) et qu'on n'a pas déjà envoyé aujourd'hui
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
            logging.error("❌ Message des rôles introuvable - rappels DM annulés")
            return
        
        # Récupérer les utilisateurs ayant réagi
        reacted_users = await self.get_users_who_reacted(message)
        logging.info(f"✅ {len(reacted_users)} utilisateur(s) ont réagi au message")
        
        # Statistiques
        dm_sent = 0
        dm_failed = 0
        dm_skipped_reacted = 0
        dm_skipped_bot = 0
        
        # Parcourir tous les membres du serveur
        for member in guild.members:
            # Ignorer les bots
            if member.bot:
                dm_skipped_bot += 1
                continue
            
            # Ignorer ceux qui ont déjà réagi
            if member.id in reacted_users:
                # S'ils étaient dans notified_users, on les retire
                if str(member.id) in notified_users:
                    del notified_users[str(member.id)]
                dm_skipped_reacted += 1
                continue
            
            # Ignorer ceux déjà notifiés aujourd'hui
            user_data = notified_users.get(str(member.id), {})
            last_notified = user_data.get("last_notified")
            
            if last_notified:
                try:
                    last_date = datetime.datetime.fromisoformat(last_notified).date()
                    if last_date == current_date:
                        continue  # Déjà notifié aujourd'hui
                except:
                    pass
            
            # Envoyer le DM
            success = await self.send_dm_reminder(member)
            
            if success:
                dm_sent += 1
                notified_users[str(member.id)] = {
                    "last_notified": now.isoformat(),
                    "dm_count": user_data.get("dm_count", 0) + 1,
                    "username": member.name
                }
            else:
                dm_failed += 1
            
            # Petit délai pour éviter le rate limit
            await asyncio.sleep(1.5)
        
        # Sauvegarder
        sauvegarder_notified()
        
        # Log résumé
        logging.info(
            f"📊 Résumé DM Reminder:\n"
            f"   • DMs envoyés: {dm_sent}\n"
            f"   • DMs échoués: {dm_failed}\n"
            f"   • Ignorés (ont réagi): {dm_skipped_reacted}\n"
            f"   • Ignorés (bots): {dm_skipped_bot}"
        )
    
    @dm_reminder_task.before_loop
    async def before_dm_reminder_task(self):
        """Attend que le bot soit prêt."""
        await self.bot.wait_until_ready()
        logging.info("📬 Tâche DM Reminder prête")
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # ÉVÉNEMENT: Réaction ajoutée
    # ═══════════════════════════════════════════════════════════════════════════════
    
    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        """Retire l'utilisateur de la liste quand il réagit au message."""
        if payload.message_id != ROLE_MESSAGE_ID:
            return
        
        if payload.user_id == self.bot.user.id:
            return
        
        user_id_str = str(payload.user_id)
        
        if user_id_str in notified_users:
            del notified_users[user_id_str]
            sauvegarder_notified()
            logging.info(f"✅ {payload.user_id} a réagi - retiré de la liste des rappels DM")
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # COMMANDES ADMIN
    # ═══════════════════════════════════════════════════════════════════════════════
    
    @commands.command(name="dm_reminder_status")
    @commands.has_any_role(*ADMIN_ROLES)
    async def dm_reminder_status(self, ctx):
        """Affiche le statut du système de rappel DM."""
        global last_dm_date
        
        now = datetime.datetime.now(TIMEZONE)
        
        embed = discord.Embed(
            title="📬 Statut DM Reminder",
            color=discord.Color.blue(),
            timestamp=now
        )
        
        # Statut de la tâche
        task_status = "✅ Active" if self.dm_reminder_task.is_running() else "❌ Inactive"
        embed.add_field(name="🔄 Tâche", value=task_status, inline=True)
        
        # Prochain envoi
        if last_dm_date == now.date():
            next_send = "Demain à 12h00"
        elif now.hour < SEND_HOUR:
            next_send = f"Aujourd'hui à {SEND_HOUR}h00"
        else:
            next_send = "Demain à 12h00"
        embed.add_field(name="⏰ Prochain envoi", value=next_send, inline=True)
        
        # Dernier envoi
        last_send = last_dm_date.strftime("%d/%m/%Y") if last_dm_date else "Jamais"
        embed.add_field(name="📅 Dernier envoi", value=last_send, inline=True)
        
        # Message cible
        embed.add_field(
            name="📨 Message cible",
            value=f"`{ROLE_MESSAGE_ID}`",
            inline=True
        )
        
        # Utilisateurs notifiés
        embed.add_field(
            name="👥 Utilisateurs notifiés",
            value=f"{len(notified_users)} utilisateur(s)",
            inline=True
        )
        
        # Message trouvé ?
        message_status = "✅ Trouvé" if self.role_message else "❓ Non vérifié"
        embed.add_field(name="📄 Message", value=message_status, inline=True)
        
        embed.set_footer(text=f"Demandé par {ctx.author.name}")
        await ctx.send(embed=embed)
    
    @commands.command(name="dm_reminder_test")
    @commands.has_any_role(*ADMIN_ROLES)
    async def dm_reminder_test(self, ctx):
        """Teste l'envoi d'un rappel DM à l'utilisateur cible (608234789564186644)."""
        TEST_USER_ID = 608234789564186644
        
        embed = discord.Embed(
            title="🧪 Test DM Reminder",
            description=f"Envoi d'un DM test à <@{TEST_USER_ID}> en cours...",
            color=discord.Color.orange()
        )
        msg = await ctx.send(embed=embed)
        
        # Récupérer l'utilisateur cible
        member = ctx.guild.get_member(TEST_USER_ID)
        
        if not member:
            embed.description = f"❌ Utilisateur `{TEST_USER_ID}` introuvable sur ce serveur."
            embed.color = discord.Color.red()
            await msg.edit(embed=embed)
            return
        
        success = await self.send_dm_reminder(member)
        
        if success:
            embed.description = f"✅ DM de test envoyé à **{member.name}** avec succès !"
            embed.color = discord.Color.green()
        else:
            embed.description = f"❌ Échec de l'envoi du DM à **{member.name}** (DMs fermés ?)"
            embed.color = discord.Color.red()
        
        await msg.edit(embed=embed)
    
    @commands.command(name="dm_reminder_test_me")
    @commands.has_any_role(*ADMIN_ROLES)
    async def dm_reminder_test_me(self, ctx):
        """Teste l'envoi d'un rappel DM à soi-même."""
        embed = discord.Embed(
            title="🧪 Test DM Reminder (moi)",
            description="Envoi d'un DM test en cours...",
            color=discord.Color.orange()
        )
        msg = await ctx.send(embed=embed)
        
        success = await self.send_dm_reminder(ctx.author)
        
        if success:
            embed.description = "✅ DM de test envoyé avec succès !"
            embed.color = discord.Color.green()
        else:
            embed.description = "❌ Échec de l'envoi du DM (DMs fermés ?)"
            embed.color = discord.Color.red()
        
        await msg.edit(embed=embed)
    
    @commands.command(name="dm_reminder_check")
    @commands.has_any_role(*ADMIN_ROLES)
    async def dm_reminder_check(self, ctx):
        """Vérifie le message et compte les membres sans réaction."""
        embed = discord.Embed(
            title="🔍 Vérification DM Reminder",
            description="Analyse en cours...",
            color=discord.Color.orange()
        )
        msg = await ctx.send(embed=embed)
        
        # Récupérer le message
        message = await self.get_role_message(ctx.guild)
        
        if not message:
            embed.description = f"❌ Message `{ROLE_MESSAGE_ID}` introuvable sur ce serveur."
            embed.color = discord.Color.red()
            await msg.edit(embed=embed)
            return
        
        # Compter les réactions
        reacted_users = await self.get_users_who_reacted(message)
        
        # Compter les membres sans réaction
        members_without_reaction = 0
        for member in ctx.guild.members:
            if not member.bot and member.id not in reacted_users:
                members_without_reaction += 1
        
        embed.title = "📊 Rapport DM Reminder"
        embed.description = ""
        embed.color = discord.Color.green()
        
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
        
        # Lien vers le message
        if self.role_channel:
            link = f"https://discord.com/channels/{ctx.guild.id}/{self.role_channel.id}/{ROLE_MESSAGE_ID}"
            embed.add_field(
                name="🔗 Lien",
                value=f"[Voir le message]({link})",
                inline=True
            )
        
        await msg.edit(embed=embed)
    
    @commands.command(name="dm_reminder_force")
    @commands.has_any_role(*ADMIN_ROLES)
    async def dm_reminder_force(self, ctx, limit: int = 10):
        """Force l'envoi des rappels DM maintenant (avec limite).
        
        Usage: !dm_reminder_force [limite]
        Exemple: !dm_reminder_force 5  (envoie à max 5 personnes)
        """
        if limit < 1:
            limit = 1
        if limit > 50:
            limit = 50  # Limite de sécurité
        
        embed = discord.Embed(
            title="⚡ Envoi forcé des DM",
            description=f"Envoi en cours (limite: {limit})...",
            color=discord.Color.orange()
        )
        msg = await ctx.send(embed=embed)
        
        # Récupérer le message
        message = await self.get_role_message(ctx.guild)
        
        if not message:
            embed.description = f"❌ Message `{ROLE_MESSAGE_ID}` introuvable."
            embed.color = discord.Color.red()
            await msg.edit(embed=embed)
            return
        
        # Récupérer les utilisateurs ayant réagi
        reacted_users = await self.get_users_who_reacted(message)
        
        sent = 0
        failed = 0
        
        for member in ctx.guild.members:
            if sent >= limit:
                break
            
            if member.bot:
                continue
            
            if member.id in reacted_users:
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
    
    @commands.command(name="dm_reminder_list")
    @commands.has_any_role(*ADMIN_ROLES)
    async def dm_reminder_list(self, ctx):
        """Affiche la liste des utilisateurs notifiés."""
        if not notified_users:
            embed = discord.Embed(
                title="📋 Liste des notifiés",
                description="Aucun utilisateur n'a encore été notifié.",
                color=discord.Color.blue()
            )
            await ctx.send(embed=embed)
            return
        
        # Pagination
        items_per_page = 10
        users_list = list(notified_users.items())
        pages = []
        
        for i in range(0, len(users_list), items_per_page):
            page_users = users_list[i:i + items_per_page]
            
            embed = discord.Embed(
                title="📋 Utilisateurs notifiés",
                color=discord.Color.blue()
            )
            
            for user_id, data in page_users:
                username = data.get("username", "Inconnu")
                dm_count = data.get("dm_count", 1)
                last = data.get("last_notified", "N/A")
                
                try:
                    last_dt = datetime.datetime.fromisoformat(last)
                    last_str = last_dt.strftime("%d/%m/%Y %H:%M")
                except:
                    last_str = last
                
                embed.add_field(
                    name=f"👤 {username}",
                    value=f"ID: `{user_id}`\nDMs: {dm_count}\nDernier: {last_str}",
                    inline=True
                )
            
            embed.set_footer(
                text=f"Page {len(pages) + 1}/{(len(users_list) + items_per_page - 1) // items_per_page} • Total: {len(notified_users)}"
            )
            pages.append(embed)
        
        # Afficher la première page
        if len(pages) == 1:
            await ctx.send(embed=pages[0])
        else:
            current_page = 0
            message = await ctx.send(embed=pages[current_page])
            
            await message.add_reaction('⬅️')
            await message.add_reaction('➡️')
            
            def check(reaction, user):
                return user == ctx.author and str(reaction.emoji) in ['⬅️', '➡️'] and reaction.message.id == message.id
            
            while True:
                try:
                    reaction, user = await self.bot.wait_for('reaction_add', timeout=60.0, check=check)
                    
                    if str(reaction.emoji) == '⬅️' and current_page > 0:
                        current_page -= 1
                        await message.edit(embed=pages[current_page])
                    elif str(reaction.emoji) == '➡️' and current_page < len(pages) - 1:
                        current_page += 1
                        await message.edit(embed=pages[current_page])
                    
                    await message.remove_reaction(reaction, user)
                except asyncio.TimeoutError:
                    await message.clear_reactions()
                    break


# ═══════════════════════════════════════════════════════════════════════════════
# SETUP
# ═══════════════════════════════════════════════════════════════════════════════

async def setup(bot):
    """Setup pour discord.py 2.0+"""
    await bot.add_cog(DMReminder(bot))
    logging.info("✅ Cog DMReminder chargé avec succès")
