"""
Modération — /clear · /slowmode · /lock · /unlock · /timeout · /kick · /ban
============================================================================
Chaque action :
  - vérifie la hiérarchie (le bot ne peut pas viser plus haut que lui)
  - répond proprement en ephemeral
  - log l'action dans le salon bot-logs si configuré
"""
import datetime
import logging

import discord
from discord import app_commands
from discord.ext import commands

from bot.config import (
    GUILD_ID, CHANNELS, COLOR_SUCCESS, COLOR_ERROR, COLOR_WARNING,
)

log = logging.getLogger("lanortrad.moderation")

GUILD = discord.Object(id=GUILD_ID) if GUILD_ID else None


async def mod_log(bot, guild, *, action: str, moderator, target=None, reason=None, extra=None):
    """Envoie un embed d'action de modération dans bot-logs (si configuré)."""
    ch_id = CHANNELS.get("bot_logs")
    if not ch_id:
        return
    channel = guild.get_channel(ch_id)
    if channel is None:
        return

    embed = discord.Embed(
        title=f"🛠️ {action}",
        color=COLOR_WARNING,
        timestamp=datetime.datetime.now(datetime.timezone.utc),
    )
    embed.add_field(name="Modérateur", value=f"{moderator.mention} (`{moderator.id}`)", inline=False)
    if target is not None:
        tgt = f"{target.mention} (`{target.id}`)" if hasattr(target, "mention") else str(target)
        embed.add_field(name="Cible", value=tgt, inline=False)
    if reason:
        embed.add_field(name="Raison", value=reason, inline=False)
    if extra:
        embed.add_field(name="Détails", value=extra, inline=False)
    try:
        await channel.send(embed=embed)
    except discord.HTTPException:
        pass


def _can_act_on(interaction: discord.Interaction, member: discord.Member) -> str | None:
    """Renvoie un message d'erreur si l'action est interdite, sinon None."""
    if member == interaction.user:
        return "❌ Tu ne peux pas te cibler toi-même."
    if member == interaction.guild.me:
        return "❌ Je ne peux pas me cibler moi-même."
    if member.id == interaction.guild.owner_id:
        return "❌ Impossible de cibler le propriétaire du serveur."
    # Hiérarchie du modérateur (sauf owner)
    if (interaction.user.id != interaction.guild.owner_id
            and member.top_role >= interaction.user.top_role):
        return "❌ Cette personne a un rôle supérieur ou égal au tien."
    # Hiérarchie du bot
    if member.top_role >= interaction.guild.me.top_role:
        return "❌ Cette personne est au-dessus de moi dans la hiérarchie des rôles."
    return None


class Moderation(commands.Cog):
    """Commandes de modération."""

    def __init__(self, bot):
        self.bot = bot

    # ─── /clear ───
    @app_commands.command(name="clear", description="(Mod) Supprime les N derniers messages")
    @app_commands.describe(amount="Nombre de messages à supprimer (1-100)")
    @app_commands.default_permissions(manage_messages=True)
    @app_commands.checks.bot_has_permissions(manage_messages=True)
    @app_commands.guilds(GUILD)
    async def clear(self, interaction: discord.Interaction, amount: int):
        amount = max(1, min(amount, 100))
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            deleted = await interaction.channel.purge(limit=amount)
        except discord.Forbidden:
            await interaction.followup.send("❌ Permission manquante pour purger ici.", ephemeral=True)
            return
        await interaction.followup.send(f"🧹 **{len(deleted)}** message(s) supprimé(s).", ephemeral=True)
        await mod_log(
            self.bot, interaction.guild, action="Purge de messages",
            moderator=interaction.user,
            extra=f"{len(deleted)} message(s) dans {interaction.channel.mention}",
        )

    # ─── /slowmode ───
    @app_commands.command(name="lent", description="(Mod) Définit le mode lent du salon")
    @app_commands.describe(seconds="Délai en secondes (0 = désactivé, max 21600)")
    @app_commands.default_permissions(manage_channels=True)
    @app_commands.checks.bot_has_permissions(manage_channels=True)
    @app_commands.guilds(GUILD)
    async def slowmode(self, interaction: discord.Interaction, seconds: int):
        seconds = max(0, min(seconds, 21600))
        try:
            await interaction.channel.edit(slowmode_delay=seconds)
        except discord.Forbidden:
            await interaction.response.send_message("❌ Permission manquante.", ephemeral=True)
            return
        txt = "désactivé" if seconds == 0 else f"**{seconds}s**"
        await interaction.response.send_message(f"🐌 Mode lent {txt}.", ephemeral=True)

    # ─── /lock ───
    @app_commands.command(name="verrou", description="(Mod) Verrouille le salon (everyone ne peut plus écrire)")
    @app_commands.default_permissions(manage_channels=True)
    @app_commands.checks.bot_has_permissions(manage_roles=True)
    @app_commands.guilds(GUILD)
    async def lock(self, interaction: discord.Interaction):
        everyone = interaction.guild.default_role
        ow = interaction.channel.overwrites_for(everyone)
        ow.send_messages = False
        try:
            await interaction.channel.set_permissions(everyone, overwrite=ow, reason=f"Lock par {interaction.user}")
        except discord.Forbidden:
            await interaction.response.send_message("❌ Permission manquante.", ephemeral=True)
            return
        await interaction.response.send_message("🔒 Salon verrouillé.")
        await mod_log(self.bot, interaction.guild, action="Salon verrouillé",
                      moderator=interaction.user, extra=interaction.channel.mention)

    # ─── /unlock ───
    @app_commands.command(name="deverrou", description="(Mod) Déverrouille le salon")
    @app_commands.default_permissions(manage_channels=True)
    @app_commands.checks.bot_has_permissions(manage_roles=True)
    @app_commands.guilds(GUILD)
    async def unlock(self, interaction: discord.Interaction):
        everyone = interaction.guild.default_role
        ow = interaction.channel.overwrites_for(everyone)
        ow.send_messages = None  # retour à la valeur héritée
        try:
            await interaction.channel.set_permissions(everyone, overwrite=ow, reason=f"Unlock par {interaction.user}")
        except discord.Forbidden:
            await interaction.response.send_message("❌ Permission manquante.", ephemeral=True)
            return
        await interaction.response.send_message("🔓 Salon déverrouillé.")
        await mod_log(self.bot, interaction.guild, action="Salon déverrouillé",
                      moderator=interaction.user, extra=interaction.channel.mention)

    # ─── /timeout ───
    @app_commands.command(name="timeout", description="(Mod) Exclut temporairement un membre")
    @app_commands.describe(
        member="Le membre à exclure",
        minutes="Durée en minutes (1-40320 = 28j)",
        reason="Raison (optionnel)",
    )
    @app_commands.default_permissions(moderate_members=True)
    @app_commands.checks.bot_has_permissions(moderate_members=True)
    @app_commands.guilds(GUILD)
    async def timeout(self, interaction: discord.Interaction, member: discord.Member,
                      minutes: int, reason: str = None):
        err = _can_act_on(interaction, member)
        if err:
            await interaction.response.send_message(err, ephemeral=True)
            return
        minutes = max(1, min(minutes, 40320))
        until = datetime.timedelta(minutes=minutes)
        try:
            await member.timeout(until, reason=reason or f"Par {interaction.user}")
        except discord.Forbidden:
            await interaction.response.send_message("❌ Je ne peux pas exclure ce membre.", ephemeral=True)
            return
        await interaction.response.send_message(
            f"⏳ {member.mention} exclu·e pour **{minutes} min**.", ephemeral=True
        )
        await mod_log(self.bot, interaction.guild, action="Timeout",
                      moderator=interaction.user, target=member,
                      reason=reason, extra=f"{minutes} minutes")

    # ─── /kick ───
    @app_commands.command(name="kick", description="(Mod) Expulse un membre")
    @app_commands.describe(member="Le membre à expulser", reason="Raison (optionnel)")
    @app_commands.default_permissions(kick_members=True)
    @app_commands.checks.bot_has_permissions(kick_members=True)
    @app_commands.guilds(GUILD)
    async def kick(self, interaction: discord.Interaction, member: discord.Member, reason: str = None):
        err = _can_act_on(interaction, member)
        if err:
            await interaction.response.send_message(err, ephemeral=True)
            return
        try:
            await member.kick(reason=reason or f"Par {interaction.user}")
        except discord.Forbidden:
            await interaction.response.send_message("❌ Je ne peux pas expulser ce membre.", ephemeral=True)
            return
        await interaction.response.send_message(f"👢 {member} expulsé·e.", ephemeral=True)
        await mod_log(self.bot, interaction.guild, action="Kick",
                      moderator=interaction.user, target=member, reason=reason)

    # ─── /ban ───
    @app_commands.command(name="ban", description="(Mod) Bannit un membre")
    @app_commands.describe(
        member="Le membre à bannir",
        reason="Raison (optionnel)",
        delete_days="Jours de messages à supprimer (0-7, défaut 0)",
    )
    @app_commands.default_permissions(ban_members=True)
    @app_commands.checks.bot_has_permissions(ban_members=True)
    @app_commands.guilds(GUILD)
    async def ban(self, interaction: discord.Interaction, member: discord.Member,
                  reason: str = None, delete_days: int = 0):
        err = _can_act_on(interaction, member)
        if err:
            await interaction.response.send_message(err, ephemeral=True)
            return
        delete_days = max(0, min(delete_days, 7))
        try:
            await member.ban(
                reason=reason or f"Par {interaction.user}",
                delete_message_days=delete_days,
            )
        except discord.Forbidden:
            await interaction.response.send_message("❌ Je ne peux pas bannir ce membre.", ephemeral=True)
            return
        await interaction.response.send_message(f"🔨 {member} banni·e.", ephemeral=True)
        await mod_log(self.bot, interaction.guild, action="Ban",
                      moderator=interaction.user, target=member, reason=reason)


async def setup(bot):
    await bot.add_cog(Moderation(bot))
