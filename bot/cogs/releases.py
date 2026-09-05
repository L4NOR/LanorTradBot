"""
/release — Poste une release (FR scanlation ou EN translation)
==============================================================
Embed automatique + ping Lecteur FR/Reader EN + ping rôle manga
+ création auto du thread de discussion.

Le salon cible peut être un **salon texte** (message + thread) ou un
**forum** (post avec tags 🇫🇷/🇬🇧 + nom du manga appliqués automatiquement).

La logique de publication est exposée via `post_release()` pour être
réutilisée par le planificateur et l'auto-publication RSS.

/releases — Affiche les dernières releases postées (historique persistant).
"""
import logging
import time

import discord
from discord import app_commands
from discord.ext import commands

from bot.config import (
    GUILD_ID, MANGAS, CHANNELS, ROLES,
    COLOR_FR, COLOR_EN, COLOR_NEUTRAL,
    RELEASE_HISTORY_MAX, RELEASE_FORUM_MODE, RELEASE_FORUM_KEY,
    IS_INFO_SERVER, SITE, manga_url,
)
from bot.storage import JSONStore
from bot.embeds import LinkRow

log = logging.getLogger("lanortrad.release")

GUILD = discord.Object(id=GUILD_ID) if GUILD_ID else None


class ReleaseError(Exception):
    """Erreur métier renvoyée telle quelle à l'utilisateur."""


class Release(commands.Cog):
    """Commande /release pour poster les sorties."""

    def __init__(self, bot):
        self.bot = bot
        # Historique persistant : liste de dicts (plus récent en dernier)
        self._history = JSONStore("releases.json", default={"items": []})

    def _record(self, entry: dict):
        items = self._history.setdefault("items", [])
        items.append(entry)
        # Garde seulement les N plus récents
        if len(items) > RELEASE_HISTORY_MAX:
            del items[:-RELEASE_HISTORY_MAX]
        self._history.save()

    def recent(self, since_ts: float = 0) -> list:
        """Releases postées depuis `since_ts` (plus récente en dernier)."""
        return [it for it in self._history.get("items", [])
                if it.get("ts", 0) >= since_ts]

    def already_posted(self, manga_key: str, chapter: str, lang: str) -> bool:
        """Anti-doublon (utilisé par l'auto-publication RSS)."""
        for it in self._history.get("items", []):
            if (it.get("manga") == manga_key
                    and str(it.get("chapter")) == str(chapter)
                    and it.get("lang") == lang):
                return True
        return False

    # ─────────────────────────────────────────────
    # Cœur : publication d'une release
    # ─────────────────────────────────────────────
    def _target_channel(self, guild, is_fr: bool):
        if RELEASE_FORUM_KEY and CHANNELS.get(RELEASE_FORUM_KEY):
            ch = guild.get_channel(CHANNELS[RELEASE_FORUM_KEY])
            if ch is not None:
                return ch
        # Serveur informatif : un seul salon de sorties (#nouveaux-chapitres)
        key = "sorties_fr" if (is_fr or IS_INFO_SERVER) else "translations_en"
        ch_id = CHANNELS.get(key)
        if not ch_id:
            raise ReleaseError(
                f"Salon non configuré : `CHANNELS['{key}']` est vide dans `bot_config.py`.")
        ch = guild.get_channel(ch_id)
        if ch is None:
            raise ReleaseError(f"Salon introuvable (ID {ch_id}).")
        return ch

    @staticmethod
    def _forum_tags(channel: discord.ForumChannel, manga_name: str, is_fr: bool):
        """Retrouve les tags du forum correspondant à la langue et au manga."""
        wanted = {
            "fr" if is_fr else "en",
            manga_name.lower(),
            "chapitre",           # présent sur les forums manga bilingues
        }
        tags = [t for t in channel.available_tags if t.name.lower() in wanted]
        return tags[:5]

    def _build_embed(self, manga_info, chapter, is_fr, link, cover, note):
        emoji, name = manga_info["emoji"], manga_info["name"]
        if is_fr:
            title = f"{emoji} {name} — Chapitre {chapter}"
            description = (
                "**Scanlation complète FR** disponible 🩸\n"
                "Clean · Redraw · Typeset · QC\n\n"
                f"🔗 **Lire** → {link}"
            )
            color, footer = COLOR_FR, "LanorTrad · French Scanlation"
        else:
            title = f"{emoji} {name} — Chapter {chapter}"
            description = (
                "**EN text translation** available 🌐\n"
                "*Script only — no clean / redraw / typeset*\n\n"
                f"🔗 **Read** → {link}"
            )
            color, footer = COLOR_EN, "LanorTrad · EN Translation"

        if note:
            description += f"\n\n📝 *{note}*"
        if IS_INFO_SERVER:
            description += (
                f"\n\n💬 Envie d'en parler ? C'est sur le forum du site :\n{SITE['forum']}"
            )

        embed = discord.Embed(title=title, description=description, color=color, url=link)
        embed.set_footer(text=footer)
        if cover:
            embed.set_image(url=cover)
        return embed

    async def post_release(self, guild, *, manga_key: str, chapter: str, lang: str,
                           link: str, cover: str = None, note: str = None,
                           author_id: int = None, source: str = "commande"):
        """Publie une release. Retourne (message, channel). Lève ReleaseError."""
        manga_info = MANGAS.get(manga_key)
        if manga_info is None:
            raise ReleaseError(f"Manga inconnu : `{manga_key}`.")
        # Lien omis → on renvoie vers la fiche de la série sur le site
        link = link or manga_url(manga_key)
        if not link.startswith(("http://", "https://")):
            raise ReleaseError("Le lien doit commencer par `http://` ou `https://`.")

        is_fr = (lang == "fr")
        emoji, name = manga_info["emoji"], manga_info["name"]
        channel = self._target_channel(guild, is_fr)

        # ─── Pings : rôle langue + rôle manga ───
        pings = []
        lang_role = ROLES.get("lecteur_fr" if is_fr else "reader_en")
        manga_role = ROLES.get(manga_info["role_key"])
        if lang_role:
            pings.append(f"<@&{lang_role}>")
        if manga_role:
            pings.append(f"<@&{manga_role}>")
        pings_str = " ".join(pings)

        embed = self._build_embed(manga_info, chapter, is_fr, link, cover, note)
        read_label = "📖 Lire le chapitre" if is_fr else "📖 Read the chapter"
        view = LinkRow(link, read_label=read_label)
        thread_name = f"💬 {name} · Ch.{chapter}" + ("" if is_fr else " (EN)")
        mentions = discord.AllowedMentions(roles=True)

        use_forum = (RELEASE_FORUM_MODE == "auto"
                     and isinstance(channel, discord.ForumChannel))

        try:
            if use_forum:
                created = await channel.create_thread(
                    name=f"{emoji} {name} — "
                         f"{'Chapitre' if is_fr else 'Chapter'} {chapter}"[:100],
                    content=pings_str or None,
                    embed=embed,
                    view=view,
                    applied_tags=self._forum_tags(channel, name, is_fr),
                    allowed_mentions=mentions,
                )
                message = created.message
            else:
                message = await channel.send(
                    content=pings_str or None, embed=embed, view=view,
                    allowed_mentions=mentions,
                )
                try:
                    await message.create_thread(name=thread_name[:100],
                                                auto_archive_duration=1440)
                except discord.HTTPException as e:
                    log.warning("Thread non créé : %s", e)
        except discord.Forbidden:
            raise ReleaseError(f"Permissions insuffisantes pour poster dans {channel.mention}.")
        except discord.HTTPException as e:
            log.error("Envoi release KO : %s", e)
            raise ReleaseError(f"Discord a refusé l'envoi : {e}")

        self._record({
            "manga": manga_key, "name": name, "emoji": emoji,
            "chapter": chapter, "lang": lang, "link": link,
            "url": message.jump_url if message else None,
            "by": author_id, "source": source, "ts": int(time.time()),
        })
        log.info("Release %s Ch.%s (%s) publiée via %s.", name, chapter, lang, source)

        return message, channel

    # ─────────────────────────────────────────────
    # Commandes
    # ─────────────────────────────────────────────
    @app_commands.command(
        name="release",
        description="Poste une release (sortie FR ou translation EN)"
    )
    @app_commands.describe(
        manga="Le manga concerné",
        chapter="Numéro du chapitre (ex: 142)",
        lang="fr = scanlation complète · en = text translation",
        link="URL du chapitre (vide = fiche de la série sur le site)",
        cover="URL de la cover (optionnel)",
        note="Note additionnelle (optionnel)",
    )
    @app_commands.choices(
        manga=[
            app_commands.Choice(name=info["name"], value=key)
            for key, info in MANGAS.items()
        ],
        lang=[
            app_commands.Choice(name="🇫🇷 FR (scanlation complète)", value="fr"),
            app_commands.Choice(name="🇬🇧 EN (text translation)", value="en"),
        ],
    )
    @app_commands.default_permissions(manage_messages=True)
    @app_commands.guilds(GUILD)
    async def release(
        self,
        interaction: discord.Interaction,
        manga: app_commands.Choice[str],
        chapter: str,
        lang: app_commands.Choice[str] = None,
        link: str = None,
        cover: str = None,
        note: str = None,
    ):
        # On répond tout de suite en "thinking" : la suite fait plusieurs appels
        # réseau (envoi du message + création du thread) qui peuvent dépasser
        # la limite de 3s d'une réponse d'interaction.
        await interaction.response.defer(ephemeral=True, thinking=True)

        try:
            message, channel = await self.post_release(
                interaction.guild,
                manga_key=manga.value, chapter=chapter,
                lang=(lang.value if lang else "fr"),
                link=link, cover=cover, note=note,
                author_id=interaction.user.id, source="commande",
            )
        except ReleaseError as e:
            await interaction.followup.send(f"❌ {e}", ephemeral=True)
            return

        await interaction.followup.send(
            f"✅ Release postée dans {channel.mention}", ephemeral=True)

    @app_commands.command(
        name="sorties",
        description="Affiche les dernières releases postées"
    )
    @app_commands.describe(count="Nombre de releases à afficher (1-15, défaut 10)")
    @app_commands.guilds(GUILD)
    async def releases(self, interaction: discord.Interaction, count: int = 10):
        count = max(1, min(count, 15))
        items = self._history.get("items", [])
        if not items:
            await interaction.response.send_message(
                "📭 Aucune release enregistrée pour l'instant.",
                ephemeral=True,
            )
            return

        recent = list(reversed(items[-count:]))
        lines = []
        for it in recent:
            flag = "🇫🇷" if it.get("lang") == "fr" else "🇬🇧"
            ts = it.get("ts")
            when = f"<t:{ts}:R>" if ts else ""
            link = it.get("url") or it.get("link") or ""
            label = f"{it.get('emoji', '')} **{it.get('name', '?')}** — Ch.{it.get('chapter', '?')}"
            if link:
                label = f"[{label}]({link})"
            lines.append(f"{flag} {label} · {when}".strip(" ·"))

        embed = discord.Embed(
            title="📦 Dernières releases",
            description="\n".join(lines),
            color=COLOR_NEUTRAL,
        )
        embed.set_footer(text=f"{len(items)} release(s) au total")
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(Release(bot))
