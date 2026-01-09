# shop.py
# Système de Shop Virtuel
import discord
from discord.ext import commands
import json
import os
import asyncio
from datetime import datetime, timedelta
from config import COLORS

SHOP_FILE = "data/shop_items.json"
PURCHASES_FILE = "data/purchases.json"
USER_INVENTORY_FILE = "data/user_inventory.json"
os.makedirs("data", exist_ok=True)

# Items par défaut du shop
DEFAULT_SHOP_ITEMS = {
    # === RÔLES CUSTOM ===
    "custom_role_color": {
        "id": "custom_role_color",
        "name": "Couleur de Rôle Custom",
        "description": "Obtenez un rôle avec une couleur personnalisée de votre choix",
        "emoji": "🎨",
        "category": "roles",
        "price": 2000,
        "stock": -1,  # -1 = illimité
        "type": "one_time",
        "requirements": {"badges": [], "level": 0},
        "active": True
    },
    "custom_role_name": {
        "id": "custom_role_name",
        "name": "Nom de Rôle Custom",
        "description": "Obtenez un rôle avec un nom personnalisé",
        "emoji": "✏️",
        "category": "roles",
        "price": 3000,
        "stock": -1,
        "type": "one_time",
        "requirements": {"badges": [], "level": 0},
        "active": True
    },
    "vip_role": {
        "id": "vip_role",
        "name": "Rôle VIP",
        "description": "Accès au salon VIP exclusif pendant 30 jours",
        "emoji": "⭐",
        "category": "roles",
        "price": 1500,
        "stock": -1,
        "type": "temporary",
        "duration_days": 30,
        "role_id": None,  # À configurer
        "requirements": {"badges": [], "level": 0},
        "active": True
    },
    
    # === AVANTAGES ===
    "double_points_24h": {
        "id": "double_points_24h",
        "name": "Double Points (24h)",
        "description": "Doublez vos points gagnés pendant 24 heures",
        "emoji": "⚡",
        "category": "boosts",
        "price": 500,
        "stock": -1,
        "type": "consumable",
        "duration_hours": 24,
        "requirements": {"badges": [], "level": 0},
        "active": True
    },
    "highlight_review": {
        "id": "highlight_review",
        "name": "Review en Vedette",
        "description": "Mettez votre prochaine review en avant avec un embed spécial",
        "emoji": "🌟",
        "category": "boosts",
        "price": 300,
        "stock": -1,
        "type": "consumable",
        "requirements": {"badges": [], "level": 0},
        "active": True
    },
    "theory_boost": {
        "id": "theory_boost",
        "name": "Boost Théorie",
        "description": "Votre prochaine théorie apparaît en haut de la liste pendant 48h",
        "emoji": "🚀",
        "category": "boosts",
        "price": 400,
        "stock": -1,
        "type": "consumable",
        "requirements": {"badges": [], "level": 0},
        "active": True
    },
    
    # === COSMÉTIQUES ===
    "profile_banner_slot": {
        "id": "profile_banner_slot",
        "name": "Slot Bannière Profil",
        "description": "Ajoutez une bannière personnalisée à votre profil",
        "emoji": "🖼️",
        "category": "cosmetics",
        "price": 1000,
        "stock": -1,
        "type": "one_time",
        "requirements": {"badges": [], "level": 0},
        "active": True
    },
    "extra_badge_slot": {
        "id": "extra_badge_slot",
        "name": "Slot Badge Supplémentaire",
        "description": "Affichez 1 badge supplémentaire sur votre profil (max +2)",
        "emoji": "🏅",
        "category": "cosmetics",
        "price": 800,
        "stock": -1,
        "type": "one_time",
        "max_purchases": 2,
        "requirements": {"badges": [], "level": 0},
        "active": True
    },
    "nickname_color": {
        "id": "nickname_color",
        "name": "Pseudo Coloré",
        "description": "Choisissez la couleur de votre pseudo (rôle dédié)",
        "emoji": "🌈",
        "category": "cosmetics",
        "price": 1500,
        "stock": -1,
        "type": "one_time",
        "requirements": {"badges": [], "level": 0},
        "active": True
    },
    
    # === PRIVILÈGES ===
    "early_access": {
        "id": "early_access",
        "name": "Accès Anticipé",
        "description": "Accès aux chapitres 1h avant tout le monde (30 jours)",
        "emoji": "⏰",
        "category": "privileges",
        "price": 5000,
        "stock": 10,  # Limité
        "type": "temporary",
        "duration_days": 30,
        "requirements": {"badges": ["reviewer_silver"], "level": 0},
        "active": True
    },
    "suggestion_priority": {
        "id": "suggestion_priority",
        "name": "Suggestion Prioritaire",
        "description": "Votre suggestion de manga sera examinée en priorité",
        "emoji": "📬",
        "category": "privileges",
        "price": 2500,
        "stock": -1,
        "type": "consumable",
        "requirements": {"badges": [], "level": 0},
        "active": True
    },
    
    # === LOTERIE / FUN ===
    "lottery_ticket": {
        "id": "lottery_ticket",
        "name": "Ticket Loterie",
        "description": "Participez à la loterie hebdomadaire (1 ticket = 1 chance)",
        "emoji": "🎟️",
        "category": "lottery",
        "price": 100,
        "stock": -1,
        "type": "consumable",
        "requirements": {"badges": [], "level": 0},
        "active": True
    },
    "mystery_box": {
        "id": "mystery_box",
        "name": "Boîte Mystère",
        "description": "Recevez un item aléatoire (peut être rare !)",
        "emoji": "🎁",
        "category": "lottery",
        "price": 750,
        "stock": -1,
        "type": "consumable",
        "requirements": {"badges": [], "level": 0},
        "active": True
    }
}

# Catégories avec emojis
CATEGORIES = {
    "roles": {"name": "🎭 Rôles", "emoji": "🎭"},
    "boosts": {"name": "⚡ Boosts", "emoji": "⚡"},
    "cosmetics": {"name": "✨ Cosmétiques", "emoji": "✨"},
    "privileges": {"name": "👑 Privilèges", "emoji": "👑"},
    "lottery": {"name": "🎲 Loterie", "emoji": "🎲"}
}

# Données en mémoire
shop_items = {}
purchases_history = {}
user_inventory = {}

def charger_shop():
    """Charge les données du shop"""
    global shop_items, purchases_history, user_inventory
    
    # Items du shop
    if os.path.exists(SHOP_FILE):
        try:
            with open(SHOP_FILE, "r", encoding="utf-8") as f:
                contenu = f.read().strip()
                if contenu:
                    shop_items = json.loads(contenu)
        except Exception as e:
            print(f"❌ Erreur chargement shop: {e}")
            shop_items = DEFAULT_SHOP_ITEMS.copy()
    else:
        shop_items = DEFAULT_SHOP_ITEMS.copy()
    
    # Historique des achats
    if os.path.exists(PURCHASES_FILE):
        try:
            with open(PURCHASES_FILE, "r", encoding="utf-8") as f:
                contenu = f.read().strip()
                if contenu:
                    purchases_history = json.loads(contenu)
        except Exception as e:
            print(f"❌ Erreur chargement purchases: {e}")
    
    # Inventaires utilisateurs
    if os.path.exists(USER_INVENTORY_FILE):
        try:
            with open(USER_INVENTORY_FILE, "r", encoding="utf-8") as f:
                contenu = f.read().strip()
                if contenu:
                    user_inventory = json.loads(contenu)
        except Exception as e:
            print(f"❌ Erreur chargement inventory: {e}")
    
    print(f"✅ Shop chargé ({len(shop_items)} items)")

def sauvegarder_shop():
    """Sauvegarde les données du shop"""
    try:
        with open(SHOP_FILE, "w", encoding="utf-8") as f:
            json.dump(shop_items, f, ensure_ascii=False, indent=4)
        with open(PURCHASES_FILE, "w", encoding="utf-8") as f:
            json.dump(purchases_history, f, ensure_ascii=False, indent=4)
        with open(USER_INVENTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(user_inventory, f, ensure_ascii=False, indent=4)
        print("✅ Shop sauvegardé")
    except Exception as e:
        print(f"❌ Erreur sauvegarde shop: {e}")

def get_user_inventory(user_id):
    """Récupère l'inventaire d'un utilisateur"""
    user_id_str = str(user_id)
    if user_id_str not in user_inventory:
        user_inventory[user_id_str] = {
            "items": {},
            "active_boosts": {},
            "total_spent": 0,
            "purchases_count": 0
        }
    return user_inventory[user_id_str]

def add_to_inventory(user_id, item_id, quantity=1):
    """Ajoute un item à l'inventaire"""
    inv = get_user_inventory(user_id)
    if item_id not in inv["items"]:
        inv["items"][item_id] = 0
    inv["items"][item_id] += quantity
    sauvegarder_shop()

def remove_from_inventory(user_id, item_id, quantity=1):
    """Retire un item de l'inventaire"""
    inv = get_user_inventory(user_id)
    if item_id in inv["items"]:
        inv["items"][item_id] -= quantity
        if inv["items"][item_id] <= 0:
            del inv["items"][item_id]
        sauvegarder_shop()
        return True
    return False


class ShopSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        charger_shop()
    
    @commands.command(name="shop")
    async def show_shop(self, ctx, category: str = None):
        """Affiche le shop"""
        # Import pour récupérer les points
        try:
            from community import get_user_stats
            user_stats = get_user_stats(ctx.author.id)
            user_points = user_stats.get("points", 0)
        except:
            user_points = 0
        
        if category:
            # Afficher une catégorie spécifique
            cat_lower = category.lower()
            cat_key = None
            
            for key, cat_info in CATEGORIES.items():
                if key == cat_lower or cat_info["name"].lower().find(cat_lower) != -1:
                    cat_key = key
                    break
            
            if not cat_key:
                await ctx.send(f"❌ Catégorie '{category}' introuvable.")
                return
            
            items = {k: v for k, v in shop_items.items() 
                    if v.get("category") == cat_key and v.get("active", True)}
            
            if not items:
                await ctx.send(f"❌ Aucun item dans cette catégorie.")
                return
            
            cat_info = CATEGORIES[cat_key]
            
            embed = discord.Embed(
                title=f"🛒 Shop - {cat_info['name']}",
                description=f"💰 Vos points: **{user_points:,}**",
                color=discord.Color.blue(),
                timestamp=datetime.now()
            )
            
            for item_id, item in items.items():
                stock_text = f"Stock: {item['stock']}" if item['stock'] > 0 else "♾️ Illimité" if item['stock'] == -1 else "❌ Rupture"
                can_afford = "✅" if user_points >= item['price'] else "❌"
                
                value = (
                    f"{item['description']}\n"
                    f"💵 **{item['price']:,}** pts {can_afford}\n"
                    f"📦 {stock_text}"
                )
                
                embed.add_field(
                    name=f"{item['emoji']} {item['name']}",
                    value=value,
                    inline=True
                )
            
            embed.set_footer(text=f"Utilisez !buy <nom> pour acheter")
            await ctx.send(embed=embed)
            
        else:
            # Afficher le menu principal
            embed = discord.Embed(
                title="🛒 Shop LanorTrad",
                description=(
                    f"💰 Vos points: **{user_points:,}**\n\n"
                    "Bienvenue dans le shop ! Dépensez vos points gagnés en participant à la communauté.\n\n"
                    "**Catégories disponibles:**"
                ),
                color=discord.Color.gold(),
                timestamp=datetime.now()
            )
            
            for cat_key, cat_info in CATEGORIES.items():
                items_count = len([i for i in shop_items.values() 
                                  if i.get("category") == cat_key and i.get("active", True)])
                
                embed.add_field(
                    name=cat_info["name"],
                    value=f"{items_count} item(s)\n`!shop {cat_key}`",
                    inline=True
                )
            
            embed.add_field(
                name="━━━━━━━━━━━━━━━━━━━━",
                value="",
                inline=False
            )
            
            embed.add_field(
                name="📋 Commandes",
                value=(
                    "`!shop <catégorie>` - Voir une catégorie\n"
                    "`!buy <item>` - Acheter un item\n"
                    "`!inventory` - Voir votre inventaire\n"
                    "`!use <item>` - Utiliser un item"
                ),
                inline=False
            )
            
            embed.set_thumbnail(url=ctx.guild.icon.url if ctx.guild.icon else None)
            embed.set_footer(text="Gagnez des points en laissant des reviews et des théories !")
            
            await ctx.send(embed=embed)
    
    @commands.command(name="buy")
    async def buy_item(self, ctx, *, item_name: str):
        """Achète un item du shop"""
        # Chercher l'item
        found_item = None
        found_id = None
        
        for iid, item in shop_items.items():
            if item["name"].lower() == item_name.lower() or iid.lower() == item_name.lower():
                found_item = item
                found_id = iid
                break
        
        if not found_item:
            await ctx.send(f"❌ Item '{item_name}' introuvable. Utilisez `!shop` pour voir les items disponibles.")
            return
        
        if not found_item.get("active", True):
            await ctx.send("❌ Cet item n'est pas disponible actuellement.")
            return
        
        # Vérifier le stock
        if found_item["stock"] == 0:
            await ctx.send("❌ Cet item est en rupture de stock.")
            return
        
        # Import pour les points
        try:
            from community import get_user_stats, add_points, sauvegarder_donnees
            user_stats = get_user_stats(ctx.author.id)
            user_points = user_stats.get("points", 0)
        except Exception as e:
            await ctx.send(f"❌ Erreur système: {e}")
            return
        
        price = found_item["price"]
        
        # Vérifier les points
        if user_points < price:
            await ctx.send(f"❌ Vous n'avez pas assez de points. (Vous avez **{user_points:,}** pts, il faut **{price:,}** pts)")
            return
        
        # Vérifier les achats max
        inv = get_user_inventory(ctx.author.id)
        if "max_purchases" in found_item:
            current_owned = inv["items"].get(found_id, 0)
            if current_owned >= found_item["max_purchases"]:
                await ctx.send(f"❌ Vous avez atteint la limite d'achat pour cet item ({found_item['max_purchases']} max).")
                return
        
        # Vérifier les requirements
        requirements = found_item.get("requirements", {})
        required_badges = requirements.get("badges", [])
        
        if required_badges:
            try:
                from achievements import get_user_badges
                user_badges = get_user_badges(ctx.author.id)
                for badge_id in required_badges:
                    if badge_id not in user_badges.get("unlocked", []):
                        await ctx.send(f"❌ Vous avez besoin du badge `{badge_id}` pour acheter cet item.")
                        return
            except:
                pass
        
        # Confirmation
        embed_confirm = discord.Embed(
            title="🛒 Confirmation d'Achat",
            description=f"Voulez-vous acheter **{found_item['emoji']} {found_item['name']}** ?",
            color=discord.Color.blue()
        )
        embed_confirm.add_field(name="💵 Prix", value=f"**{price:,}** pts", inline=True)
        embed_confirm.add_field(name="💰 Vos points", value=f"**{user_points:,}** pts", inline=True)
        embed_confirm.add_field(name="💰 Après achat", value=f"**{user_points - price:,}** pts", inline=True)
        embed_confirm.add_field(name="📝 Description", value=found_item["description"], inline=False)
        embed_confirm.set_footer(text="Réagissez ✅ pour confirmer ou ❌ pour annuler")
        
        confirm_msg = await ctx.send(embed=embed_confirm)
        await confirm_msg.add_reaction("✅")
        await confirm_msg.add_reaction("❌")
        
        def check(reaction, user):
            return user == ctx.author and str(reaction.emoji) in ["✅", "❌"] and reaction.message.id == confirm_msg.id
        
        try:
            reaction, _ = await self.bot.wait_for("reaction_add", timeout=30, check=check)
            await confirm_msg.clear_reactions()
            
            if str(reaction.emoji) == "❌":
                await ctx.send("❌ Achat annulé.")
                return
            
            # Effectuer l'achat
            # Retirer les points
            add_points(ctx.author.id, -price)
            sauvegarder_donnees()
            
            # Ajouter à l'inventaire
            add_to_inventory(ctx.author.id, found_id)
            
            # Mettre à jour les stats
            inv["total_spent"] += price
            inv["purchases_count"] += 1
            
            # Réduire le stock si limité
            if found_item["stock"] > 0:
                shop_items[found_id]["stock"] -= 1
            
            # Enregistrer l'achat
            if str(ctx.author.id) not in purchases_history:
                purchases_history[str(ctx.author.id)] = []
            
            purchases_history[str(ctx.author.id)].append({
                "item_id": found_id,
                "item_name": found_item["name"],
                "price": price,
                "date": datetime.now().isoformat()
            })
            
            sauvegarder_shop()
            
            # Vérifier les badges liés aux achats
            try:
                from achievements import check_badges, get_user_badges
                user_badges_data = get_user_badges(ctx.author.id)
                user_badges_data["stats"]["purchases"] = inv["purchases_count"]
                user_badges_data["stats"]["total_spent"] = inv["total_spent"]
                
                unlocked = check_badges(ctx.author.id, user_stats)
                if unlocked:
                    badges_text = ", ".join([f"{b['emoji']} {b['name']}" for b in unlocked])
                    await ctx.send(f"🏆 **Nouveau(x) badge(s) débloqué(s):** {badges_text}")
            except:
                pass
            
            # Confirmation d'achat
            embed_success = discord.Embed(
                title="✅ Achat Réussi !",
                description=f"Vous avez acheté **{found_item['emoji']} {found_item['name']}** !",
                color=discord.Color.green(),
                timestamp=datetime.now()
            )
            embed_success.add_field(name="💵 Dépensé", value=f"**{price:,}** pts", inline=True)
            embed_success.add_field(name="💰 Reste", value=f"**{user_points - price:,}** pts", inline=True)
            
            # Instructions spéciales selon le type
            item_type = found_item.get("type", "consumable")
            if item_type == "consumable":
                embed_success.add_field(
                    name="📋 Utilisation",
                    value=f"Utilisez `!use {found_item['name']}` pour activer cet item.",
                    inline=False
                )
            elif item_type == "one_time":
                embed_success.add_field(
                    name="📋 Information",
                    value="Un membre du staff vous contactera pour configurer votre achat.",
                    inline=False
                )
            
            embed_success.set_footer(text=f"Achat #{inv['purchases_count']}")
            await ctx.send(embed=embed_success)
            
        except asyncio.TimeoutError:
            await confirm_msg.clear_reactions()
            await ctx.send("⏰ Temps écoulé. Achat annulé.")
    
    @commands.command(name="inventory")
    async def show_inventory(self, ctx, member: discord.Member = None):
        """Affiche l'inventaire"""
        member = member or ctx.author
        inv = get_user_inventory(member.id)
        
        embed = discord.Embed(
            title=f"🎒 Inventaire de {member.display_name}",
            description=f"💸 Total dépensé: **{inv['total_spent']:,}** pts",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        
        if not inv["items"]:
            embed.add_field(
                name="Vide",
                value="Aucun item dans l'inventaire.\nVisitez le `!shop` pour acheter !",
                inline=False
            )
        else:
            # Grouper par catégorie
            by_category = {}
            for item_id, quantity in inv["items"].items():
                if item_id in shop_items:
                    item = shop_items[item_id]
                    cat = item.get("category", "other")
                    if cat not in by_category:
                        by_category[cat] = []
                    by_category[cat].append((item, quantity))
            
            for cat, items in by_category.items():
                cat_name = CATEGORIES.get(cat, {}).get("name", cat.capitalize())
                items_text = "\n".join([f"{item['emoji']} {item['name']} x{qty}" for item, qty in items])
                embed.add_field(name=cat_name, value=items_text, inline=True)
        
        # Boosts actifs
        if inv.get("active_boosts"):
            boosts_text = ""
            for boost_id, boost_data in inv["active_boosts"].items():
                expires = datetime.fromisoformat(boost_data["expires"])
                remaining = expires - datetime.now()
                if remaining.total_seconds() > 0:
                    hours = int(remaining.total_seconds() // 3600)
                    minutes = int((remaining.total_seconds() % 3600) // 60)
                    boosts_text += f"⚡ {boost_data['name']} - {hours}h {minutes}m restant\n"
            
            if boosts_text:
                embed.add_field(name="🔥 Boosts Actifs", value=boosts_text, inline=False)
        
        embed.set_thumbnail(url=member.avatar.url if member.avatar else None)
        embed.set_footer(text=f"Utilisez !use <item> pour activer un item")
        
        await ctx.send(embed=embed)
    
    @commands.command(name="use")
    async def use_item(self, ctx, *, item_name: str):
        """Utilise un item de l'inventaire"""
        inv = get_user_inventory(ctx.author.id)
        
        # Chercher l'item
        found_item = None
        found_id = None
        
        for iid, item in shop_items.items():
            if item["name"].lower() == item_name.lower() or iid.lower() == item_name.lower():
                found_item = item
                found_id = iid
                break
        
        if not found_item:
            await ctx.send(f"❌ Item '{item_name}' introuvable.")
            return
        
        if found_id not in inv["items"] or inv["items"][found_id] <= 0:
            await ctx.send(f"❌ Vous ne possédez pas cet item.")
            return
        
        item_type = found_item.get("type", "consumable")
        
        if item_type != "consumable":
            await ctx.send("❌ Cet item ne peut pas être utilisé directement. Contactez un admin si nécessaire.")
            return
        
        # Utiliser l'item
        remove_from_inventory(ctx.author.id, found_id)
        
        # Effets spéciaux selon l'item
        effect_text = ""
        
        if found_id == "double_points_24h":
            # Activer le boost
            expires = datetime.now() + timedelta(hours=24)
            if "active_boosts" not in inv:
                inv["active_boosts"] = {}
            inv["active_boosts"]["double_points"] = {
                "name": found_item["name"],
                "expires": expires.isoformat(),
                "multiplier": 2
            }
            effect_text = "⚡ Vos points seront doublés pendant 24h !"
            
        elif found_id == "highlight_review":
            if "active_boosts" not in inv:
                inv["active_boosts"] = {}
            inv["active_boosts"]["highlight_review"] = {
                "name": found_item["name"],
                "uses": 1
            }
            effect_text = "🌟 Votre prochaine review sera mise en avant !"
            
        elif found_id == "theory_boost":
            if "active_boosts" not in inv:
                inv["active_boosts"] = {}
            inv["active_boosts"]["theory_boost"] = {
                "name": found_item["name"],
                "uses": 1
            }
            effect_text = "🚀 Votre prochaine théorie sera boostée !"
            
        elif found_id == "lottery_ticket":
            # Ajouter à la loterie
            effect_text = "🎟️ Votre ticket a été enregistré pour la prochaine loterie !"
            
        elif found_id == "mystery_box":
            # Ouvrir la boîte mystère
            import random
            possible_rewards = [
                {"type": "points", "amount": 100, "name": "100 points", "emoji": "💰"},
                {"type": "points", "amount": 250, "name": "250 points", "emoji": "💰"},
                {"type": "points", "amount": 500, "name": "500 points", "emoji": "💎"},
                {"type": "points", "amount": 1000, "name": "1000 points", "emoji": "💎", "rare": True},
                {"type": "item", "item_id": "lottery_ticket", "name": "Ticket Loterie", "emoji": "🎟️"},
                {"type": "item", "item_id": "double_points_24h", "name": "Double Points (24h)", "emoji": "⚡"},
            ]
            
            reward = random.choice(possible_rewards)
            
            if reward["type"] == "points":
                try:
                    from community import add_points
                    add_points(ctx.author.id, reward["amount"])
                except:
                    pass
                effect_text = f"🎁 Vous avez gagné **{reward['emoji']} {reward['name']}** !"
            elif reward["type"] == "item":
                add_to_inventory(ctx.author.id, reward["item_id"])
                effect_text = f"🎁 Vous avez gagné **{reward['emoji']} {reward['name']}** !"
        
        else:
            effect_text = f"✅ {found_item['name']} utilisé !"
        
        sauvegarder_shop()
        
        embed = discord.Embed(
            title=f"{found_item['emoji']} Item Utilisé !",
            description=effect_text,
            color=discord.Color.green(),
            timestamp=datetime.now()
        )
        embed.set_footer(text=f"Stock restant: {inv['items'].get(found_id, 0)}")
        
        await ctx.send(embed=embed)
    
    # ==================== ADMIN ====================
    
    @commands.command(name="shop_add")
    @commands.has_any_role(1326417422663680090, 1330147432847114321)
    async def shop_add(self, ctx):
        """(Admin) Ajoute un item au shop de manière interactive"""
        
        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel
        
        try:
            # Nom
            await ctx.send("📝 **Nom de l'item:**")
            msg = await self.bot.wait_for("message", timeout=60, check=check)
            name = msg.content.strip()
            
            # ID
            item_id = name.lower().replace(" ", "_")
            
            # Description
            await ctx.send("📋 **Description:**")
            msg = await self.bot.wait_for("message", timeout=60, check=check)
            description = msg.content.strip()
            
            # Emoji
            await ctx.send("😀 **Emoji:**")
            msg = await self.bot.wait_for("message", timeout=60, check=check)
            emoji = msg.content.strip()
            
            # Catégorie
            cats_list = ", ".join(CATEGORIES.keys())
            await ctx.send(f"📁 **Catégorie:** ({cats_list})")
            msg = await self.bot.wait_for("message", timeout=60, check=check)
            category = msg.content.strip().lower()
            
            # Prix
            await ctx.send("💵 **Prix (en points):**")
            msg = await self.bot.wait_for("message", timeout=60, check=check)
            price = int(msg.content.strip())
            
            # Stock
            await ctx.send("📦 **Stock:** (-1 pour illimité)")
            msg = await self.bot.wait_for("message", timeout=60, check=check)
            stock = int(msg.content.strip())
            
            # Type
            await ctx.send("🔧 **Type:** (one_time, consumable, temporary)")
            msg = await self.bot.wait_for("message", timeout=60, check=check)
            item_type = msg.content.strip().lower()
            
            # Créer l'item
            shop_items[item_id] = {
                "id": item_id,
                "name": name,
                "description": description,
                "emoji": emoji,
                "category": category,
                "price": price,
                "stock": stock,
                "type": item_type,
                "requirements": {"badges": [], "level": 0},
                "active": True
            }
            
            sauvegarder_shop()
            
            embed = discord.Embed(
                title="✅ Item Ajouté !",
                description=f"**{emoji} {name}** a été ajouté au shop.",
                color=discord.Color.green()
            )
            embed.add_field(name="💵 Prix", value=f"{price:,} pts", inline=True)
            embed.add_field(name="📦 Stock", value=str(stock) if stock >= 0 else "Illimité", inline=True)
            
            await ctx.send(embed=embed)
            
        except asyncio.TimeoutError:
            await ctx.send("⏰ Temps écoulé.")
        except ValueError:
            await ctx.send("❌ Valeur invalide.")
    
    @commands.command(name="shop_remove")
    @commands.has_any_role(1326417422663680090, 1330147432847114321)
    async def shop_remove(self, ctx, *, item_name: str):
        """(Admin) Retire un item du shop"""
        found_id = None
        for iid, item in shop_items.items():
            if item["name"].lower() == item_name.lower() or iid.lower() == item_name.lower():
                found_id = iid
                break
        
        if not found_id:
            await ctx.send(f"❌ Item '{item_name}' introuvable.")
            return
        
        item = shop_items[found_id]
        del shop_items[found_id]
        sauvegarder_shop()
        
        await ctx.send(f"✅ Item **{item['emoji']} {item['name']}** supprimé du shop.")
    
    @commands.command(name="give_item")
    @commands.has_any_role(1326417422663680090, 1330147432847114321)
    async def give_item(self, ctx, member: discord.Member, *, item_name: str):
        """(Admin) Donne un item à un membre"""
        found_id = None
        for iid, item in shop_items.items():
            if item["name"].lower() == item_name.lower() or iid.lower() == item_name.lower():
                found_id = iid
                break
        
        if not found_id:
            await ctx.send(f"❌ Item '{item_name}' introuvable.")
            return
        
        add_to_inventory(member.id, found_id)
        item = shop_items[found_id]
        
        await ctx.send(f"✅ **{item['emoji']} {item['name']}** donné à {member.mention} !")
    
    @commands.command(name="set_points")
    @commands.has_any_role(1326417422663680090, 1330147432847114321)
    async def set_points(self, ctx, member: discord.Member, amount: int):
        """(Admin) Définit les points d'un membre"""
        try:
            from community import get_user_stats, sauvegarder_donnees
            stats = get_user_stats(member.id)
            old_points = stats.get("points", 0)
            stats["points"] = amount
            sauvegarder_donnees()
            
            await ctx.send(f"✅ Points de {member.mention}: **{old_points:,}** → **{amount:,}**")
        except Exception as e:
            await ctx.send(f"❌ Erreur: {e}")
    
    @commands.command(name="add_points_admin")
    @commands.has_any_role(1326417422663680090, 1330147432847114321)
    async def add_points_admin(self, ctx, member: discord.Member, amount: int):
        """(Admin) Ajoute des points à un membre"""
        try:
            from community import add_points, get_user_stats
            new_total = add_points(member.id, amount)
            
            action = "ajoutés à" if amount >= 0 else "retirés de"
            await ctx.send(f"✅ **{abs(amount):,}** points {action} {member.mention} (Total: **{new_total:,}**)")
        except Exception as e:
            await ctx.send(f"❌ Erreur: {e}")


async def setup(bot):
    """Setup pour discord.py 2.0+"""
    await bot.add_cog(ShopSystem(bot))
