# community.py
# ═══════════════════════════════════════════════════════════════════════════════
# SYSTÈME COMMUNAUTAIRE MODERNISÉ - POINTS AUTOMATIQUES PAR ACTIVITÉ
# ═══════════════════════════════════════════════════════════════════════════════

import discord
from discord.ext import commands, tasks
import json
import os
import random
import asyncio
from datetime import datetime, timedelta
from config import (
    COLORS, ADMIN_ROLES, DATA_FILES, POINTS, CHANNELS, 
    POINTS_ALLOWED_CHANNELS, MANGA_EMOJIS
)
from utils import load_json, save_json
import logging

# Fichiers de données
USER_STATS_FILE = DATA_FILES["user_stats"]
os.makedirs("data", exist_ok=True)

# Données en mémoire
user_stats = {}

# Cooldowns pour les gains de points par message
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


def charger_donnees():
    """Charge les données utilisateurs"""
    global user_stats
    user_stats = load_json(USER_STATS_FILE, {})
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
            "points": 0,
            "total_points_earned": 0,
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
            "weekly_points": 0,
            "week_start": datetime.now().isocalendar()[1]
        }
    return user_stats[user_id_str]


def get_active_multiplier(user_id):
    """
    Récupère le multiplicateur de points actif pour un utilisateur.
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


def add_points(user_id, amount, reason=""):
    """
    Ajoute des points à un utilisateur AVEC multiplicateurs.
    Retourne (points_finaux, multiplicateur_utilisé)
    """
    stats = get_user_stats(user_id)
    
    if amount > 0:
        multiplier = get_active_multiplier(user_id)
        final_amount = int(amount * multiplier)
        stats["total_points_earned"] += final_amount
    else:
        multiplier = 1.0
        final_amount = amount
    
    stats["points"] += final_amount
    stats["last_activity"] = datetime.now().isoformat()
    
    # Mise à jour stats hebdomadaires
    current_week = datetime.now().isocalendar()[1]
    if stats.get("week_start") != current_week:
        stats["week_start"] = current_week
        stats["weekly_points"] = 0
    
    if final_amount > 0:
        stats["weekly_points"] += final_amount
    
    sauvegarder_donnees()
    
    # Vérifier les badges
    if final_amount > 0:
        try:
            from achievements import check_badges
            check_badges(user_id, stats)
        except:
            pass
    
    return final_amount, multiplier


class CommunitySystem(commands.Cog):
    """Système communautaire avec gains de points automatiques"""
    
    def __init__(self, bot):
        self.bot = bot
        charger_donnees()
        self.voice_check_loop.start()
        self.seniority_bonus_loop.start()
    
    def cog_unload(self):
        self.voice_check_loop.cancel()
        self.seniority_bonus_loop.cancel()
        sauvegarder_donnees()
    
    # ═══════════════════════════════════════════════════════════════════════════
    # SYSTÈME DE GAIN PAR MESSAGE
    # ═══════════════════════════════════════════════════════════════════════════
    
    @commands.Cog.listener()
    async def on_message(self, message):
        """Gain de points passif par message"""
        if message.author.bot:
            return
        
        if message.channel.id not in POINTS_ALLOWED_CHANNELS:
            return
        
        user_id = message.author.id
        now = datetime.now()
        
        # Vérifier cooldown
        if user_id in message_cooldowns:
            last_time = message_cooldowns[user_id]
            if (now - last_time).total_seconds() < POINTS["message_cooldown"]:
                return
        
        # Gagner des points
        points_earned = random.randint(POINTS["message_min"], POINTS["message_max"])
        final_points, multiplier = add_points(user_id, points_earned, "message")
        
        # Mettre à jour stats
        stats = get_user_stats(user_id)
        stats["messages_count"] += 1
        
        message_cooldowns[user_id] = now
        sauvegarder_donnees()
    
    # ═══════════════════════════════════════════════════════════════════════════
    # SYSTÈME DE RÉACTIONS AUX ANNONCES
    # ═══════════════════════════════════════════════════════════════════════════
    
    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        """Gain de points pour réactions sur annonces de chapitres"""
        if payload.user_id == self.bot.user.id:
            return
        
        # Vérifier si c'est dans le canal des annonces
        if payload.channel_id != CHANNELS.get("chapter_announcements"):
            return
        
        # Réactions comptées
        valid_emojis = ['🔥', '👀', '❤', '❤️']
        if str(payload.emoji) not in valid_emojis:
            return
        
        # Vérifier que l'utilisateur n'a pas déjà réagi à ce message
        try:
            channel = self.bot.get_channel(payload.channel_id)
            message = await channel.fetch_message(payload.message_id)
            
            # Compter les réactions de cet utilisateur
            user_reaction_count = 0
            for reaction in message.reactions:
                async for user in reaction.users():
                    if user.id == payload.user_id:
                        user_reaction_count += 1
            
            # Si c'est la première réaction de l'utilisateur sur ce message
            if user_reaction_count == 1:
                points_earned, multiplier = add_points(
                    payload.user_id, 
                    POINTS["chapter_reaction"],
                    "chapter_reaction"
                )
                
                stats = get_user_stats(payload.user_id)
                stats["chapter_reactions"] += 1
                sauvegarder_donnees()
                
                logging.info(f"✅ {payload.user_id} a gagné {points_earned} pts (réaction chapitre)")
        
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
        
        # Utilisateur rejoint un canal vocal
        if before.channel is None and after.channel is not None:
            voice_tracking[user_id] = datetime.now()
            logging.info(f"🎤 {member.name} a rejoint un vocal")
        
        # Utilisateur quitte un canal vocal
        elif before.channel is not None and after.channel is None:
            if user_id in voice_tracking:
                start_time = voice_tracking[user_id]
                duration = (datetime.now() - start_time).total_seconds() / 60  # minutes
                
                # Calculer les points (5 pts par 15 min)
                intervals = int(duration / 15)
                if intervals > 0:
                    points_earned = intervals * POINTS["voice_per_15min"]
                    final_points, multiplier = add_points(user_id, points_earned, "vocal")
                    
                    stats = get_user_stats(user_id)
                    stats["voice_minutes"] += int(duration)
                    sauvegarder_donnees()
                    
                    logging.info(f"🎤 {member.name} a gagné {final_points} pts ({int(duration)} min en vocal)")
                
                del voice_tracking[user_id]
    
    @tasks.loop(minutes=15)
    async def voice_check_loop(self):
        """Donne des points toutes les 15 min aux users en vocal"""
        for user_id, start_time in list(voice_tracking.items()):
            duration = (datetime.now() - start_time).total_seconds() / 60
            if duration >= 15:
                points_earned, multiplier = add_points(user_id, POINTS["voice_per_15min"], "vocal_interval")
                
                stats = get_user_stats(user_id)
                stats["voice_minutes"] += 15
                
                # Reset le compteur
                voice_tracking[user_id] = datetime.now()
                
                logging.info(f"🎤 User {user_id} a gagné {points_earned} pts (15 min vocal)")
        
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
        
        # Vérifier si c'est lundi (début de semaine)
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
            
            # Vérifier si déjà reçu cette semaine
            if last_bonus:
                last_date = datetime.fromisoformat(last_bonus).date()
                if (today - last_date).days < 7:
                    continue
            
            # Calculer l'ancienneté en jours
            joined_at = member.joined_at
            if joined_at:
                days_on_server = (datetime.now(joined_at.tzinfo) - joined_at).days
                
                # Calculer le bonus (50-200 pts selon ancienneté)
                if days_on_server < 30:
                    bonus = POINTS["seniority_base"]
                elif days_on_server < 90:
                    bonus = 100
                elif days_on_server < 180:
                    bonus = 150
                else:
                    bonus = POINTS["seniority_max"]
                
                final_bonus, multiplier = add_points(member.id, bonus, "seniority")
                stats["last_seniority_bonus"] = datetime.now().isoformat()
                
                logging.info(f"🏅 {member.name} a reçu {final_bonus} pts (ancienneté: {days_on_server} jours)")
        
        sauvegarder_donnees()
    
    @seniority_bonus_loop.before_loop
    async def before_seniority_check(self):
        await self.bot.wait_until_ready()
    
    # ═══════════════════════════════════════════════════════════════════════════
    # COMMANDES - BONUS QUOTIDIEN
    # ═══════════════════════════════════════════════════════════════════════════
    
    @commands.command(name="daily")
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
        base_bonus = random.randint(POINTS["daily_min"], POINTS["daily_max"])
        streak_bonus = min(stats["daily_streak"] * POINTS["streak_bonus"], POINTS["streak_max_bonus"])
        total_bonus = base_bonus + streak_bonus
        
        final_bonus, multiplier = add_points(ctx.author.id, total_bonus, "daily")
        
        embed = discord.Embed(
            title="🎁 Bonus quotidien réclamé !",
            description=f"Tu as reçu **{final_bonus} points** !",
            color=COLORS["success"],
            timestamp=datetime.now()
        )
        
        embed.add_field(name="💰 Bonus de base", value=f"{base_bonus} pts", inline=True)
        embed.add_field(name="🔥 Bonus streak", value=f"+{streak_bonus} pts", inline=True)
        embed.add_field(name="⚡ Total", value=f"**{final_bonus} pts**", inline=True)
        
        embed.add_field(
            name="📊 Progression",
            value=f"🔥 Streak: **{stats['daily_streak']} jour(s)**\n💰 Points totaux: **{stats['points']:,} pts**",
            inline=False
        )
        
        if multiplier > 1:
            embed.add_field(name="⚡ Multiplicateur actif", value=f"x{multiplier:.1f}", inline=True)
        
        embed.set_footer(text="Reviens demain pour continuer ton streak !")
        embed.set_thumbnail(url=ctx.author.avatar.url if ctx.author.avatar else None)
        
        sauvegarder_donnees()
        await ctx.send(embed=embed)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # COMMANDES - MINI-JEUX
    # ═══════════════════════════════════════════════════════════════════════════
    
    @commands.command(name="trivia")
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
        
        # Points selon difficulté
        points_reward = {
            "easy": POINTS["trivia_easy"],
            "medium": POINTS["trivia_medium"],
            "hard": POINTS["trivia_hard"]
        }[difficulty]
        
        embed = discord.Embed(
            title=f"🎮 Quiz Manga - {difficulty.capitalize()}",
            description=question_data["question"],
            color=COLORS["info"]
        )
        embed.add_field(name="🏆 Récompense", value=f"{points_reward} points", inline=True)
        embed.add_field(name="⏱️ Temps", value="30 secondes", inline=True)
        embed.set_footer(text="Réponds directement dans le chat !")
        
        await ctx.send(embed=embed)
        
        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel
        
        try:
            msg = await self.bot.wait_for('message', check=check, timeout=30)
            
            if msg.content.lower().strip() == question_data["answer"].lower():
                final_points, multiplier = add_points(ctx.author.id, points_reward, "trivia")
                
                stats = get_user_stats(ctx.author.id)
                stats["trivia_correct"] += 1
                sauvegarder_donnees()
                
                embed = discord.Embed(
                    title="✅ Bonne réponse !",
                    description=f"Bravo ! Tu gagnes **{final_points} points** !",
                    color=COLORS["success"]
                )
                embed.add_field(name="💰 Points totaux", value=f"{stats['points']:,} pts")
                await ctx.send(embed=embed)
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
    async def guess_game(self, ctx):
        """Devine le manga à partir d'un emoji"""
        manga_list = list(MANGA_EMOJIS.items())
        correct_manga, emoji = random.choice(manga_list)
        
        embed = discord.Embed(
            title="🎮 Devine le manga !",
            description=f"Quel manga représente cet emoji ?\n\n# {emoji}",
            color=COLORS["info"]
        )
        embed.add_field(name="🏆 Récompense", value=f"{POINTS['guess_correct']} points")
        embed.add_field(name="⏱️ Temps", value="20 secondes")
        embed.set_footer(text="Écris le nom du manga dans le chat !")
        
        await ctx.send(embed=embed)
        
        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel
        
        try:
            msg = await self.bot.wait_for('message', check=check, timeout=20)
            
            if msg.content.lower().replace(" ", "") in correct_manga.lower().replace(" ", ""):
                final_points, multiplier = add_points(ctx.author.id, POINTS["guess_correct"], "guess")
                
                stats = get_user_stats(ctx.author.id)
                sauvegarder_donnees()
                
                embed = discord.Embed(
                    title="✅ Correct !",
                    description=f"C'était bien **{correct_manga}** !\nTu gagnes **{final_points} points** !",
                    color=COLORS["success"]
                )
                embed.add_field(name="💰 Points totaux", value=f"{stats['points']:,} pts")
                await ctx.send(embed=embed)
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
    # COMMANDES - STATISTIQUES ET LEADERBOARD
    # ═══════════════════════════════════════════════════════════════════════════
    
    @commands.command(name="points", aliases=["pts", "balance"])
    async def show_points(self, ctx, member: discord.Member = None):
        """Affiche les points d'un utilisateur"""
        member = member or ctx.author
        stats = get_user_stats(member.id)
        
        embed = discord.Embed(
            title=f"💰 Points de {member.display_name}",
            color=member.color if member.color != discord.Color.default() else COLORS["info"],
            timestamp=datetime.now()
        )
        
        embed.add_field(name="💎 Points actuels", value=f"**{stats['points']:,}**", inline=True)
        embed.add_field(name="📈 Total gagné", value=f"{stats['total_points_earned']:,}", inline=True)
        embed.add_field(name="🔥 Streak", value=f"{stats.get('daily_streak', 0)} jours", inline=True)
        
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
    async def leaderboard(self, ctx, page: int = 1):
        """Affiche le classement des points"""
        if page < 1:
            page = 1
        
        # Trier par points
        sorted_users = sorted(
            user_stats.items(),
            key=lambda x: x[1].get("points", 0),
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
            title="🏆 Classement des Points",
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
            
            streak_emoji = "🔥" if stats.get("daily_streak", 0) > 0 else ""
            
            embed.add_field(
                name=f"{medal} #{i} - {username}",
                value=(
                    f"💰 **{stats['points']:,}** pts {streak_emoji}\n"
                    f"📊 +{stats.get('weekly_points', 0):,} cette semaine"
                ),
                inline=False
            )
        
        embed.set_footer(text="Utilise !daily pour gagner plus de points !")
        await ctx.send(embed=embed)
    
    @commands.command(name="profile", aliases=["profil"])
    async def user_profile(self, ctx, member: discord.Member = None):
        """Affiche le profil complet d'un utilisateur"""
        member = member or ctx.author
        stats = get_user_stats(member.id)
        
        # Calculer le rang
        sorted_users = sorted(
            user_stats.items(),
            key=lambda x: x[1].get("points", 0),
            reverse=True
        )
        
        rank = 1
        for user_id_str, _ in sorted_users:
            if int(user_id_str) == member.id:
                break
            rank += 1
        
        embed = discord.Embed(
            title=f"📊 Profil de {member.display_name}",
            color=member.color if member.color != discord.Color.default() else discord.Color.blue(),
            timestamp=datetime.now()
        )
        
        embed.set_thumbnail(url=member.avatar.url if member.avatar else None)
        
        # Stats principales
        embed.add_field(name="💰 Points", value=f"**{stats.get('points', 0):,}**", inline=True)
        embed.add_field(name="🏆 Rang", value=f"#{rank}", inline=True)
        embed.add_field(name="🔥 Streak", value=f"{stats.get('daily_streak', 0)} jours", inline=True)
        
        embed.add_field(
            name="📊 Activité",
            value=(
                f"💬 Messages: {stats.get('messages_count', 0)}\n"
                f"🎤 Vocal: {stats.get('voice_minutes', 0)} min\n"
                f"🔥 Réactions chapitres: {stats.get('chapter_reactions', 0)}"
            ),
            inline=True
        )
        
        embed.add_field(
            name="🎮 Mini-jeux",
            value=f"✅ Quiz réussis: {stats.get('trivia_correct', 0)}",
            inline=True
        )
        
        # Stats hebdomadaires
        embed.add_field(
            name="📅 Cette Semaine",
            value=f"⚡ {stats.get('weekly_points', 0):,} pts",
            inline=False
        )
        
        # Multiplicateur actif
        multiplier = get_active_multiplier(member.id)
        if multiplier > 1:
            embed.add_field(name="⚡ Boost Actif", value=f"x{multiplier:.1f}", inline=True)
        
        # Badges
        try:
            from achievements import get_user_badges, badges_data
            user_badges = get_user_badges(member.id)
            if user_badges.get("displayed"):
                badges_display = " ".join([
                    badges_data[bid]["emoji"] 
                    for bid in user_badges["displayed"] 
                    if bid in badges_data
                ])
                embed.add_field(name="🏅 Badges", value=badges_display, inline=False)
        except:
            pass
        
        embed.set_footer(text=f"Total gagné: {stats.get('total_points_earned', 0):,} pts")
        
        await ctx.send(embed=embed)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # COMMANDES ADMIN
    # ═══════════════════════════════════════════════════════════════════════════
    
    @commands.command(name="give_points")
    @commands.has_any_role(*ADMIN_ROLES)
    async def give_points(self, ctx, member: discord.Member, amount: int):
        """Donne des points à un utilisateur (ADMIN)"""
        if amount == 0:
            await ctx.send("❌ Le montant ne peut pas être 0.")
            return
        
        final_amount, _ = add_points(member.id, amount, "admin_gift")
        
        action = "ajouté" if amount > 0 else "retiré"
        stats = get_user_stats(member.id)
        
        embed = discord.Embed(
            title=f"✅ Points {action}",
            description=f"**{abs(final_amount)}** points ont été {action}s à {member.mention}",
            color=COLORS["success"] if amount > 0 else COLORS["warning"]
        )
        embed.add_field(name="💰 Nouveau total", value=f"{stats['points']:,} pts")
        await ctx.send(embed=embed)
    
    @commands.command(name="reset_points")
    @commands.has_any_role(*ADMIN_ROLES)
    async def reset_points(self, ctx, member: discord.Member):
        """Réinitialise les points d'un utilisateur (ADMIN)"""
        stats = get_user_stats(member.id)
        old_points = stats["points"]
        stats["points"] = 0
        sauvegarder_donnees()
        
        embed = discord.Embed(
            title="♻️ Points réinitialisés",
            description=f"Les points de {member.mention} ont été remis à zéro.",
            color=COLORS["warning"]
        )
        embed.add_field(name="💰 Anciens points", value=f"{old_points:,}")
        await ctx.send(embed=embed)


async def setup(bot):
    """Setup pour discord.py 2.0+"""
    await bot.add_cog(CommunitySystem(bot))
    logging.info("✅ Cog CommunitySystem chargé avec succès")