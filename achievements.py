# achievements.py
# Système de Badges et Achievements
import discord
from discord.ext import commands
import json
import os
from datetime import datetime
from config import COLORS

BADGES_FILE = "data/badges.json"
USER_BADGES_FILE = "data/user_badges.json"
os.makedirs("data", exist_ok=True)

# Badges par défaut du système
DEFAULT_BADGES = {
    # === REVIEWS ===
    "first_review": {
        "id": "first_review",
        "name": "Critique Débutant",
        "description": "Laisser sa première review",
        "emoji": "📝",
        "category": "reviews",
        "rarity": "common",
        "points_reward": 50,
        "condition": {"type": "reviews_count", "value": 1}
    },
    "reviewer_bronze": {
        "id": "reviewer_bronze",
        "name": "Critique Bronze",
        "description": "Laisser 10 reviews",
        "emoji": "🥉",
        "category": "reviews",
        "rarity": "uncommon",
        "points_reward": 100,
        "condition": {"type": "reviews_count", "value": 10}
    },
    "reviewer_silver": {
        "id": "reviewer_silver",
        "name": "Critique Argent",
        "description": "Laisser 25 reviews",
        "emoji": "🥈",
        "category": "reviews",
        "rarity": "rare",
        "points_reward": 250,
        "condition": {"type": "reviews_count", "value": 25}
    },
    "reviewer_gold": {
        "id": "reviewer_gold",
        "name": "Critique Or",
        "description": "Laisser 50 reviews",
        "emoji": "🥇",
        "category": "reviews",
        "rarity": "epic",
        "points_reward": 500,
        "condition": {"type": "reviews_count", "value": 50}
    },
    "reviewer_master": {
        "id": "reviewer_master",
        "name": "Maître Critique",
        "description": "Laisser 100 reviews",
        "emoji": "👑",
        "category": "reviews",
        "rarity": "legendary",
        "points_reward": 1000,
        "condition": {"type": "reviews_count", "value": 100}
    },
    
    # === THÉORIES ===
    "first_theory": {
        "id": "first_theory",
        "name": "Théoricien Novice",
        "description": "Poster sa première théorie",
        "emoji": "💭",
        "category": "theories",
        "rarity": "common",
        "points_reward": 50,
        "condition": {"type": "theories_count", "value": 1}
    },
    "theorist_bronze": {
        "id": "theorist_bronze",
        "name": "Théoricien Bronze",
        "description": "Poster 5 théories",
        "emoji": "🔮",
        "category": "theories",
        "rarity": "uncommon",
        "points_reward": 100,
        "condition": {"type": "theories_count", "value": 5}
    },
    "theorist_silver": {
        "id": "theorist_silver",
        "name": "Théoricien Argent",
        "description": "Poster 15 théories",
        "emoji": "🌟",
        "category": "theories",
        "rarity": "rare",
        "points_reward": 250,
        "condition": {"type": "theories_count", "value": 15}
    },
    "theorist_gold": {
        "id": "theorist_gold",
        "name": "Théoricien Or",
        "description": "Poster 30 théories",
        "emoji": "✨",
        "category": "theories",
        "rarity": "epic",
        "points_reward": 500,
        "condition": {"type": "theories_count", "value": 30}
    },
    "theory_confirmed": {
        "id": "theory_confirmed",
        "name": "Visionnaire",
        "description": "Avoir une théorie confirmée",
        "emoji": "🎯",
        "category": "theories",
        "rarity": "legendary",
        "points_reward": 1000,
        "condition": {"type": "theory_confirmed", "value": 1}
    },
    "popular_theorist": {
        "id": "popular_theorist",
        "name": "Théoricien Populaire",
        "description": "Recevoir 50 votes positifs sur vos théories",
        "emoji": "🔥",
        "category": "theories",
        "rarity": "epic",
        "points_reward": 300,
        "condition": {"type": "theories_votes_received", "value": 50}
    },
    
    # === PARTICIPATION ===
    "early_bird": {
        "id": "early_bird",
        "name": "Lève-Tôt",
        "description": "Être parmi les 5 premiers à reviewer un chapitre",
        "emoji": "🐦",
        "category": "participation",
        "rarity": "uncommon",
        "points_reward": 75,
        "condition": {"type": "early_reviews", "value": 1}
    },
    "speed_reader": {
        "id": "speed_reader",
        "name": "Lecteur Rapide",
        "description": "Reviewer un chapitre dans l'heure de sa sortie",
        "emoji": "⚡",
        "category": "participation",
        "rarity": "rare",
        "points_reward": 150,
        "condition": {"type": "fast_review", "value": 1}
    },
    "dedicated_fan": {
        "id": "dedicated_fan",
        "name": "Fan Dévoué",
        "description": "Reviewer tous les chapitres d'un manga (min 10)",
        "emoji": "❤️",
        "category": "participation",
        "rarity": "epic",
        "points_reward": 400,
        "condition": {"type": "complete_manga_reviews", "value": 10}
    },
    "active_voter": {
        "id": "active_voter",
        "name": "Votant Actif",
        "description": "Voter sur 25 théories",
        "emoji": "🗳️",
        "category": "participation",
        "rarity": "uncommon",
        "points_reward": 100,
        "condition": {"type": "theories_votes_given", "value": 25}
    },
    
    # === MANGAS SPÉCIFIQUES ===
    "tougen_anki_fan": {
        "id": "tougen_anki_fan",
        "name": "Fan de Tougen Anki",
        "description": "Reviewer 10 chapitres de Tougen Anki",
        "emoji": "😈",
        "category": "manga_specific",
        "rarity": "rare",
        "points_reward": 200,
        "condition": {"type": "manga_reviews", "manga": "tougen anki", "value": 10}
    },
    "ao_no_exorcist_fan": {
        "id": "ao_no_exorcist_fan",
        "name": "Fan d'Ao No Exorcist",
        "description": "Reviewer 10 chapitres d'Ao No Exorcist",
        "emoji": "👹",
        "category": "manga_specific",
        "rarity": "rare",
        "points_reward": 200,
        "condition": {"type": "manga_reviews", "manga": "ao no exorcist", "value": 10}
    },
    "satsudou_fan": {
        "id": "satsudou_fan",
        "name": "Fan de Satsudou",
        "description": "Reviewer 10 chapitres de Satsudou",
        "emoji": "🩸",
        "category": "manga_specific",
        "rarity": "rare",
        "points_reward": 200,
        "condition": {"type": "manga_reviews", "manga": "satsudou", "value": 10}
    },
    "tokyo_underworld_fan": {
        "id": "tokyo_underworld_fan",
        "name": "Fan de Tokyo Underworld",
        "description": "Reviewer 10 chapitres de Tokyo Underworld",
        "emoji": "🗼",
        "category": "manga_specific",
        "rarity": "rare",
        "points_reward": 200,
        "condition": {"type": "manga_reviews", "manga": "tokyo underworld", "value": 10}
    },
    "catenaccio_fan": {
        "id": "catenaccio_fan",
        "name": "Fan de Catenaccio",
        "description": "Reviewer 10 chapitres de Catenaccio",
        "emoji": "⚽",
        "category": "manga_specific",
        "rarity": "rare",
        "points_reward": 200,
        "condition": {"type": "manga_reviews", "manga": "catenaccio", "value": 10}
    },
    
    # === POINTS / ÉCONOMIE ===
    "first_purchase": {
        "id": "first_purchase",
        "name": "Premier Achat",
        "description": "Effectuer son premier achat dans le shop",
        "emoji": "🛒",
        "category": "economy",
        "rarity": "common",
        "points_reward": 25,
        "condition": {"type": "purchases", "value": 1}
    },
    "big_spender": {
        "id": "big_spender",
        "name": "Grand Dépensier",
        "description": "Dépenser 1000 points au total",
        "emoji": "💸",
        "category": "economy",
        "rarity": "rare",
        "points_reward": 100,
        "condition": {"type": "total_spent", "value": 1000}
    },
    "millionaire": {
        "id": "millionaire",
        "name": "Riche",
        "description": "Atteindre 5000 points",
        "emoji": "💰",
        "category": "economy",
        "rarity": "epic",
        "points_reward": 0,
        "condition": {"type": "points_reached", "value": 5000}
    },
    
    # === INVITATIONS ===
    "recruiter": {
        "id": "recruiter",
        "name": "Recruteur",
        "description": "Inviter 5 personnes",
        "emoji": "📨",
        "category": "invites",
        "rarity": "uncommon",
        "points_reward": 150,
        "condition": {"type": "invites", "value": 5}
    },
    "ambassador": {
        "id": "ambassador",
        "name": "Ambassadeur",
        "description": "Inviter 20 personnes",
        "emoji": "🎖️",
        "category": "invites",
        "rarity": "epic",
        "points_reward": 500,
        "condition": {"type": "invites", "value": 20}
    },
    
    # === SPÉCIAUX ===
    "og_member": {
        "id": "og_member",
        "name": "Membre OG",
        "description": "Faire partie des 100 premiers membres",
        "emoji": "🏆",
        "category": "special",
        "rarity": "legendary",
        "points_reward": 500,
        "condition": {"type": "manual", "value": 0}
    },
    "event_winner": {
        "id": "event_winner",
        "name": "Champion d'Event",
        "description": "Gagner un événement communautaire",
        "emoji": "🎉",
        "category": "special",
        "rarity": "legendary",
        "points_reward": 300,
        "condition": {"type": "manual", "value": 0}
    }
}

# Couleurs par rareté
RARITY_COLORS = {
    "common": 0x9E9E9E,      # Gris
    "uncommon": 0x4CAF50,    # Vert
    "rare": 0x2196F3,        # Bleu
    "epic": 0x9C27B0,        # Violet
    "legendary": 0xFFD700    # Or
}

RARITY_NAMES = {
    "common": "Commun",
    "uncommon": "Peu commun",
    "rare": "Rare",
    "epic": "Épique",
    "legendary": "Légendaire"
}

# Données en mémoire
badges_data = {}
user_badges = {}

def charger_badges():
    """Charge les badges"""
    global badges_data, user_badges
    
    # Charger les badges custom ou utiliser les defaults
    if os.path.exists(BADGES_FILE):
        try:
            with open(BADGES_FILE, "r", encoding="utf-8") as f:
                contenu = f.read().strip()
                if contenu:
                    badges_data = json.loads(contenu)
        except Exception as e:
            print(f"❌ Erreur chargement badges: {e}")
            badges_data = DEFAULT_BADGES.copy()
    else:
        badges_data = DEFAULT_BADGES.copy()
    
    # Charger les badges utilisateurs
    if os.path.exists(USER_BADGES_FILE):
        try:
            with open(USER_BADGES_FILE, "r", encoding="utf-8") as f:
                contenu = f.read().strip()
                if contenu:
                    user_badges = json.loads(contenu)
        except Exception as e:
            print(f"❌ Erreur chargement user_badges: {e}")
            user_badges = {}
    
    print(f"✅ {len(badges_data)} badges chargés")

def sauvegarder_badges():
    """Sauvegarde les badges"""
    try:
        with open(BADGES_FILE, "w", encoding="utf-8") as f:
            json.dump(badges_data, f, ensure_ascii=False, indent=4)
        with open(USER_BADGES_FILE, "w", encoding="utf-8") as f:
            json.dump(user_badges, f, ensure_ascii=False, indent=4)
        print("✅ Badges sauvegardés")
    except Exception as e:
        print(f"❌ Erreur sauvegarde badges: {e}")

def get_user_badges(user_id):
    """Récupère les badges d'un utilisateur"""
    user_id_str = str(user_id)
    if user_id_str not in user_badges:
        user_badges[user_id_str] = {
            "unlocked": [],
            "displayed": [],
            "stats": {
                "reviews_count": 0,
                "theories_count": 0,
                "theories_votes_given": 0,
                "theories_votes_received": 0,
                "early_reviews": 0,
                "fast_reviews": 0,
                "purchases": 0,
                "total_spent": 0,
                "manga_reviews": {}
            }
        }
    return user_badges[user_id_str]

def unlock_badge(user_id, badge_id):
    """Débloque un badge pour un utilisateur"""
    if badge_id not in badges_data:
        return None
    
    user = get_user_badges(user_id)
    
    if badge_id in user["unlocked"]:
        return None  # Déjà débloqué
    
    user["unlocked"].append(badge_id)
    sauvegarder_badges()
    
    return badges_data[badge_id]

def check_badges(user_id, user_stats):
    """Vérifie et débloque les badges éligibles"""
    unlocked = []
    user = get_user_badges(user_id)
    
    for badge_id, badge in badges_data.items():
        if badge_id in user["unlocked"]:
            continue
        
        condition = badge.get("condition", {})
        ctype = condition.get("type")
        value = condition.get("value", 0)
        
        should_unlock = False
        
        if ctype == "reviews_count":
            should_unlock = user_stats.get("reviews_count", 0) >= value
        elif ctype == "theories_count":
            should_unlock = user_stats.get("theories_count", 0) >= value
        elif ctype == "theories_votes_given":
            should_unlock = user_stats.get("theories_votes_given", 0) >= value
        elif ctype == "theories_votes_received":
            should_unlock = user_stats.get("theories_votes_received", 0) >= value
        elif ctype == "purchases":
            should_unlock = user["stats"].get("purchases", 0) >= value
        elif ctype == "total_spent":
            should_unlock = user["stats"].get("total_spent", 0) >= value
        elif ctype == "points_reached":
            should_unlock = user_stats.get("points", 0) >= value
        elif ctype == "invites":
            should_unlock = user_stats.get("real", 0) >= value
        elif ctype == "manga_reviews":
            manga = condition.get("manga", "").lower()
            manga_count = user["stats"].get("manga_reviews", {}).get(manga, 0)
            should_unlock = manga_count >= value
        elif ctype == "early_reviews":
            should_unlock = user["stats"].get("early_reviews", 0) >= value
        
        if should_unlock:
            unlock_badge(user_id, badge_id)
            unlocked.append(badge)
    
    return unlocked


class AchievementSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        charger_badges()
    
    @commands.command(name="badges")
    async def show_badges(self, ctx, member: discord.Member = None):
        """Affiche les badges d'un membre"""
        member = member or ctx.author
        user = get_user_badges(member.id)
        
        unlocked_badges = [badges_data[bid] for bid in user["unlocked"] if bid in badges_data]
        
        embed = discord.Embed(
            title=f"🏆 Badges de {member.display_name}",
            description=f"**{len(unlocked_badges)}** / **{len(badges_data)}** badges débloqués",
            color=discord.Color.gold(),
            timestamp=datetime.now()
        )
        
        if not unlocked_badges:
            embed.add_field(
                name="Aucun badge",
                value="Commencez à participer pour débloquer des badges !",
                inline=False
            )
        else:
            # Grouper par catégorie
            by_category = {}
            for badge in unlocked_badges:
                cat = badge.get("category", "other")
                if cat not in by_category:
                    by_category[cat] = []
                by_category[cat].append(badge)
            
            category_names = {
                "reviews": "📝 Reviews",
                "theories": "💭 Théories",
                "participation": "🎯 Participation",
                "manga_specific": "📚 Mangas",
                "economy": "💰 Économie",
                "invites": "📨 Invitations",
                "special": "⭐ Spéciaux"
            }
            
            for cat, cat_badges in by_category.items():
                badges_str = " ".join([f"{b['emoji']}" for b in cat_badges])
                embed.add_field(
                    name=category_names.get(cat, cat.capitalize()),
                    value=badges_str,
                    inline=True
                )
        
        # Badges affichés
        if user.get("displayed"):
            displayed = [badges_data[bid]["emoji"] for bid in user["displayed"] if bid in badges_data]
            embed.add_field(
                name="🎖️ Badges Affichés",
                value=" ".join(displayed) if displayed else "Aucun",
                inline=False
            )
        
        embed.set_thumbnail(url=member.avatar.url if member.avatar else None)
        embed.set_footer(text="Utilisez !badge_info <nom> pour plus de détails")
        
        await ctx.send(embed=embed)
    
    @commands.command(name="all_badges")
    async def all_badges(self, ctx):
        """Liste tous les badges disponibles"""
        member = ctx.author
        user = get_user_badges(member.id)
        
        # Grouper par rareté
        by_rarity = {}
        for badge_id, badge in badges_data.items():
            rarity = badge.get("rarity", "common")
            if rarity not in by_rarity:
                by_rarity[rarity] = []
            
            is_unlocked = badge_id in user["unlocked"]
            by_rarity[rarity].append((badge, is_unlocked))
        
        embed = discord.Embed(
            title="🏆 Tous les Badges Disponibles",
            description=f"Vous avez débloqué **{len(user['unlocked'])}** / **{len(badges_data)}** badges",
            color=discord.Color.gold(),
            timestamp=datetime.now()
        )
        
        rarity_order = ["legendary", "epic", "rare", "uncommon", "common"]
        
        for rarity in rarity_order:
            if rarity not in by_rarity:
                continue
            
            badges_list = by_rarity[rarity]
            rarity_name = RARITY_NAMES.get(rarity, rarity)
            
            badges_str = ""
            for badge, unlocked in badges_list:
                status = badge["emoji"] if unlocked else "🔒"
                badges_str += f"{status} "
            
            unlocked_count = sum(1 for _, u in badges_list if u)
            
            embed.add_field(
                name=f"{rarity_name} ({unlocked_count}/{len(badges_list)})",
                value=badges_str.strip(),
                inline=False
            )
        
        embed.set_footer(text="Utilisez !badge_info <nom> pour voir les conditions")
        await ctx.send(embed=embed)
    
    @commands.command(name="badge_info")
    async def badge_info(self, ctx, *, badge_name: str):
        """Affiche les détails d'un badge"""
        # Chercher le badge
        found_badge = None
        found_id = None
        
        for bid, badge in badges_data.items():
            if badge["name"].lower() == badge_name.lower() or bid.lower() == badge_name.lower():
                found_badge = badge
                found_id = bid
                break
        
        if not found_badge:
            await ctx.send(f"❌ Badge '{badge_name}' introuvable.")
            return
        
        user = get_user_badges(ctx.author.id)
        is_unlocked = found_id in user["unlocked"]
        
        rarity = found_badge.get("rarity", "common")
        color = RARITY_COLORS.get(rarity, 0x9E9E9E)
        
        embed = discord.Embed(
            title=f"{found_badge['emoji']} {found_badge['name']}",
            description=found_badge["description"],
            color=color,
            timestamp=datetime.now()
        )
        
        embed.add_field(name="🎖️ Rareté", value=RARITY_NAMES.get(rarity, rarity), inline=True)
        embed.add_field(name="🏆 Récompense", value=f"+{found_badge.get('points_reward', 0)} pts", inline=True)
        embed.add_field(name="📊 Statut", value="✅ Débloqué" if is_unlocked else "🔒 Verrouillé", inline=True)
        
        # Condition
        condition = found_badge.get("condition", {})
        ctype = condition.get("type", "manual")
        value = condition.get("value", 0)
        
        condition_text = {
            "reviews_count": f"Laisser {value} review(s)",
            "theories_count": f"Poster {value} théorie(s)",
            "theories_votes_given": f"Voter sur {value} théorie(s)",
            "theories_votes_received": f"Recevoir {value} vote(s) positif(s)",
            "purchases": f"Effectuer {value} achat(s)",
            "total_spent": f"Dépenser {value} points",
            "points_reached": f"Atteindre {value} points",
            "invites": f"Inviter {value} personne(s)",
            "manga_reviews": f"Reviewer {value} chapitres de {condition.get('manga', 'ce manga')}",
            "early_reviews": f"Être parmi les premiers à reviewer {value} fois",
            "manual": "Attribution manuelle par le staff"
        }.get(ctype, "Condition spéciale")
        
        embed.add_field(name="📋 Condition", value=condition_text, inline=False)
        
        await ctx.send(embed=embed)
    
    @commands.command(name="display_badge")
    async def display_badge(self, ctx, *, badge_name: str):
        """Ajoute un badge à votre affichage (max 3)"""
        user = get_user_badges(ctx.author.id)
        
        # Chercher le badge
        found_id = None
        for bid, badge in badges_data.items():
            if badge["name"].lower() == badge_name.lower() or bid.lower() == badge_name.lower():
                found_id = bid
                break
        
        if not found_id:
            await ctx.send(f"❌ Badge '{badge_name}' introuvable.")
            return
        
        if found_id not in user["unlocked"]:
            await ctx.send("❌ Vous n'avez pas débloqué ce badge.")
            return
        
        if found_id in user.get("displayed", []):
            await ctx.send("❌ Ce badge est déjà affiché.")
            return
        
        if "displayed" not in user:
            user["displayed"] = []
        
        if len(user["displayed"]) >= 3:
            await ctx.send("❌ Vous ne pouvez afficher que 3 badges maximum. Utilisez `!remove_badge` d'abord.")
            return
        
        user["displayed"].append(found_id)
        sauvegarder_badges()
        
        badge = badges_data[found_id]
        await ctx.send(f"✅ Badge **{badge['emoji']} {badge['name']}** ajouté à votre affichage !")
    
    @commands.command(name="remove_badge")
    async def remove_badge(self, ctx, *, badge_name: str):
        """Retire un badge de votre affichage"""
        user = get_user_badges(ctx.author.id)
        
        # Chercher le badge
        found_id = None
        for bid, badge in badges_data.items():
            if badge["name"].lower() == badge_name.lower() or bid.lower() == badge_name.lower():
                found_id = bid
                break
        
        if not found_id:
            await ctx.send(f"❌ Badge '{badge_name}' introuvable.")
            return
        
        if found_id not in user.get("displayed", []):
            await ctx.send("❌ Ce badge n'est pas dans votre affichage.")
            return
        
        user["displayed"].remove(found_id)
        sauvegarder_badges()
        
        badge = badges_data[found_id]
        await ctx.send(f"✅ Badge **{badge['emoji']} {badge['name']}** retiré de votre affichage.")
    
    @commands.command(name="give_badge")
    @commands.has_any_role(1326417422663680090, 1330147432847114321)
    async def give_badge(self, ctx, member: discord.Member, *, badge_name: str):
        """(Admin) Donne un badge à un membre"""
        # Chercher le badge
        found_id = None
        for bid, badge in badges_data.items():
            if badge["name"].lower() == badge_name.lower() or bid.lower() == badge_name.lower():
                found_id = bid
                break
        
        if not found_id:
            await ctx.send(f"❌ Badge '{badge_name}' introuvable.")
            return
        
        result = unlock_badge(member.id, found_id)
        
        if result is None:
            await ctx.send(f"❌ {member.mention} possède déjà ce badge.")
            return
        
        badge = badges_data[found_id]
        
        embed = discord.Embed(
            title="🎉 Badge Attribué !",
            description=f"{member.mention} a reçu le badge **{badge['emoji']} {badge['name']}** !",
            color=RARITY_COLORS.get(badge.get("rarity", "common"), 0x9E9E9E)
        )
        embed.add_field(name="🏆 Récompense", value=f"+{badge.get('points_reward', 0)} pts", inline=True)
        embed.set_thumbnail(url=member.avatar.url if member.avatar else None)
        
        await ctx.send(embed=embed)
    
    @commands.command(name="leaderboard_badges")
    async def leaderboard_badges(self, ctx):
        """Affiche le classement des badges"""
        # Trier par nombre de badges
        sorted_users = sorted(
            user_badges.items(),
            key=lambda x: len(x[1].get("unlocked", [])),
            reverse=True
        )[:10]
        
        embed = discord.Embed(
            title="🏆 Classement des Badges",
            description="Top 10 des collectionneurs de badges",
            color=discord.Color.gold(),
            timestamp=datetime.now()
        )
        
        medals = ["🥇", "🥈", "🥉"]
        
        for i, (user_id, data) in enumerate(sorted_users, 1):
            member = ctx.guild.get_member(int(user_id))
            if not member:
                continue
            
            badge_count = len(data.get("unlocked", []))
            displayed = [badges_data[bid]["emoji"] for bid in data.get("displayed", [])[:3] if bid in badges_data]
            
            medal = medals[i-1] if i <= 3 else f"**{i}.**"
            badges_str = " ".join(displayed) if displayed else ""
            
            embed.add_field(
                name=f"{medal} {member.display_name}",
                value=f"**{badge_count}** badges {badges_str}",
                inline=False
            )
        
        await ctx.send(embed=embed)


async def setup(bot):
    """Setup pour discord.py 2.0+"""
    await bot.add_cog(AchievementSystem(bot))
