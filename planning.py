# planning.py
# ═══════════════════════════════════════════════════════════════════════════════
# SYSTÈME DE PLANNING - Sorties de chapitres à venir
# Canal cible: 1332363693174034472
# ═══════════════════════════════════════════════════════════════════════════════

import discord
from discord.ext import commands, tasks
from discord.ui import View, Button, Select
import datetime
import logging
import asyncio
import pytz

from config import ADMIN_ROLES, COLORS, MANGA_EMOJIS, MANGA_ROLES, TASK_ROLES, DATA_DIR
from utils import load_json, save_json, save_with_meta, paginate, get_manga_emoji

logger = logging.getLogger(__name__)

# Canal de planning
PLANNING_CHANNEL_ID = 1332363693174034472

# Fichiers de données
PLANNING_FILE = f"{DATA_DIR}/planning.json"
PLANNING_META_FILE = f"{DATA_DIR}/planning_meta.json"

# Données en mémoire
planning_data = {}  # {"id": {manga, chapter, date, status, notes, added_by, message_id}}

# Statuts possibles
STATUTS = {
    "prevu": {"emoji": "📅", "label": "Prévu", "color": 0x3498DB},
    "en_cours": {"emoji": "🔄", "label": "En cours", "color": 0xF39C12},
    "trad_done": {"emoji": "🌍", "label": "Trad terminée", "color": 0x9B59B6},
    "check_done": {"emoji": "✅", "label": "Check terminé", "color": 0x2ECC71},
    "pret": {"emoji": "🚀", "label": "Prêt à sortir", "color": 0x1ABC9C},
    "sorti": {"emoji": "📢", "label": "Sorti", "color": 0x2ECC71},
    "retarde": {"emoji": "⚠️", "label": "Retardé", "color": 0xE74C3C},
}

JOURS_FR = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
MOIS_FR = ["", "Janvier", "Février", "Mars", "Avril", "Mai", "Juin",
           "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"]


def charger_planning():
    """Charge le planning depuis le fichier."""
    global planning_data
    planning_data = load_json(PLANNING_FILE, {})
    logger.info(f"📅 {len(planning_data)} entrée(s) de planning chargée(s)")


def sauvegarder_planning():
    """Sauvegarde le planning."""
    save_with_meta(PLANNING_FILE, planning_data, PLANNING_META_FILE)


def format_date_fr(date_str):
    """Convertit une date YYYY-MM-DD en format français lisible."""
    try:
        dt = datetime.datetime.strptime(date_str, "%Y-%m-%d")
        jour = JOURS_FR[dt.weekday()]
        mois = MOIS_FR[dt.month]
        return f"{jour} {dt.day} {mois} {dt.year}"
    except:
        return date_str


def build_planning_embed(upcoming_only=True):
    """Construit l'embed principal du planning."""
    now = datetime.datetime.now()
    today = now.date()

    # Filtrer et trier les entrées
    entries = []
    for pid, pdata in planning_data.items():
        try:
            date = datetime.datetime.strptime(pdata["date"], "%Y-%m-%d").date()
            if upcoming_only and date < today and pdata.get("status") == "sorti":
                continue  # Masquer les sorties passées déjà publiées
            entries.append((pid, pdata, date))
        except:
            entries.append((pid, pdata, today))

    entries.sort(key=lambda x: x[2])

    if not entries:
        embed = discord.Embed(
            title="📅 Planning des Sorties",
            description="*Aucune sortie planifiée pour le moment.*\n\nUtilisez `!planning_add` pour ajouter une entrée.",
            color=COLORS["info"]
        )
        embed.set_footer(text="LanorTrad • Planning")
        return embed

    embed = discord.Embed(
        title="📅 Planning des Sorties — LanorTrad",
        description="━━━━━━━━━━━━━━━━━━━━━━━━",
        color=COLORS["info"],
        timestamp=now
    )

    for pid, pdata, date in entries:
        manga = pdata["manga"]
        chapter = pdata["chapter"]
        status_key = pdata.get("status", "prevu")
        status_info = STATUTS.get(status_key, STATUTS["prevu"])
        emoji_manga = get_manga_emoji(manga)
        notes = pdata.get("notes", "")

        # Calcul jours restants
        delta = (date - today).days
        if delta == 0:
            countdown = "**AUJOURD'HUI** 🔥"
        elif delta == 1:
            countdown = "**Demain** ⏰"
        elif delta < 0:
            countdown = f"Il y a {abs(delta)} jour(s)"
        elif delta <= 7:
            countdown = f"Dans **{delta}** jour(s)"
        else:
            countdown = f"Dans {delta} jours"

        date_formatted = format_date_fr(pdata["date"])

        field_value = (
            f"{status_info['emoji']} **{status_info['label']}**\n"
            f"📆 {date_formatted}\n"
            f"⏳ {countdown}"
        )
        if notes:
            field_value += f"\n📝 _{notes}_"

        embed.add_field(
            name=f"{emoji_manga} {manga} — Chapitre {chapter}",
            value=field_value,
            inline=False
        )

    embed.set_footer(text=f"LanorTrad • {len(entries)} sortie(s) planifiée(s)")
    return embed


# ═══════════════════════════════════════════════════════════════════════════════
# VUE DE MISE À JOUR DU STATUT
# ═══════════════════════════════════════════════════════════════════════════════

class PlanningStatusSelect(Select):
    """Menu déroulant pour changer le statut d'une entrée."""

    def __init__(self, planning_id: str):
        self.planning_id = planning_id

        options = [
            discord.SelectOption(
                label=info["label"],
                value=key,
                emoji=info["emoji"],
                description=f"Marquer comme {info['label'].lower()}"
            )
            for key, info in STATUTS.items()
        ]

        super().__init__(
            placeholder="📊 Changer le statut...",
            options=options,
            custom_id=f"planning_status_{planning_id}"
        )

    async def callback(self, interaction: discord.Interaction):
        # Vérifier les permissions
        user_roles = [role.id for role in interaction.user.roles]
        if not any(role in user_roles for role in TASK_ROLES):
            await interaction.response.send_message("❌ Permissions insuffisantes.", ephemeral=True)
            return

        new_status = self.values[0]
        entry = planning_data.get(self.planning_id)
        if not entry:
            await interaction.response.send_message("❌ Entrée introuvable.", ephemeral=True)
            return

        old_status = entry.get("status", "prevu")
        entry["status"] = new_status
        entry["last_updated"] = datetime.datetime.now().isoformat()
        entry["updated_by"] = interaction.user.id
        sauvegarder_planning()

        status_info = STATUTS[new_status]
        await interaction.response.send_message(
            f"{status_info['emoji']} Statut de **{entry['manga']} Ch.{entry['chapter']}** "
            f"mis à jour : **{status_info['label']}**",
            ephemeral=True
        )

        # Mettre à jour le message du planning si possible
        cog = interaction.client.get_cog("PlanningSystem")
        if cog:
            await cog.update_planning_message()


class PlanningStatusView(View):
    """Vue avec le sélecteur de statut."""

    def __init__(self, planning_id: str):
        super().__init__(timeout=None)
        self.add_item(PlanningStatusSelect(planning_id))


# ═══════════════════════════════════════════════════════════════════════════════
# COG PRINCIPAL
# ═══════════════════════════════════════════════════════════════════════════════

class PlanningSystem(commands.Cog):
    """Système de planning des sorties de chapitres."""

    def __init__(self, bot):
        self.bot = bot
        charger_planning()
        self.planning_message_id = None  # ID du message planning affiché
        self.daily_planning_check.start()
        # Restaurer les views persistantes
        for pid in planning_data:
            bot.add_view(PlanningStatusView(pid))

    def cog_unload(self):
        self.daily_planning_check.cancel()
        sauvegarder_planning()

    async def update_planning_message(self):
        """Met à jour le message de planning épinglé."""
        channel = self.bot.get_channel(PLANNING_CHANNEL_ID)
        if not channel:
            return

        embed = build_planning_embed()

        if self.planning_message_id:
            try:
                msg = await channel.fetch_message(self.planning_message_id)
                await msg.edit(embed=embed)
                return
            except discord.NotFound:
                self.planning_message_id = None

    # ─────────────────────────────────────────────────────────────────────────
    # LOOP - VÉRIFICATION QUOTIDIENNE
    # ─────────────────────────────────────────────────────────────────────────

    @tasks.loop(hours=1)
    async def daily_planning_check(self):
        """Vérifie les sorties prévues aujourd'hui et envoie des rappels."""
        tz_paris = pytz.timezone('Europe/Paris')
        now = datetime.datetime.now(tz_paris)

        # Exécuter seulement à 9h
        if now.hour != 9:
            return

        today = now.date().isoformat()
        tomorrow = (now.date() + datetime.timedelta(days=1)).isoformat()

        channel = self.bot.get_channel(PLANNING_CHANNEL_ID)
        if not channel:
            return

        # Rappels pour aujourd'hui
        today_releases = []
        tomorrow_releases = []

        for pid, pdata in planning_data.items():
            if pdata.get("status") in ["sorti"]:
                continue
            if pdata["date"] == today:
                today_releases.append(pdata)
            elif pdata["date"] == tomorrow:
                tomorrow_releases.append(pdata)

        if today_releases:
            embed = discord.Embed(
                title="🔥 Sorties prévues AUJOURD'HUI !",
                color=0xFF6B6B,
                timestamp=now
            )
            for r in today_releases:
                emoji = get_manga_emoji(r["manga"])
                status = STATUTS.get(r.get("status", "prevu"), STATUTS["prevu"])
                embed.add_field(
                    name=f"{emoji} {r['manga']} — Ch. {r['chapter']}",
                    value=f"{status['emoji']} {status['label']}",
                    inline=True
                )
            embed.set_footer(text="LanorTrad • Planning")
            await channel.send(embed=embed)

        if tomorrow_releases:
            embed = discord.Embed(
                title="⏰ Sorties prévues DEMAIN",
                color=COLORS["warning"],
                timestamp=now
            )
            for r in tomorrow_releases:
                emoji = get_manga_emoji(r["manga"])
                embed.add_field(
                    name=f"{emoji} {r['manga']} — Ch. {r['chapter']}",
                    value=f"📅 {format_date_fr(r['date'])}",
                    inline=True
                )
            embed.set_footer(text="LanorTrad • Planning")
            await channel.send(embed=embed)

    @daily_planning_check.before_loop
    async def before_daily_check(self):
        await self.bot.wait_until_ready()

    # ─────────────────────────────────────────────────────────────────────────
    # COMMANDE - AFFICHER LE PLANNING
    # ─────────────────────────────────────────────────────────────────────────

    @commands.command(name="planning")
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def show_planning(self, ctx):
        """Affiche le planning des sorties de chapitres à venir."""
        embed = build_planning_embed(upcoming_only=True)
        await ctx.send(embed=embed)

    @commands.command(name="planning_full", aliases=["planning_all"])
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def show_full_planning(self, ctx):
        """Affiche le planning complet (y compris les sorties passées)."""
        if not planning_data:
            await ctx.send("📅 Aucune sortie planifiée.")
            return

        # Paginer si beaucoup d'entrées
        entries = sorted(
            planning_data.items(),
            key=lambda x: x[1].get("date", ""),
            reverse=True
        )

        pages = []
        per_page = 6

        for i in range(0, len(entries), per_page):
            page_entries = entries[i:i + per_page]
            embed = discord.Embed(
                title="📅 Planning Complet — LanorTrad",
                color=COLORS["info"],
                timestamp=datetime.datetime.now(datetime.timezone.utc)
            )

            for pid, pdata in page_entries:
                manga = pdata["manga"]
                chapter = pdata["chapter"]
                status_key = pdata.get("status", "prevu")
                status_info = STATUTS.get(status_key, STATUTS["prevu"])
                emoji = get_manga_emoji(manga)
                date_fr = format_date_fr(pdata["date"])

                embed.add_field(
                    name=f"{emoji} {manga} — Ch. {chapter}",
                    value=(
                        f"{status_info['emoji']} {status_info['label']}\n"
                        f"📆 {date_fr}\n"
                        f"🆔 `{pid}`"
                    ),
                    inline=True
                )

            embed.set_footer(text=f"Page {len(pages)+1} • {len(entries)} entrée(s)")
            pages.append(embed)

        await paginate(ctx, pages)

    # ─────────────────────────────────────────────────────────────────────────
    # COMMANDE - AJOUTER AU PLANNING
    # ─────────────────────────────────────────────────────────────────────────

    @commands.command(name="planning_add", aliases=["add_planning"])
    @commands.has_any_role(*TASK_ROLES)
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def add_planning(self, ctx, manga: str = None, chapter: str = None,
                           date: str = None, *, notes: str = None):
        """
        Ajoute une sortie au planning.

        Usage rapide: !planning_add "Tougen Anki" 220 2026-03-20 Notes optionnelles
        Usage interactif: !planning_add (sans arguments)
        """
        if manga and chapter and date:
            await self._add_quick(ctx, manga, chapter, date, notes)
        else:
            await self._add_interactive(ctx)

    async def _add_quick(self, ctx, manga, chapter, date_str, notes=None):
        """Ajout rapide en une ligne."""
        # Valider la date
        try:
            date = datetime.datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            await ctx.send("❌ Format de date invalide. Utilisez `AAAA-MM-JJ` (ex: `2026-03-20`).", delete_after=10)
            return

        # Valider le chapitre
        if not chapter.isdigit():
            await ctx.send("❌ Numéro de chapitre invalide.", delete_after=10)
            return

        await self._finalize_add(ctx, manga.strip(), chapter, date_str, notes)

    async def _add_interactive(self, ctx):
        """Ajout interactif étape par étape."""
        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel

        try:
            # Manga
            manga_list = "\n".join([f"{v} `{k}`" for k, v in MANGA_EMOJIS.items()])
            embed = discord.Embed(
                title="📅 Ajouter au Planning",
                description=f"Quel manga ?\n\n{manga_list}\n\nOu tapez un nom personnalisé.",
                color=COLORS["info"]
            )
            await ctx.send(embed=embed)
            msg = await self.bot.wait_for('message', check=check, timeout=60)
            manga = msg.content.strip()

            # Chapitre
            embed = discord.Embed(
                title="📖 Numéro de chapitre",
                description="Quel numéro de chapitre ?",
                color=COLORS["info"]
            )
            await ctx.send(embed=embed)
            msg = await self.bot.wait_for('message', check=check, timeout=60)
            chapter = msg.content.strip()

            if not chapter.replace("-", "").isdigit():
                await ctx.send("❌ Numéro de chapitre invalide.", delete_after=10)
                return

            # Date
            embed = discord.Embed(
                title="📆 Date de sortie prévue",
                description="Format: `AAAA-MM-JJ` (ex: `2026-03-25`)",
                color=COLORS["info"]
            )
            await ctx.send(embed=embed)
            msg = await self.bot.wait_for('message', check=check, timeout=60)
            date_str = msg.content.strip()

            try:
                datetime.datetime.strptime(date_str, "%Y-%m-%d")
            except ValueError:
                await ctx.send("❌ Format de date invalide.", delete_after=10)
                return

            # Notes
            embed = discord.Embed(
                title="📝 Notes (optionnel)",
                description="Ajoutez des notes (ou tapez `non` pour passer).",
                color=COLORS["info"]
            )
            await ctx.send(embed=embed)
            msg = await self.bot.wait_for('message', check=check, timeout=60)
            notes = msg.content.strip() if msg.content.strip().lower() != "non" else None

            await self._finalize_add(ctx, manga, chapter, date_str, notes)

        except asyncio.TimeoutError:
            await ctx.send("⏰ Temps écoulé. Ajout annulé.", delete_after=10)

    async def _finalize_add(self, ctx, manga, chapter, date_str, notes=None):
        """Finalise l'ajout au planning."""
        planning_id = f"{manga.lower().replace(' ', '_')}_{chapter}"

        # Vérifier si déjà existant
        if planning_id in planning_data:
            await ctx.send(
                f"⚠️ **{manga} Ch.{chapter}** est déjà dans le planning. "
                f"Utilisez `!planning_update {planning_id}` pour modifier.",
                delete_after=15
            )
            return

        planning_data[planning_id] = {
            "manga": manga,
            "chapter": chapter,
            "date": date_str,
            "status": "prevu",
            "notes": notes or "",
            "added_by": ctx.author.id,
            "created_at": datetime.datetime.now().isoformat(),
            "last_updated": datetime.datetime.now().isoformat(),
            "message_id": None,
        }
        sauvegarder_planning()

        emoji = get_manga_emoji(manga)
        date_fr = format_date_fr(date_str)

        # Embed de confirmation
        embed = discord.Embed(
            title="✅ Ajouté au planning !",
            color=COLORS["success"],
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )
        embed.add_field(name=f"{emoji} Manga", value=manga, inline=True)
        embed.add_field(name="📖 Chapitre", value=chapter, inline=True)
        embed.add_field(name="📆 Date prévue", value=date_fr, inline=True)
        if notes:
            embed.add_field(name="📝 Notes", value=notes, inline=False)
        embed.add_field(name="🆔 ID", value=f"`{planning_id}`", inline=False)
        embed.set_footer(text=f"Ajouté par {ctx.author.name}")

        await ctx.send(embed=embed)

        # Poster dans le canal planning
        planning_channel = self.bot.get_channel(PLANNING_CHANNEL_ID)
        if planning_channel:
            planning_embed = build_planning_embed()
            view = PlanningStatusView(planning_id)
            msg = await planning_channel.send(embed=planning_embed, view=view)
            planning_data[planning_id]["message_id"] = msg.id
            self.planning_message_id = msg.id
            sauvegarder_planning()

    # ─────────────────────────────────────────────────────────────────────────
    # COMMANDE - MODIFIER LE STATUT
    # ─────────────────────────────────────────────────────────────────────────

    @commands.command(name="planning_status", aliases=["planning_update"])
    @commands.has_any_role(*TASK_ROLES)
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def update_status(self, ctx, planning_id: str, new_status: str = None):
        """
        Met à jour le statut d'une entrée du planning.

        Usage: !planning_status <id> <statut>
        Statuts: prevu, en_cours, trad_done, check_done, pret, sorti, retarde
        """
        entry = planning_data.get(planning_id)
        if not entry:
            # Chercher par correspondance partielle
            matches = [pid for pid in planning_data if planning_id.lower() in pid.lower()]
            if len(matches) == 1:
                planning_id = matches[0]
                entry = planning_data[planning_id]
            else:
                await ctx.send(f"❌ Entrée `{planning_id}` introuvable.", delete_after=10)
                return

        if not new_status:
            # Afficher le sélecteur
            view = PlanningStatusView(planning_id)
            emoji = get_manga_emoji(entry["manga"])
            embed = discord.Embed(
                title=f"{emoji} {entry['manga']} — Ch. {entry['chapter']}",
                description="Sélectionnez le nouveau statut :",
                color=COLORS["info"]
            )
            current = STATUTS.get(entry.get("status", "prevu"), STATUTS["prevu"])
            embed.add_field(name="Statut actuel", value=f"{current['emoji']} {current['label']}")
            await ctx.send(embed=embed, view=view)
            return

        new_status = new_status.lower()
        if new_status not in STATUTS:
            statuts_list = ", ".join([f"`{k}` ({v['emoji']} {v['label']})" for k, v in STATUTS.items()])
            await ctx.send(f"❌ Statut invalide. Choix : {statuts_list}", delete_after=15)
            return

        entry["status"] = new_status
        entry["last_updated"] = datetime.datetime.now().isoformat()
        entry["updated_by"] = ctx.author.id
        sauvegarder_planning()

        status_info = STATUTS[new_status]
        embed = discord.Embed(
            title=f"{status_info['emoji']} Statut mis à jour",
            description=(
                f"**{entry['manga']}** — Chapitre **{entry['chapter']}**\n"
                f"Nouveau statut : **{status_info['label']}**"
            ),
            color=status_info["color"]
        )
        embed.set_footer(text=f"Par {ctx.author.name}")
        await ctx.send(embed=embed)

        # Mettre à jour le message dans le canal planning
        await self.update_planning_message()

        # Si "sorti", notification spéciale
        if new_status == "sorti":
            planning_channel = self.bot.get_channel(PLANNING_CHANNEL_ID)
            if planning_channel:
                notif = discord.Embed(
                    title=f"📢 {get_manga_emoji(entry['manga'])} NOUVEAU CHAPITRE DISPONIBLE !",
                    description=(
                        f"**{entry['manga']}** — Chapitre **{entry['chapter']}** est maintenant sorti !\n\n"
                        "Bonne lecture à tous ! 🎉"
                    ),
                    color=0xFFD700,
                    timestamp=datetime.datetime.now(datetime.timezone.utc)
                )
                notif.set_footer(text="LanorTrad • Sortie")

                # Ping le rôle manga si configuré
                role_id = MANGA_ROLES.get(entry["manga"])
                mention = f"<@&{role_id}>" if role_id else ""
                await planning_channel.send(mention, embed=notif)

    # ─────────────────────────────────────────────────────────────────────────
    # COMMANDE - MODIFIER LA DATE
    # ─────────────────────────────────────────────────────────────────────────

    @commands.command(name="planning_date", aliases=["planning_reschedule"])
    @commands.has_any_role(*TASK_ROLES)
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def update_date(self, ctx, planning_id: str, new_date: str):
        """
        Change la date de sortie prévue.

        Usage: !planning_date <id> <AAAA-MM-JJ>
        """
        entry = planning_data.get(planning_id)
        if not entry:
            matches = [pid for pid in planning_data if planning_id.lower() in pid.lower()]
            if len(matches) == 1:
                planning_id = matches[0]
                entry = planning_data[planning_id]
            else:
                await ctx.send(f"❌ Entrée `{planning_id}` introuvable.", delete_after=10)
                return

        try:
            datetime.datetime.strptime(new_date, "%Y-%m-%d")
        except ValueError:
            await ctx.send("❌ Format invalide. Utilisez `AAAA-MM-JJ`.", delete_after=10)
            return

        old_date = entry["date"]
        entry["date"] = new_date
        entry["last_updated"] = datetime.datetime.now().isoformat()
        sauvegarder_planning()

        emoji = get_manga_emoji(entry["manga"])
        embed = discord.Embed(
            title=f"{emoji} Date modifiée",
            description=(
                f"**{entry['manga']}** — Ch. **{entry['chapter']}**\n\n"
                f"📅 Ancienne date : ~~{format_date_fr(old_date)}~~\n"
                f"📆 Nouvelle date : **{format_date_fr(new_date)}**"
            ),
            color=COLORS["warning"]
        )
        embed.set_footer(text=f"Par {ctx.author.name}")
        await ctx.send(embed=embed)

        await self.update_planning_message()

    # ─────────────────────────────────────────────────────────────────────────
    # COMMANDE - SUPPRIMER DU PLANNING
    # ─────────────────────────────────────────────────────────────────────────

    @commands.command(name="planning_remove", aliases=["planning_delete", "del_planning"])
    @commands.has_any_role(*ADMIN_ROLES)
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def remove_planning(self, ctx, planning_id: str):
        """Supprime une entrée du planning."""
        if planning_id in planning_data:
            entry = planning_data.pop(planning_id)
            sauvegarder_planning()

            emoji = get_manga_emoji(entry["manga"])
            embed = discord.Embed(
                title="🗑️ Entrée supprimée",
                description=f"{emoji} **{entry['manga']}** — Ch. **{entry['chapter']}** retiré du planning.",
                color=COLORS["error"]
            )
            embed.set_footer(text=f"Par {ctx.author.name}")
            await ctx.send(embed=embed)

            await self.update_planning_message()
        else:
            await ctx.send(f"❌ Entrée `{planning_id}` introuvable.", delete_after=10)

    # ─────────────────────────────────────────────────────────────────────────
    # COMMANDE - POSTER/RAFRAÎCHIR LE PLANNING DANS LE CANAL
    # ─────────────────────────────────────────────────────────────────────────

    @commands.command(name="planning_post", aliases=["planning_refresh"])
    @commands.has_any_role(*TASK_ROLES)
    @commands.cooldown(1, 30, commands.BucketType.user)
    async def post_planning(self, ctx):
        """Poste ou rafraîchit le planning dans le canal dédié."""
        channel = self.bot.get_channel(PLANNING_CHANNEL_ID)
        if not channel:
            await ctx.send(f"❌ Canal de planning introuvable (ID: {PLANNING_CHANNEL_ID}).", delete_after=10)
            return

        embed = build_planning_embed()
        msg = await channel.send(embed=embed)
        self.planning_message_id = msg.id

        await ctx.send(f"✅ Planning posté/rafraîchi dans {channel.mention} !")

    # ─────────────────────────────────────────────────────────────────────────
    # COMMANDE - PROCHAINE SORTIE
    # ─────────────────────────────────────────────────────────────────────────

    @commands.command(name="next_release", aliases=["prochaine_sortie", "next"])
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def next_release(self, ctx):
        """Affiche la prochaine sortie prévue."""
        today = datetime.datetime.now().date()

        upcoming = []
        for pid, pdata in planning_data.items():
            if pdata.get("status") == "sorti":
                continue
            try:
                date = datetime.datetime.strptime(pdata["date"], "%Y-%m-%d").date()
                if date >= today:
                    upcoming.append((pid, pdata, date))
            except:
                pass

        if not upcoming:
            await ctx.send("📅 Aucune sortie à venir pour le moment.")
            return

        upcoming.sort(key=lambda x: x[2])
        pid, pdata, date = upcoming[0]

        delta = (date - today).days
        emoji = get_manga_emoji(pdata["manga"])
        status_info = STATUTS.get(pdata.get("status", "prevu"), STATUTS["prevu"])

        embed = discord.Embed(
            title=f"📅 Prochaine sortie",
            color=status_info["color"],
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )
        embed.add_field(name=f"{emoji} Manga", value=pdata["manga"], inline=True)
        embed.add_field(name="📖 Chapitre", value=pdata["chapter"], inline=True)
        embed.add_field(name=f"{status_info['emoji']} Statut", value=status_info["label"], inline=True)
        embed.add_field(name="📆 Date", value=format_date_fr(pdata["date"]), inline=True)

        if delta == 0:
            embed.add_field(name="⏳ Countdown", value="**AUJOURD'HUI** 🔥", inline=True)
        elif delta == 1:
            embed.add_field(name="⏳ Countdown", value="**Demain** ⏰", inline=True)
        else:
            embed.add_field(name="⏳ Countdown", value=f"Dans **{delta}** jour(s)", inline=True)

        if pdata.get("notes"):
            embed.add_field(name="📝 Notes", value=pdata["notes"], inline=False)

        # Autres sorties à venir
        if len(upcoming) > 1:
            others = []
            for _, op, od in upcoming[1:5]:
                oem = get_manga_emoji(op["manga"])
                others.append(f"{oem} **{op['manga']}** Ch.{op['chapter']} — {format_date_fr(op['date'])}")
            embed.add_field(name="📋 Aussi à venir", value="\n".join(others), inline=False)

        embed.set_footer(text="LanorTrad • Planning")
        await ctx.send(embed=embed)


async def setup(bot):
    """Setup pour discord.py 2.0+"""
    await bot.add_cog(PlanningSystem(bot))
    logging.info("✅ Cog PlanningSystem chargé avec succès")
