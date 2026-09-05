"""
Sauvegarde de la structure du serveur
=======================================
Exporte rôles, catégories, salons, permissions et tags de forum dans un
fichier JSON horodaté. Sert à :

  • repartir vite après un incident (suppression accidentelle, compte compromis)
  • comparer l'état actuel à un état connu (`/backup diff`)
  • archiver la configuration avant un gros changement

  /backup creer   — crée une sauvegarde maintenant
  /backup liste   — liste les sauvegardes disponibles
  /backup obtenir — renvoie le fichier JSON d'une sauvegarde
  /backup diff    — compare le serveur à la dernière sauvegarde

Une sauvegarde automatique est faite chaque semaine.
⚠️ La restauration n'est PAS automatique (trop destructif) : le JSON sert de
référence, et `reset_rebuild.py` reste l'outil de reconstruction.
"""
import datetime
import glob
import json
import logging
import os
import time

import discord
from discord import app_commands
from discord.ext import commands, tasks

from bot.config import (
    GUILD_ID, CHANNELS, COLOR_NEUTRAL, COLOR_SUCCESS, BACKUP_KEEP,
    BACKUP_CHANNEL_ID, BACKUP_MIN_DAYS,
)
from bot.embeds import brand_embed
from bot.storage import JSONStore

log = logging.getLogger("lanortrad.backup")

GUILD = discord.Object(id=GUILD_ID) if GUILD_ID else None

BACKUP_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "backups")


def _overwrites(channel) -> dict:
    out = {}
    for target, perms in channel.overwrites.items():
        allow, deny = perms.pair()
        out[f"{'role' if isinstance(target, discord.Role) else 'member'}:{target.name}"] = {
            "allow": allow.value, "deny": deny.value,
        }
    return out


def snapshot(guild: discord.Guild) -> dict:
    """Photographie complète de la structure (aucun message, aucune donnée membre)."""
    data = {
        "guild": {
            "id": guild.id,
            "name": guild.name,
            "description": guild.description,
            "verification_level": str(guild.verification_level),
            "member_count": guild.member_count,
            "premium_tier": guild.premium_tier,
        },
        "taken_at": int(datetime.datetime.now(datetime.timezone.utc).timestamp()),
        "roles": [],
        "categories": [],
        "channels": [],
        "emojis": [e.name for e in guild.emojis],
    }

    for role in sorted(guild.roles, key=lambda r: r.position, reverse=True):
        if role.is_default():
            continue
        data["roles"].append({
            "name": role.name,
            "color": role.color.value,
            "hoist": role.hoist,
            "mentionable": role.mentionable,
            "permissions": role.permissions.value,
            "position": role.position,
            "managed": role.managed,
            "member_count": len(role.members),
        })

    for cat in sorted(guild.categories, key=lambda c: c.position):
        data["categories"].append({
            "name": cat.name,
            "position": cat.position,
            "overwrites": _overwrites(cat),
        })

    for ch in sorted(guild.channels, key=lambda c: (c.category.position if c.category else -1,
                                                    c.position)):
        if isinstance(ch, discord.CategoryChannel):
            continue
        entry = {
            "name": ch.name,
            "type": str(ch.type),
            "category": ch.category.name if ch.category else None,
            "position": ch.position,
            "overwrites": _overwrites(ch),
        }
        if isinstance(ch, (discord.TextChannel, discord.ForumChannel)):
            entry["topic"] = ch.topic
            entry["nsfw"] = ch.nsfw
            entry["slowmode"] = ch.slowmode_delay
        if isinstance(ch, discord.ForumChannel):
            entry["tags"] = [
                {"name": t.name, "emoji": str(t.emoji) if t.emoji else None,
                 "moderated": t.moderated}
                for t in ch.available_tags
            ]
        if isinstance(ch, discord.VoiceChannel):
            entry["bitrate"] = ch.bitrate
            entry["user_limit"] = ch.user_limit
        data["channels"].append(entry)

    return data


def _files():
    os.makedirs(BACKUP_DIR, exist_ok=True)
    return sorted(glob.glob(os.path.join(BACKUP_DIR, "backup-*.json")), reverse=True)


class Backup(commands.Cog):
    """Sauvegardes de la structure du serveur."""

    def __init__(self, bot):
        self.bot = bot
        self._store = JSONStore("backup.json", default={})
        self.weekly_backup.start()

    def cog_unload(self):
        if self.weekly_backup.is_running():
            self.weekly_backup.cancel()

    # ─────────────────────────────────────────────
    def create(self, guild: discord.Guild, *, tag: str = "manuel") -> str:
        os.makedirs(BACKUP_DIR, exist_ok=True)
        data = snapshot(guild)
        data["tag"] = tag
        stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        path = os.path.join(BACKUP_DIR, f"backup-{stamp}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        # Rotation
        for old in _files()[BACKUP_KEEP:]:
            try:
                os.remove(old)
            except OSError:
                pass
        log.info("Sauvegarde créée : %s", path)
        return path

    def _salon_rapport(self, guild):
        """Où déposer la sauvegarde : l'ID de la config d'abord.

        Sans ID explicite on retombe sur #bot-logs, puis sur le salon
        d'équipe — mais un fichier de 30 Ko toutes les semaines n'a rien
        à faire dans un salon de discussion.
        """
        for ch_id in (BACKUP_CHANNEL_ID, CHANNELS.get("bot_logs"),
                      CHANNELS.get("staff_chat")):
            if not ch_id:
                continue
            salon = guild.get_channel(ch_id)
            if salon is not None:
                return salon
        return None

    @tasks.loop(hours=168)
    async def weekly_backup(self):
        # discord.py relance la boucle dès le démarrage : on vérifie
        # nous-mêmes qu'une semaine est bien passée.
        depuis = time.time() - self._store.get("derniere_auto", 0)
        if depuis < BACKUP_MIN_DAYS * 86400:
            log.info("Sauvegarde auto ignorée : la dernière date de %.1f jour(s).",
                     depuis / 86400)
            return

        for guild in self.bot.guilds:
            try:
                path = self.create(guild, tag="auto-hebdo")
            except OSError as e:
                log.error("Sauvegarde auto KO : %s", e)
                continue
            channel = self._salon_rapport(guild)
            if channel:
                try:
                    await channel.send(
                        "💾 Sauvegarde hebdomadaire de la structure du serveur.",
                        file=discord.File(path),
                    )
                except discord.HTTPException:
                    pass

        self._store["derniere_auto"] = time.time()
        self._store.save()

    @weekly_backup.before_loop
    async def _before_backup(self):
        await self.bot.wait_until_ready()

    # ─────────────────────────────────────────────
    backup = app_commands.Group(
        name="backup",
        description="Sauvegardes de la structure du serveur (staff)",
        guild_ids=[GUILD_ID] if GUILD_ID else None,
        default_permissions=discord.Permissions(manage_guild=True),
    )

    @backup.command(name="creer", description="Crée une sauvegarde maintenant")
    async def creer(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            path = self.create(interaction.guild, tag=f"manuel ({interaction.user})")
        except OSError as e:
            await interaction.followup.send(f"❌ Écriture impossible : {e}", ephemeral=True)
            return

        data = snapshot(interaction.guild)
        embed = brand_embed(
            interaction.guild,
            title="💾 Sauvegarde créée",
            description=(
                f"**{len(data['roles'])}** rôles · "
                f"**{len(data['categories'])}** catégories · "
                f"**{len(data['channels'])}** salons · "
                f"**{len(data['emojis'])}** emojis\n\n"
                f"Fichier : `{os.path.basename(path)}`"
            ),
            color=COLOR_SUCCESS,
        )
        await interaction.followup.send(embed=embed, file=discord.File(path), ephemeral=True)

    @backup.command(name="liste", description="Liste les sauvegardes disponibles")
    async def liste(self, interaction: discord.Interaction):
        files = _files()
        if not files:
            await interaction.response.send_message(
                "📭 Aucune sauvegarde. Lance `/backup creer`.", ephemeral=True)
            return
        lines = []
        for i, path in enumerate(files, start=1):
            size = os.path.getsize(path) / 1024
            mtime = int(os.path.getmtime(path))
            lines.append(f"`{i}` **{os.path.basename(path)}** · "
                         f"{size:.0f} Ko · <t:{mtime}:R>")
        embed = brand_embed(
            interaction.guild,
            title="💾 Sauvegardes",
            description="\n".join(lines),
            color=COLOR_NEUTRAL,
        )
        embed.set_footer(text=f"{len(files)} fichier(s) · rotation à {BACKUP_KEEP}")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @backup.command(name="obtenir", description="Renvoie le fichier d'une sauvegarde")
    @app_commands.describe(numero="Numéro affiché par /backup liste (1 = la plus récente)")
    async def obtenir(self, interaction: discord.Interaction, numero: int = 1):
        files = _files()
        if not files or numero < 1 or numero > len(files):
            await interaction.response.send_message(
                "❌ Numéro invalide (voir `/backup liste`).", ephemeral=True)
            return
        await interaction.response.send_message(
            f"💾 `{os.path.basename(files[numero - 1])}`",
            file=discord.File(files[numero - 1]), ephemeral=True)

    @backup.command(name="diff",
                    description="Compare le serveur actuel à la dernière sauvegarde")
    async def diff(self, interaction: discord.Interaction):
        files = _files()
        if not files:
            await interaction.response.send_message(
                "📭 Aucune sauvegarde à comparer.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True, thinking=True)
        with open(files[0], encoding="utf-8") as f:
            old = json.load(f)
        new = snapshot(interaction.guild)

        def names(data, key):
            return {item["name"] for item in data[key]}

        blocks = []
        for key, label in (("roles", "Rôles"), ("channels", "Salons"),
                           ("categories", "Catégories")):
            added = names(new, key) - names(old, key)
            removed = names(old, key) - names(new, key)
            if not added and not removed:
                continue
            bits = []
            if added:
                bits.append("➕ " + ", ".join(sorted(added)[:15]))
            if removed:
                bits.append("➖ " + ", ".join(sorted(removed)[:15]))
            blocks.append(f"**{label}**\n" + "\n".join(bits))

        body = "\n\n".join(blocks) or "✅ Aucune différence de structure."
        embed = brand_embed(
            interaction.guild,
            title="🔍 Différences depuis la dernière sauvegarde",
            description=(f"Référence : `{os.path.basename(files[0])}` "
                         f"(<t:{old.get('taken_at', 0)}:R>)\n\n{body}")[:4000],
            color=COLOR_NEUTRAL,
        )
        await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(Backup(bot))
