"""
Avertissements — /warn · /warnings · /delwarn · /clearwarns
=============================================================
Historique persistant dans data/warns.json :
    { "<user_id>": [ {"mod": id, "reason": str, "ts": int}, ... ] }

Complète la modération (kick/ban/timeout) avec une trace écrite.
"""
import datetime
import logging
import time

import discord
from discord import app_commands
from discord.ext import commands

from bot.config import (
    GUILD_ID, CHANNELS, WARN_DM_USER,
    COLOR_WARNING, COLOR_SUCCESS, COLOR_NEUTRAL,
)
from bot.embeds import brand_embed
from bot.storage import JSONStore

log = logging.getLogger("lanortrad.warns")

GUILD = discord.Object(id=GUILD_ID) if GUILD_ID else None


class Warns(commands.Cog):
    """Système d'avertissements."""

    def __init__(self, bot):
        self.bot = bot
        self._store = JSONStore("warns.json", default={})

    def _warns_for(self, user_id: int) -> list:
        return self._store.get(str(user_id), [])

    async def _modlog(self, guild, embed: discord.Embed):
        ch_id = CHANNELS.get("bot_logs")
        if not ch_id:
            return
        channel = guild.get_channel(ch_id)
        if channel:
            try:
                await channel.send(embed=embed)
            except discord.HTTPException:
                pass

    # ─── /warn ───
    @app_commands.command(name="warn", description="(Mod) Avertit un membre")
    @app_commands.describe(member="Le membre à avertir", reason="Raison de l'avertissement")
    @app_commands.default_permissions(manage_messages=True)
    @app_commands.guilds(GUILD)
    async def warn(self, interaction: discord.Interaction, member: discord.Member, reason: str):
        if member.bot:
            await interaction.response.send_message("❌ On n'avertit pas un bot.", ephemeral=True)
            return
        if member == interaction.user:
            await interaction.response.send_message("❌ Tu ne peux pas t'auto-avertir.", ephemeral=True)
            return
        if (interaction.user.id != interaction.guild.owner_id
                and member.top_role >= interaction.user.top_role):
            await interaction.response.send_message(
                "❌ Ce membre a un rôle supérieur ou égal au tien.", ephemeral=True)
            return

        entry = {"mod": interaction.user.id, "reason": reason, "ts": int(time.time())}
        warns = self._store.setdefault(str(member.id), [])
        warns.append(entry)
        self._store.save()
        total = len(warns)

        # DM best-effort
        dm_ok = False
        if WARN_DM_USER:
            try:
                dm = brand_embed(
                    interaction.guild,
                    title="⚠️ Avertissement reçu",
                    description=(
                        f"Tu as reçu un avertissement sur **{interaction.guild.name}**.\n\n"
                        f"**Raison :** {reason}\n"
                        f"**Total :** {total} avertissement(s)"
                    ),
                    color=COLOR_WARNING,
                )
                await member.send(embed=dm)
                dm_ok = True
            except (discord.Forbidden, discord.HTTPException):
                pass

        await interaction.response.send_message(
            f"⚠️ {member.mention} averti·e (**{total}** au total)."
            + ("" if dm_ok else " *(DM impossible)*"),
            ephemeral=True,
        )

        embed = brand_embed(interaction.guild, title="⚠️ Avertissement", color=COLOR_WARNING)
        embed.add_field(name="Membre", value=f"{member.mention} (`{member.id}`)", inline=False)
        embed.add_field(name="Modérateur", value=interaction.user.mention, inline=True)
        embed.add_field(name="Total", value=str(total), inline=True)
        embed.add_field(name="Raison", value=reason, inline=False)
        await self._modlog(interaction.guild, embed)
        log.info("Warn %s par %s : %s", member, interaction.user, reason)

    # ─── /warnings ───
    @app_commands.command(name="warns", description="(Mod) Liste les avertissements d'un membre")
    @app_commands.describe(member="Le membre à consulter")
    @app_commands.default_permissions(manage_messages=True)
    @app_commands.guilds(GUILD)
    async def warnings(self, interaction: discord.Interaction, member: discord.Member):
        warns = self._warns_for(member.id)
        if not warns:
            await interaction.response.send_message(
                f"✅ {member.mention} n'a aucun avertissement.", ephemeral=True)
            return

        embed = brand_embed(
            interaction.guild,
            title=f"⚠️ Avertissements · {member.display_name}",
            description=f"**{len(warns)}** avertissement(s) au total.",
            color=COLOR_WARNING,
        )
        for i, w in enumerate(warns[-15:], start=max(1, len(warns) - 14)):
            mod = interaction.guild.get_member(w.get("mod"))
            mod_txt = mod.mention if mod else f"`{w.get('mod')}`"
            ts = w.get("ts")
            when = f"<t:{ts}:R>" if ts else ""
            embed.add_field(
                name=f"#{i} · {when}",
                value=f"{w.get('reason', '—')}\n— par {mod_txt}",
                inline=False,
            )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # ─── /delwarn ───
    @app_commands.command(name="delwarn", description="(Mod) Supprime un avertissement précis")
    @app_commands.describe(member="Le membre", index="Numéro de l'avertissement (cf. /warnings)")
    @app_commands.default_permissions(manage_messages=True)
    @app_commands.guilds(GUILD)
    async def delwarn(self, interaction: discord.Interaction, member: discord.Member, index: int):
        warns = self._warns_for(member.id)
        if not warns:
            await interaction.response.send_message(
                f"✅ {member.mention} n'a aucun avertissement.", ephemeral=True)
            return
        if index < 1 or index > len(warns):
            await interaction.response.send_message(
                f"❌ Numéro invalide (1-{len(warns)}).", ephemeral=True)
            return
        removed = warns.pop(index - 1)
        if warns:
            self._store[str(member.id)] = warns
        else:
            self._store.pop(str(member.id), None)
        self._store.save()
        await interaction.response.send_message(
            f"🗑️ Avertissement #{index} de {member.mention} supprimé "
            f"(*{removed.get('reason', '—')}*).",
            ephemeral=True,
        )

    # ─── /clearwarns ───
    @app_commands.command(name="clearwarns", description="(Mod) Efface TOUS les avertissements d'un membre")
    @app_commands.describe(member="Le membre")
    @app_commands.default_permissions(manage_messages=True)
    @app_commands.guilds(GUILD)
    async def clearwarns(self, interaction: discord.Interaction, member: discord.Member):
        if str(member.id) not in self._store:
            await interaction.response.send_message(
                f"✅ {member.mention} n'a aucun avertissement.", ephemeral=True)
            return
        count = len(self._warns_for(member.id))
        self._store.pop(str(member.id), None)
        self._store.save()
        await interaction.response.send_message(
            f"🧹 {count} avertissement(s) effacé(s) pour {member.mention}.", ephemeral=True)
        embed = brand_embed(interaction.guild, title="🧹 Avertissements effacés", color=COLOR_SUCCESS)
        embed.add_field(name="Membre", value=f"{member.mention} (`{member.id}`)", inline=False)
        embed.add_field(name="Par", value=interaction.user.mention, inline=True)
        await self._modlog(interaction.guild, embed)


async def setup(bot):
    await bot.add_cog(Warns(bot))
