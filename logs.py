# logs.py
# ═══════════════════════════════════════════════════════════════════════════════
# SYSTÈME D'AUDIT / LOGS - Suivi des actions modération et serveur
# ═══════════════════════════════════════════════════════════════════════════════

import discord
from discord.ext import commands
import datetime
import logging

from config import ADMIN_ROLES, CHANNELS, COLORS

logger = logging.getLogger(__name__)


class AuditLog(commands.Cog):
    """Système de logs d'audit pour le serveur."""

    def __init__(self, bot):
        self.bot = bot
        logger.info("✅ Module AuditLog initialisé")

    # ─────────────────────────────────────────────────────────────────────────
    # HELPER
    # ─────────────────────────────────────────────────────────────────────────

    async def send_log(self, embed: discord.Embed):
        """Envoie un embed dans le canal de logs."""
        channel = self.bot.get_channel(CHANNELS.get("logs"))
        if channel:
            try:
                await channel.send(embed=embed)
            except Exception as e:
                logger.error(f"Erreur envoi log: {e}")
        else:
            logger.warning("Canal de logs introuvable")

    # ─────────────────────────────────────────────────────────────────────────
    # ÉVÉNEMENTS - MEMBRES
    # ─────────────────────────────────────────────────────────────────────────

    @commands.Cog.listener()
    async def on_member_join(self, member):
        """Log quand un membre rejoint le serveur."""
        account_age = (datetime.datetime.now(datetime.timezone.utc) - member.created_at).days

        embed = discord.Embed(
            title="📥 Membre rejoint",
            description=f"{member.mention} ({member.name})",
            color=COLORS["success"],
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="🆔 ID", value=str(member.id), inline=True)
        embed.add_field(name="📅 Compte créé", value=f"Il y a {account_age} jour(s)", inline=True)
        embed.add_field(
            name="👥 Membres",
            value=str(member.guild.member_count),
            inline=True
        )

        if account_age < 7:
            embed.add_field(
                name="⚠️ Attention",
                value="Compte récent (< 7 jours)",
                inline=False
            )

        embed.set_footer(text="Audit Log • Arrivée")
        await self.send_log(embed)

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        """Log quand un membre quitte/est kick du serveur."""
        embed = discord.Embed(
            title="📤 Membre parti",
            description=f"**{member.name}** ({member.mention})",
            color=COLORS["error"],
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="🆔 ID", value=str(member.id), inline=True)

        # Rôles qu'il avait
        roles = [r.mention for r in member.roles if r.name != "@everyone"][:10]
        if roles:
            embed.add_field(name="📋 Rôles", value=", ".join(roles), inline=False)

        # Vérifier si c'est un kick via audit log
        try:
            async for entry in member.guild.audit_logs(limit=5, action=discord.AuditLogAction.kick):
                if entry.target.id == member.id:
                    time_diff = (datetime.datetime.now(datetime.timezone.utc) - entry.created_at).total_seconds()
                    if time_diff < 10:
                        embed.title = "🦶 Membre kick"
                        embed.add_field(name="👮 Kick par", value=entry.user.mention, inline=True)
                        if entry.reason:
                            embed.add_field(name="📝 Raison", value=entry.reason, inline=False)
                        break
        except discord.Forbidden:
            pass

        embed.add_field(name="👥 Membres restants", value=str(member.guild.member_count), inline=True)
        embed.set_footer(text="Audit Log • Départ")
        await self.send_log(embed)

    @commands.Cog.listener()
    async def on_member_ban(self, guild, user):
        """Log quand un membre est banni."""
        embed = discord.Embed(
            title="🔨 Membre banni",
            description=f"**{user.name}** ({user.mention})",
            color=0x8B0000,
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )
        embed.set_thumbnail(url=user.display_avatar.url)
        embed.add_field(name="🆔 ID", value=str(user.id), inline=True)

        # Chercher qui a banni
        try:
            async for entry in guild.audit_logs(limit=5, action=discord.AuditLogAction.ban):
                if entry.target.id == user.id:
                    embed.add_field(name="👮 Banni par", value=entry.user.mention, inline=True)
                    if entry.reason:
                        embed.add_field(name="📝 Raison", value=entry.reason, inline=False)
                    break
        except discord.Forbidden:
            pass

        embed.set_footer(text="Audit Log • Ban")
        await self.send_log(embed)

    @commands.Cog.listener()
    async def on_member_unban(self, guild, user):
        """Log quand un membre est débanni."""
        embed = discord.Embed(
            title="🔓 Membre débanni",
            description=f"**{user.name}** ({user.mention})",
            color=COLORS["success"],
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )
        embed.add_field(name="🆔 ID", value=str(user.id), inline=True)

        try:
            async for entry in guild.audit_logs(limit=5, action=discord.AuditLogAction.unban):
                if entry.target.id == user.id:
                    embed.add_field(name="👮 Débanni par", value=entry.user.mention, inline=True)
                    break
        except discord.Forbidden:
            pass

        embed.set_footer(text="Audit Log • Unban")
        await self.send_log(embed)

    # ─────────────────────────────────────────────────────────────────────────
    # ÉVÉNEMENTS - RÔLES
    # ─────────────────────────────────────────────────────────────────────────

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        """Log les changements de rôles."""
        if before.roles == after.roles:
            return

        added = [r for r in after.roles if r not in before.roles]
        removed = [r for r in before.roles if r not in after.roles]

        if not added and not removed:
            return

        embed = discord.Embed(
            title="🏷️ Changement de rôles",
            description=f"**{after.name}** ({after.mention})",
            color=COLORS["info"],
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )
        embed.set_thumbnail(url=after.display_avatar.url)

        if added:
            embed.add_field(
                name="➕ Rôle(s) ajouté(s)",
                value=", ".join([r.mention for r in added]),
                inline=False
            )
        if removed:
            embed.add_field(
                name="➖ Rôle(s) retiré(s)",
                value=", ".join([r.mention for r in removed]),
                inline=False
            )

        # Chercher qui a modifié
        try:
            async for entry in after.guild.audit_logs(limit=5, action=discord.AuditLogAction.member_role_update):
                if entry.target.id == after.id:
                    time_diff = (datetime.datetime.now(datetime.timezone.utc) - entry.created_at).total_seconds()
                    if time_diff < 10:
                        embed.add_field(name="👮 Par", value=entry.user.mention, inline=True)
                        break
        except discord.Forbidden:
            pass

        embed.set_footer(text="Audit Log • Rôles")
        await self.send_log(embed)

    # ─────────────────────────────────────────────────────────────────────────
    # ÉVÉNEMENTS - MESSAGES
    # ─────────────────────────────────────────────────────────────────────────

    @commands.Cog.listener()
    async def on_message_delete(self, message):
        """Log les messages supprimés."""
        if message.author.bot:
            return

        content = message.content[:200] if message.content else "*[Pas de texte]*"
        if len(message.content) > 200:
            content += "..."

        embed = discord.Embed(
            title="🗑️ Message supprimé",
            color=COLORS["warning"],
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )
        embed.add_field(name="👤 Auteur", value=f"{message.author.mention} ({message.author.name})", inline=True)
        embed.add_field(name="📌 Canal", value=message.channel.mention, inline=True)
        embed.add_field(name="📝 Contenu", value=content, inline=False)

        if message.attachments:
            files = "\n".join([f"• `{a.filename}`" for a in message.attachments[:5]])
            embed.add_field(name="📎 Pièces jointes", value=files, inline=False)

        embed.set_footer(text=f"Audit Log • Message ID: {message.id}")
        await self.send_log(embed)

    @commands.Cog.listener()
    async def on_bulk_message_delete(self, messages):
        """Log les suppressions en masse."""
        if not messages:
            return

        channel = messages[0].channel

        embed = discord.Embed(
            title="🗑️ Suppression en masse",
            description=f"**{len(messages)}** message(s) supprimé(s)",
            color=COLORS["error"],
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )
        embed.add_field(name="📌 Canal", value=channel.mention, inline=True)

        # Compter les auteurs uniques
        authors = set(m.author.name for m in messages if m.author)
        embed.add_field(name="👤 Auteurs", value=", ".join(list(authors)[:5]), inline=True)

        embed.set_footer(text="Audit Log • Purge")
        await self.send_log(embed)

    # ─────────────────────────────────────────────────────────────────────────
    # ÉVÉNEMENTS - CANAUX
    # ─────────────────────────────────────────────────────────────────────────

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel):
        """Log la création de canaux."""
        embed = discord.Embed(
            title="📁 Canal créé",
            description=f"**{channel.name}** ({channel.mention})",
            color=COLORS["success"],
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )
        embed.add_field(name="📂 Type", value=str(channel.type), inline=True)
        if hasattr(channel, 'category') and channel.category:
            embed.add_field(name="📁 Catégorie", value=channel.category.name, inline=True)

        try:
            async for entry in channel.guild.audit_logs(limit=3, action=discord.AuditLogAction.channel_create):
                if entry.target.id == channel.id:
                    embed.add_field(name="👮 Par", value=entry.user.mention, inline=True)
                    break
        except discord.Forbidden:
            pass

        embed.set_footer(text="Audit Log • Canal")
        await self.send_log(embed)

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):
        """Log la suppression de canaux."""
        embed = discord.Embed(
            title="📁 Canal supprimé",
            description=f"**{channel.name}**",
            color=COLORS["error"],
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )
        embed.add_field(name="📂 Type", value=str(channel.type), inline=True)
        if hasattr(channel, 'category') and channel.category:
            embed.add_field(name="📁 Catégorie", value=channel.category.name, inline=True)

        try:
            async for entry in channel.guild.audit_logs(limit=3, action=discord.AuditLogAction.channel_delete):
                if entry.target.id == channel.id:
                    embed.add_field(name="👮 Par", value=entry.user.mention, inline=True)
                    break
        except discord.Forbidden:
            pass

        embed.set_footer(text="Audit Log • Canal")
        await self.send_log(embed)

    # ─────────────────────────────────────────────────────────────────────────
    # ÉVÉNEMENTS - VOCAL
    # ─────────────────────────────────────────────────────────────────────────

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        """Log les mouvements vocaux."""
        if member.bot:
            return

        # Rejoindre un vocal
        if before.channel is None and after.channel is not None:
            embed = discord.Embed(
                title="🎤 Rejoint un vocal",
                description=f"{member.mention} a rejoint **{after.channel.name}**",
                color=COLORS["success"],
                timestamp=datetime.datetime.now(datetime.timezone.utc)
            )
            embed.set_footer(text="Audit Log • Vocal")
            await self.send_log(embed)

        # Quitter un vocal
        elif before.channel is not None and after.channel is None:
            embed = discord.Embed(
                title="🎤 Quitté un vocal",
                description=f"{member.mention} a quitté **{before.channel.name}**",
                color=COLORS["warning"],
                timestamp=datetime.datetime.now(datetime.timezone.utc)
            )
            embed.set_footer(text="Audit Log • Vocal")
            await self.send_log(embed)

        # Changer de vocal
        elif before.channel != after.channel and before.channel and after.channel:
            embed = discord.Embed(
                title="🎤 Changement de vocal",
                description=f"{member.mention}\n**{before.channel.name}** → **{after.channel.name}**",
                color=COLORS["info"],
                timestamp=datetime.datetime.now(datetime.timezone.utc)
            )
            embed.set_footer(text="Audit Log • Vocal")
            await self.send_log(embed)

    # ─────────────────────────────────────────────────────────────────────────
    # COMMANDE - CONFIGURER LE CANAL DE LOGS
    # ─────────────────────────────────────────────────────────────────────────

    @commands.command(name="set_logs")
    @commands.has_any_role(*ADMIN_ROLES)
    async def set_logs(self, ctx, channel: discord.TextChannel = None):
        """Définit le canal de logs actuel comme canal d'audit."""
        channel = channel or ctx.channel
        embed = discord.Embed(
            title="✅ Canal de logs configuré",
            description=f"Les logs d'audit seront envoyés dans {channel.mention}",
            color=COLORS["success"]
        )
        embed.set_footer(text=f"ID: {channel.id}")
        await ctx.send(embed=embed)
        logger.info(f"Canal de logs configuré: {channel.name} ({channel.id})")

    @commands.command(name="audit_test")
    @commands.has_any_role(*ADMIN_ROLES)
    async def audit_test(self, ctx):
        """Envoie un message test dans les logs d'audit."""
        embed = discord.Embed(
            title="🧪 Test Audit Log",
            description=f"Message de test envoyé par {ctx.author.mention}",
            color=COLORS["info"],
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )
        embed.set_footer(text="Audit Log • Test")
        await self.send_log(embed)
        await ctx.send("✅ Message test envoyé dans le canal de logs !")


async def setup(bot):
    """Setup pour discord.py 2.0+"""
    await bot.add_cog(AuditLog(bot))
    logging.info("✅ Cog AuditLog chargé avec succès")
