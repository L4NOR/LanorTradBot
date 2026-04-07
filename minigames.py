# minigames.py
# ═══════════════════════════════════════════════════════════════════════════════
# MINI-JEUX COMMUNAUTAIRES - GAINS D'XP PAR LE JEU
# ═══════════════════════════════════════════════════════════════════════════════

import discord
from discord.ext import commands, tasks
import random
import asyncio
import unicodedata
from datetime import datetime, timedelta
from config import COLORS, POINTS_ALLOWED_CHANNELS
from community import add_xp, get_user_stats, sauvegarder_donnees, calculate_level, xp_progress, generate_xp_bar
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


# ═══════════════════════════════════════════════════════════════════════════════
# COG PRINCIPAL
# ═══════════════════════════════════════════════════════════════════════════════

class MiniGames(commands.Cog):
    """Mini-jeux communautaires pour gagner de l'XP"""

    def __init__(self, bot):
        self.bot = bot
        self.active_games = {}  # channel_id -> type de jeu actif
        self.boss_data = load_json(BOSS_FILE, {})
        self.attack_cooldowns = {}  # user_id -> datetime

    def cog_unload(self):
        pass

    def _is_game_active(self, channel_id):
        return channel_id in self.active_games

    def _set_game(self, channel_id, game_type):
        self.active_games[channel_id] = game_type

    def _clear_game(self, channel_id):
        self.active_games.pop(channel_id, None)

    # ═══════════════════════════════════════════════════════════════════════════
    # 🎯 REACTION - Jeu de rapidité
    # ═══════════════════════════════════════════════════════════════════════════

    @commands.command(name="reaction")
    @commands.cooldown(1, 30, commands.BucketType.channel)
    async def reaction_game(self, ctx):
        """Sois le premier à réagir avec le bon emoji !"""
        if self._is_game_active(ctx.channel.id):
            return await ctx.send("❌ Un jeu est déjà en cours dans ce channel !")

        self._set_game(ctx.channel.id, "reaction")

        try:
            target_emoji = random.choice(REACTION_EMOJIS)
            delay = random.uniform(2, 6)

            embed = discord.Embed(
                title="🎯 Jeu de Réaction",
                description="Préparez-vous... Un emoji va apparaître !\nSoyez le **premier** à réagir avec le bon emoji !",
                color=COLORS["info"]
            )
            msg = await ctx.send(embed=embed)

            await asyncio.sleep(delay)

            embed.description = f"# RÉAGIS AVEC {target_emoji} !"
            embed.color = 0xFF0000
            await msg.edit(embed=embed)

            def check(reaction, user):
                return (
                    reaction.message.id == msg.id
                    and str(reaction.emoji) == target_emoji
                    and not user.bot
                )

            try:
                reaction, winner = await self.bot.wait_for("reaction_add", check=check, timeout=10)
                xp_earned, _, level_up, new_level = add_xp(winner.id, MINIGAME_XP["reaction"], "reaction_game")

                embed = discord.Embed(
                    title="🎯 Réaction — Victoire !",
                    description=f"{winner.mention} a été le plus rapide !\n**+{xp_earned} XP** gagnés !",
                    color=COLORS["success"]
                )
                await msg.edit(embed=embed)

                if level_up:
                    from community import CommunitySystem
                    cog = self.bot.get_cog("CommunitySystem")
                    if cog:
                        await cog.announce_level_up(winner.id, new_level)

            except asyncio.TimeoutError:
                embed = discord.Embed(
                    title="🎯 Réaction — Temps écoulé !",
                    description="Personne n'a réagi à temps... 😔",
                    color=COLORS["error"]
                )
                await msg.edit(embed=embed)
        finally:
            self._clear_game(ctx.channel.id)

    # ═══════════════════════════════════════════════════════════════════════════
    # 🔤 UNSCRAMBLE - Mot mélangé
    # ═══════════════════════════════════════════════════════════════════════════

    @commands.command(name="unscramble")
    @commands.cooldown(1, 15, commands.BucketType.channel)
    async def unscramble_game(self, ctx):
        """Remets les lettres dans le bon ordre !"""
        if self._is_game_active(ctx.channel.id):
            return await ctx.send("❌ Un jeu est déjà en cours dans ce channel !")

        self._set_game(ctx.channel.id, "unscramble")

        try:
            word = random.choice(MANGA_WORDS)
            scrambled = list(word)
            attempts = 0
            while ''.join(scrambled) == word and attempts < 10:
                random.shuffle(scrambled)
                attempts += 1
            scrambled = ''.join(scrambled).upper()

            embed = discord.Embed(
                title="🔤 Unscramble",
                description=f"Remettez les lettres dans le bon ordre !\n\n# `{scrambled}`\n\n*{len(word)} lettres — 30 secondes*",
                color=COLORS["info"]
            )
            await ctx.send(embed=embed)

            def check(m):
                return (
                    m.channel.id == ctx.channel.id
                    and not m.author.bot
                    and normalize(m.content.strip()) == normalize(word)
                )

            try:
                msg = await self.bot.wait_for("message", check=check, timeout=30)
                xp_earned, _, level_up, new_level = add_xp(msg.author.id, MINIGAME_XP["unscramble"], "unscramble")

                embed = discord.Embed(
                    title="🔤 Unscramble — Bravo !",
                    description=f"{msg.author.mention} a trouvé le mot **{word}** !\n**+{xp_earned} XP** gagnés !",
                    color=COLORS["success"]
                )
                await ctx.send(embed=embed)

                if level_up:
                    cog = self.bot.get_cog("CommunitySystem")
                    if cog:
                        await cog.announce_level_up(msg.author.id, new_level)

            except asyncio.TimeoutError:
                embed = discord.Embed(
                    title="🔤 Unscramble — Temps écoulé !",
                    description=f"Personne n'a trouvé ! Le mot était **{word}**",
                    color=COLORS["error"]
                )
                await ctx.send(embed=embed)
        finally:
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

        result = random.choice(["pile", "face"])
        win = random.random() < 0.5

        embed = discord.Embed(title="🪙 Coinflip", color=COLORS["info"])
        embed.description = f"La pièce tourne..."
        msg = await ctx.send(embed=embed)

        await asyncio.sleep(1.5)

        if win:
            xp_earned, _, level_up, new_level = add_xp(ctx.author.id, mise, "coinflip_win")
            embed.title = f"🪙 {result.upper()} — Tu gagnes !"
            embed.description = f"**+{xp_earned} XP** gagnés !\n💰 Solde : {stats.get('xp', 0):,} XP"
            embed.color = COLORS["success"]

            if level_up:
                cog = self.bot.get_cog("CommunitySystem")
                if cog:
                    await cog.announce_level_up(ctx.author.id, new_level)
        else:
            remove_xp(ctx.author.id, mise)
            embed.title = f"🪙 {result.upper()} — Tu perds !"
            embed.description = f"**-{mise} XP** perdus...\n💰 Solde : {stats.get('xp', 0):,} XP"
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
            embed.title = title
            embed.description = f"{display}\n\n🎉 **x{multiplier}** — **+{xp_earned} XP** !"
            embed.color = 0xFFD700

            if level_up:
                cog = self.bot.get_cog("CommunitySystem")
                if cog:
                    await cog.announce_level_up(ctx.author.id, new_level)

        elif reels[0] == reels[1] or reels[1] == reels[2] or reels[0] == reels[2]:
            # 2 identiques
            gain = mise
            xp_earned, _, level_up, new_level = add_xp(ctx.author.id, gain, "slots_small")
            embed.title = "🎰 Petite victoire !"
            embed.description = f"{display}\n\n**+{xp_earned} XP** gagnés !"
            embed.color = COLORS["success"]

            if level_up:
                cog = self.bot.get_cog("CommunitySystem")
                if cog:
                    await cog.announce_level_up(ctx.author.id, new_level)
        else:
            # Perdu
            remove_xp(ctx.author.id, mise)
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
            embed.title = "🎡 Roulette — Tu gagnes !"
            embed.description = f"{result_text}\n\n**x{multiplier}** — **+{xp_earned} XP** !"
            embed.color = COLORS["success"]

            if level_up:
                cog = self.bot.get_cog("CommunitySystem")
                if cog:
                    await cog.announce_level_up(ctx.author.id, new_level)
        else:
            remove_xp(ctx.author.id, mise)
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

        # Demander l'acceptation
        embed = discord.Embed(
            title="⚔️ Défi en Duel !",
            description=(
                f"{ctx.author.mention} défie {adversaire.mention} !\n"
                f"💰 Mise : **{mise} XP**\n\n"
                f"{adversaire.mention}, réagis avec ✅ pour accepter ou ❌ pour refuser."
            ),
            color=COLORS["warning"]
        )
        msg = await ctx.send(embed=embed)
        await msg.add_reaction("✅")
        await msg.add_reaction("❌")

        def check(reaction, user):
            return (
                reaction.message.id == msg.id
                and user.id == adversaire.id
                and str(reaction.emoji) in ("✅", "❌")
            )

        try:
            reaction, _ = await self.bot.wait_for("reaction_add", check=check, timeout=60)

            if str(reaction.emoji) == "❌":
                embed.title = "⚔️ Duel refusé"
                embed.description = f"{adversaire.display_name} a refusé le duel."
                embed.color = COLORS["error"]
                return await msg.edit(embed=embed)

        except asyncio.TimeoutError:
            embed.title = "⚔️ Duel expiré"
            embed.description = "Pas de réponse... Le duel est annulé."
            embed.color = COLORS["error"]
            return await msg.edit(embed=embed)

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
            cog = self.bot.get_cog("CommunitySystem")
            if cog:
                await cog.announce_level_up(winner.id, new_level)

    # ═══════════════════════════════════════════════════════════════════════════
    # 🟩 WORDLE - Deviner un mot en 6 essais
    # ═══════════════════════════════════════════════════════════════════════════

    @commands.command(name="wordle")
    @commands.cooldown(1, 30, commands.BucketType.user)
    async def wordle(self, ctx):
        """Devine le mot en 6 essais ! 🟩 = bonne place, 🟨 = mauvaise place, ⬛ = absent"""
        if self._is_game_active(ctx.channel.id):
            return await ctx.send("❌ Un jeu est déjà en cours dans ce channel !")

        self._set_game(ctx.channel.id, "wordle")

        try:
            word = random.choice(WORDLE_WORDS)
            word_normalized = normalize(word)
            word_len = len(word_normalized)
            max_attempts = 6
            attempts = []

            embed = discord.Embed(
                title="🟩 Wordle Manga",
                description=(
                    f"Devine le mot en **{max_attempts} essais** !\n"
                    f"Le mot fait **{word_len} lettres**.\n\n"
                    f"🟩 = bonne lettre, bonne place\n"
                    f"🟨 = bonne lettre, mauvaise place\n"
                    f"⬛ = lettre absente\n\n"
                    f"*Tape ton essai dans le chat !*"
                ),
                color=COLORS["info"]
            )
            game_msg = await ctx.send(embed=embed)

            for attempt_num in range(1, max_attempts + 1):
                def check(m):
                    return (
                        m.channel.id == ctx.channel.id
                        and m.author.id == ctx.author.id
                        and len(normalize(m.content.strip())) == word_len
                        and m.content.strip().isalpha()
                    )

                try:
                    msg = await self.bot.wait_for("message", check=check, timeout=60)
                except asyncio.TimeoutError:
                    embed.title = "🟩 Wordle — Temps écoulé !"
                    embed.description = f"Le mot était **{word}** !"
                    embed.color = COLORS["error"]
                    attempts.append("⬛" * word_len + f" ~~{normalize(msg.content.strip()) if 'msg' in dir() else '?'}~~")
                    return await game_msg.edit(embed=embed)

                guess = normalize(msg.content.strip())

                # Générer le feedback
                feedback = []
                word_chars = list(word_normalized)
                guess_chars = list(guess)
                result = ["⬛"] * word_len

                # Premier passage : lettres correctes (bonne place)
                for i in range(word_len):
                    if guess_chars[i] == word_chars[i]:
                        result[i] = "🟩"
                        word_chars[i] = None
                        guess_chars[i] = None

                # Second passage : lettres présentes (mauvaise place)
                for i in range(word_len):
                    if guess_chars[i] is not None and guess_chars[i] in word_chars:
                        result[i] = "🟨"
                        word_chars[word_chars.index(guess_chars[i])] = None

                feedback_str = "".join(result)
                attempts.append(f"{feedback_str} `{guess.upper()}`")

                # Victoire ?
                if guess == word_normalized:
                    bonus = max(10, MINIGAME_XP["wordle"] + (max_attempts - attempt_num) * 10)
                    xp_earned, _, level_up, new_level = add_xp(ctx.author.id, bonus, "wordle")

                    embed.title = "🟩 Wordle — Bravo !"
                    embed.description = (
                        "\n".join(attempts) +
                        f"\n\n🎉 Trouvé en **{attempt_num}/{max_attempts}** essais !\n"
                        f"**+{xp_earned} XP** gagnés !"
                    )
                    embed.color = COLORS["success"]
                    await game_msg.edit(embed=embed)

                    if level_up:
                        cog = self.bot.get_cog("CommunitySystem")
                        if cog:
                            await cog.announce_level_up(ctx.author.id, new_level)
                    return

                # Mettre à jour l'embed
                remaining = max_attempts - attempt_num
                embed.description = (
                    "\n".join(attempts) +
                    f"\n\n*{remaining} essai(s) restant(s)*"
                )
                await game_msg.edit(embed=embed)

            # Défaite
            embed.title = "🟩 Wordle — Perdu !"
            embed.description = "\n".join(attempts) + f"\n\nLe mot était **{word}** !"
            embed.color = COLORS["error"]
            await game_msg.edit(embed=embed)

        finally:
            self._clear_game(ctx.channel.id)

    # ═══════════════════════════════════════════════════════════════════════════
    # 💀 HANGMAN - Pendu
    # ═══════════════════════════════════════════════════════════════════════════

    @commands.command(name="hangman", aliases=["pendu"])
    @commands.cooldown(1, 15, commands.BucketType.channel)
    async def hangman(self, ctx):
        """Jeu du pendu ! Devine le mot lettre par lettre"""
        if self._is_game_active(ctx.channel.id):
            return await ctx.send("❌ Un jeu est déjà en cours dans ce channel !")

        self._set_game(ctx.channel.id, "hangman")

        try:
            word = random.choice(MANGA_WORDS)
            word_normalized = normalize(word)
            guessed_letters = set()
            wrong_guesses = 0
            max_wrong = len(HANGMAN_STAGES) - 1

            def get_display():
                return " ".join(
                    c.upper() if normalize(c) in guessed_letters else "\_"
                    for c in word
                )

            def build_embed():
                display = get_display()
                embed = discord.Embed(
                    title="💀 Pendu",
                    description=f"{HANGMAN_STAGES[wrong_guesses]}\n\n**{display}**\n\n*{len(word)} lettres*",
                    color=COLORS["info"]
                )
                if guessed_letters:
                    embed.add_field(
                        name="Lettres essayées",
                        value=" ".join(sorted(l.upper() for l in guessed_letters))
                    )
                embed.set_footer(text=f"Erreurs : {wrong_guesses}/{max_wrong} — Tape une lettre !")
                return embed

            game_msg = await ctx.send(embed=build_embed())

            while wrong_guesses < max_wrong:
                def check(m):
                    return (
                        m.channel.id == ctx.channel.id
                        and not m.author.bot
                        and len(m.content.strip()) == 1
                        and m.content.strip().isalpha()
                    )

                try:
                    msg = await self.bot.wait_for("message", check=check, timeout=60)
                except asyncio.TimeoutError:
                    embed = discord.Embed(
                        title="💀 Pendu — Temps écoulé !",
                        description=f"Le mot était **{word}** !",
                        color=COLORS["error"]
                    )
                    return await game_msg.edit(embed=embed)

                letter = normalize(msg.content.strip().lower())

                if letter in guessed_letters:
                    await msg.reply(f"❌ `{letter.upper()}` déjà essayée !", delete_after=3)
                    continue

                guessed_letters.add(letter)

                if letter in word_normalized:
                    # Vérifier si le mot est complet
                    if all(normalize(c) in guessed_letters for c in word):
                        xp_earned, _, level_up, new_level = add_xp(msg.author.id, MINIGAME_XP["hangman"], "hangman")
                        embed = discord.Embed(
                            title="💀 Pendu — Victoire !",
                            description=(
                                f"Le mot était **{word}** !\n\n"
                                f"🎉 {msg.author.mention} a trouvé la dernière lettre !\n"
                                f"**+{xp_earned} XP** gagnés !"
                            ),
                            color=COLORS["success"]
                        )
                        await game_msg.edit(embed=embed)

                        if level_up:
                            cog = self.bot.get_cog("CommunitySystem")
                            if cog:
                                await cog.announce_level_up(msg.author.id, new_level)
                        return
                else:
                    wrong_guesses += 1

                await game_msg.edit(embed=build_embed())

            # Défaite
            embed = discord.Embed(
                title="💀 Pendu — Défaite !",
                description=f"{HANGMAN_STAGES[-1]}\n\nLe mot était **{word}** !",
                color=COLORS["error"]
            )
            await game_msg.edit(embed=embed)

        finally:
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

        self._set_game(ctx.channel.id, "chain")

        try:
            start_word = random.choice(["manga", "anime", "combat", "magie", "epee", "demon"])
            used_words = {start_word}
            current_letter = normalize(start_word[-1])
            last_player = None
            participants = {}  # user_id -> count

            embed = discord.Embed(
                title="🔗 Chaîne de Mots",
                description=(
                    f"Le premier mot est : **{start_word.upper()}**\n\n"
                    f"Tapez un mot qui commence par la lettre **`{current_letter.upper()}`** !\n"
                    f"⏱️ **15 secondes** par tour — dernier debout gagne !\n\n"
                    f"*Règles : min. 3 lettres, pas de répétition, pas 2x d'affilée le même joueur*"
                ),
                color=COLORS["info"]
            )
            await ctx.send(embed=embed)

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
                    msg = await self.bot.wait_for("message", check=check, timeout=15)
                except asyncio.TimeoutError:
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
                        cog = self.bot.get_cog("CommunitySystem")
                        if cog:
                            await cog.announce_level_up(winner_id, new_level)
                    return

                word = normalize(msg.content.strip().lower())
                used_words.add(word)
                current_letter = word[-1]
                last_player = msg.author.id
                participants[msg.author.id] = participants.get(msg.author.id, 0) + 1

                await msg.add_reaction("✅")

        finally:
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


async def setup(bot):
    """Setup pour discord.py 2.0+"""
    await bot.add_cog(MiniGames(bot))
    logging.info("✅ Cog MiniGames chargé avec succès")
