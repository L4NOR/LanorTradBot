# minigames.py
# ═══════════════════════════════════════════════════════════════════════════════
# MINI-JEUX COMMUNAUTAIRES - GAINS D'XP PAR LE JEU
# ═══════════════════════════════════════════════════════════════════════════════

import discord
from discord.ext import commands, tasks
import random
import asyncio
import time
import unicodedata
from datetime import datetime, timedelta
from config import COLORS, POINTS_ALLOWED_CHANNELS
from community import add_xp, get_user_stats, sauvegarder_donnees, calculate_level, xp_progress, generate_xp_bar
from database import db
from utils import safe_api_call, load_json, save_json
import logging

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════════
# CONSTANTES
# ═══════════════════════════════════════════════════════════════════════════════

MINIGAME_XP = {
    "reaction": 15,
    "unscramble": 25,
    "wordle": 50,
    "hangman": 30,
    "chain": 20,
    "boss_hit": 5,
    "boss_kill": 100,
    "duel_min_bet": 10,
}

# ═══════════════════════════════════════════════════════════════════════════════
# LIMITES QUOTIDIENNES — pool partagé par catégorie
# ═══════════════════════════════════════════════════════════════════════════════
# Les admins (rôles dans ADMIN_ROLES) ne sont pas soumis à ces limites.
# Chaque utilisateur dispose d'un pool partagé :
#   • "minigames" : 15 parties/jour réparties librement entre les 9 mini-jeux
#   • "boss"      : 1 attaque/jour
# Le compteur est stocké en SQLite via la "catégorie" comme clé (pas par jeu).

CATEGORY_LIMITS = {
    "minigames": 15,
    "boss":      1,
}

# Mapping nom du jeu → catégorie partagée
GAME_CATEGORIES = {
    "reaction":   "minigames",
    "unscramble": "minigames",
    "wordle":     "minigames",
    "hangman":    "minigames",
    "chain":      "minigames",
    "coinflip":   "minigames",
    "slots":      "minigames",
    "roulette":   "minigames",
    "duel":       "minigames",
    "boss":       "boss",
}

CATEGORY_LABELS = {
    "minigames": "Mini-jeux",
    "boss":      "Attaques boss",
}

# Mots pour les jeux (thème manga / traduction)
MANGA_WORDS = [
    # Personnages & Mangas
    "exorciste", "demon", "satan", "flammes", "paladin",
    "assassin", "combat", "survie", "lame", "maldiction",
    "football", "gardien", "attaquant", "defenseur", "match",
    "yakuza", "crime", "souterrain", "gang",
    "oni", "shiki", "transformation",
    # Termes manga
    "manga", "anime", "shonen", "seinen", "chapitre", "tome",
    "traduction", "sensei", "nakama", "katana", "shinobi",
    "jutsu", "sabre", "pouvoir", "technique", "combat",
    "guerrier", "dragon", "esprit", "ombre", "lumiere",
    "heros", "vilain", "mentor", "rival", "equipe",
    "mission", "quete", "aventure", "mystere", "secret",
    "magie", "sortilege", "invocation", "portail", "dimension",
    "armure", "bouclier", "lance", "arc", "fleche",
    "clan", "royaume", "empire", "forteresse", "donjon",
    "elixir", "poison", "antidote", "potion", "parchemin",
    "prophete", "oracle", "gardien", "sentinelle", "chasseur",
    "fantome", "spectre", "vampire", "loup", "phenix",
]

# Mots de 5 lettres pour Wordle (sans accents)
WORDLE_WORDS = [
    "manga", "anime", "demon", "sabre", "magie", "force",
    "lames", "flame", "heros", "shiki", "garde", "armes",
    "monde", "coeur", "piege", "noble", "titan", "chaos",
    "divin", "epees", "ombre", "guilde", "quete", "rival",
    "lance", "duels", "arena", "glace", "foudre",
    "ninja", "ronin", "shogu", "droit", "clan",
    "encre", "trait", "plume", "panel", "trame",
    "scans", "clean", "check", "ligne", "bulle",
]

# Emojis pour le slot machine
SLOT_EMOJIS = ["🍒", "🍋", "🍊", "🍇", "⭐", "💎", "7️⃣"]

# Emojis pour le jeu de réaction
REACTION_EMOJIS = ["🔥", "⚡", "💎", "🎯", "🌟", "👑", "🎲", "🎪", "🎭", "🎨"]

BOSS_FILE = "data/boss.json"

# Hangman stages
HANGMAN_STAGES = [
    "```\n  +---+\n      |\n      |\n      |\n      |\n=========```",
    "```\n  +---+\n  O   |\n      |\n      |\n      |\n=========```",
    "```\n  +---+\n  O   |\n  |   |\n      |\n      |\n=========```",
    "```\n  +---+\n  O   |\n /|   |\n      |\n      |\n=========```",
    "```\n  +---+\n  O   |\n /|\\  |\n      |\n      |\n=========```",
    "```\n  +---+\n  O   |\n /|\\  |\n /    |\n      |\n=========```",
    "```\n  +---+\n  O   |\n /|\\  |\n / \\  |\n      |\n=========```",
]


def normalize(text):
    """Supprime les accents pour la comparaison"""
    nfkd = unicodedata.normalize('NFKD', text.lower())
    return ''.join(c for c in nfkd if not unicodedata.combining(c))


def remove_xp(user_id, amount):
    """Retire de l'XP du solde uniquement (sans affecter le niveau/total_xp)"""
    stats = get_user_stats(user_id)
    stats["xp"] = max(0, stats.get("xp", 0) - amount)
    sauvegarder_donnees()


def fmt_deadline(seconds_from_now):
    """Retourne un timestamp Discord relatif (ex: <t:1234567890:R>)"""
    return f"<t:{int(time.time()) + int(seconds_from_now)}:R>"


def format_countdown(remaining_seconds, total_seconds, bar_length=12):
    """Construit une ligne de compte à rebours : '⏱️ 00:27 🟩🟩🟩⬜⬜⬜'"""
    remaining = max(0, int(remaining_seconds))
    total = max(1, int(total_seconds))
    mins = remaining // 60
    secs = remaining % 60
    ratio = min(1.0, max(0.0, remaining / total))
    filled = round(ratio * bar_length)
    # Couleur de la barre selon temps restant
    if ratio > 0.5:
        cell = "🟩"
    elif ratio > 0.25:
        cell = "🟨"
    else:
        cell = "🟥"
    bar = cell * filled + "⬛" * (bar_length - filled)
    return f"⏱️ **{mins:02d}:{secs:02d}** `{bar}`"


def build_timer_embed(remaining_seconds, total_seconds, title="⏱️ Temps restant"):
    """Construit un embed dédié au compte à rebours (séparé du jeu)."""
    remaining = max(0, remaining_seconds)
    total = max(1, total_seconds)
    ratio = remaining / total
    if ratio > 0.5:
        color = 0x2ECC71  # vert
    elif ratio > 0.25:
        color = 0xF1C40F  # jaune
    else:
        color = 0xE74C3C  # rouge
    return discord.Embed(
        title=title,
        description=format_countdown(remaining, total),
        color=color,
    )


async def finalize_timer(timer_msg, status="⌛ Temps écoulé !", color=None):
    """Édite le message timer pour afficher l'état final (fin de jeu)."""
    if timer_msg is None:
        return
    try:
        await timer_msg.edit(embed=discord.Embed(
            title="⏱️ Terminé",
            description=status,
            color=color if color is not None else 0x95A5A6,  # gris
        ))
    except (discord.NotFound, discord.Forbidden, discord.HTTPException):
        pass


async def run_countdown(message, state, rebuild_embed, interval=3):
    """Tâche d'arrière-plan qui édite l'embed pour mettre à jour le compte à rebours.

    - state: dict partagé contenant au minimum `deadline` (timestamp unix) et
      éventuellement `ended` (bool) pour stopper proprement.
    - rebuild_embed(remaining_seconds): callable retournant un discord.Embed à jour.
    - interval: intervalle (secondes) entre deux éditions (>=2s pour éviter le
      rate-limit Discord).
    """
    try:
        # Petit délai initial : laisse le main code entrer dans wait_for avant
        # le premier tick, et évite de ré-éditer immédiatement après ctx.send()
        await asyncio.sleep(1.0)

        while True:
            if state.get("ended"):
                return
            remaining = state.get("deadline", 0) - time.time()
            if remaining <= 0:
                return

            # Construction de l'embed (protégée : si le rebuild crash,
            # on log la trace et on arrête pour ne pas boucler à l'infini)
            try:
                embed = rebuild_embed(remaining)
            except Exception:
                logger.exception("run_countdown: rebuild_embed a crashé")
                return

            try:
                await message.edit(embed=embed)
            except asyncio.CancelledError:
                raise
            except discord.NotFound:
                return
            except discord.Forbidden:
                logger.warning("run_countdown: edit refusé (Forbidden)")
                return
            except discord.HTTPException as e:
                # Rate-limit ou autre erreur HTTP transitoire : on loggue et on continue
                logger.warning(f"run_countdown: edit HTTP échoué ({e}) — on continue")
            except Exception:
                logger.exception("run_countdown: edit inattendu")
                return

            # Sleep jusqu'au prochain tick, sans dépasser le temps restant
            sleep_for = min(interval, max(0.5, remaining))
            try:
                await asyncio.sleep(sleep_for)
            except asyncio.CancelledError:
                raise
    except asyncio.CancelledError:
        return
    except Exception:
        logger.exception("run_countdown: erreur fatale")


async def stop_countdown(task, state):
    """Arrête proprement une tâche de countdown et attend sa fin.

    Garantit que la tâche ne produira plus d'édition APRÈS cet appel, ce qui
    évite qu'un tick résiduel n'écrase l'embed final de fin de jeu.
    """
    if state is not None:
        state["ended"] = True
    if task is None or task.done():
        return
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
    except Exception:
        logger.exception("stop_countdown: erreur en attendant la tâche")


async def announce_level_up_safe(bot, user_id, new_level):
    """Annonce un level-up sans casser le flux du jeu en cas d'erreur."""
    try:
        cog = bot.get_cog("CommunitySystem")
        if cog:
            await cog.announce_level_up(user_id, new_level)
    except Exception as e:
        logger.warning(f"announce_level_up failed: {e}")


# ═══════════════════════════════════════════════════════════════════════════════
# COG PRINCIPAL
# ═══════════════════════════════════════════════════════════════════════════════

class MiniGames(commands.Cog):
    """Mini-jeux communautaires pour gagner de l'XP"""

    def __init__(self, bot):
        self.bot = bot
        # channel_id -> {"type": str, "owner_id": int|None}
        self.active_games = {}
        self.boss_data = load_json(BOSS_FILE, {})
        self.attack_cooldowns = {}  # user_id -> datetime

    def cog_unload(self):
        pass

    def _is_game_active(self, channel_id):
        return channel_id in self.active_games

    def _get_game(self, channel_id):
        return self.active_games.get(channel_id)

    def _set_game(self, channel_id, game_type, owner_id=None):
        self.active_games[channel_id] = {"type": game_type, "owner_id": owner_id}

    def _clear_game(self, channel_id):
        self.active_games.pop(channel_id, None)

    # ─────────────────────────────────────────────────────────────────────────
    # LIMITES QUOTIDIENNES
    # ─────────────────────────────────────────────────────────────────────────

    def _is_admin(self, member):
        """Un admin contourne les limites quotidiennes."""
        try:
            from config import ADMIN_ROLES
            roles = getattr(member, "roles", None) or []
            return any(r.name in ADMIN_ROLES for r in roles)
        except Exception:
            return False

    async def _check_daily_limit(self, ctx, game):
        """Vérifie la limite quotidienne (pool partagé par catégorie) et incrémente.

        Retourne True si l'utilisateur peut jouer, False sinon (un message
        d'erreur a déjà été envoyé au joueur).

        Comportement :
        - Chaque jeu appartient à une catégorie (`GAME_CATEGORIES`) qui partage
          un pool unique par utilisateur (`CATEGORY_LIMITS`).
        - Les admins bypass la limite (et ne consomment pas de compteur).
        - Une catégorie sans limite (0 ou absente) passe toujours.
        """
        category = GAME_CATEGORIES.get(game)
        if category is None:
            return True

        limit = CATEGORY_LIMITS.get(category, 0)
        if limit <= 0:
            return True

        if self._is_admin(ctx.author):
            return True

        used = db.get_daily_usage(ctx.author.id, category)
        if used >= limit:
            now = datetime.now()
            next_midnight = (now + timedelta(days=1)).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            reset_unix = int(next_midnight.timestamp())

            label = CATEGORY_LABELS.get(category, category)
            embed = discord.Embed(
                title="🚫 Limite quotidienne atteinte",
                description=(
                    f"{ctx.author.mention}, tu as déjà utilisé **{used}/{limit}** "
                    f"de tes **{label}** aujourd'hui.\n\n"
                    f"⏰ Reset <t:{reset_unix}:R>\n"
                    f"📊 Utilise `!mglimits` pour voir tes compteurs."
                ),
                color=COLORS["error"],
            )
            await ctx.send(embed=embed)
            return False

        db.increment_daily_usage(ctx.author.id, category)
        return True

    # ═══════════════════════════════════════════════════════════════════════════
    # 🎯 REACTION - Jeu de rapidité
    # ═══════════════════════════════════════════════════════════════════════════

    @commands.command(name="reaction")
    @commands.cooldown(1, 30, commands.BucketType.channel)
    async def reaction_game(self, ctx):
        """Sois le premier à réagir avec le bon emoji !"""
        if self._is_game_active(ctx.channel.id):
            return await ctx.send("❌ Un jeu est déjà en cours dans ce channel !")

        if not await self._check_daily_limit(ctx, "reaction"):
            return

        self._set_game(ctx.channel.id, "reaction", owner_id=None)

        countdown_task = None
        timer_msg = None
        state = {"deadline": 0, "ended": False}
        try:
            target_emoji = random.choice(REACTION_EMOJIS)
            delay = random.uniform(2, 6)

            embed = discord.Embed(
                title="🎯 Jeu de Réaction",
                description=(
                    f"Lancé par {ctx.author.mention}\n"
                    "Préparez-vous... Un emoji va apparaître !\n"
                    "Soyez le **premier** à réagir avec le bon emoji !"
                ),
                color=COLORS["info"]
            )
            msg = await ctx.send(embed=embed)

            await asyncio.sleep(delay)

            react_timeout = 10
            state["deadline"] = time.time() + react_timeout

            await msg.edit(embed=discord.Embed(
                title="🎯 Jeu de Réaction",
                description=f"# RÉAGIS AVEC {target_emoji} !",
                color=0xFF0000,
            ))

            timer_msg = await ctx.send(embed=build_timer_embed(react_timeout, react_timeout))
            countdown_task = asyncio.create_task(
                run_countdown(
                    timer_msg, state,
                    lambda r: build_timer_embed(r, react_timeout),
                    interval=2,
                )
            )

            start_time = time.time()

            def check(reaction, user):
                return (
                    reaction.message.id == msg.id
                    and str(reaction.emoji) == target_emoji
                    and not user.bot
                )

            try:
                reaction, winner = await self.bot.wait_for("reaction_add", check=check, timeout=react_timeout)
                await stop_countdown(countdown_task, state)
                countdown_task = None
                elapsed = time.time() - start_time
                xp_earned, _, level_up, new_level = add_xp(winner.id, MINIGAME_XP["reaction"], "reaction_game")
                db.record_minigame(winner.id, "reaction", True, xp_earned, duration_seconds=elapsed)

                await finalize_timer(timer_msg, status=f"✅ {winner.display_name} a réagi en {elapsed:.2f}s", color=COLORS["success"])

                embed = discord.Embed(
                    title="🎯 Réaction — Victoire !",
                    description=(
                        f"{winner.mention} a été le plus rapide !\n"
                        f"⚡ **{elapsed:.2f}s** de réaction\n"
                        f"**+{xp_earned} XP** gagnés !"
                    ),
                    color=COLORS["success"]
                )
                await msg.edit(embed=embed)

                if level_up:
                    await announce_level_up_safe(self.bot, winner.id, new_level)

            except asyncio.TimeoutError:
                await stop_countdown(countdown_task, state)
                countdown_task = None
                await finalize_timer(timer_msg, status="⌛ Temps écoulé !", color=COLORS["error"])
                embed = discord.Embed(
                    title="🎯 Réaction — Temps écoulé !",
                    description="Personne n'a réagi à temps... 😔",
                    color=COLORS["error"]
                )
                await msg.edit(embed=embed)
        finally:
            await stop_countdown(countdown_task, state)
            self._clear_game(ctx.channel.id)

    # ═══════════════════════════════════════════════════════════════════════════
    # 🔤 UNSCRAMBLE - Mot mélangé
    # ═══════════════════════════════════════════════════════════════════════════

    @commands.command(name="unscramble")
    @commands.cooldown(1, 15, commands.BucketType.user)
    async def unscramble_game(self, ctx):
        """[Solo] Remets les lettres dans le bon ordre !"""
        if self._is_game_active(ctx.channel.id):
            return await ctx.send("❌ Un jeu est déjà en cours dans ce channel !")

        if not await self._check_daily_limit(ctx, "unscramble"):
            return

        self._set_game(ctx.channel.id, "unscramble", owner_id=ctx.author.id)
        total_timeout = 30

        countdown_task = None
        timer_msg = None
        state = {"deadline": 0, "ended": False}
        try:
            word = random.choice(MANGA_WORDS)
            scrambled = list(word)
            attempts = 0
            while ''.join(scrambled) == word and attempts < 10:
                random.shuffle(scrambled)
                attempts += 1
            scrambled = ''.join(scrambled).upper()

            state["deadline"] = time.time() + total_timeout

            game_embed = discord.Embed(
                title="🔤 Unscramble",
                description=(
                    f"👤 Joueur : {ctx.author.mention}\n\n"
                    f"# `{scrambled}`\n\n"
                    f"*{len(word)} lettres — réponds dans le chat !*"
                ),
                color=COLORS["info"],
            )
            game_embed.set_footer(text="Jeu solo — seul le joueur qui a lancé peut répondre")
            game_msg = await ctx.send(embed=game_embed)

            timer_msg = await ctx.send(embed=build_timer_embed(total_timeout, total_timeout))
            countdown_task = asyncio.create_task(
                run_countdown(
                    timer_msg, state,
                    lambda r: build_timer_embed(r, total_timeout),
                    interval=3,
                )
            )

            def check(m):
                return (
                    m.channel.id == ctx.channel.id
                    and m.author.id == ctx.author.id
                    and normalize(m.content.strip()) == normalize(word)
                )

            start = time.time()
            try:
                msg = await self.bot.wait_for("message", check=check, timeout=total_timeout)
                await stop_countdown(countdown_task, state)
                countdown_task = None

                elapsed = time.time() - start
                xp_earned, _, level_up, new_level = add_xp(ctx.author.id, MINIGAME_XP["unscramble"], "unscramble")
                db.record_minigame(ctx.author.id, "unscramble", True, xp_earned, duration_seconds=elapsed)

                await finalize_timer(timer_msg, status=f"✅ Trouvé en {elapsed:.1f}s", color=COLORS["success"])

                win_embed = discord.Embed(
                    title="🔤 Unscramble — Bravo !",
                    description=(
                        f"{ctx.author.mention} a trouvé le mot **{word.upper()}** !\n"
                        f"⚡ Résolu en **{elapsed:.1f}s**\n"
                        f"**+{xp_earned} XP** gagnés !"
                    ),
                    color=COLORS["success"],
                )
                await game_msg.edit(embed=win_embed)

                if level_up:
                    await announce_level_up_safe(self.bot, ctx.author.id, new_level)

            except asyncio.TimeoutError:
                await stop_countdown(countdown_task, state)
                countdown_task = None
                db.record_minigame(ctx.author.id, "unscramble", False, 0)
                await finalize_timer(timer_msg, status="⌛ Temps écoulé !", color=COLORS["error"])
                lose_embed = discord.Embed(
                    title="🔤 Unscramble — Temps écoulé !",
                    description=f"{ctx.author.mention}, le mot était **{word.upper()}**",
                    color=COLORS["error"],
                )
                await game_msg.edit(embed=lose_embed)
        finally:
            await stop_countdown(countdown_task, state)
            self._clear_game(ctx.channel.id)

    # ═══════════════════════════════════════════════════════════════════════════
    # 🪙 COINFLIP - Pile ou Face
    # ═══════════════════════════════════════════════════════════════════════════

    @commands.command(name="coinflip", aliases=["cf"])
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def coinflip(self, ctx, mise: int = None):
        """Pile ou face ! Mise ton XP (x2 ou perdu)"""
        if mise is None:
            return await ctx.send("❌ Usage : `!coinflip <montant>`")

        if mise < 5:
            return await ctx.send("❌ Mise minimum : **5 XP**")

        stats = get_user_stats(ctx.author.id)
        if stats.get("xp", 0) < mise:
            return await ctx.send(f"❌ Tu n'as que **{stats.get('xp', 0):,} XP** !")

        if not await self._check_daily_limit(ctx, "coinflip"):
            return

        result = random.choice(["pile", "face"])
        win = random.random() < 0.5

        embed = discord.Embed(title="🪙 Coinflip", color=COLORS["info"])
        embed.description = "La pièce tourne..."
        msg = await ctx.send(embed=embed)

        await asyncio.sleep(1.5)

        if win:
            xp_earned, _, level_up, new_level = add_xp(ctx.author.id, mise, "coinflip_win")
            db.record_minigame(ctx.author.id, "coinflip", True, xp_earned)
            new_balance = get_user_stats(ctx.author.id).get("xp", 0)
            embed.title = f"🪙 {result.upper()} — Tu gagnes !"
            embed.description = f"**+{xp_earned} XP** gagnés !\n💰 Solde : {new_balance:,} XP"
            embed.color = COLORS["success"]

            if level_up:
                await announce_level_up_safe(self.bot, ctx.author.id, new_level)
        else:
            remove_xp(ctx.author.id, mise)
            db.record_minigame(ctx.author.id, "coinflip", False, -mise)
            new_balance = get_user_stats(ctx.author.id).get("xp", 0)
            embed.title = f"🪙 {result.upper()} — Tu perds !"
            embed.description = f"**-{mise} XP** perdus...\n💰 Solde : {new_balance:,} XP"
            embed.color = COLORS["error"]

        await msg.edit(embed=embed)

    # ═══════════════════════════════════════════════════════════════════════════
    # 🎰 SLOTS - Machine à sous
    # ═══════════════════════════════════════════════════════════════════════════

    @commands.command(name="slots")
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def slots(self, ctx, mise: int = None):
        """Machine à sous ! 3 identiques = jackpot"""
        if mise is None:
            return await ctx.send("❌ Usage : `!slots <montant>`")

        if mise < 5:
            return await ctx.send("❌ Mise minimum : **5 XP**")

        stats = get_user_stats(ctx.author.id)
        if stats.get("xp", 0) < mise:
            return await ctx.send(f"❌ Tu n'as que **{stats.get('xp', 0):,} XP** !")

        if not await self._check_daily_limit(ctx, "slots"):
            return

        # Tirer 3 emojis
        reels = [random.choice(SLOT_EMOJIS) for _ in range(3)]

        embed = discord.Embed(title="🎰 Machine à Sous", color=COLORS["info"])
        embed.description = "Les rouleaux tournent..."
        msg = await ctx.send(embed=embed)

        await asyncio.sleep(1.5)

        display = f"# {reels[0]} | {reels[1]} | {reels[2]}"

        # Vérifier les gains
        if reels[0] == reels[1] == reels[2]:
            # Jackpot — 3 identiques
            if reels[0] == "7️⃣":
                multiplier = 15
                title = "🎰 MEGA JACKPOT !!! 🎆"
            elif reels[0] == "💎":
                multiplier = 10
                title = "🎰 JACKPOT DIAMANT ! 💎"
            else:
                multiplier = 5
                title = "🎰 JACKPOT !"

            gain = mise * multiplier
            xp_earned, _, level_up, new_level = add_xp(ctx.author.id, gain, "slots_jackpot")
            db.record_minigame(ctx.author.id, "slots", True, xp_earned)
            embed.title = title
            embed.description = f"{display}\n\n🎉 **x{multiplier}** — **+{xp_earned} XP** !"
            embed.color = 0xFFD700

            if level_up:
                await announce_level_up_safe(self.bot, ctx.author.id, new_level)

        elif reels[0] == reels[1] or reels[1] == reels[2] or reels[0] == reels[2]:
            # 2 identiques
            gain = mise
            xp_earned, _, level_up, new_level = add_xp(ctx.author.id, gain, "slots_small")
            db.record_minigame(ctx.author.id, "slots", True, xp_earned)
            embed.title = "🎰 Petite victoire !"
            embed.description = f"{display}\n\n**+{xp_earned} XP** gagnés !"
            embed.color = COLORS["success"]

            if level_up:
                await announce_level_up_safe(self.bot, ctx.author.id, new_level)
        else:
            # Perdu
            remove_xp(ctx.author.id, mise)
            db.record_minigame(ctx.author.id, "slots", False, -mise)
            embed.title = "🎰 Perdu..."
            embed.description = f"{display}\n\n**-{mise} XP** perdus"
            embed.color = COLORS["error"]

        embed.set_footer(text=f"💰 Solde : {get_user_stats(ctx.author.id).get('xp', 0):,} XP")
        await msg.edit(embed=embed)

    # ═══════════════════════════════════════════════════════════════════════════
    # 🎡 ROULETTE
    # ═══════════════════════════════════════════════════════════════════════════

    @commands.command(name="roulette")
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def roulette(self, ctx, mise: int = None, *, choix: str = None):
        """Roulette ! Mise sur rouge, noir ou un numéro (0-36)"""
        if mise is None or choix is None:
            embed = discord.Embed(
                title="🎡 Roulette — Comment jouer",
                description=(
                    "`!roulette <mise> rouge` — x2\n"
                    "`!roulette <mise> noir` — x2\n"
                    "`!roulette <mise> vert` — x14\n"
                    "`!roulette <mise> <0-36>` — x10"
                ),
                color=COLORS["info"]
            )
            return await ctx.send(embed=embed)

        if mise < 5:
            return await ctx.send("❌ Mise minimum : **5 XP**")

        stats = get_user_stats(ctx.author.id)
        if stats.get("xp", 0) < mise:
            return await ctx.send(f"❌ Tu n'as que **{stats.get('xp', 0):,} XP** !")

        choix = choix.lower().strip()

        # Valider le choix
        bet_type = None
        bet_number = None
        if choix in ("rouge", "red"):
            bet_type = "rouge"
        elif choix in ("noir", "black"):
            bet_type = "noir"
        elif choix in ("vert", "green"):
            bet_type = "vert"
        elif choix.isdigit() and 0 <= int(choix) <= 36:
            bet_type = "number"
            bet_number = int(choix)
        else:
            return await ctx.send("❌ Choix invalide ! Utilise `rouge`, `noir`, `vert` ou un numéro `0-36`")

        if not await self._check_daily_limit(ctx, "roulette"):
            return

        # Tirer le résultat
        result = random.randint(0, 36)
        rouges = {1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36}
        if result == 0:
            result_color = "vert"
            result_emoji = "🟢"
        elif result in rouges:
            result_color = "rouge"
            result_emoji = "🔴"
        else:
            result_color = "noir"
            result_emoji = "⚫"

        embed = discord.Embed(title="🎡 Roulette", description="La bille tourne...", color=COLORS["info"])
        msg = await ctx.send(embed=embed)
        await asyncio.sleep(2)

        # Calculer le gain
        win = False
        multiplier = 0
        if bet_type == "rouge" and result_color == "rouge":
            win, multiplier = True, 2
        elif bet_type == "noir" and result_color == "noir":
            win, multiplier = True, 2
        elif bet_type == "vert" and result_color == "vert":
            win, multiplier = True, 14
        elif bet_type == "number" and result == bet_number:
            win, multiplier = True, 10

        result_text = f"{result_emoji} **{result}** ({result_color})"

        if win:
            gain = mise * (multiplier - 1)
            xp_earned, _, level_up, new_level = add_xp(ctx.author.id, gain, "roulette_win")
            db.record_minigame(ctx.author.id, "roulette", True, xp_earned)
            embed.title = "🎡 Roulette — Tu gagnes !"
            embed.description = f"{result_text}\n\n**x{multiplier}** — **+{xp_earned} XP** !"
            embed.color = COLORS["success"]

            if level_up:
                await announce_level_up_safe(self.bot, ctx.author.id, new_level)
        else:
            remove_xp(ctx.author.id, mise)
            db.record_minigame(ctx.author.id, "roulette", False, -mise)
            embed.title = "🎡 Roulette — Perdu..."
            embed.description = f"{result_text}\n\n**-{mise} XP** perdus"
            embed.color = COLORS["error"]

        embed.set_footer(text=f"💰 Solde : {get_user_stats(ctx.author.id).get('xp', 0):,} XP")
        await msg.edit(embed=embed)

    # ═══════════════════════════════════════════════════════════════════════════
    # ⚔️ DUEL - PvP avec mise d'XP
    # ═══════════════════════════════════════════════════════════════════════════

    @commands.command(name="duel")
    @commands.cooldown(1, 30, commands.BucketType.user)
    async def duel(self, ctx, adversaire: discord.Member = None, mise: int = None):
        """Défie un autre membre en duel ! Le gagnant prend la mise"""
        if adversaire is None or mise is None:
            return await ctx.send("❌ Usage : `!duel @adversaire <mise>`")

        if adversaire.bot or adversaire.id == ctx.author.id:
            return await ctx.send("❌ Tu ne peux pas te défier toi-même ou un bot !")

        if mise < MINIGAME_XP["duel_min_bet"]:
            return await ctx.send(f"❌ Mise minimum : **{MINIGAME_XP['duel_min_bet']} XP**")

        # Vérifier les soldes
        stats_challenger = get_user_stats(ctx.author.id)
        stats_opponent = get_user_stats(adversaire.id)

        if stats_challenger.get("xp", 0) < mise:
            return await ctx.send(f"❌ Tu n'as que **{stats_challenger.get('xp', 0):,} XP** !")
        if stats_opponent.get("xp", 0) < mise:
            return await ctx.send(f"❌ {adversaire.display_name} n'a que **{stats_opponent.get('xp', 0):,} XP** !")

        if not await self._check_daily_limit(ctx, "duel"):
            return

        # Demander l'acceptation — avec countdown dans un message à part
        accept_timeout = 60
        duel_state = {"deadline": time.time() + accept_timeout, "ended": False}

        msg = await ctx.send(embed=discord.Embed(
            title="⚔️ Défi en Duel !",
            description=(
                f"{ctx.author.mention} défie {adversaire.mention} !\n"
                f"💰 Mise : **{mise} XP**\n\n"
                f"{adversaire.mention}, réagis avec ✅ pour accepter ou ❌ pour refuser."
            ),
            color=COLORS["warning"],
        ))
        await msg.add_reaction("✅")
        await msg.add_reaction("❌")

        timer_msg = await ctx.send(embed=build_timer_embed(accept_timeout, accept_timeout, title="⏱️ Temps pour accepter"))
        duel_countdown = asyncio.create_task(
            run_countdown(
                timer_msg, duel_state,
                lambda r: build_timer_embed(r, accept_timeout, title="⏱️ Temps pour accepter"),
                interval=3,
            )
        )

        def check(reaction, user):
            return (
                reaction.message.id == msg.id
                and user.id == adversaire.id
                and str(reaction.emoji) in ("✅", "❌")
            )

        try:
            reaction, _ = await self.bot.wait_for("reaction_add", check=check, timeout=accept_timeout)
            await stop_countdown(duel_countdown, duel_state)

            if str(reaction.emoji) == "❌":
                await finalize_timer(timer_msg, status="❌ Duel refusé", color=COLORS["error"])
                refused = discord.Embed(
                    title="⚔️ Duel refusé",
                    description=f"{adversaire.display_name} a refusé le duel.",
                    color=COLORS["error"],
                )
                return await msg.edit(embed=refused)

            await finalize_timer(timer_msg, status="✅ Défi accepté !", color=COLORS["success"])

        except asyncio.TimeoutError:
            await stop_countdown(duel_countdown, duel_state)
            await finalize_timer(timer_msg, status="⌛ Pas de réponse", color=COLORS["error"])
            expired = discord.Embed(
                title="⚔️ Duel expiré",
                description="Pas de réponse... Le duel est annulé.",
                color=COLORS["error"],
            )
            return await msg.edit(embed=expired)

        # Combat ! Lancer de dés
        roll_challenger = random.randint(1, 20)
        roll_opponent = random.randint(1, 20)

        # Égalité → relance
        while roll_challenger == roll_opponent:
            roll_challenger = random.randint(1, 20)
            roll_opponent = random.randint(1, 20)

        embed = discord.Embed(title="⚔️ Duel en cours...", color=COLORS["info"])
        embed.description = "Les dés roulent... 🎲"
        await msg.edit(embed=embed)
        await asyncio.sleep(2)

        if roll_challenger > roll_opponent:
            winner, loser = ctx.author, adversaire
            roll_win, roll_lose = roll_challenger, roll_opponent
        else:
            winner, loser = adversaire, ctx.author
            roll_win, roll_lose = roll_opponent, roll_challenger

        # Transférer l'XP
        xp_earned, _, level_up, new_level = add_xp(winner.id, mise, "duel_win")
        remove_xp(loser.id, mise)
        db.record_minigame(winner.id, "duel", True, xp_earned)
        db.record_minigame(loser.id, "duel", False, -mise)

        embed = discord.Embed(
            title=f"⚔️ {winner.display_name} remporte le duel !",
            description=(
                f"🎲 {ctx.author.display_name} : **{roll_challenger}** vs "
                f"{adversaire.display_name} : **{roll_opponent}**\n\n"
                f"🏆 {winner.mention} gagne **+{xp_earned} XP** !\n"
                f"💀 {loser.display_name} perd **-{mise} XP**"
            ),
            color=COLORS["success"]
        )
        await msg.edit(embed=embed)

        if level_up:
            await announce_level_up_safe(self.bot, winner.id, new_level)

    # ═══════════════════════════════════════════════════════════════════════════
    # 🟩 WORDLE - Deviner un mot en 6 essais
    # ═══════════════════════════════════════════════════════════════════════════

    @commands.command(name="wordle")
    @commands.cooldown(1, 30, commands.BucketType.user)
    async def wordle(self, ctx):
        """[Solo] Devine le mot en 6 essais ! 🟩 = bonne place, 🟨 = mauvaise place, ⬛ = absent"""
        if self._is_game_active(ctx.channel.id):
            return await ctx.send("❌ Un jeu est déjà en cours dans ce channel !")

        if not await self._check_daily_limit(ctx, "wordle"):
            return

        self._set_game(ctx.channel.id, "wordle", owner_id=ctx.author.id)
        per_turn_timeout = 60

        countdown_task = None
        timer_msg = None
        state = {
            "deadline": 0,
            "ended": False,
            "remaining_attempts": 6,
        }
        try:
            word = random.choice(WORDLE_WORDS)
            word_normalized = normalize(word)
            word_len = len(word_normalized)
            max_attempts = 6
            attempts = []
            start_time = time.time()

            state["deadline"] = time.time() + per_turn_timeout
            state["remaining_attempts"] = max_attempts

            def render_embed(title=None, color=None, status_line=None):
                desc_lines = [
                    f"👤 Joueur : {ctx.author.mention}",
                    f"📏 **{word_len} lettres** — **{state['remaining_attempts']}/{max_attempts}** essais restants",
                    "",
                ]
                if attempts:
                    desc_lines.append("\n".join(attempts))
                    desc_lines.append("")
                desc_lines.append("🟩 bonne place · 🟨 mauvaise place · ⬛ absente")
                if status_line:
                    desc_lines.append("")
                    desc_lines.append(status_line)
                e = discord.Embed(
                    title=title or "🟩 Wordle Manga",
                    description="\n".join(desc_lines),
                    color=color if color is not None else COLORS["info"],
                )
                e.set_footer(text="Jeu solo — tape ton essai dans le chat")
                return e

            game_msg = await ctx.send(embed=render_embed())
            timer_msg = await ctx.send(embed=build_timer_embed(per_turn_timeout, per_turn_timeout))
            countdown_task = asyncio.create_task(
                run_countdown(
                    timer_msg, state,
                    lambda r: build_timer_embed(r, per_turn_timeout),
                    interval=3,
                )
            )

            for attempt_num in range(1, max_attempts + 1):
                state["deadline"] = time.time() + per_turn_timeout
                state["remaining_attempts"] = max_attempts - attempt_num + 1

                def check(m):
                    return (
                        m.channel.id == ctx.channel.id
                        and m.author.id == ctx.author.id
                        and len(normalize(m.content.strip())) == word_len
                        and m.content.strip().isalpha()
                    )

                try:
                    msg = await self.bot.wait_for("message", check=check, timeout=per_turn_timeout)
                except asyncio.TimeoutError:
                    await stop_countdown(countdown_task, state)
                    countdown_task = None
                    db.record_minigame(ctx.author.id, "wordle", False, 0)
                    await finalize_timer(timer_msg, status="⌛ Temps écoulé !", color=COLORS["error"])
                    return await game_msg.edit(embed=render_embed(
                        title="🟩 Wordle — Temps écoulé !",
                        color=COLORS["error"],
                        status_line=f"⌛ Plus de temps... Le mot était **{word.upper()}**",
                    ))

                guess = normalize(msg.content.strip())

                word_chars = list(word_normalized)
                guess_chars = list(guess)
                result = ["⬛"] * word_len

                for i in range(word_len):
                    if guess_chars[i] == word_chars[i]:
                        result[i] = "🟩"
                        word_chars[i] = None
                        guess_chars[i] = None

                for i in range(word_len):
                    if guess_chars[i] is not None and guess_chars[i] in word_chars:
                        result[i] = "🟨"
                        word_chars[word_chars.index(guess_chars[i])] = None

                feedback_str = "".join(result)
                attempts.append(f"{feedback_str} `{guess.upper()}`")

                if guess == word_normalized:
                    elapsed = time.time() - start_time
                    bonus = max(10, MINIGAME_XP["wordle"] + (max_attempts - attempt_num) * 10)
                    xp_earned, _, level_up, new_level = add_xp(ctx.author.id, bonus, "wordle")
                    db.record_minigame(ctx.author.id, "wordle", True, xp_earned, duration_seconds=elapsed)

                    await stop_countdown(countdown_task, state)
                    countdown_task = None
                    state["remaining_attempts"] = max_attempts - attempt_num
                    await finalize_timer(timer_msg, status=f"✅ Trouvé en {elapsed:.1f}s", color=COLORS["success"])

                    await game_msg.edit(embed=render_embed(
                        title="🟩 Wordle — Bravo !",
                        color=COLORS["success"],
                        status_line=(
                            f"🎉 Trouvé en **{attempt_num}/{max_attempts}** essais "
                            f"(⚡ {elapsed:.1f}s) — **+{xp_earned} XP** !"
                        ),
                    ))

                    if level_up:
                        await announce_level_up_safe(self.bot, ctx.author.id, new_level)
                    return

                remaining = max_attempts - attempt_num
                if remaining > 0:
                    state["deadline"] = time.time() + per_turn_timeout
                    state["remaining_attempts"] = remaining
                    await game_msg.edit(embed=render_embed())

            # Défaite : tous les essais épuisés
            await stop_countdown(countdown_task, state)
            countdown_task = None
            state["remaining_attempts"] = 0
            db.record_minigame(ctx.author.id, "wordle", False, 0)
            await finalize_timer(timer_msg, status="❌ Tous les essais épuisés", color=COLORS["error"])
            await game_msg.edit(embed=render_embed(
                title="🟩 Wordle — Perdu !",
                color=COLORS["error"],
                status_line=f"💀 Le mot était **{word.upper()}**",
            ))

        finally:
            await stop_countdown(countdown_task, state)
            self._clear_game(ctx.channel.id)

    # ═══════════════════════════════════════════════════════════════════════════
    # 💀 HANGMAN - Pendu
    # ═══════════════════════════════════════════════════════════════════════════

    @commands.command(name="hangman", aliases=["pendu"])
    @commands.cooldown(1, 15, commands.BucketType.user)
    async def hangman(self, ctx):
        """[Solo] Jeu du pendu ! Devine le mot lettre par lettre"""
        if self._is_game_active(ctx.channel.id):
            return await ctx.send("❌ Un jeu est déjà en cours dans ce channel !")

        if not await self._check_daily_limit(ctx, "hangman"):
            return

        self._set_game(ctx.channel.id, "hangman", owner_id=ctx.author.id)
        per_turn_timeout = 60

        countdown_task = None
        timer_msg = None
        state = {
            "deadline": 0,
            "ended": False,
            "wrong": 0,
            "max_wrong": len(HANGMAN_STAGES) - 1,
        }
        try:
            word = random.choice(MANGA_WORDS)
            word_normalized = normalize(word)
            guessed_letters = set()
            start_time = time.time()

            state["deadline"] = time.time() + per_turn_timeout

            def get_display():
                return " ".join(
                    c.upper() if normalize(c) in guessed_letters else "\\_"
                    for c in word
                )

            def build_embed(title=None, color=None, status_line=None):
                wrong = state["wrong"]
                max_wrong = state["max_wrong"]
                desc_lines = [
                    f"👤 Joueur : {ctx.author.mention}",
                    f"❤️ Vies : **{max_wrong - wrong}/{max_wrong}**",
                ]
                desc_lines.append(HANGMAN_STAGES[wrong])
                desc_lines.append(f"**{get_display()}**  *({len(word)} lettres)*")
                if status_line:
                    desc_lines.append("")
                    desc_lines.append(status_line)
                e = discord.Embed(
                    title=title or "💀 Pendu",
                    description="\n".join(desc_lines),
                    color=color if color is not None else COLORS["info"],
                )
                if guessed_letters:
                    e.add_field(
                        name="Lettres essayées",
                        value=" ".join(sorted(l.upper() for l in guessed_letters)),
                        inline=False,
                    )
                e.set_footer(text="Jeu solo — tape une lettre dans le chat")
                return e

            game_msg = await ctx.send(embed=build_embed())
            timer_msg = await ctx.send(embed=build_timer_embed(per_turn_timeout, per_turn_timeout))
            countdown_task = asyncio.create_task(
                run_countdown(
                    timer_msg, state,
                    lambda r: build_timer_embed(r, per_turn_timeout),
                    interval=3,
                )
            )

            while state["wrong"] < state["max_wrong"]:
                state["deadline"] = time.time() + per_turn_timeout

                def check(m):
                    return (
                        m.channel.id == ctx.channel.id
                        and m.author.id == ctx.author.id
                        and len(m.content.strip()) == 1
                        and m.content.strip().isalpha()
                    )

                try:
                    msg = await self.bot.wait_for("message", check=check, timeout=per_turn_timeout)
                except asyncio.TimeoutError:
                    await stop_countdown(countdown_task, state)
                    countdown_task = None
                    db.record_minigame(ctx.author.id, "hangman", False, 0)
                    await finalize_timer(timer_msg, status="⌛ Temps écoulé !", color=COLORS["error"])
                    return await game_msg.edit(embed=build_embed(
                        title="💀 Pendu — Temps écoulé !",
                        color=COLORS["error"],
                        status_line=f"⌛ Le mot était **{word.upper()}**",
                    ))

                letter = normalize(msg.content.strip().lower())

                if letter in guessed_letters:
                    try:
                        await msg.reply(f"❌ `{letter.upper()}` déjà essayée !", delete_after=3)
                    except Exception:
                        pass
                    continue

                guessed_letters.add(letter)

                if letter in word_normalized:
                    if all(normalize(c) in guessed_letters for c in word):
                        elapsed = time.time() - start_time
                        xp_earned, _, level_up, new_level = add_xp(ctx.author.id, MINIGAME_XP["hangman"], "hangman")
                        db.record_minigame(ctx.author.id, "hangman", True, xp_earned, duration_seconds=elapsed)

                        await stop_countdown(countdown_task, state)
                        countdown_task = None
                        await finalize_timer(timer_msg, status=f"✅ Trouvé en {elapsed:.1f}s", color=COLORS["success"])

                        await game_msg.edit(embed=build_embed(
                            title="💀 Pendu — Victoire !",
                            color=COLORS["success"],
                            status_line=(
                                f"🎉 Mot trouvé : **{word.upper()}** "
                                f"(⚡ {elapsed:.1f}s) — **+{xp_earned} XP** !"
                            ),
                        ))

                        if level_up:
                            await announce_level_up_safe(self.bot, ctx.author.id, new_level)
                        return
                else:
                    state["wrong"] += 1

                # Reset deadline pour le tour suivant
                state["deadline"] = time.time() + per_turn_timeout
                await game_msg.edit(embed=build_embed())

            # Défaite
            await stop_countdown(countdown_task, state)
            countdown_task = None
            db.record_minigame(ctx.author.id, "hangman", False, 0)
            await finalize_timer(timer_msg, status="💀 Pendu", color=COLORS["error"])
            await game_msg.edit(embed=build_embed(
                title="💀 Pendu — Défaite !",
                color=COLORS["error"],
                status_line=f"💀 Le mot était **{word.upper()}**",
            ))

        finally:
            await stop_countdown(countdown_task, state)
            self._clear_game(ctx.channel.id)

    # ═══════════════════════════════════════════════════════════════════════════
    # 🔗 CHAIN - Chaîne de mots
    # ═══════════════════════════════════════════════════════════════════════════

    @commands.command(name="chain", aliases=["chaine"])
    @commands.cooldown(1, 30, commands.BucketType.channel)
    async def chain_game(self, ctx):
        """Chaîne de mots ! Chaque mot doit commencer par la dernière lettre du précédent"""
        if self._is_game_active(ctx.channel.id):
            return await ctx.send("❌ Un jeu est déjà en cours dans ce channel !")

        if not await self._check_daily_limit(ctx, "chain"):
            return

        self._set_game(ctx.channel.id, "chain", owner_id=None)
        turn_timeout = 15

        countdown_task = None
        timer_msg = None
        state = {"deadline": 0, "ended": False}
        try:
            start_word = random.choice(["manga", "anime", "combat", "magie", "epee", "demon"])
            used_words = {start_word}
            current_letter = normalize(start_word[-1])
            last_player = None
            participants = {}  # user_id -> count

            embed = discord.Embed(
                title="🔗 Chaîne de Mots",
                description=(
                    f"Lancée par {ctx.author.mention}\n"
                    f"Le premier mot est : **{start_word.upper()}**\n\n"
                    f"Tapez un mot qui commence par la lettre **`{current_letter.upper()}`** !\n"
                    f"⏱️ **{turn_timeout}s** par tour — dernier debout gagne !\n\n"
                    f"*Règles : min. 3 lettres, pas de répétition, pas 2x d'affilée le même joueur*"
                ),
                color=COLORS["info"]
            )
            await ctx.send(embed=embed)

            state["deadline"] = time.time() + turn_timeout
            timer_msg = await ctx.send(embed=build_timer_embed(turn_timeout, turn_timeout, title="⏱️ Tour en cours"))
            countdown_task = asyncio.create_task(
                run_countdown(
                    timer_msg, state,
                    lambda r: build_timer_embed(r, turn_timeout, title="⏱️ Tour en cours"),
                    interval=2,
                )
            )

            while True:
                def check(m):
                    if m.channel.id != ctx.channel.id or m.author.bot:
                        return False
                    word = normalize(m.content.strip().lower())
                    return (
                        len(word) >= 3
                        and word.isalpha()
                        and word[0] == current_letter
                        and word not in used_words
                        and m.author.id != last_player
                    )

                try:
                    msg = await self.bot.wait_for("message", check=check, timeout=turn_timeout)
                except asyncio.TimeoutError:
                    await stop_countdown(countdown_task, state)
                    countdown_task = None
                    await finalize_timer(timer_msg, status="⌛ Temps écoulé !", color=COLORS["error"])
                    # Fin du jeu
                    if not participants:
                        embed = discord.Embed(
                            title="🔗 Chaîne — Terminée !",
                            description="Personne n'a joué... 😔",
                            color=COLORS["error"]
                        )
                        return await ctx.send(embed=embed)

                    # Le gagnant est celui avec le plus de mots
                    winner_id = max(participants, key=participants.get)
                    winner = ctx.guild.get_member(winner_id)

                    xp_earned, _, level_up, new_level = add_xp(winner_id, MINIGAME_XP["chain"], "chain")
                    db.record_minigame(winner_id, "chain", True, xp_earned)
                    for pid in participants:
                        if pid != winner_id:
                            db.record_minigame(pid, "chain", False, 0)

                    embed = discord.Embed(
                        title="🔗 Chaîne — Temps écoulé !",
                        description=(
                            f"La chaîne s'arrête à **{len(used_words)}** mots !\n\n"
                            f"🏆 {winner.mention if winner else f'User {winner_id}'} gagne avec "
                            f"**{participants[winner_id]} mots** !\n"
                            f"**+{xp_earned} XP** gagnés !"
                        ),
                        color=COLORS["success"]
                    )
                    await ctx.send(embed=embed)

                    if level_up:
                        await announce_level_up_safe(self.bot, winner_id, new_level)
                    return

                word = normalize(msg.content.strip().lower())
                used_words.add(word)
                current_letter = word[-1]
                last_player = msg.author.id
                participants[msg.author.id] = participants.get(msg.author.id, 0) + 1

                # Reset du deadline pour le tour suivant
                state["deadline"] = time.time() + turn_timeout

                try:
                    await msg.add_reaction("✅")
                except Exception:
                    pass

        finally:
            await stop_countdown(countdown_task, state)
            self._clear_game(ctx.channel.id)

    # ═══════════════════════════════════════════════════════════════════════════
    # 👹 BOSS - Boss communautaire
    # ═══════════════════════════════════════════════════════════════════════════

    @commands.command(name="boss_spawn", aliases=["spawn_boss"])
    @commands.has_any_role(*__import__('config').ADMIN_ROLES)
    async def boss_spawn(self, ctx, hp: int = 500, *, name: str = None):
        """(ADMIN) Fait apparaître un boss communautaire"""
        if self.boss_data.get("active"):
            return await ctx.send("❌ Un boss est déjà actif ! Utilise `!boss` pour voir son état.")

        boss_names = [
            "🐉 Dragon des Ombres", "👹 Oni Suprême", "💀 Spectre Maudit",
            "🔥 Démon des Flammes", "⚡ Titan de Foudre", "🌊 Léviathan Abyssal",
            "👿 Seigneur Déchu", "🦇 Vampire Ancien", "🐺 Loup Alpha",
        ]
        boss_name = name or random.choice(boss_names)

        self.boss_data = {
            "active": True,
            "name": boss_name,
            "max_hp": hp,
            "hp": hp,
            "participants": {},  # user_id_str -> total_damage
            "spawned_at": datetime.now().isoformat(),
            "channel_id": ctx.channel.id,
        }
        save_json(BOSS_FILE, self.boss_data)

        embed = discord.Embed(
            title=f"⚠️ {boss_name} APPARAÎT !",
            description=(
                f"Un boss redoutable a envahi le serveur !\n\n"
                f"❤️ **HP : {hp:,} / {hp:,}**\n"
                f"```{'█' * 20} 100%```\n\n"
                f"Utilisez `!attack` pour l'attaquer !\n"
                f"⏱️ Cooldown : 30 secondes par attaque\n"
                f"🏆 **{MINIGAME_XP['boss_kill']} XP** pour le coup fatal !"
            ),
            color=0xFF0000
        )
        await ctx.send(embed=embed)

    @commands.command(name="boss")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def boss_status(self, ctx):
        """Affiche l'état du boss actuel"""
        if not self.boss_data.get("active"):
            return await ctx.send("❌ Aucun boss actif. Un admin peut en invoquer un avec `!boss_spawn`.")

        hp = self.boss_data["hp"]
        max_hp = self.boss_data["max_hp"]
        name = self.boss_data["name"]
        percentage = int((hp / max_hp) * 100)
        bar_len = 20
        filled = int((hp / max_hp) * bar_len)

        # Top attaquants
        participants = self.boss_data.get("participants", {})
        sorted_attackers = sorted(participants.items(), key=lambda x: x[1], reverse=True)[:5]

        attackers_text = ""
        for i, (uid, dmg) in enumerate(sorted_attackers):
            member = ctx.guild.get_member(int(uid))
            name_str = member.display_name if member else f"User {uid}"
            medal = ["🥇", "🥈", "🥉"][i] if i < 3 else f"#{i+1}"
            attackers_text += f"{medal} {name_str} — **{dmg:,}** dégâts\n"

        embed = discord.Embed(
            title=f"👹 {name}",
            description=(
                f"❤️ **HP : {hp:,} / {max_hp:,}**\n"
                f"```{'█' * filled}{'░' * (bar_len - filled)} {percentage}%```"
            ),
            color=0xFF0000 if percentage > 50 else 0xFF8C00 if percentage > 25 else 0x00FF00
        )

        if attackers_text:
            embed.add_field(name="⚔️ Top Attaquants", value=attackers_text, inline=False)

        embed.set_footer(text=f"Utilise !attack pour attaquer • {len(participants)} participant(s)")
        await ctx.send(embed=embed)

    @commands.command(name="attack", aliases=["attaque", "atk"])
    async def attack_boss(self, ctx):
        """Attaque le boss actuel !"""
        if not self.boss_data.get("active"):
            return await ctx.send("❌ Aucun boss actif !")

        # Cooldown manuel (30 secondes)
        user_id = ctx.author.id
        now = datetime.now()
        last_attack = self.attack_cooldowns.get(user_id)
        if last_attack and (now - last_attack).total_seconds() < 30:
            remaining = 30 - int((now - last_attack).total_seconds())
            return await ctx.send(f"⏱️ Cooldown ! Attaque disponible dans **{remaining}s**", delete_after=5)

        if not await self._check_daily_limit(ctx, "boss"):
            return

        self.attack_cooldowns[user_id] = now

        # Dégâts aléatoires
        damage = random.randint(10, 50)
        crit = random.random() < 0.1  # 10% de chance de critique
        if crit:
            damage *= 3
            crit_text = " **CRITIQUE !** 💥"
        else:
            crit_text = ""

        self.boss_data["hp"] = max(0, self.boss_data["hp"] - damage)

        # Enregistrer la participation
        uid_str = str(user_id)
        self.boss_data.setdefault("participants", {})
        self.boss_data["participants"][uid_str] = self.boss_data["participants"].get(uid_str, 0) + damage

        # XP par hit
        xp_hit, _, _, _ = add_xp(user_id, MINIGAME_XP["boss_hit"], "boss_hit")

        save_json(BOSS_FILE, self.boss_data)

        # Boss mort ?
        if self.boss_data["hp"] <= 0:
            # Coup fatal !
            xp_kill, _, level_up, new_level = add_xp(user_id, MINIGAME_XP["boss_kill"], "boss_kill")
            participants = self.boss_data.get("participants", {})

            # XP bonus pour tous les participants
            for pid_str, total_dmg in participants.items():
                if int(pid_str) != user_id:
                    bonus = min(50, total_dmg // 10)
                    if bonus > 0:
                        add_xp(int(pid_str), bonus, "boss_participation")

            # Top 3
            sorted_attackers = sorted(participants.items(), key=lambda x: x[1], reverse=True)[:3]
            podium = ""
            medals = ["🥇", "🥈", "🥉"]
            for i, (uid, dmg) in enumerate(sorted_attackers):
                member = ctx.guild.get_member(int(uid))
                name_str = member.display_name if member else f"User {uid}"
                podium += f"{medals[i]} {name_str} — **{dmg:,}** dégâts\n"

            embed = discord.Embed(
                title=f"☠️ {self.boss_data['name']} est VAINCU !",
                description=(
                    f"💥 {ctx.author.mention} a porté le **coup fatal** !{crit_text}\n"
                    f"**+{xp_kill + xp_hit} XP** pour le coup fatal !\n\n"
                    f"**Podium :**\n{podium}\n"
                    f"🎉 **{len(participants)} participants** — XP bonus distribué à tous !"
                ),
                color=0xFFD700
            )
            await ctx.send(embed=embed)

            # Reset
            self.boss_data = {"active": False}
            save_json(BOSS_FILE, self.boss_data)

            if level_up:
                cog = self.bot.get_cog("CommunitySystem")
                if cog:
                    await cog.announce_level_up(user_id, new_level)
        else:
            hp = self.boss_data["hp"]
            max_hp = self.boss_data["max_hp"]
            percentage = int((hp / max_hp) * 100)
            bar_len = 15
            filled = int((hp / max_hp) * bar_len)

            embed = discord.Embed(
                title=f"⚔️ {ctx.author.display_name} attaque !",
                description=(
                    f"**-{damage}** dégâts !{crit_text} (+{xp_hit} XP)\n\n"
                    f"❤️ **{hp:,} / {max_hp:,}** HP\n"
                    f"```{'█' * filled}{'░' * (bar_len - filled)} {percentage}%```"
                ),
                color=COLORS["warning"]
            )
            await ctx.send(embed=embed)

    @commands.command(name="boss_end")
    @commands.has_any_role(*__import__('config').ADMIN_ROLES)
    async def boss_end(self, ctx):
        """(ADMIN) Termine le boss de force"""
        if not self.boss_data.get("active"):
            return await ctx.send("❌ Aucun boss actif.")

        self.boss_data = {"active": False}
        save_json(BOSS_FILE, self.boss_data)
        await ctx.send("✅ Boss terminé de force.")

    # ═══════════════════════════════════════════════════════════════════════════
    # 📊 MGSTATS / MGTOP / MGCANCEL - Stats & gestion
    # ═══════════════════════════════════════════════════════════════════════════

    @commands.command(name="mgstats", aliases=["minigame_stats", "gamestats"])
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def mgstats(self, ctx, member: discord.Member = None):
        """Affiche tes statistiques de mini-jeux (ou celles d'un autre membre)"""
        target = member or ctx.author
        rows = db.get_minigame_stats(target.id)
        totals = db.get_minigame_totals(target.id)

        embed = discord.Embed(
            title=f"📊 Stats Mini-Jeux — {target.display_name}",
            color=COLORS["info"],
        )
        embed.set_thumbnail(url=target.display_avatar.url)

        if not rows or not totals or totals.get("played", 0) == 0:
            embed.description = "Aucune partie jouée pour le moment.\nLance `!unscramble`, `!wordle`, `!hangman`... pour commencer !"
            return await ctx.send(embed=embed)

        played = totals.get("played", 0) or 0
        wins = totals.get("wins", 0) or 0
        losses = totals.get("losses", 0) or 0
        winrate = (wins / played * 100) if played else 0
        net = (totals.get("xp_earned", 0) or 0) - (totals.get("xp_lost", 0) or 0)

        embed.description = (
            f"🎮 **{played:,}** parties · 🏆 **{wins:,}** victoires · 💀 **{losses:,}** défaites\n"
            f"📈 Winrate : **{winrate:.1f}%**\n"
            f"💰 XP net : **{net:+,}** (gagnés {totals.get('xp_earned', 0):,} / perdus {totals.get('xp_lost', 0):,})\n"
            f"🔥 Meilleure série : **{totals.get('best_streak', 0)}**"
        )

        # Détail par jeu
        emoji_map = {
            "reaction": "🎯", "unscramble": "🔤", "wordle": "🟩",
            "hangman": "💀", "chain": "🔗", "coinflip": "🪙",
            "slots": "🎰", "roulette": "🎡", "duel": "⚔️",
        }
        lines = []
        for r in rows:
            game = r["game"]
            emo = emoji_map.get(game, "🎲")
            wr = (r["wins"] / r["played"] * 100) if r["played"] else 0
            line = f"{emo} **{game.capitalize()}** — {r['played']} parties · {r['wins']}V/{r['losses']}D ({wr:.0f}%)"
            if r.get("fastest_win_seconds"):
                line += f" · ⚡ {r['fastest_win_seconds']:.1f}s"
            lines.append(line)

        if lines:
            embed.add_field(name="Détail par jeu", value="\n".join(lines), inline=False)

        await ctx.send(embed=embed)

    @commands.command(name="mgtop", aliases=["minigame_top"])
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def mgtop(self, ctx, game: str = None):
        """Classement des meilleurs joueurs de mini-jeux. Usage: !mgtop [jeu]"""
        valid_games = {"reaction", "unscramble", "wordle", "hangman", "chain",
                       "coinflip", "slots", "roulette", "duel"}
        game_filter = None
        if game:
            game = game.lower().strip()
            if game not in valid_games:
                return await ctx.send(
                    f"❌ Jeu inconnu. Disponibles : {', '.join(sorted(valid_games))}"
                )
            game_filter = game

        rows = db.get_minigame_leaderboard(game=game_filter, limit=10, sort_by="wins")

        title = f"🏆 Top Mini-Jeux" + (f" — {game_filter.capitalize()}" if game_filter else " (global)")
        embed = discord.Embed(title=title, color=COLORS["info"])

        if not rows:
            embed.description = "Aucun joueur classé pour le moment."
            return await ctx.send(embed=embed)

        medals = ["🥇", "🥈", "🥉"]
        lines = []
        for i, r in enumerate(rows):
            uid = r["user_id"]
            member = ctx.guild.get_member(uid) if ctx.guild else None
            name = member.display_name if member else f"User {uid}"
            medal = medals[i] if i < 3 else f"`#{i+1}`"
            wins = r.get("wins") or 0
            played = r.get("played") or 0
            xp = r.get("xp_earned") or 0
            lines.append(
                f"{medal} **{name}** — {wins}V / {played} parties · {xp:,} XP"
            )

        embed.description = "\n".join(lines)
        embed.set_footer(text="Trié par victoires • !mgstats pour tes stats perso")
        await ctx.send(embed=embed)

    @commands.command(name="mgcancel", aliases=["cancel_game"])
    async def mgcancel(self, ctx):
        """Annule le mini-jeu actif dans ce channel (uniquement le lanceur ou un admin)"""
        game = self._get_game(ctx.channel.id)
        if not game:
            return await ctx.send("❌ Aucun mini-jeu actif dans ce channel.")

        from config import ADMIN_ROLES
        is_admin = any(r.name in ADMIN_ROLES for r in getattr(ctx.author, "roles", []))
        owner_id = game.get("owner_id")
        is_owner = owner_id == ctx.author.id

        if not (is_owner or is_admin):
            return await ctx.send(
                "❌ Seul le joueur qui a lancé la partie (ou un admin) peut l'annuler."
            )

        self._clear_game(ctx.channel.id)
        await ctx.send(f"✅ Mini-jeu **{game.get('type', '?')}** annulé. Tu peux en relancer un.")

    @commands.command(name="mglimits", aliases=["mglimit", "minigame_limits"])
    async def mglimits(self, ctx, member: discord.Member = None):
        """Affiche les pools quotidiens (mini-jeux + boss) et ton usage du jour."""
        target = member or ctx.author
        usage = db.get_all_daily_usage(target.id)
        is_admin_target = self._is_admin(target)

        now = datetime.now()
        next_midnight = (now + timedelta(days=1)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        reset_unix = int(next_midnight.timestamp())

        embed = discord.Embed(
            title=f"📊 Limites quotidiennes — {target.display_name}",
            description=f"⏰ Reset <t:{reset_unix}:R>",
            color=COLORS["info"],
        )

        if is_admin_target:
            embed.add_field(
                name="👑 Admin",
                value="Bypass actif — aucune limite quotidienne.",
                inline=False,
            )

        lines = []
        for category, limit in CATEGORY_LIMITS.items():
            label = CATEGORY_LABELS.get(category, category)
            used = usage.get(category, 0)
            if is_admin_target:
                bar = "♾️"
                status = f"`{used}` utilisées"
            else:
                ratio = min(1.0, used / limit) if limit > 0 else 0
                filled = int(ratio * 10)
                if used >= limit:
                    bar = "🟥" * 10
                else:
                    bar = "🟩" * filled + "⬜" * (10 - filled)
                status = f"`{used}/{limit}`"
            lines.append(f"**{label}** — {status}\n{bar}")

        embed.add_field(name="Pools", value="\n\n".join(lines), inline=False)
        embed.add_field(
            name="ℹ️ Détail",
            value=(
                "• **Mini-jeux** : pool partagé entre `reaction`, `unscramble`, "
                "`wordle`, `hangman`, `chain`, `coinflip`, `slots`, `roulette`, `duel`.\n"
                "• **Attaques boss** : 1 `!attack` par jour."
            ),
            inline=False,
        )
        embed.set_footer(text="Les admins ont un bypass • !mgstats pour tes stats")
        await ctx.send(embed=embed)


async def setup(bot):
    """Setup pour discord.py 2.0+"""
    await bot.add_cog(MiniGames(bot))
    logging.info("✅ Cog MiniGames chargé avec succès")
