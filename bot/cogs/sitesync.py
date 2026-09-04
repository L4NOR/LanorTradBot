"""
Synchronisation avec le site — Discord suit, le site décide
=============================================================
L'équipe met déjà à jour le site (series.js · atelier.js · chapters.js).
Ce cog lit ces fichiers et recopie tout dans Discord :

  📅 **Calendrier hebdomadaire** — même règle que le site : chaque série
     tombe le jour de semaine de sa dernière mise à jour
  🛠️ **Atelier** — où en est chaque prochain chapitre, avec la même jauge
     en 6 étapes (pages → clean → trad → edit → q-check → sortie)
  📚 **Catalogue** — genres, auteur, note, couverture, couleur d'accent

Et il détecte tout seul :
  • un **avancement d'étape** → message dans le salon de l'équipe
  • un **nouveau chapitre paru** → publication automatique avec ping

  /atelier · /planning · /serie · /catalogue · /site_sync (staff)

Aucune ressaisie, aucune divergence possible entre le site et le serveur.
"""
import asyncio
import datetime
import logging

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands, tasks

from bot import site as sitelib
from bot.config import (
    GUILD_ID, CHANNELS, MANGAS, SITE_URL, SITE,
    COLOR_NEUTRAL, COLOR_SUCCESS, COLOR_WARNING,
    SITE_SYNC_ENABLED, SITE_SYNC_INTERVAL,
    SITE_BOARD_PUBLIC, SITE_BOARD_STAFF,
    SITE_ANNOUNCE_STEPS, SITE_AUTO_RELEASE, SITE_STEPS_CHANNEL,
    SITE_INCIDENT_ALERTS, SITE_INCIDENT_STRIKES, SITE_INCIDENT_CHANNEL,
    SITE_STALE_DAYS, COLOR_ERROR,
)
from bot.embeds import brand_embed
from bot.storage import JSONStore

log = logging.getLogger("lanortrad.sitesync")

GUILD = discord.Object(id=GUILD_ID) if GUILD_ID else None

FULL, EMPTY = "▰", "▱"


def manga_key_for(series_id: str):
    """Retrouve la clé MANGAS correspondant à un identifiant de série du site."""
    target = sitelib.normalize(series_id)
    for key, info in MANGAS.items():
        if sitelib.normalize(info["name"]) == target:
            return key
    return None


def gauge(index: int, total: int) -> str:
    return FULL * (index + 1) + EMPTY * (total - index - 1)


def fr_date(iso: str) -> str:
    try:
        d = datetime.date.fromisoformat(iso)
        return f"<t:{int(datetime.datetime.combine(d, datetime.time(12, 0), tzinfo=datetime.timezone.utc).timestamp())}:D>"
    except (TypeError, ValueError):
        return iso or "—"


class SiteSync(commands.Cog):
    """Miroir Discord des données du site."""

    def __init__(self, bot):
        self.bot = bot
        self._store = JSONStore("sitesync.json", default={
            "boards": {}, "chapters": {}, "workshop": {}, "initialized": False,
        })
        self._session = None
        self.data = None            # dernier SiteData récupéré
        self._failures = 0          # échecs consécutifs de récupération
        self._down = False          # panne déjà annoncée ?
        if SITE_SYNC_ENABLED and SITE_URL:
            self.sync.start()

    def cog_unload(self):
        if self.sync.is_running():
            self.sync.cancel()
        if self._session and not self._session.closed:
            asyncio.create_task(self._session.close())

    async def _http(self):
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                headers={"User-Agent": "LanorTradBot/1.0"},
                timeout=aiohttp.ClientTimeout(total=25),
            )
        return self._session

    async def refresh(self):
        """Recharge les données du site. Retourne le SiteData ou None."""
        try:
            session = await self._http()
            self.data = await sitelib.fetch(session, SITE_URL)
            return self.data
        except (aiohttp.ClientError, ValueError, asyncio.TimeoutError) as e:
            log.warning("Site illisible : %s", e)
            return None

    # ─────────────────────────────────────────────
    # Rendu
    # ─────────────────────────────────────────────
    def workshop_embed(self, guild, *, detailed: bool) -> discord.Embed:
        items = self.data.workshop() if self.data else []
        if not items:
            description = "*Aucun chapitre en fabrication pour le moment.*"
        else:
            blocks = []
            for i in items:
                head = f"**{i['series']}** · ch. {i['chapter']}"
                line = (f"{gauge(i['step_index'], len(sitelib.STEPS))} "
                        f"{i['step_emoji']} **{i['step_label']}** ({i['progress']})")
                bits = [head, f"╰ {line}"]
                if i["eta"]:
                    bits.append(f"╰ 🎯 visé pour le {fr_date(i['eta'])}")
                if detailed and i["updated"]:
                    bits.append(f"╰ 🕒 dernier point d'étape le {fr_date(i['updated'])}")
                if i["note"]:
                    bits.append(f"╰ 📝 *{i['note']}*")
                blocks.append("\n".join(bits))
            description = "\n\n".join(blocks)

        embed = brand_embed(
            guild,
            title="🛠️ À l'atelier",
            description=description,
            color=COLOR_NEUTRAL,
        )
        legend = " → ".join(f"{s[2]} {s[1]}" for s in sitelib.STEPS)
        embed.add_field(name="Les étapes", value=legend, inline=False)
        embed.set_footer(text="Reflet du site · lanortradtest.netlify.app/planning")
        return embed

    def weekly_embed(self, guild) -> discord.Embed:
        today = datetime.date.today().weekday()
        today_fr = sitelib.DAYS_FR[(today + 1) % 7]

        lines = []
        for day, items in (self.data.weekly() if self.data else []):
            marker = " ← **aujourd'hui**" if day == today_fr else ""
            if not items:
                lines.append(f"**{day}**{marker}\n╰ *pas de sortie prévue*")
                continue
            body = "\n".join(
                f"╰ {MANGAS.get(manga_key_for(x['series']['id']), {}).get('emoji', '📖')} "
                f"**{x['series']['id']}** — ch. {x['next']} à venir"
                for x in items
            )
            lines.append(f"**{day}**{marker}\n{body}")

        embed = brand_embed(
            guild,
            title="📅 Rythme de parution",
            description="\n".join(lines) or "*Aucune série en cours.*",
            color=COLOR_NEUTRAL,
        )
        embed.add_field(
            name="Voir le détail",
            value=f"[Planning complet sur le site]({SITE['planning']})",
            inline=False,
        )
        return embed

    def series_embed(self, guild, series: dict) -> discord.Embed:
        d = self.data
        stars = "★" * int(round(series.get("rating", 0))) + \
                "☆" * (5 - int(round(series.get("rating", 0))))
        key = manga_key_for(series["id"])
        emoji = MANGAS.get(key, {}).get("emoji", "📖")

        embed = brand_embed(
            guild,
            title=f"{emoji} {series.get('title', series['id'])}",
            description=(series.get("description") or "")[:900],
            color=d.accent(series) if d else COLOR_NEUTRAL,
            url=d.series_url(series) if d else None,
        )
        embed.add_field(name="Statut", value=series.get("status", "—"), inline=True)
        embed.add_field(name="Chapitres", value=str(series.get("chapters", "—")), inline=True)
        embed.add_field(name="Note", value=f"{stars} {series.get('rating', '—')}", inline=True)
        embed.add_field(name="Auteur", value=series.get("author") or "—", inline=True)
        embed.add_field(name="Année", value=str(series.get("year") or "—"), inline=True)
        embed.add_field(name="Genres", value=", ".join(series.get("genres") or []) or "—",
                        inline=True)

        last = d.last_chapter(series["id"]) if d else None
        if last:
            embed.add_field(name="Dernier chapitre paru", value=f"Chapitre {last}", inline=True)

        entry = (d.atelier or {}).get(series["id"]) if d else None
        if entry:
            info = sitelib.STEP_INFO.get(entry.get("step"))
            if info:
                embed.add_field(
                    name="En fabrication",
                    value=f"ch. {entry.get('chapter')} · {info[2]} {info[1]}",
                    inline=True,
                )
        if d:
            cover = d.cover_url(series)
            if cover:
                embed.set_thumbnail(url=cover)
        return embed

    # ─────────────────────────────────────────────
    # Boards auto-mis à jour
    # ─────────────────────────────────────────────
    async def _upsert(self, guild, channel_key: str, embeds: list, store_key: str):
        ch_id = CHANNELS.get(channel_key)
        if not ch_id:
            return
        channel = guild.get_channel(ch_id)
        if channel is None:
            return

        boards = self._store.setdefault("boards", {})
        msg_id = boards.get(store_key)
        message = None
        if msg_id:
            try:
                message = await channel.fetch_message(int(msg_id))
            except (discord.NotFound, discord.HTTPException):
                message = None
        try:
            if message:
                await message.edit(embeds=embeds)
            else:
                message = await channel.send(embeds=embeds)
                boards[store_key] = message.id
                self._store.save()
                try:
                    await message.pin(reason="Miroir du site")
                except discord.HTTPException:
                    pass
        except discord.HTTPException as e:
            log.warning("Board %s non mis à jour : %s", store_key, e)

    async def refresh_boards(self, guild):
        if self.data is None:
            return
        if SITE_BOARD_PUBLIC:
            await self._upsert(
                guild, SITE_BOARD_PUBLIC,
                [self.weekly_embed(guild), self.workshop_embed(guild, detailed=False)],
                "public",
            )
        if SITE_BOARD_STAFF:
            await self._upsert(
                guild, SITE_BOARD_STAFF,
                [self.workshop_embed(guild, detailed=True)],
                "staff",
            )

    # ─────────────────────────────────────────────
    # Détection des changements
    # ─────────────────────────────────────────────
    async def _announce_steps(self, guild, previous: dict):
        current = self.data.workshop_signature()
        ch_id = CHANNELS.get(SITE_STEPS_CHANNEL) or CHANNELS.get("staff_chat")
        channel = guild.get_channel(ch_id) if ch_id else None

        for series_id, signature in current.items():
            if previous.get(series_id) == signature:
                continue
            old_step = (previous.get(series_id) or "|").split("|")[-1]
            chapter, step = signature.split("|", 1)
            info = sitelib.STEP_INFO.get(step)
            if not info or channel is None:
                continue
            old_label = sitelib.STEP_INFO.get(old_step, ("", "nouveau", "", ""))[1]
            try:
                await channel.send(
                    f"{info[2]} **{series_id}** ch. {chapter} — "
                    f"{old_label} → **{info[1]}**\n*{info[3]}*"
                )
            except discord.HTTPException:
                pass

        self._store["workshop"] = current
        self._store.save()

    async def _detect_releases(self, guild, previous: dict):
        """Un chapitre de plus dans chapters.js = un chapitre publié."""
        release_cog = self.bot.get_cog("Release")
        current = {}
        for series in self.data.series:
            last = self.data.last_chapter(series["id"])
            if last:
                current[series["id"]] = last

        first_run = not self._store.get("initialized")
        for series_id, last in current.items():
            if previous.get(series_id) == last:
                continue
            if first_run or not SITE_AUTO_RELEASE or release_cog is None:
                continue

            key = manga_key_for(series_id)
            series = self.data.get_series(series_id)
            if key is None or series is None:
                log.info("Nouveau chapitre ignoré (série hors catalogue) : %s", series_id)
                continue
            if release_cog.already_posted(key, last, "fr"):
                continue
            try:
                await release_cog.post_release(
                    guild, manga_key=key, chapter=last, lang="fr",
                    link=self.data.series_url(series),
                    cover=self.data.cover_url(series),
                    source="auto (site)",
                )
                log.info("Release auto publiée : %s ch.%s", series_id, last)
            except Exception as e:                     # noqa: BLE001
                log.error("Publication auto KO (%s ch.%s) : %s", series_id, last, e)

        self._store["chapters"] = current
        self._store["initialized"] = True
        self._store.save()

    # ─────────────────────────────────────────────
    # Surveillance du site
    # ─────────────────────────────────────────────
    async def _incident(self, *, down: bool):
        """Annonce une panne du site, ou son rétablissement."""
        if not SITE_INCIDENT_ALERTS:
            return
        ch_id = CHANNELS.get(SITE_INCIDENT_CHANNEL)
        for guild in self.bot.guilds:
            channel = guild.get_channel(ch_id) if ch_id else None
            if channel is None:
                continue
            if down:
                embed = brand_embed(
                    guild,
                    title="🩹 Le site ne répond pas",
                    description=(
                        f"Nos données sont injoignables depuis "
                        f"**{self._failures} vérifications** "
                        f"(~{self._failures * SITE_SYNC_INTERVAL} min).\n\n"
                        "La lecture est peut-être perturbée. On regarde ça.\n"
                        f"En attendant : {SITE_URL}"
                    ),
                    color=COLOR_ERROR,
                )
            else:
                embed = brand_embed(
                    guild,
                    title="✅ Le site refonctionne",
                    description="Tout est revenu à la normale. Bonne lecture !",
                    color=COLOR_SUCCESS,
                )
            try:
                await channel.send(embed=embed)
            except discord.HTTPException:
                pass

    async def _nudge_stale(self, guild):
        """Une fois par semaine, ressort les chapitres qui n'ont pas bougé."""
        if not SITE_STALE_DAYS or self.data is None:
            return
        today = datetime.date.today()
        last_nudge = self._store.get("last_nudge")
        if last_nudge:
            try:
                if (today - datetime.date.fromisoformat(last_nudge)).days < 7:
                    return
            except ValueError:
                pass

        stale = []
        for item in self.data.workshop():
            try:
                age = (today - datetime.date.fromisoformat(item["updated"])).days
            except (TypeError, ValueError):
                continue
            if age >= SITE_STALE_DAYS:
                stale.append((item, age))
        if not stale:
            self._store["last_nudge"] = today.isoformat()
            self._store.save()
            return

        ch_id = CHANNELS.get(SITE_STEPS_CHANNEL) or CHANNELS.get("staff_chat")
        channel = guild.get_channel(ch_id) if ch_id else None
        if channel is None:
            return

        lines = [
            f"{i['step_emoji']} **{i['series']}** ch. {i['chapter']} — "
            f"bloqué en {i['step_label']} depuis **{age} jours**"
            for i, age in sorted(stale, key=lambda x: -x[1])
        ]
        embed = brand_embed(
            guild,
            title="🕒 Ça dort un peu à l'atelier",
            description="\n".join(lines) + (
                "\n\n*Rappel hebdomadaire. Un point d'étape sur le site "
                "suffit à me faire taire.*"
            ),
            color=COLOR_WARNING,
        )
        try:
            await channel.send(embed=embed)
        except discord.HTTPException:
            pass
        self._store["last_nudge"] = today.isoformat()
        self._store.save()

    # ─────────────────────────────────────────────
    # Boucle
    # ─────────────────────────────────────────────
    @tasks.loop(minutes=max(5, SITE_SYNC_INTERVAL))
    async def sync(self):
        if await self.refresh() is None:
            self._failures += 1
            if not self._down and self._failures >= SITE_INCIDENT_STRIKES:
                self._down = True
                await self._incident(down=True)
            return

        if self._down:
            self._down = False
            await self._incident(down=False)
        self._failures = 0
        previous_chapters = dict(self._store.get("chapters", {}))
        previous_workshop = dict(self._store.get("workshop", {}))
        # Premier démarrage : on mémorise l'état sans rien annoncer
        first_run = not self._store.get("initialized")

        for guild in self.bot.guilds:
            await self._detect_releases(guild, previous_chapters)
            if SITE_ANNOUNCE_STEPS and not first_run:
                await self._announce_steps(guild, previous_workshop)
            else:
                self._store["workshop"] = self.data.workshop_signature()
                self._store.save()
            await self.refresh_boards(guild)
            if not first_run:
                await self._nudge_stale(guild)

    @sync.before_loop
    async def _before_sync(self):
        await self.bot.wait_until_ready()

    # ─────────────────────────────────────────────
    # Commandes
    # ─────────────────────────────────────────────
    async def _ensure_data(self, interaction):
        if self.data is None:
            await self.refresh()
        if self.data is None:
            await interaction.followup.send(
                "❌ Le site est injoignable pour le moment.", ephemeral=True)
            return False
        return True

    @app_commands.command(name="atelier",
                          description="Où en est chaque prochain chapitre")
    @app_commands.guilds(GUILD)
    async def atelier(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True)
        if not await self._ensure_data(interaction):
            return
        await interaction.followup.send(
            embed=self.workshop_embed(interaction.guild, detailed=False))

    @app_commands.command(name="planning",
                          description="Le rythme de parution des séries")
    @app_commands.guilds(GUILD)
    async def planning(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True)
        if not await self._ensure_data(interaction):
            return
        await interaction.followup.send(embed=self.weekly_embed(interaction.guild))

    @app_commands.command(name="serie", description="La fiche d'une série")
    @app_commands.describe(nom="Nom de la série (laisse vide pour la liste)")
    @app_commands.guilds(GUILD)
    async def serie(self, interaction: discord.Interaction, nom: str = None):
        await interaction.response.defer(thinking=True)
        if not await self._ensure_data(interaction):
            return

        if not nom:
            await interaction.followup.send(embed=self.catalogue_embed(interaction.guild))
            return

        series = self.data.get_series(nom)
        if series is None:
            candidates = [s["id"] for s in self.data.series
                          if sitelib.normalize(nom) in sitelib.normalize(s["id"])]
            if len(candidates) == 1:
                series = self.data.get_series(candidates[0])
            else:
                await interaction.followup.send(
                    "❌ Série inconnue. Essaie : "
                    + ", ".join(f"`{s['id']}`" for s in self.data.series[:10]),
                    ephemeral=True)
                return
        await interaction.followup.send(embed=self.series_embed(interaction.guild, series))

    @serie.autocomplete("nom")
    async def serie_autocomplete(self, interaction: discord.Interaction, current: str):
        if self.data is None:
            return []
        needle = sitelib.normalize(current)
        return [
            app_commands.Choice(name=s["id"], value=s["id"])
            for s in self.data.series
            if needle in sitelib.normalize(s["id"])
        ][:25]

    def catalogue_embed(self, guild) -> discord.Embed:
        d = self.data
        ongoing = d.ongoing()
        others = [s for s in d.series if s not in ongoing]

        def line(s):
            key = manga_key_for(s["id"])
            emoji = MANGAS.get(key, {}).get("emoji", "📖")
            last = d.last_chapter(s["id"])
            return (f"{emoji} **{s['id']}** — {s.get('chapters', '?')} ch. · "
                    f"{'★' * int(round(s.get('rating', 0)))} {s.get('rating', '')}"
                    + (f" · dernier : ch. {last}" if last else ""))

        embed = brand_embed(
            guild,
            title="📚 Catalogue LanorTrad",
            description=f"[Tout le catalogue sur le site]({SITE['catalogue']})",
            color=COLOR_NEUTRAL,
        )
        if ongoing:
            embed.add_field(name="En cours",
                            value="\n".join(line(s) for s in ongoing), inline=False)
        if others:
            embed.add_field(name="Terminés · oneshots",
                            value="\n".join(line(s) for s in others), inline=False)
        return embed

    @app_commands.command(name="catalogue", description="Toutes les séries LanorTrad")
    @app_commands.guilds(GUILD)
    async def catalogue(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True)
        if not await self._ensure_data(interaction):
            return
        await interaction.followup.send(embed=self.catalogue_embed(interaction.guild))

    @app_commands.command(name="site_sync",
                          description="(Staff) Force la synchronisation avec le site")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.guilds(GUILD)
    async def site_sync(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        if await self.refresh() is None:
            await interaction.followup.send("❌ Site injoignable.", ephemeral=True)
            return
        await self.refresh_boards(interaction.guild)
        embed = brand_embed(
            interaction.guild,
            title="🔄 Synchronisation effectuée",
            description=(
                f"**{len(self.data.series)}** séries · "
                f"**{len(self.data.ongoing())}** en cours\n"
                f"**{len(self.data.workshop())}** chapitres en fabrication\n"
                f"Tableaux mis à jour."
            ),
            color=COLOR_SUCCESS,
        )
        await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(SiteSync(bot))
