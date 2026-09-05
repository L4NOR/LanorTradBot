"""
Logs serveur — traçabilité pour le staff
==========================================
  - server_logs  : arrivées · départs · bans · unbans
  - message_logs : messages supprimés · édités · purges

Les messages sont archivés dans un **SQLite local** (`bot/msgcache.py`),
donc le contenu reste consultable même pour un message posté avant le
dernier redémarrage du bot — ce que le cache RAM de Discord ne permet pas.
Rétention : MSG_CACHE_DAYS jours, purge automatique.

Chaque salon est optionnel : si l'ID vaut None dans bot_config, le log
correspondant est simplement ignoré (pas d'erreur).
"""
import datetime
import logging

import discord
from discord import app_commands
from discord.ext import commands, tasks

from bot.config import (
    GUILD_ID, CHANNELS,
    COLOR_SUCCESS, COLOR_ERROR, COLOR_NEUTRAL, COLOR_WARNING,
    MSG_CACHE_ENABLED, MSG_CACHE_DAYS, MSG_CACHE_MAX_LEN,
)
from bot.embeds import brand_embed
from bot.msgcache import MessageCache

log = logging.getLogger("lanortrad.logs")

GUILD = discord.Object(id=GUILD_ID) if GUILD_ID else None


def _utcnow():
    return datetime.datetime.now(datetime.timezone.utc)


class Logs(commands.Cog):
    """Journalisation des événements serveur."""

    def __init__(self, bot):
        self.bot = bot
        self.cache = MessageCache(MSG_CACHE_MAX_LEN) if MSG_CACHE_ENABLED else None
        if self.cache:
            self.purge_cache.start()

    def cog_unload(self):
        if self.purge_cache.is_running():
            self.purge_cache.cancel()
        if self.cache:
            self.cache.close()

    async def _send(self, guild, channel_key: str, embed: discord.Embed):
        ch_id = CHANNELS.get(channel_key)
        if not ch_id or guild is None:
            return
        channel = guild.get_channel(ch_id)
        if channel is None:
            return
        try:
            await channel.send(embed=embed)
        except discord.HTTPException as e:
            log.warning("Log dans %s impossible : %s", channel_key, e)

    # ─── Membres ───
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        embed = discord.Embed(
            description=f"📥 {member.mention} **a rejoint** le serveur.",
            color=COLOR_SUCCESS,
            timestamp=_utcnow(),
        )
        embed.set_author(name=str(member), icon_url=member.display_avatar.url)
        embed.add_field(
            name="Compte créé",
            value=f"<t:{int(member.created_at.timestamp())}:R>",
            inline=True,
        )
        embed.set_footer(text=f"ID {member.id} · {member.guild.member_count} membres")
        await self._send(member.guild, "server_logs", embed)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        roles = [r.mention for r in member.roles if r.name != "@everyone"]
        embed = discord.Embed(
            description=f"📤 **{member}** a quitté le serveur.",
            color=COLOR_NEUTRAL,
            timestamp=_utcnow(),
        )
        embed.set_author(name=str(member), icon_url=member.display_avatar.url)
        if roles:
            embed.add_field(name="Rôles", value=" ".join(roles[:20]), inline=False)
        embed.set_footer(text=f"ID {member.id}")
        await self._send(member.guild, "server_logs", embed)

    @commands.Cog.listener()
    async def on_member_ban(self, guild: discord.Guild, user: discord.User):
        embed = discord.Embed(
            description=f"🔨 **{user}** a été **banni·e**.",
            color=COLOR_ERROR,
            timestamp=_utcnow(),
        )
        embed.set_author(name=str(user), icon_url=user.display_avatar.url)
        embed.set_footer(text=f"ID {user.id}")
        await self._send(guild, "server_logs", embed)

    @commands.Cog.listener()
    async def on_member_unban(self, guild: discord.Guild, user: discord.User):
        embed = discord.Embed(
            description=f"♻️ **{user}** a été **débanni·e**.",
            color=COLOR_WARNING,
            timestamp=_utcnow(),
        )
        embed.set_author(name=str(user), icon_url=user.display_avatar.url)
        embed.set_footer(text=f"ID {user.id}")
        await self._send(guild, "server_logs", embed)

    # ─── Archivage des messages ───
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if self.cache and message.guild and not message.author.bot:
            self.cache.store(message)

    def _archived(self, message_id: int):
        return self.cache.get(message_id) if self.cache else None

    # ─── Messages supprimés / édités (événements bruts) ───
    @commands.Cog.listener()
    async def on_raw_message_delete(self, payload: discord.RawMessageDeleteEvent):
        if payload.guild_id is None:
            return
        guild = self.bot.get_guild(payload.guild_id)

        message = payload.cached_message
        archived = self._archived(payload.message_id)
        if message is None and archived is None:
            return                              # rien à montrer, on n'inonde pas les logs

        if message is not None:
            if message.author.bot:
                return
            author = f"{message.author.mention} (`{message.author.id}`)"
            content = message.content
            files = "\n".join(a.filename for a in message.attachments[:5])
            created = message.created_at
        else:
            author = f"<@{archived['author_id']}> (`{archived['author_id']}`)"
            content = archived["content"]
            files = archived["attachments"]
            created = datetime.datetime.fromtimestamp(
                archived["created_at"], datetime.timezone.utc)

        embed = discord.Embed(
            description=f"🗑️ Message de {author} supprimé dans <#{payload.channel_id}>",
            color=COLOR_ERROR,
            timestamp=_utcnow(),
        )
        embed.add_field(name="Contenu", value=(content or "*(vide)*")[:1024], inline=False)
        if files:
            embed.add_field(name="Pièces jointes", value=files[:1024], inline=False)
        embed.add_field(name="Posté", value=f"<t:{int(created.timestamp())}:R>", inline=True)
        embed.set_footer(
            text="depuis le cache local" if message is None else "depuis le cache mémoire")
        await self._send(guild, "message_logs", embed)

    @commands.Cog.listener()
    async def on_raw_message_edit(self, payload: discord.RawMessageUpdateEvent):
        if payload.guild_id is None:
            return
        data = payload.data or {}
        if data.get("author", {}).get("bot"):
            return

        after_content = data.get("content")
        if after_content is None:
            return                              # édition d'embed/épinglage : pas de texte

        before = payload.cached_message
        archived = self._archived(payload.message_id)
        before_content = before.content if before else (
            archived["content"] if archived else None)
        if before_content is None or before_content == after_content:
            return

        guild = self.bot.get_guild(payload.guild_id)
        author_id = (before.author.id if before
                     else (archived["author_id"] if archived
                           else data.get("author", {}).get("id")))
        jump = (f"https://discord.com/channels/{payload.guild_id}/"
                f"{payload.channel_id}/{payload.message_id}")

        embed = discord.Embed(
            description=(
                f"✏️ Message de <@{author_id}> édité dans <#{payload.channel_id}> · "
                f"[aller au message]({jump})"
            ),
            color=COLOR_WARNING,
            timestamp=_utcnow(),
        )
        embed.add_field(name="Avant", value=before_content[:1024] or "*(vide)*", inline=False)
        embed.add_field(name="Après", value=after_content[:1024] or "*(vide)*", inline=False)
        embed.set_footer(text=f"Auteur ID {author_id}")
        await self._send(guild, "message_logs", embed)

        # Le cache doit refléter la dernière version connue
        if self.cache and archived:
            self.cache.update_content(payload.message_id, after_content)

    @commands.Cog.listener()
    async def on_raw_bulk_message_delete(self, payload: discord.RawBulkMessageDeleteEvent):
        if payload.guild_id is None:
            return
        guild = self.bot.get_guild(payload.guild_id)
        embed = discord.Embed(
            description=(
                f"🧹 **{len(payload.message_ids)} messages** supprimés en masse "
                f"dans <#{payload.channel_id}>"
            ),
            color=COLOR_ERROR,
            timestamp=_utcnow(),
        )
        await self._send(guild, "message_logs", embed)

    # ─── Entretien du cache ───
    @tasks.loop(hours=24)
    async def purge_cache(self):
        if not self.cache:
            return
        removed = self.cache.purge(MSG_CACHE_DAYS)
        if removed:
            log.info("Cache messages : %d entrées purgées (> %d j).", removed, MSG_CACHE_DAYS)

    @purge_cache.before_loop
    async def _before_purge(self):
        await self.bot.wait_until_ready()

    @app_commands.command(name="logs",
                          description="(Staff) État du cache local des messages")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.guilds(GUILD)
    async def logs_stats(self, interaction: discord.Interaction):
        if not self.cache:
            await interaction.response.send_message(
                "❌ Cache désactivé (`MSG_CACHE_ENABLED = False`).", ephemeral=True)
            return
        stats = self.cache.stats()
        oldest = (f"<t:{stats['oldest']}:R>" if stats["oldest"] else "—")
        embed = brand_embed(
            interaction.guild,
            title="💾 Cache des messages",
            description=(
                f"**Messages archivés :** {stats['count']:,}\n".replace(",", " ")
                + f"**Plus ancien :** {oldest}\n"
                f"**Taille du fichier :** {stats['size'] / 1024:.0f} Ko\n"
                f"**Rétention :** {MSG_CACHE_DAYS} jours"
            ),
            color=COLOR_NEUTRAL,
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(Logs(bot))
