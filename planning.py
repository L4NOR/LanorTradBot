# planning.py
# ═══════════════════════════════════════════════════════════════════════════════
# SYSTÈME DE PLANNING - Sorties de chapitres à venir
# Un message par mois dans #planning, auto-update à chaque modification.
# Les users n'ont qu'à regarder le channel, aucune commande nécessaire.
# ═══════════════════════════════════════════════════════════════════════════════

import discord
from discord.ext import commands, tasks
from discord.ui import View, Button, Select
import datetime
import logging
import asyncio
import pytz
import calendar as cal_module

from config import ADMIN_ROLES, COLORS, MANGA_EMOJIS, MANGA_ROLES, TASK_ROLES, DATA_DIR
from utils import load_json, save_json, save_with_meta, paginate, get_manga_emoji

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

PLANNING_CHANNEL_ID = 1332363693174034472

PLANNING_FILE = f"{DATA_DIR}/planning.json"
PLANNING_META_FILE = f"{DATA_DIR}/planning_meta.json"
PLANNING_MESSAGES_FILE = f"{DATA_DIR}/planning_messages.json"

# Données en mémoire
planning_data = {}       # {"id": {manga, chapter, date, status, notes, teaser, ...}}
planning_messages = {}   # {"2026-03": message_id, "2026-04": message_id, ...}

# Statuts
STATUTS = {
    "prevu":      {"emoji": "📅", "label": "Prévu",           "color": 0x5865F2},
    "en_cours":   {"emoji": "🔄", "label": "En cours",        "color": 0xF39C12},
    "trad_done":  {"emoji": "🌍", "label": "Trad terminée",   "color": 0x9B59B6},
    "check_done": {"emoji": "✅", "label": "Check terminé",   "color": 0x57F287},
    "pret":       {"emoji": "🚀", "label": "Prêt à sortir",   "color": 0x1ABC9C},
    "sorti":      {"emoji": "📢", "label": "Sorti",           "color": 0x2ECC71},
    "retarde":    {"emoji": "⚠️", "label": "Retardé",         "color": 0xED4245},
}

JOURS_FR = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
JOURS_FR_COURT = ["LUN", "MAR", "MER", "JEU", "VEN", "SAM", "DIM"]
MOIS_FR = ["", "Janvier", "Février", "Mars", "Avril", "Mai", "Juin",
           "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"]

# Couleurs thème
CALENDAR_COLOR = 0x5865F2
ACCENT_COLOR = 0x7c3aed
RELEASE_COLOR = 0x10b981


# ═══════════════════════════════════════════════════════════════════════════════
# UTILITAIRES
# ═══════════════════════════════════════════════════════════════════════════════

def parse_chapters(chapter_input):
    """Parse: '220', '220,221,222', '220-222', '220,223,225-227'"""
    chapters = []
    parts = chapter_input.replace(" ", "").split(",")
    for part in parts:
        if "-" in part:
            bounds = part.split("-", 1)
            if len(bounds) == 2 and bounds[0].isdigit() and bounds[1].isdigit():
                start, end = int(bounds[0]), int(bounds[1])
                if start > end:
                    start, end = end, start
                if end - start > 50:
                    continue
                chapters.extend(str(i) for i in range(start, end + 1))
            else:
                chapters.append(part)
        else:
            if part:
                chapters.append(part)
    return chapters


def charger_planning():
    global planning_data, planning_messages
    planning_data = load_json(PLANNING_FILE, {})
    planning_messages = load_json(PLANNING_MESSAGES_FILE, {})
    logger.info(f"📅 {len(planning_data)} entrée(s) de planning chargée(s)")
    logger.info(f"📅 {len(planning_messages)} message(s) de planning trackés")


def sauvegarder_planning():
    save_with_meta(PLANNING_FILE, planning_data, PLANNING_META_FILE)
    save_json(PLANNING_MESSAGES_FILE, planning_messages)


def format_date_fr(date_str):
    try:
        dt = datetime.datetime.strptime(date_str, "%Y-%m-%d")
        return f"{JOURS_FR[dt.weekday()]} {dt.day} {MOIS_FR[dt.month]} {dt.year}"
    except:
        return date_str


def format_date_court(date_str):
    try:
        dt = datetime.datetime.strptime(date_str, "%Y-%m-%d")
        return f"{JOURS_FR_COURT[dt.weekday()]} {dt.day} {MOIS_FR[dt.month]}"
    except:
        return date_str


def get_month_key(date_str):
    """Retourne '2026-03' depuis '2026-03-14'."""
    return date_str[:7]


def resolve_manga_role(manga_name):
    for name, role_id in MANGA_ROLES.items():
        if name.lower() == manga_name.lower():
            return role_id
    return None


def get_progress_bar(status_key):
    stages = ["prevu", "en_cours", "trad_done", "check_done", "pret", "sorti"]
    if status_key == "retarde":
        return "⚠️ ░░░░░░░░ Retardé"
    try:
        idx = stages.index(status_key)
    except ValueError:
        idx = 0
    total = len(stages) - 1
    filled = int((idx / total) * 8)
    bar = "█" * filled + "░" * (8 - filled)
    pct = int((idx / total) * 100)
    return f"{bar} {pct}%"


# ═══════════════════════════════════════════════════════════════════════════════
# CONSTRUCTION DU CALENDRIER VISUEL
# ═══════════════════════════════════════════════════════════════════════════════

def build_calendar_grid(year, month, releases_by_day, today):
    cal = cal_module.Calendar(firstweekday=0)
    weeks = cal.monthdayscalendar(year, month)

    lines = []
    header = "  ".join(f" {j} " for j in JOURS_FR_COURT)
    lines.append(header)
    lines.append("─" * len(header))

    for week in weeks:
        row = []
        for day in week:
            if day == 0:
                row.append("  ·  ")
            elif day == today.day and month == today.month and year == today.year:
                row.append(f"[{day:>2}]★" if day in releases_by_day else f"[{day:>2}] ")
            elif day in releases_by_day:
                row.append(f" {day:>2} ★")
            else:
                row.append(f" {day:>2}  ")
        lines.append("  ".join(row))

    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════════
# CONSTRUCTION DE L'EMBED MENSUEL (le message unique par mois)
# ═══════════════════════════════════════════════════════════════════════════════

def build_month_embed(year, month):
    """
    Construit l'embed complet pour un mois donné.
    Calendrier + détails de chaque sortie, le tout dans un seul embed.
    """
    now = datetime.datetime.now()
    today = now.date()
    mois_nom = MOIS_FR[month]

    # ── Collecter les entrées du mois ──
    releases_by_day = {}
    month_entries = []

    for pid, pdata in planning_data.items():
        try:
            date = datetime.datetime.strptime(pdata["date"], "%Y-%m-%d").date()
            if date.year == year and date.month == month:
                day = date.day
                if day not in releases_by_day:
                    releases_by_day[day] = []
                releases_by_day[day].append({
                    "id": pid,
                    "manga": pdata["manga"],
                    "chapter": pdata["chapter"],
                    "status": pdata.get("status", "prevu"),
                    "notes": pdata.get("notes", ""),
                    "teaser": pdata.get("teaser", ""),
                    "date": date,
                })
                month_entries.append((pid, pdata, date))
        except:
            continue

    month_entries.sort(key=lambda x: x[2])

    # ── Embed principal ──
    embed = discord.Embed(color=CALENDAR_COLOR)
    embed.title = f"📅  Planning — {mois_nom} {year}"

    # ── Partie 1 : Calendrier ──
    cal_text = build_calendar_grid(year, month, releases_by_day, today)
    desc = f"```\n{cal_text}\n```\n"
    desc += "```\n[XX] = Aujourd'hui    ★ = Jour de sortie\n```\n"

    # ── Stats rapides ──
    total = len(month_entries)
    sorti_count = sum(1 for _, p, _ in month_entries if p.get("status") == "sorti")
    en_cours_count = sum(1 for _, p, _ in month_entries if p.get("status") not in ["sorti", "prevu"])

    if total > 0:
        stats_parts = [f"**{total}** sortie(s)"]
        if sorti_count:
            stats_parts.append(f"**{sorti_count}** publiée(s)")
        if en_cours_count:
            stats_parts.append(f"**{en_cours_count}** en cours")
        desc += " · ".join(stats_parts) + "\n"

    desc += "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"

    # ── Partie 2 : Détails par jour ──
    if releases_by_day:
        for day in sorted(releases_by_day.keys()):
            date_obj = datetime.date(year, month, day)
            jour_nom = JOURS_FR[date_obj.weekday()]
            delta = (date_obj - today).days

            # Header du jour
            if delta == 0:
                day_header = f"🔥 **{jour_nom} {day} {mois_nom}** — AUJOURD'HUI"
            elif delta == 1:
                day_header = f"⏰ **{jour_nom} {day} {mois_nom}** — Demain"
            elif delta == -1:
                day_header = f"📆 **{jour_nom} {day} {mois_nom}** — Hier"
            elif delta < -1:
                day_header = f"📆 ~~{jour_nom} {day} {mois_nom}~~"
            elif delta <= 7:
                day_header = f"📆 **{jour_nom} {day} {mois_nom}** — J-{delta}"
            else:
                day_header = f"📆 **{jour_nom} {day} {mois_nom}**"

            desc += f"{day_header}\n"

            for entry in releases_by_day[day]:
                emoji = get_manga_emoji(entry["manga"])
                status_info = STATUTS.get(entry["status"], STATUTS["prevu"])

                desc += f"> {emoji} **{entry['manga']}** · Ch. **{entry['chapter']}**\n"
                desc += f"> {status_info['emoji']} `{status_info['label']}`  {get_progress_bar(entry['status'])}\n"

                if entry.get("teaser"):
                    desc += f"> 🔮 ||{entry['teaser']}||\n"
                if entry.get("notes"):
                    desc += f"> 📝 *{entry['notes']}*\n"

            desc += "\n"
    else:
        desc += "*Aucune sortie planifiée pour ce mois.*\n"

    # ── Sécurité limite 4096 chars ──
    if len(desc) > 4000:
        desc = desc[:3990] + "\n*...et plus*"

    embed.description = desc

    # ── Timestamp de dernière MAJ ──
    embed.set_footer(text=f"LanorTrad · Dernière mise à jour")
    embed.timestamp = now

    return embed


# ═══════════════════════════════════════════════════════════════════════════════
# VUE DE MISE À JOUR DU STATUT (pour les boutons select admin)
# ═══════════════════════════════════════════════════════════════════════════════

class PlanningStatusSelect(Select):
    def __init__(self, planning_id: str):
        self.planning_id = planning_id
        options = [
            discord.SelectOption(
                label=info["label"], value=key, emoji=info["emoji"],
                description=f"Marquer comme {info['label'].lower()}"
            )
            for key, info in STATUTS.items()
        ]
        super().__init__(placeholder="📊 Changer le statut...", options=options,
                         custom_id=f"planning_status_{planning_id}")

    async def callback(self, interaction: discord.Interaction):
        user_roles = [role.id for role in interaction.user.roles]
        if not any(role in user_roles for role in TASK_ROLES):
            await interaction.response.send_message("❌ Permissions insuffisantes.", ephemeral=True)
            return

        new_status = self.values[0]
        entry = planning_data.get(self.planning_id)
        if not entry:
            await interaction.response.send_message("❌ Entrée introuvable.", ephemeral=True)
            return

        entry["status"] = new_status
        entry["last_updated"] = datetime.datetime.now().isoformat()
        entry["updated_by"] = interaction.user.id
        sauvegarder_planning()

        status_info = STATUTS[new_status]
        await interaction.response.send_message(
            f"{status_info['emoji']} **{entry['manga']} Ch.{entry['chapter']}** → **{status_info['label']}**",
            ephemeral=True
        )

        cog = interaction.client.get_cog("PlanningSystem")
        if cog:
            month_key = get_month_key(entry["date"])
            await cog.refresh_month_message(month_key)


class PlanningStatusView(View):
    def __init__(self, planning_id: str):
        super().__init__(timeout=None)
        self.add_item(PlanningStatusSelect(planning_id))


# ═══════════════════════════════════════════════════════════════════════════════
# COG PRINCIPAL
# ═══════════════════════════════════════════════════════════════════════════════

class PlanningSystem(commands.Cog):
    """Système de planning auto-update dans #planning."""

    def __init__(self, bot):
        self.bot = bot
        charger_planning()
        self.daily_planning_check.start()
        # Restaurer les views persistantes
        for pid in planning_data:
            bot.add_view(PlanningStatusView(pid))

    def cog_unload(self):
        self.daily_planning_check.cancel()
        sauvegarder_planning()

    # ─────────────────────────────────────────────────────────────────────────
    # CŒUR : Rafraîchir/créer le message d'un mois dans #planning
    # ─────────────────────────────────────────────────────────────────────────

    async def refresh_month_message(self, month_key):
        """
        Met à jour (ou crée) le message embed d'un mois dans #planning.
        month_key: "2026-03"
        """
        channel = self.bot.get_channel(PLANNING_CHANNEL_ID)
        if not channel:
            logger.warning(f"Canal planning {PLANNING_CHANNEL_ID} introuvable.")
            return

        # Parser le month_key
        try:
            year, month = int(month_key[:4]), int(month_key[5:7])
        except:
            logger.error(f"month_key invalide: {month_key}")
            return

        # Vérifier s'il y a des entrées pour ce mois
        has_entries = any(
            pdata["date"].startswith(month_key)
            for pdata in planning_data.values()
        )

        if not has_entries:
            # Plus d'entrées → supprimer le message si il existe
            msg_id = planning_messages.get(month_key)
            if msg_id:
                try:
                    msg = await channel.fetch_message(msg_id)
                    await msg.delete()
                except:
                    pass
                del planning_messages[month_key]
                sauvegarder_planning()
            return

        # Construire l'embed
        embed = build_month_embed(year, month)

        # Essayer d'éditer le message existant
        msg_id = planning_messages.get(month_key)
        if msg_id:
            try:
                msg = await channel.fetch_message(msg_id)
                await msg.edit(embed=embed)
                logger.info(f"📅 Message planning {month_key} mis à jour (ID: {msg_id})")
                return
            except discord.NotFound:
                logger.info(f"📅 Message planning {month_key} introuvable, recréation...")
                del planning_messages[month_key]
            except Exception as e:
                logger.error(f"Erreur édition message planning: {e}")

        # Créer un nouveau message
        msg = await channel.send(embed=embed)
        planning_messages[month_key] = msg.id
        sauvegarder_planning()
        logger.info(f"📅 Nouveau message planning créé pour {month_key} (ID: {msg.id})")

    # ─────────────────────────────────────────────────────────────────────────
    # LOOP - VÉRIFICATION QUOTIDIENNE (9h Paris)
    # ─────────────────────────────────────────────────────────────────────────

    @tasks.loop(hours=1)
    async def daily_planning_check(self):
        tz_paris = pytz.timezone('Europe/Paris')
        now = datetime.datetime.now(tz_paris)

        if now.hour != 9:
            return

        today_str = now.date().isoformat()
        tomorrow_str = (now.date() + datetime.timedelta(days=1)).isoformat()

        channel = self.bot.get_channel(PLANNING_CHANNEL_ID)
        if not channel:
            return

        # Rafraîchir le message du mois courant (met à jour "AUJOURD'HUI")
        current_month_key = today_str[:7]
        await self.refresh_month_message(current_month_key)

        # Notifications sorties du jour
        today_releases = []
        tomorrow_releases = []

        for pid, pdata in planning_data.items():
            if pdata.get("status") == "sorti":
                continue
            if pdata["date"] == today_str:
                today_releases.append(pdata)
            elif pdata["date"] == tomorrow_str:
                tomorrow_releases.append(pdata)

        if today_releases:
            embed = discord.Embed(title="🔥  SORTIES DU JOUR", color=0xFF6B6B, timestamp=now)
            desc = ""
            mentions = []
            for r in today_releases:
                emoji = get_manga_emoji(r["manga"])
                status = STATUTS.get(r.get("status", "prevu"), STATUTS["prevu"])
                desc += f"> {emoji} **{r['manga']}** · Ch. **{r['chapter']}**\n"
                desc += f"> {status['emoji']} `{status['label']}`\n\n"
                role_id = resolve_manga_role(r["manga"])
                if role_id:
                    mentions.append(f"<@&{role_id}>")
            embed.description = desc
            embed.set_footer(text="LanorTrad · Planning")
            await channel.send(" ".join(set(mentions)) if mentions else "", embed=embed)

        if tomorrow_releases:
            embed = discord.Embed(title="⏰  Sorties prévues DEMAIN", color=COLORS["warning"], timestamp=now)
            desc = ""
            for r in tomorrow_releases:
                emoji = get_manga_emoji(r["manga"])
                desc += f"> {emoji} **{r['manga']}** · Ch. **{r['chapter']}**\n"
                desc += f"> 📆 {format_date_fr(r['date'])}\n\n"
            embed.description = desc
            embed.set_footer(text="LanorTrad · Planning")
            await channel.send(embed=embed)

    @daily_planning_check.before_loop
    async def before_daily_check(self):
        await self.bot.wait_until_ready()

    # ─────────────────────────────────────────────────────────────────────────
    # COMMANDE ADMIN - AJOUTER AU PLANNING
    # ─────────────────────────────────────────────────────────────────────────

    @commands.command(name="planning_add", aliases=["add_planning"])
    @commands.has_any_role(*TASK_ROLES)
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def add_planning(self, ctx, manga: str = None, chapter: str = None,
                           date: str = None, *, notes: str = None):
        """
        ⚙️ Ajoute une ou plusieurs sorties au planning.

        Usage rapide: !planning_add "Tougen Anki" 220-222 2026-03-20 Notes optionnelles
        Usage interactif: !planning_add (sans arguments)
        """
        if manga and chapter and date:
            await self._add_quick(ctx, manga, chapter, date, notes)
        else:
            await self._add_interactive(ctx)

    async def _add_quick(self, ctx, manga, chapter, date_str, notes=None):
        try:
            datetime.datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            await ctx.send("❌ Format de date invalide. Utilisez `AAAA-MM-JJ`.", delete_after=10)
            return

        chapters = parse_chapters(chapter)
        if not chapters:
            await ctx.send("❌ Numéro(s) de chapitre invalide(s).", delete_after=10)
            return

        added = []
        for ch in chapters:
            result = await self._finalize_add(ctx, manga.strip(), ch, date_str, notes)
            if result:
                added.append(ch)

        if added:
            emoji = get_manga_emoji(manga)
            role_id = resolve_manga_role(manga)
            role_mention = f"<@&{role_id}>" if role_id else ""

            embed = discord.Embed(title="✅  Ajouté au planning !", color=RELEASE_COLOR)
            chapters_display = ", ".join(added)
            desc = (
                f"## {emoji} {manga}\n"
                f"**Chapitre(s) :** {chapters_display}\n"
                f"**Date :** 📆 {format_date_fr(date_str)}\n"
                f"**Statut :** 📅 Prévu\n"
            )
            if notes:
                desc += f"**Notes :** 📝 *{notes}*\n"
            if role_mention:
                desc += f"\n**Rôle notifié :** {role_mention}"
            embed.description = desc
            embed.set_footer(text=f"Ajouté par {ctx.author.name} · {len(added)} chapitre(s)")
            await ctx.send(embed=embed)

            # Auto-update le message du mois dans #planning
            month_key = get_month_key(date_str)
            await self.refresh_month_message(month_key)

            # Notification ping dans #planning
            planning_channel = self.bot.get_channel(PLANNING_CHANNEL_ID)
            if planning_channel and role_mention:
                notif = discord.Embed(
                    title=f"📅  Nouvelle(s) sortie(s) planifiée(s) !",
                    color=CALENDAR_COLOR,
                )
                notif.description = (
                    f"{emoji} **{manga}** · Ch. **{chapters_display}**\n"
                    f"📆 {format_date_fr(date_str)}"
                )
                if notes:
                    notif.description += f"\n📝 *{notes}*"
                notif.set_footer(text=f"Ajouté par {ctx.author.name}")
                await planning_channel.send(role_mention, embed=notif)

    async def _add_interactive(self, ctx):
        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel

        try:
            # Étape 1 : Manga
            manga_list = "\n".join([f"  {v} `{k}`" for k, v in MANGA_EMOJIS.items()])
            embed = discord.Embed(
                title="📅  Ajouter au Planning",
                description=f"**Quel manga ?**\n\n{manga_list}\n\n*Ou tapez un nom personnalisé.*",
                color=CALENDAR_COLOR
            )
            embed.set_footer(text="Étape 1/4 · Tapez le nom du manga")
            await ctx.send(embed=embed)
            msg = await self.bot.wait_for('message', check=check, timeout=60)
            manga = msg.content.strip()

            # Étape 2 : Chapitre(s)
            embed = discord.Embed(
                title="📖  Numéro(s) de chapitre",
                description=(
                    "**Formats acceptés :**\n"
                    "> `220` — Un seul chapitre\n"
                    "> `220,221,222` — Plusieurs chapitres\n"
                    "> `220-222` — Plage de chapitres\n"
                    "> `220,223,225-227` — Mix"
                ),
                color=CALENDAR_COLOR
            )
            embed.set_footer(text="Étape 2/4 · Tapez le(s) numéro(s)")
            await ctx.send(embed=embed)
            msg = await self.bot.wait_for('message', check=check, timeout=60)
            chapters = parse_chapters(msg.content.strip())
            if not chapters:
                await ctx.send("❌ Numéro(s) invalide(s).", delete_after=10)
                return

            # Étape 3 : Date
            embed = discord.Embed(
                title="📆  Date de sortie prévue",
                description="**Format :** `AAAA-MM-JJ`\n*Exemple : `2026-03-25`*",
                color=CALENDAR_COLOR
            )
            embed.set_footer(text="Étape 3/4 · Tapez la date")
            await ctx.send(embed=embed)
            msg = await self.bot.wait_for('message', check=check, timeout=60)
            date_str = msg.content.strip()
            try:
                datetime.datetime.strptime(date_str, "%Y-%m-%d")
            except ValueError:
                await ctx.send("❌ Format invalide.", delete_after=10)
                return

            # Étape 4 : Notes
            embed = discord.Embed(
                title="📝  Notes & Teaser (optionnel)",
                description="Ajoutez des **notes** ou tapez `non` pour passer.",
                color=CALENDAR_COLOR
            )
            embed.set_footer(text="Étape 4/4")
            await ctx.send(embed=embed)
            msg = await self.bot.wait_for('message', check=check, timeout=60)
            notes = msg.content.strip() if msg.content.strip().lower() != "non" else None

            # Teaser
            embed = discord.Embed(
                title="🔮  Teaser / Spoil (optionnel)",
                description="Tapez un **teaser** (caché sous spoiler) ou `non` pour passer.",
                color=0x9B59B6
            )
            await ctx.send(embed=embed)
            msg = await self.bot.wait_for('message', check=check, timeout=60)
            teaser = msg.content.strip() if msg.content.strip().lower() != "non" else None

            # Finaliser
            added = []
            for ch in chapters:
                result = await self._finalize_add(ctx, manga, ch, date_str, notes, teaser)
                if result:
                    added.append(ch)

            if added:
                emoji = get_manga_emoji(manga)
                role_id = resolve_manga_role(manga)
                role_mention = f"<@&{role_id}>" if role_id else ""

                embed = discord.Embed(title="✅  Ajouté au planning !", color=RELEASE_COLOR)
                chapters_display = ", ".join(added)
                desc = (
                    f"## {emoji} {manga}\n"
                    f"**Chapitre(s) :** {chapters_display}\n"
                    f"**Date :** 📆 {format_date_fr(date_str)}\n"
                    f"**Statut :** 📅 Prévu\n"
                )
                if notes:
                    desc += f"**Notes :** 📝 *{notes}*\n"
                if teaser:
                    desc += f"**Teaser :** 🔮 ||{teaser}||\n"
                if role_mention:
                    desc += f"\n**Rôle notifié :** {role_mention}"
                embed.description = desc
                embed.set_footer(text=f"Ajouté par {ctx.author.name} · {len(added)} chapitre(s)")
                await ctx.send(embed=embed)

                # Auto-update #planning
                month_key = get_month_key(date_str)
                await self.refresh_month_message(month_key)

                # Ping dans #planning
                planning_channel = self.bot.get_channel(PLANNING_CHANNEL_ID)
                if planning_channel and role_mention:
                    notif = discord.Embed(
                        title=f"📅  Nouvelle(s) sortie(s) planifiée(s) !",
                        color=CALENDAR_COLOR,
                    )
                    notif.description = f"{emoji} **{manga}** · Ch. **{chapters_display}**\n📆 {format_date_fr(date_str)}"
                    notif.set_footer(text=f"Ajouté par {ctx.author.name}")
                    await planning_channel.send(role_mention, embed=notif)

        except asyncio.TimeoutError:
            await ctx.send("⏰ Temps écoulé. Ajout annulé.", delete_after=10)

    async def _finalize_add(self, ctx, manga, chapter, date_str, notes=None, teaser=None):
        """Finalise l'ajout. Retourne True si ajouté."""
        planning_id = f"{manga.lower().replace(' ', '_')}_{chapter}"

        if planning_id in planning_data:
            return False

        planning_data[planning_id] = {
            "manga": manga,
            "chapter": chapter,
            "date": date_str,
            "status": "prevu",
            "notes": notes or "",
            "teaser": teaser or "",
            "added_by": ctx.author.id,
            "created_at": datetime.datetime.now().isoformat(),
            "last_updated": datetime.datetime.now().isoformat(),
        }
        sauvegarder_planning()
        self.bot.add_view(PlanningStatusView(planning_id))
        return True

    # ─────────────────────────────────────────────────────────────────────────
    # COMMANDE ADMIN - MODIFIER LE STATUT
    # ─────────────────────────────────────────────────────────────────────────

    @commands.command(name="planning_status", aliases=["planning_update"])
    @commands.has_any_role(*TASK_ROLES)
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def update_status(self, ctx, planning_id: str, new_status: str = None):
        """
        ⚙️ Met à jour le statut d'une entrée.

        Usage: !planning_status <id> [statut]
        Statuts: prevu, en_cours, trad_done, check_done, pret, sorti, retarde
        """
        entry, planning_id = self._resolve_entry(planning_id)
        if not entry:
            await ctx.send(f"❌ Entrée `{planning_id}` introuvable.", delete_after=10)
            return

        if not new_status:
            view = PlanningStatusView(planning_id)
            emoji = get_manga_emoji(entry["manga"])
            current = STATUTS.get(entry.get("status", "prevu"), STATUTS["prevu"])
            embed = discord.Embed(
                title=f"{emoji}  {entry['manga']} — Ch. {entry['chapter']}",
                description=f"Statut actuel : {current['emoji']} **{current['label']}**\n`{get_progress_bar(entry.get('status', 'prevu'))}`",
                color=CALENDAR_COLOR
            )
            await ctx.send(embed=embed, view=view)
            return

        new_status = new_status.lower()
        if new_status not in STATUTS:
            statuts_list = "\n".join([f"> `{k}` — {v['emoji']} {v['label']}" for k, v in STATUTS.items()])
            embed = discord.Embed(title="❌ Statut invalide", description=f"**Choix :**\n{statuts_list}", color=COLORS["error"])
            await ctx.send(embed=embed, delete_after=15)
            return

        old_status = entry.get("status", "prevu")
        entry["status"] = new_status
        entry["last_updated"] = datetime.datetime.now().isoformat()
        entry["updated_by"] = ctx.author.id
        sauvegarder_planning()

        status_info = STATUTS[new_status]
        old_info = STATUTS.get(old_status, STATUTS["prevu"])
        emoji = get_manga_emoji(entry["manga"])

        embed = discord.Embed(title=f"{status_info['emoji']}  Statut mis à jour", color=status_info["color"])
        embed.description = (
            f"## {emoji} {entry['manga']} · Ch. {entry['chapter']}\n\n"
            f"{old_info['emoji']} ~~{old_info['label']}~~ → {status_info['emoji']} **{status_info['label']}**\n\n"
            f"`{get_progress_bar(new_status)}`"
        )
        embed.set_footer(text=f"Par {ctx.author.name}")
        await ctx.send(embed=embed)

        # Auto-update le message du mois
        month_key = get_month_key(entry["date"])
        await self.refresh_month_message(month_key)

        # Si "sorti" → notification spéciale avec ping
        if new_status == "sorti":
            planning_channel = self.bot.get_channel(PLANNING_CHANNEL_ID)
            if planning_channel:
                role_id = resolve_manga_role(entry["manga"])
                role_mention = f"<@&{role_id}>" if role_id else ""
                notif = discord.Embed(
                    title=f"📢  NOUVEAU CHAPITRE DISPONIBLE !",
                    color=0xFFD700,
                    timestamp=datetime.datetime.now(datetime.timezone.utc)
                )
                notif.description = (
                    f"## {emoji} {entry['manga']}\n"
                    f"### Chapitre {entry['chapter']}\n\n"
                    "Bonne lecture à tous ! 🎉"
                )
                notif.set_footer(text="LanorTrad · Sortie")
                await planning_channel.send(role_mention, embed=notif)

    # ─────────────────────────────────────────────────────────────────────────
    # COMMANDE ADMIN - MODIFIER LA DATE
    # ─────────────────────────────────────────────────────────────────────────

    @commands.command(name="planning_date", aliases=["planning_reschedule"])
    @commands.has_any_role(*TASK_ROLES)
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def update_date(self, ctx, planning_id: str, new_date: str):
        """⚙️ Change la date de sortie. Usage: !planning_date <id> <AAAA-MM-JJ>"""
        entry, planning_id = self._resolve_entry(planning_id)
        if not entry:
            await ctx.send(f"❌ Entrée `{planning_id}` introuvable.", delete_after=10)
            return

        try:
            datetime.datetime.strptime(new_date, "%Y-%m-%d")
        except ValueError:
            await ctx.send("❌ Format invalide. Utilisez `AAAA-MM-JJ`.", delete_after=10)
            return

        old_date = entry["date"]
        old_month_key = get_month_key(old_date)
        entry["date"] = new_date
        entry["last_updated"] = datetime.datetime.now().isoformat()
        sauvegarder_planning()

        emoji = get_manga_emoji(entry["manga"])
        embed = discord.Embed(title=f"📆  Date modifiée", color=COLORS["warning"])
        embed.description = (
            f"## {emoji} {entry['manga']} · Ch. {entry['chapter']}\n\n"
            f"~~{format_date_fr(old_date)}~~ → **{format_date_fr(new_date)}**"
        )
        embed.set_footer(text=f"Par {ctx.author.name}")
        await ctx.send(embed=embed)

        # Rafraîchir l'ancien ET le nouveau mois
        new_month_key = get_month_key(new_date)
        await self.refresh_month_message(old_month_key)
        if old_month_key != new_month_key:
            await self.refresh_month_message(new_month_key)

    # ─────────────────────────────────────────────────────────────────────────
    # COMMANDE ADMIN - AJOUTER/MODIFIER UN TEASER
    # ─────────────────────────────────────────────────────────────────────────

    @commands.command(name="planning_teaser", aliases=["planning_spoil", "teaser"])
    @commands.has_any_role(*TASK_ROLES)
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def set_teaser(self, ctx, planning_id: str = None, *, teaser_text: str = None):
        """⚙️ Ajoute/modifie le teaser. Usage: !planning_teaser <id> <texte>"""
        if not planning_id:
            embed = discord.Embed(
                title="🔮  Teaser / Spoil",
                description="**Usage :**\n> `!planning_teaser <id> <texte>`\n> `!planning_teaser <id> supprimer`",
                color=0x9B59B6
            )
            await ctx.send(embed=embed, delete_after=15)
            return

        entry, planning_id = self._resolve_entry(planning_id)
        if not entry:
            await ctx.send(f"❌ Entrée `{planning_id}` introuvable.", delete_after=10)
            return

        emoji = get_manga_emoji(entry["manga"])

        if not teaser_text:
            current = entry.get("teaser", "")
            embed = discord.Embed(title=f"🔮  {entry['manga']} — Ch. {entry['chapter']}", color=0x9B59B6)
            embed.description = f"**Teaser actuel :**\n> ||{current}||" if current else "*Aucun teaser.*"
            await ctx.send(embed=embed)
            return

        if teaser_text.lower() in ["supprimer", "delete", "remove", "none"]:
            entry["teaser"] = ""
            entry["last_updated"] = datetime.datetime.now().isoformat()
            sauvegarder_planning()
            embed = discord.Embed(title="🗑️  Teaser supprimé",
                                  description=f"{emoji} **{entry['manga']}** · Ch. **{entry['chapter']}**",
                                  color=COLORS["warning"])
            await ctx.send(embed=embed)
        else:
            entry["teaser"] = teaser_text
            entry["last_updated"] = datetime.datetime.now().isoformat()
            sauvegarder_planning()
            embed = discord.Embed(title="🔮  Teaser mis à jour !",
                                  description=f"{emoji} **{entry['manga']}** · Ch. **{entry['chapter']}**\n\n> ||{teaser_text}||",
                                  color=0x9B59B6)
            await ctx.send(embed=embed)

        month_key = get_month_key(entry["date"])
        await self.refresh_month_message(month_key)

    # ─────────────────────────────────────────────────────────────────────────
    # COMMANDE ADMIN - SUPPRIMER
    # ─────────────────────────────────────────────────────────────────────────

    @commands.command(name="planning_remove", aliases=["planning_delete", "del_planning"])
    @commands.has_any_role(*ADMIN_ROLES)
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def remove_planning(self, ctx, planning_id: str):
        """⚙️ Supprime une entrée du planning."""
        entry, planning_id = self._resolve_entry(planning_id)
        if not entry:
            await ctx.send(f"❌ Entrée `{planning_id}` introuvable.", delete_after=10)
            return

        month_key = get_month_key(entry["date"])
        planning_data.pop(planning_id)
        sauvegarder_planning()

        emoji = get_manga_emoji(entry["manga"])
        embed = discord.Embed(
            title="🗑️  Entrée supprimée",
            description=f"{emoji} **{entry['manga']}** · Ch. **{entry['chapter']}** retiré.",
            color=COLORS["error"]
        )
        embed.set_footer(text=f"Par {ctx.author.name}")
        await ctx.send(embed=embed)

        await self.refresh_month_message(month_key)

    # ─────────────────────────────────────────────────────────────────────────
    # COMMANDE ADMIN - POSTER/FORCER LE RAFRAÎCHISSEMENT
    # ─────────────────────────────────────────────────────────────────────────

    @commands.command(name="planning_post", aliases=["planning_refresh"])
    @commands.has_any_role(*TASK_ROLES)
    @commands.cooldown(1, 30, commands.BucketType.user)
    async def post_planning(self, ctx):
        """⚙️ Force le rafraîchissement de tous les messages planning."""
        # Trouver tous les mois qui ont des entrées
        month_keys = set()
        for pdata in planning_data.values():
            month_keys.add(get_month_key(pdata["date"]))

        if not month_keys:
            await ctx.send("📅 Aucune donnée de planning.", delete_after=10)
            return

        for mk in sorted(month_keys):
            await self.refresh_month_message(mk)

        channel = self.bot.get_channel(PLANNING_CHANNEL_ID)
        await ctx.send(f"✅ Planning rafraîchi dans {channel.mention} ! ({len(month_keys)} mois)")

    # ─────────────────────────────────────────────────────────────────────────
    # COMMANDE ADMIN - PLANNING COMPLET (liste avec IDs pour gestion)
    # ─────────────────────────────────────────────────────────────────────────

    @commands.command(name="planning_full", aliases=["planning_all", "planning_list"])
    @commands.has_any_role(*TASK_ROLES)
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def show_full_planning(self, ctx):
        """⚙️ Affiche toutes les entrées avec leurs IDs (pour gestion)."""
        if not planning_data:
            await ctx.send("📅 Aucune sortie planifiée.")
            return

        entries = sorted(planning_data.items(), key=lambda x: x[1].get("date", ""), reverse=True)
        pages = []
        per_page = 5

        for i in range(0, len(entries), per_page):
            page_entries = entries[i:i + per_page]
            embed = discord.Embed(title="📋  Planning — Administration", color=ACCENT_COLOR)
            desc = ""
            for pid, pdata in page_entries:
                emoji = get_manga_emoji(pdata["manga"])
                status_info = STATUTS.get(pdata.get("status", "prevu"), STATUTS["prevu"])
                desc += (
                    f"**{emoji} {pdata['manga']}** · Ch. **{pdata['chapter']}**\n"
                    f"> {status_info['emoji']} `{status_info['label']}` · 📆 {format_date_court(pdata['date'])}\n"
                    f"> 🆔 `{pid}`\n"
                )
                if pdata.get("teaser"):
                    desc += f"> 🔮 ||{pdata['teaser']}||\n"
                desc += "\n"
            embed.description = desc
            embed.set_footer(text=f"Page {len(pages)+1} · {len(entries)} entrée(s)")
            pages.append(embed)

        if len(pages) == 1:
            await ctx.send(embed=pages[0])
        else:
            await paginate(ctx, pages)

    # ─────────────────────────────────────────────────────────────────────────
    # UTILITAIRE : Résoudre un ID (exact ou partiel)
    # ─────────────────────────────────────────────────────────────────────────

    def _resolve_entry(self, planning_id):
        """Retourne (entry, resolved_id) ou (None, original_id)."""
        entry = planning_data.get(planning_id)
        if entry:
            return entry, planning_id

        matches = [pid for pid in planning_data if planning_id.lower() in pid.lower()]
        if len(matches) == 1:
            return planning_data[matches[0]], matches[0]

        return None, planning_id


async def setup(bot):
    await bot.add_cog(PlanningSystem(bot))
    logging.info("✅ Cog PlanningSystem chargé avec succès")
