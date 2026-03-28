# planning.py
# ===============================================================================
# SYSTEME DE PLANNING - Sorties de chapitres a venir
# Un message PAR MANGA PAR MOIS dans #planning.
# A chaque modification -> le message est supprime et recree (remonte + ping).
# ===============================================================================

import discord
from discord.ext import commands, tasks
from discord.ui import View, Button, Select
import datetime
import logging
import asyncio
import unicodedata
import pytz
import calendar as cal_module

from config import ADMIN_ROLES, COLORS, MANGA_EMOJIS, MANGA_ROLES, TASK_ROLES, DATA_DIR
from utils import load_json, save_json, save_with_meta, paginate, get_manga_emoji, safe_api_call

logger = logging.getLogger(__name__)

# ===============================================================================
# CONFIGURATION
# ===============================================================================

PLANNING_CHANNEL_ID = 1332363693174034472

PLANNING_FILE = f"{DATA_DIR}/planning.json"
PLANNING_META_FILE = f"{DATA_DIR}/planning_meta.json"
PLANNING_MESSAGES_FILE = f"{DATA_DIR}/planning_messages.json"

# Donnees en memoire
planning_data = {}       # {"id": {manga, chapter, date, status, notes, teaser, ...}}
planning_messages = {}   # {"2026-03_catenaccio": msg_id, "2026-03_tougen_anki": msg_id, ...}

# Statuts (ordre = workflow de production)
STATUTS = {
    "prevu":      {"emoji": "📅", "label": "Prévu",           "color": 0x5865F2},
    "en_cours":   {"emoji": "🔄", "label": "En cours",        "color": 0xF39C12},
    "trad_done":  {"emoji": "🌍", "label": "Trad terminée",   "color": 0x9B59B6},
    "edit_done":  {"emoji": "✏️", "label": "Edit terminé",    "color": 0xE67E22},
    "check_done": {"emoji": "✅", "label": "Check terminé",   "color": 0x57F287},
    "pret":       {"emoji": "🚀", "label": "Prêt à sortir",   "color": 0x1ABC9C},
    "sorti":      {"emoji": "📢", "label": "Sorti",           "color": 0x2ECC71},
    "retarde":    {"emoji": "⚠️", "label": "Retardé",         "color": 0xED4245},
}

JOURS_FR = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
JOURS_FR_COURT = ["LUN", "MAR", "MER", "JEU", "VEN", "SAM", "DIM"]
MOIS_FR = ["", "Janvier", "Février", "Mars", "Avril", "Mai", "Juin",
           "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"]

# Couleurs theme
CALENDAR_COLOR = 0x5865F2
ACCENT_COLOR = 0x7c3aed
RELEASE_COLOR = 0x10b981

# Auto-nettoyage : supprimer les entrees "sorti" depuis plus de X jours
AUTO_CLEANUP_DAYS = 30


# ===============================================================================
# UTILITAIRES
# ===============================================================================

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


def get_manga_key(manga_name):
    """Normalise le nom manga pour cle: 'Tougen Anki' -> 'tougen_anki'"""
    return manga_name.lower().replace(" ", "_")


def get_message_key(month_key, manga_name):
    """Cle unique par mois+manga: '2026-03_catenaccio'"""
    return f"{month_key}_{get_manga_key(manga_name)}"


def resolve_manga_role(manga_name):
    for name, role_id in MANGA_ROLES.items():
        if name.lower() == manga_name.lower():
            return role_id
    return None


def normalize_str(s):
    """Retire les accents et met en minuscule pour la recherche fuzzy."""
    s = s.lower().strip()
    return ''.join(
        c for c in unicodedata.normalize('NFD', s)
        if unicodedata.category(c) != 'Mn'
    )


def get_progress_bar(status_key):
    stages = ["prevu", "en_cours", "trad_done", "edit_done", "check_done", "pret", "sorti"]
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


def get_overall_progress(entries):
    """Calcule la progression globale de toutes les entrees d'un manga/mois."""
    stages = ["prevu", "en_cours", "trad_done", "edit_done", "check_done", "pret", "sorti"]
    if not entries:
        return 0
    total_pct = 0
    for e in entries:
        status = e.get("status", "prevu")
        if status == "retarde":
            continue
        try:
            idx = stages.index(status)
        except ValueError:
            idx = 0
        total_pct += int((idx / (len(stages) - 1)) * 100)
    return total_pct // len(entries)


# ===============================================================================
# CONSTRUCTION DU CALENDRIER VISUEL (pour un seul manga)
# ===============================================================================

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


# ===============================================================================
# CONSTRUCTION DE L'EMBED PAR MANGA PAR MOIS
# ===============================================================================

def build_manga_month_embed(year, month, manga_name, manga_entries):
    """
    Construit l'embed pour UN manga sur UN mois.
    Retourne une LISTE d'embeds (1 si ca tient, plusieurs si overflow).
    """
    now = datetime.datetime.now()
    today = now.date()
    mois_nom = MOIS_FR[month]
    emoji = get_manga_emoji(manga_name)

    # Trier par date
    manga_entries.sort(key=lambda e: e["date"])

    # Collecter les jours de sortie
    releases_by_day = {}
    for e in manga_entries:
        try:
            d = datetime.datetime.strptime(e["date"], "%Y-%m-%d").date()
            day = d.day
            if day not in releases_by_day:
                releases_by_day[day] = []
            releases_by_day[day].append(e)
        except:
            continue

    # -- Couleur dynamique selon progression globale --
    overall = get_overall_progress(manga_entries)
    if overall == 100:
        color = 0x2ECC71   # Tout sorti -> vert
    elif overall >= 60:
        color = 0x1ABC9C   # Bien avance -> turquoise
    elif overall >= 20:
        color = 0xF39C12   # En cours -> orange
    else:
        color = CALENDAR_COLOR  # Prevu -> bleu

    title = f"{emoji}  Planning {mois_nom} {year} — {manga_name}"

    # -- Calendrier --
    cal_text = build_calendar_grid(year, month, releases_by_day, today)
    header_text = f"```\n{cal_text}\n```\n"
    header_text += "```\n[XX] = Aujourd'hui    ★ = Jour de sortie\n```\n"

    # -- Stats --
    total = len(manga_entries)
    sorti = sum(1 for e in manga_entries if e.get("status") == "sorti")
    header_text += f"**{total}** chapitre(s)"
    if sorti:
        header_text += f" · **{sorti}** publié(s)"
    header_text += f" · Progression globale : **{overall}%**\n"

    # Barre globale
    filled = overall * 20 // 100
    bar = "█" * filled + "░" * (20 - filled)
    header_text += f"`{bar}` {overall}%\n"
    header_text += "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"

    # -- Details par jour --
    day_blocks = []
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

        block = f"{day_header}\n"
        for entry in releases_by_day[day]:
            status_info = STATUTS.get(entry.get("status", "prevu"), STATUTS["prevu"])
            block += f"> 📖 **Chapitre {entry['chapter']}**\n"
            block += f"> {status_info['emoji']} `{status_info['label']}`  {get_progress_bar(entry.get('status', 'prevu'))}\n"
            if entry.get("teaser"):
                block += f"> 🔮 ||{entry['teaser']}||\n"
            if entry.get("notes"):
                block += f"> 📝 *{entry['notes']}*\n"
        block += "\n"
        day_blocks.append(block)

    # -- Assemblage avec gestion overflow multi-embeds --
    embeds = []
    current_desc = header_text
    max_len = 3900  # Marge de securite sous 4096

    for block in day_blocks:
        if len(current_desc) + len(block) > max_len:
            # Flush l'embed courant
            embed = discord.Embed(color=color, description=current_desc)
            if not embeds:
                embed.title = title
            else:
                embed.title = f"{title} (suite)"
            embed.set_footer(text="LanorTrad · Dernière mise à jour")
            embed.timestamp = now
            embeds.append(embed)
            current_desc = ""
        current_desc += block

    # Dernier embed
    if current_desc.strip():
        embed = discord.Embed(color=color, description=current_desc)
        if not embeds:
            embed.title = title
        else:
            embed.title = f"{title} (suite)"
        embed.set_footer(text="LanorTrad · Dernière mise à jour")
        embed.timestamp = now
        embeds.append(embed)

    return embeds


# ===============================================================================
# VUE SELECT STATUT (admin, menu deroulant)
# ===============================================================================

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

        # Delete + recreate le message du manga/mois
        cog = interaction.client.get_cog("PlanningSystem")
        if cog:
            await cog.refresh_manga_message(entry["manga"], get_month_key(entry["date"]))


class PlanningStatusView(View):
    def __init__(self, planning_id: str):
        super().__init__(timeout=None)
        self.add_item(PlanningStatusSelect(planning_id))


# ===============================================================================
# VUE CONFIRMATION SUPPRESSION
# ===============================================================================

class ConfirmDeleteView(View):
    def __init__(self, planning_id: str, author_id: int):
        super().__init__(timeout=30)
        self.planning_id = planning_id
        self.author_id = author_id
        self.confirmed = None

    @discord.ui.button(label="Confirmer", style=discord.ButtonStyle.danger, emoji="🗑️")
    async def confirm(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("❌ Seul l'auteur peut confirmer.", ephemeral=True)
            return
        self.confirmed = True
        self.stop()
        await interaction.response.defer()

    @discord.ui.button(label="Annuler", style=discord.ButtonStyle.secondary, emoji="❌")
    async def cancel(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("❌ Seul l'auteur peut annuler.", ephemeral=True)
            return
        self.confirmed = False
        self.stop()
        await interaction.response.defer()


# ===============================================================================
# COG PRINCIPAL
# ===============================================================================

class PlanningSystem(commands.Cog):
    """Système de planning : 1 message par manga par mois, auto-update."""

    def __init__(self, bot):
        self.bot = bot
        charger_planning()
        self.daily_planning_check.start()
        for pid in planning_data:
            bot.add_view(PlanningStatusView(pid))

    def cog_unload(self):
        self.daily_planning_check.cancel()
        sauvegarder_planning()

    # -------------------------------------------------------------------------
    # COEUR : Delete + Recreate le message d'un manga pour un mois
    # -------------------------------------------------------------------------

    async def refresh_manga_message(self, manga_name, month_key, silent=False):
        """
        Supprime l'ancien message et en cree un nouveau (remonte dans le channel).
        Mentionne le role manga pour notifier.
        """
        channel = self.bot.get_channel(PLANNING_CHANNEL_ID)
        if not channel:
            logger.warning(f"Canal planning {PLANNING_CHANNEL_ID} introuvable.")
            return

        try:
            year, month = int(month_key[:4]), int(month_key[5:7])
        except:
            logger.error(f"month_key invalide: {month_key}")
            return

        msg_key = get_message_key(month_key, manga_name)

        # Collecter les entrees de ce manga pour ce mois
        manga_entries = []
        for pid, pdata in planning_data.items():
            if (get_manga_key(pdata["manga"]) == get_manga_key(manga_name)
                    and pdata["date"].startswith(month_key)):
                manga_entries.append(pdata)

        # -- Supprimer l'ancien message --
        old_msg_id = planning_messages.get(msg_key)
        if old_msg_id:
            try:
                old_msg = await channel.fetch_message(old_msg_id)
                await safe_api_call(old_msg.delete)
                logger.info(f"📅 Ancien message supprimé pour {msg_key}")
            except discord.NotFound:
                pass
            except Exception as e:
                logger.error(f"Erreur suppression message {msg_key}: {e}")
            del planning_messages[msg_key]
            await asyncio.sleep(1)  # Pause entre delete et send

        # Plus d'entrees -> on ne recree rien
        if not manga_entries:
            sauvegarder_planning()
            return

        # -- Construire les embeds --
        embeds = build_manga_month_embed(year, month, manga_name, manga_entries)

        # -- Ping du role manga --
        role_id = resolve_manga_role(manga_name)
        role_mention = f"<@&{role_id}>" if role_id and not silent else ""

        # -- Envoyer (nouveau message -> remonte en bas du channel) --
        msg = await safe_api_call(
            channel.send,
            role_mention, embeds=embeds,
            allowed_mentions=discord.AllowedMentions(roles=True)
        )
        if msg:
            planning_messages[msg_key] = msg.id
        sauvegarder_planning()
        logger.info(f"📅 Nouveau message planning pour {msg_key} (ID: {msg.id if msg else 'ECHEC'})")

    # -------------------------------------------------------------------------
    # RAFRAICHIR TOUS LES MESSAGES D'UN MOIS
    # -------------------------------------------------------------------------

    async def refresh_all_for_month(self, month_key, silent=True):
        """Rafraichit tous les messages manga d'un mois."""
        mangas_in_month = set()
        for pdata in planning_data.values():
            if pdata["date"].startswith(month_key):
                mangas_in_month.add(pdata["manga"])

        for manga in sorted(mangas_in_month):
            await self.refresh_manga_message(manga, month_key, silent=silent)
            await asyncio.sleep(3)  # Rate limit - 3s entre chaque manga

    # -------------------------------------------------------------------------
    # AUTO-NETTOYAGE : Supprimer les entrees "sorti" depuis > 30 jours
    # -------------------------------------------------------------------------

    async def _auto_cleanup(self):
        """Supprime les entrees 'sorti' dont la date est passee depuis AUTO_CLEANUP_DAYS."""
        today = datetime.date.today()
        to_remove = []
        affected_months = set()

        for pid, pdata in planning_data.items():
            if pdata.get("status") != "sorti":
                continue
            try:
                entry_date = datetime.datetime.strptime(pdata["date"], "%Y-%m-%d").date()
            except:
                continue
            if (today - entry_date).days > AUTO_CLEANUP_DAYS:
                to_remove.append(pid)
                affected_months.add((pdata["manga"], get_month_key(pdata["date"])))

        if not to_remove:
            return 0

        for pid in to_remove:
            planning_data.pop(pid, None)

        sauvegarder_planning()
        logger.info(f"🧹 Auto-nettoyage planning : {len(to_remove)} entrée(s) archivée(s)")

        # Refresh les messages affectes
        for manga, mk in affected_months:
            await self.refresh_manga_message(manga, mk, silent=True)
            await asyncio.sleep(3)

        return len(to_remove)

    # -------------------------------------------------------------------------
    # LOOP - VERIFICATION QUOTIDIENNE
    # -------------------------------------------------------------------------

    @tasks.loop(hours=1)
    async def daily_planning_check(self):
        tz_paris = pytz.timezone('Europe/Paris')
        now = datetime.datetime.now(tz_paris)

        # A minuit -> refresh silencieux + auto-nettoyage
        if now.hour == 0:
            if not planning_data:
                return
            current_month_key = now.date().isoformat()[:7]
            await self.refresh_all_for_month(current_month_key, silent=True)
            # Si on est le 1er du mois, refresh aussi le mois precedent
            if now.day == 1:
                prev = (now.date() - datetime.timedelta(days=1))
                prev_key = prev.isoformat()[:7]
                await self.refresh_all_for_month(prev_key, silent=True)
            # Auto-nettoyage des vieilles entrees
            await self._auto_cleanup()
            return

        # A 9h -> refresh + notifications
        if now.hour != 9:
            return

        today_str = now.date().isoformat()

        channel = self.bot.get_channel(PLANNING_CHANNEL_ID)
        if not channel:
            return

        # Rafraichir les messages du mois courant (silencieux, pas de ping)
        current_month_key = today_str[:7]
        await self.refresh_all_for_month(current_month_key, silent=True)

        # Notifications sorties du jour (message separe)
        today_releases = []
        for pid, pdata in planning_data.items():
            if pdata.get("status") == "sorti":
                continue
            if pdata["date"] == today_str:
                today_releases.append(pdata)

        if today_releases:
            # Grouper par manga
            by_manga = {}
            for r in today_releases:
                by_manga.setdefault(r["manga"], []).append(r)

            for manga, releases in by_manga.items():
                emoji = get_manga_emoji(manga)
                role_id = resolve_manga_role(manga)
                mention = f"<@&{role_id}>" if role_id else ""

                embed = discord.Embed(title="🔥  SORTIE(S) DU JOUR", color=0xFF6B6B, timestamp=now)
                desc = ""
                for r in releases:
                    status = STATUTS.get(r.get("status", "prevu"), STATUTS["prevu"])
                    desc += f"> {emoji} **{manga}** · Ch. **{r['chapter']}**\n"
                    desc += f"> {status['emoji']} `{status['label']}`\n\n"
                embed.description = desc
                embed.set_footer(text="LanorTrad · Planning")
                await safe_api_call(channel.send, mention, embed=embed)
                await asyncio.sleep(2)  # Délai entre chaque notification manga

    @daily_planning_check.before_loop
    async def before_daily_check(self):
        await self.bot.wait_until_ready()

    # -------------------------------------------------------------------------
    # COMMANDE CONSULTATION - !planning [manga]
    # -------------------------------------------------------------------------

    @commands.command(name="planning")
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def show_planning(self, ctx, *, manga_filter: str = None):
        """
        📅 Affiche le planning du mois en cours.

        Usage: !planning [nom du manga]
        Sans argument : affiche tous les mangas du mois.
        Avec argument : filtre par manga.
        """
        if not planning_data:
            await ctx.send("📅 Aucune sortie planifiée.")
            return

        now = datetime.datetime.now()
        current_month_key = now.date().isoformat()[:7]
        year, month = now.year, now.month

        # Filtrer les entrees du mois courant
        entries_by_manga = {}
        for pid, pdata in planning_data.items():
            if not pdata["date"].startswith(current_month_key):
                continue
            if manga_filter:
                if normalize_str(manga_filter) not in normalize_str(pdata["manga"]):
                    continue
            entries_by_manga.setdefault(pdata["manga"], []).append(pdata)

        if not entries_by_manga:
            if manga_filter:
                await ctx.send(f"📅 Aucune sortie trouvée pour **{manga_filter}** ce mois-ci.")
            else:
                await ctx.send(f"📅 Aucune sortie planifiée pour {MOIS_FR[month]} {year}.")
            return

        # Construire les embeds pour chaque manga
        all_embeds = []
        for manga_name in sorted(entries_by_manga.keys()):
            manga_entries = entries_by_manga[manga_name]
            embeds = build_manga_month_embed(year, month, manga_name, manga_entries)
            all_embeds.extend(embeds)

        # Envoyer (paginé si > 1 embed)
        if len(all_embeds) == 1:
            await ctx.send(embed=all_embeds[0])
        else:
            await paginate(ctx, all_embeds)

    # -------------------------------------------------------------------------
    # COMMANDE ADMIN - AJOUTER AU PLANNING
    # -------------------------------------------------------------------------

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

            # Delete + recreate le message du manga/mois dans #planning
            month_key = get_month_key(date_str)
            await self.refresh_manga_message(manga.strip(), month_key)

    async def _add_interactive(self, ctx):
        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel

        try:
            # Etape 1 : Manga
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

            # Etape 2 : Chapitre(s)
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

            # Etape 3 : Date
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

            # Etape 4 : Notes
            embed = discord.Embed(
                title="📝  Notes (optionnel)",
                description="Ajoutez des **notes** ou tapez `non` pour passer.",
                color=CALENDAR_COLOR
            )
            embed.set_footer(text="Étape 4/5")
            await ctx.send(embed=embed)
            msg = await self.bot.wait_for('message', check=check, timeout=60)
            notes = msg.content.strip() if msg.content.strip().lower() != "non" else None

            # Etape 5 : Teaser
            embed = discord.Embed(
                title="🔮  Teaser / Spoil (optionnel)",
                description="Tapez un **teaser** (caché sous spoiler) ou `non` pour passer.",
                color=0x9B59B6
            )
            embed.set_footer(text="Étape 5/5")
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

                # Delete + recreate dans #planning
                month_key = get_month_key(date_str)
                await self.refresh_manga_message(manga, month_key)

        except asyncio.TimeoutError:
            await ctx.send("⏰ Temps écoulé. Ajout annulé.", delete_after=10)

    async def _finalize_add(self, ctx, manga, chapter, date_str, notes=None, teaser=None):
        """Finalise l'ajout. Retourne True si ajoute."""
        planning_id = f"{get_manga_key(manga)}_{chapter}"

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

    # -------------------------------------------------------------------------
    # COMMANDE ADMIN - MODIFIER LE STATUT
    # -------------------------------------------------------------------------

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

        # Delete + recreate le message du manga/mois (avec ping)
        month_key = get_month_key(entry["date"])
        await self.refresh_manga_message(entry["manga"], month_key)

    # -------------------------------------------------------------------------
    # COMMANDE ADMIN - BATCH STATUS (modifier plusieurs d'un coup)
    # -------------------------------------------------------------------------

    @commands.command(name="planning_batch_status", aliases=["batch_status"])
    @commands.has_any_role(*TASK_ROLES)
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def batch_status(self, ctx, new_status: str, manga_or_id: str = None, *, rest: str = None):
        """
        ⚙️ Change le statut de plusieurs entrées d'un coup.

        Usage par manga + chapitres :
          !planning_batch_status <statut> "Manga" <chapitres>
          Ex: !planning_batch_status en_cours "Catenaccio" 47-54
          Ex: !planning_batch_status sorti "Catenaccio" 47,48,50

        Usage par IDs :
          !planning_batch_status <statut> <id1> <id2> ...
          Ex: !planning_batch_status sorti catenaccio_47 catenaccio_48

        Statuts: prevu, en_cours, trad_done, edit_done, check_done, pret, sorti, retarde
        """
        if not manga_or_id:
            await ctx.send(
                "❌ Usage :\n"
                "> `!planning_batch_status <statut> \"Manga\" <chapitres>`\n"
                "> `!planning_batch_status <statut> <id1> <id2> ...`\n\n"
                "Exemples :\n"
                "> `!planning_batch_status en_cours \"Catenaccio\" 47-54`\n"
                "> `!planning_batch_status sorti catenaccio_47 catenaccio_48`",
                delete_after=20
            )
            return

        new_status = new_status.lower()
        if new_status not in STATUTS:
            statuts_list = ", ".join([f"`{k}`" for k in STATUTS.keys()])
            await ctx.send(f"❌ Statut invalide. Choix : {statuts_list}", delete_after=15)
            return

        # Determine si c'est le mode "manga + chapitres" ou le mode "IDs"
        planning_ids = []
        chapters_input = rest.strip() if rest else ""

        # Tente de parser comme chapitres (ex: "47-54", "47,48,50")
        parsed_chapters = parse_chapters(chapters_input) if chapters_input else []

        if parsed_chapters:
            # Mode manga + chapitres : construire les IDs a partir du nom manga
            manga_key = get_manga_key(manga_or_id)
            for ch in parsed_chapters:
                planning_ids.append(f"{manga_key}_{ch}")
        else:
            # Mode IDs classique : tous les args sont des IDs
            planning_ids.append(manga_or_id)
            if rest:
                planning_ids.extend(rest.split())

        updated = []
        not_found = []
        months_to_refresh = set()

        for pid in planning_ids:
            entry, resolved_id = self._resolve_entry(pid)
            if not entry:
                not_found.append(pid)
                continue

            entry["status"] = new_status
            entry["last_updated"] = datetime.datetime.now().isoformat()
            entry["updated_by"] = ctx.author.id
            updated.append(f"{entry['manga']} Ch.{entry['chapter']}")
            months_to_refresh.add((entry["manga"], get_month_key(entry["date"])))

        if updated:
            sauvegarder_planning()

        status_info = STATUTS[new_status]
        emoji = get_manga_emoji(manga_or_id) if parsed_chapters else ""
        embed = discord.Embed(
            title=f"{status_info['emoji']}  Batch — {len(updated)} entrée(s) → {status_info['label']}",
            color=status_info["color"]
        )
        desc = ""
        if updated:
            # Regrouper par manga pour un affichage compact
            chapters_by_manga = {}
            for u in updated:
                parts = u.rsplit(" Ch.", 1)
                m = parts[0]
                ch = parts[1] if len(parts) > 1 else "?"
                chapters_by_manga.setdefault(m, []).append(ch)
            for m, chs in chapters_by_manga.items():
                m_emoji = get_manga_emoji(m)
                desc += f"> {m_emoji} **{m}** — Ch. {', '.join(chs)}\n"
            desc += f"\n{status_info['emoji']} **{status_info['label']}**  `{get_progress_bar(new_status)}`\n"
        if not_found:
            desc += f"\n**Non trouvé(s) ({len(not_found)}) :**\n"
            desc += "\n".join([f"> ❌ `{nf}`" for nf in not_found]) + "\n"
        embed.description = desc
        embed.set_footer(text=f"Par {ctx.author.name}")
        await ctx.send(embed=embed)

        # Refresh les messages affectes
        for manga, mk in months_to_refresh:
            await self.refresh_manga_message(manga, mk)
            await asyncio.sleep(2)

    # -------------------------------------------------------------------------
    # COMMANDE ADMIN - MODIFIER LA DATE
    # -------------------------------------------------------------------------

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
        new_month_key = get_month_key(new_date)

        entry["date"] = new_date
        entry["last_updated"] = datetime.datetime.now().isoformat()
        sauvegarder_planning()

        emoji = get_manga_emoji(entry["manga"])
        embed = discord.Embed(title="📆  Date modifiée", color=COLORS["warning"])
        embed.description = (
            f"## {emoji} {entry['manga']} · Ch. {entry['chapter']}\n\n"
            f"~~{format_date_fr(old_date)}~~ → **{format_date_fr(new_date)}**"
        )
        embed.set_footer(text=f"Par {ctx.author.name}")
        await ctx.send(embed=embed)

        # Refresh les deux mois si changement
        await self.refresh_manga_message(entry["manga"], old_month_key)
        if old_month_key != new_month_key:
            await self.refresh_manga_message(entry["manga"], new_month_key)

    # -------------------------------------------------------------------------
    # COMMANDE ADMIN - AJOUTER/MODIFIER UN TEASER
    # -------------------------------------------------------------------------

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
            sauvegarder_planning()
            embed = discord.Embed(title="🗑️  Teaser supprimé",
                                  description=f"{emoji} **{entry['manga']}** · Ch. **{entry['chapter']}**",
                                  color=COLORS["warning"])
            await ctx.send(embed=embed)
        else:
            entry["teaser"] = teaser_text
            sauvegarder_planning()
            embed = discord.Embed(title="🔮  Teaser mis à jour !",
                                  description=f"{emoji} **{entry['manga']}** · Ch. **{entry['chapter']}**\n\n> ||{teaser_text}||",
                                  color=0x9B59B6)
            await ctx.send(embed=embed)

        entry["last_updated"] = datetime.datetime.now().isoformat()
        sauvegarder_planning()

        month_key = get_month_key(entry["date"])
        await self.refresh_manga_message(entry["manga"], month_key)

    # -------------------------------------------------------------------------
    # COMMANDE ADMIN - MODIFIER LES NOTES
    # -------------------------------------------------------------------------

    @commands.command(name="planning_notes", aliases=["planning_note"])
    @commands.has_any_role(*TASK_ROLES)
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def set_notes(self, ctx, planning_id: str = None, *, notes_text: str = None):
        """⚙️ Ajoute/modifie les notes. Usage: !planning_notes <id> <texte>"""
        if not planning_id:
            embed = discord.Embed(
                title="📝  Notes",
                description="**Usage :**\n> `!planning_notes <id> <texte>`\n> `!planning_notes <id> supprimer`",
                color=CALENDAR_COLOR
            )
            await ctx.send(embed=embed, delete_after=15)
            return

        entry, planning_id = self._resolve_entry(planning_id)
        if not entry:
            await ctx.send(f"❌ Entrée `{planning_id}` introuvable.", delete_after=10)
            return

        emoji = get_manga_emoji(entry["manga"])

        if not notes_text:
            current = entry.get("notes", "")
            embed = discord.Embed(title=f"📝  {entry['manga']} — Ch. {entry['chapter']}", color=CALENDAR_COLOR)
            embed.description = f"**Notes actuelles :**\n> {current}" if current else "*Aucune note.*"
            await ctx.send(embed=embed)
            return

        if notes_text.lower() in ["supprimer", "delete", "remove", "none"]:
            entry["notes"] = ""
            sauvegarder_planning()
            embed = discord.Embed(title="🗑️  Notes supprimées",
                                  description=f"{emoji} **{entry['manga']}** · Ch. **{entry['chapter']}**",
                                  color=COLORS["warning"])
            await ctx.send(embed=embed)
        else:
            entry["notes"] = notes_text
            sauvegarder_planning()
            embed = discord.Embed(title="📝  Notes mises à jour !",
                                  description=f"{emoji} **{entry['manga']}** · Ch. **{entry['chapter']}**\n\n> {notes_text}",
                                  color=CALENDAR_COLOR)
            await ctx.send(embed=embed)

        entry["last_updated"] = datetime.datetime.now().isoformat()
        sauvegarder_planning()

        month_key = get_month_key(entry["date"])
        await self.refresh_manga_message(entry["manga"], month_key)

    # -------------------------------------------------------------------------
    # COMMANDE ADMIN - SUPPRIMER (avec confirmation)
    # -------------------------------------------------------------------------

    @commands.command(name="planning_remove", aliases=["planning_delete", "del_planning"])
    @commands.has_any_role(*ADMIN_ROLES)
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def remove_planning(self, ctx, planning_id: str):
        """⚙️ Supprime une entrée du planning (avec confirmation)."""
        entry, planning_id = self._resolve_entry(planning_id)
        if not entry:
            await ctx.send(f"❌ Entrée `{planning_id}` introuvable.", delete_after=10)
            return

        emoji = get_manga_emoji(entry["manga"])
        status_info = STATUTS.get(entry.get("status", "prevu"), STATUTS["prevu"])

        # Demander confirmation
        confirm_embed = discord.Embed(
            title="⚠️  Confirmer la suppression ?",
            description=(
                f"{emoji} **{entry['manga']}** · Ch. **{entry['chapter']}**\n"
                f"> {status_info['emoji']} `{status_info['label']}` · 📆 {format_date_court(entry['date'])}\n"
                f"> 🆔 `{planning_id}`\n\n"
                f"**Cette action est irréversible.**"
            ),
            color=COLORS["error"]
        )
        view = ConfirmDeleteView(planning_id, ctx.author.id)
        confirm_msg = await ctx.send(embed=confirm_embed, view=view)

        # Attendre la reponse
        await view.wait()

        if view.confirmed is None:
            # Timeout
            embed = discord.Embed(title="⏰ Suppression annulée", description="Temps écoulé.", color=COLORS["warning"])
            await confirm_msg.edit(embed=embed, view=None)
            return

        if not view.confirmed:
            embed = discord.Embed(title="❌ Suppression annulée", color=COLORS["info"])
            await confirm_msg.edit(embed=embed, view=None)
            return

        # Confirme -> supprimer
        manga_name = entry["manga"]
        month_key = get_month_key(entry["date"])
        planning_data.pop(planning_id)
        sauvegarder_planning()

        embed = discord.Embed(
            title="🗑️  Entrée supprimée",
            description=f"{emoji} **{manga_name}** · Ch. **{entry['chapter']}** retiré.",
            color=COLORS["error"]
        )
        embed.set_footer(text=f"Par {ctx.author.name}")
        await confirm_msg.edit(embed=embed, view=None)

        # Refresh (va supprimer le message si plus d'entrees pour ce manga/mois)
        await self.refresh_manga_message(manga_name, month_key)

    # -------------------------------------------------------------------------
    # COMMANDE ADMIN - FORCER LE RAFRAICHISSEMENT
    # -------------------------------------------------------------------------

    @commands.command(name="planning_post", aliases=["planning_refresh"])
    @commands.has_any_role(*TASK_ROLES)
    @commands.cooldown(1, 30, commands.BucketType.user)
    async def post_planning(self, ctx):
        """⚙️ Force la recréation de tous les messages planning."""
        # Collecter tous les combos mois+manga
        combos = set()
        for pdata in planning_data.values():
            mk = get_month_key(pdata["date"])
            combos.add((pdata["manga"], mk))

        if not combos:
            await ctx.send("📅 Aucune donnée de planning.", delete_after=10)
            return

        for manga, mk in sorted(combos, key=lambda x: x[1]):
            await self.refresh_manga_message(manga, mk, silent=True)
            await asyncio.sleep(2)

        channel = self.bot.get_channel(PLANNING_CHANNEL_ID)
        await ctx.send(f"✅ Planning rafraîchi dans {channel.mention} ! ({len(combos)} message(s))")

    # -------------------------------------------------------------------------
    # COMMANDE ADMIN - PLANNING COMPLET (liste avec IDs pour gestion)
    # -------------------------------------------------------------------------

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
                if pdata.get("notes"):
                    desc += f"> 📝 *{pdata['notes']}*\n"
                desc += "\n"
            embed.description = desc
            embed.set_footer(text=f"Page {len(pages)+1} · {len(entries)} entrée(s)")
            pages.append(embed)

        if len(pages) == 1:
            await ctx.send(embed=pages[0])
        else:
            await paginate(ctx, pages)

    # -------------------------------------------------------------------------
    # UTILITAIRE : Resoudre un ID (exact, partiel, fuzzy)
    # -------------------------------------------------------------------------

    def _resolve_entry(self, planning_id):
        """
        Retourne (entry, resolved_id) ou (None, original_id).
        Supporte :
        - ID exact : "tougen_anki_220"
        - Partiel : "tougen_220" ou "220" (si unique)
        - Nom manga seul : "tougen" (si un seul resultat)
        - Tolerant accents/casse
        """
        # Exact match
        entry = planning_data.get(planning_id)
        if entry:
            return entry, planning_id

        # Recherche partielle insensible casse
        normalized = normalize_str(planning_id)
        matches = [
            pid for pid in planning_data
            if normalized in normalize_str(pid)
        ]
        if len(matches) == 1:
            return planning_data[matches[0]], matches[0]

        # Recherche par nom manga (si l'input match un nom de manga)
        manga_matches = [
            pid for pid, pdata in planning_data.items()
            if normalized in normalize_str(pdata["manga"])
        ]
        if len(manga_matches) == 1:
            return planning_data[manga_matches[0]], manga_matches[0]

        # Recherche par numero de chapitre seul
        if planning_id.isdigit():
            chapter_matches = [
                pid for pid, pdata in planning_data.items()
                if pdata["chapter"] == planning_id
            ]
            if len(chapter_matches) == 1:
                return planning_data[chapter_matches[0]], chapter_matches[0]

        return None, planning_id


async def setup(bot):
    await bot.add_cog(PlanningSystem(bot))
    logging.info("✅ Cog PlanningSystem chargé avec succès")
