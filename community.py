# community.py
# ═══════════════════════════════════════════════════════════════════════════════
# SYSTÈME COMMUNAUTAIRE - NIVEAUX XP AUTOMATIQUES PAR ACTIVITÉ
# ═══════════════════════════════════════════════════════════════════════════════

import discord
from discord.ext import commands, tasks
import json
import os
import random
import asyncio
import math
from datetime import datetime, timedelta
from config import (
    COLORS, ADMIN_ROLES, DATA_FILES, XP_GAINS, CHANNELS,
    POINTS_ALLOWED_CHANNELS, MANGA_EMOJIS, LEVELS
)
from utils import load_json, save_json
import logging

# Alias pour compatibilité
POINTS = XP_GAINS

# Fichiers de données
USER_STATS_FILE = DATA_FILES["user_stats"]
os.makedirs("data", exist_ok=True)

# Données en mémoire
user_stats = {}

# Cooldowns pour les gains d'XP par message
message_cooldowns = {}

# Tracking temps vocal
voice_tracking = {}

# Questions trivia
TRIVIA_QUESTIONS = {
    "easy": [
        {
            "question": "Quel manga parle d'exorcistes qui combattent des démons ?",
            "answer": "ao no exorcist",
            "hints": ["Rin Okumura", "Flammes bleues", "Satan"]
        },
        {
            "question": "Dans quel manga le héros utilise des maldictions ?",
            "answer": "tougen anki",
            "hints": ["Shiki", "Oni", "Maldictions"]
        },
        {
            "question": "Quel manga se déroule dans les bas-fonds de Tokyo ?",
            "answer": "tokyo underworld",
            "hints": ["Yakuza", "Gangs", "Survie"]
        },
    ],
    "medium": [
        {
            "question": "Quel est le prénom du protagoniste de Ao No Exorcist ?",
            "answer": "rin",
            "hints": ["Frère de Yukio", "Fils de Satan", "Flammes bleues"]
        },
        {
            "question": "Comment s'appelle l'équipe de foot dans Catenaccio ?",
            "answer": "inter",
            "hints": ["Milan", "Italie", "Football"]
        },
    ],
    "hard": [
        {
            "question": "Quel est le nom de la technique de combat principale dans Tougen Anki ?",
            "answer": "jingi",
            "hints": ["Maldictions", "Transformation", "Pouvoir oni"]
        },
    ]
}


# ═══════════════════════════════════════════════════════════════════════════════
# FONCTIONS DE CALCUL DE NIVEAU
# ═══════════════════════════════════════════════════════════════════════════════

def xp_for_level(level):
    """Calcule l'XP total nécessaire pour atteindre un niveau donné"""
    if level <= 0:
        return 0
    base = LEVELS["xp_per_level_base"]
    growth = LEVELS["xp_growth_factor"]
    total = 0
    for i in range(1, level + 1):
        total += int(base * (growth ** (i - 1)))
    return total


def calculate_level(total_xp):
    """Calcule le niveau actuel à partir de l'XP total"""
    level = 0
    max_level = LEVELS["max_level"]
    while level < max_level:
        xp_needed = xp_for_level(level + 1)
        if total_xp < xp_needed:
            break
        level += 1
    return level


def xp_progress(total_xp):
    """
    Retourne (niveau_actuel, xp_dans_le_niveau, xp_requis_pour_prochain)
    """
    level = calculate_level(total_xp)
    max_level = LEVELS["max_level"]

    if level >= max_level:
        return level, 0, 0

    xp_current_level = xp_for_level(level)
    xp_next_level = xp_for_level(level + 1)
    xp_in_level = total_xp - xp_current_level
    xp_needed = xp_next_level - xp_current_level

    return level, xp_in_level, xp_needed


def generate_xp_bar(current, needed, length=10):
    """Génère une barre de progression visuelle"""
    if needed <= 0:
        return "█" * length + " MAX"
    filled = int((current / needed) * length)
    filled = min(filled, length)
    empty = length - filled
    percentage = int((current / needed) * 100)
    return f"{'█' * filled}{'░' * empty} {percentage}%"


def charger_donnees():
    """Charge les données utilisateurs et migre les anciens champs si nécessaire"""
    global user_stats
    user_stats = load_json(USER_STATS_FILE, {})

    # Migration : points → xp pour les anciens profils
    migrated = False
    for uid, stats in user_stats.items():
        if "points" in stats and "xp" not in stats:
            stats["xp"] = stats.pop("points")
            migrated = True
        if "total_points_earned" in stats and "total_xp" not in stats:
            stats["total_xp"] = stats.pop("total_points_earned")
            migrated = True
        if "weekly_points" in stats and "weekly_xp" not in stats:
            stats["weekly_xp"] = stats.pop("weekly_points")
            migrated = True

    if migrated:
        sauvegarder_donnees()
        logging.info("📦 Migration points → xp effectuée")

    logging.info(f"✅ Stats de {len(user_stats)} utilisateur(s) chargées")


def sauvegarder_donnees():
    """Sauvegarde les données"""
    try:
        with open(USER_STATS_FILE, "w", encoding="utf-8") as f:
            json.dump(user_stats, f, ensure_ascii=False, indent=4)
        logging.info(f"✅ Stats sauvegardées ({len(user_stats)} utilisateurs)")
    except Exception as e:
        logging.error(f"❌ Erreur sauvegarde: {e}")


def get_user_stats(user_id):
    """Récupère ou crée les stats d'un utilisateur"""
    user_id_str = str(user_id)
    if user_id_str not in user_stats:
        user_stats[user_id_str] = {
            "xp": 0,
            "total_xp": 0,
            "messages_count": 0,
            "voice_minutes": 0,
            "chapter_reactions": 0,
            "trivia_correct": 0,
            "badges": [],
            "joined_at": datetime.now().isoformat(),
            "last_activity": datetime.now().isoformat(),
            "daily_streak": 0,
            "last_daily": None,
            "last_seniority_bonus": None,
            "weekly_xp": 0,
            "week_start": datetime.now().isocalendar()[1]
        }
    else:
        # Migration on-the-fly pour les anciens profils
        s = user_stats[user_id_str]
        if "points" in s and "xp" not in s:
            s["xp"] = s.pop("points")
        if "total_points_earned" in s and "total_xp" not in s:
            s["total_xp"] = s.pop("total_points_earned")
        if "weekly_points" in s and "weekly_xp" not in s:
            s["weekly_xp"] = s.pop("weekly_points")
        # Assurer les clés par défaut
        s.setdefault("xp", 0)
        s.setdefault("total_xp", 0)
        s.setdefault("weekly_xp", 0)

    return user_stats[user_id_str]


def get_active_multiplier(user_id):
    """
    Récupère le multiplicateur d'XP actif pour un utilisateur.
    Vérifie les boosts dans l'inventaire shop.
    """
    try:
        from shop import get_user_inventory
        inv = get_user_inventory(user_id)
        active_boosts = inv.get("active_boosts", {})

        multiplier = 1.0
        expired_boosts = []

        for boost_id, boost_data in active_boosts.items():
            if "expires" in boost_data:
                expires = datetime.fromisoformat(boost_data["expires"])
                if datetime.now() >= expires:
                    expired_boosts.append(boost_id)
                    continue

            if boost_id == "double_points":
                multiplier *= boost_data.get("multiplier", 2)
            elif boost_id == "triple_points":
                multiplier *= boost_data.get("multiplier", 3)

        if expired_boosts:
            for boost_id in expired_boosts:
                del active_boosts[boost_id]
            from shop import sauvegarder_shop
            sauvegarder_shop()

        return multiplier
    except Exception as e:
        logging.error(f"Erreur get_active_multiplier: {e}")
        return 1.0


def add_xp(user_id, amount, reason=""):
    """
    Ajoute de l'XP à un utilisateur AVEC multiplicateurs.
    Retourne (xp_final, multiplicateur, level_up: bool, nouveau_niveau: int)
    """
    stats = get_user_stats(user_id)
    old_level = calculate_level(stats.get("total_xp", 0))

    if amount > 0:
        multiplier = get_active_multiplier(user_id)
        final_amount = int(amount * multiplier)
        stats["total_xp"] = stats.get("total_xp", 0) + final_amount
    else:
        multiplier = 1.0
        final_amount = amount

    stats["xp"] = stats.get("xp", 0) + final_amount
    stats["last_activity"] = datetime.now().isoformat()

    # Mise à jour stats hebdomadaires
    current_week = datetime.now().isocalendar()[1]
    if stats.get("week_start") != current_week:
        stats["week_start"] = current_week
        stats["weekly_xp"] = 0

    if final_amount > 0:
        stats["weekly_xp"] = stats.get("weekly_xp", 0) + final_amount

    sauvegarder_donnees()

    # Calculer le nouveau niveau
    new_level = calculate_level(stats.get("total_xp", 0))
    level_up = new_level > old_level

    # Vérifier les badges
    if final_amount > 0:
        try:
            from achievements import check_badges
            check_badges(user_id, stats)
        except:
            pass

    return final_amount, multiplier, level_up, new_level


# Alias de compatibilité pour les autres modules (shop, achievements)
def add_points(user_id, amount, reason=""):
    """Alias de compatibilité - utilise add_xp en interne"""
    final, mult, _, _ = add_xp(user_id, amount, reason)
    return final, mult


class CommunitySystem(commands.Cog):
    """Système communautaire avec gains d'XP automatiques et niveaux"""

    def __init__(self, bot):
        self.bot = bot
        charger_donnees()
        self.voice_check_loop.start()
        self.seniority_bonus_loop.start()

    def cog_unload(self):
        self.voice_check_loop.cancel()
        self.seniority_bonus_loop.cancel()
        sauvegarder_donnees()

    async def announce_level_up(self, user_id, new_level, channel=None):
        """Annonce un level-up et attribue les rôles de niveau"""
        try:
            guild = self.bot.guilds[0] if self.bot.guilds else None
            if not guild:
                return

            member = guild.get_member(user_id)
            if not member:
                try:
                    member = await guild.fetch_member(user_id)
                except:
                    return

            # Attribuer le rôle de niveau si configuré
            level_roles = LEVELS.get("level_roles", {})
            if new_level in level_roles:
                role_id = level_roles[new_level]
                role = guild.get_role(role_id)
                if role and role not in member.roles:
                    try:
                        await member.add_roles(role)
                    except:
                        pass

            # Envoyer l'annonce
            announce_channel_id = LEVELS.get("announce_channel")
            if announce_channel_id:
                announce_channel = self.bot.get_channel(announce_channel_id)
            elif channel:
                announce_channel = channel
            else:
                return

            if not announce_channel:
                return

            # Embed de level-up
            level_emojis = {
                10: "⭐", 20: "🌟", 30: "💫", 40: "✨",
                50: "🔥", 60: "💎", 70: "👑", 80: "🏆",
                90: "🌈", 100: "🎆"
            }
            emoji = "🎉"
            for threshold in sorted(level_emojis.keys(), reverse=True):
                if new_level >= threshold:
                    emoji = level_emojis[threshold]
                    break

            stats = get_user_stats(user_id)
            level, xp_in, xp_needed = xp_progress(stats.get("total_xp", 0))
            bar = generate_xp_bar(xp_in, xp_needed)

            embed = discord.Embed(
                title=f"{emoji} LEVEL UP !",
                description=f"{member.mention} est passé au **niveau {new_level}** !",
                color=0xFFD700
            )
            embed.add_field(name="📊 Progression", value=f"```{bar}```", inline=False)

            # Bonus de rôle si applicable
            if new_level in level_roles:
                role = guild.get_role(level_roles[new_level])
                if role:
                    embed.add_field(name="🎁 Récompense", value=f"Rôle {role.mention} obtenu !", inline=False)

            embed.set_thumbnail(url=member.display_avatar.url)
            embed.set_footer(text="Continue comme ça !")

            await announce_channel.send(embed=embed)

        except Exception as e:
            logging.error(f"Erreur announce_level_up: {e}")

    # ═══════════════════════════════════════════════════════════════════════════
    # SYSTÈME DE GAIN PAR MESSAGE
    # ═══════════════════════════════════════════════════════════════════════════

    @commands.Cog.listener()
    async def on_message(self, message):
        """Gain d'XP passif par message"""
        if message.author.bot:
            return

        if message.channel.id not in POINTS_ALLOWED_CHANNELS:
            return

        user_id = message.author.id
        now = datetime.now()

        # Vérifier cooldown
        if user_id in message_cooldowns:
            last_time = message_cooldowns[user_id]
            if (now - last_time).total_seconds() < XP_GAINS["message_cooldown"]:
                return

        # Gagner de l'XP
        xp_earned = random.randint(XP_GAINS["message_min"], XP_GAINS["message_max"])
        final_xp, multiplier, level_up, new_level = add_xp(user_id, xp_earned, "message")

        # Mettre à jour stats
        stats = get_user_stats(user_id)
        stats["messages_count"] += 1

        message_cooldowns[user_id] = now
        sauvegarder_donnees()

        # Annoncer level-up
        if level_up:
            await self.announce_level_up(user_id, new_level, message.channel)

    # ═══════════════════════════════════════════════════════════════════════════
    # SYSTÈME DE RÉACTIONS AUX ANNONCES
    # ═══════════════════════════════════════════════════════════════════════════

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        """Gain d'XP pour réactions sur annonces de chapitres"""
        if payload.user_id == self.bot.user.id:
            return

        if payload.channel_id != CHANNELS.get("chapter_announcements"):
            return

        valid_emojis = ['🔥', '👀', '❤', '❤️']
        if str(payload.emoji) not in valid_emojis:
            return

        try:
            channel = self.bot.get_channel(payload.channel_id)
            message = await channel.fetch_message(payload.message_id)

            user_reaction_count = 0
            for reaction in message.reactions:
                async for user in reaction.users():
                    if user.id == payload.user_id:
                        user_reaction_count += 1

            if user_reaction_count == 1:
                final_xp, multiplier, level_up, new_level = add_xp(
                    payload.user_id,
                    XP_GAINS["chapter_reaction"],
                    "chapter_reaction"
                )

                stats = get_user_stats(payload.user_id)
                stats["chapter_reactions"] += 1
                sauvegarder_donnees()

                logging.info(f"✅ {payload.user_id} a gagné {final_xp} XP (réaction chapitre)")

                if level_up:
                    await self.announce_level_up(payload.user_id, new_level, channel)

        except Exception as e:
            logging.error(f"Erreur réaction annonce: {e}")

    # ═══════════════════════════════════════════════════════════════════════════
    # SYSTÈME DE TRACKING VOCAL
    # ═══════════════════════════════════════════════════════════════════════════

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        """Track le temps passé en vocal"""
        if member.bot:
            return

        user_id = member.id

        if before.channel is None and after.channel is not None:
            voice_tracking[user_id] = datetime.now()
            logging.info(f"🎤 {member.name} a rejoint un vocal")

        elif before.channel is not None and after.channel is None:
            if user_id in voice_tracking:
                start_time = voice_tracking[user_id]
                duration = (datetime.now() - start_time).total_seconds() / 60

                intervals = int(duration / 15)
                if intervals > 0:
                    xp_earned = intervals * XP_GAINS["voice_per_15min"]
                    final_xp, multiplier, level_up, new_level = add_xp(user_id, xp_earned, "vocal")

                    stats = get_user_stats(user_id)
                    stats["voice_minutes"] += int(duration)
                    sauvegarder_donnees()

                    logging.info(f"🎤 {member.name} a gagné {final_xp} XP ({int(duration)} min en vocal)")

                    if level_up:
                        await self.announce_level_up(user_id, new_level)

                del voice_tracking[user_id]

    @tasks.loop(minutes=15)
    async def voice_check_loop(self):
        """Donne de l'XP toutes les 15 min aux users en vocal"""
        for user_id, start_time in list(voice_tracking.items()):
            duration = (datetime.now() - start_time).total_seconds() / 60
            if duration >= 15:
                final_xp, multiplier, level_up, new_level = add_xp(user_id, XP_GAINS["voice_per_15min"], "vocal_interval")

                stats = get_user_stats(user_id)
                stats["voice_minutes"] += 15

                voice_tracking[user_id] = datetime.now()

                logging.info(f"🎤 User {user_id} a gagné {final_xp} XP (15 min vocal)")

                if level_up:
                    await self.announce_level_up(user_id, new_level)
                    await asyncio.sleep(1.5)

        sauvegarder_donnees()

    @voice_check_loop.before_loop
    async def before_voice_check(self):
        await self.bot.wait_until_ready()

    # ═══════════════════════════════════════════════════════════════════════════
    # BONUS D'ANCIENNETÉ (HEBDOMADAIRE)
    # ═══════════════════════════════════════════════════════════════════════════

    @tasks.loop(hours=24)
    async def seniority_bonus_loop(self):
        """Donne le bonus d'ancienneté hebdomadaire"""
        today = datetime.now().date()

        if today.weekday() != 0:
            return

        guild = self.bot.guilds[0] if self.bot.guilds else None
        if not guild:
            return

        for member in guild.members:
            if member.bot:
                continue

            stats = get_user_stats(member.id)
            last_bonus = stats.get("last_seniority_bonus")

            if last_bonus:
                last_date = datetime.fromisoformat(last_bonus).date()
                if (today - last_date).days < 7:
                    continue

            joined_at = member.joined_at
            if joined_at:
                days_on_server = (datetime.now(joined_at.tzinfo) - joined_at).days

                if days_on_server < 30:
                    bonus = XP_GAINS["seniority_base"]
                elif days_on_server < 90:
                    bonus = 100
                elif days_on_server < 180:
                    bonus = 150
                else:
                    bonus = XP_GAINS["seniority_max"]

                final_xp, multiplier, level_up, new_level = add_xp(member.id, bonus, "seniority")
                stats["last_seniority_bonus"] = datetime.now().isoformat()

                logging.info(f"🏅 {member.name} a reçu {final_xp} XP (ancienneté: {days_on_server} jours)")

                if level_up:
                    await self.announce_level_up(member.id, new_level)
                    await asyncio.sleep(1.5)

        sauvegarder_donnees()

    @seniority_bonus_loop.before_loop
    async def before_seniority_check(self):
        await self.bot.wait_until_ready()

    # ═══════════════════════════════════════════════════════════════════════════
    # COMMANDES - BONUS QUOTIDIEN
    # ═══════════════════════════════════════════════════════════════════════════

    @commands.command(name="daily")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def daily_bonus(self, ctx):
        """Récupère le bonus quotidien avec streak"""
        stats = get_user_stats(ctx.author.id)
        today = datetime.now().date().isoformat()

        if stats.get("last_daily") == today:
            next_daily = datetime.now() + timedelta(days=1)
            next_daily = next_daily.replace(hour=0, minute=0, second=0)
            timestamp = int(next_daily.timestamp())

            embed = discord.Embed(
                title="⏱️ Bonus déjà réclamé",
                description=f"Tu as déjà réclamé ton bonus aujourd'hui !\nReviens <t:{timestamp}:R>",
                color=COLORS["warning"]
            )
            embed.add_field(name="🔥 Streak actuel", value=f"{stats.get('daily_streak', 0)} jours")
            await ctx.send(embed=embed)
            return

        # Calculer le streak
        last_daily = stats.get("last_daily")
        if last_daily:
            last_date = datetime.fromisoformat(last_daily).date()
            today_date = datetime.now().date()
            diff = (today_date - last_date).days

            if diff == 1:
                stats["daily_streak"] += 1
            elif diff > 1:
                stats["daily_streak"] = 1
        else:
            stats["daily_streak"] = 1

        stats["last_daily"] = today

        # Calculer le bonus
        base_bonus = random.randint(XP_GAINS["daily_min"], XP_GAINS["daily_max"])
        streak_bonus = min(stats["daily_streak"] * XP_GAINS["streak_bonus"], XP_GAINS["streak_max_bonus"])
        total_bonus = base_bonus + streak_bonus

        final_xp, multiplier, level_up, new_level = add_xp(ctx.author.id, total_bonus, "daily")

        # Info niveau
        level, xp_in, xp_needed = xp_progress(stats.get("total_xp", 0))
        bar = generate_xp_bar(xp_in, xp_needed)

        embed = discord.Embed(
            title="🎁 Bonus quotidien réclamé !",
            description=f"Tu as reçu **{final_xp} XP** !",
            color=COLORS["success"],
            timestamp=datetime.now()
        )

        embed.add_field(name="💰 Bonus de base", value=f"{base_bonus} XP", inline=True)
        embed.add_field(name="🔥 Bonus streak", value=f"+{streak_bonus} XP", inline=True)
        embed.add_field(name="⚡ Total", value=f"**{final_xp} XP**", inline=True)

        embed.add_field(
            name="📊 Progression",
            value=(
                f"🔥 Streak: **{stats['daily_streak']} jour(s)**\n"
                f"📈 Niveau **{level}** — {stats.get('xp', 0):,} XP\n"
                f"```{bar}```"
            ),
            inline=False
        )

        if multiplier > 1:
            embed.add_field(name="⚡ Multiplicateur actif", value=f"x{multiplier:.1f}", inline=True)

        embed.set_footer(text="Reviens demain pour continuer ton streak !")
        embed.set_thumbnail(url=ctx.author.avatar.url if ctx.author.avatar else None)

        sauvegarder_donnees()
        await ctx.send(embed=embed)

        if level_up:
            await self.announce_level_up(ctx.author.id, new_level, ctx.channel)

    # ═══════════════════════════════════════════════════════════════════════════
    # COMMANDES - MINI-JEUX
    # ═══════════════════════════════════════════════════════════════════════════

    @commands.command(name="trivia")
    @commands.cooldown(1, 30, commands.BucketType.user)
    async def trivia_game(self, ctx, difficulty: str = "easy"):
        """Lance un quiz manga (easy/medium/hard)"""
        difficulty = difficulty.lower()

        if difficulty not in ["easy", "medium", "hard"]:
            await ctx.send("❌ Difficulté invalide ! Utilise: `easy`, `medium` ou `hard`")
            return

        questions = TRIVIA_QUESTIONS.get(difficulty, [])
        if not questions:
            await ctx.send("❌ Aucune question disponible pour cette difficulté.")
            return

        question_data = random.choice(questions)

        xp_reward = {
            "easy": XP_GAINS["trivia_easy"],
            "medium": XP_GAINS["trivia_medium"],
            "hard": XP_GAINS["trivia_hard"]
        }[difficulty]

        embed = discord.Embed(
            title=f"🎮 Quiz Manga - {difficulty.capitalize()}",
            description=question_data["question"],
            color=COLORS["info"]
        )
        embed.add_field(name="🏆 Récompense", value=f"{xp_reward} XP", inline=True)
        embed.add_field(name="⏱️ Temps", value="30 secondes", inline=True)
        embed.set_footer(text="Réponds directement dans le chat !")

        await ctx.send(embed=embed)

        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel

        try:
            msg = await self.bot.wait_for('message', check=check, timeout=30)

            if msg.content.lower().strip() == question_data["answer"].lower():
                final_xp, multiplier, level_up, new_level = add_xp(ctx.author.id, xp_reward, "trivia")

                stats = get_user_stats(ctx.author.id)
                stats["trivia_correct"] += 1
                sauvegarder_donnees()

                level, xp_in, xp_needed = xp_progress(stats.get("total_xp", 0))

                embed = discord.Embed(
                    title="✅ Bonne réponse !",
                    description=f"Bravo ! Tu gagnes **{final_xp} XP** !",
                    color=COLORS["success"]
                )
                embed.add_field(name="📈 Niveau", value=f"Nv. {level} — {stats.get('xp', 0):,} XP")
                await ctx.send(embed=embed)

                if level_up:
                    await self.announce_level_up(ctx.author.id, new_level, ctx.channel)
            else:
                embed = discord.Embed(
                    title="❌ Mauvaise réponse",
                    description=f"La bonne réponse était: **{question_data['answer']}**",
                    color=COLORS["error"]
                )
                await ctx.send(embed=embed)

        except asyncio.TimeoutError:
            embed = discord.Embed(
                title="⏱️ Temps écoulé",
                description=f"La bonne réponse était: **{question_data['answer']}**",
                color=COLORS["warning"]
            )
            await ctx.send(embed=embed)

    @commands.command(name="guess")
    @commands.cooldown(1, 30, commands.BucketType.user)
    async def guess_game(self, ctx):
        """Devine le manga à partir d'un emoji"""
        manga_list = list(MANGA_EMOJIS.items())
        correct_manga, emoji = random.choice(manga_list)

        embed = discord.Embed(
            title="🎮 Devine le manga !",
            description=f"Quel manga représente cet emoji ?\n\n# {emoji}",
            color=COLORS["info"]
        )
        embed.add_field(name="🏆 Récompense", value=f"{XP_GAINS['guess_correct']} XP")
        embed.add_field(name="⏱️ Temps", value="20 secondes")
        embed.set_footer(text="Écris le nom du manga dans le chat !")

        await ctx.send(embed=embed)

        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel

        try:
            msg = await self.bot.wait_for('message', check=check, timeout=20)

            if msg.content.lower().replace(" ", "") in correct_manga.lower().replace(" ", ""):
                final_xp, multiplier, level_up, new_level = add_xp(ctx.author.id, XP_GAINS["guess_correct"], "guess")

                stats = get_user_stats(ctx.author.id)
                sauvegarder_donnees()

                level, xp_in, xp_needed = xp_progress(stats.get("total_xp", 0))

                embed = discord.Embed(
                    title="✅ Correct !",
                    description=f"C'était bien **{correct_manga}** !\nTu gagnes **{final_xp} XP** !",
                    color=COLORS["success"]
                )
                embed.add_field(name="📈 Niveau", value=f"Nv. {level} — {stats.get('xp', 0):,} XP")
                await ctx.send(embed=embed)

                if level_up:
                    await self.announce_level_up(ctx.author.id, new_level, ctx.channel)
            else:
                embed = discord.Embed(
                    title="❌ Raté !",
                    description=f"C'était: **{correct_manga}**",
                    color=COLORS["error"]
                )
                await ctx.send(embed=embed)

        except asyncio.TimeoutError:
            embed = discord.Embed(
                title="⏱️ Temps écoulé",
                description=f"C'était: **{correct_manga}**",
                color=COLORS["warning"]
            )
            await ctx.send(embed=embed)

    # ═══════════════════════════════════════════════════════════════════════════
    # COMMANDES - XP, NIVEAU, LEADERBOARD
    # ═══════════════════════════════════════════════════════════════════════════

    @commands.command(name="xp", aliases=["points", "pts", "balance", "niveau", "level"])
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def show_xp(self, ctx, member: discord.Member = None):
        """Affiche le niveau et l'XP d'un utilisateur"""
        member = member or ctx.author
        stats = get_user_stats(member.id)

        level, xp_in, xp_needed = xp_progress(stats.get("total_xp", 0))
        bar = generate_xp_bar(xp_in, xp_needed)

        embed = discord.Embed(
            title=f"📊 Niveau de {member.display_name}",
            color=member.color if member.color != discord.Color.default() else COLORS["info"],
            timestamp=datetime.now()
        )

        embed.add_field(name="⭐ Niveau", value=f"**{level}**", inline=True)
        embed.add_field(name="💎 XP total", value=f"**{stats.get('xp', 0):,}**", inline=True)
        embed.add_field(name="🔥 Streak", value=f"{stats.get('daily_streak', 0)} jours", inline=True)

        embed.add_field(
            name="📈 Progression vers niveau " + str(level + 1),
            value=f"```{bar}```\n{xp_in:,} / {xp_needed:,} XP",
            inline=False
        )

        embed.add_field(
            name="📊 Activité",
            value=(
                f"💬 Messages: {stats.get('messages_count', 0)}\n"
                f"🎤 Vocal: {stats.get('voice_minutes', 0)} min\n"
                f"🔥 Réactions: {stats.get('chapter_reactions', 0)}"
            ),
            inline=True
        )

        embed.add_field(
            name="🎮 Mini-jeux",
            value=f"✅ Trivia réussies: {stats.get('trivia_correct', 0)}",
            inline=True
        )

        # Multiplicateur actif
        multiplier = get_active_multiplier(member.id)
        if multiplier > 1:
            embed.add_field(name="⚡ Boost actif", value=f"x{multiplier:.1f}", inline=True)

        embed.set_thumbnail(url=member.avatar.url if member.avatar else None)
        embed.set_footer(text="Utilise !daily pour ton bonus quotidien !")

        await ctx.send(embed=embed)

    @commands.command(name="leaderboard", aliases=["lb", "top"])
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def leaderboard(self, ctx, page: int = 1):
        """Affiche le classement par niveau"""
        if page < 1:
            page = 1

        # Trier par total_xp (= niveau effectif)
        sorted_users = sorted(
            user_stats.items(),
            key=lambda x: x[1].get("total_xp", x[1].get("total_points_earned", 0)),
            reverse=True
        )

        per_page = 10
        start = (page - 1) * per_page
        end = start + per_page
        page_users = sorted_users[start:end]

        if not page_users:
            await ctx.send("❌ Aucun utilisateur trouvé pour cette page.")
            return

        embed = discord.Embed(
            title="🏆 Classement par Niveau",
            description=f"Page {page}/{(len(sorted_users) + per_page - 1) // per_page}",
            color=COLORS["info"],
            timestamp=datetime.now()
        )

        for i, (user_id_str, stats) in enumerate(page_users, start=start + 1):
            try:
                user = await self.bot.fetch_user(int(user_id_str))
                username = user.display_name if user else f"User {user_id_str}"
            except:
                username = f"User {user_id_str}"

            medal = ""
            if i == 1:
                medal = "🥇"
            elif i == 2:
                medal = "🥈"
            elif i == 3:
                medal = "🥉"

            total_xp = stats.get("total_xp", stats.get("total_points_earned", 0))
            level = calculate_level(total_xp)
            streak_emoji = "🔥" if stats.get("daily_streak", 0) > 0 else ""

            embed.add_field(
                name=f"{medal} #{i} - {username}",
                value=(
                    f"⭐ **Nv. {level}** — {stats.get('xp', stats.get('points', 0)):,} XP {streak_emoji}\n"
                    f"📊 +{stats.get('weekly_xp', stats.get('weekly_points', 0)):,} cette semaine"
                ),
                inline=False
            )

        embed.set_footer(text="Utilise !daily pour gagner plus d'XP !")
        await ctx.send(embed=embed)

    @commands.command(name="profile", aliases=["profil"])
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def user_profile(self, ctx, member: discord.Member = None):
        """Affiche le profil enrichi d'un utilisateur"""
        member = member or ctx.author
        stats = get_user_stats(member.id)

        # Calculer le rang
        sorted_users = sorted(
            user_stats.items(),
            key=lambda x: x[1].get("total_xp", x[1].get("total_points_earned", 0)),
            reverse=True
        )

        rank = 1
        for user_id_str, _ in sorted_users:
            if int(user_id_str) == member.id:
                break
            rank += 1

        total_xp = stats.get("total_xp", stats.get("total_points_earned", 0))
        level, xp_in, xp_needed = xp_progress(total_xp)
        bar = generate_xp_bar(xp_in, xp_needed)

        # Titre de niveau enrichi
        level_titles = {
            0: "🌱 Novice", 5: "📖 Lecteur", 10: "⭐ Habitué",
            20: "🌟 Fidèle", 30: "💫 Expert", 40: "✨ Vétéran",
            50: "🔥 Légende", 60: "💎 Diamant", 70: "👑 Roi",
            80: "🏆 Champion", 90: "🌈 Mythique", 100: "🎆 Transcendant"
        }
        title = "🌱 Novice"
        for threshold in sorted(level_titles.keys(), reverse=True):
            if level >= threshold:
                title = level_titles[threshold]
                break

        embed = discord.Embed(
            title=f"{title} — {member.display_name}",
            color=member.color if member.color != discord.Color.default() else discord.Color.blue(),
            timestamp=datetime.now()
        )

        embed.set_thumbnail(url=member.display_avatar.url)

        # Stats principales
        embed.add_field(name="⭐ Niveau", value=f"**{level}**", inline=True)
        embed.add_field(name="🏆 Rang", value=f"#{rank}/{len(user_stats)}", inline=True)
        embed.add_field(name="🔥 Streak", value=f"{stats.get('daily_streak', 0)} jours", inline=True)

        # Barre XP
        embed.add_field(
            name=f"📈 Progression (Nv. {level} → {level + 1})",
            value=f"```{bar}```\n{xp_in:,} / {xp_needed:,} XP",
            inline=False
        )

        # Activité détaillée
        messages = stats.get('messages_count', 0)
        voice_min = stats.get('voice_minutes', 0)
        reactions = stats.get('chapter_reactions', 0)

        embed.add_field(
            name="📊 Activité",
            value=(
                f"💬 Messages: **{messages:,}**\n"
                f"🎤 Vocal: **{voice_min:,}** min ({voice_min // 60}h {voice_min % 60}m)\n"
                f"🔥 Réactions: **{reactions}**"
            ),
            inline=True
        )

        embed.add_field(
            name="🎮 Mini-jeux",
            value=f"✅ Quiz réussis: **{stats.get('trivia_correct', 0)}**",
            inline=True
        )

        # Tâches réclamées (enrichi)
        try:
            import commands as cmd
            claimed_tasks = 0
            done_tasks = 0
            for key, tasks_data in cmd.etat_taches_global.items():
                for task_name, task_val in tasks_data.items():
                    if isinstance(task_val, dict) and task_val.get("claimed_by") == member.id:
                        claimed_tasks += 1
                    if isinstance(task_val, dict) and task_val.get("claimed_by") == member.id and task_val.get("status") == "✅ Terminé":
                        done_tasks += 1

            if claimed_tasks > 0:
                embed.add_field(
                    name="📋 Contributions",
                    value=f"📌 Tâches réclamées: **{claimed_tasks}**\n✅ Terminées: **{done_tasks}**",
                    inline=True
                )
        except:
            pass

        # Stats hebdomadaires
        embed.add_field(
            name="📅 Cette Semaine",
            value=f"⚡ {stats.get('weekly_xp', stats.get('weekly_points', 0)):,} XP",
            inline=True
        )

        # Ancienneté serveur
        if member.joined_at:
            days_on_server = (datetime.now(member.joined_at.tzinfo) - member.joined_at).days
            embed.add_field(
                name="📆 Ancienneté",
                value=f"Membre depuis **{days_on_server}** jour(s)\n({discord.utils.format_dt(member.joined_at, style='D')})",
                inline=True
            )

        # Multiplicateur actif
        multiplier = get_active_multiplier(member.id)
        if multiplier > 1:
            embed.add_field(name="⚡ Boost Actif", value=f"x{multiplier:.1f}", inline=True)

        # Badges enrichi
        try:
            from achievements import get_user_badges, BADGES_DATA as badges_data
            user_badges = get_user_badges(member.id)
            all_badges = user_badges.get("badges", [])
            if all_badges:
                displayed = user_badges.get("displayed", all_badges[:5])
                badges_display = " ".join([
                    badges_data[bid]["emoji"]
                    for bid in displayed
                    if bid in badges_data
                ])
                if badges_display:
                    embed.add_field(
                        name=f"🏅 Badges ({len(all_badges)})",
                        value=badges_display,
                        inline=False
                    )
        except:
            pass

        # Rôles principaux
        roles = [r.mention for r in member.roles if r.name != "@everyone"][:8]
        if roles:
            embed.add_field(
                name=f"🏷️ Rôles ({len(member.roles) - 1})",
                value=" ".join(roles),
                inline=False
            )

        embed.set_footer(text=f"XP total: {total_xp:,} • ID: {member.id}")

        await ctx.send(embed=embed)

    # ═══════════════════════════════════════════════════════════════════════════
    # COMMANDES ADMIN
    # ═══════════════════════════════════════════════════════════════════════════

    @commands.command(name="give_xp", aliases=["give_points", "addxp"])
    @commands.has_any_role(*ADMIN_ROLES)
    async def give_xp(self, ctx, member: discord.Member, amount: int):
        """Donne de l'XP à un utilisateur (ADMIN)"""
        if amount == 0:
            await ctx.send("❌ Le montant ne peut pas être 0.")
            return

        final_amount, _, level_up, new_level = add_xp(member.id, amount, "admin_gift")

        action = "ajouté" if amount > 0 else "retiré"
        stats = get_user_stats(member.id)
        level = calculate_level(stats.get("total_xp", 0))

        embed = discord.Embed(
            title=f"✅ XP {action}",
            description=f"**{abs(final_amount)}** XP ont été {action}s à {member.mention}",
            color=COLORS["success"] if amount > 0 else COLORS["warning"]
        )
        embed.add_field(name="⭐ Niveau", value=str(level), inline=True)
        embed.add_field(name="💎 XP total", value=f"{stats.get('xp', 0):,}", inline=True)
        await ctx.send(embed=embed)

        if level_up:
            await self.announce_level_up(member.id, new_level, ctx.channel)

    @commands.command(name="reset_xp", aliases=["reset_points"])
    @commands.has_any_role(*ADMIN_ROLES)
    async def reset_xp(self, ctx, member: discord.Member):
        """Réinitialise l'XP d'un utilisateur (ADMIN)"""
        stats = get_user_stats(member.id)
        old_xp = stats.get("xp", 0)
        stats["xp"] = 0
        stats["total_xp"] = 0
        sauvegarder_donnees()

        embed = discord.Embed(
            title="♻️ XP réinitialisé",
            description=f"L'XP de {member.mention} a été remis à zéro.",
            color=COLORS["warning"]
        )
        embed.add_field(name="💎 Ancien XP", value=f"{old_xp:,}")
        await ctx.send(embed=embed)


async def setup(bot):
    """Setup pour discord.py 2.0+"""
    await bot.add_cog(CommunitySystem(bot))
    logging.info("✅ Cog CommunitySystem chargé avec succès")
