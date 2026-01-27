# admin_data.py
# Commandes d'administration centralisées pour la gestion des données
import discord
from config import ADMIN_ROLES, TARGET_USER_ID
from discord.ext import commands
import json
import os
import asyncio
from datetime import datetime
from config import COLORS

# ID de l'utilisateur qui recevra les fichiers

# Définition de tous les modules de données
DATA_MODULES = {
    "tasks": {
        "name": "Tâches",
        "emoji": "📝",
        "file": "data/etat_taches.json",
        "meta_file": "data/etat_taches_meta.json",
        "module": "commands",
        "load_func": "charger_etat_taches",
        "save_func": "sauvegarder_etat_taches",
        "data_var": "etat_taches_global"
    },
    "rappels": {
        "name": "Rappels",
        "emoji": "⏰",
        "file": "data/rappels_tasks.json",
        "meta_file": "data/rappels_tasks_meta.json",
        "module": "rappels",
        "load_func": "charger_rappels",
        "save_func": "sauvegarder_rappels",
        "data_var": "rappels_actifs"
    },
    "invites": {
        "name": "Invitations",
        "emoji": "📨",
        "file": "data/invites_tracker.json",
        "meta_file": "data/invites_tracker_meta.json",
        "module": "giveaway",
        "load_func": "charger_invites",
        "save_func": "sauvegarder_invites",
        "data_var": "invites_tracker"
    },
    "giveaways": {
        "name": "Giveaways",
        "emoji": "🎁",
        "file": "data/giveaways.json",
        "meta_file": "data/giveaways_meta.json",
        "module": "giveaway",
        "load_func": "charger_giveaways",
        "save_func": "sauvegarder_giveaways",
        "data_var": "giveaways_actifs"
    },
    "reviews": {
        "name": "Reviews",
        "emoji": "⭐",
        "file": "data/reviews.json",
        "meta_file": "data/reviews_meta.json",
        "module": "community",
        "load_func": "charger_donnees",
        "save_func": "sauvegarder_donnees",
        "data_var": "reviews_data"
    },
    "theories": {
        "name": "Théories",
        "emoji": "💭",
        "file": "data/theories.json",
        "meta_file": "data/theories_meta.json",
        "module": "community",
        "load_func": "charger_donnees",
        "save_func": "sauvegarder_donnees",
        "data_var": "theories_data"
    },
    "chapters": {
        "name": "Chapitres Community",
        "emoji": "📚",
        "file": "data/chapters_community.json",
        "meta_file": "data/chapters_community_meta.json",
        "module": "community",
        "load_func": "charger_donnees",
        "save_func": "sauvegarder_donnees",
        "data_var": "chapters_data"
    },
    "user_stats": {
        "name": "Stats Utilisateurs",
        "emoji": "📊",
        "file": "data/user_stats.json",
        "meta_file": "data/user_stats_meta.json",
        "module": "community",
        "load_func": "charger_donnees",
        "save_func": "sauvegarder_donnees",
        "data_var": "user_stats"
    },
    "badges": {
        "name": "Badges Config",
        "emoji": "🏆",
        "file": "data/badges.json",
        "meta_file": "data/badges_meta.json",
        "module": "achievements",
        "load_func": "charger_badges",
        "save_func": "sauvegarder_badges",
        "data_var": "badges_data"
    },
    "user_badges": {
        "name": "Badges Utilisateurs",
        "emoji": "🎖️",
        "file": "data/user_badges.json",
        "meta_file": "data/user_badges_meta.json",
        "module": "achievements",
        "load_func": "charger_badges",
        "save_func": "sauvegarder_badges",
        "data_var": "user_badges"
    },
    "shop": {
        "name": "Shop Items",
        "emoji": "🛒",
        "file": "data/shop_items.json",
        "meta_file": "data/shop_items_meta.json",
        "module": "shop",
        "load_func": "charger_shop",
        "save_func": "sauvegarder_shop",
        "data_var": "shop_items"
    },
    "purchases": {
        "name": "Achats",
        "emoji": "💳",
        "file": "data/purchases.json",
        "meta_file": "data/purchases_meta.json",
        "module": "shop",
        "load_func": "charger_shop",
        "save_func": "sauvegarder_shop",
        "data_var": "purchases_history"
    },
    "inventory": {
        "name": "Inventaires",
        "emoji": "🎒",
        "file": "data/user_inventory.json",
        "meta_file": "data/user_inventory_meta.json",
        "module": "shop",
        "load_func": "charger_shop",
        "save_func": "sauvegarder_shop",
        "data_var": "user_inventory"
    }
}

# Groupes de modules pour sélection rapide
DATA_GROUPS = {
    "all": {
        "name": "Tout",
        "emoji": "📦",
        "modules": list(DATA_MODULES.keys())
    },
    "community": {
        "name": "Communauté",
        "emoji": "👥",
        "modules": ["reviews", "theories", "chapters", "user_stats"]
    },
    "achievements": {
        "name": "Achievements",
        "emoji": "🏆",
        "modules": ["badges", "user_badges"]
    },
    "shop": {
        "name": "Shop",
        "emoji": "🛒",
        "modules": ["shop", "purchases", "inventory"]
    },
    "giveaway": {
        "name": "Giveaway",
        "emoji": "🎁",
        "modules": ["invites", "giveaways"]
    },
    "workflow": {
        "name": "Workflow",
        "emoji": "📋",
        "modules": ["tasks", "rappels"]
    }
}


def get_module_data(module_key):
    """Récupère les données d'un module"""
    if module_key not in DATA_MODULES:
        return None, 0
    
    config = DATA_MODULES[module_key]
    
    try:
        module = __import__(config["module"])
        data = getattr(module, config["data_var"], {})
        return data, len(data) if isinstance(data, dict) else 0
    except Exception as e:
        print(f"Erreur récupération {module_key}: {e}")
        return None, 0


def save_module_data(module_key):
    """Sauvegarde les données d'un module"""
    if module_key not in DATA_MODULES:
        return False
    
    config = DATA_MODULES[module_key]
    
    try:
        module = __import__(config["module"])
        save_func = getattr(module, config["save_func"], None)
        if save_func:
            save_func()
        
        # Créer le fichier meta
        data, count = get_module_data(module_key)
        meta = {
            "last_saved": datetime.utcnow().isoformat() + "Z",
            "item_count": count,
            "module": module_key
        }
        
        meta_file = config.get("meta_file")
        if meta_file:
            os.makedirs(os.path.dirname(meta_file), exist_ok=True)
            with open(meta_file, "w", encoding="utf-8") as f:
                json.dump(meta, f, ensure_ascii=False, indent=4)
        
        return True
    except Exception as e:
        print(f"Erreur sauvegarde {module_key}: {e}")
        return False


def load_module_data(module_key):
    """Recharge les données d'un module"""
    if module_key not in DATA_MODULES:
        return False
    
    config = DATA_MODULES[module_key]
    
    try:
        module = __import__(config["module"])
        load_func = getattr(module, config["load_func"], None)
        if load_func:
            load_func()
        return True
    except Exception as e:
        print(f"Erreur rechargement {module_key}: {e}")
        return False


class AdminData(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.command(name="data")
    @commands.has_any_role(*ADMIN_ROLES)
    async def data_manager(self, ctx, action: str = None, target: str = None):
        """
        Gestionnaire de données centralisé.
        
        Usage:
        !data                    - Menu interactif
        !data save <module/group> - Sauvegarder
        !data reload <module/group> - Recharger
        !data export <module/group> - Exporter en MP
        !data status             - Voir le statut de tous les modules
        """
        
        if action is None:
            # Menu interactif
            await self.show_data_menu(ctx)
            return
        
        action = action.lower()
        
        if action == "status":
            await self.show_data_status(ctx)
            return
        
        if action not in ["save", "reload", "export"]:
            await ctx.send(f"❌ Action invalide. Utilisez: `save`, `reload`, `export`, `status`")
            return
        
        if target is None:
            await ctx.send(f"❌ Spécifiez un module ou groupe. Ex: `!data {action} all`")
            return
        
        target = target.lower()
        
        # Déterminer les modules à traiter
        if target in DATA_GROUPS:
            modules_to_process = DATA_GROUPS[target]["modules"]
            target_name = DATA_GROUPS[target]["name"]
        elif target in DATA_MODULES:
            modules_to_process = [target]
            target_name = DATA_MODULES[target]["name"]
        else:
            await ctx.send(f"❌ Module/groupe `{target}` introuvable.")
            return
        
        # Exécuter l'action
        if action == "save":
            await self.save_modules(ctx, modules_to_process, target_name)
        elif action == "reload":
            await self.reload_modules(ctx, modules_to_process, target_name)
        elif action == "export":
            await self.export_modules(ctx, modules_to_process, target_name)
    
    async def show_data_menu(self, ctx):
        """Affiche le menu interactif de gestion des données"""
        embed = discord.Embed(
            title="📦 Gestionnaire de Données",
            description="Sélectionnez une action avec les réactions",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        
        # Groupes disponibles
        groups_text = "\n".join([
            f"{g['emoji']} **{g['name']}** - `{key}`" 
            for key, g in DATA_GROUPS.items()
        ])
        embed.add_field(name="📁 Groupes", value=groups_text, inline=False)
        
        # Modules individuels (raccourci)
        modules_text = " | ".join([
            f"{m['emoji']} `{key}`" 
            for key, m in list(DATA_MODULES.items())[:6]
        ])
        modules_text += "\n" + " | ".join([
            f"{m['emoji']} `{key}`" 
            for key, m in list(DATA_MODULES.items())[6:]
        ])
        embed.add_field(name="📄 Modules", value=modules_text, inline=False)
        
        embed.add_field(
            name="━━━━━━━━━━━━━━━━━━━━",
            value=(
                "💾 `!data save <cible>` - Sauvegarder\n"
                "♻️ `!data reload <cible>` - Recharger\n"
                "📤 `!data export <cible>` - Exporter en MP\n"
                "📊 `!data status` - Statut de tous les modules"
            ),
            inline=False
        )
        
        embed.set_footer(text="Exemple: !data save all | !data export community")
        
        message = await ctx.send(embed=embed)
        
        # Ajouter les réactions pour actions rapides
        reactions = ["💾", "♻️", "📤", "📊"]
        for r in reactions:
            await message.add_reaction(r)
        
        def check(reaction, user):
            return user == ctx.author and str(reaction.emoji) in reactions and reaction.message.id == message.id
        
        try:
            reaction, _ = await self.bot.wait_for("reaction_add", timeout=60, check=check)
            await message.clear_reactions()
            
            emoji = str(reaction.emoji)
            
            if emoji == "💾":
                await self.save_modules(ctx, DATA_GROUPS["all"]["modules"], "Tout")
            elif emoji == "♻️":
                await self.reload_modules(ctx, DATA_GROUPS["all"]["modules"], "Tout")
            elif emoji == "📤":
                await self.export_modules(ctx, DATA_GROUPS["all"]["modules"], "Tout")
            elif emoji == "📊":
                await self.show_data_status(ctx)
                
        except asyncio.TimeoutError:
            await message.clear_reactions()
    
    async def show_data_status(self, ctx):
        """Affiche le statut de tous les modules"""
        embed = discord.Embed(
            title="📊 Statut des Données",
            description="État actuel de tous les modules",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        
        total_items = 0
        
        for key, config in DATA_MODULES.items():
            data, count = get_module_data(key)
            total_items += count
            
            # Vérifier si le fichier existe
            file_exists = os.path.exists(config["file"])
            status = "✅" if file_exists and data is not None else "⚠️"
            
            # Récupérer la date de dernière sauvegarde
            last_saved = "N/A"
            if os.path.exists(config.get("meta_file", "")):
                try:
                    with open(config["meta_file"], "r", encoding="utf-8") as f:
                        meta = json.load(f)
                        last_saved = meta.get("last_saved", "N/A")[:16].replace("T", " ")
                except:
                    pass
            
            embed.add_field(
                name=f"{config['emoji']} {config['name']}",
                value=f"{status} **{count}** éléments\n`{last_saved}`",
                inline=True
            )
        
        embed.add_field(
            name="━━━━━━━━━━━━━━━━━━━━",
            value=f"**Total:** {total_items} éléments dans {len(DATA_MODULES)} modules",
            inline=False
        )
        
        embed.set_footer(text=f"Demandé par {ctx.author.name}")
        await ctx.send(embed=embed)
    
    async def save_modules(self, ctx, modules, target_name):
        """Sauvegarde les modules spécifiés"""
        embed = discord.Embed(
            title="💾 Sauvegarde en cours...",
            description=f"Sauvegarde de **{target_name}**",
            color=discord.Color.gold(),
            timestamp=datetime.now()
        )
        msg = await ctx.send(embed=embed)
        
        results = {"success": [], "failed": []}
        
        for module_key in modules:
            config = DATA_MODULES.get(module_key)
            if not config:
                continue
            
            success = save_module_data(module_key)
            
            if success:
                results["success"].append(f"{config['emoji']} {config['name']}")
            else:
                results["failed"].append(f"{config['emoji']} {config['name']}")
        
        # Résultat
        embed = discord.Embed(
            title="💾 Sauvegarde Terminée",
            description=f"**{target_name}** sauvegardé",
            color=discord.Color.green() if not results["failed"] else discord.Color.orange(),
            timestamp=datetime.now()
        )
        
        if results["success"]:
            embed.add_field(
                name=f"✅ Succès ({len(results['success'])})",
                value="\n".join(results["success"][:10]),
                inline=True
            )
        
        if results["failed"]:
            embed.add_field(
                name=f"❌ Échecs ({len(results['failed'])})",
                value="\n".join(results["failed"]),
                inline=True
            )
        
        embed.set_footer(text=f"Demandé par {ctx.author.name}")
        await msg.edit(embed=embed)
    
    async def reload_modules(self, ctx, modules, target_name):
        """Recharge les modules spécifiés"""
        embed = discord.Embed(
            title="♻️ Rechargement en cours...",
            description=f"Rechargement de **{target_name}**",
            color=discord.Color.gold(),
            timestamp=datetime.now()
        )
        msg = await ctx.send(embed=embed)
        
        results = {"success": [], "failed": []}
        
        for module_key in modules:
            config = DATA_MODULES.get(module_key)
            if not config:
                continue
            
            success = load_module_data(module_key)
            
            if success:
                data, count = get_module_data(module_key)
                results["success"].append(f"{config['emoji']} {config['name']} ({count})")
            else:
                results["failed"].append(f"{config['emoji']} {config['name']}")
        
        # Résultat
        embed = discord.Embed(
            title="♻️ Rechargement Terminé",
            description=f"**{target_name}** rechargé",
            color=discord.Color.green() if not results["failed"] else discord.Color.orange(),
            timestamp=datetime.now()
        )
        
        if results["success"]:
            embed.add_field(
                name=f"✅ Succès ({len(results['success'])})",
                value="\n".join(results["success"][:10]),
                inline=True
            )
        
        if results["failed"]:
            embed.add_field(
                name=f"❌ Échecs ({len(results['failed'])})",
                value="\n".join(results["failed"]),
                inline=True
            )
        
        embed.set_footer(text=f"Demandé par {ctx.author.name}")
        await msg.edit(embed=embed)
    
    async def export_modules(self, ctx, modules, target_name):
        """Exporte les modules spécifiés en MP"""
        embed = discord.Embed(
            title="📤 Export en cours...",
            description=f"Préparation de **{target_name}**",
            color=discord.Color.gold(),
            timestamp=datetime.now()
        )
        msg = await ctx.send(embed=embed)
        
        # Récupérer l'utilisateur cible
        target_user = await self.bot.fetch_user(TARGET_USER_ID)
        if not target_user:
            await ctx.send("❌ Utilisateur cible introuvable.")
            return
        
        # Sauvegarder d'abord
        for module_key in modules:
            save_module_data(module_key)
        
        # Préparer les fichiers
        files_to_send = []
        files_info = []
        
        for module_key in modules:
            config = DATA_MODULES.get(module_key)
            if not config:
                continue
            
            # Fichier principal
            if os.path.exists(config["file"]):
                files_to_send.append(discord.File(config["file"]))
                data, count = get_module_data(module_key)
                files_info.append(f"{config['emoji']} {config['name']}: **{count}** éléments")
        
        if not files_to_send:
            await ctx.send("❌ Aucun fichier à exporter.")
            return
        
        # Créer l'embed pour le MP
        embed_dm = discord.Embed(
            title=f"📤 Export: {target_name}",
            description=f"Export demandé par {ctx.author.name}",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        
        embed_dm.add_field(
            name="📁 Fichiers inclus",
            value="\n".join(files_info[:15]),
            inline=False
        )
        
        embed_dm.set_footer(text=f"Serveur: {ctx.guild.name}")
        
        # Envoyer en plusieurs messages si nécessaire (limite de 10 fichiers par message)
        try:
            for i in range(0, len(files_to_send), 10):
                batch = files_to_send[i:i+10]
                if i == 0:
                    await target_user.send(embed=embed_dm, files=batch)
                else:
                    await target_user.send(f"📁 Suite de l'export ({i+1}-{i+len(batch)})...", files=batch)
            
            # Confirmation
            embed = discord.Embed(
                title="📤 Export Terminé",
                description=f"**{len(files_to_send)}** fichier(s) envoyé(s) à {target_user.mention}",
                color=discord.Color.green(),
                timestamp=datetime.now()
            )
            embed.add_field(
                name="📁 Contenu",
                value="\n".join(files_info[:10]),
                inline=False
            )
            embed.set_footer(text=f"Demandé par {ctx.author.name}")
            await msg.edit(embed=embed)
            
        except discord.Forbidden:
            embed = discord.Embed(
                title="❌ Erreur d'Export",
                description=f"Impossible d'envoyer un MP à {target_user.mention}.",
                color=discord.Color.red()
            )
            await msg.edit(embed=embed)
    
    @commands.command(name="backup")
    @commands.has_any_role(*ADMIN_ROLES)
    async def backup_all(self, ctx):
        """Sauvegarde et exporte TOUTES les données en une commande"""
        await self.save_modules(ctx, DATA_GROUPS["all"]["modules"], "Tout")
        await asyncio.sleep(1)
        await self.export_modules(ctx, DATA_GROUPS["all"]["modules"], "Tout")
    
    @commands.command(name="data_list")
    @commands.has_any_role(*ADMIN_ROLES)
    async def data_list(self, ctx):
        """Liste tous les modules et groupes disponibles"""
        embed = discord.Embed(
            title="📋 Modules de Données Disponibles",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        
        # Groupes
        groups_text = ""
        for key, group in DATA_GROUPS.items():
            modules_list = ", ".join(group["modules"][:4])
            if len(group["modules"]) > 4:
                modules_list += f"... (+{len(group['modules'])-4})"
            groups_text += f"{group['emoji']} **{key}** - {group['name']}\n└ {modules_list}\n"
        
        embed.add_field(name="📁 Groupes", value=groups_text, inline=False)
        
        # Modules
        modules_text = ""
        for key, config in DATA_MODULES.items():
            modules_text += f"{config['emoji']} **{key}** - {config['name']}\n"
        
        embed.add_field(name="📄 Modules Individuels", value=modules_text, inline=False)
        
        embed.add_field(
            name="💡 Utilisation",
            value=(
                "`!data save all` - Tout sauvegarder\n"
                "`!data export community` - Exporter le groupe communauté\n"
                "`!data reload reviews` - Recharger les reviews\n"
                "`!backup` - Sauvegarder + Exporter tout"
            ),
            inline=False
        )
        
        await ctx.send(embed=embed)


async def setup(bot):
    """Setup pour discord.py 2.0+"""
    await bot.add_cog(AdminData(bot))