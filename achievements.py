import discord
from config import ADMIN_ROLES, DATA_FILES, RARITY_COLORS
from discord.ext import commands
import json
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
from utils import load_json, save_json

# ═══════════════════════════════════════════════════════════════════════════════
# FICHIERS DE DONNÉES (depuis config.py)
# ═══════════════════════════════════════════════════════════════════════════════

BADGES_FILE = DATA_FILES["badges"]
BADGES_CONFIG_FILE = DATA_FILES["badges_config"]

# ═══════════════════════════════════════════════════════════════════════════════
# DÉFINITION DES BADGES
# ═══════════════════════════════════════════════════════════════════════════════

BADGES_DATA = {
    # ─────────────────────────────────────────────────────────────────────────
    # BADGES DE CONTRIBUTION
    # ─────────────────────────────────────────────────────────────────────────
    "first_task": {
        "name": "Première Contribution",
        "description": "A complété sa première tâche pour l'équipe",
        "emoji": "🌟",
        "category": "contribution",
        "points_reward": 50,
        "rarity": "common",
        "secret": False
    },
    "task_master": {
        "name": "Maître des Tâches",
        "description": "A complété 50 tâches au total",
        "emoji": "⚔️",
        "category": "contribution",
        "points_reward": 500,
        "rarity": "epic",
        "secret": False
    },
    "speed_demon": {
        "name": "Speed Demon",
        "description": "A complété 5 tâches en une journée",
        "emoji": "⚡",
        "category": "contribution",
        "points_reward": 200,
        "rarity": "rare",
        "secret": False
    },
    "perfectionist": {
        "name": "Perfectionniste",
        "description": "10 tâches complétées sans aucune correction demandée",
        "emoji": "💎",
        "category": "contribution",
        "points_reward": 300,
        "rarity": "epic",
        "secret": False
    },
    
    # ─────────────────────────────────────────────────────────────────────────
    # BADGES D'ANCIENNETÉ
    # ─────────────────────────────────────────────────────────────────────────
    "newcomer": {
        "name": "Nouveau Venu",
        "description": "A rejoint l'équipe LanorTrad",
        "emoji": "👋",
        "category": "anciennete",
        "points_reward": 10,
        "rarity": "common",
        "secret": False
    },
    "veteran": {
        "name": "Vétéran",
        "description": "Membre depuis plus de 6 mois",
        "emoji": "🎖️",
        "category": "anciennete",
        "points_reward": 200,
        "rarity": "rare",
        "secret": False
    },
    "founder": {
        "name": "Membre Fondateur",
        "description": "Parmi les premiers membres de l'équipe",
        "emoji": "👑",
        "category": "anciennete",
        "points_reward": 1000,
        "rarity": "legendary",
        "secret": False
    },
    "anniversary": {
        "name": "Anniversaire",
        "description": "1 an dans l'équipe LanorTrad",
        "emoji": "🎂",
        "category": "anciennete",
        "points_reward": 500,
        "rarity": "epic",
        "secret": False
    },
    
    # ─────────────────────────────────────────────────────────────────────────
    # BADGES DE SPÉCIALISATION
    # ─────────────────────────────────────────────────────────────────────────
    "translator_pro": {
        "name": "Traducteur Pro",
        "description": "A traduit 20 chapitres",
        "emoji": "📝",
        "category": "specialisation",
        "points_reward": 400,
        "rarity": "epic",
        "secret": False
    },
    "cleaner_expert": {
        "name": "Cleaner Expert",
        "description": "A nettoyé 30 chapitres",
        "emoji": "🧹",
        "category": "specialisation",
        "points_reward": 400,
        "rarity": "epic",
        "secret": False
    },
    "editor_master": {
        "name": "Éditeur Maître",
        "description": "A édité 25 chapitres",
        "emoji": "✒️",
        "category": "specialisation",
        "points_reward": 400,
        "rarity": "epic",
        "secret": False
    },
    "checker_hawk": {
        "name": "Œil de Lynx",
        "description": "A vérifié 40 chapitres",
        "emoji": "🔍",
        "category": "specialisation",
        "points_reward": 400,
        "rarity": "epic",
        "secret": False
    },
    "polyvalent": {
        "name": "Polyvalent",
        "description": "A contribué dans au moins 3 rôles différents",
        "emoji": "🎭",
        "category": "specialisation",
        "points_reward": 300,
        "rarity": "rare",
        "secret": False
    },
    
    # ─────────────────────────────────────────────────────────────────────────
    # BADGES DE MANGA SPÉCIFIQUES
    # ─────────────────────────────────────────────────────────────────────────
    "tougen_fan": {
        "name": "Fan de Tougen Anki",
        "description": "A contribué à 10 chapitres de Tougen Anki",
        "emoji": "👹",
        "category": "manga",
        "points_reward": 150,
        "rarity": "uncommon",
        "secret": False
    },
    "ao_devotee": {
        "name": "Dévoué d'Ao no Exorcist",
        "description": "A contribué à 10 chapitres d'Ao no Exorcist",
        "emoji": "🔵",
        "category": "manga",
        "points_reward": 150,
        "rarity": "uncommon",
        "secret": False
    },
    "tokyo_expert": {
        "name": "Expert Tokyo Underworld",
        "description": "A contribué à 10 chapitres de Tokyo Underworld",
        "emoji": "🏙️",
        "category": "manga",
        "points_reward": 150,
        "rarity": "uncommon",
        "secret": False
    },
    "satsudou_master": {
        "name": "Maître Satsudou",
        "description": "A contribué à 10 chapitres de Satsudou",
        "emoji": "⚔️",
        "category": "manga",
        "points_reward": 150,
        "rarity": "uncommon",
        "secret": False
    },
    "catenaccio_champion": {
        "name": "Champion Catenaccio",
        "description": "A contribué à 10 chapitres de Catenaccio",
        "emoji": "⚽",
        "category": "manga",
        "points_reward": 150,
        "rarity": "uncommon",
        "secret": False
    },
    
    # ─────────────────────────────────────────────────────────────────────────
    # BADGES SOCIAUX
    # ─────────────────────────────────────────────────────────────────────────
    "helper": {
        "name": "Entraide",
        "description": "A aidé 10 autres membres",
        "emoji": "🤝",
        "category": "social",
        "points_reward": 100,
        "rarity": "uncommon",
        "secret": False
    },
    "mentor": {
        "name": "Mentor",
        "description": "A formé 3 nouveaux membres",
        "emoji": "🎓",
        "category": "social",
        "points_reward": 250,
        "rarity": "rare",
        "secret": False
    },
    "community_star": {
        "name": "Star de la Communauté",
        "description": "500 messages dans le serveur",
        "emoji": "⭐",
        "category": "social",
        "points_reward": 100,
        "rarity": "uncommon",
        "secret": False
    },
    "event_participant": {
        "name": "Participant",
        "description": "A participé à un événement communautaire",
        "emoji": "🎉",
        "category": "social",
        "points_reward": 50,
        "rarity": "common",
        "secret": False
    },
    
    # ─────────────────────────────────────────────────────────────────────────
    # BADGES SHOP & ÉCONOMIE
    # ─────────────────────────────────────────────────────────────────────────
    "first_purchase": {
        "name": "Premier Achat",
        "description": "A effectué son premier achat dans la boutique",
        "emoji": "🛒",
        "category": "economie",
        "points_reward": 25,
        "rarity": "common",
        "secret": False
    },
    "big_spender": {
        "name": "Gros Dépensier",
        "description": "A dépensé plus de 5000 points au total",
        "emoji": "💰",
        "category": "economie",
        "points_reward": 200,
        "rarity": "rare",
        "secret": False
    },
    "lottery_winner": {
        "name": "Chanceux",
        "description": "A gagné la loterie",
        "emoji": "🎰",
        "category": "economie",
        "points_reward": 100,
        "rarity": "rare",
        "secret": False
    },
    "collector": {
        "name": "Collectionneur",
        "description": "Possède 10 badges différents",
        "emoji": "🏆",
        "category": "economie",
        "points_reward": 150,
        "rarity": "uncommon",
        "secret": False
    },
    
    # ─────────────────────────────────────────────────────────────────────────
    # BADGES SECRETS
    # ─────────────────────────────────────────────────────────────────────────
    "night_owl": {
        "name": "Oiseau de Nuit",
        "description": "A complété une tâche entre 2h et 5h du matin",
        "emoji": "🦉",
        "category": "secret",
        "points_reward": 100,
        "rarity": "rare",
        "secret": True
    },
    "early_bird": {
        "name": "Lève-Tôt",
        "description": "A complété une tâche avant 7h du matin",
        "emoji": "🐦",
        "category": "secret",
        "points_reward": 100,
        "rarity": "rare",
        "secret": True
    },
    "marathon": {
        "name": "Marathon",
        "description": "10 tâches complétées en 48h",
        "emoji": "🏃",
        "category": "secret",
        "points_reward": 300,
        "rarity": "epic",
        "secret": True
    },
    "lucky_seven": {
        "name": "Lucky Seven",
        "description": "7 tâches complétées un 7 du mois",
        "emoji": "🍀",
        "category": "secret",
        "points_reward": 77,
        "rarity": "rare",
        "secret": True
    },
    "dedication": {
        "name": "Dévouement",
        "description": "A contribué chaque semaine pendant 2 mois consécutifs",
        "emoji": "💪",
        "category": "secret",
        "points_reward": 500,
        "rarity": "legendary",
        "secret": True
    }
}

# Couleurs par rareté
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

# ═══════════════════════════════════════════════════════════════════════════════
# FONCTIONS UTILITAIRES
# ═══════════════════════════════════════════════════════════════════════════════

def ensure_data_dir():
    """S'assure que le dossier data existe"""
    os.makedirs("data", exist_ok=True)

def load_badges_data() -> Dict:
    """Charge les données des badges utilisateurs"""
    ensure_data_dir()
    if os.path.exists(BADGES_FILE):
        try:
            with open(BADGES_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}
    return {}

def save_badges_data(data: Dict):
    """Sauvegarde les données des badges"""
    ensure_data_dir()
    with open(BADGES_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def get_user_badges(user_id: int) -> Dict:
    """Récupère les badges d'un utilisateur"""
    data = load_badges_data()
    user_id_str = str(user_id)
    
    if user_id_str not in data:
        data[user_id_str] = {
            "badges": [],
            "badge_dates": {},
            "stats": {
                "tasks_completed": 0,
                "tasks_today": 0,
                "last_task_date": None,
                "chapters_translated": 0,
                "chapters_cleaned": 0,
                "chapters_edited": 0,
                "chapters_checked": 0,
                "roles_contributed": [],
                "manga_contributions": {},
                "messages_count": 0,
                "members_helped": 0,
                "members_mentored": 0,
                "events_participated": 0,
                "consecutive_weeks": 0,
                "last_contribution_week": None,
                "join_date": None
            }
        }
        save_badges_data(data)
    
    return data[user_id_str]

def has_badge(user_id: int, badge_id: str) -> bool:
    """Vérifie si un utilisateur a un badge"""
    user_data = get_user_badges(user_id)
    return badge_id in user_data.get("badges", [])

def unlock_badge(user_id: int, badge_id: str, bot=None) -> Optional[Dict]:
    """
    Débloque un badge pour un utilisateur.
    Retourne les infos du badge si nouveau, None si déjà possédé ou invalide.
    """
    if badge_id not in BADGES_DATA:
        return None
    
    if has_badge(user_id, badge_id):
        return None
    
    data = load_badges_data()
    user_id_str = str(user_id)
    
    if user_id_str not in data:
        get_user_badges(user_id)
        data = load_badges_data()
    
    # Ajouter le badge
    data[user_id_str]["badges"].append(badge_id)
    data[user_id_str]["badge_dates"][badge_id] = datetime.now().isoformat()
    
    save_badges_data(data)
    
    badge_info = BADGES_DATA[badge_id]
    
    # Donner les points de récompense
    try:
        from community import add_points, sauvegarder_donnees
        add_points(user_id, badge_info["points_reward"])
        sauvegarder_donnees()
    except ImportError:
        pass
    
    # Vérifier le badge "collector" (10 badges)
    if len(data[user_id_str]["badges"]) >= 10 and not has_badge(user_id, "collector"):
        unlock_badge(user_id, "collector", bot)
    
    return badge_info

def update_user_stat(user_id: int, stat_name: str, value: Any = None, increment: int = 1):
    """Met à jour une statistique utilisateur"""
    data = load_badges_data()
    user_id_str = str(user_id)
    
    if user_id_str not in data:
        get_user_badges(user_id)
        data = load_badges_data()
    
    stats = data[user_id_str].get("stats", {})
    
    if value is not None:
        stats[stat_name] = value
    else:
        stats[stat_name] = stats.get(stat_name, 0) + increment
    
    data[user_id_str]["stats"] = stats
    save_badges_data(data)
    
    return stats[stat_name]

def get_badge_info(badge_id: str) -> Optional[Dict]:
    """Récupère les infos d'un badge"""
    return BADGES_DATA.get(badge_id)

def get_all_badges() -> Dict:
    """Retourne tous les badges disponibles"""
    return BADGES_DATA

def get_badges_by_category(category: str) -> Dict:
    """Récupère les badges d'une catégorie"""
    return {k: v for k, v in BADGES_DATA.items() if v.get("category") == category}

def get_visible_badges() -> Dict:
    """Récupère les badges non secrets"""
    return {k: v for k, v in BADGES_DATA.items() if not v.get("secret", False)}

def count_user_badges(user_id: int) -> int:
    """Compte le nombre de badges d'un utilisateur"""
    user_data = get_user_badges(user_id)
    return len(user_data.get("badges", []))

def get_badge_progress(user_id: int, badge_id: str) -> Optional[Dict]:
    """Calcule la progression vers un badge"""
    if badge_id not in BADGES_DATA:
        return None
    
    user_data = get_user_badges(user_id)
    stats = user_data.get("stats", {})
    
    progress_mapping = {
        "task_master": ("tasks_completed", 50),
        "translator_pro": ("chapters_translated", 20),
        "cleaner_expert": ("chapters_cleaned", 30),
        "editor_master": ("chapters_edited", 25),
        "checker_hawk": ("chapters_checked", 40),
        "community_star": ("messages_count", 500),
        "helper": ("members_helped", 10),
        "mentor": ("members_mentored", 3),
        "collector": (lambda: len(user_data.get("badges", [])), 10),
    }
    
    if badge_id in progress_mapping:
        mapping = progress_mapping[badge_id]
        if callable(mapping[0]):
            current = mapping[0]()
        else:
            current = stats.get(mapping[0], 0)
        target = mapping[1]
        return {
            "current": current,
            "target": target,
            "percentage": min(100, int((current / target) * 100))
        }
    
    return None

# ═══════════════════════════════════════════════════════════════════════════════
# COG DISCORD
# ═══════════════════════════════════════════════════════════════════════════════

class Achievements(commands.Cog):
    """Système de badges et achievements"""
    
    def __init__(self, bot):
        self.bot = bot
    
    # ─────────────────────────────────────────────────────────────────────────
    # COMMANDES UTILISATEUR
    # ─────────────────────────────────────────────────────────────────────────
    
    @commands.command(name="badges", aliases=["achievements", "mes_badges"])
    async def show_badges(self, ctx, member: Optional[discord.Member] = None):
        """Affiche les badges d'un membre"""
        target = member or ctx.author
        user_data = get_user_badges(target.id)
        user_badges = user_data.get("badges", [])
        
        if not user_badges:
            if target == ctx.author:
                embed = discord.Embed(
                    title="🏅 Mes Badges",
                    description="Tu n'as pas encore de badges.\nParticipe aux activités pour en débloquer !",
                    color=0x9e9e9e
                )
            else:
                embed = discord.Embed(
                    title=f"🏅 Badges de {target.display_name}",
                    description="Ce membre n'a pas encore de badges.",
                    color=0x9e9e9e
                )
            await ctx.send(embed=embed)
            return
        
        # Trier par rareté (legendary -> common)
        rarity_order = ["legendary", "epic", "rare", "uncommon", "common"]
        sorted_badges = sorted(
            user_badges,
            key=lambda x: rarity_order.index(BADGES_DATA.get(x, {}).get("rarity", "common"))
        )
        
        # Créer l'embed
        if target == ctx.author:
            embed = discord.Embed(
                title="🏅 Mes Badges",
                description=f"**{len(user_badges)}** badges débloqués",
                color=0xffd700
            )
        else:
            embed = discord.Embed(
                title=f"🏅 Badges de {target.display_name}",
                description=f"**{len(user_badges)}** badges débloqués",
                color=0xffd700
            )
        
        # Grouper par rareté
        by_rarity = {}
        for badge_id in sorted_badges:
            badge = BADGES_DATA.get(badge_id, {})
            rarity = badge.get("rarity", "common")
            if rarity not in by_rarity:
                by_rarity[rarity] = []
            by_rarity[rarity].append(badge)
        
        for rarity in rarity_order:
            if rarity in by_rarity:
                badges_text = " ".join([f"{b['emoji']}" for b in by_rarity[rarity]])
                embed.add_field(
                    name=f"{RARITY_NAMES[rarity]} ({len(by_rarity[rarity])})",
                    value=badges_text,
                    inline=False
                )
        
        embed.set_thumbnail(url=target.display_avatar.url)
        await ctx.send(embed=embed)
    
    @commands.command(name="badge_info", aliases=["badgeinfo"])
    async def badge_info(self, ctx, *, badge_name: str):
        """Affiche les détails d'un badge"""
        # Recherche par nom ou ID
        badge_id = None
        badge_data = None
        
        for bid, bdata in BADGES_DATA.items():
            if bid.lower() == badge_name.lower() or bdata["name"].lower() == badge_name.lower():
                badge_id = bid
                badge_data = bdata
                break
        
        if not badge_data:
            await ctx.send("❌ Badge non trouvé. Utilise `!all_badges` pour voir la liste.")
            return
        
        # Badge secret non débloqué
        if badge_data.get("secret") and not has_badge(ctx.author.id, badge_id):
            embed = discord.Embed(
                title="🔒 Badge Secret",
                description="Ce badge est secret ! Débloque-le pour en savoir plus.",
                color=0x2f3136
            )
            await ctx.send(embed=embed)
            return
        
        rarity = badge_data.get("rarity", "common")
        color = RARITY_COLORS.get(rarity, 0x9e9e9e)
        
        embed = discord.Embed(
            title=f"{badge_data['emoji']} {badge_data['name']}",
            description=badge_data["description"],
            color=color
        )
        
        embed.add_field(name="Rareté", value=RARITY_NAMES[rarity], inline=True)
        embed.add_field(name="Récompense", value=f"{badge_data['points_reward']} points", inline=True)
        embed.add_field(name="Catégorie", value=badge_data["category"].title(), inline=True)
        
        # Progression si applicable
        progress = get_badge_progress(ctx.author.id, badge_id)
        if progress and not has_badge(ctx.author.id, badge_id):
            embed.add_field(
                name="Ta Progression",
                value=f"{'█' * (progress['percentage'] // 10)}{'░' * (10 - progress['percentage'] // 10)} {progress['percentage']}%\n{progress['current']}/{progress['target']}",
                inline=False
            )
        
        # Statut
        if has_badge(ctx.author.id, badge_id):
            user_data = get_user_badges(ctx.author.id)
            date_str = user_data.get("badge_dates", {}).get(badge_id, "")
            if date_str:
                try:
                    date = datetime.fromisoformat(date_str)
                    embed.add_field(name="Statut", value=f"✅ Débloqué le {date.strftime('%d/%m/%Y')}", inline=False)
                except:
                    embed.add_field(name="Statut", value="✅ Débloqué", inline=False)
            else:
                embed.add_field(name="Statut", value="✅ Débloqué", inline=False)
        else:
            embed.add_field(name="Statut", value="🔒 Non débloqué", inline=False)
        
        await ctx.send(embed=embed)
    
    @commands.command(name="all_badges", aliases=["listbadges", "badges_list"])
    async def all_badges(self, ctx, category: Optional[str] = None):
        """
        Affiche tous les badges disponibles
        Catégories: contribution, anciennete, specialisation, manga, social, economie
        """
        user_badges = get_user_badges(ctx.author.id).get("badges", [])
        
        if category:
            badges = get_badges_by_category(category.lower())
            if not badges:
                await ctx.send(f"❌ Catégorie inconnue. Catégories disponibles: contribution, anciennete, specialisation, manga, social, economie")
                return
            title = f"🏅 Badges - {category.title()}"
        else:
            badges = get_visible_badges()
            title = "🏅 Tous les Badges"
        
        embed = discord.Embed(title=title, color=0xffd700)
        
        # Grouper par catégorie si pas de filtre
        if not category:
            categories = {}
            for bid, bdata in badges.items():
                cat = bdata.get("category", "autre")
                if cat not in categories:
                    categories[cat] = []
                status = "✅" if bid in user_badges else "🔒"
                categories[cat].append(f"{status} {bdata['emoji']} **{bdata['name']}**")
            
            for cat_name, badge_list in categories.items():
                embed.add_field(
                    name=cat_name.title(),
                    value="\n".join(badge_list[:10]) + (f"\n*+{len(badge_list)-10} autres...*" if len(badge_list) > 10 else ""),
                    inline=True
                )
        else:
            lines = []
            for bid, bdata in badges.items():
                status = "✅" if bid in user_badges else "🔒"
                rarity_emoji = {"common": "⬜", "uncommon": "🟩", "rare": "🟦", "epic": "🟪", "legendary": "🟨"}
                lines.append(f"{status} {bdata['emoji']} **{bdata['name']}** {rarity_emoji.get(bdata['rarity'], '')}")
            embed.description = "\n".join(lines)
        
        unlocked = len([b for b in badges if b in user_badges])
        embed.set_footer(text=f"Tu as débloqué {unlocked}/{len(badges)} badges")
        
        await ctx.send(embed=embed)
    
    @commands.command(name="badge_stats", aliases=["mystats"])
    async def badge_stats(self, ctx):
        """Affiche tes statistiques de progression"""
        user_data = get_user_badges(ctx.author.id)
        stats = user_data.get("stats", {})
        badges = user_data.get("badges", [])
        
        embed = discord.Embed(
            title=f"📊 Statistiques de {ctx.author.display_name}",
            color=0x3498db
        )
        
        # Stats générales
        embed.add_field(
            name="🏅 Badges",
            value=f"**{len(badges)}** débloqués",
            inline=True
        )
        embed.add_field(
            name="📝 Tâches",
            value=f"**{stats.get('tasks_completed', 0)}** complétées",
            inline=True
        )
        embed.add_field(
            name="💬 Messages",
            value=f"**{stats.get('messages_count', 0)}**",
            inline=True
        )
        
        # Stats de spécialisation
        spec_text = []
        if stats.get("chapters_translated", 0) > 0:
            spec_text.append(f"📝 Traduction: **{stats['chapters_translated']}**")
        if stats.get("chapters_cleaned", 0) > 0:
            spec_text.append(f"🧹 Cleaning: **{stats['chapters_cleaned']}**")
        if stats.get("chapters_edited", 0) > 0:
            spec_text.append(f"✒️ Édition: **{stats['chapters_edited']}**")
        if stats.get("chapters_checked", 0) > 0:
            spec_text.append(f"🔍 Vérification: **{stats['chapters_checked']}**")
        
        if spec_text:
            embed.add_field(
                name="📚 Chapitres par rôle",
                value="\n".join(spec_text),
                inline=False
            )
        
        # Prochain badge le plus proche
        closest_badge = None
        closest_progress = 0
        
        for badge_id in BADGES_DATA:
            if badge_id not in badges:
                progress = get_badge_progress(ctx.author.id, badge_id)
                if progress and progress["percentage"] > closest_progress and progress["percentage"] < 100:
                    closest_progress = progress["percentage"]
                    closest_badge = badge_id
        
        if closest_badge:
            badge = BADGES_DATA[closest_badge]
            progress = get_badge_progress(ctx.author.id, closest_badge)
            embed.add_field(
                name="🎯 Prochain badge",
                value=f"{badge['emoji']} **{badge['name']}**\n{progress['current']}/{progress['target']} ({progress['percentage']}%)",
                inline=False
            )
        
        embed.set_thumbnail(url=ctx.author.display_avatar.url)
        await ctx.send(embed=embed)
    
    @commands.command(name="leaderboard_badges", aliases=["top_badges"])
    async def leaderboard_badges(self, ctx):
        """Affiche le classement des badges"""
        data = load_badges_data()
        
        if not data:
            await ctx.send("Aucune donnée de badges pour le moment.")
            return
        
        # Calculer les scores (nombre de badges * rareté)
        scores = []
        rarity_points = {"common": 1, "uncommon": 2, "rare": 3, "epic": 5, "legendary": 10}
        
        for user_id, user_data in data.items():
            badges = user_data.get("badges", [])
            score = sum(rarity_points.get(BADGES_DATA.get(b, {}).get("rarity", "common"), 1) for b in badges)
            scores.append((user_id, len(badges), score))
        
        # Trier par score puis par nombre
        scores.sort(key=lambda x: (-x[2], -x[1]))
        
        embed = discord.Embed(
            title="🏆 Classement des Badges",
            color=0xffd700
        )
        
        medals = ["🥇", "🥈", "🥉"]
        lines = []
        
        for i, (user_id, count, score) in enumerate(scores[:10]):
            try:
                member = await self.bot.fetch_user(int(user_id))
                name = member.display_name
            except:
                name = f"Utilisateur #{user_id[:6]}"
            
            medal = medals[i] if i < 3 else f"**{i+1}.**"
            lines.append(f"{medal} {name} - **{count}** badges ({score} pts)")
        
        embed.description = "\n".join(lines) if lines else "Aucun classement disponible."
        await ctx.send(embed=embed)
    
    # ─────────────────────────────────────────────────────────────────────────
    # COMMANDES ADMIN
    # ─────────────────────────────────────────────────────────────────────────
    
    @commands.command(name="give_badge")
    @commands.has_permissions(administrator=True)
    async def give_badge(self, ctx, member: discord.Member, *, badge_name: str):
        """[Admin] Donne un badge à un membre"""
        # Recherche du badge
        badge_id = None
        for bid, bdata in BADGES_DATA.items():
            if bid.lower() == badge_name.lower() or bdata["name"].lower() == badge_name.lower():
                badge_id = bid
                break
        
        if not badge_id:
            await ctx.send("❌ Badge non trouvé.")
            return
        
        result = unlock_badge(member.id, badge_id, self.bot)
        
        if result:
            badge = BADGES_DATA[badge_id]
            embed = discord.Embed(
                title="🎖️ Badge Attribué",
                description=f"{member.mention} a reçu le badge **{badge['emoji']} {badge['name']}**!",
                color=RARITY_COLORS.get(badge["rarity"], 0xffd700)
            )
            embed.add_field(name="Récompense", value=f"+{badge['points_reward']} points")
            await ctx.send(embed=embed)
            
            # Notifier le membre
            try:
                dm_embed = discord.Embed(
                    title="🎖️ Nouveau Badge !",
                    description=f"Tu as reçu le badge **{badge['emoji']} {badge['name']}**\n\n*{badge['description']}*",
                    color=RARITY_COLORS.get(badge["rarity"], 0xffd700)
                )
                dm_embed.add_field(name="Récompense", value=f"+{badge['points_reward']} points")
                await member.send(embed=dm_embed)
            except:
                pass
        else:
            await ctx.send("❌ Ce membre possède déjà ce badge.")
    
    @commands.command(name="remove_badge")
    @commands.has_permissions(administrator=True)
    async def remove_badge(self, ctx, member: discord.Member, *, badge_name: str):
        """[Admin] Retire un badge à un membre"""
        badge_id = None
        for bid, bdata in BADGES_DATA.items():
            if bid.lower() == badge_name.lower() or bdata["name"].lower() == badge_name.lower():
                badge_id = bid
                break
        
        if not badge_id:
            await ctx.send("❌ Badge non trouvé.")
            return
        
        if not has_badge(member.id, badge_id):
            await ctx.send("❌ Ce membre n'a pas ce badge.")
            return
        
        data = load_badges_data()
        user_id_str = str(member.id)
        
        if user_id_str in data and badge_id in data[user_id_str].get("badges", []):
            data[user_id_str]["badges"].remove(badge_id)
            if badge_id in data[user_id_str].get("badge_dates", {}):
                del data[user_id_str]["badge_dates"][badge_id]
            save_badges_data(data)
            
            badge = BADGES_DATA[badge_id]
            await ctx.send(f"✅ Badge **{badge['emoji']} {badge['name']}** retiré de {member.mention}.")
        else:
            await ctx.send("❌ Erreur lors du retrait du badge.")
    
    @commands.command(name="set_stat")
    @commands.has_permissions(administrator=True)
    async def set_stat(self, ctx, member: discord.Member, stat_name: str, value: int):
        """[Admin] Définit une statistique d'un membre"""
        valid_stats = [
            "tasks_completed", "chapters_translated", "chapters_cleaned",
            "chapters_edited", "chapters_checked", "messages_count",
            "members_helped", "members_mentored", "events_participated"
        ]
        
        if stat_name not in valid_stats:
            await ctx.send(f"❌ Statistique invalide. Valides: {', '.join(valid_stats)}")
            return
        
        update_user_stat(member.id, stat_name, value=value)
        await ctx.send(f"✅ Statistique `{stat_name}` de {member.mention} définie à **{value}**.")
    
    @commands.command(name="check_badges")
    @commands.has_permissions(administrator=True)
    async def check_badges(self, ctx, member: discord.Member):
        """[Admin] Vérifie et attribue les badges mérités"""
        user_data = get_user_badges(member.id)
        stats = user_data.get("stats", {})
        current_badges = user_data.get("badges", [])
        
        unlocked = []
        
        # Vérifications automatiques
        checks = [
            ("task_master", stats.get("tasks_completed", 0) >= 50),
            ("translator_pro", stats.get("chapters_translated", 0) >= 20),
            ("cleaner_expert", stats.get("chapters_cleaned", 0) >= 30),
            ("editor_master", stats.get("chapters_edited", 0) >= 25),
            ("checker_hawk", stats.get("chapters_checked", 0) >= 40),
            ("community_star", stats.get("messages_count", 0) >= 500),
            ("helper", stats.get("members_helped", 0) >= 10),
            ("mentor", stats.get("members_mentored", 0) >= 3),
            ("collector", len(current_badges) >= 10),
        ]
        
        # Vérifier polyvalent (3 rôles différents)
        roles = stats.get("roles_contributed", [])
        if len(set(roles)) >= 3:
            checks.append(("polyvalent", True))
        
        for badge_id, condition in checks:
            if condition and badge_id not in current_badges:
                result = unlock_badge(member.id, badge_id, self.bot)
                if result:
                    unlocked.append(badge_id)
        
        if unlocked:
            badges_text = ", ".join([f"{BADGES_DATA[b]['emoji']} {BADGES_DATA[b]['name']}" for b in unlocked])
            await ctx.send(f"✅ Badges débloqués pour {member.mention}: {badges_text}")
        else:
            await ctx.send(f"Aucun nouveau badge à débloquer pour {member.mention}.")
    
    # ─────────────────────────────────────────────────────────────────────────
    # ÉVÉNEMENTS
    # ─────────────────────────────────────────────────────────────────────────
    
    @commands.Cog.listener()
    async def on_message(self, message):
        """Tracking des messages pour badges sociaux"""
        if message.author.bot:
            return
        
        # Incrémenter le compteur de messages
        data = load_badges_data()
        user_id = str(message.author.id)
        
        if user_id in data:
            stats = data[user_id].get("stats", {})
            stats["messages_count"] = stats.get("messages_count", 0) + 1
            data[user_id]["stats"] = stats
            save_badges_data(data)
            
            # Vérifier badge community_star
            if stats["messages_count"] == 500 and not has_badge(message.author.id, "community_star"):
                result = unlock_badge(message.author.id, "community_star", self.bot)
                if result:
                    try:
                        embed = discord.Embed(
                            title="🎖️ Nouveau Badge Débloqué !",
                            description=f"**{BADGES_DATA['community_star']['emoji']} {BADGES_DATA['community_star']['name']}**\n\n*{BADGES_DATA['community_star']['description']}*",
                            color=RARITY_COLORS["uncommon"]
                        )
                        await message.channel.send(f"🎉 {message.author.mention} a débloqué un badge !", embed=embed)
                    except:
                        pass

# ═══════════════════════════════════════════════════════════════════════════════
# SETUP
# ═══════════════════════════════════════════════════════════════════════════════

async def setup(bot):
    await bot.add_cog(Achievements(bot))