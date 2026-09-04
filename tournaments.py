# tournaments.py
# ═══════════════════════════════════════════════════════════════════════════════
# SYSTÈME DE TOURNOIS (bracket à élimination directe)
# ═══════════════════════════════════════════════════════════════════════════════
# Un staff/animateur ouvre un tournoi sur un mini-jeu précis (ou "libre"),
# les utilisateurs rejoignent, le staff lance — le bot génère le bracket,
# les joueurs s'affrontent en duel, le gagnant signale son résultat,
# le bracket progresse jusqu'au champion.
#
# Commandes :
#   !tournament create <game> <name...>     — créer un tournoi (staff)
#   !tournament join <id>                   — rejoindre
#   !tournament leave <id>                  — quitter
#   !tournament list                        — voir les tournois en cours
#   !tournament info <id>                   — détails + bracket
#   !tournament start <id>                  — démarrer (staff/créateur)
#   !tournament report <id> <winner_mention>— signaler le vainqueur d'un match
#   !tournament cancel <id>                 — annuler (staff/créateur)
#
# Les données sont persistées dans data/tournaments.json.

import logging
import math
import random
from datetime import datetime

import discord
from discord.ext import commands

from config import DATA_DIR
from utils import load_json, save_json

logger = logging.getLogger(__name__)

TOURNAMENTS_FILE = f"{DATA_DIR}/tournaments.json"

# Jeux autorisés pour les tournois (doit exister côté minigames ou être "libre")
ALLOWED_GAMES = {
    "libre": "🎮 Libre",
    "reaction": "⚡ Reaction",
    "unscramble": "🔤 Unscramble",
    "wordle": "🟩 Wordle",
    "hangman": "💀 Hangman",
    "devinette": "❓ Devinette",
    "anagram": "🔀 Anagram",
    "emojirebus": "🧩 Emoji Rebus",
    "quoteguess": "💬 Quote Guess",
    "click": "🖱️ Fast Click",
    "memory": "🧠 Memory",
    "ttt": "⭕ Morpion",
    "connect4": "🔴 Puissance 4",
}

# Récompenses XP par étape (staff peut override mais défaut raisonnable)
XP_PER_WIN = 50
XP_CHAMPION_BONUS = 200
XP_RUNNERUP_BONUS = 100
XP_SEMI_BONUS = 50

MAX_PLAYERS = 32
MIN_PLAYERS = 2


# ═══════════════════════════════════════════════════════════════════════════════
# PERSISTANCE
# ═══════════════════════════════════════════════════════════════════════════════

_data = None


def _load():
    global _data
    if _data is not None:
        return _data
    raw = load_json(TOURNAMENTS_FILE) or {}
    raw.setdefault("tournaments", {})
    raw.setdefault("next_id", 1)
    _data = raw
    logger.info(f"🏆 Tournaments: {len(_data['tournaments'])} tournoi(s) chargé(s)")
    return _data


def _save():
    if _data is not None:
        save_json(TOURNAMENTS_FILE, _data)


def _new_id():
    d = _load()
    nid = int(d.get("next_id", 1))
    d["next_id"] = nid + 1
    _save()
    return str(nid)


# ═══════════════════════════════════════════════════════════════════════════════
# MODELE
# ═══════════════════════════════════════════════════════════════════════════════

def _empty_tournament(tid, name, game, creator_id, channel_id):
    return {
        "id": tid,
        "name": name,
        "game": game,
        "creator_id": str(creator_id),
        "channel_id": str(channel_id),
        "status": "open",        # open → running → finished / cancelled
        "players": [],           # liste d'user_id (str)
        "bracket": [],           # list[list[match]] — rounds
        "round_index": 0,
        "winner_id": None,
        "runner_up_id": None,
        "semi_ids": [],
        "created_at": datetime.now().isoformat(),
        "started_at": None,
        "finished_at": None,
    }


def _empty_match(mid, p1, p2):
    return {
        "mid": mid,
        "p1": p1,
        "p2": p2,     # peut être None (bye)
        "winner": None,
    }


def _get(tid):
    return _load()["tournaments"].get(str(tid))


# ═══════════════════════════════════════════════════════════════════════════════
# BRACKET
# ═══════════════════════════════════════════════════════════════════════════════

def _build_bracket(players):
    """Construit le premier round avec byes si nombre impair / non puissance de 2."""
    shuffled = list(players)
    random.shuffle(shuffled)
    n = len(shuffled)
    if n < 2:
        return []
    size = 1 << (n - 1).bit_length()  # prochaine puissance de 2 ≥ n
    byes = size - n
    # Donne les byes aux premiers (qui passent directement au round 2)
    round1 = []
    i = 0
    mid = 1
    # D'abord, matchs complets
    while i + 1 < n - byes:
        round1.append(_empty_match(str(mid), shuffled[i], shuffled[i + 1]))
        mid += 1
        i += 2
    # Ensuite, byes — un joueur "seul" qui passe
    remaining = shuffled[i:]
    # Pour garder un bracket cohérent, on crée des matchs avec p2=None
    for pl in remaining:
        m = _empty_match(str(mid), pl, None)
        m["winner"] = pl  # avance automatiquement
        round1.append(m)
        mid += 1
    return [round1]


def _round_is_complete(round_matches):
    return all(m.get("winner") for m in round_matches)


def _advance_round(t):
    """Construit le round suivant depuis les gagnants du round courant."""
    cur = t["bracket"][t["round_index"]]
    winners = [m["winner"] for m in cur if m.get("winner")]
    if len(winners) <= 1:
        return False  # tournoi terminé
    next_round = []
    mid_start = sum(len(r) for r in t["bracket"]) + 1
    i = 0
    mid = mid_start
    while i + 1 < len(winners):
        next_round.append(_empty_match(str(mid), winners[i], winners[i + 1]))
        mid += 1
        i += 2
    if i < len(winners):
        # bye
        m = _empty_match(str(mid), winners[i], None)
        m["winner"] = winners[i]
        next_round.append(m)
    t["bracket"].append(next_round)
    t["round_index"] += 1
    return True


def _current_matches(t):
    if not t["bracket"]:
        return []
    return [m for m in t["bracket"][t["round_index"]] if not m.get("winner")]


# ═══════════════════════════════════════════════════════════════════════════════
# AFFICHAGE
# ═══════════════════════════════════════════════════════════════════════════════

def _mention(bot, uid):
    if not uid:
        return "*(bye)*"
    return f"<@{uid}>"


def _round_name(idx, total_rounds):
    remaining = total_rounds - idx
    if remaining == 1:
        return "🏆 Finale"
    if remaining == 2:
        return "🥈 Demi-finales"
    if remaining == 3:
        return "🎯 Quarts de finale"
    if remaining == 4:
        return "🎮 Huitièmes"
    return f"Round {idx + 1}"


def _bracket_text(bot, t):
    if not t["bracket"]:
        return "*Pas encore démarré.*"
    total = len(t["bracket"])
    # Estimation du nombre total de rounds initiaux
    initial_players = len(t["players"])
    if initial_players < 2:
        return "*Pas assez de joueurs.*"
    total_rounds = max(1, (initial_players - 1).bit_length())
    lines = []
    for idx, rnd in enumerate(t["bracket"]):
        lines.append(f"**{_round_name(idx, total_rounds)}**")
        for m in rnd:
            p1 = _mention(bot, m["p1"])
            p2 = _mention(bot, m["p2"])
            if m.get("winner"):
                if m["p2"] is None:
                    lines.append(f"  • {p1} ✅ *(bye)*")
                else:
                    w = _mention(bot, m["winner"])
                    lines.append(f"  • {p1} vs {p2} → {w} ✅")
            else:
                lines.append(f"  • {p1} vs {p2} 🕓")
        lines.append("")
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════════
# COG
# ═══════════════════════════════════════════════════════════════════════════════

class Tournaments(commands.Cog):
    """Système de tournois à élimination directe."""

    def __init__(self, bot):
        self.bot = bot
        _load()

    # ── helpers ────────────────────────────────────────────────────────────
    def _is_staff(self, member):
        if member.guild_permissions.manage_guild:
            return True
        return any(r.name.lower() in ("staff", "admin", "modérateur", "moderateur") for r in member.roles)

    async def _award_xp(self, uid, amount, reason):
        try:
            from community import add_xp
            add_xp(uid, amount, reason)
        except Exception as e:
            logger.warning(f"XP award failed: {e}")

    # ── group ──────────────────────────────────────────────────────────────
    @commands.group(name="tournament", aliases=["tournoi", "tourney"], invoke_without_command=True)
    async def tournament(self, ctx):
        """Commandes de tournoi. Voir !tournament list."""
        emb = discord.Embed(
            title="🏆 Tournois — Aide",
            description=(
                "**Commandes disponibles** :\n"
                "`!tournament create <game> <nom...>` — créer (staff)\n"
                "`!tournament join <id>` — rejoindre\n"
                "`!tournament leave <id>` — quitter\n"
                "`!tournament list` — lister les tournois ouverts\n"
                "`!tournament info <id>` — détails + bracket\n"
                "`!tournament start <id>` — démarrer (créateur/staff)\n"
                "`!tournament report <id> @gagnant` — signaler un vainqueur\n"
                "`!tournament cancel <id>` — annuler (créateur/staff)\n\n"
                f"**Jeux autorisés** : {', '.join(ALLOWED_GAMES.keys())}"
            ),
            color=discord.Color.gold(),
        )
        await ctx.send(embed=emb)

    # ── CREATE ─────────────────────────────────────────────────────────────
    @tournament.command(name="create")
    async def t_create(self, ctx, game: str = None, *, name: str = None):
        if not self._is_staff(ctx.author):
            await ctx.send("❌ Seul le staff peut créer un tournoi.")
            return
        if not game or not name:
            await ctx.send("❌ Usage : `!tournament create <game> <nom...>`")
            return
        game = game.lower()
        if game not in ALLOWED_GAMES:
            await ctx.send(f"❌ Jeu inconnu. Autorisés : {', '.join(ALLOWED_GAMES.keys())}")
            return

        tid = _new_id()
        t = _empty_tournament(tid, name, game, ctx.author.id, ctx.channel.id)
        _load()["tournaments"][tid] = t
        _save()

        emb = discord.Embed(
            title=f"🏆 Nouveau tournoi — {name}",
            description=(
                f"**Jeu** : {ALLOWED_GAMES[game]}\n"
                f"**ID** : `{tid}`\n"
                f"**Créateur** : {ctx.author.mention}\n\n"
                f"➡️ Rejoignez avec `!tournament join {tid}`"
            ),
            color=discord.Color.gold(),
        )
        emb.set_footer(text=f"Max {MAX_PLAYERS} joueurs • Min {MIN_PLAYERS}")
        await ctx.send(embed=emb)

    # ── JOIN ───────────────────────────────────────────────────────────────
    @tournament.command(name="join")
    async def t_join(self, ctx, tid: str = None):
        if not tid:
            await ctx.send("❌ Usage : `!tournament join <id>`")
            return
        t = _get(tid)
        if not t:
            await ctx.send("❌ Tournoi introuvable.")
            return
        if t["status"] != "open":
            await ctx.send("❌ Les inscriptions sont fermées pour ce tournoi.")
            return
        uid = str(ctx.author.id)
        if uid in t["players"]:
            await ctx.send("❌ Tu es déjà inscrit.")
            return
        if len(t["players"]) >= MAX_PLAYERS:
            await ctx.send(f"❌ Tournoi complet ({MAX_PLAYERS} joueurs max).")
            return
        t["players"].append(uid)
        _save()
        await ctx.send(f"✅ {ctx.author.mention} a rejoint **{t['name']}** ({len(t['players'])} joueurs).")

    # ── LEAVE ──────────────────────────────────────────────────────────────
    @tournament.command(name="leave")
    async def t_leave(self, ctx, tid: str = None):
        if not tid:
            await ctx.send("❌ Usage : `!tournament leave <id>`")
            return
        t = _get(tid)
        if not t:
            await ctx.send("❌ Tournoi introuvable.")
            return
        if t["status"] != "open":
            await ctx.send("❌ Impossible de quitter un tournoi déjà lancé.")
            return
        uid = str(ctx.author.id)
        if uid not in t["players"]:
            await ctx.send("❌ Tu n'es pas inscrit.")
            return
        t["players"].remove(uid)
        _save()
        await ctx.send(f"👋 {ctx.author.mention} a quitté **{t['name']}**.")

    # ── LIST ───────────────────────────────────────────────────────────────
    @tournament.command(name="list")
    async def t_list(self, ctx):
        d = _load()
        active = [t for t in d["tournaments"].values() if t["status"] in ("open", "running")]
        if not active:
            await ctx.send("😴 Aucun tournoi en cours.")
            return
        emb = discord.Embed(title="🏆 Tournois en cours", color=discord.Color.gold())
        for t in active:
            status = "🟢 Ouvert" if t["status"] == "open" else "🔴 En cours"
            emb.add_field(
                name=f"#{t['id']} — {t['name']}",
                value=(
                    f"{ALLOWED_GAMES.get(t['game'], t['game'])} • {status}\n"
                    f"👥 {len(t['players'])} joueurs"
                ),
                inline=False,
            )
        await ctx.send(embed=emb)

    # ── INFO ───────────────────────────────────────────────────────────────
    @tournament.command(name="info")
    async def t_info(self, ctx, tid: str = None):
        if not tid:
            await ctx.send("❌ Usage : `!tournament info <id>`")
            return
        t = _get(tid)
        if not t:
            await ctx.send("❌ Tournoi introuvable.")
            return
        players_list = "\n".join(f"• <@{uid}>" for uid in t["players"]) or "*Aucun*"
        emb = discord.Embed(
            title=f"🏆 {t['name']} (#{t['id']})",
            description=(
                f"**Jeu** : {ALLOWED_GAMES.get(t['game'], t['game'])}\n"
                f"**Statut** : {t['status']}\n"
                f"**Créateur** : <@{t['creator_id']}>"
            ),
            color=discord.Color.gold(),
        )
        emb.add_field(name=f"👥 Joueurs ({len(t['players'])})", value=players_list[:1024], inline=False)
        if t["status"] == "running":
            bracket_txt = _bracket_text(self.bot, t)[:1024]
            emb.add_field(name="📊 Bracket", value=bracket_txt or "—", inline=False)
            cur = _current_matches(t)
            if cur:
                cur_txt = "\n".join(
                    f"• {_mention(self.bot, m['p1'])} vs {_mention(self.bot, m['p2'])}"
                    for m in cur
                )
                emb.add_field(name="⚔️ Matchs en cours", value=cur_txt[:1024], inline=False)
        elif t["status"] == "finished" and t.get("winner_id"):
            emb.add_field(name="🥇 Champion", value=f"<@{t['winner_id']}>", inline=False)
        await ctx.send(embed=emb)

    # ── START ──────────────────────────────────────────────────────────────
    @tournament.command(name="start")
    async def t_start(self, ctx, tid: str = None):
        if not tid:
            await ctx.send("❌ Usage : `!tournament start <id>`")
            return
        t = _get(tid)
        if not t:
            await ctx.send("❌ Tournoi introuvable.")
            return
        if str(ctx.author.id) != t["creator_id"] and not self._is_staff(ctx.author):
            await ctx.send("❌ Seul le créateur ou le staff peut démarrer.")
            return
        if t["status"] != "open":
            await ctx.send("❌ Ce tournoi n'est plus ouvert.")
            return
        if len(t["players"]) < MIN_PLAYERS:
            await ctx.send(f"❌ Il faut au moins {MIN_PLAYERS} joueurs.")
            return

        t["status"] = "running"
        t["started_at"] = datetime.now().isoformat()
        t["bracket"] = _build_bracket(t["players"])
        t["round_index"] = 0
        _save()

        emb = discord.Embed(
            title=f"🚀 Tournoi lancé — {t['name']}",
            description=(
                f"**Jeu** : {ALLOWED_GAMES.get(t['game'], t['game'])}\n"
                f"**{len(t['players'])} joueurs**\n\n"
                f"Affrontez-vous puis signalez le vainqueur avec\n"
                f"`!tournament report {tid} @gagnant`"
            ),
            color=discord.Color.orange(),
        )
        emb.add_field(name="📊 Round 1", value=_bracket_text(self.bot, t)[:1024], inline=False)
        await ctx.send(embed=emb)

    # ── REPORT ─────────────────────────────────────────────────────────────
    @tournament.command(name="report")
    async def t_report(self, ctx, tid: str = None, winner: discord.Member = None):
        if not tid or not winner:
            await ctx.send("❌ Usage : `!tournament report <id> @gagnant`")
            return
        t = _get(tid)
        if not t:
            await ctx.send("❌ Tournoi introuvable.")
            return
        if t["status"] != "running":
            await ctx.send("❌ Ce tournoi n'est pas en cours.")
            return

        wid = str(winner.id)
        cur_round = t["bracket"][t["round_index"]]
        # Trouve le match concerné
        match = None
        for m in cur_round:
            if m.get("winner"):
                continue
            if wid in (m["p1"], m["p2"]):
                match = m
                break
        if not match:
            await ctx.send("❌ Aucun match en cours pour ce joueur dans le round actuel.")
            return

        # Autorisé : les deux joueurs concernés, le créateur ou le staff
        author_id = str(ctx.author.id)
        allowed = {match["p1"], match["p2"], t["creator_id"]}
        if author_id not in allowed and not self._is_staff(ctx.author):
            await ctx.send("❌ Seuls les participants du match, le créateur ou le staff peuvent signaler.")
            return

        match["winner"] = wid
        _save()

        # XP pour victoire
        loser = match["p1"] if wid == match["p2"] else match["p2"]
        await self._award_xp(wid, XP_PER_WIN, f"tournament_{tid}")
        await ctx.send(
            f"✅ {winner.mention} remporte son match ! (+{XP_PER_WIN} XP)"
        )

        # Si round complet, avancer
        if _round_is_complete(cur_round):
            # Vérifier si tournoi terminé (1 seul gagnant restant)
            winners = [m["winner"] for m in cur_round if m.get("winner")]
            if len(winners) == 1:
                await self._finish(ctx, t, winners[0], loser)
                return
            # Sinon, round suivant
            _advance_round(t)
            _save()
            emb = discord.Embed(
                title=f"🏆 {t['name']} — Round suivant",
                color=discord.Color.gold(),
            )
            emb.add_field(name="📊 Bracket", value=_bracket_text(self.bot, t)[:1024], inline=False)
            await ctx.send(embed=emb)

    async def _finish(self, ctx, t, winner_id, runner_up_id):
        t["status"] = "finished"
        t["winner_id"] = winner_id
        t["runner_up_id"] = runner_up_id
        t["finished_at"] = datetime.now().isoformat()

        # Identifier les demi-finalistes (perdants de l'avant-dernier round)
        semi_ids = []
        if len(t["bracket"]) >= 2:
            semi_round = t["bracket"][-2]
            for m in semi_round:
                if m.get("winner") and m["p2"] and m["p1"] and m["p2"] != m["winner"]:
                    loser = m["p1"] if m["winner"] == m["p2"] else m["p2"]
                    if loser and loser != runner_up_id:
                        semi_ids.append(loser)
        t["semi_ids"] = semi_ids
        _save()

        # Récompenses bonus
        await self._award_xp(winner_id, XP_CHAMPION_BONUS, f"tournament_win_{t['id']}")
        if runner_up_id:
            await self._award_xp(runner_up_id, XP_RUNNERUP_BONUS, f"tournament_2nd_{t['id']}")
        for sid in semi_ids:
            await self._award_xp(sid, XP_SEMI_BONUS, f"tournament_semi_{t['id']}")

        emb = discord.Embed(
            title=f"🏆 Tournoi terminé — {t['name']}",
            description=(
                f"🥇 **Champion** : <@{winner_id}> (+{XP_CHAMPION_BONUS} XP)\n"
                f"🥈 **Finaliste** : <@{runner_up_id}> (+{XP_RUNNERUP_BONUS} XP)\n"
                + (f"🥉 **Demi-finalistes** : {', '.join(f'<@{u}>' for u in semi_ids)}\n" if semi_ids else "")
            ),
            color=discord.Color.gold(),
        )
        emb.set_footer(text=f"Tournoi #{t['id']} • {ALLOWED_GAMES.get(t['game'], t['game'])}")
        await ctx.send(embed=emb)

    # ── CANCEL ─────────────────────────────────────────────────────────────
    @tournament.command(name="cancel")
    async def t_cancel(self, ctx, tid: str = None):
        if not tid:
            await ctx.send("❌ Usage : `!tournament cancel <id>`")
            return
        t = _get(tid)
        if not t:
            await ctx.send("❌ Tournoi introuvable.")
            return
        if str(ctx.author.id) != t["creator_id"] and not self._is_staff(ctx.author):
            await ctx.send("❌ Seul le créateur ou le staff peut annuler.")
            return
        if t["status"] in ("finished", "cancelled"):
            await ctx.send("❌ Ce tournoi est déjà clos.")
            return
        t["status"] = "cancelled"
        t["finished_at"] = datetime.now().isoformat()
        _save()
        await ctx.send(f"🛑 Tournoi **{t['name']}** (#{tid}) annulé.")


async def setup(bot):
    await bot.add_cog(Tournaments(bot))
