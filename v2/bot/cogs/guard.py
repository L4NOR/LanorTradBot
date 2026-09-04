"""
Garde — automod, anti-raid et anti-flood
==========================================
Trois protections, un seul module :

  1. **AutoMod** — supprime les liens d'invitation vers d'autres serveurs et
     les messages bourrés de mentions. Le staff est exempté.
  2. **Vague d'arrivées** — X arrivées en Y secondes → mode raid : alerte
     staff, verrouillage des salons publics, et expulsion des comptes trop
     récents tant que le mode est actif.
  3. **Anti-flood** — trop de messages, ou trop de doublons d'affilée →
     timeout automatique et nettoyage.

  /raid on|off|status  ·  /lockdown on|off
"""
import asyncio
import datetime
import logging
import re
import time
from collections import defaultdict, deque

import discord
from discord import app_commands
from discord.ext import commands

from bot.config import (
    GUILD_ID, CHANNELS, ROLES,
    COLOR_ERROR, COLOR_SUCCESS, COLOR_WARNING,
    AUTOMOD_ENABLED, AUTOMOD_BLOCK_INVITES, AUTOMOD_MAX_MENTIONS,
    AUTOMOD_DELETE_DELAY,
    RAID_ENABLED, RAID_JOIN_THRESHOLD, RAID_JOIN_WINDOW,
    RAID_AUTO_LOCKDOWN, RAID_LOCKDOWN_MIN,
    RAID_MIN_ACCOUNT_AGE_DAYS, RAID_KICK_NEW_ACCOUNTS,
    RAID_LOCK_CHANNELS, RAID_ALERT_ROLE,
    RAID_SPAM_MAX_MSG, RAID_SPAM_WINDOW, RAID_SPAM_DUPLICATES,
    RAID_SPAM_TIMEOUT_MIN,
)
from bot.embeds import brand_embed

log = logging.getLogger("lanortrad.guard")

GUILD = discord.Object(id=GUILD_ID) if GUILD_ID else None

# discord.gg/xxx · discordapp.com/invite/xxx · discord.com/invite/xxx
_INVITE_RE = re.compile(
    r"(?:https?://)?(?:www\.)?(?:discord(?:app)?\.com/invite|discord\.gg|discord\.me)/\S+",
    re.IGNORECASE,
)

DAY = 86400


class AutoMod(commands.Cog):
    """Filtre anti-spam léger."""

    def __init__(self, bot):
        self.bot = bot

    async def _log(self, message: discord.Message, reason: str):
        ch_id = CHANNELS.get("automod_logs")
        if not ch_id:
            return
        channel = message.guild.get_channel(ch_id)
        if channel is None:
            return
        embed = discord.Embed(
            title="🛡️ AutoMod",
            description=reason,
            color=COLOR_ERROR,
            timestamp=message.created_at,
        )
        embed.add_field(name="Membre", value=f"{message.author.mention} (`{message.author.id}`)", inline=False)
        embed.add_field(name="Salon", value=message.channel.mention, inline=False)
        content = message.content[:1000] if message.content else "*(vide)*"
        embed.add_field(name="Message", value=content, inline=False)
        try:
            await channel.send(embed=embed)
        except discord.HTTPException:
            pass

    def _is_exempt(self, message: discord.Message) -> bool:
        if message.author.bot or message.guild is None:
            return True
        if not isinstance(message.author, discord.Member):
            return True
        perms = message.author.guild_permissions
        # Staff/mods exemptés
        return perms.manage_messages or perms.administrator

    async def _punish(self, message: discord.Message, user_warning: str, log_reason: str):
        try:
            await message.delete()
        except discord.HTTPException:
            return
        await self._log(message, log_reason)
        try:
            await message.channel.send(
                f"{message.author.mention} {user_warning}",
                delete_after=AUTOMOD_DELETE_DELAY,
            )
        except discord.HTTPException:
            pass

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if not AUTOMOD_ENABLED or self._is_exempt(message):
            return

        # ─── Mentions de masse ───
        if AUTOMOD_MAX_MENTIONS > 0:
            mention_count = len(set(message.mentions)) + len(message.role_mentions)
            if mention_count > AUTOMOD_MAX_MENTIONS:
                await self._punish(
                    message,
                    "⚠️ trop de mentions d'un coup · too many mentions.",
                    f"Mentions de masse ({mention_count} mentions).",
                )
                return

        # ─── Liens d'invitation ───
        if AUTOMOD_BLOCK_INVITES and _INVITE_RE.search(message.content or ""):
            await self._punish(
                message,
                "⚠️ pas de pub pour d'autres serveurs ici · no server ads.",
                "Lien d'invitation Discord détecté.",
            )
            return


class Raid(commands.Cog):
    """Protection anti-raid et anti-flood."""

    def __init__(self, bot):
        self.bot = bot
        self.raid_mode = False
        self.locked = False
        self._joins = deque(maxlen=200)                       # timestamps d'arrivée
        self._msgs = defaultdict(lambda: deque(maxlen=30))    # user_id → timestamps
        self._last = {}                                       # user_id → (contenu, répétitions)
        self._unlock_task = None

    # ─────────────────────────────────────────────
    # Helpers
    # ─────────────────────────────────────────────
    def _alert_channel(self, guild):
        for key in ("staff_chat", "server_logs", "bot_logs"):
            ch_id = CHANNELS.get(key)
            if ch_id:
                ch = guild.get_channel(ch_id)
                if ch:
                    return ch
        return None

    async def _alert(self, guild, embed: discord.Embed, ping=True):
        channel = self._alert_channel(guild)
        if channel is None:
            log.warning("Alerte raid sans salon de destination : %s", embed.title)
            return
        content = None
        if ping and RAID_ALERT_ROLE:
            role_id = ROLES.get(RAID_ALERT_ROLE)
            if role_id:
                content = f"<@&{role_id}>"
        try:
            await channel.send(content=content, embed=embed,
                               allowed_mentions=discord.AllowedMentions(roles=True))
        except discord.HTTPException as e:
            log.warning("Alerte raid non envoyée : %s", e)

    @staticmethod
    def _is_exempt(member: discord.Member) -> bool:
        if not isinstance(member, discord.Member):
            return True
        perms = member.guild_permissions
        return perms.manage_messages or perms.administrator

    # ─────────────────────────────────────────────
    # Lockdown
    # ─────────────────────────────────────────────
    def _lockable_channels(self, guild):
        out = []
        for key in RAID_LOCK_CHANNELS:
            ch_id = CHANNELS.get(key)
            if not ch_id:
                continue
            ch = guild.get_channel(ch_id)
            if isinstance(ch, (discord.TextChannel, discord.ForumChannel)):
                out.append(ch)
        return out

    async def lockdown(self, guild, *, lock: bool, reason: str):
        """Verrouille/déverrouille les salons publics pour @everyone."""
        changed = 0
        for ch in self._lockable_channels(guild):
            ow = ch.overwrites_for(guild.default_role)
            ow.send_messages = False if lock else None
            ow.create_public_threads = False if lock else None
            ow.send_messages_in_threads = False if lock else None
            try:
                await ch.set_permissions(guild.default_role, overwrite=ow, reason=reason)
                changed += 1
                await asyncio.sleep(0.3)   # respecte le rate limit
            except discord.HTTPException as e:
                log.warning("Lockdown %s KO : %s", ch.name, e)
        self.locked = lock
        return changed

    async def _auto_unlock_later(self, guild, minutes: int):
        try:
            await asyncio.sleep(minutes * 60)
            if self.raid_mode:
                await self.set_raid_mode(guild, False, reason="fin automatique du lockdown")
        except asyncio.CancelledError:
            pass

    async def set_raid_mode(self, guild, active: bool, *, reason: str):
        if self.raid_mode == active:
            return
        self.raid_mode = active

        if active:
            if RAID_AUTO_LOCKDOWN:
                n = await self.lockdown(guild, lock=True, reason=f"Anti-raid : {reason}")
            else:
                n = 0
            embed = brand_embed(
                guild,
                title="🚨 MODE RAID ACTIVÉ",
                description=(
                    f"**Cause :** {reason}\n"
                    f"**Salons verrouillés :** {n}\n"
                    f"**Comptes de moins de {RAID_MIN_ACCOUNT_AGE_DAYS} j :** "
                    f"{'expulsés' if RAID_KICK_NEW_ACCOUNTS else 'signalés'}\n\n"
                    "Désactivation : `/raidmode etat:off`"
                ),
                color=COLOR_ERROR,
            )
            await self._alert(guild, embed)
            if RAID_LOCKDOWN_MIN > 0:
                if self._unlock_task:
                    self._unlock_task.cancel()
                self._unlock_task = asyncio.create_task(
                    self._auto_unlock_later(guild, RAID_LOCKDOWN_MIN))
        else:
            if self._unlock_task:
                self._unlock_task.cancel()
                self._unlock_task = None
            n = await self.lockdown(guild, lock=False, reason=f"Fin anti-raid : {reason}")
            embed = brand_embed(
                guild,
                title="✅ Mode raid désactivé",
                description=f"**Cause :** {reason}\n**Salons déverrouillés :** {n}",
                color=COLOR_SUCCESS,
            )
            await self._alert(guild, embed, ping=False)

    # ─────────────────────────────────────────────
    # 1) Détection de vague d'arrivées
    # ─────────────────────────────────────────────
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if not RAID_ENABLED:
            return

        now = time.time()
        self._joins.append(now)
        recent = [t for t in self._joins if now - t <= RAID_JOIN_WINDOW]

        if not self.raid_mode and len(recent) >= RAID_JOIN_THRESHOLD:
            await self.set_raid_mode(
                member.guild, True,
                reason=f"{len(recent)} arrivées en {RAID_JOIN_WINDOW} s",
            )

        if not self.raid_mode:
            return

        # Mode raid actif → filtre des comptes trop récents
        age_days = (discord.utils.utcnow() - member.created_at).days
        if age_days >= RAID_MIN_ACCOUNT_AGE_DAYS:
            return

        embed = brand_embed(
            member.guild,
            title="⚠️ Compte récent pendant un raid",
            description=(
                f"{member.mention} (`{member.id}`)\n"
                f"Compte créé il y a **{age_days} j** "
                f"(seuil : {RAID_MIN_ACCOUNT_AGE_DAYS} j)"
            ),
            color=COLOR_WARNING,
        )

        if not RAID_KICK_NEW_ACCOUNTS:
            await self._alert(member.guild, embed, ping=False)
            return

        try:
            await member.send(
                "🚨 Le serveur **LanorTrad** est en protection anti-raid.\n"
                "Ton compte est trop récent pour rejoindre maintenant — "
                "réessaie dans quelques heures. Désolé pour la gêne !"
            )
        except discord.HTTPException:
            pass
        try:
            await member.kick(reason="Anti-raid : compte trop récent")
            embed.description += "\n\n🔨 **Expulsé automatiquement.**"
        except discord.HTTPException as e:
            embed.description += f"\n\n❌ Expulsion impossible : {e}"
        await self._alert(member.guild, embed, ping=False)

    # ─────────────────────────────────────────────
    # 2) Anti-flood permanent
    # ─────────────────────────────────────────────
    async def _punish_flood(self, message: discord.Message, reason: str):
        member = message.author
        try:
            await message.delete()
        except discord.HTTPException:
            pass

        try:
            await member.timeout(
                datetime.timedelta(minutes=RAID_SPAM_TIMEOUT_MIN),
                reason=f"Anti-flood : {reason}",
            )
        except discord.HTTPException as e:
            log.warning("Timeout anti-flood KO pour %s : %s", member, e)

        try:
            await message.channel.send(
                f"🔇 {member.mention} a été mis en sourdine "
                f"{RAID_SPAM_TIMEOUT_MIN} min · *{reason}*",
                delete_after=10,
            )
        except discord.HTTPException:
            pass

        embed = brand_embed(
            message.guild,
            title="🛡️ Anti-flood",
            description=(
                f"{member.mention} (`{member.id}`)\n"
                f"**Motif :** {reason}\n"
                f"**Salon :** {message.channel.mention}\n"
                f"**Sanction :** timeout {RAID_SPAM_TIMEOUT_MIN} min"
            ),
            color=COLOR_ERROR,
        )
        ch_id = CHANNELS.get("automod_logs") or CHANNELS.get("bot_logs")
        if ch_id:
            ch = message.guild.get_channel(ch_id)
            if ch:
                try:
                    await ch.send(embed=embed)
                except discord.HTTPException:
                    pass

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if not RAID_ENABLED or message.guild is None or message.author.bot:
            return
        if self._is_exempt(message.author):
            return

        uid = message.author.id
        now = time.time()

        # ─── Débit de messages ───
        q = self._msgs[uid]
        q.append(now)
        recent = [t for t in q if now - t <= RAID_SPAM_WINDOW]
        if RAID_SPAM_MAX_MSG > 0 and len(recent) >= RAID_SPAM_MAX_MSG:
            q.clear()
            await self._punish_flood(
                message, f"{len(recent)} messages en {RAID_SPAM_WINDOW} s")
            return

        # ─── Messages identiques d'affilée ───
        if RAID_SPAM_DUPLICATES > 0 and message.content:
            prev, count = self._last.get(uid, (None, 0))
            if prev == message.content:
                count += 1
            else:
                count = 1
            self._last[uid] = (message.content, count)
            if count >= RAID_SPAM_DUPLICATES:
                self._last[uid] = (message.content, 0)
                await self._punish_flood(
                    message, f"{count} messages identiques d'affilée")

    # ─────────────────────────────────────────────
    # 3) Commandes staff
    # ─────────────────────────────────────────────
    @app_commands.command(name="raid",
                          description="(Staff) Active/désactive la protection anti-raid")
    @app_commands.describe(etat="on = lockdown + filtre comptes récents · off = retour à la normale")
    @app_commands.choices(etat=[
        app_commands.Choice(name="🚨 on — activer", value="on"),
        app_commands.Choice(name="✅ off — désactiver", value="off"),
        app_commands.Choice(name="ℹ️ status — état actuel", value="status"),
    ])
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.guilds(GUILD)
    async def raidmode(self, interaction: discord.Interaction,
                       etat: app_commands.Choice[str]):
        if etat.value == "status":
            embed = brand_embed(
                interaction.guild,
                title="🛡️ État de la protection",
                description=(
                    f"**Mode raid :** {'🚨 ACTIF' if self.raid_mode else '✅ inactif'}\n"
                    f"**Lockdown :** {'🔒 oui' if self.locked else '🔓 non'}\n"
                    f"**Seuil :** {RAID_JOIN_THRESHOLD} arrivées / {RAID_JOIN_WINDOW} s\n"
                    f"**Anti-flood :** {RAID_SPAM_MAX_MSG} msg / {RAID_SPAM_WINDOW} s "
                    f"· {RAID_SPAM_DUPLICATES} doublons"
                ),
                color=COLOR_ERROR if self.raid_mode else COLOR_SUCCESS,
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True, thinking=True)
        await self.set_raid_mode(
            interaction.guild, etat.value == "on",
            reason=f"commande manuelle de {interaction.user}",
        )
        await interaction.followup.send(
            f"✅ Mode raid **{'activé' if etat.value == 'on' else 'désactivé'}**.",
            ephemeral=True,
        )

    @app_commands.command(name="lockdown",
                          description="(Staff) Verrouille ou déverrouille les salons publics")
    @app_commands.describe(etat="on = verrouiller · off = déverrouiller")
    @app_commands.choices(etat=[
        app_commands.Choice(name="🔒 on — verrouiller", value="on"),
        app_commands.Choice(name="🔓 off — déverrouiller", value="off"),
    ])
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.guilds(GUILD)
    async def lockdown_cmd(self, interaction: discord.Interaction,
                           etat: app_commands.Choice[str]):
        await interaction.response.defer(ephemeral=True, thinking=True)
        lock = etat.value == "on"
        n = await self.lockdown(
            interaction.guild, lock=lock,
            reason=f"Lockdown manuel de {interaction.user}",
        )
        await interaction.followup.send(
            f"{'🔒' if lock else '🔓'} {n} salon(s) "
            f"{'verrouillés' if lock else 'déverrouillés'}.",
            ephemeral=True,
        )

async def setup(bot):
    await bot.add_cog(AutoMod(bot))
    await bot.add_cog(Raid(bot))
