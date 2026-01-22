# shop.py
# Système de boutique AMÉLIORÉ : Loterie hebdomadaire, Boosts fonctionnels, Expirations auto
import discord
from discord.ext import commands, tasks
import json
import os
import random
from datetime import datetime, timedelta
from config import COLORS

SHOP_FILE = "data/shop_inventory.json"
LOTTERY_FILE = "data/lottery.json"
os.makedirs("data", exist_ok=True)

# Inventaires des utilisateurs
shop_inventory = {}

# Données de la loterie
lottery_data = {
    "current_jackpot": 500,
    "participants": [],
    "last_draw": None,
    "winner_history": []
}

# Articles de la boutique
SHOP_ITEMS = {
    # === BOOSTS DE POINTS ===
    "double_points": {
        "name": "🚀 Double Points 24h",
        "description": "Double tous vos gains de points pendant 24 heures",
        "price": 200,
        "category": "boost",
        "duration_hours": 24,
        "multiplier": 2,
        "max_stock": 99,
        "icon": "🚀"
    },
    "triple_points": {
        "name": "⚡ Triple Points 12h",
        "description": "Triple tous vos gains pendant 12 heures !",
        "price": 400,
        "category": "boost",
        "duration_hours": 12,
        "multiplier": 3,
        "max_stock": 99,
        "icon": "⚡"
    },
    
    # === BOOSTS COMMUNAUTAIRES ===
    "highlight_review": {
        "name": "🌟 Review en Vedette",
        "description": "Votre prochaine review sera mise en avant",
        "price": 100,
        "category": "boost",
        "one_time_use": True,
        "icon": "🌟"
    },
    "theory_boost": {
        "name": "💡 Boost Théorie",
        "description": "Votre prochaine théorie sera épinglée 48h",
        "price": 150,
        "category": "boost",
        "one_time_use": True,
        "icon": "💡"
    },
    "super_vote": {
        "name": "🗳️ Super Vote",
        "description": "Votre prochain vote compte triple",
        "price": 75,
        "category": "boost",
        "one_time_use": True,
        "icon": "🗳️"
    },
    
    # === LOTERIE ===
    "lottery_ticket": {
        "name": "🎰 Ticket Loterie",
        "description": "Participez au tirage hebdomadaire !",
        "price": 50,
        "category": "lottery",
        "icon": "🎰"
    },
    "lottery_ticket_x5": {
        "name": "🎰 Pack 5 Tickets",
        "description": "5 tickets pour le prix de 4 !",
        "price": 200,
        "category": "lottery",
        "tickets": 5,
        "icon": "🎰"
    },
    
    # === RÔLES TEMPORAIRES ===
    "vip_role_7d": {
        "name": "👑 Rôle VIP 7 jours",
        "description": "Accédez au salon VIP pendant 7 jours",
        "price": 500,
        "category": "role",
        "duration_days": 7,
        "role_id": None,  # À configurer
        "icon": "👑"
    },
    "vip_role_30d": {
        "name": "👑 Rôle VIP 30 jours",
        "description": "Accédez au salon VIP pendant 30 jours",
        "price": 1500,
        "category": "role",
        "duration_days": 30,
        "role_id": None,  # À configurer
        "icon": "👑"
    },
    "color_role_30d": {
        "name": "🎨 Couleur Custom 30j",
        "description": "Un rôle coloré personnalisé pendant 30 jours",
        "price": 800,
        "category": "role",
        "duration_days": 30,
        "custom_color": True,
        "icon": "🎨"
    },
    
    # === MYSTERY BOX ===
    "mystery_box_common": {
        "name": "📦 Mystery Box",
        "description": "Contient un item aléatoire",
        "price": 150,
        "category": "mystery",
        "icon": "📦",
        "loot_table": {
            "common": 60,    # 60% chance
            "uncommon": 30,  # 30% chance
            "rare": 10       # 10% chance
        }
    },
    "mystery_box_rare": {
        "name": "💎 Mystery Box Rare",
        "description": "Meilleures chances d'items rares !",
        "price": 400,
        "category": "mystery",
        "icon": "💎",
        "loot_table": {
            "common": 20,    # 20% chance
            "uncommon": 50,  # 50% chance
            "rare": 30       # 30% chance
        }
    },
    
    # === COLLECTIBLES ===
    "badge_collector": {
        "name": "🏅 Badge Collectionneur",
        "description": "Un badge exclusif pour votre profil",
        "price": 1000,
        "category": "collectible",
        "badge_id": "collector",
        "icon": "🏅"
    }
}

# Loot tables pour mystery boxes
LOOT_COMMON = [
    {"item": "lottery_ticket", "quantity": 1},
    {"item": "points", "quantity": 50},
    {"item": "points", "quantity": 75},
]

LOOT_UNCOMMON = [
    {"item": "highlight_review", "quantity": 1},
    {"item": "theory_boost", "quantity": 1},
    {"item": "lottery_ticket", "quantity": 2},
    {"item": "points", "quantity": 150},
]

LOOT_RARE = [
    {"item": "double_points", "quantity": 1},
    {"item": "triple_points", "quantity": 1},
    {"item": "lottery_ticket", "quantity": 5},
    {"item": "points", "quantity": 500},
]

def charger_shop():
    """Charge les données de la boutique"""
    global shop_inventory, lottery_data
    
    if os.path.exists(SHOP_FILE):
        try:
            with open(SHOP_FILE, "r", encoding="utf-8") as f:
                contenu = f.read().strip()
                if contenu:
                    shop_inventory.update(json.loads(contenu))
            print("✅ Inventaires shop chargés")
        except Exception as e:
            print(f"❌ Erreur chargement shop: {e}")
    
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
            "lottery_tickets": 0
        }
    return shop_inventory[user_id_str]

def activate_boost(user_id, boost_id, item_data):
    """Active un boost pour un utilisateur"""
    inv = get_user_inventory(user_id)
    
    if "active_boosts" not in inv:
        inv["active_boosts"] = {}
    
    if item_data.get("one_time_use"):
        # Boost à usage unique (s'active au prochain usage)
        inv["active_boosts"][boost_id] = {
            "activated_at": datetime.now().isoformat(),
            "one_time": True
        }
    else:
        # Boost temporaire
        duration = item_data.get("duration_hours", 24)
        expires = datetime.now() + timedelta(hours=duration)
        
        inv["active_boosts"][boost_id] = {
            "activated_at": datetime.now().isoformat(),
            "expires": expires.isoformat(),
            "multiplier": item_data.get("multiplier", 2)
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
        lottery_data["participants"] = []
        lottery_data["current_jackpot"] = 500
        lottery_data["last_draw"] = datetime.now().isoformat()
        
        sauvegarder_shop()
        
        # Annoncer (chercher un salon approprié)
        for guild in self.bot.guilds:
            # Chercher un salon général ou annonces
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
                    color=discord.Color.gold()
                )
                embed.add_field(name="💰 Gains", value=f"**{jackpot:,}** points !", inline=True)
                embed.add_field(name="👥 Participants", value=str(len(lottery_data["winner_history"][-1]["participants_count"])), inline=True)
                
                try:
                    await channel.send(embed=embed)
                except:
                    pass
    
    @weekly_lottery.before_loop
    async def before_lottery(self):
        await self.bot.wait_until_ready()
    
    # ==================== EXPIRATION AUTO ====================
    
    @tasks.loop(hours=1)  # Vérifier chaque heure
    async def check_expirations(self):
        """Vérifie et retire les rôles/boosts expirés"""
        now = datetime.now()
        
        for user_id, inv in shop_inventory.items():
            # Vérifier les rôles temporaires
            expired_roles = []
            for role_key, role_data in inv.get("active_roles", {}).items():
                if "expires" in role_data:
                    expires = datetime.fromisoformat(role_data["expires"])
                    if now >= expires:
                        expired_roles.append((role_key, role_data))
            
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
                                    
                                    # Notifier l'utilisateur
                                    try:
                                        await member.send(
                                            f"⏰ Votre rôle temporaire **{role.name}** a expiré. "
                                            f"Vous pouvez le racheter dans la boutique avec `!shop`"
                                        )
                                    except:
                                        pass
                                except:
                                    pass
                
                del inv["active_roles"][role_key]
            
            # Vérifier les boosts expirés
            expired_boosts = []
            for boost_id, boost_data in inv.get("active_boosts", {}).items():
                if "expires" in boost_data:
                    expires = datetime.fromisoformat(boost_data["expires"])
                    if now >= expires:
                        expired_boosts.append(boost_id)
            
            for boost_id in expired_boosts:
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
        Catégories: boost, lottery, role, mystery, collectible
        """
        if category:
            filtered = {k: v for k, v in SHOP_ITEMS.items() if v.get("category") == category.lower()}
            if not filtered:
                await ctx.send(f"❌ Catégorie invalide. Choix: `boost`, `lottery`, `role`, `mystery`, `collectible`")
                return
            items = filtered
            title = f"🛒 Boutique - {category.title()}"
        else:
            items = SHOP_ITEMS
            title = "🛒 Boutique LanorTrad"
        
        # Récupérer les points de l'utilisateur
        try:
            from community import get_user_stats
            user_stats = get_user_stats(ctx.author.id)
            user_points = user_stats.get("points", 0)
        except:
            user_points = 0
        
        embed = discord.Embed(
            title=title,
            description=f"💰 Votre solde: **{user_points:,}** points\n\n"
                       f"Utilisez `!buy <article>` pour acheter",
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
            "boost": "⚡ Boosts",
            "lottery": "🎰 Loterie",
            "role": "👑 Rôles",
            "mystery": "📦 Mystery Box",
            "collectible": "🏆 Collectibles"
        }
        
        for cat, cat_items in categories.items():
            items_text = ""
            for item_id, item in cat_items:
                can_afford = "✅" if user_points >= item["price"] else "❌"
                items_text += f"{can_afford} **{item['name']}** - {item['price']} pts\n"
                items_text += f"   *{item['description'][:50]}*\n"
            
            embed.add_field(
                name=category_names.get(cat, cat.title()),
                value=items_text or "Aucun article",
                inline=False
            )
        
        # Info loterie
        embed.add_field(
            name="🎰 Jackpot Actuel",
            value=f"**{lottery_data['current_jackpot']:,}** points\n"
                  f"👥 {len(lottery_data['participants'])} participants",
            inline=True
        )
        
        embed.set_footer(text="!shop <catégorie> pour filtrer | !buy <article> pour acheter")
        await ctx.send(embed=embed)
    
    @commands.command(name="buy", aliases=["acheter"])
    async def buy(self, ctx, *, item_name: str):
        """Achète un article de la boutique"""
        # Trouver l'item
        item_id = None
        item_data = None
        
        item_name_lower = item_name.lower().replace(" ", "_")
        
        for iid, idata in SHOP_ITEMS.items():
            if iid == item_name_lower or idata["name"].lower() == item_name.lower():
                item_id = iid
                item_data = idata
                break
        
        if not item_data:
            await ctx.send(f"❌ Article introuvable. Utilisez `!shop` pour voir les articles disponibles.")
            return
        
        # Vérifier les points
        try:
            from community import get_user_stats, add_points
            user_stats = get_user_stats(ctx.author.id)
            user_points = user_stats.get("points", 0)
        except Exception as e:
            await ctx.send(f"❌ Erreur: {e}")
            return
        
        if user_points < item_data["price"]:
            await ctx.send(f"❌ Vous n'avez pas assez de points. (Vous avez {user_points:,}, il faut {item_data['price']:,})")
            return
        
        # Déduire les points
        add_points(ctx.author.id, -item_data["price"], f"achat_{item_id}")
        
        inv = get_user_inventory(ctx.author.id)
        
        # Ajouter à l'historique
        inv["purchase_history"].append({
            "item_id": item_id,
            "price": item_data["price"],
            "date": datetime.now().isoformat()
        })
        
        # Traitement selon la catégorie
        result_embed = discord.Embed(
            title=f"✅ Achat Réussi !",
            description=f"Vous avez acheté **{item_data['name']}**",
            color=discord.Color.green(),
            timestamp=datetime.now()
        )
        
        # === BOOST ===
        if item_data["category"] == "boost":
            activate_boost(ctx.author.id, item_id.replace("_24h", "").replace("_12h", ""), item_data)
            
            if item_data.get("one_time_use"):
                result_embed.add_field(
                    name="⚡ Activation",
                    value="S'activera automatiquement à votre prochaine action !",
                    inline=False
                )
            else:
                duration = item_data.get("duration_hours", 24)
                expires = datetime.now() + timedelta(hours=duration)
                result_embed.add_field(
                    name="⏰ Durée",
                    value=f"Actif jusqu'au {expires.strftime('%d/%m à %H:%M')}",
                    inline=True
                )
                result_embed.add_field(
                    name="⚡ Multiplicateur",
                    value=f"x{item_data.get('multiplier', 2)}",
                    inline=True
                )
        
        # === LOTERIE ===
        elif item_data["category"] == "lottery":
            tickets = item_data.get("tickets", 1)
            inv["lottery_tickets"] = inv.get("lottery_tickets", 0) + tickets
            
            # Ajouter aux participants
            for _ in range(tickets):
                lottery_data["participants"].append(str(ctx.author.id))
            
            # Augmenter le jackpot (10% du prix va au jackpot)
            lottery_data["current_jackpot"] += int(item_data["price"] * 0.1 * tickets)
            
            result_embed.add_field(
                name="🎰 Tickets",
                value=f"+{tickets} ticket(s) ajouté(s)\nVous avez maintenant **{inv['lottery_tickets']}** ticket(s)",
                inline=True
            )
            result_embed.add_field(
                name="💰 Jackpot",
                value=f"**{lottery_data['current_jackpot']:,}** points",
                inline=True
            )
        
        # === RÔLE TEMPORAIRE ===
        elif item_data["category"] == "role":
            if item_data.get("custom_color"):
                # Demander la couleur
                result_embed.add_field(
                    name="🎨 Couleur Custom",
                    value="Utilisez `!setcolor #HEXCODE` pour définir votre couleur !",
                    inline=False
                )
                inv["pending_color_role"] = {
                    "purchased_at": datetime.now().isoformat(),
                    "duration_days": item_data.get("duration_days", 30)
                }
            else:
                role_id = item_data.get("role_id")
                if role_id:
                    role = ctx.guild.get_role(role_id)
                    if role:
                        try:
                            await ctx.author.add_roles(role, reason="Achat boutique")
                            
                            # Enregistrer l'expiration
                            duration = item_data.get("duration_days", 7)
                            expires = datetime.now() + timedelta(days=duration)
                            
                            if "active_roles" not in inv:
                                inv["active_roles"] = {}
                            
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
                            result_embed.add_field(name="❌ Erreur", value=str(e), inline=False)
                else:
                    result_embed.add_field(
                        name="⚠️ Configuration",
                        value="Ce rôle n'est pas encore configuré. Contactez un admin.",
                        inline=False
                    )
        
        # === MYSTERY BOX ===
        elif item_data["category"] == "mystery":
            loot = self.open_mystery_box(item_data.get("loot_table", {}))
            
            result_embed.title = f"📦 Mystery Box Ouverte !"
            
            if loot["type"] == "points":
                add_points(ctx.author.id, loot["quantity"], "mystery_box")
                result_embed.add_field(
                    name="💰 Vous avez obtenu",
                    value=f"**{loot['quantity']}** points !",
                    inline=False
                )
            elif loot["type"] == "item":
                # Activer l'item gagné
                won_item = SHOP_ITEMS.get(loot["item_id"])
                if won_item:
                    if won_item["category"] == "boost":
                        activate_boost(ctx.author.id, loot["item_id"], won_item)
                    elif won_item["category"] == "lottery":
                        inv["lottery_tickets"] = inv.get("lottery_tickets", 0) + loot.get("quantity", 1)
                        for _ in range(loot.get("quantity", 1)):
                            lottery_data["participants"].append(str(ctx.author.id))
                    
                    result_embed.add_field(
                        name=f"🎁 Vous avez obtenu",
                        value=f"**{won_item['name']}** x{loot.get('quantity', 1)} !",
                        inline=False
                    )
            
            result_embed.add_field(
                name="🎲 Rareté",
                value=f"**{loot['rarity'].upper()}**",
                inline=True
            )
        
        # === COLLECTIBLE ===
        elif item_data["category"] == "collectible":
            badge_id = item_data.get("badge_id")
            if badge_id:
                try:
                    from achievements import unlock_badge
                    unlock_badge(ctx.author.id, badge_id)
                    result_embed.add_field(
                        name="🏅 Badge Débloqué",
                        value=f"Vous avez maintenant le badge **{item_data['name']}** !",
                        inline=False
                    )
                except:
                    if "items" not in inv:
                        inv["items"] = {}
                    inv["items"][item_id] = inv["items"].get(item_id, 0) + 1
        
        sauvegarder_shop()
        
        # Afficher le nouveau solde
        try:
            user_stats = get_user_stats(ctx.author.id)
            result_embed.set_footer(text=f"💰 Nouveau solde: {user_stats.get('points', 0):,} points")
        except:
            pass
        
        result_embed.set_thumbnail(url=ctx.author.avatar.url if ctx.author.avatar else None)
        await ctx.send(embed=result_embed)
    
    def open_mystery_box(self, loot_table):
        """Ouvre une mystery box et retourne le loot"""
        # Déterminer la rareté
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
        
        # Choisir un item aléatoire
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
            value=f"**{lottery_data['current_jackpot']:,}** points",
            inline=True
        )
        
        embed.add_field(
            name="👥 Participants",
            value=f"**{len(lottery_data['participants'])}** tickets en jeu",
            inline=True
        )
        
        # Tickets de l'utilisateur
        inv = get_user_inventory(ctx.author.id)
        user_tickets = lottery_data["participants"].count(str(ctx.author.id))
        
        embed.add_field(
            name="🎫 Vos Tickets",
            value=f"**{user_tickets}** ticket(s) en jeu",
            inline=True
        )
        
        # Probabilité de gain
        if len(lottery_data["participants"]) > 0:
            win_chance = (user_tickets / len(lottery_data["participants"])) * 100
            embed.add_field(
                name="📊 Vos Chances",
                value=f"**{win_chance:.1f}%**",
                inline=True
            )
        
        # Dernier gagnant
        if lottery_data["winner_history"]:
            last_winner = lottery_data["winner_history"][-1]
            member = ctx.guild.get_member(int(last_winner["user_id"]))
            winner_name = member.display_name if member else "Inconnu"
            
            embed.add_field(
                name="🏆 Dernier Gagnant",
                value=f"**{winner_name}** ({last_winner['jackpot']:,} pts)",
                inline=True
            )
        
        embed.add_field(
            name="🛒 Acheter des Tickets",
            value="`!buy lottery_ticket` (50 pts)\n`!buy lottery_ticket_x5` (200 pts)",
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
            for boost_id, boost_data in active_boosts.items():
                item_name = SHOP_ITEMS.get(boost_id, {}).get("name", boost_id)
                
                if boost_data.get("one_time"):
                    boosts_text += f"⚡ **{item_name}** - Prêt à l'emploi\n"
                elif "expires" in boost_data:
                    expires = datetime.fromisoformat(boost_data["expires"])
                    remaining = expires - datetime.now()
                    hours = int(remaining.total_seconds() // 3600)
                    boosts_text += f"⚡ **{item_name}** - {hours}h restantes\n"
            
            embed.add_field(name="🚀 Boosts Actifs", value=boosts_text or "Aucun", inline=False)
        
        # Rôles temporaires
        active_roles = inv.get("active_roles", {})
        if active_roles:
            roles_text = ""
            for role_key, role_data in active_roles.items():
                expires = datetime.fromisoformat(role_data["expires"])
                days_left = (expires - datetime.now()).days
                role = ctx.guild.get_role(role_data.get("role_id", 0))
                role_name = role.name if role else role_key
                roles_text += f"👑 **{role_name}** - {days_left} jours\n"
            
            embed.add_field(name="👑 Rôles Temporaires", value=roles_text or "Aucun", inline=False)
        
        # Tickets loterie
        lottery_tickets = inv.get("lottery_tickets", 0)
        in_draw = lottery_data["participants"].count(str(member.id))
        embed.add_field(
            name="🎰 Loterie",
            value=f"**{in_draw}** ticket(s) en jeu",
            inline=True
        )
        
        # Items collectés
        items = inv.get("items", {})
        if items:
            items_text = ""
            for item_id, qty in items.items():
                item_name = SHOP_ITEMS.get(item_id, {}).get("name", item_id)
                items_text += f"• **{item_name}** x{qty}\n"
            embed.add_field(name="📦 Items", value=items_text[:500], inline=False)
        
        # Stats d'achat
        history = inv.get("purchase_history", [])
        total_spent = sum(p.get("price", 0) for p in history)
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
            await ctx.send("❌ Vous n'avez pas de couleur custom en attente. Achetez-en une avec `!buy color_role_30d`")
            return
        
        # Valider la couleur hex
        color = color.strip("#")
        try:
            color_int = int(color, 16)
        except ValueError:
            await ctx.send("❌ Couleur invalide. Utilisez le format hex: `!setcolor #FF5500`")
            return
        
        # Créer le rôle
        try:
            role = await ctx.guild.create_role(
                name=f"🎨 {ctx.author.display_name}",
                color=discord.Color(color_int),
                reason="Couleur custom achetée"
            )
            
            # Positionner le rôle
            await ctx.author.add_roles(role)
            
            # Enregistrer l'expiration
            duration = inv["pending_color_role"].get("duration_days", 30)
            expires = datetime.now() + timedelta(days=duration)
            
            if "active_roles" not in inv:
                inv["active_roles"] = {}
            
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
            
        except Exception as e:
            await ctx.send(f"❌ Erreur lors de la création du rôle: {e}")
    
    # ==================== COMMANDES ADMIN ====================
    
    @commands.command(name="forcedraw")
    @commands.has_permissions(administrator=True)
    async def force_lottery_draw(self, ctx):
        """Force un tirage de loterie (admin)"""
        if not lottery_data["participants"]:
            await ctx.send("❌ Aucun participant dans la loterie.")
            return
        
        await ctx.send("🎰 **Tirage forcé de la loterie...**")
        
        # Utiliser la tâche de tirage
        await self.weekly_lottery()
        
        if lottery_data["winner_history"]:
            last = lottery_data["winner_history"][-1]
            winner = ctx.guild.get_member(int(last["user_id"]))
            winner_name = winner.mention if winner else "Inconnu"
            
            await ctx.send(f"🎉 **{winner_name}** a remporté **{last['jackpot']:,}** points !")
    
    @commands.command(name="setjackpot")
    @commands.has_permissions(administrator=True)
    async def set_jackpot(self, ctx, amount: int):
        """Définit le jackpot de la loterie (admin)"""
        lottery_data["current_jackpot"] = amount
        sauvegarder_shop()
        await ctx.send(f"✅ Jackpot défini à **{amount:,}** points.")
    
    @commands.command(name="configrole")
    @commands.has_permissions(administrator=True)
    async def config_shop_role(self, ctx, item_id: str, role: discord.Role):
        """Configure un rôle pour un article de la boutique (admin)"""
        if item_id not in SHOP_ITEMS:
            await ctx.send("❌ Article introuvable.")
            return
        
        SHOP_ITEMS[item_id]["role_id"] = role.id
        await ctx.send(f"✅ Le rôle {role.mention} a été configuré pour **{SHOP_ITEMS[item_id]['name']}**")


async def setup(bot):
    """Setup pour discord.py 2.0+"""
    await bot.add_cog(ShopSystem(bot))