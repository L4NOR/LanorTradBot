# shop.py
# Système de boutique AMÉLIORÉ : Loterie hebdomadaire, Boosts fonctionnels, Expirations auto
import discord
from discord.ext import commands, tasks
import json
import os
import random
from datetime import datetime, timedelta
from config import COLORS, ADMIN_ROLES

SHOP_FILE = "data/shop_inventory.json"
SHOP_ITEMS_FILE = "data/shop_items.json"
PURCHASES_FILE = "data/purchases.json"
LOTTERY_FILE = "data/lottery.json"
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

# === CONFIGURATION DES RÔLES (À MODIFIER AVEC VOS IDS) ===
SHOP_ROLES = {
    "vip_role": None,  # ID du rôle VIP - À configurer
    "expert_manga_role": None,  # ID du rôle Expert Manga - À configurer
    "theorist_elite_role": None,  # ID du rôle Théoricien d'Élite - À configurer
}

# Loot tables pour mystery boxes
LOOT_COMMON = [
    {"item": "lottery_ticket", "quantity": 1},
    {"item": "points", "quantity": 50},
    {"item": "points", "quantity": 75},
    {"item": "points", "quantity": 100},
]

LOOT_UNCOMMON = [
    {"item": "highlight_review", "quantity": 1},
    {"item": "theory_boost", "quantity": 1},
    {"item": "lottery_ticket", "quantity": 2},
    {"item": "points", "quantity": 150},
    {"item": "points", "quantity": 200},
]

LOOT_RARE = [
    {"item": "double_points_24h", "quantity": 1},
    {"item": "triple_points_12h", "quantity": 1},
    {"item": "lottery_ticket", "quantity": 5},
    {"item": "points", "quantity": 500},
    {"item": "points", "quantity": 750},
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
        
        # Tirer un gagnant
        winner_id = random.choice(lottery_data["participants"])
        jackpot = lottery_data["current_jackpot"]
        
        # Donner les gains
        try:
            from community import add_points
            add_points(int(winner_id), jackpot, "lottery_win")
        except Exception as e:
            print(f"Erreur ajout points loterie: {e}")
        
        # Donner le badge chanceux
        try:
            from achievements import unlock_badge
            unlock_badge(int(winner_id), "lottery_winner")
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
        
        sauvegarder_shop()
    
    @check_expirations.before_loop
    async def before_check_expirations(self):
        await self.bot.wait_until_ready()
    
    # ==================== COMMANDES SHOP ====================
    
    @commands.command(name="shop", aliases=["boutique", "magasin"])
    async def shop(self, ctx, category: str = None):
        """
        Affiche la boutique.
        Catégories: roles, boosts, cosmetics, privileges, lottery, manga_packs, social, utility, limited
        """
        # Récupérer les points de l'utilisateur
        try:
            from community import get_user_stats
            user_stats = get_user_stats(ctx.author.id)
            user_points = user_stats.get("points", 0)
        except:
            user_points = 0
        
        if not shop_items:
            await ctx.send("❌ La boutique est vide. Contactez un administrateur.")
            return
        
        # Filtrer par catégorie si spécifiée
        if category:
            category_lower = category.lower()
            filtered = {k: v for k, v in shop_items.items() 
                       if v.get("category", "").lower() == category_lower and v.get("active", True)}
            if not filtered:
                categories = list(set(v.get("category", "autre") for v in shop_items.values()))
                await ctx.send(f"❌ Catégorie invalide. Catégories disponibles: `{', '.join(categories)}`")
                return
            items = filtered
            title = f"🛒 Boutique - {category.title()}"
        else:
            items = {k: v for k, v in shop_items.items() if v.get("active", True)}
            title = "🛒 Boutique LanorTrad"
        
        embed = discord.Embed(
            title=title,
            description=f"💰 Votre solde: **{user_points:,}** points\n\n"
                       f"Utilisez `!buy <article>` pour acheter\n"
                       f"Utilisez `!shop <catégorie>` pour filtrer",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        
        # Grouper par catégorie
        categories = {}
        for item_id, item in items.items():
            cat = item.get("category", "autre")
            if cat not in categories:
                categories[cat] = []
            categories[cat].append((item_id, item))
        
        category_names = {
            "roles": "👑 Rôles",
            "boosts": "⚡ Boosts",
            "cosmetics": "🎨 Cosmétiques",
            "privileges": "⭐ Privilèges",
            "lottery": "🎰 Loterie",
            "manga_packs": "📚 Packs Manga",
            "social": "💬 Social",
            "utility": "🔧 Utilitaires",
            "limited": "💎 Édition Limitée"
        }
        
        for cat, cat_items in list(categories.items())[:8]:  # Max 8 catégories pour l'embed
            items_text = ""
            for item_id, item in cat_items[:5]:  # Max 5 items par catégorie
                can_afford = "✅" if user_points >= item.get("price", 0) else "❌"
                stock_text = ""
                if item.get("stock", -1) > 0:
                    stock_text = f" (Stock: {item['stock']})"
                elif item.get("stock", -1) == 0:
                    stock_text = " ⛔ Rupture"
                    can_afford = "⛔"
                
                emoji = item.get("emoji", "📦")
                items_text += f"{can_afford} {emoji} **{item.get('name', item_id)}** - {item.get('price', 0):,} pts{stock_text}\n"
            
            if len(cat_items) > 5:
                items_text += f"*...et {len(cat_items) - 5} autres*\n"
            
            embed.add_field(
                name=category_names.get(cat, f"📦 {cat.title()}"),
                value=items_text or "Aucun article",
                inline=True
            )
        
        # Info loterie
        embed.add_field(
            name="🎰 Jackpot Actuel",
            value=f"**{lottery_data.get('current_jackpot', 500):,}** points\n"
                  f"👥 {len(lottery_data.get('participants', []))} participant(s)",
            inline=True
        )
        
        embed.set_footer(text=f"!shop <catégorie> pour filtrer | !item_info <nom> pour les détails")
        await ctx.send(embed=embed)
    
    @commands.command(name="item_info", aliases=["shopinfo"])
    async def item_info(self, ctx, *, item_name: str):
        """Affiche les détails d'un item de la boutique"""
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
            await ctx.send(f"❌ Article introuvable. Utilisez `!shop` pour voir les articles disponibles.")
            return
        
        embed = discord.Embed(
            title=f"{item_data.get('emoji', '📦')} {item_data.get('name', item_id)}",
            description=item_data.get("description", "Pas de description"),
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        
        embed.add_field(name="💰 Prix", value=f"**{item_data.get('price', 0):,}** points", inline=True)
        embed.add_field(name="📁 Catégorie", value=item_data.get("category", "autre").title(), inline=True)
        
        # Stock
        stock = item_data.get("stock", -1)
        if stock == -1:
            stock_text = "♾️ Illimité"
        elif stock == 0:
            stock_text = "⛔ Rupture de stock"
        else:
            stock_text = f"📦 {stock} restant(s)"
        embed.add_field(name="📊 Stock", value=stock_text, inline=True)
        
        # Type
        item_type = item_data.get("type", "one_time")
        type_names = {
            "one_time": "🔒 Achat unique",
            "consumable": "🔄 Consommable",
            "temporary": "⏰ Temporaire"
        }
        embed.add_field(name="🏷️ Type", value=type_names.get(item_type, item_type), inline=True)
        
        # Durée si temporaire
        if item_data.get("duration_days"):
            embed.add_field(name="⏱️ Durée", value=f"{item_data['duration_days']} jour(s)", inline=True)
        elif item_data.get("duration_hours"):
            embed.add_field(name="⏱️ Durée", value=f"{item_data['duration_hours']} heure(s)", inline=True)
        
        # Prérequis
        requirements = item_data.get("requirements", {})
        if requirements.get("badges"):
            embed.add_field(name="🏅 Badges requis", value=", ".join(requirements["badges"]), inline=False)
        
        embed.set_footer(text=f"ID: {item_id} | !buy {item_id}")
        await ctx.send(embed=embed)
    
    @commands.command(name="buy", aliases=["acheter"])
    async def buy(self, ctx, *, item_name: str):
        """Achète un article de la boutique"""
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
            await ctx.send(f"❌ Article introuvable. Utilisez `!shop` pour voir les articles disponibles.")
            return
        
        # Vérifier si actif
        if not item_data.get("active", True):
            await ctx.send(f"❌ Cet article n'est plus disponible.")
            return
        
        # Vérifier le stock
        if item_data.get("stock", -1) == 0:
            await ctx.send(f"❌ Cet article est en rupture de stock.")
            return
        
        # Vérifier les points
        try:
            from community import get_user_stats, add_points
            user_stats = get_user_stats(ctx.author.id)
            user_points = user_stats.get("points", 0)
        except Exception as e:
            await ctx.send(f"❌ Erreur système: {e}")
            return
        
        price = item_data.get("price", 0)
        
        if user_points < price:
            await ctx.send(f"❌ Vous n'avez pas assez de points.\n"
                          f"💰 Vous avez: **{user_points:,}** pts\n"
                          f"💸 Prix: **{price:,}** pts\n"
                          f"❌ Il vous manque: **{price - user_points:,}** pts")
            return
        
        # Vérifier les prérequis
        requirements = item_data.get("requirements", {})
        if requirements.get("badges"):
            try:
                from achievements import get_user_badges
                user_badges = get_user_badges(ctx.author.id)
                unlocked = user_badges.get("unlocked", [])
                missing = [b for b in requirements["badges"] if b not in unlocked]
                if missing:
                    await ctx.send(f"❌ Vous n'avez pas les badges requis: `{', '.join(missing)}`")
                    return
            except:
                pass
        
        # Vérifier max_purchases
        inv = get_user_inventory(ctx.author.id)
        if item_data.get("max_purchases"):
            current_purchases = sum(1 for p in inv.get("purchase_history", []) if p.get("item_id") == item_id)
            if current_purchases >= item_data["max_purchases"]:
                await ctx.send(f"❌ Vous avez atteint la limite d'achat pour cet article ({item_data['max_purchases']} max).")
                return
        
        # Déduire les points
        add_points(ctx.author.id, -price, f"achat_{item_id}")
        
        # Mettre à jour le stock
        if item_data.get("stock", -1) > 0:
            shop_items[item_id]["stock"] -= 1
            # Sauvegarder le fichier items
            with open(SHOP_ITEMS_FILE, "w", encoding="utf-8") as f:
                json.dump(shop_items, f, ensure_ascii=False, indent=4)
        
        # Mettre à jour l'inventaire
        inv["total_spent"] = inv.get("total_spent", 0) + price
        inv["purchase_history"].append({
            "item_id": item_id,
            "price": price,
            "date": datetime.now().isoformat()
        })
        
        # Créer l'embed de résultat
        result_embed = discord.Embed(
            title=f"✅ Achat Réussi !",
            description=f"Vous avez acheté **{item_data.get('name', item_id)}**",
            color=discord.Color.green(),
            timestamp=datetime.now()
        )
        
        category = item_data.get("category", "")
        item_type = item_data.get("type", "one_time")
        
        # === TRAITEMENT SELON LA CATÉGORIE ===
        
        # BOOSTS
        if category == "boosts":
            # Gérer les packs
            if "pack" in item_id.lower() or "weekly_boost_pack" in item_id:
                # Ajouter plusieurs items
                activate_boost(ctx.author.id, "double_points", {"duration_hours": 24})
                activate_boost(ctx.author.id, "double_points_2", {"duration_hours": 24})
                activate_boost(ctx.author.id, "highlight_review", {"one_time": True})
                activate_boost(ctx.author.id, "theory_boost", {"one_time": True})
                result_embed.add_field(
                    name="📦 Contenu du Pack",
                    value="• 2x Double Points 24h\n• 1x Review en Vedette\n• 1x Boost Théorie",
                    inline=False
                )
            else:
                activate_boost(ctx.author.id, item_id, item_data)
                
                if item_data.get("duration_hours"):
                    duration = item_data.get("duration_hours", 24)
                    expires = datetime.now() + timedelta(hours=duration)
                    result_embed.add_field(
                        name="⏰ Durée",
                        value=f"Actif jusqu'au {expires.strftime('%d/%m à %H:%M')}",
                        inline=True
                    )
                else:
                    result_embed.add_field(
                        name="⚡ Activation",
                        value="S'activera à votre prochaine action !",
                        inline=False
                    )
        
        # LOTERIE
        elif category == "lottery":
            tickets = 1
            if "x5" in item_id or "pack_5" in item_id:
                tickets = 5
            
            inv["lottery_tickets"] = inv.get("lottery_tickets", 0) + tickets
            
            for _ in range(tickets):
                lottery_data["participants"].append(str(ctx.author.id))
            
            # Augmenter le jackpot
            lottery_data["current_jackpot"] = lottery_data.get("current_jackpot", 500) + int(price * 0.1 * tickets)
            
            result_embed.add_field(
                name="🎰 Tickets",
                value=f"+{tickets} ticket(s)\nTotal en jeu: **{lottery_data['participants'].count(str(ctx.author.id))}**",
                inline=True
            )
            result_embed.add_field(
                name="💰 Jackpot",
                value=f"**{lottery_data['current_jackpot']:,}** pts",
                inline=True
            )
        
        # RÔLES
        elif category == "roles":
            role_id = item_data.get("role_id") or SHOP_ROLES.get(item_id)
            
            if item_data.get("custom_color") or "color" in item_id.lower():
                inv["pending_color_role"] = {
                    "purchased_at": datetime.now().isoformat(),
                    "duration_days": item_data.get("duration_days", 30)
                }
                result_embed.add_field(
                    name="🎨 Couleur Custom",
                    value="Utilisez `!setcolor #HEXCODE` pour définir votre couleur !",
                    inline=False
                )
            elif role_id:
                role = ctx.guild.get_role(role_id)
                if role:
                    try:
                        await ctx.author.add_roles(role, reason="Achat boutique")
                        
                        duration = item_data.get("duration_days", 30)
                        expires = datetime.now() + timedelta(days=duration)
                        
                        inv["active_roles"][item_id] = {
                            "role_id": role_id,
                            "expires": expires.isoformat(),
                            "purchased_at": datetime.now().isoformat()
                        }
                        
                        result_embed.add_field(
                            name="👑 Rôle Activé",
                            value=f"{role.mention}\nExpire le {expires.strftime('%d/%m/%Y')}",
                            inline=False
                        )
                    except Exception as e:
                        result_embed.add_field(name="⚠️ Erreur", value=f"Impossible d'ajouter le rôle: {e}", inline=False)
                else:
                    result_embed.add_field(
                        name="⚠️ Configuration",
                        value="Rôle non configuré. Contactez un admin pour recevoir votre rôle.",
                        inline=False
                    )
                    # Enregistrer pour attribution manuelle
                    inv["pending_roles"] = inv.get("pending_roles", [])
                    inv["pending_roles"].append({"item_id": item_id, "date": datetime.now().isoformat()})
            else:
                result_embed.add_field(
                    name="⚠️ Configuration",
                    value="Rôle non configuré. Contactez un admin.",
                    inline=False
                )
                inv["pending_roles"] = inv.get("pending_roles", [])
                inv["pending_roles"].append({"item_id": item_id, "date": datetime.now().isoformat()})
        
        # MYSTERY BOX
        elif "mystery" in category or "mystery" in item_id.lower():
            loot = self.open_mystery_box(item_data)
            
            result_embed.title = f"📦 Mystery Box Ouverte !"
            
            if loot["type"] == "points":
                add_points(ctx.author.id, loot["quantity"], "mystery_box")
                result_embed.add_field(
                    name="💰 Vous avez obtenu",
                    value=f"**{loot['quantity']}** points !",
                    inline=False
                )
            elif loot["type"] == "item":
                won_item = get_shop_item(loot["item_id"])
                if won_item:
                    if won_item.get("category") == "boosts":
                        activate_boost(ctx.author.id, loot["item_id"], won_item)
                    elif won_item.get("category") == "lottery":
                        inv["lottery_tickets"] = inv.get("lottery_tickets", 0) + loot.get("quantity", 1)
                        for _ in range(loot.get("quantity", 1)):
                            lottery_data["participants"].append(str(ctx.author.id))
                    else:
                        inv["items"][loot["item_id"]] = inv["items"].get(loot["item_id"], 0) + loot.get("quantity", 1)
                    
                    result_embed.add_field(
                        name=f"🎁 Vous avez obtenu",
                        value=f"**{won_item.get('name', loot['item_id'])}** x{loot.get('quantity', 1)} !",
                        inline=False
                    )
            
            rarity_colors = {"common": "⬜", "uncommon": "🟩", "rare": "🟦", "epic": "🟪", "legendary": "🟨"}
            result_embed.add_field(
                name="🎲 Rareté",
                value=f"{rarity_colors.get(loot['rarity'], '⬜')} **{loot['rarity'].upper()}**",
                inline=True
            )
        
        # COLLECTIBLES / BADGES
        elif category == "limited" or "badge" in item_id.lower():
            badge_id = item_data.get("badge_id") or item_id.replace("_badge", "")
            try:
                from achievements import unlock_badge
                result = unlock_badge(ctx.author.id, badge_id)
                if result:
                    result_embed.add_field(
                        name="🏅 Badge Débloqué",
                        value=f"Vous avez maintenant le badge **{item_data.get('name', item_id)}** !",
                        inline=False
                    )
                else:
                    result_embed.add_field(
                        name="⚠️ Note",
                        value="Vous possédez déjà ce badge.",
                        inline=False
                    )
            except Exception as e:
                inv["items"][item_id] = inv["items"].get(item_id, 0) + 1
                result_embed.add_field(
                    name="📦 Item ajouté",
                    value=f"**{item_data.get('name', item_id)}** ajouté à votre inventaire.",
                    inline=False
                )
        
        # AUTRES (cosmetics, privileges, etc.)
        else:
            inv["items"][item_id] = inv["items"].get(item_id, 0) + 1
            result_embed.add_field(
                name="📦 Item ajouté",
                value=f"**{item_data.get('name', item_id)}** ajouté à votre inventaire.\n"
                      f"Contactez un admin pour l'activer si nécessaire.",
                inline=False
            )
        
        # Vérifier le badge big_spender
        if inv.get("total_spent", 0) >= 5000:
            try:
                from achievements import unlock_badge
                unlock_badge(ctx.author.id, "big_spender")
            except:
                pass
        
        sauvegarder_shop()
        
        # Afficher le nouveau solde
        try:
            user_stats = get_user_stats(ctx.author.id)
            result_embed.set_footer(text=f"💰 Nouveau solde: {user_stats.get('points', 0):,} points")
        except:
            pass
        
        result_embed.set_thumbnail(url=ctx.author.avatar.url if ctx.author.avatar else None)
        await ctx.send(embed=result_embed)
    
    def open_mystery_box(self, item_data):
        """Ouvre une mystery box et retourne le loot"""
        loot_table = item_data.get("loot_table", {"common": 60, "uncommon": 30, "rare": 10})
        
        roll = random.randint(1, 100)
        
        common_chance = loot_table.get("common", 60)
        uncommon_chance = loot_table.get("uncommon", 30)
        
        if roll <= common_chance:
            rarity = "common"
            loot_pool = LOOT_COMMON
        elif roll <= common_chance + uncommon_chance:
            rarity = "uncommon"
            loot_pool = LOOT_UNCOMMON
        else:
            rarity = "rare"
            loot_pool = LOOT_RARE
        
        # Pour les box légendaires, améliorer le loot
        if "legendary" in item_data.get("id", "").lower():
            if rarity == "common":
                rarity = "uncommon"
                loot_pool = LOOT_UNCOMMON
            elif rarity == "uncommon":
                rarity = "rare"
                loot_pool = LOOT_RARE
        
        loot = random.choice(loot_pool)
        
        if loot["item"] == "points":
            return {
                "type": "points",
                "quantity": loot["quantity"],
                "rarity": rarity
            }
        else:
            return {
                "type": "item",
                "item_id": loot["item"],
                "quantity": loot.get("quantity", 1),
                "rarity": rarity
            }
    
    @commands.command(name="use", aliases=["utiliser"])
    async def use_item(self, ctx, *, item_name: str):
        """Utilise un item de votre inventaire"""
        inv = get_user_inventory(ctx.author.id)
        items = inv.get("items", {})
        
        # Trouver l'item
        item_id = None
        for iid in items.keys():
            if iid.lower() == item_name.lower().replace(" ", "_"):
                item_id = iid
                break
            item_data = get_shop_item(iid)
            if item_data and item_data.get("name", "").lower() == item_name.lower():
                item_id = iid
                break
        
        if not item_id or items.get(item_id, 0) <= 0:
            await ctx.send(f"❌ Vous n'avez pas cet item dans votre inventaire.")
            return
        
        item_data = get_shop_item(item_id)
        if not item_data:
            await ctx.send(f"❌ Item non reconnu.")
            return
        
        # Utiliser l'item
        items[item_id] -= 1
        if items[item_id] <= 0:
            del items[item_id]
        
        # Activer l'effet
        if item_data.get("category") == "boosts":
            activate_boost(ctx.author.id, item_id, item_data)
        
        sauvegarder_shop()
        
        embed = discord.Embed(
            title="✅ Item Utilisé",
            description=f"Vous avez utilisé **{item_data.get('name', item_id)}**",
            color=discord.Color.green()
        )
        
        if item_data.get("duration_hours"):
            expires = datetime.now() + timedelta(hours=item_data["duration_hours"])
            embed.add_field(name="⏰ Actif jusqu'à", value=expires.strftime("%d/%m à %H:%M"))
        
        await ctx.send(embed=embed)
    
    @commands.command(name="lottery", aliases=["loto", "loterie"])
    async def lottery_info(self, ctx):
        """Affiche les infos de la loterie"""
        embed = discord.Embed(
            title="🎰 Loterie Hebdomadaire",
            description="Achetez des tickets pour participer au tirage !",
            color=discord.Color.gold(),
            timestamp=datetime.now()
        )
        
        embed.add_field(
            name="💰 Jackpot Actuel",
            value=f"**{lottery_data.get('current_jackpot', 500):,}** points",
            inline=True
        )
        
        participants = lottery_data.get("participants", [])
        embed.add_field(
            name="👥 Participants",
            value=f"**{len(participants)}** tickets en jeu",
            inline=True
        )
        
        # Tickets de l'utilisateur
        user_tickets = participants.count(str(ctx.author.id))
        
        embed.add_field(
            name="🎫 Vos Tickets",
            value=f"**{user_tickets}** ticket(s) en jeu",
            inline=True
        )
        
        # Probabilité de gain
        if len(participants) > 0 and user_tickets > 0:
            win_chance = (user_tickets / len(participants)) * 100
            embed.add_field(
                name="📊 Vos Chances",
                value=f"**{win_chance:.1f}%**",
                inline=True
            )
        
        # Dernier gagnant
        winner_history = lottery_data.get("winner_history", [])
        if winner_history:
            last_winner = winner_history[-1]
            member = ctx.guild.get_member(int(last_winner["user_id"])) if ctx.guild else None
            winner_name = member.display_name if member else "Inconnu"
            
            embed.add_field(
                name="🏆 Dernier Gagnant",
                value=f"**{winner_name}**\n{last_winner['jackpot']:,} pts",
                inline=True
            )
        
        embed.add_field(
            name="🛒 Acheter des Tickets",
            value="`!buy lottery_ticket` (50 pts)\n`!buy lottery_ticket_pack_5` (200 pts)",
            inline=False
        )
        
        embed.set_footer(text="Tirage automatique chaque semaine !")
        await ctx.send(embed=embed)
    
    @commands.command(name="inventory", aliases=["inv", "inventaire"])
    async def inventory(self, ctx, member: discord.Member = None):
        """Affiche l'inventaire d'un membre"""
        member = member or ctx.author
        inv = get_user_inventory(member.id)
        
        embed = discord.Embed(
            title=f"🎒 Inventaire de {member.display_name}",
            color=member.color if member.color != discord.Color.default() else discord.Color.blue(),
            timestamp=datetime.now()
        )
        
        # Boosts actifs
        active_boosts = inv.get("active_boosts", {})
        if active_boosts:
            boosts_text = ""
            for boost_id, boost_data in list(active_boosts.items()):
                item_data = get_shop_item(boost_id)
                item_name = item_data.get("name", boost_id) if item_data else boost_id
                
                if boost_data.get("one_time"):
                    boosts_text += f"⚡ **{item_name}** - Prêt à l'emploi\n"
                elif "expires" in boost_data:
                    try:
                        expires = datetime.fromisoformat(boost_data["expires"])
                        remaining = expires - datetime.now()
                        if remaining.total_seconds() > 0:
                            hours = int(remaining.total_seconds() // 3600)
                            mins = int((remaining.total_seconds() % 3600) // 60)
                            boosts_text += f"⚡ **{item_name}** - {hours}h{mins:02d} restantes\n"
                    except:
                        pass
            
            if boosts_text:
                embed.add_field(name="🚀 Boosts Actifs", value=boosts_text, inline=False)
        
        # Rôles temporaires
        active_roles = inv.get("active_roles", {})
        if active_roles:
            roles_text = ""
            for role_key, role_data in list(active_roles.items()):
                try:
                    expires = datetime.fromisoformat(role_data["expires"])
                    days_left = (expires - datetime.now()).days
                    if days_left >= 0:
                        role = ctx.guild.get_role(role_data.get("role_id", 0)) if ctx.guild else None
                        role_name = role.name if role else role_key
                        roles_text += f"👑 **{role_name}** - {days_left} jour(s)\n"
                except:
                    pass
            
            if roles_text:
                embed.add_field(name="👑 Rôles Temporaires", value=roles_text, inline=False)
        
        # Tickets loterie
        user_tickets = lottery_data.get("participants", []).count(str(member.id))
        embed.add_field(
            name="🎰 Loterie",
            value=f"**{user_tickets}** ticket(s) en jeu",
            inline=True
        )
        
        # Items
        items = inv.get("items", {})
        if items:
            items_text = ""
            for item_id, qty in list(items.items())[:10]:
                item_data = get_shop_item(item_id)
                item_name = item_data.get("name", item_id) if item_data else item_id
                emoji = item_data.get("emoji", "📦") if item_data else "📦"
                items_text += f"{emoji} **{item_name}** x{qty}\n"
            
            if len(items) > 10:
                items_text += f"*...et {len(items) - 10} autres*"
            
            embed.add_field(name="📦 Items", value=items_text, inline=False)
        
        # Rôles en attente
        pending_roles = inv.get("pending_roles", [])
        if pending_roles:
            pending_text = "\n".join([f"• {p['item_id']}" for p in pending_roles[:5]])
            embed.add_field(name="⏳ Rôles en attente", value=pending_text, inline=False)
        
        # Stats d'achat
        history = inv.get("purchase_history", [])
        total_spent = inv.get("total_spent", 0)
        embed.add_field(
            name="📊 Statistiques",
            value=f"Achats: **{len(history)}**\nTotal dépensé: **{total_spent:,}** pts",
            inline=False
        )
        
        embed.set_thumbnail(url=member.avatar.url if member.avatar else None)
        await ctx.send(embed=embed)
    
    @commands.command(name="setcolor")
    async def set_custom_color(self, ctx, color: str):
        """Définit votre couleur custom (après achat)"""
        inv = get_user_inventory(ctx.author.id)
        
        if "pending_color_role" not in inv:
            await ctx.send("❌ Vous n'avez pas de couleur custom en attente. Achetez-en une avec `!buy custom_role_color`")
            return
        
        color = color.strip("#")
        try:
            color_int = int(color, 16)
        except ValueError:
            await ctx.send("❌ Couleur invalide. Utilisez le format hex: `!setcolor #FF5500`")
            return
        
        try:
            # Créer le rôle
            role = await ctx.guild.create_role(
                name=f"🎨 {ctx.author.display_name}",
                color=discord.Color(color_int),
                reason="Couleur custom achetée"
            )
            
            # Positionner le rôle (au-dessus des rôles normaux)
            try:
                bot_role = ctx.guild.me.top_role
                await role.edit(position=bot_role.position - 1)
            except:
                pass
            
            await ctx.author.add_roles(role)
            
            duration = inv["pending_color_role"].get("duration_days", 30)
            expires = datetime.now() + timedelta(days=duration)
            
            inv["active_roles"]["custom_color"] = {
                "role_id": role.id,
                "expires": expires.isoformat(),
                "color": color
            }
            
            del inv["pending_color_role"]
            sauvegarder_shop()
            
            embed = discord.Embed(
                title="🎨 Couleur Appliquée !",
                description=f"Votre nouvelle couleur: **#{color}**",
                color=discord.Color(color_int)
            )
            embed.add_field(name="⏰ Expire le", value=expires.strftime("%d/%m/%Y"))
            
            await ctx.send(embed=embed)
            
        except discord.Forbidden:
            await ctx.send("❌ Je n'ai pas la permission de créer des rôles.")
        except Exception as e:
            await ctx.send(f"❌ Erreur: {e}")
    
    # ==================== COMMANDES ADMIN ====================
    
    @commands.command(name="shop_add")
    @commands.has_any_role(*ADMIN_ROLES)
    async def shop_add_item(self, ctx):
        """Ajoute un item à la boutique (interactif)"""
        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel
        
        try:
            await ctx.send("📦 **Création d'un item** - Entrez l'ID de l'item (ex: `super_boost`):")
            msg = await self.bot.wait_for("message", timeout=60, check=check)
            item_id = msg.content.strip().lower().replace(" ", "_")
            
            await ctx.send("📝 Entrez le nom affiché:")
            msg = await self.bot.wait_for("message", timeout=60, check=check)
            name = msg.content.strip()
            
            await ctx.send("📋 Entrez la description:")
            msg = await self.bot.wait_for("message", timeout=120, check=check)
            description = msg.content.strip()
            
            await ctx.send("💰 Entrez le prix (en points):")
            msg = await self.bot.wait_for("message", timeout=60, check=check)
            price = int(msg.content.strip())
            
            await ctx.send("📁 Entrez la catégorie (roles/boosts/cosmetics/privileges/lottery/limited):")
            msg = await self.bot.wait_for("message", timeout=60, check=check)
            category = msg.content.strip().lower()
            
            await ctx.send("😀 Entrez l'emoji (ex: 🚀):")
            msg = await self.bot.wait_for("message", timeout=60, check=check)
            emoji = msg.content.strip()
            
            # Créer l'item
            shop_items[item_id] = {
                "id": item_id,
                "name": name,
                "description": description,
                "emoji": emoji,
                "category": category,
                "price": price,
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
    
    @commands.command(name="set_points")
    @commands.has_any_role(*ADMIN_ROLES)
    async def set_points(self, ctx, member: discord.Member, amount: int):
        """Définit les points d'un membre"""
        try:
            from community import get_user_stats, sauvegarder_donnees
            stats = get_user_stats(member.id)
            old_points = stats.get("points", 0)
            stats["points"] = amount
            sauvegarder_donnees()
            
            await ctx.send(f"✅ Points de {member.mention}: **{old_points}** → **{amount}**")
        except Exception as e:
            await ctx.send(f"❌ Erreur: {e}")
    
    @commands.command(name="add_points_admin")
    @commands.has_any_role(*ADMIN_ROLES)
    async def add_points_admin(self, ctx, member: discord.Member, amount: int):
        """Ajoute/retire des points à un membre"""
        try:
            from community import add_points, get_user_stats
            final, _ = add_points(member.id, amount, "admin_adjustment")
            stats = get_user_stats(member.id)
            
            if amount >= 0:
                await ctx.send(f"✅ +{amount} points pour {member.mention} ! (Total: **{stats['points']:,}**)")
            else:
                await ctx.send(f"✅ {amount} points pour {member.mention} ! (Total: **{stats['points']:,}**)")
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