# shop.py
# Système de boutique AMÉLIORÉ : Loterie hebdomadaire, Boosts fonctionnels, Expirations auto
import discord
from discord.ext import commands, tasks
import json
import os
import random
from datetime import datetime, timedelta
from config import COLORS, ADMIN_ROLES, DATA_FILES, SHOP_ROLES
from utils import load_json, save_json

# Fichiers de données (depuis config.py)
SHOP_FILE = DATA_FILES["shop_inventory"]
SHOP_ITEMS_FILE = DATA_FILES["shop_items"]
PURCHASES_FILE = DATA_FILES["purchases"]
LOTTERY_FILE = DATA_FILES["lottery"]
os.makedirs("data", exist_ok=True)

# Inventaires des utilisateurs
shop_inventory = {}

# Items de la boutique (chargés depuis le fichier)
shop_items = {}

# Historique des achats
purchases_history = {}

# Données de la loterie
lottery_data = {
    "current_jackpot": 500,
    "participants": [],
    "last_draw": None,
    "winner_history": []
}

# Loot tables pour mystery boxes
LOOT_COMMON = [
    {"item": "lottery_ticket", "quantity": 1},
    {"item": "points", "quantity": 50},
    {"item": "points", "quantity": 75},
    {"item": "points", "quantity": 100},
]

LOOT_UNCOMMON = [
    {"item": "lottery_ticket", "quantity": 2},
    {"item": "points", "quantity": 150},
    {"item": "points", "quantity": 200},
    {"item": "points", "quantity": 250},
]

LOOT_RARE = [
    {"item": "double_points_24h", "quantity": 1},
    {"item": "triple_points_12h", "quantity": 1},
    {"item": "lottery_ticket", "quantity": 5},
    {"item": "points", "quantity": 500},
    {"item": "points", "quantity": 750},
]

# ═══════════════════════════════════════════════════════════════════════════════
# IMAGES DE MARCHANDS (URLs d'images de PNJ marchands)
# ═══════════════════════════════════════════════════════════════════════════════

MERCHANT_IMAGES = {
    "main": "https://i.pinimg.com/736x/0c/95/9b/0c959b9133574f97d9b3a081bc9aa607.jpg",  # Marchand principal
    "lottery": "https://i.pinimg.com/736x/0c/95/9b/0c959b9133574f97d9b3a081bc9aa607.jpg",  # Marchand de loterie
    "special": "https://i.pinimg.com/736x/0c/95/9b/0c959b9133574f97d9b3a081bc9aa607.jpg"  # Marchand d'articles spéciaux
}

# Messages aléatoires du marchand
MERCHANT_GREETINGS = [
    "Bienvenue dans ma boutique, voyageur ! 🎭",
    "Ah, un nouveau client ! Que puis-je faire pour vous ? 🤝",
    "Bonjour ! Vous cherchez quelque chose de spécial ? ✨",
    "Entrez, entrez ! J'ai les meilleurs articles du serveur ! 🏪",
    "Salutations ! Prêt à dépenser vos précieux points ? 💰",
    "Bienvenue chez le marchand le plus réputé du royaume ! 👑"
]

MERCHANT_BUY_SUCCESS = [
    "Excellent choix ! Merci pour votre achat ! 🎉",
    "Voilà qui est fait ! Profitez bien de votre acquisition ! ✨",
    "Transaction réussie ! Revenez me voir quand vous voulez ! 🤝",
    "Merci pour votre confiance ! Vous ne serez pas déçu ! 💫",
    "Parfait ! C'est un plaisir de faire affaire avec vous ! 🌟"
]

MERCHANT_INSUFFICIENT_FUNDS = [
    "Hmm... Il semblerait que vos poches soient un peu légères... 💸",
    "Désolé, mais vous n'avez pas assez de points pour cet article. 😔",
    "Revenez quand vous aurez économisé davantage ! 🏦",
    "Cet article nécessite plus de points que ce que vous possédez... 📊"
]


def charger_shop():
    """Charge les données de la boutique"""
    global shop_inventory, lottery_data, shop_items, purchases_history
    
    # Charger les inventaires utilisateurs
    if os.path.exists(SHOP_FILE):
        try:
            with open(SHOP_FILE, "r", encoding="utf-8") as f:
                contenu = f.read().strip()
                if contenu:
                    shop_inventory.update(json.loads(contenu))
            print("✅ Inventaires shop chargés")
        except Exception as e:
            print(f"❌ Erreur chargement inventaires: {e}")
    
    # Charger les items de la boutique
    if os.path.exists(SHOP_ITEMS_FILE):
        try:
            with open(SHOP_ITEMS_FILE, "r", encoding="utf-8") as f:
                contenu = f.read().strip()
                if contenu:
                    shop_items.update(json.loads(contenu))
            print(f"✅ {len(shop_items)} items shop chargés")
        except Exception as e:
            print(f"❌ Erreur chargement items shop: {e}")
    
    # Charger l'historique des achats
    if os.path.exists(PURCHASES_FILE):
        try:
            with open(PURCHASES_FILE, "r", encoding="utf-8") as f:
                contenu = f.read().strip()
                if contenu:
                    purchases_history.update(json.loads(contenu))
            print("✅ Historique achats chargé")
        except Exception as e:
            print(f"❌ Erreur chargement achats: {e}")
    
    # Charger la loterie
    if os.path.exists(LOTTERY_FILE):
        try:
            with open(LOTTERY_FILE, "r", encoding="utf-8") as f:
                contenu = f.read().strip()
                if contenu:
                    lottery_data.update(json.loads(contenu))
            print("✅ Loterie chargée")
        except Exception as e:
            print(f"❌ Erreur chargement loterie: {e}")


def sauvegarder_shop():
    """Sauvegarde les données"""
    try:
        with open(SHOP_FILE, "w", encoding="utf-8") as f:
            json.dump(shop_inventory, f, ensure_ascii=False, indent=4)
        with open(PURCHASES_FILE, "w", encoding="utf-8") as f:
            json.dump(purchases_history, f, ensure_ascii=False, indent=4)
        with open(LOTTERY_FILE, "w", encoding="utf-8") as f:
            json.dump(lottery_data, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"❌ Erreur sauvegarde shop: {e}")


def get_user_inventory(user_id):
    """Récupère ou crée l'inventaire d'un utilisateur"""
    user_id_str = str(user_id)
    if user_id_str not in shop_inventory:
        shop_inventory[user_id_str] = {
            "items": {},
            "active_boosts": {},
            "active_roles": {},
            "purchase_history": [],
            "lottery_tickets": 0,
            "total_spent": 0
        }
    # Migration pour anciens inventaires
    if "total_spent" not in shop_inventory[user_id_str]:
        shop_inventory[user_id_str]["total_spent"] = 0
    if "active_boosts" not in shop_inventory[user_id_str]:
        shop_inventory[user_id_str]["active_boosts"] = {}
    if "active_roles" not in shop_inventory[user_id_str]:
        shop_inventory[user_id_str]["active_roles"] = {}
    return shop_inventory[user_id_str]


def get_shop_item(item_id):
    """Récupère un item de la boutique par son ID"""
    # Chercher dans le fichier JSON d'abord
    if item_id in shop_items:
        return shop_items[item_id]
    
    # Chercher par nom (insensible à la casse)
    item_id_lower = item_id.lower().replace(" ", "_").replace("-", "_")
    for iid, idata in shop_items.items():
        if iid.lower() == item_id_lower:
            return idata
        if idata.get("name", "").lower().replace(" ", "_") == item_id_lower:
            return idata
    
    return None


def activate_boost(user_id, boost_id, item_data):
    """Active un boost pour un utilisateur"""
    inv = get_user_inventory(user_id)
    
    if "active_boosts" not in inv:
        inv["active_boosts"] = {}
    
    # Déterminer le type de boost
    item_type = item_data.get("type", "consumable")
    
    if item_type == "consumable" and not item_data.get("duration_hours"):
        # Boost à usage unique (s'active au prochain usage)
        inv["active_boosts"][boost_id] = {
            "activated_at": datetime.now().isoformat(),
            "one_time": True
        }
    else:
        # Boost temporaire
        duration = item_data.get("duration_hours", 24)
        expires = datetime.now() + timedelta(hours=duration)
        
        # Déterminer le multiplicateur
        multiplier = 1.0
        if "double" in boost_id.lower():
            multiplier = 2.0
        elif "triple" in boost_id.lower():
            multiplier = 3.0
        
        inv["active_boosts"][boost_id] = {
            "activated_at": datetime.now().isoformat(),
            "expires": expires.isoformat(),
            "multiplier": multiplier
        }
    
    sauvegarder_shop()
    return True


class ShopSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        charger_shop()
    
    async def cog_load(self):
        """Démarrer les tâches"""
        self.weekly_lottery.start()
        self.check_expirations.start()
        print("✅ Tâches shop démarrées")
    
    async def cog_unload(self):
        self.weekly_lottery.cancel()
        self.check_expirations.cancel()
    
    # ==================== TIRAGE LOTERIE ====================
    
    @tasks.loop(hours=168)  # Chaque semaine
    async def weekly_lottery(self):
        """Tirage automatique de la loterie chaque semaine"""
        if not lottery_data["participants"]:
            return
        
        winner_id = random.choice(lottery_data["participants"])
        jackpot = lottery_data.get("current_jackpot", 500)
        
        # Donner les points au gagnant
        try:
            from community import add_points
            add_points(int(winner_id), jackpot, "lottery_win")
        except:
            pass
        
        # Enregistrer le gagnant
        lottery_data["winner_history"].append({
            "user_id": winner_id,
            "jackpot": jackpot,
            "date": datetime.now().isoformat(),
            "participants_count": len(lottery_data["participants"])
        })
        
        # Reset
        old_participants = len(lottery_data["participants"])
        lottery_data["participants"] = []
        lottery_data["current_jackpot"] = 500
        lottery_data["last_draw"] = datetime.now().isoformat()
        
        sauvegarder_shop()
        
        # Annoncer (chercher un salon approprié)
        for guild in self.bot.guilds:
            channel = discord.utils.find(
                lambda c: "general" in c.name.lower() or "annonce" in c.name.lower(),
                guild.text_channels
            )
            if channel:
                winner = guild.get_member(int(winner_id))
                winner_name = winner.mention if winner else f"User {winner_id}"
                
                embed = discord.Embed(
                    title="🎰 TIRAGE DE LA LOTERIE ! 🎰",
                    description=f"**{winner_name}** remporte le jackpot !",
                    color=discord.Color.gold(),
                    timestamp=datetime.now()
                )
                embed.add_field(name="💰 Gains", value=f"**{jackpot:,}** points !", inline=True)
                embed.add_field(name="👥 Participants", value=str(old_participants), inline=True)
                embed.set_footer(text="Prochain tirage dans 7 jours !")
                
                try:
                    await channel.send("@here 🎰 **TIRAGE DE LA LOTERIE !**", embed=embed)
                except:
                    pass
    
    @weekly_lottery.before_loop
    async def before_lottery(self):
        await self.bot.wait_until_ready()
    
    # ==================== EXPIRATION AUTO ====================
    
    @tasks.loop(hours=1)
    async def check_expirations(self):
        """Vérifie et retire les rôles/boosts expirés"""
        now = datetime.now()
        
        for user_id, inv in list(shop_inventory.items()):
            # Vérifier les rôles temporaires
            expired_roles = []
            for role_key, role_data in list(inv.get("active_roles", {}).items()):
                if "expires" in role_data:
                    try:
                        expires = datetime.fromisoformat(role_data["expires"])
                        if now >= expires:
                            expired_roles.append((role_key, role_data))
                    except:
                        pass
            
            # Retirer les rôles expirés
            for role_key, role_data in expired_roles:
                role_id = role_data.get("role_id")
                if role_id:
                    for guild in self.bot.guilds:
                        member = guild.get_member(int(user_id))
                        if member:
                            role = guild.get_role(role_id)
                            if role and role in member.roles:
                                try:
                                    await member.remove_roles(role, reason="Rôle temporaire expiré")
                                    try:
                                        await member.send(
                                            f"⏰ Votre rôle temporaire **{role.name}** a expiré. "
                                            f"Vous pouvez le racheter dans la boutique avec `!shop`"
                                        )
                                    except:
                                        pass
                                except:
                                    pass
                
                if role_key in inv.get("active_roles", {}):
                    del inv["active_roles"][role_key]
            
            # Vérifier les boosts expirés
            expired_boosts = []
            for boost_id, boost_data in list(inv.get("active_boosts", {}).items()):
                if "expires" in boost_data:
                    try:
                        expires = datetime.fromisoformat(boost_data["expires"])
                        if now >= expires:
                            expired_boosts.append(boost_id)
                    except:
                        pass
            
            for boost_id in expired_boosts:
                if boost_id in inv.get("active_boosts", {}):
                    del inv["active_boosts"][boost_id]
            
            if expired_roles or expired_boosts:
                sauvegarder_shop()
    
    @check_expirations.before_loop
    async def before_check(self):
        await self.bot.wait_until_ready()
    
    # ==================== COMMANDES SHOP AMÉLIORÉES ====================
    
    @commands.command(name="shop", aliases=["boutique", "magasin"])
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def shop(self, ctx, category: str = None):
        """
        Affiche la boutique avec une interface immersive type RPG.
        Catégories: roles, boosts, cosmetics, privileges, lottery, manga_packs, social, utility, limited
        """
        # Récupérer les points de l'utilisateur
        try:
            from community import get_user_stats
            user_stats = get_user_stats(ctx.author.id)
            user_points = user_stats.get("xp", user_stats.get("points", 0))
        except:
            user_points = 0

        if not shop_items:
            await ctx.send("❌ La boutique est vide. Contactez un administrateur.")
            return
        
        # Message d'accueil aléatoire du marchand
        greeting = random.choice(MERCHANT_GREETINGS)
        
        # Filtrer par catégorie si spécifiée
        if category:
            category_lower = category.lower()
            filtered = {k: v for k, v in shop_items.items() 
                       if v.get("category", "").lower() == category_lower and v.get("active", True)}
            if not filtered:
                categories = list(set(v.get("category", "autre") for v in shop_items.values()))
                
                embed = discord.Embed(
                    title="🏪 Catégorie Introuvable",
                    description=f"*Le marchand secoue la tête...*\n\n"
                               f"❌ Désolé, je n'ai pas de section **{category}** dans ma boutique.\n\n"
                               f"**Catégories disponibles:**\n" + 
                               "\n".join([f"• `{cat}`" for cat in sorted(categories)]),
                    color=discord.Color.orange()
                )
                embed.set_thumbnail(url=MERCHANT_IMAGES["main"])
                embed.set_footer(text="Utilisez !shop <catégorie> pour explorer une section")
                await ctx.send(embed=embed)
                return
            items = filtered
            title = f"🏪 {category.title()}"
        else:
            items = {k: v for k, v in shop_items.items() if v.get("active", True)}
            title = "🏪 Boutique de LanorTrad"
        
        # Créer l'embed principal avec design immersif
        embed = discord.Embed(
            title=title,
            description=f"*{greeting}*\n\n"
                       f"╔══════════════════════════════╗\n"
                       f"  💰 **Votre Bourse:** {user_points:,} points\n"
                       f"╚══════════════════════════════╝",
            color=discord.Color.from_rgb(255, 215, 0),  # Couleur or
            timestamp=datetime.now()
        )
        
        # Image du marchand
        embed.set_thumbnail(url=MERCHANT_IMAGES["main"])
        
        # Grouper par catégorie
        categories = {}
        for item_id, item in items.items():
            cat = item.get("category", "autre")
            if cat not in categories:
                categories[cat] = []
            categories[cat].append((item_id, item))
        
        # Emojis et noms de catégories plus immersifs
        category_display = {
            "roles": {"emoji": "👑", "name": "Rôles Prestigieux", "desc": "Devenez quelqu'un d'important"},
            "boosts": {"emoji": "⚡", "name": "Potions & Boosts", "desc": "Augmentez votre pouvoir"},
            "cosmetics": {"emoji": "🎨", "name": "Parures Cosmétiques", "desc": "Personnalisez votre apparence"},
            "privileges": {"emoji": "⭐", "name": "Privilèges Exclusifs", "desc": "Accédez à l'élite"},
            "lottery": {"emoji": "🎰", "name": "Jeux de Hasard", "desc": "Tentez votre chance"},
            "manga_packs": {"emoji": "📚", "name": "Collections Manga", "desc": "Des packs pour les passionnés"},
            "social": {"emoji": "💬", "name": "Articles Sociaux", "desc": "Interagissez différemment"},
            "utility": {"emoji": "🔧", "name": "Outils Pratiques", "desc": "Facilitez-vous la vie"},
            "limited": {"emoji": "💎", "name": "Édition Limitée", "desc": "Rarissimes et précieux"}
        }
        
        # Afficher jusqu'à 6 catégories dans l'embed
        displayed_categories = 0
        for cat, cat_items in sorted(categories.items(), key=lambda x: len(x[1]), reverse=True):
            if displayed_categories >= 6:
                break
            
            cat_info = category_display.get(cat, {"emoji": "📦", "name": cat.title(), "desc": ""})
            items_text = ""
            
            for item_id, item in cat_items[:4]:  # Max 4 items par catégorie
                # Vérifier si l'utilisateur peut se le permettre
                price = item.get("price", 0)
                can_afford = user_points >= price
                
                # Icône de disponibilité
                stock = item.get("stock", -1)
                if stock == 0:
                    status_icon = "⛔"
                elif can_afford:
                    status_icon = "💚"
                else:
                    status_icon = "🔒"
                
                # Stock info
                stock_text = ""
                if stock > 0 and stock <= 10:
                    stock_text = f" `[{stock} restant{'s' if stock > 1 else ''}]`"
                elif stock == 0:
                    stock_text = " `[ÉPUISÉ]`"
                
                emoji = item.get("emoji", "📦")
                name = item.get("name", item_id)
                
                # Formatage prix
                price_display = f"{price:,}" if price >= 1000 else str(price)
                
                items_text += f"{status_icon} {emoji} **{name}**{stock_text}\n"
                items_text += f"    └ *{price_display} pts*\n"
            
            # Ajouter "..." si plus d'items
            if len(cat_items) > 4:
                items_text += f"    *...et {len(cat_items) - 4} autre(s)*\n"
            
            # Ajouter le champ
            field_name = f"{cat_info['emoji']} {cat_info['name']}"
            embed.add_field(
                name=field_name,
                value=items_text or "Aucun article",
                inline=True
            )
            
            displayed_categories += 1
        
        # Ajouter la loterie si active
        if lottery_data.get("current_jackpot", 0) > 0:
            jackpot = lottery_data.get("current_jackpot", 500)
            participants = len(lottery_data.get("participants", []))
            
            lottery_text = (
                f"🎲 **Jackpot:** {jackpot:,} pts\n"
                f"👥 **{participants}** participant{'s' if participants > 1 else ''}\n"
                f"🎟️ *Tentez votre chance !*"
            )
            
            embed.add_field(
                name="🎰 Loterie Hebdomadaire",
                value=lottery_text,
                inline=True
            )
        
        # Instructions en bas
        embed.add_field(
            name="📋 Comment Commander",
            value=(
                "🔹 `!buy <article>` → Acheter un article\n"
                "🔹 `!item_info <article>` → Détails d'un article\n"
                "🔹 `!shop <catégorie>` → Filtrer par catégorie\n"
                "🔹 `!inventory` → Voir votre inventaire"
            ),
            inline=False
        )
        
        # Footer avec citation du marchand
        merchant_quotes = [
            "Les meilleurs prix du royaume !",
            "Qualité garantie ou remboursé !",
            "Chaque point compte, dépensez sagement !",
            "Vos points sont précieux, choisissez bien !",
            "La satisfaction client est ma priorité !"
        ]
        embed.set_footer(
            text=f"💬 Marchand: \"{random.choice(merchant_quotes)}\"",
            icon_url=ctx.author.avatar.url if ctx.author.avatar else None
        )
        
        await ctx.send(embed=embed)
    
    @commands.command(name="item_info", aliases=["shopinfo", "info_article"])
    async def item_info(self, ctx, *, item_name: str):
        """Affiche les détails d'un item avec un design immersif"""
        item_id = None
        item_data = None
        
        # Recherche flexible
        item_name_lower = item_name.lower().replace(" ", "_")
        
        for iid, idata in shop_items.items():
            if iid.lower() == item_name_lower or \
               idata.get("name", "").lower() == item_name.lower() or \
               idata.get("id", "").lower() == item_name_lower:
                item_id = iid
                item_data = idata
                break
        
        if not item_data:
            embed = discord.Embed(
                title="❌ Article Introuvable",
                description=f"*Le marchand fouille dans ses étagères...*\n\n"
                           f"Désolé, je n'ai pas d'article nommé **{item_name}**.\n"
                           f"Utilisez `!shop` pour voir tous mes articles !",
                color=discord.Color.red()
            )
            embed.set_thumbnail(url=MERCHANT_IMAGES["main"])
            await ctx.send(embed=embed)
            return
        
        # Créer l'embed détaillé
        emoji = item_data.get("emoji", "📦")
        name = item_data.get("name", item_id)
        price = item_data.get("price", 0)
        
        # Description immersive
        description = item_data.get("description", "Un article mystérieux...")
        
        embed = discord.Embed(
            title=f"{emoji} {name}",
            description=f"*Le marchand vous présente l'article avec fierté...*\n\n"
                       f"╔════════════════════════════════╗\n"
                       f"  {description}\n"
                       f"╚════════════════════════════════╝",
            color=discord.Color.from_rgb(75, 0, 130),  # Violet royal
            timestamp=datetime.now()
        )
        
        # Image de l'article (si disponible)
        if item_data.get("image_url"):
            embed.set_image(url=item_data["image_url"])
        else:
            embed.set_thumbnail(url=MERCHANT_IMAGES["special"])
        
        # Prix avec design
        price_display = f"{price:,}" if price >= 1000 else str(price)
        embed.add_field(
            name="💰 Prix",
            value=f"```fix\n{price_display} points```",
            inline=True
        )
        
        # Catégorie
        cat = item_data.get("category", "autre")
        cat_display = category_display.get(cat, {"emoji": "📦", "name": cat.title()})
        embed.add_field(
            name="📁 Catégorie",
            value=f"{cat_display['emoji']} {cat_display['name']}",
            inline=True
        )
        
        # Stock avec design
        stock = item_data.get("stock", -1)
        if stock == -1:
            stock_text = "♾️ Illimité"
            stock_color = "fix"
        elif stock == 0:
            stock_text = "⛔ Épuisé"
            stock_color = "diff"
        elif stock <= 5:
            stock_text = f"⚠️ {stock} restant{'s' if stock > 1 else ''}"
            stock_color = "css"
        else:
            stock_text = f"✅ {stock} en stock"
            stock_color = "css"
        
        embed.add_field(
            name="📊 Disponibilité",
            value=f"```{stock_color}\n{stock_text}```",
            inline=True
        )
        
        # Type d'article
        item_type = item_data.get("type", "one_time")
        type_icons = {
            "one_time": "🔒 Achat Unique",
            "consumable": "🔄 Consommable",
            "temporary": "⏰ Temporaire"
        }
        embed.add_field(
            name="🏷️ Type",
            value=type_icons.get(item_type, item_type),
            inline=True
        )
        
        # Durée si temporaire
        if item_data.get("duration_days"):
            days = item_data["duration_days"]
            embed.add_field(
                name="⏱️ Durée",
                value=f"```yaml\n{days} jour{'s' if days > 1 else ''}```",
                inline=True
            )
        elif item_data.get("duration_hours"):
            hours = item_data["duration_hours"]
            embed.add_field(
                name="⏱️ Durée",
                value=f"```yaml\n{hours} heure{'s' if hours > 1 else ''}```",
                inline=True
            )
        
        # Avantages/Effets
        if item_data.get("effects"):
            effects_text = "\n".join([f"• {effect}" for effect in item_data["effects"]])
            embed.add_field(
                name="✨ Effets",
                value=effects_text,
                inline=False
            )
        
        # Prérequis
        requirements = item_data.get("requirements", {})
        req_text = []
        if requirements.get("level", 0) > 0:
            req_text.append(f"📊 Niveau {requirements['level']} requis")
        if requirements.get("badges"):
            badges = ", ".join(requirements["badges"])
            req_text.append(f"🏅 Badges: {badges}")
        
        if req_text:
            embed.add_field(
                name="⚠️ Prérequis",
                value="\n".join(req_text),
                inline=False
            )
        
        # Vérifier si l'utilisateur peut acheter
        try:
            from community import get_user_stats
            user_stats = get_user_stats(ctx.author.id)
            user_points = user_stats.get("xp", user_stats.get("points", 0))

            if user_points >= price and stock != 0:
                purchase_status = "✅ Vous pouvez acheter cet article !"
                status_color = discord.Color.green()
            elif stock == 0:
                purchase_status = "⛔ Article épuisé pour le moment"
                status_color = discord.Color.orange()
            else:
                missing = price - user_points
                purchase_status = f"🔒 Il vous manque {missing:,} XP"
                status_color = discord.Color.red()
            
            embed.add_field(
                name="💳 Statut d'Achat",
                value=purchase_status,
                inline=False
            )
            embed.color = status_color
        except:
            pass
        
        # Footer
        embed.set_footer(
            text=f"🛒 Commande: !buy {item_id} | ID: {item_id}",
            icon_url=ctx.author.avatar.url if ctx.author.avatar else None
        )
        
        await ctx.send(embed=embed)
    
    @commands.command(name="buy", aliases=["acheter"])
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def buy(self, ctx, *, item_name: str):
        """Achète un article de la boutique avec confirmation immersive"""
        # Trouver l'item
        item_id = None
        item_data = None
        
        item_name_lower = item_name.lower().replace(" ", "_").replace("-", "_")
        
        for iid, idata in shop_items.items():
            if iid.lower() == item_name_lower or \
               idata.get("name", "").lower() == item_name.lower() or \
               idata.get("id", "").lower() == item_name_lower:
                item_id = iid
                item_data = idata
                break
        
        if not item_data:
            embed = discord.Embed(
                title="❌ Article Introuvable",
                description=f"*Le marchand secoue la tête...*\n\n"
                           f"Je n'ai pas d'article nommé **{item_name}**.\n"
                           f"Utilisez `!shop` pour voir ma collection !",
                color=discord.Color.red()
            )
            embed.set_thumbnail(url=MERCHANT_IMAGES["main"])
            await ctx.send(embed=embed)
            return
        
        # Vérifier si actif
        if not item_data.get("active", True):
            embed = discord.Embed(
                title="❌ Article Indisponible",
                description=f"*Le marchand semble embarrassé...*\n\n"
                           f"Désolé, **{item_data.get('name', item_id)}** n'est plus en vente.",
                color=discord.Color.red()
            )
            embed.set_thumbnail(url=MERCHANT_IMAGES["main"])
            await ctx.send(embed=embed)
            return
        
        # Vérifier le stock
        if item_data.get("stock", -1) == 0:
            embed = discord.Embed(
                title="⛔ Rupture de Stock",
                description=f"*Le marchand vérifie ses réserves...*\n\n"
                           f"Malheureusement, **{item_data.get('name', item_id)}** est épuisé.\n"
                           f"Revenez plus tard !",
                color=discord.Color.orange()
            )
            embed.set_thumbnail(url=MERCHANT_IMAGES["main"])
            embed.set_footer(text="Les stocks se renouvellent régulièrement !")
            await ctx.send(embed=embed)
            return
        
        # Vérifier les points
        try:
            from community import get_user_stats, add_points
            user_stats = get_user_stats(ctx.author.id)
            user_points = user_stats.get("xp", user_stats.get("points", 0))
        except Exception as e:
            await ctx.send(f"❌ Erreur système: {e}")
            return
        
        price = item_data.get("price", 0)
        
        if user_points < price:
            # Message d'échec immersif
            merchant_msg = random.choice(MERCHANT_INSUFFICIENT_FUNDS)
            missing = price - user_points
            
            embed = discord.Embed(
                title="💸 Fonds Insuffisants",
                description=f"*{merchant_msg}*\n\n"
                           f"╔══════════════════════════════╗\n"
                           f"  Prix: **{price:,}** points\n"
                           f"  Vous avez: **{user_points:,}** points\n"
                           f"  Il manque: **{missing:,}** points\n"
                           f"╚══════════════════════════════╝",
                color=discord.Color.red()
            )
            embed.set_thumbnail(url=MERCHANT_IMAGES["main"])
            embed.add_field(
                name="💡 Astuce",
                value="Gagnez plus de points en participant aux activités du serveur !",
                inline=False
            )
            embed.set_footer(text="Revenez quand votre bourse sera mieux garnie !")
            await ctx.send(embed=embed)
            return
        
        # Vérifier les prérequis
        requirements = item_data.get("requirements", {})
        if requirements.get("level", 0) > 0:
            user_level = user_stats.get("level", 1)
            if user_level < requirements["level"]:
                embed = discord.Embed(
                    title="🔒 Niveau Insuffisant",
                    description=f"*Le marchand vous regarde avec un air désolé...*\n\n"
                               f"Cet article nécessite le niveau **{requirements['level']}**.\n"
                               f"Vous êtes niveau **{user_level}**.",
                    color=discord.Color.orange()
                )
                embed.set_thumbnail(url=MERCHANT_IMAGES["main"])
                await ctx.send(embed=embed)
                return
        
        if requirements.get("badges"):
            try:
                from achievements import user_badges
                user_badge_list = user_badges.get(str(ctx.author.id), {}).get("unlocked", [])
                missing_badges = [b for b in requirements["badges"] if b not in user_badge_list]
                if missing_badges:
                    embed = discord.Embed(
                        title="🏅 Badges Requis",
                        description=f"*Le marchand secoue la tête...*\n\n"
                                   f"Vous devez posséder ces badges:\n" +
                                   "\n".join([f"• {b}" for b in missing_badges]),
                        color=discord.Color.orange()
                    )
                    embed.set_thumbnail(url=MERCHANT_IMAGES["main"])
                    await ctx.send(embed=embed)
                    return
            except:
                pass
        
        # Vérifier si déjà acheté (pour les one-time)
        inv = get_user_inventory(ctx.author.id)
        if item_data.get("type") == "one_time":
            if item_id in inv.get("items", {}):
                embed = discord.Embed(
                    title="⚠️ Déjà Possédé",
                    description=f"*Le marchand sourit...*\n\n"
                               f"Vous possédez déjà **{item_data.get('name', item_id)}** !\n"
                               f"Cet article ne peut être acheté qu'une seule fois.",
                    color=discord.Color.orange()
                )
                embed.set_thumbnail(url=MERCHANT_IMAGES["main"])
                await ctx.send(embed=embed)
                return
        
        # === TRANSACTION ===
        
        # Déduire les points
        try:
            add_points(ctx.author.id, -price, f"shop_purchase_{item_id}")
        except Exception as e:
            await ctx.send(f"❌ Erreur lors de la transaction: {e}")
            return
        
        # Ajouter à l'inventaire
        inv["items"][item_id] = inv["items"].get(item_id, 0) + 1
        inv["total_spent"] = inv.get("total_spent", 0) + price
        
        # Mettre à jour le stock
        if item_data.get("stock", -1) > 0:
            shop_items[item_id]["stock"] -= 1
            with open(SHOP_ITEMS_FILE, "w", encoding="utf-8") as f:
                json.dump(shop_items, f, ensure_ascii=False, indent=4)
        
        # Enregistrer l'achat
        purchase_record = {
            "user_id": str(ctx.author.id),
            "item_id": item_id,
            "price": price,
            "date": datetime.now().isoformat()
        }
        inv["purchase_history"].append(purchase_record)
        
        if str(ctx.author.id) not in purchases_history:
            purchases_history[str(ctx.author.id)] = []
        purchases_history[str(ctx.author.id)].append(purchase_record)
        
        # Gérer les types spéciaux
        item_type = item_data.get("type", "one_time")
        
        if item_type == "consumable":
            # Activer automatiquement les consommables
            if item_data.get("category") == "boosts":
                activate_boost(ctx.author.id, item_id, item_data)
        
        elif item_type == "temporary":
            # Pour les rôles temporaires
            if item_data.get("role_id"):
                role = ctx.guild.get_role(item_data["role_id"])
                if role:
                    try:
                        await ctx.author.add_roles(role, reason=f"Achat boutique: {item_id}")
                        
                        duration = item_data.get("duration_days", 30)
                        expires = datetime.now() + timedelta(days=duration)
                        
                        inv["active_roles"][item_id] = {
                            "role_id": role.id,
                            "expires": expires.isoformat(),
                            "purchased_at": datetime.now().isoformat()
                        }
                    except Exception as e:
                        print(f"Erreur attribution rôle: {e}")
                        # Marquer comme en attente
                        if "pending_roles" not in inv:
                            inv["pending_roles"] = []
                        inv["pending_roles"].append({
                            "item_id": item_id,
                            "date": datetime.now().isoformat()
                        })
        
        # Loterie
        if item_id == "lottery_ticket":
            if str(ctx.author.id) not in lottery_data["participants"]:
                lottery_data["participants"].append(str(ctx.author.id))
        
        sauvegarder_shop()
        
        # === CONFIRMATION IMMERSIVE ===
        
        merchant_msg = random.choice(MERCHANT_BUY_SUCCESS)
        new_balance = user_points - price
        
        embed = discord.Embed(
            title="✅ Transaction Réussie !",
            description=f"*{merchant_msg}*\n\n"
                       f"╔══════════════════════════════════╗\n"
                       f"  {item_data.get('emoji', '📦')} **{item_data.get('name', item_id)}**\n"
                       f"╚══════════════════════════════════╝",
            color=discord.Color.green(),
            timestamp=datetime.now()
        )
        
        embed.set_thumbnail(url=MERCHANT_IMAGES["special"])
        
        # Résumé de la transaction
        embed.add_field(
            name="💰 Résumé Financier",
            value=f"```diff\n"
                  f"- Prix payé: {price:,} pts\n"
                  f"+ Nouveau solde: {new_balance:,} pts```",
            inline=False
        )
        
        # Info sur l'article acheté
        if item_type == "temporary" and item_data.get("duration_days"):
            expires = datetime.now() + timedelta(days=item_data["duration_days"])
            embed.add_field(
                name="⏰ Validité",
                value=f"Actif jusqu'au **{expires.strftime('%d/%m/%Y')}**",
                inline=True
            )
        
        if item_type == "consumable":
            embed.add_field(
                name="✨ Activation",
                value="Article activé automatiquement !",
                inline=True
            )
        
        # Stats d'achat
        total_spent = inv.get("total_spent", price)
        total_purchases = len(inv.get("purchase_history", []))
        
        embed.add_field(
            name="📊 Vos Statistiques",
            value=f"Total dépensé: **{total_spent:,}** pts\n"
                  f"Achats effectués: **{total_purchases}**",
            inline=False
        )
        
        embed.set_footer(
            text="Merci pour votre confiance ! Revenez quand vous voulez !",
            icon_url=ctx.author.avatar.url if ctx.author.avatar else None
        )
        
        await ctx.send(embed=embed)
        
        # Notification DM optionnelle
        try:
            dm_embed = discord.Embed(
                title="🎉 Achat Confirmé",
                description=f"Vous avez acheté **{item_data.get('name', item_id)}** !",
                color=discord.Color.green()
            )
            dm_embed.add_field(name="Prix", value=f"{price:,} points", inline=True)
            dm_embed.add_field(name="Solde restant", value=f"{new_balance:,} points", inline=True)
            await ctx.author.send(embed=dm_embed)
        except:
            pass  # L'utilisateur a peut-être les DMs fermés
    
    # [... Le reste du code reste identique - commandes inventory, use, lottery, etc. ...]
    
    @commands.command(name="inventory", aliases=["inv", "inventaire"])
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def inventory(self, ctx, member: discord.Member = None):
        """Affiche l'inventaire d'un utilisateur de façon immersive"""
        target = member or ctx.author
        inv = get_user_inventory(target.id)
        
        try:
            from community import get_user_stats, calculate_level
            user_stats = get_user_stats(target.id)
            user_points = user_stats.get("xp", user_stats.get("points", 0))
            user_level = calculate_level(user_stats.get("total_xp", user_stats.get("total_points_earned", 0)))
        except:
            user_points = 0
            user_level = 0

        embed = discord.Embed(
            title=f"🎒 Inventaire de {target.display_name}",
            description=f"*Contenu de votre sac magique...*\n\n"
                       f"╔══════════════════════════════╗\n"
                       f"  ⭐ Niveau: **{user_level}** — 💎 XP: **{user_points:,}**\n"
                       f"  💳 Total dépensé: **{inv.get('total_spent', 0):,}**\n"
                       f"╚══════════════════════════════╝",
            color=discord.Color.purple(),
            timestamp=datetime.now()
        )
        
        embed.set_thumbnail(url=target.avatar.url if target.avatar else None)
        
        # Items possédés
        items = inv.get("items", {})
        if items:
            items_text = ""
            for item_id, quantity in list(items.items())[:10]:
                item_data = get_shop_item(item_id)
                if item_data:
                    emoji = item_data.get("emoji", "📦")
                    name = item_data.get("name", item_id)
                    items_text += f"{emoji} **{name}** x{quantity}\n"
                else:
                    items_text += f"📦 **{item_id}** x{quantity}\n"
            
            if len(items) > 10:
                items_text += f"\n*...et {len(items) - 10} autre(s)*"
            
            embed.add_field(
                name="📦 Articles Possédés",
                value=items_text,
                inline=False
            )
        else:
            embed.add_field(
                name="📦 Articles Possédés",
                value="*Inventaire vide*",
                inline=False
            )
        
        # Boosts actifs
        active_boosts = inv.get("active_boosts", {})
        if active_boosts:
            boosts_text = ""
            for boost_id, boost_data in list(active_boosts.items())[:5]:
                if "expires" in boost_data:
                    expires = datetime.fromisoformat(boost_data["expires"])
                    time_left = expires - datetime.now()
                    hours_left = int(time_left.total_seconds() / 3600)
                    boosts_text += f"⚡ **{boost_id}** - {hours_left}h restantes\n"
                else:
                    boosts_text += f"⚡ **{boost_id}** - Actif\n"
            
            embed.add_field(
                name="⚡ Boosts Actifs",
                value=boosts_text,
                inline=True
            )
        
        # Rôles temporaires
        active_roles = inv.get("active_roles", {})
        if active_roles:
            roles_text = ""
            for role_key, role_data in list(active_roles.items())[:5]:
                if "expires" in role_data:
                    expires = datetime.fromisoformat(role_data["expires"])
                    roles_text += f"👑 **{role_key}** - Expire le {expires.strftime('%d/%m')}\n"
            
            embed.add_field(
                name="👑 Rôles Temporaires",
                value=roles_text or "Aucun",
                inline=True
            )
        
        # Tickets de loterie
        lottery_tickets = inv.get("lottery_tickets", 0)
        if lottery_tickets > 0:
            embed.add_field(
                name="🎟️ Tickets de Loterie",
                value=f"**{lottery_tickets}** ticket(s)",
                inline=True
            )
        
        # Derniers achats
        purchase_history = inv.get("purchase_history", [])
        if purchase_history:
            recent = purchase_history[-3:]
            history_text = ""
            for purchase in reversed(recent):
                item_name = purchase.get("item_id", "Inconnu")
                price = purchase.get("price", 0)
                date = purchase.get("date", "")[:10]
                history_text += f"• **{item_name}** ({price:,} pts) - {date}\n"
            
            embed.add_field(
                name="📜 Achats Récents",
                value=history_text,
                inline=False
            )
        
        embed.set_footer(text="Utilisez !use <article> pour utiliser un consommable")
        await ctx.send(embed=embed)
    
    @commands.command(name="use", aliases=["utiliser"])
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def use_item(self, ctx, *, item_name: str):
        """Utilise un item consommable"""
        inv = get_user_inventory(ctx.author.id)
        
        # Chercher l'item
        item_id = None
        for iid in inv.get("items", {}).keys():
            if iid.lower() == item_name.lower() or iid.lower().replace("_", " ") == item_name.lower():
                item_id = iid
                break
        
        if not item_id:
            await ctx.send(f"❌ Vous ne possédez pas cet article.")
            return
        
        item_data = get_shop_item(item_id)
        if not item_data:
            await ctx.send("❌ Article introuvable dans la base de données.")
            return
        
        # Vérifier si c'est un consommable
        if item_data.get("type") != "consumable":
            await ctx.send("❌ Cet article n'est pas un consommable.")
            return
        
        # Utiliser l'item
        if item_data.get("category") == "boosts":
            activate_boost(ctx.author.id, item_id, item_data)
            
            # Déduire de l'inventaire
            inv["items"][item_id] -= 1
            if inv["items"][item_id] <= 0:
                del inv["items"][item_id]
            
            sauvegarder_shop()
            
            embed = discord.Embed(
                title="✨ Article Utilisé !",
                description=f"Vous avez activé **{item_data.get('name', item_id)}** !",
                color=discord.Color.green()
            )
            
            if item_data.get("duration_hours"):
                embed.add_field(
                    name="⏰ Durée",
                    value=f"{item_data['duration_hours']} heure(s)",
                    inline=True
                )
            
            await ctx.send(embed=embed)
        else:
            await ctx.send("⚠️ Cet article ne peut pas être utilisé de cette manière.")
    
    @commands.command(name="lottery", aliases=["loterie"])
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def lottery_info(self, ctx):
        """Affiche les informations sur la loterie"""
        jackpot = lottery_data.get("current_jackpot", 500)
        participants = lottery_data.get("participants", [])
        
        embed = discord.Embed(
            title="🎰 Loterie Hebdomadaire",
            description=f"*Le marchand vous montre le pot...*\n\n"
                       f"╔═══════════════════════════════╗\n"
                       f"  💰 Jackpot: **{jackpot:,}** points\n"
                       f"  👥 Participants: **{len(participants)}**\n"
                       f"╚═══════════════════════════════╝",
            color=discord.Color.gold(),
            timestamp=datetime.now()
        )
        
        embed.set_thumbnail(url=MERCHANT_IMAGES["lottery"])
        
        # Vérifier si l'utilisateur participe
        if str(ctx.author.id) in participants:
            embed.add_field(
                name="🎟️ Votre Participation",
                value="✅ Vous participez au tirage !",
                inline=False
            )
        else:
            embed.add_field(
                name="🎟️ Comment Participer",
                value="Achetez un **ticket de loterie** dans la boutique avec `!buy lottery_ticket`",
                inline=False
            )
        
        # Historique des gagnants
        winner_history = lottery_data.get("winner_history", [])
        if winner_history:
            last_winner = winner_history[-1]
            winner_id = last_winner.get("user_id")
            winner = ctx.guild.get_member(int(winner_id)) if winner_id else None
            winner_name = winner.display_name if winner else "Inconnu"
            
            embed.add_field(
                name="🏆 Dernier Gagnant",
                value=f"**{winner_name}** - {last_winner.get('jackpot', 0):,} points",
                inline=True
            )
        
        # Prochain tirage
        last_draw = lottery_data.get("last_draw")
        if last_draw:
            last_draw_date = datetime.fromisoformat(last_draw)
            next_draw = last_draw_date + timedelta(days=7)
            days_until = (next_draw - datetime.now()).days
            
            embed.add_field(
                name="📅 Prochain Tirage",
                value=f"Dans **{days_until}** jour(s)",
                inline=True
            )
        
        embed.set_footer(text="Bonne chance à tous les participants ! 🍀")
        await ctx.send(embed=embed)
    
    # ==================== COMMANDES ADMIN ====================
    
    @commands.command(name="shop_add")
    @commands.has_any_role(*ADMIN_ROLES)
    async def shop_add_item(self, ctx):
        """Ajoute un item à la boutique (commande interactive)"""
        import asyncio
        
        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel
        
        try:
            await ctx.send("📝 **Nom de l'article:**")
            msg = await self.bot.wait_for('message', check=check, timeout=60)
            name = msg.content.strip()
            
            await ctx.send("💰 **Prix (en points):**")
            msg = await self.bot.wait_for('message', check=check, timeout=60)
            price = int(msg.content.strip())
            
            await ctx.send("📁 **Catégorie:** (roles, boosts, cosmetics, etc.)")
            msg = await self.bot.wait_for('message', check=check, timeout=60)
            category = msg.content.strip().lower()
            
            await ctx.send("😊 **Emoji:** (ex: 🎁)")
            msg = await self.bot.wait_for('message', check=check, timeout=60)
            emoji = msg.content.strip()
            
            # Générer un ID
            item_id = name.lower().replace(" ", "_").replace("-", "_")
            
            # Ajouter à la base
            shop_items[item_id] = {
                "id": item_id,
                "name": name,
                "price": price,
                "description": "Nouvel article",
                "emoji": emoji,
                "category": category,
                "stock": -1,
                "type": "one_time",
                "requirements": {"badges": [], "level": 0},
                "active": True
            }
            
            # Sauvegarder
            with open(SHOP_ITEMS_FILE, "w", encoding="utf-8") as f:
                json.dump(shop_items, f, ensure_ascii=False, indent=4)
            
            embed = discord.Embed(
                title="✅ Item Créé",
                description=f"**{name}** ajouté à la boutique !",
                color=discord.Color.green()
            )
            embed.add_field(name="ID", value=item_id, inline=True)
            embed.add_field(name="Prix", value=f"{price} pts", inline=True)
            embed.add_field(name="Catégorie", value=category, inline=True)
            
            await ctx.send(embed=embed)
            
        except asyncio.TimeoutError:
            await ctx.send("⏰ Temps écoulé.")
        except ValueError:
            await ctx.send("❌ Valeur invalide.")
    
    @commands.command(name="shop_remove")
    @commands.has_any_role(*ADMIN_ROLES)
    async def shop_remove_item(self, ctx, item_id: str):
        """Retire un item de la boutique"""
        if item_id not in shop_items:
            await ctx.send("❌ Item introuvable.")
            return
        
        item_name = shop_items[item_id].get("name", item_id)
        del shop_items[item_id]
        
        with open(SHOP_ITEMS_FILE, "w", encoding="utf-8") as f:
            json.dump(shop_items, f, ensure_ascii=False, indent=4)
        
        await ctx.send(f"✅ **{item_name}** retiré de la boutique.")
    
    @commands.command(name="give_item")
    @commands.has_any_role(*ADMIN_ROLES)
    async def give_item(self, ctx, member: discord.Member, *, item_name: str):
        """Donne un item à un membre"""
        item_data = get_shop_item(item_name)
        
        if not item_data:
            await ctx.send("❌ Item introuvable.")
            return
        
        inv = get_user_inventory(member.id)
        item_id = item_name.lower().replace(" ", "_")
        
        # Chercher l'ID correct
        for iid, idata in shop_items.items():
            if idata.get("name", "").lower() == item_name.lower():
                item_id = iid
                break
        
        inv["items"][item_id] = inv["items"].get(item_id, 0) + 1
        sauvegarder_shop()
        
        await ctx.send(f"✅ **{item_data.get('name', item_name)}** donné à {member.mention} !")
    
    @commands.command(name="set_xp", aliases=["set_points"])
    @commands.has_any_role(*ADMIN_ROLES)
    async def set_xp(self, ctx, member: discord.Member, amount: int):
        """Définit l'XP d'un membre"""
        try:
            from community import get_user_stats, sauvegarder_donnees, calculate_level
            stats = get_user_stats(member.id)
            old_xp = stats.get("xp", stats.get("points", 0))
            stats["xp"] = amount
            stats["total_xp"] = amount
            sauvegarder_donnees()
            level = calculate_level(amount)

            await ctx.send(f"✅ XP de {member.mention}: **{old_xp}** → **{amount}** (Niveau {level})")
        except Exception as e:
            await ctx.send(f"❌ Erreur: {e}")

    @commands.command(name="add_xp_admin", aliases=["add_points_admin"])
    @commands.has_any_role(*ADMIN_ROLES)
    async def add_xp_admin(self, ctx, member: discord.Member, amount: int):
        """Ajoute/retire de l'XP à un membre"""
        try:
            from community import add_points, get_user_stats, calculate_level
            final, _ = add_points(member.id, amount, "admin_adjustment")
            stats = get_user_stats(member.id)
            level = calculate_level(stats.get("total_xp", stats.get("total_points_earned", 0)))

            if amount >= 0:
                await ctx.send(f"✅ +{amount} XP pour {member.mention} ! (Nv. {level} — {stats.get('xp', 0):,} XP)")
            else:
                await ctx.send(f"✅ {amount} XP pour {member.mention} ! (Nv. {level} — {stats.get('xp', 0):,} XP)")
        except Exception as e:
            await ctx.send(f"❌ Erreur: {e}")
    
    @commands.command(name="forcedraw")
    @commands.has_any_role(*ADMIN_ROLES)
    async def force_lottery_draw(self, ctx):
        """Force un tirage de loterie"""
        participants = lottery_data.get("participants", [])
        if not participants:
            await ctx.send("❌ Aucun participant dans la loterie.")
            return
        
        await ctx.send("🎰 **Tirage forcé de la loterie...**")
        await self.weekly_lottery()
        
        winner_history = lottery_data.get("winner_history", [])
        if winner_history:
            last = winner_history[-1]
            winner = ctx.guild.get_member(int(last["user_id"]))
            winner_name = winner.mention if winner else "Inconnu"
            await ctx.send(f"🎉 **{winner_name}** a remporté **{last['jackpot']:,}** points !")
    
    @commands.command(name="setjackpot")
    @commands.has_any_role(*ADMIN_ROLES)
    async def set_jackpot(self, ctx, amount: int):
        """Définit le jackpot de la loterie"""
        lottery_data["current_jackpot"] = amount
        sauvegarder_shop()
        await ctx.send(f"✅ Jackpot défini à **{amount:,}** points.")
    
    @commands.command(name="configrole")
    @commands.has_any_role(*ADMIN_ROLES)
    async def config_shop_role(self, ctx, item_id: str, role: discord.Role):
        """Configure un rôle pour un article"""
        if item_id not in shop_items:
            await ctx.send("❌ Article introuvable.")
            return
        
        shop_items[item_id]["role_id"] = role.id
        
        with open(SHOP_ITEMS_FILE, "w", encoding="utf-8") as f:
            json.dump(shop_items, f, ensure_ascii=False, indent=4)
        
        await ctx.send(f"✅ Le rôle {role.mention} a été configuré pour **{shop_items[item_id].get('name', item_id)}**")
    
    @commands.command(name="pending_roles")
    @commands.has_any_role(*ADMIN_ROLES)
    async def list_pending_roles(self, ctx):
        """Liste les rôles en attente d'attribution"""
        pending = []
        
        for user_id, inv in shop_inventory.items():
            if inv.get("pending_roles"):
                member = ctx.guild.get_member(int(user_id))
                for p in inv["pending_roles"]:
                    pending.append({
                        "member": member,
                        "user_id": user_id,
                        "item_id": p["item_id"],
                        "date": p["date"]
                    })
        
        if not pending:
            await ctx.send("✅ Aucun rôle en attente.")
            return
        
        embed = discord.Embed(
            title="⏳ Rôles en attente",
            color=discord.Color.orange()
        )
        
        for p in pending[:20]:
            member_name = p["member"].mention if p["member"] else f"ID: {p['user_id']}"
            embed.add_field(
                name=f"{member_name}",
                value=f"Item: `{p['item_id']}`\nDate: {p['date'][:10]}",
                inline=True
            )
        
        embed.set_footer(text="Utilisez !give_role @user <item_id> pour attribuer")
        await ctx.send(embed=embed)
    
    @commands.command(name="give_role")
    @commands.has_any_role(*ADMIN_ROLES)
    async def give_pending_role(self, ctx, member: discord.Member, item_id: str, role: discord.Role):
        """Attribue un rôle en attente à un membre"""
        inv = get_user_inventory(member.id)
        
        # Vérifier si le rôle est en attente
        pending = inv.get("pending_roles", [])
        found = None
        for i, p in enumerate(pending):
            if p["item_id"] == item_id:
                found = i
                break
        
        if found is None:
            await ctx.send(f"❌ {member.mention} n'a pas de rôle `{item_id}` en attente.")
            return
        
        try:
            await member.add_roles(role, reason="Attribution manuelle - achat boutique")
            
            item_data = get_shop_item(item_id)
            duration = item_data.get("duration_days", 30) if item_data else 30
            expires = datetime.now() + timedelta(days=duration)
            
            inv["active_roles"][item_id] = {
                "role_id": role.id,
                "expires": expires.isoformat(),
                "purchased_at": pending[found]["date"]
            }
            
            del pending[found]
            sauvegarder_shop()
            
            await ctx.send(f"✅ Rôle {role.mention} attribué à {member.mention} jusqu'au {expires.strftime('%d/%m/%Y')}")
            
        except Exception as e:
            await ctx.send(f"❌ Erreur: {e}")


async def setup(bot):
    """Setup pour discord.py 2.0+"""
    await bot.add_cog(ShopSystem(bot))