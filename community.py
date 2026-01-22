# community.py
# Système communautaire AMÉLIORÉ : Reviews, Théories, Points avec Boosts, Leaderboards
import discord
from discord.ext import commands, tasks
import json
import os
import asyncio
from datetime import datetime, timedelta
from config import COLORS

# Fichiers de données
REVIEWS_FILE = "data/reviews.json"
THEORIES_FILE = "data/theories.json"
CHAPTERS_FILE = "data/chapters_community.json"
USER_STATS_FILE = "data/user_stats.json"
os.makedirs("data", exist_ok=True)

# Données en mémoire
reviews_data = {}
theories_data = {}
chapters_data = {}
user_stats = {}

# Emojis pour les notes
RATING_EMOJIS = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣"]
REACTION_EMOJIS = ["🔥", "😭", "😱", "🤯", "❤️", "😂", "💀"]

# Points gagnés par action (BASE - avant multiplicateurs)
POINTS = {
    "review": 10,
    "theory": 15,
    "theory_vote": 2,
    "first_review": 25,
    "first_theory": 30,
    "daily_bonus": 5,
    "streak_bonus": 10,  # Par jour de streak
}

def charger_donnees():
    """Charge toutes les données communautaires"""
    global reviews_data, theories_data, chapters_data, user_stats
    
    for file_path, data_dict, name in [
        (REVIEWS_FILE, reviews_data, "reviews"),
        (THEORIES_FILE, theories_data, "théories"),
        (CHAPTERS_FILE, chapters_data, "chapitres"),
        (USER_STATS_FILE, user_stats, "stats utilisateurs")
    ]:
        if os.path.exists(file_path):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    contenu = f.read().strip()
                    if contenu:
                        loaded = json.loads(contenu)
                        if name == "reviews":
                            reviews_data.update(loaded)
                        elif name == "théories":
                            theories_data.update(loaded)
                        elif name == "chapitres":
                            chapters_data.update(loaded)
                        elif name == "stats utilisateurs":
                            user_stats.update(loaded)
                print(f"✅ {name} chargé(s)")
            except Exception as e:
                print(f"❌ Erreur chargement {name}: {e}")

def sauvegarder_donnees():
    """Sauvegarde toutes les données"""
    try:
        with open(REVIEWS_FILE, "w", encoding="utf-8") as f:
            json.dump(reviews_data, f, ensure_ascii=False, indent=4)
        with open(THEORIES_FILE, "w", encoding="utf-8") as f:
            json.dump(theories_data, f, ensure_ascii=False, indent=4)
        with open(CHAPTERS_FILE, "w", encoding="utf-8") as f:
            json.dump(chapters_data, f, ensure_ascii=False, indent=4)
        with open(USER_STATS_FILE, "w", encoding="utf-8") as f:
            json.dump(user_stats, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"❌ Erreur sauvegarde: {e}")

def get_user_stats(user_id):
    """Récupère ou crée les stats d'un utilisateur"""
    user_id_str = str(user_id)
    if user_id_str not in user_stats:
        user_stats[user_id_str] = {
            "points": 0,
            "total_points_earned": 0,
            "reviews_count": 0,
            "theories_count": 0,
            "theories_votes_given": 0,
            "theories_votes_received": 0,
            "badges": [],
            "joined_at": datetime.now().isoformat(),
            "last_activity": datetime.now().isoformat(),
            "daily_streak": 0,
            "last_daily": None,
            "weekly_points": 0,
            "weekly_reviews": 0,
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
            # Vérifier si le boost a une date d'expiration
            if "expires" in boost_data:
                expires = datetime.fromisoformat(boost_data["expires"])
                if datetime.now() >= expires:
                    expired_boosts.append(boost_id)
                    continue
            
            # Appliquer le multiplicateur
            if boost_id == "double_points":
                multiplier *= boost_data.get("multiplier", 2)
            elif boost_id == "triple_points":
                multiplier *= boost_data.get("multiplier", 3)
        
        # Nettoyer les boosts expirés
        if expired_boosts:
            for boost_id in expired_boosts:
                del active_boosts[boost_id]
            from shop import sauvegarder_shop
            sauvegarder_shop()
        
        return multiplier
    except Exception as e:
        print(f"Erreur get_active_multiplier: {e}")
        return 1.0

def add_points(user_id, amount, reason=""):
    """
    Ajoute des points à un utilisateur AVEC multiplicateurs.
    Retourne (points_finaux, multiplicateur_utilisé)
    """
    stats = get_user_stats(user_id)
    
    # Appliquer le multiplicateur seulement pour les gains positifs
    if amount > 0:
        multiplier = get_active_multiplier(user_id)
        final_amount = int(amount * multiplier)
        stats["total_points_earned"] += final_amount
    else:
        multiplier = 1.0
        final_amount = amount
    
    stats["points"] += final_amount
    stats["last_activity"] = datetime.now().isoformat()
    
    # Mise à jour des stats hebdomadaires
    current_week = datetime.now().isocalendar()[1]
    if stats.get("week_start") != current_week:
        stats["week_start"] = current_week
        stats["weekly_points"] = 0
        stats["weekly_reviews"] = 0
    
    if final_amount > 0:
        stats["weekly_points"] += final_amount
    
    sauvegarder_donnees()
    
    # Vérifier les badges après gain de points
    if final_amount > 0:
        try:
            from achievements import check_badges
            check_badges(user_id, stats)
        except:
            pass
    
    return final_amount, multiplier

def update_daily_streak(user_id):
    """Met à jour le streak quotidien et donne le bonus"""
    stats = get_user_stats(user_id)
    today = datetime.now().date().isoformat()
    
    bonus_points = 0
    
    if stats.get("last_daily") != today:
        last_daily = stats.get("last_daily")
        
        if last_daily:
            last_date = datetime.fromisoformat(last_daily).date()
            today_date = datetime.now().date()
            diff = (today_date - last_date).days
            
            if diff == 1:
                # Streak continue
                stats["daily_streak"] += 1
            elif diff > 1:
                # Streak cassé
                stats["daily_streak"] = 1
        else:
            stats["daily_streak"] = 1
        
        stats["last_daily"] = today
        
        # Calculer le bonus
        bonus_points = POINTS["daily_bonus"] + (stats["daily_streak"] * POINTS["streak_bonus"])
        bonus_points = min(bonus_points, 100)  # Cap à 100 pts
        
        sauvegarder_donnees()
    
    return bonus_points, stats["daily_streak"]

def get_manga_emoji(manga_name):
    """Récupère l'emoji d'un manga"""
    emojis = {
        "ao no exorcist": "👹",
        "satsudou": "🩸",
        "tougen anki": "😈",
        "catenaccio": "⚽",
        "tokyo underworld": "🗼"
    }
    return emojis.get(manga_name.lower(), "📚")


class CommunitySystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        charger_donnees()
    
    async def cog_load(self):
        """Démarrer les tâches de fond"""
        self.weekly_rewards.start()
        print("✅ Tâches communautaires démarrées")
    
    async def cog_unload(self):
        """Arrêter les tâches"""
        self.weekly_rewards.cancel()
    
    @tasks.loop(hours=168)  # Chaque semaine
    async def weekly_rewards(self):
        """Distribue les récompenses hebdomadaires"""
        # Trouver le meilleur reviewer de la semaine
        current_week = datetime.now().isocalendar()[1]
        
        best_reviewer = None
        best_reviews = 0
        best_points = 0
        best_points_user = None
        
        for user_id, stats in user_stats.items():
            if stats.get("week_start") == current_week:
                if stats.get("weekly_reviews", 0) > best_reviews:
                    best_reviews = stats["weekly_reviews"]
                    best_reviewer = user_id
                if stats.get("weekly_points", 0) > best_points:
                    best_points = stats["weekly_points"]
                    best_points_user = user_id
        
        # Reset des stats hebdomadaires
        for user_id, stats in user_stats.items():
            stats["weekly_points"] = 0
            stats["weekly_reviews"] = 0
            stats["week_start"] = datetime.now().isocalendar()[1]
        
        sauvegarder_donnees()
    
    @weekly_rewards.before_loop
    async def before_weekly_rewards(self):
        await self.bot.wait_until_ready()
    
    # ==================== COMMANDES ADMIN ====================
    
    @commands.command(name="newchapter")
    @commands.has_any_role(1326417422663680090, 1330147432847114321)
    async def newchapter(self, ctx, message_id: int, manga: str, chapitre: str):
        """Lie une annonce de chapitre au système communautaire."""
        try:
            target_message = await ctx.channel.fetch_message(message_id)
        except discord.NotFound:
            await ctx.send("❌ Message introuvable dans ce salon.")
            return
        except discord.HTTPException as e:
            await ctx.send(f"❌ Erreur lors de la récupération du message: {e}")
            return
        
        chapter_key = f"{manga.lower()}_{chapitre}"
        
        chapters_data[chapter_key] = {
            "manga": manga,
            "chapter": chapitre,
            "message_id": message_id,
            "channel_id": ctx.channel.id,
            "guild_id": ctx.guild.id,
            "created_at": datetime.now().isoformat(),
            "reviews": {},
            "reactions": {},
            "theories_linked": [],
            "review_count": 0
        }
        
        sauvegarder_donnees()
        
        manga_emoji = get_manga_emoji(manga)
        
        embed = discord.Embed(
            title=f"{manga_emoji} {manga} - Chapitre {chapitre}",
            description=(
                "**📝 Partagez votre avis sur ce chapitre !**\n\n"
                f"⭐ **Noter** : `!review {manga} {chapitre} <1-5> [commentaire]`\n"
                f"💭 **Théorie** : `!theory {manga} <votre théorie>`\n"
                f"📊 **Voir les avis** : `!chapter_reviews {manga} {chapitre}`\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━"
            ),
            color=discord.Color.gold(),
            timestamp=datetime.now()
        )
        
        embed.add_field(
            name="📊 Statistiques",
            value="⭐ Note moyenne: --\n📝 Reviews: 0\n💭 Théories: 0",
            inline=True
        )
        
        embed.add_field(
            name="🏆 Points à gagner",
            value=f"+{POINTS['review']} pts (review)\n+{POINTS['first_review']} pts (1er review)",
            inline=True
        )
        
        embed.set_footer(text=f"ID: {chapter_key}")
        
        interaction_msg = await ctx.send(embed=embed)
        
        for emoji in REACTION_EMOJIS:
            await interaction_msg.add_reaction(emoji)
        
        chapters_data[chapter_key]["interaction_message_id"] = interaction_msg.id
        sauvegarder_donnees()
        
        confirm_embed = discord.Embed(
            title="✅ Chapitre Lié !",
            description=f"Le chapitre **{chapitre}** de **{manga}** est maintenant lié au système communautaire.",
            color=discord.Color.green()
        )
        confirm_embed.add_field(name="🆔 Message d'annonce", value=f"`{message_id}`", inline=True)
        confirm_embed.add_field(name="🆔 Clé", value=f"`{chapter_key}`", inline=True)
        
        await ctx.send(embed=confirm_embed, delete_after=10)
    
    # ==================== REVIEWS ====================
    
    @commands.command(name="review")
    async def review(self, ctx, manga: str, chapitre: str, note: int, *, commentaire: str = None):
        """Laisse une review sur un chapitre avec système de points amélioré."""
        if note < 1 or note > 5:
            await ctx.send("❌ La note doit être entre 1 et 5.")
            return
        
        chapter_key = f"{manga.lower()}_{chapitre}"
        
        if chapter_key not in chapters_data:
            await ctx.send(f"❌ Chapitre introuvable. Assurez-vous que le chapitre a été lié avec `!newchapter`.")
            return
        
        user_id = str(ctx.author.id)
        is_first_review = len(chapters_data[chapter_key]["reviews"]) == 0
        already_reviewed = user_id in chapters_data[chapter_key]["reviews"]
        
        # Créer/mettre à jour la review
        chapters_data[chapter_key]["reviews"][user_id] = {
            "note": note,
            "commentaire": commentaire,
            "created_at": datetime.now().isoformat(),
            "username": ctx.author.name
        }
        
        if chapter_key not in reviews_data:
            reviews_data[chapter_key] = {}
        reviews_data[chapter_key][user_id] = chapters_data[chapter_key]["reviews"][user_id]
        
        # Mettre à jour les stats utilisateur
        stats = get_user_stats(ctx.author.id)
        
        points_base = 0
        multiplier = 1.0
        
        if not already_reviewed:
            stats["reviews_count"] += 1
            stats["weekly_reviews"] += 1
            chapters_data[chapter_key]["review_count"] = len(chapters_data[chapter_key]["reviews"])
            
            # Points de base
            points_base = POINTS["first_review"] if is_first_review else POINTS["review"]
            
            # Bonus de streak
            daily_bonus, streak = update_daily_streak(ctx.author.id)
            
            # Ajouter les points avec multiplicateur
            final_points, multiplier = add_points(ctx.author.id, points_base)
            
            # Ajouter bonus daily séparément
            if daily_bonus > 0:
                add_points(ctx.author.id, daily_bonus, "daily_streak")
        
        sauvegarder_donnees()
        
        # Vérifier les badges
        try:
            from achievements import check_badges, get_user_badges
            user_badges = get_user_badges(ctx.author.id)
            
            # Mettre à jour les stats manga spécifiques
            manga_lower = manga.lower()
            if "manga_reviews" not in user_badges["stats"]:
                user_badges["stats"]["manga_reviews"] = {}
            if manga_lower not in user_badges["stats"]["manga_reviews"]:
                user_badges["stats"]["manga_reviews"][manga_lower] = 0
            user_badges["stats"]["manga_reviews"][manga_lower] += 1
            
            unlocked = check_badges(ctx.author.id, stats)
        except Exception as e:
            print(f"Erreur badges: {e}")
            unlocked = []
        
        # Calculer la moyenne
        reviews = chapters_data[chapter_key]["reviews"]
        moyenne = sum(r["note"] for r in reviews.values()) / len(reviews)
        
        # Vérifier si highlight review est actif
        highlight = False
        try:
            from shop import get_user_inventory
            inv = get_user_inventory(ctx.author.id)
            if "highlight_review" in inv.get("active_boosts", {}):
                highlight = True
                del inv["active_boosts"]["highlight_review"]
                from shop import sauvegarder_shop
                sauvegarder_shop()
        except:
            pass
        
        # Créer l'embed de confirmation
        stars = "⭐" * note + "☆" * (5 - note)
        manga_emoji = get_manga_emoji(manga)
        
        embed_color = discord.Color.gold() if highlight else discord.Color.green()
        
        embed = discord.Embed(
            title=f"{'🌟 REVIEW EN VEDETTE 🌟' if highlight else ''}{manga_emoji} Review Enregistrée !",
            description=f"**{manga}** - Chapitre {chapitre}",
            color=embed_color,
            timestamp=datetime.now()
        )
        
        embed.add_field(name="📊 Votre Note", value=stars, inline=True)
        embed.add_field(name="📈 Moyenne", value=f"⭐ {moyenne:.1f}/5 ({len(reviews)} avis)", inline=True)
        
        if commentaire:
            embed.add_field(name="💬 Commentaire", value=commentaire[:500], inline=False)
        
        if not already_reviewed and points_base > 0:
            bonus_text = ""
            if is_first_review:
                bonus_text = " 🎉 Premier review !"
            if multiplier > 1:
                bonus_text += f" ⚡ x{multiplier:.1f}"
            
            embed.add_field(
                name="🏆 Points Gagnés",
                value=f"+{final_points} pts{bonus_text}",
                inline=False
            )
            
            # Afficher le streak
            streak = stats.get("daily_streak", 0)
            if streak > 1:
                embed.add_field(
                    name="🔥 Streak",
                    value=f"{streak} jours consécutifs !",
                    inline=True
                )
        
        # Badges débloqués
        if unlocked:
            badges_text = " ".join([f"{b['emoji']}" for b in unlocked])
            embed.add_field(name="🏅 Nouveau(x) Badge(s) !", value=badges_text, inline=False)
        
        embed.set_footer(text=f"Total: {stats['points']} points | {stats['reviews_count']} reviews")
        embed.set_thumbnail(url=ctx.author.avatar.url if ctx.author.avatar else None)
        
        await ctx.send(embed=embed)
        await self.update_chapter_embed(chapter_key)
    
    @commands.command(name="chapter_reviews")
    async def chapter_reviews(self, ctx, manga: str, chapitre: str):
        """Affiche toutes les reviews d'un chapitre"""
        chapter_key = f"{manga.lower()}_{chapitre}"
        
        if chapter_key not in chapters_data:
            await ctx.send(f"❌ Chapitre introuvable.")
            return
        
        chapter = chapters_data[chapter_key]
        reviews = chapter.get("reviews", {})
        
        manga_emoji = get_manga_emoji(manga)
        
        if not reviews:
            embed = discord.Embed(
                title=f"{manga_emoji} {manga} - Chapitre {chapitre}",
                description="Aucune review pour ce chapitre.\n\nSoyez le premier à donner votre avis !",
                color=discord.Color.blue()
            )
            embed.add_field(
                name="💡 Comment reviewer ?",
                value=f"`!review {manga} {chapitre} <note 1-5> [commentaire]`",
                inline=False
            )
            await ctx.send(embed=embed)
            return
        
        moyenne = sum(r["note"] for r in reviews.values()) / len(reviews)
        distribution = {i: 0 for i in range(1, 6)}
        for r in reviews.values():
            distribution[r["note"]] += 1
        
        embed = discord.Embed(
            title=f"{manga_emoji} {manga} - Chapitre {chapitre}",
            description=f"**⭐ Note Moyenne: {moyenne:.1f}/5** ({len(reviews)} avis)",
            color=discord.Color.gold(),
            timestamp=datetime.now()
        )
        
        dist_text = ""
        for i in range(5, 0, -1):
            bar_length = int((distribution[i] / len(reviews)) * 10) if reviews else 0
            bar = "█" * bar_length + "░" * (10 - bar_length)
            dist_text += f"{'⭐' * i}{'☆' * (5-i)} {bar} {distribution[i]}\n"
        
        embed.add_field(name="📊 Distribution", value=f"```{dist_text}```", inline=False)
        
        recent_reviews = sorted(reviews.items(), key=lambda x: x[1]["created_at"], reverse=True)[:5]
        
        for user_id, review in recent_reviews:
            member = ctx.guild.get_member(int(user_id))
            name = member.display_name if member else review.get("username", "Inconnu")
            stars = "⭐" * review["note"]
            
            value = f"{stars}\n"
            if review.get("commentaire"):
                value += f"*\"{review['commentaire'][:100]}{'...' if len(review.get('commentaire', '')) > 100 else ''}\"*"
            else:
                value += "*Pas de commentaire*"
            
            embed.add_field(name=f"💬 {name}", value=value, inline=False)
        
        if len(reviews) > 5:
            embed.set_footer(text=f"Affichage des 5 dernières reviews sur {len(reviews)}")
        
        await ctx.send(embed=embed)
    
    # ==================== THÉORIES ====================
    
    @commands.command(name="theory")
    async def theory(self, ctx, manga: str, *, contenu: str):
        """Poste une théorie sur un manga avec système de points amélioré."""
        if len(contenu) < 20:
            await ctx.send("❌ Votre théorie doit faire au moins 20 caractères.")
            return
        
        if len(contenu) > 1500:
            await ctx.send("❌ Votre théorie est trop longue (max 1500 caractères).")
            return
        
        manga_lower = manga.lower()
        user_id = str(ctx.author.id)
        
        theory_id = f"theory_{int(datetime.now().timestamp())}_{user_id[:8]}"
        
        manga_theories = [t for t in theories_data.values() if t.get("manga", "").lower() == manga_lower]
        is_first = len(manga_theories) == 0
        
        # Vérifier si theory boost est actif
        boosted = False
        try:
            from shop import get_user_inventory
            inv = get_user_inventory(ctx.author.id)
            if "theory_boost" in inv.get("active_boosts", {}):
                boosted = True
                del inv["active_boosts"]["theory_boost"]
                from shop import sauvegarder_shop
                sauvegarder_shop()
        except:
            pass
        
        theories_data[theory_id] = {
            "id": theory_id,
            "manga": manga,
            "author_id": user_id,
            "author_name": ctx.author.name,
            "contenu": contenu,
            "created_at": datetime.now().isoformat(),
            "votes_up": [],
            "votes_down": [],
            "status": "active",
            "channel_id": ctx.channel.id,
            "message_id": None,
            "boosted": boosted,
            "boost_expires": (datetime.now() + timedelta(hours=48)).isoformat() if boosted else None
        }
        
        stats = get_user_stats(ctx.author.id)
        stats["theories_count"] += 1
        
        points_base = POINTS["first_theory"] if is_first else POINTS["theory"]
        final_points, multiplier = add_points(ctx.author.id, points_base)
        
        # Bonus streak
        daily_bonus, streak = update_daily_streak(ctx.author.id)
        if daily_bonus > 0:
            add_points(ctx.author.id, daily_bonus, "daily_streak")
        
        sauvegarder_donnees()
        
        # Vérifier les badges
        try:
            from achievements import check_badges
            unlocked = check_badges(ctx.author.id, stats)
        except:
            unlocked = []
        
        manga_emoji = get_manga_emoji(manga)
        
        embed = discord.Embed(
            title=f"{'🚀 THÉORIE BOOSTÉE 🚀 ' if boosted else ''}💭 Nouvelle Théorie - {manga_emoji} {manga}",
            description=contenu,
            color=discord.Color.purple() if not boosted else discord.Color.gold(),
            timestamp=datetime.now()
        )
        
        embed.add_field(name="👤 Auteur", value=ctx.author.mention, inline=True)
        embed.add_field(name="📊 Votes", value="👍 0 | 👎 0", inline=True)
        embed.add_field(name="🏷️ Statut", value="🔮 En attente", inline=True)
        
        bonus_text = ""
        if is_first:
            bonus_text = " 🎉 Première théorie !"
        if multiplier > 1:
            bonus_text += f" ⚡ x{multiplier:.1f}"
        if boosted:
            bonus_text += " 🚀 Boostée 48h"
        
        embed.add_field(name="🏆 Points", value=f"+{final_points} pts{bonus_text}", inline=False)
        
        if unlocked:
            badges_text = " ".join([f"{b['emoji']}" for b in unlocked])
            embed.add_field(name="🏅 Nouveau(x) Badge(s) !", value=badges_text, inline=False)
        
        embed.set_footer(text=f"ID: {theory_id} | Votez avec 👍 ou 👎")
        embed.set_thumbnail(url=ctx.author.avatar.url if ctx.author.avatar else None)
        
        theory_msg = await ctx.send(embed=embed)
        await theory_msg.add_reaction("👍")
        await theory_msg.add_reaction("👎")
        
        theories_data[theory_id]["message_id"] = theory_msg.id
        sauvegarder_donnees()
    
    @commands.command(name="theories")
    async def list_theories(self, ctx, manga: str = None):
        """Liste les théories (optionnel: filtrer par manga)"""
        if manga:
            filtered = {k: v for k, v in theories_data.items() 
                       if v.get("manga", "").lower() == manga.lower() and v.get("status") == "active"}
        else:
            filtered = {k: v for k, v in theories_data.items() if v.get("status") == "active"}
        
        if not filtered:
            msg = f"Aucune théorie trouvée" + (f" pour **{manga}**" if manga else "") + "."
            await ctx.send(f"❌ {msg}")
            return
        
        # Trier: boostées en premier, puis par score
        def sort_key(item):
            theory = item[1]
            is_boosted = theory.get("boosted", False)
            if is_boosted and theory.get("boost_expires"):
                expires = datetime.fromisoformat(theory["boost_expires"])
                if datetime.now() >= expires:
                    is_boosted = False
            score = len(theory.get("votes_up", [])) - len(theory.get("votes_down", []))
            return (is_boosted, score)
        
        sorted_theories = sorted(filtered.items(), key=sort_key, reverse=True)[:10]
        
        title = f"💭 Théories" + (f" - {get_manga_emoji(manga)} {manga}" if manga else " Populaires")
        
        embed = discord.Embed(
            title=title,
            description=f"Top {len(sorted_theories)} théories",
            color=discord.Color.purple(),
            timestamp=datetime.now()
        )
        
        for i, (tid, theory) in enumerate(sorted_theories, 1):
            score = len(theory.get("votes_up", [])) - len(theory.get("votes_down", []))
            score_emoji = "🔥" if score >= 5 else "👍" if score >= 0 else "👎"
            
            is_boosted = theory.get("boosted", False)
            boost_text = "🚀 " if is_boosted else ""
            
            manga_emoji = get_manga_emoji(theory.get("manga", ""))
            contenu = theory["contenu"][:100] + "..." if len(theory["contenu"]) > 100 else theory["contenu"]
            
            embed.add_field(
                name=f"{i}. {boost_text}{manga_emoji} {theory.get('manga', 'N/A')} | {score_emoji} {score}",
                value=f"*\"{contenu}\"*\n— {theory.get('author_name', 'Inconnu')} | `{tid[:20]}...`",
                inline=False
            )
        
        embed.set_footer(text="Utilisez !theory_info <id> pour plus de détails")
        await ctx.send(embed=embed)
    
    @commands.command(name="theory_info")
    async def theory_info(self, ctx, theory_id: str):
        """Affiche les détails d'une théorie"""
        found_id = None
        for tid in theories_data.keys():
            if tid.startswith(theory_id) or theory_id in tid:
                found_id = tid
                break
        
        if not found_id:
            await ctx.send("❌ Théorie introuvable.")
            return
        
        theory = theories_data[found_id]
        manga_emoji = get_manga_emoji(theory.get("manga", ""))
        
        score = len(theory.get("votes_up", [])) - len(theory.get("votes_down", []))
        
        status_map = {
            "active": "🔮 En attente",
            "confirmed": "✅ Confirmée",
            "debunked": "❌ Réfutée"
        }
        
        embed = discord.Embed(
            title=f"💭 Théorie - {manga_emoji} {theory.get('manga', 'N/A')}",
            description=theory["contenu"],
            color=discord.Color.purple(),
            timestamp=datetime.fromisoformat(theory["created_at"])
        )
        
        author = ctx.guild.get_member(int(theory["author_id"]))
        author_name = author.mention if author else theory.get("author_name", "Inconnu")
        
        embed.add_field(name="👤 Auteur", value=author_name, inline=True)
        embed.add_field(name="📊 Score", value=f"👍 {len(theory.get('votes_up', []))} | 👎 {len(theory.get('votes_down', []))}", inline=True)
        embed.add_field(name="🏷️ Statut", value=status_map.get(theory.get("status", "active"), "🔮 En attente"), inline=True)
        
        embed.set_footer(text=f"ID: {found_id}")
        
        await ctx.send(embed=embed)
    
    @commands.command(name="theory_status")
    @commands.has_any_role(1326417422663680090, 1330147432847114321)
    async def theory_status(self, ctx, theory_id: str, status: str):
        """Change le statut d'une théorie (admin)."""
        valid_status = ["confirmed", "debunked", "active"]
        if status.lower() not in valid_status:
            await ctx.send(f"❌ Statut invalide. Choisissez parmi: {', '.join(valid_status)}")
            return
        
        found_id = None
        for tid in theories_data.keys():
            if tid.startswith(theory_id) or theory_id in tid:
                found_id = tid
                break
        
        if not found_id:
            await ctx.send("❌ Théorie introuvable.")
            return
        
        old_status = theories_data[found_id].get("status", "active")
        theories_data[found_id]["status"] = status.lower()
        
        # Bonus si théorie confirmée
        if status.lower() == "confirmed" and old_status != "confirmed":
            author_id = theories_data[found_id]["author_id"]
            add_points(int(author_id), 100, "theory_confirmed")
            
            try:
                from achievements import unlock_badge
                unlock_badge(int(author_id), "theory_confirmed")
            except:
                pass
        
        sauvegarder_donnees()
        
        status_emoji = {"confirmed": "✅", "debunked": "❌", "active": "🔮"}
        await ctx.send(f"{status_emoji.get(status.lower(), '🔮')} Statut de la théorie mis à jour: **{status}**")
    
    # ==================== LEADERBOARDS ====================
    
    @commands.command(name="leaderboard", aliases=["lb", "top"])
    async def leaderboard(self, ctx, category: str = "points"):
        """
        Affiche les classements.
        Catégories: points, reviews, theories, weekly
        """
        category = category.lower()
        
        if category not in ["points", "reviews", "theories", "weekly"]:
            await ctx.send("❌ Catégorie invalide. Choisissez: `points`, `reviews`, `theories`, `weekly`")
            return
        
        # Trier les utilisateurs
        if category == "points":
            sorted_users = sorted(user_stats.items(), key=lambda x: x[1].get("points", 0), reverse=True)[:10]
            title = "🏆 Top 10 - Points"
            field_name = "points"
            emoji = "💰"
        elif category == "reviews":
            sorted_users = sorted(user_stats.items(), key=lambda x: x[1].get("reviews_count", 0), reverse=True)[:10]
            title = "📝 Top 10 - Reviews"
            field_name = "reviews_count"
            emoji = "📝"
        elif category == "theories":
            sorted_users = sorted(user_stats.items(), key=lambda x: x[1].get("theories_count", 0), reverse=True)[:10]
            title = "💭 Top 10 - Théories"
            field_name = "theories_count"
            emoji = "💭"
        elif category == "weekly":
            sorted_users = sorted(user_stats.items(), key=lambda x: x[1].get("weekly_points", 0), reverse=True)[:10]
            title = "📅 Top 10 - Cette Semaine"
            field_name = "weekly_points"
            emoji = "⚡"
        
        embed = discord.Embed(
            title=title,
            color=discord.Color.gold(),
            timestamp=datetime.now()
        )
        
        medals = ["🥇", "🥈", "🥉"]
        
        description = ""
        for i, (user_id, stats) in enumerate(sorted_users, 1):
            member = ctx.guild.get_member(int(user_id))
            if not member:
                continue
            
            medal = medals[i-1] if i <= 3 else f"**{i}.**"
            value = stats.get(field_name, 0)
            
            # Indicateur de streak pour le leaderboard weekly
            streak_text = ""
            if category == "weekly" and stats.get("daily_streak", 0) > 1:
                streak_text = f" 🔥{stats['daily_streak']}"
            
            description += f"{medal} {member.display_name} - {emoji} **{value:,}**{streak_text}\n"
        
        embed.description = description if description else "Aucune donnée disponible."
        
        # Position de l'utilisateur
        user_pos = None
        for i, (uid, _) in enumerate(sorted(user_stats.items(), key=lambda x: x[1].get(field_name, 0), reverse=True), 1):
            if uid == str(ctx.author.id):
                user_pos = i
                break
        
        if user_pos:
            my_stats = get_user_stats(ctx.author.id)
            embed.add_field(
                name="📍 Votre Position",
                value=f"#{user_pos} - {emoji} **{my_stats.get(field_name, 0):,}**",
                inline=False
            )
        
        embed.set_footer(text=f"!leaderboard [points/reviews/theories/weekly]")
        await ctx.send(embed=embed)
    
    @commands.command(name="profile", aliases=["stats", "me"])
    async def profile(self, ctx, member: discord.Member = None):
        """Affiche le profil communautaire d'un membre"""
        member = member or ctx.author
        stats = get_user_stats(member.id)
        
        # Calculer le rang
        sorted_by_points = sorted(user_stats.items(), key=lambda x: x[1].get("points", 0), reverse=True)
        rank = 1
        for uid, _ in sorted_by_points:
            if uid == str(member.id):
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
        
        embed.add_field(name="📝 Reviews", value=str(stats.get("reviews_count", 0)), inline=True)
        embed.add_field(name="💭 Théories", value=str(stats.get("theories_count", 0)), inline=True)
        embed.add_field(name="🗳️ Votes donnés", value=str(stats.get("theories_votes_given", 0)), inline=True)
        
        # Stats hebdomadaires
        embed.add_field(
            name="📅 Cette Semaine",
            value=f"⚡ {stats.get('weekly_points', 0):,} pts\n📝 {stats.get('weekly_reviews', 0)} reviews",
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
                badges_display = " ".join([badges_data[bid]["emoji"] for bid in user_badges["displayed"] if bid in badges_data])
                embed.add_field(name="🏅 Badges", value=badges_display, inline=False)
        except:
            pass
        
        embed.set_footer(text=f"Total gagné: {stats.get('total_points_earned', 0):,} pts")
        
        await ctx.send(embed=embed)
    
    # ==================== LISTENERS ====================
    
    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        """Gère les votes sur les théories"""
        if payload.user_id == self.bot.user.id:
            return
        
        emoji = str(payload.emoji)
        if emoji not in ["👍", "👎"]:
            return
        
        for theory_id, theory in theories_data.items():
            if theory.get("message_id") == payload.message_id:
                user_id = str(payload.user_id)
                
                # Ne pas voter pour sa propre théorie
                if user_id == theory["author_id"]:
                    return
                
                if user_id in theory.get("votes_up", []):
                    theory["votes_up"].remove(user_id)
                if user_id in theory.get("votes_down", []):
                    theory["votes_down"].remove(user_id)
                
                # Vérifier super vote
                super_vote = False
                try:
                    from shop import get_user_inventory
                    inv = get_user_inventory(payload.user_id)
                    if "super_vote" in inv.get("active_boosts", {}):
                        super_vote = True
                        del inv["active_boosts"]["super_vote"]
                        from shop import sauvegarder_shop
                        sauvegarder_shop()
                except:
                    pass
                
                vote_count = 3 if super_vote else 1
                
                if emoji == "👍":
                    if "votes_up" not in theory:
                        theory["votes_up"] = []
                    for _ in range(vote_count):
                        theory["votes_up"].append(user_id)
                else:
                    if "votes_down" not in theory:
                        theory["votes_down"] = []
                    theory["votes_down"].append(user_id)
                
                voter_stats = get_user_stats(payload.user_id)
                voter_stats["theories_votes_given"] += 1
                add_points(payload.user_id, POINTS["theory_vote"])
                
                if emoji == "👍":
                    author_stats = get_user_stats(int(theory["author_id"]))
                    author_stats["theories_votes_received"] += vote_count
                    add_points(int(theory["author_id"]), vote_count)
                
                sauvegarder_donnees()
                break
    
    # ==================== HELPERS ====================
    
    async def update_chapter_embed(self, chapter_key):
        """Met à jour l'embed d'interaction d'un chapitre"""
        if chapter_key not in chapters_data:
            return
        
        chapter = chapters_data[chapter_key]
        
        if "interaction_message_id" not in chapter:
            return
        
        try:
            channel = self.bot.get_channel(chapter["channel_id"])
            if not channel:
                return
            
            message = await channel.fetch_message(chapter["interaction_message_id"])
            
            reviews = chapter.get("reviews", {})
            moyenne = sum(r["note"] for r in reviews.values()) / len(reviews) if reviews else 0
            
            manga_emoji = get_manga_emoji(chapter["manga"])
            
            embed = discord.Embed(
                title=f"{manga_emoji} {chapter['manga']} - Chapitre {chapter['chapter']}",
                description=(
                    "**📝 Partagez votre avis sur ce chapitre !**\n\n"
                    f"⭐ **Noter** : `!review {chapter['manga']} {chapter['chapter']} <1-5> [commentaire]`\n"
                    f"💭 **Théorie** : `!theory {chapter['manga']} <votre théorie>`\n"
                    f"📊 **Voir les avis** : `!chapter_reviews {chapter['manga']} {chapter['chapter']}`\n\n"
                    "━━━━━━━━━━━━━━━━━━━━━━━━"
                ),
                color=discord.Color.gold(),
                timestamp=datetime.now()
            )
            
            stars = f"⭐ {moyenne:.1f}/5" if reviews else "⭐ --"
            embed.add_field(
                name="📊 Statistiques",
                value=f"{stars}\n📝 Reviews: {len(reviews)}\n💭 Théories: {len(chapter.get('theories_linked', []))}",
                inline=True
            )
            
            embed.add_field(
                name="🏆 Points à gagner",
                value=f"+{POINTS['review']} pts (review)\n+{POINTS['theory']} pts (théorie)",
                inline=True
            )
            
            embed.set_footer(text=f"ID: {chapter_key}")
            
            await message.edit(embed=embed)
            
        except Exception as e:
            print(f"❌ Erreur mise à jour embed: {e}")
    
    @commands.command(name="my_reviews")
    async def my_reviews(self, ctx):
        """Affiche vos reviews"""
        user_id = str(ctx.author.id)
        
        user_reviews = []
        for chapter_key, chapter in chapters_data.items():
            if user_id in chapter.get("reviews", {}):
                user_reviews.append({
                    "key": chapter_key,
                    "manga": chapter["manga"],
                    "chapter": chapter["chapter"],
                    "review": chapter["reviews"][user_id]
                })
        
        if not user_reviews:
            await ctx.send("❌ Vous n'avez pas encore laissé de review.")
            return
        
        embed = discord.Embed(
            title=f"📝 Vos Reviews",
            description=f"Vous avez laissé **{len(user_reviews)}** review(s)",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        
        for r in user_reviews[:10]:
            manga_emoji = get_manga_emoji(r["manga"])
            stars = "⭐" * r["review"]["note"]
            
            value = f"{stars}"
            if r["review"].get("commentaire"):
                value += f"\n*\"{r['review']['commentaire'][:50]}...\"*" if len(r["review"].get("commentaire", "")) > 50 else f"\n*\"{r['review']['commentaire']}\"*"
            
            embed.add_field(
                name=f"{manga_emoji} {r['manga']} Ch.{r['chapter']}",
                value=value,
                inline=True
            )
        
        embed.set_thumbnail(url=ctx.author.avatar.url if ctx.author.avatar else None)
        await ctx.send(embed=embed)


async def setup(bot):
    """Setup pour discord.py 2.0+"""
    await bot.add_cog(CommunitySystem(bot))