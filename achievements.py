# achievements.py
# Système de badges AMÉLIORÉ : Vérification auto, Notifications progression, Plus de badges
import discord
from discord.ext import commands
import json
import os
from datetime import datetime
from config import COLORS

BADGES_FILE = "data/user_badges.json"
os.makedirs("data", exist_ok=True)

# Badges utilisateurs
user_badges_data = {}

# Définition des badges
badges_data = {
    # === REVIEWS ===
    "first_review": {
        "name": "Premier Pas",
        "description": "Poster sa première review",
        "emoji": "🌱",
        "category": "reviews",
        "condition": {"reviews_count": 1},
        "points_reward": 10,
        "rarity": "common"
    },
    "reviewer_10": {
        "name": "Critique Amateur",
        "description": "Poster 10 reviews",
        "emoji": "📝",
        "category": "reviews",
        "condition": {"reviews_count": 10},
        "points_reward": 50,
        "rarity": "common"
    },
    "reviewer_50": {
        "name": "Critique Confirmé",
        "description": "Poster 50 reviews",
        "emoji": "✍️",
        "category": "reviews",
        "condition": {"reviews_count": 50},
        "points_reward": 150,
        "rarity": "uncommon"
    },
    "reviewer_100": {
        "name": "Critique Expert",
        "description": "Poster 100 reviews",
        "emoji": "🎭",
        "category": "reviews",
        "condition": {"reviews_count": 100},
        "points_reward": 300,
        "rarity": "rare"
    },
    "reviewer_500": {
        "name": "Maître Critique",
        "description": "Poster 500 reviews",
        "emoji": "👑",
        "category": "reviews",
        "condition": {"reviews_count": 500},
        "points_reward": 1000,
        "rarity": "legendary"
    },
    
    # === THÉORIES ===
    "first_theory": {
        "name": "Penseur",
        "description": "Poster sa première théorie",
        "emoji": "💭",
        "category": "theories",
        "condition": {"theories_count": 1},
        "points_reward": 15,
        "rarity": "common"
    },
    "theorist_10": {
        "name": "Théoricien",
        "description": "Poster 10 théories",
        "emoji": "🧠",
        "category": "theories",
        "condition": {"theories_count": 10},
        "points_reward": 75,
        "rarity": "uncommon"
    },
    "theorist_50": {
        "name": "Philosophe",
        "description": "Poster 50 théories",
        "emoji": "📚",
        "category": "theories",
        "condition": {"theories_count": 50},
        "points_reward": 250,
        "rarity": "rare"
    },
    "theory_confirmed": {
        "name": "Visionnaire",
        "description": "Avoir une théorie confirmée",
        "emoji": "🔮",
        "category": "theories",
        "condition": {"theory_confirmed": True},
        "points_reward": 500,
        "rarity": "epic",
        "manual": True  # Déblocage manuel par admin
    },
    "theory_popular": {
        "name": "Influenceur",
        "description": "Avoir une théorie avec 10+ upvotes",
        "emoji": "🔥",
        "category": "theories",
        "condition": {"theory_votes": 10},
        "points_reward": 100,
        "rarity": "uncommon"
    },
    
    # === POINTS & ACTIVITÉ ===
    "points_1000": {
        "name": "Économe",
        "description": "Accumuler 1,000 points",
        "emoji": "💰",
        "category": "points",
        "condition": {"total_points": 1000},
        "points_reward": 100,
        "rarity": "common"
    },
    "points_5000": {
        "name": "Riche",
        "description": "Accumuler 5,000 points",
        "emoji": "💎",
        "category": "points",
        "condition": {"total_points": 5000},
        "points_reward": 250,
        "rarity": "uncommon"
    },
    "points_10000": {
        "name": "Millionnaire",
        "description": "Accumuler 10,000 points",
        "emoji": "🏦",
        "category": "points",
        "condition": {"total_points": 10000},
        "points_reward": 500,
        "rarity": "rare"
    },
    "streak_7": {
        "name": "Régulier",
        "description": "Maintenir un streak de 7 jours",
        "emoji": "🔥",
        "category": "activity",
        "condition": {"daily_streak": 7},
        "points_reward": 70,
        "rarity": "common"
    },
    "streak_30": {
        "name": "Dévoué",
        "description": "Maintenir un streak de 30 jours",
        "emoji": "⚡",
        "category": "activity",
        "condition": {"daily_streak": 30},
        "points_reward": 300,
        "rarity": "rare"
    },
    "streak_100": {
        "name": "Légende",
        "description": "Maintenir un streak de 100 jours",
        "emoji": "🌟",
        "category": "activity",
        "condition": {"daily_streak": 100},
        "points_reward": 1000,
        "rarity": "legendary"
    },
    
    # === VOTES ===
    "voter_50": {
        "name": "Démocrate",
        "description": "Voter sur 50 théories",
        "emoji": "🗳️",
        "category": "votes",
        "condition": {"theories_votes_given": 50},
        "points_reward": 50,
        "rarity": "common"
    },
    "voter_200": {
        "name": "Électeur Assidu",
        "description": "Voter sur 200 théories",
        "emoji": "📊",
        "category": "votes",
        "condition": {"theories_votes_given": 200},
        "points_reward": 150,
        "rarity": "uncommon"
    },
    
    # === MANGAS SPÉCIFIQUES ===
    "fan_ao_no_exorcist": {
        "name": "Fan d'Ao No Exorcist",
        "description": "10 reviews sur Ao No Exorcist",
        "emoji": "👹",
        "category": "manga",
        "condition": {"manga_reviews": {"ao no exorcist": 10}},
        "points_reward": 100,
        "rarity": "uncommon"
    },
    "fan_satsudou": {
        "name": "Fan de Satsudou",
        "description": "10 reviews sur Satsudou",
        "emoji": "🩸",
        "category": "manga",
        "condition": {"manga_reviews": {"satsudou": 10}},
        "points_reward": 100,
        "rarity": "uncommon"
    },
    "fan_tougen_anki": {
        "name": "Fan de Tougen Anki",
        "description": "10 reviews sur Tougen Anki",
        "emoji": "😈",
        "category": "manga",
        "condition": {"manga_reviews": {"tougen anki": 10}},
        "points_reward": 100,
        "rarity": "uncommon"
    },
    "fan_catenaccio": {
        "name": "Fan de Catenaccio",
        "description": "10 reviews sur Catenaccio",
        "emoji": "⚽",
        "category": "manga",
        "condition": {"manga_reviews": {"catenaccio": 10}},
        "points_reward": 100,
        "rarity": "uncommon"
    },
    "fan_tokyo_underworld": {
        "name": "Fan de Tokyo Underworld",
        "description": "10 reviews sur Tokyo Underworld",
        "emoji": "🗼",
        "category": "manga",
        "condition": {"manga_reviews": {"tokyo underworld": 10}},
        "points_reward": 100,
        "rarity": "uncommon"
    },
    "polyvalent": {
        "name": "Polyvalent",
        "description": "Reviewer 5 mangas différents",
        "emoji": "📖",
        "category": "manga",
        "condition": {"manga_count": 5},
        "points_reward": 200,
        "rarity": "rare"
    },
    
    # === SHOP & COLLECTIBLES ===
    "collector": {
        "name": "Collectionneur",
        "description": "Badge exclusif acheté en boutique",
        "emoji": "🏅",
        "category": "shop",
        "condition": {"purchased": True},
        "points_reward": 0,
        "rarity": "rare",
        "purchasable": True
    },
    "big_spender": {
        "name": "Gros Dépensier",
        "description": "Dépenser 5,000 points en boutique",
        "emoji": "💸",
        "category": "shop",
        "condition": {"total_spent": 5000},
        "points_reward": 200,
        "rarity": "uncommon"
    },
    "lottery_winner": {
        "name": "Chanceux",
        "description": "Gagner la loterie",
        "emoji": "🎰",
        "category": "shop",
        "condition": {"lottery_wins": 1},
        "points_reward": 0,
        "rarity": "epic",
        "manual": True
    },
    
    # === SPÉCIAUX ===
    "early_bird": {
        "name": "Early Bird",
        "description": "Être parmi les 10 premiers à poster une review",
        "emoji": "🐦",
        "category": "special",
        "condition": {"first_10_reviewer": True},
        "points_reward": 150,
        "rarity": "rare",
        "manual": True
    },
    "veteran": {
        "name": "Vétéran",
        "description": "Membre depuis plus de 6 mois",
        "emoji": "🎖️",
        "category": "special",
        "condition": {"member_months": 6},
        "points_reward": 300,
        "rarity": "rare"
    },
    "og": {
        "name": "OG",
        "description": "Membre depuis plus d'un an",
        "emoji": "👴",
        "category": "special",
        "condition": {"member_months": 12},
        "points_reward": 500,
        "rarity": "legendary"
    }
}

# Raretés avec couleurs
RARITY_COLORS = {
    "common": 0x9e9e9e,      # Gris
    "uncommon": 0x4caf50,    # Vert
    "rare": 0x2196f3,        # Bleu
    "epic": 0x9c27b0,        # Violet
    "legendary": 0xffc107    # Or
}

RARITY_NAMES = {
    "common": "Commun",
    "uncommon": "Peu commun",
    "rare": "Rare",
    "epic": "Épique",
    "legendary": "Légendaire"
}

def charger_badges():
    """Charge les données des badges"""
    global user_badges_data
    if os.path.exists(BADGES_FILE):
        try:
            with open(BADGES_FILE, "r", encoding="utf-8") as f:
                contenu = f.read().strip()
                if contenu:
                    user_badges_data.update(json.loads(contenu))
            print("✅ Badges chargés")
        except Exception as e:
            print(f"❌ Erreur chargement badges: {e}")

def sauvegarder_badges():
    """Sauvegarde les données des badges"""
    try:
        with open(BADGES_FILE, "w", encoding="utf-8") as f:
            json.dump(user_badges_data, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"❌ Erreur sauvegarde badges: {e}")

def get_user_badges(user_id):
    """Récupère ou crée les badges d'un utilisateur"""
    user_id_str = str(user_id)
    if user_id_str not in user_badges_data:
        user_badges_data[user_id_str] = {
            "unlocked": [],
            "displayed": [],  # Badges affichés (max 3)
            "stats": {
                "reviews_count": 0,
                "theories_count": 0,
                "theories_votes_given": 0,
                "theories_votes_received": 0,
                "total_points": 0,
                "daily_streak": 0,
                "total_spent": 0,
                "manga_reviews": {}
            },
            "progress": {},  # Progression vers les badges
            "notifications_seen": []
        }
    return user_badges_data[user_id_str]

def check_badges(user_id, user_stats=None):
    """
    Vérifie et débloque automatiquement les badges.
    Retourne la liste des badges nouvellement débloqués.
    """
    user_badges = get_user_badges(user_id)
    unlocked = user_badges.get("unlocked", [])
    newly_unlocked = []
    
    # Mettre à jour les stats locales
    if user_stats:
        for key in ["reviews_count", "theories_count", "theories_votes_given", 
                    "theories_votes_received", "daily_streak"]:
            if key in user_stats:
                user_badges["stats"][key] = user_stats[key]
        
        # Total points gagné
        if "total_points_earned" in user_stats:
            user_badges["stats"]["total_points"] = user_stats["total_points_earned"]
        elif "points" in user_stats:
            user_badges["stats"]["total_points"] = user_stats["points"]
    
    stats = user_badges["stats"]
    
    for badge_id, badge in badges_data.items():
        # Skip si déjà débloqué ou si c'est un badge manuel
        if badge_id in unlocked:
            continue
        if badge.get("manual") or badge.get("purchasable"):
            continue
        
        condition = badge.get("condition", {})
        should_unlock = True
        
        # Vérifier chaque condition
        for cond_key, cond_value in condition.items():
            if cond_key == "manga_reviews":
                # Condition spéciale pour les mangas
                for manga, count in cond_value.items():
                    manga_reviews = stats.get("manga_reviews", {})
                    if manga_reviews.get(manga, 0) < count:
                        should_unlock = False
                        break
            elif cond_key == "manga_count":
                # Nombre de mangas différents
                manga_reviews = stats.get("manga_reviews", {})
                if len(manga_reviews) < cond_value:
                    should_unlock = False
            elif cond_key == "member_months":
                # Ancienneté (vérifiée ailleurs)
                should_unlock = False
            else:
                # Condition numérique standard
                if stats.get(cond_key, 0) < cond_value:
                    should_unlock = False
        
        if should_unlock:
            newly_unlocked.append(unlock_badge(user_id, badge_id))
    
    return [b for b in newly_unlocked if b is not None]

def unlock_badge(user_id, badge_id):
    """Débloque un badge pour un utilisateur"""
    if badge_id not in badges_data:
        return None
    
    user_badges = get_user_badges(user_id)
    
    if badge_id in user_badges["unlocked"]:
        return None
    
    user_badges["unlocked"].append(badge_id)
    user_badges[f"unlocked_{badge_id}_date"] = datetime.now().isoformat()
    
    badge = badges_data[badge_id]
    
    # Donner les points de récompense
    if badge.get("points_reward", 0) > 0:
        try:
            from community import add_points
            add_points(int(user_id), badge["points_reward"], f"badge_{badge_id}")
        except:
            pass
    
    sauvegarder_badges()
    
    return badge

def get_badge_progress(user_id, badge_id):
    """Calcule la progression vers un badge"""
    if badge_id not in badges_data:
        return None
    
    badge = badges_data[badge_id]
    user_badges = get_user_badges(user_id)
    stats = user_badges["stats"]
    
    if badge_id in user_badges["unlocked"]:
        return {"progress": 100, "current": "MAX", "target": "MAX", "completed": True}
    
    condition = badge.get("condition", {})
    
    # Trouver la condition principale
    for cond_key, cond_value in condition.items():
        if cond_key == "manga_reviews":
            # Pour les badges manga spécifiques
            for manga, target in cond_value.items():
                current = stats.get("manga_reviews", {}).get(manga, 0)
                progress = min(100, int((current / target) * 100))
                return {"progress": progress, "current": current, "target": target, "completed": False}
        elif cond_key == "manga_count":
            current = len(stats.get("manga_reviews", {}))
            progress = min(100, int((current / cond_value) * 100))
            return {"progress": progress, "current": current, "target": cond_value, "completed": False}
        elif isinstance(cond_value, (int, float)):
            current = stats.get(cond_key, 0)
            progress = min(100, int((current / cond_value) * 100))
            return {"progress": progress, "current": current, "target": cond_value, "completed": False}
    
    return None


class AchievementsSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        charger_badges()
    
    @commands.command(name="badges", aliases=["achievements", "succes"])
    async def badges(self, ctx, member: discord.Member = None):
        """Affiche les badges d'un membre"""
        member = member or ctx.author
        user_badges = get_user_badges(member.id)
        unlocked = user_badges.get("unlocked", [])
        
        embed = discord.Embed(
            title=f"🏅 Badges de {member.display_name}",
            description=f"**{len(unlocked)}/{len(badges_data)}** badges débloqués",
            color=member.color if member.color != discord.Color.default() else discord.Color.gold(),
            timestamp=datetime.now()
        )
        
        embed.set_thumbnail(url=member.avatar.url if member.avatar else None)
        
        # Badges affichés
        displayed = user_badges.get("displayed", [])[:3]
        if displayed:
            displayed_text = " ".join([badges_data[bid]["emoji"] for bid in displayed if bid in badges_data])
            embed.add_field(name="✨ Badges Affichés", value=displayed_text or "Aucun", inline=False)
        
        # Grouper par catégorie
        categories = {
            "reviews": "📝 Reviews",
            "theories": "💭 Théories",
            "points": "💰 Points",
            "activity": "🔥 Activité",
            "votes": "🗳️ Votes",
            "manga": "📚 Mangas",
            "shop": "🛒 Boutique",
            "special": "⭐ Spéciaux"
        }
        
        for cat_id, cat_name in categories.items():
            cat_badges = [bid for bid, b in badges_data.items() if b.get("category") == cat_id]
            
            if not cat_badges:
                continue
            
            badges_text = ""
            for bid in cat_badges:
                badge = badges_data[bid]
                if bid in unlocked:
                    badges_text += f"{badge['emoji']} "
                else:
                    badges_text += "⬜ "
            
            # Compter débloqués
            unlocked_count = sum(1 for bid in cat_badges if bid in unlocked)
            
            embed.add_field(
                name=f"{cat_name} ({unlocked_count}/{len(cat_badges)})",
                value=badges_text.strip() or "Aucun",
                inline=True
            )
        
        embed.set_footer(text="!badge_info <nom> pour plus de détails | !displaybadge <nom> pour afficher")
        await ctx.send(embed=embed)
    
    @commands.command(name="badge_info", aliases=["badgeinfo"])
    async def badge_info(self, ctx, *, badge_name: str):
        """Affiche les détails d'un badge"""
        # Rechercher le badge
        badge_id = None
        badge = None
        
        badge_name_lower = badge_name.lower()
        
        for bid, b in badges_data.items():
            if bid == badge_name_lower or b["name"].lower() == badge_name_lower:
                badge_id = bid
                badge = b
                break
        
        if not badge:
            await ctx.send("❌ Badge introuvable.")
            return
        
        user_badges = get_user_badges(ctx.author.id)
        is_unlocked = badge_id in user_badges.get("unlocked", [])
        
        rarity = badge.get("rarity", "common")
        
        embed = discord.Embed(
            title=f"{badge['emoji']} {badge['name']}",
            description=badge["description"],
            color=RARITY_COLORS.get(rarity, 0x9e9e9e),
            timestamp=datetime.now()
        )
        
        embed.add_field(name="🏷️ Rareté", value=RARITY_NAMES.get(rarity, "Commun"), inline=True)
        embed.add_field(name="🏆 Récompense", value=f"+{badge.get('points_reward', 0)} pts", inline=True)
        
        # Statut
        if is_unlocked:
            unlock_date = user_badges.get(f"unlocked_{badge_id}_date", "Inconnu")
            if unlock_date != "Inconnu":
                unlock_date = unlock_date[:10]
            embed.add_field(name="✅ Statut", value=f"Débloqué le {unlock_date}", inline=True)
        else:
            progress = get_badge_progress(ctx.author.id, badge_id)
            if progress and not badge.get("manual"):
                bar_length = int(progress["progress"] / 10)
                bar = "█" * bar_length + "░" * (10 - bar_length)
                embed.add_field(
                    name="📊 Progression",
                    value=f"`{bar}` {progress['progress']}%\n{progress['current']}/{progress['target']}",
                    inline=False
                )
            elif badge.get("manual"):
                embed.add_field(name="🔒 Statut", value="Badge spécial (déblocage manuel)", inline=True)
            elif badge.get("purchasable"):
                embed.add_field(name="🛒 Statut", value="Disponible en boutique", inline=True)
            else:
                embed.add_field(name="🔒 Statut", value="Non débloqué", inline=True)
        
        # Catégorie
        categories = {
            "reviews": "📝 Reviews",
            "theories": "💭 Théories",
            "points": "💰 Points",
            "activity": "🔥 Activité",
            "votes": "🗳️ Votes",
            "manga": "📚 Mangas",
            "shop": "🛒 Boutique",
            "special": "⭐ Spéciaux"
        }
        embed.add_field(name="📁 Catégorie", value=categories.get(badge.get("category"), "Autre"), inline=True)
        
        await ctx.send(embed=embed)
    
    @commands.command(name="displaybadge", aliases=["showbadge", "equipbadge"])
    async def display_badge(self, ctx, *, badge_name: str):
        """Équipe un badge pour l'afficher sur votre profil (max 3)"""
        # Rechercher le badge
        badge_id = None
        badge = None
        
        badge_name_lower = badge_name.lower()
        
        for bid, b in badges_data.items():
            if bid == badge_name_lower or b["name"].lower() == badge_name_lower:
                badge_id = bid
                badge = b
                break
        
        if not badge:
            await ctx.send("❌ Badge introuvable.")
            return
        
        user_badges = get_user_badges(ctx.author.id)
        
        if badge_id not in user_badges.get("unlocked", []):
            await ctx.send("❌ Vous n'avez pas débloqué ce badge.")
            return
        
        displayed = user_badges.get("displayed", [])
        
        if badge_id in displayed:
            # Retirer le badge
            displayed.remove(badge_id)
            await ctx.send(f"✅ Le badge **{badge['name']}** {badge['emoji']} a été retiré de votre profil.")
        else:
            if len(displayed) >= 3:
                # Remplacer le plus ancien
                displayed.pop(0)
            displayed.append(badge_id)
            await ctx.send(f"✅ Le badge **{badge['name']}** {badge['emoji']} est maintenant affiché sur votre profil !")
        
        user_badges["displayed"] = displayed
        sauvegarder_badges()
    
    @commands.command(name="progress", aliases=["progression"])
    async def progress(self, ctx, member: discord.Member = None):
        """Affiche la progression vers les prochains badges"""
        member = member or ctx.author
        user_badges = get_user_badges(member.id)
        unlocked = user_badges.get("unlocked", [])
        
        embed = discord.Embed(
            title=f"📊 Progression de {member.display_name}",
            description="Badges les plus proches d'être débloqués",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        
        # Calculer la progression de tous les badges non débloqués
        progressions = []
        
        for badge_id, badge in badges_data.items():
            if badge_id in unlocked:
                continue
            if badge.get("manual") or badge.get("purchasable"):
                continue
            
            progress = get_badge_progress(member.id, badge_id)
            if progress and progress["progress"] > 0:
                progressions.append({
                    "id": badge_id,
                    "badge": badge,
                    "progress": progress
                })
        
        # Trier par progression décroissante
        progressions.sort(key=lambda x: x["progress"]["progress"], reverse=True)
        
        if not progressions:
            embed.description = "Aucune progression en cours. Commencez à participer !"
        else:
            for p in progressions[:8]:
                badge = p["badge"]
                progress = p["progress"]
                
                bar_length = int(progress["progress"] / 10)
                bar = "█" * bar_length + "░" * (10 - bar_length)
                
                embed.add_field(
                    name=f"{badge['emoji']} {badge['name']}",
                    value=f"`{bar}` **{progress['progress']}%**\n{progress['current']}/{progress['target']}",
                    inline=True
                )
        
        embed.set_thumbnail(url=member.avatar.url if member.avatar else None)
        embed.set_footer(text="!badges pour voir tous vos badges")
        
        await ctx.send(embed=embed)
    
    @commands.command(name="leaderboard_badges", aliases=["lb_badges", "topbadges"])
    async def leaderboard_badges(self, ctx):
        """Affiche le classement par nombre de badges"""
        # Trier les utilisateurs par nombre de badges
        sorted_users = sorted(
            user_badges_data.items(),
            key=lambda x: len(x[1].get("unlocked", [])),
            reverse=True
        )[:10]
        
        embed = discord.Embed(
            title="🏅 Top 10 - Badges",
            color=discord.Color.gold(),
            timestamp=datetime.now()
        )
        
        medals = ["🥇", "🥈", "🥉"]
        description = ""
        
        for i, (user_id, data) in enumerate(sorted_users, 1):
            member = ctx.guild.get_member(int(user_id))
            if not member:
                continue
            
            medal = medals[i-1] if i <= 3 else f"**{i}.**"
            count = len(data.get("unlocked", []))
            
            # Badges affichés
            displayed = data.get("displayed", [])[:3]
            badges_display = " ".join([badges_data[bid]["emoji"] for bid in displayed if bid in badges_data]) or ""
            
            description += f"{medal} {member.display_name} - **{count}** badges {badges_display}\n"
        
        embed.description = description if description else "Aucune donnée disponible."
        
        # Position de l'utilisateur
        user_badges = get_user_badges(ctx.author.id)
        user_count = len(user_badges.get("unlocked", []))
        
        user_pos = None
        for i, (uid, _) in enumerate(sorted(user_badges_data.items(), 
                                            key=lambda x: len(x[1].get("unlocked", [])), 
                                            reverse=True), 1):
            if uid == str(ctx.author.id):
                user_pos = i
                break
        
        if user_pos:
            embed.add_field(
                name="📍 Votre Position",
                value=f"#{user_pos} - **{user_count}** badges",
                inline=False
            )
        
        await ctx.send(embed=embed)
    
    # ==================== COMMANDES ADMIN ====================
    
    @commands.command(name="givebadge")
    @commands.has_permissions(administrator=True)
    async def give_badge(self, ctx, member: discord.Member, *, badge_name: str):
        """Donne un badge à un membre (admin)"""
        badge_id = None
        badge = None
        
        badge_name_lower = badge_name.lower()
        
        for bid, b in badges_data.items():
            if bid == badge_name_lower or b["name"].lower() == badge_name_lower:
                badge_id = bid
                badge = b
                break
        
        if not badge:
            await ctx.send("❌ Badge introuvable.")
            return
        
        result = unlock_badge(member.id, badge_id)
        
        if result:
            await ctx.send(f"✅ Le badge **{badge['name']}** {badge['emoji']} a été donné à {member.mention} !")
            
            # Notifier le membre
            try:
                embed = discord.Embed(
                    title="🎉 Nouveau Badge Débloqué !",
                    description=f"Vous avez reçu le badge **{badge['name']}** {badge['emoji']}",
                    color=RARITY_COLORS.get(badge.get("rarity", "common"), 0x9e9e9e)
                )
                embed.add_field(name="📝 Description", value=badge["description"])
                if badge.get("points_reward", 0) > 0:
                    embed.add_field(name="🏆 Récompense", value=f"+{badge['points_reward']} points")
                await member.send(embed=embed)
            except:
                pass
        else:
            await ctx.send(f"⚠️ {member.display_name} possède déjà ce badge.")
    
    @commands.command(name="removebadge")
    @commands.has_permissions(administrator=True)
    async def remove_badge(self, ctx, member: discord.Member, *, badge_name: str):
        """Retire un badge à un membre (admin)"""
        badge_id = None
        badge = None
        
        for bid, b in badges_data.items():
            if bid == badge_name.lower() or b["name"].lower() == badge_name.lower():
                badge_id = bid
                badge = b
                break
        
        if not badge:
            await ctx.send("❌ Badge introuvable.")
            return
        
        user_badges = get_user_badges(member.id)
        
        if badge_id in user_badges.get("unlocked", []):
            user_badges["unlocked"].remove(badge_id)
            if badge_id in user_badges.get("displayed", []):
                user_badges["displayed"].remove(badge_id)
            sauvegarder_badges()
            await ctx.send(f"✅ Le badge **{badge['name']}** a été retiré à {member.display_name}.")
        else:
            await ctx.send(f"⚠️ {member.display_name} ne possède pas ce badge.")


async def setup(bot):
    """Setup pour discord.py 2.0+"""
    await bot.add_cog(AchievementsSystem(bot))