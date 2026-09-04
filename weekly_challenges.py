# weekly_challenges.py
# ═══════════════════════════════════════════════════════════════════════════════
# DÉFIS HEBDOMADAIRES — 3 challenges/semaine, reset chaque lundi 00h
# ═══════════════════════════════════════════════════════════════════════════════
# Chaque semaine, le bot tire 3 défis dans un pool de templates. Les joueurs
# gagnent un bonus XP en complétant chaque défi, plus un bonus "perfect week"
# si les 3 sont validés. Les complétions sont archivées dans l'historique pour
# alimenter (plus tard) un classement mensuel.
#
# Hook : `record_event(user_id, game, won, duration_seconds)` est appelé depuis
# `database.record_minigame()` à chaque partie de mini-jeu — pas besoin de
# toucher chaque commande.

import logging
import random
import asyncio
from datetime import datetime, timedelta

import discord
from discord.ext import commands, tasks

from config import COLORS, POINTS_ALLOWED_CHANNELS, ADMIN_ROLES, DATA_DIR, AUTO_ANNONCES
from utils import load_json, save_json

logger = logging.getLogger(__name__)

CHALLENGES_FILE = f"{DATA_DIR}/weekly_challenges.json"

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIG
# ═══════════════════════════════════════════════════════════════════════════════

CHALLENGES_PER_WEEK = 3              # nb tirés chaque semaine
PERFECT_WEEK_BONUS_XP = 150          # bonus si les 3 défis sont validés
HISTORY_KEEP_WEEKS = 12              # nb semaines gardées en historique

# Liste des jeux "skill" éligibles aux défis (exclut coinflip/slots/roulette)
SKILL_GAMES = [
    "reaction", "unscramble", "wordle", "hangman", "chain",
    "devinette", "quoteguess", "emojirebus", "anagram",
    "guessmanga", "opening", "character", "click", "memory",
    "ttt", "connect4",
]

# ═══════════════════════════════════════════════════════════════════════════════
# POOL DE TEMPLATES DE DÉFIS
# ═══════════════════════════════════════════════════════════════════════════════
# Chaque template = dict avec :
#   id          : identifiant unique stable
#   title       : titre court (≤ 40 chars)
#   desc        : description (peut contenir {target}, {game})
#   type        : "win_game" | "win_any" | "diversity" | "speed_win" | "streak"
#   game        : nom du jeu (pour win_game / speed_win) — ignoré sinon
#   target      : valeur à atteindre
#   reward_xp   : XP donné à la complétion
#   max_seconds : pour speed_win uniquement
#
# La rotation tire CHALLENGES_PER_WEEK templates distincts par semaine.

CHALLENGE_POOL = [
    # ─── Win N games (jeux solo / mots) ────────────────────────────────────────
    {"id": "win_wordle_5",     "title": "🟩 Wordle Master",
     "desc": "Gagne **{target}** parties de Wordle.",
     "type": "win_game", "game": "wordle", "target": 5, "reward_xp": 80},

    {"id": "win_hangman_5",    "title": "💀 Bourreau",
     "desc": "Gagne **{target}** parties de Pendu.",
     "type": "win_game", "game": "hangman", "target": 5, "reward_xp": 70},

    {"id": "win_unscramble_8", "title": "🔤 Démêleur",
     "desc": "Gagne **{target}** parties d'Unscramble.",
     "type": "win_game", "game": "unscramble", "target": 8, "reward_xp": 70},

    {"id": "win_anagram_6",    "title": "🔠 Anagrameur",
     "desc": "Trouve **{target}** anagrammes.",
     "type": "win_game", "game": "anagram", "target": 6, "reward_xp": 80},

    {"id": "win_devinette_5",  "title": "🧠 Esprit vif",
     "desc": "Résous **{target}** devinettes.",
     "type": "win_game", "game": "devinette", "target": 5, "reward_xp": 70},

    {"id": "win_emojirebus_5", "title": "🧩 Décodeur",
     "desc": "Décode **{target}** rebus emoji.",
     "type": "win_game", "game": "emojirebus", "target": 5, "reward_xp": 70},

    {"id": "win_guessmanga_5", "title": "📖 Otaku confirmé",
     "desc": "Reconnais **{target}** mangas dans Guess Manga.",
     "type": "win_game", "game": "guessmanga", "target": 5, "reward_xp": 70},

    {"id": "win_opening_5",    "title": "🎵 Mélomane",
     "desc": "Reconnais **{target}** openings.",
     "type": "win_game", "game": "opening", "target": 5, "reward_xp": 70},

    {"id": "win_quote_5",      "title": "💬 Cinéphile",
     "desc": "Reconnais **{target}** quotes manga.",
     "type": "win_game", "game": "quoteguess", "target": 5, "reward_xp": 70},

    {"id": "win_reaction_8",   "title": "🎯 Réflexes",
     "desc": "Gagne **{target}** parties de Réaction.",
     "type": "win_game", "game": "reaction", "target": 8, "reward_xp": 60},

    {"id": "win_memory_3",     "title": "🃏 Mémoire d'éléphant",
     "desc": "Termine **{target}** parties de Memory.",
     "type": "win_game", "game": "memory", "target": 3, "reward_xp": 80},

    # ─── Win across all skill games ────────────────────────────────────────────
    {"id": "win_any_15",       "title": "🏆 Marathon",
     "desc": "Gagne **{target}** parties de mini-jeux (n'importe lesquels).",
     "type": "win_any", "target": 15, "reward_xp": 120},

    {"id": "win_any_25",       "title": "⚔️ Vétéran",
     "desc": "Gagne **{target}** parties de mini-jeux dans la semaine.",
     "type": "win_any", "target": 25, "reward_xp": 180},

    # ─── Diversité (jouer N jeux différents) ───────────────────────────────────
    {"id": "diversity_5",      "title": "🎲 Touche-à-tout",
     "desc": "Joue à **{target}** mini-jeux différents.",
     "type": "diversity", "target": 5, "reward_xp": 80},

    {"id": "diversity_8",      "title": "🌟 Polyvalent",
     "desc": "Joue à **{target}** mini-jeux différents.",
     "type": "diversity", "target": 8, "reward_xp": 130},

    # ─── Vitesse ───────────────────────────────────────────────────────────────
    {"id": "speed_reaction",   "title": "⚡ Foudre",
     "desc": "Gagne une partie de Réaction en **moins de {max_seconds}s**.",
     "type": "speed_win", "game": "reaction", "max_seconds": 1.0,
     "target": 1, "reward_xp": 90},

    {"id": "speed_wordle",     "title": "🟩 Express",
     "desc": "Gagne une partie de Wordle en **moins de {max_seconds}s**.",
     "type": "speed_win", "game": "wordle", "max_seconds": 30.0,
     "target": 1, "reward_xp": 100},

    {"id": "speed_unscramble", "title": "🔤 Éclair",
     "desc": "Gagne un Unscramble en **moins de {max_seconds}s**.",
     "type": "speed_win", "game": "unscramble", "max_seconds": 8.0,
     "target": 1, "reward_xp": 90},

    # ─── Streak ────────────────────────────────────────────────────────────────
    {"id": "streak_5",         "title": "🔥 Combo +5",
     "desc": "Atteins une série de **{target}** victoires consécutives.",
     "type": "streak", "target": 5, "reward_xp": 100},

    {"id": "streak_8",         "title": "🔥🔥 Combo +8",
     "desc": "Atteins une série de **{target}** victoires consécutives.",
     "type": "streak", "target": 8, "reward_xp": 160},
]


# ═══════════════════════════════════════════════════════════════════════════════
# HELPERS — semaine ISO
# ═══════════════════════════════════════════════════════════════════════════════

def _week_id(dt=None):
    """Retourne l'identifiant de semaine ISO (ex: '2026-W17')."""
    dt = dt or datetime.now()
    iso = dt.isocalendar()
    return f"{iso[0]}-W{iso[1]:02d}"


def _week_start(dt=None):
    """Retourne le lundi 00h00 de la semaine de dt."""
    dt = dt or datetime.now()
    monday = dt - timedelta(days=dt.weekday())
    return monday.replace(hour=0, minute=0, second=0, microsecond=0)


def _format_challenge_text(template):
    """Formate la description en injectant les variables du template."""
    fmt_args = {
        "target": template.get("target", "?"),
        "game": template.get("game", "?"),
        "max_seconds": template.get("max_seconds", "?"),
    }
    try:
        return template["desc"].format(**fmt_args)
    except Exception:
        return template["desc"]


# ═══════════════════════════════════════════════════════════════════════════════
# ÉTAT GLOBAL — chargé depuis disque, sauvegardé à chaque mutation
# ═══════════════════════════════════════════════════════════════════════════════

_state = None


def _default_state():
    return {
        "week_id": None,
        "started_at": None,
        "ends_at": None,
        "channel_id": None,
        "challenges": [],   # liste de templates "instanciés" pour la semaine
        "progress": {},     # uid -> {challenge_id -> {count, completed, completed_at}}
        "perfect_week": {}, # uid -> bool (déjà payé pour cette semaine ?)
        "history": [],      # liste {week_id, completions: {uid: count}, perfect: [uid,...]}
    }


def _load_state():
    global _state
    if _state is not None:
        return _state
    raw = load_json(CHALLENGES_FILE) or {}
    base = _default_state()
    for k, v in base.items():
        raw.setdefault(k, v)
    _state = raw
    return _state


def _save_state():
    if _state is None:
        return
    save_json(CHALLENGES_FILE, _state)


# ═══════════════════════════════════════════════════════════════════════════════
# ROTATION — démarre une nouvelle semaine si besoin
# ═══════════════════════════════════════════════════════════════════════════════

def _ensure_current_week(announce_callback=None):
    """Vérifie que la semaine courante est initialisée. Si on a basculé sur
    une nouvelle semaine, archive l'ancienne et tire de nouveaux défis.

    Retourne True si une rotation a eu lieu (pour permettre une annonce).
    """
    state = _load_state()
    now = datetime.now()
    current_wid = _week_id(now)

    if state.get("week_id") == current_wid and state.get("challenges"):
        return False  # rien à faire

    # Archive l'ancienne semaine si elle existe
    if state.get("week_id"):
        completions = {
            uid: sum(1 for c in u.values() if c.get("completed"))
            for uid, u in state.get("progress", {}).items()
        }
        perfect = [uid for uid, count in completions.items()
                   if count >= len(state.get("challenges", []))]
        state["history"].append({
            "week_id": state["week_id"],
            "started_at": state.get("started_at"),
            "ends_at": state.get("ends_at"),
            "challenges": [c["id"] for c in state.get("challenges", [])],
            "completions": completions,
            "perfect": perfect,
        })
        # Limite la taille
        state["history"] = state["history"][-HISTORY_KEEP_WEEKS:]

    # Démarre la nouvelle semaine
    week_start = _week_start(now)
    week_end = week_start + timedelta(days=7)
    picked = random.sample(CHALLENGE_POOL, min(CHALLENGES_PER_WEEK, len(CHALLENGE_POOL)))

    state["week_id"] = current_wid
    state["started_at"] = week_start.isoformat()
    state["ends_at"] = week_end.isoformat()
    state["challenges"] = picked
    state["progress"] = {}
    state["perfect_week"] = {}
    _save_state()
    logger.info(f"🗓️  Nouvelle semaine de défis : {current_wid} — "
                f"{[c['id'] for c in picked]}")
    return True


# ═══════════════════════════════════════════════════════════════════════════════
# HOOK PUBLIC — appelé depuis database.record_minigame
# ═══════════════════════════════════════════════════════════════════════════════
# Pour éviter un import circulaire, ce module n'est pas importé par database.py
# au top-level. À la place, database.record_minigame fait un import différé et
# appelle record_event(...) — voir database.py.

def record_event(user_id, game, won, duration_seconds=None, current_streak=None):
    """Met à jour la progression de tous les défis applicables.

    Appelé depuis db.record_minigame() à chaque partie. Renvoie la liste des
    défis nouvellement complétés (pour qu'un caller puisse afficher un toast).
    Les bonus XP sont distribués automatiquement via community.add_xp.
    """
    try:
        _ensure_current_week()
        state = _load_state()
        challenges = state.get("challenges", [])
        if not challenges:
            return []

        uid = str(user_id)
        progress = state.setdefault("progress", {}).setdefault(uid, {})

        newly_completed = []

        for ch in challenges:
            cid = ch["id"]
            entry = progress.setdefault(cid, {
                "count": 0, "completed": False, "completed_at": None,
            })
            if entry["completed"]:
                continue

            ctype = ch["type"]
            increment = 0

            if ctype == "win_game":
                if won and game == ch.get("game"):
                    increment = 1
            elif ctype == "win_any":
                if won and game in SKILL_GAMES:
                    increment = 1
            elif ctype == "diversity":
                # On compte une fois par jeu distinct joué (gagné OU perdu)
                played_games = entry.setdefault("games_seen", [])
                if game in SKILL_GAMES and game not in played_games:
                    played_games.append(game)
                    increment = 1
            elif ctype == "speed_win":
                if (won and game == ch.get("game")
                        and duration_seconds is not None
                        and duration_seconds <= ch.get("max_seconds", 0)):
                    increment = 1
            elif ctype == "streak":
                if won and current_streak is not None:
                    if current_streak >= ch.get("target", 0) and entry["count"] < ch["target"]:
                        entry["count"] = ch["target"]  # cap directement
                        # increment géré ci-dessous
            # else: type inconnu — ignoré

            if increment:
                entry["count"] = min(entry["count"] + increment, ch["target"])

            if not entry["completed"] and entry["count"] >= ch["target"]:
                entry["completed"] = True
                entry["completed_at"] = datetime.now().isoformat()
                newly_completed.append(ch)

        if newly_completed:
            _save_state()
            # Distribue les récompenses (XP) — import différé pour éviter circular
            try:
                from community import add_xp
                for ch in newly_completed:
                    add_xp(user_id, ch.get("reward_xp", 0), f"weekly_challenge:{ch['id']}")
                # Perfect week ?
                _maybe_pay_perfect_week(user_id)
            except Exception as e:
                logger.warning(f"weekly_challenges: paiement XP a échoué : {e}")
        else:
            _save_state()

        return newly_completed
    except Exception as e:
        logger.exception(f"weekly_challenges.record_event a échoué : {e}")
        return []


def _maybe_pay_perfect_week(user_id):
    """Si l'utilisateur a complété TOUS les défis de la semaine, paye le bonus
    'perfect week' (une seule fois)."""
    state = _load_state()
    uid = str(user_id)
    paid = state.setdefault("perfect_week", {})
    if paid.get(uid):
        return
    challenges = state.get("challenges", [])
    if not challenges:
        return
    progress = state.get("progress", {}).get(uid, {})
    if all(progress.get(c["id"], {}).get("completed") for c in challenges):
        try:
            from community import add_xp
            add_xp(user_id, PERFECT_WEEK_BONUS_XP, "weekly_challenge:perfect_week")
            paid[uid] = True
            _save_state()
            logger.info(f"🌟 Perfect week pour user {user_id} (+{PERFECT_WEEK_BONUS_XP} XP)")
        except Exception as e:
            logger.warning(f"perfect_week paiement échoué : {e}")


# ═══════════════════════════════════════════════════════════════════════════════
# COG — commandes + tâche de rotation
# ═══════════════════════════════════════════════════════════════════════════════

class WeeklyChallenges(commands.Cog):
    """Défis hebdomadaires — 3 challenges/semaine, reset chaque lundi."""

    def __init__(self, bot):
        self.bot = bot
        _load_state()
        _ensure_current_week()
        self._announce_lock = asyncio.Lock()
        self.rotation_task.start()

    def cog_unload(self):
        try:
            self.rotation_task.cancel()
        except Exception:
            pass

    # ─────────────────────────────────────────────────────────────────────────
    # Tâche d'arrière-plan — vérifie chaque heure si la semaine a tourné
    # ─────────────────────────────────────────────────────────────────────────

    @tasks.loop(hours=1)
    async def rotation_task(self):
        try:
            rotated = _ensure_current_week()
            if rotated and AUTO_ANNONCES["defis_hebdo"]:
                await self._announce_new_week()
        except Exception as e:
            logger.warning(f"rotation_task error: {e}")

    @rotation_task.before_loop
    async def before_rotation_task(self):
        await self.bot.wait_until_ready()

    async def _announce_new_week(self):
        async with self._announce_lock:
            channel = None
            for cid in POINTS_ALLOWED_CHANNELS:
                ch = self.bot.get_channel(cid)
                if ch:
                    channel = ch
                    break
            if not channel:
                return
            embed = self._build_challenges_embed(title="🗓️ Nouveaux défis hebdo !")
            embed.set_footer(text="Reset chaque lundi à minuit • !challenges pour ta progression")
            try:
                await channel.send(embed=embed)
            except Exception as e:
                logger.warning(f"Annonce défis hebdo échouée : {e}")

    # ─────────────────────────────────────────────────────────────────────────
    # Helpers d'affichage
    # ─────────────────────────────────────────────────────────────────────────

    def _build_challenges_embed(self, user_id=None, title="🗓️ Défis de la semaine"):
        state = _load_state()
        ends_iso = state.get("ends_at")
        ends_unix = None
        if ends_iso:
            try:
                ends_unix = int(datetime.fromisoformat(ends_iso).timestamp())
            except Exception:
                pass

        desc_lines = []
        if ends_unix:
            desc_lines.append(f"⏰ Reset <t:{ends_unix}:R> • semaine `{state.get('week_id')}`")
        desc_lines.append("")

        progress = (state.get("progress", {}).get(str(user_id), {}) if user_id else {})
        all_done = True

        for i, ch in enumerate(state.get("challenges", []), start=1):
            entry = progress.get(ch["id"], {"count": 0, "completed": False})
            target = ch["target"]
            count = min(entry.get("count", 0), target)
            done = entry.get("completed", False)
            if not done:
                all_done = False
            bar_len = 10
            filled = int((count / target) * bar_len) if target else 0
            bar = ("🟩" * filled) + ("⬜" * (bar_len - filled))
            check = "✅" if done else "⬜"

            desc_lines.append(
                f"**{i}. {check} {ch['title']}**  *(+{ch['reward_xp']} XP)*"
            )
            desc_lines.append(f"{_format_challenge_text(ch)}")
            if user_id is not None:
                desc_lines.append(f"`{count}/{target}` {bar}")
            desc_lines.append("")

        if user_id is not None:
            if all_done and state.get("challenges"):
                paid = state.get("perfect_week", {}).get(str(user_id))
                if paid:
                    desc_lines.append(
                        f"🌟 **Perfect Week !** Bonus de **+{PERFECT_WEEK_BONUS_XP} XP** déjà reçu."
                    )
                else:
                    desc_lines.append(
                        f"🌟 **Perfect Week !** Bonus de **+{PERFECT_WEEK_BONUS_XP} XP** en route…"
                    )
            else:
                desc_lines.append(
                    f"🌟 Complète les **{len(state.get('challenges', []))}** défis "
                    f"pour un bonus **+{PERFECT_WEEK_BONUS_XP} XP** (Perfect Week)."
                )

        return discord.Embed(
            title=title,
            description="\n".join(desc_lines),
            color=COLORS.get("info", 0x3498DB),
        )

    # ─────────────────────────────────────────────────────────────────────────
    # Commandes joueur
    # ─────────────────────────────────────────────────────────────────────────

    @commands.command(name="challenges", aliases=["weekly", "defis"])
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def challenges_cmd(self, ctx, member: discord.Member = None):
        """Affiche les défis de la semaine et ta progression."""
        _ensure_current_week()
        target = member or ctx.author
        embed = self._build_challenges_embed(
            user_id=target.id,
            title=f"🗓️ Défis hebdo — {target.display_name}",
        )
        embed.set_thumbnail(url=target.display_avatar.url)
        await ctx.send(embed=embed)

    @commands.command(name="challenges_top", aliases=["weekly_top", "defis_top"])
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def challenges_top_cmd(self, ctx):
        """Classement des joueurs par nombre de défis complétés cette semaine."""
        state = _load_state()
        progress = state.get("progress", {})
        if not progress:
            return await ctx.send(
                "📭 Personne n'a encore avancé sur les défis cette semaine. "
                "Sois le premier avec `!challenges` !"
            )

        # Compte les défis complétés par utilisateur
        scores = []
        for uid, ch_progress in progress.items():
            done = sum(1 for c in ch_progress.values() if c.get("completed"))
            if done > 0:
                scores.append((uid, done))
        scores.sort(key=lambda x: x[1], reverse=True)
        scores = scores[:10]

        if not scores:
            return await ctx.send("📭 Personne n'a encore complété de défi cette semaine.")

        medals = ["🥇", "🥈", "🥉"]
        lines = []
        total_chs = len(state.get("challenges", []))
        for i, (uid, done) in enumerate(scores):
            member = ctx.guild.get_member(int(uid)) if ctx.guild else None
            name = member.display_name if member else f"User {uid}"
            medal = medals[i] if i < 3 else f"`#{i+1}`"
            perfect = " 🌟" if done >= total_chs else ""
            lines.append(f"{medal} **{name}** — {done}/{total_chs} défis{perfect}")

        embed = discord.Embed(
            title="🏆 Top défis hebdo",
            description="\n".join(lines),
            color=COLORS.get("info", 0x3498DB),
        )
        embed.set_footer(text=f"Semaine {state.get('week_id', '?')} • !challenges pour les défis")
        await ctx.send(embed=embed)

    @commands.command(name="challenges_history", aliases=["weekly_history", "defis_history"])
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def challenges_history_cmd(self, ctx):
        """Historique des semaines passées (top 4 dernières)."""
        state = _load_state()
        history = state.get("history", [])
        if not history:
            return await ctx.send("📭 Aucun historique pour le moment.")

        recent = list(reversed(history))[:4]
        embed = discord.Embed(
            title="📜 Historique des défis hebdo",
            color=COLORS.get("info", 0x3498DB),
        )
        for week in recent:
            wid = week.get("week_id", "?")
            completions = week.get("completions", {})
            perfect_uids = week.get("perfect", [])
            top = sorted(completions.items(), key=lambda x: x[1], reverse=True)[:3]
            top_lines = []
            medals = ["🥇", "🥈", "🥉"]
            for i, (uid, n) in enumerate(top):
                member = ctx.guild.get_member(int(uid)) if ctx.guild else None
                name = member.display_name if member else f"User {uid}"
                top_lines.append(f"{medals[i]} {name} — {n} défi(s)")
            value = "\n".join(top_lines) if top_lines else "*Aucun participant*"
            if perfect_uids:
                value += f"\n🌟 **{len(perfect_uids)}** Perfect Week"
            embed.add_field(name=f"Semaine {wid}", value=value, inline=False)
        await ctx.send(embed=embed)

    # ─────────────────────────────────────────────────────────────────────────
    # Commande admin
    # ─────────────────────────────────────────────────────────────────────────

    @commands.command(name="challenges_force_rotate")
    @commands.has_any_role(*ADMIN_ROLES)
    async def challenges_force_rotate_cmd(self, ctx):
        """(ADMIN) Force la rotation des défis hebdo (tire 3 nouveaux défis)."""
        state = _load_state()
        # On force en réinitialisant le week_id pour déclencher l'archivage
        state["week_id"] = None
        _save_state()
        rotated = _ensure_current_week()
        if rotated:
            await ctx.send("✅ Défis hebdo réinitialisés.")
            await self._announce_new_week()
        else:
            await ctx.send("❌ Rotation impossible (état inattendu).")


async def setup(bot):
    await bot.add_cog(WeeklyChallenges(bot))
    logger.info("✅ Cog WeeklyChallenges chargé avec succès")
