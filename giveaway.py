import discord
from discord.ext import commands, tasks
from config import (
    ADMIN_ROLES, DATA_FILES, GIVEAWAY_ROLES, GIVEAWAY_EMOJI, GIVEAWAY_COLOR
)
from utils import load_json, save_json
import json
import os
import random
import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any

# ═══════════════════════════════════════════════════════════════════════════════
# FICHIERS DE DONNÉES (depuis config.py)
# ═══════════════════════════════════════════════════════════════════════════════

GIVEAWAYS_FILE = DATA_FILES["giveaways"]
INVITES_FILE = DATA_FILES["invites"]

# ═══════════════════════════════════════════════════════════════════════════════
# FONCTIONS UTILITAIRES
# ═══════════════════════════════════════════════════════════════════════════════

def ensure_data_dir():
    """S'assure que le dossier data existe"""
    os.makedirs("data", exist_ok=True)

def load_giveaways() -> Dict:
    """Charge les giveaways actifs"""
    ensure_data_dir()
    if os.path.exists(GIVEAWAYS_FILE):
        try:
            with open(GIVEAWAYS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {"active": {}, "ended": [], "stats": {}}
    return {"active": {}, "ended": [], "stats": {}}

def save_giveaways(data: Dict):
    """Sauvegarde les giveaways"""
    ensure_data_dir()
    with open(GIVEAWAYS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def load_invites() -> Dict:
    """Charge le tracking des invitations"""
    ensure_data_dir()
    if os.path.exists(INVITES_FILE):
        try:
            with open(INVITES_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}
    return {}

def save_invites(data: Dict):
    """Sauvegarde le tracking des invitations"""
    ensure_data_dir()
    with open(INVITES_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def parse_duration(duration_str: str) -> Optional[timedelta]:
    """
    Parse une durée string en timedelta
    Formats: 1d, 2h, 30m, 1d12h, 1h30m
    """
    if not duration_str:
        return None
    
    duration_str = duration_str.lower().strip()
    
    total_seconds = 0
    current_num = ""
    
    for char in duration_str:
        if char.isdigit():
            current_num += char
        elif char in ['d', 'h', 'm', 's']:
            if current_num:
                num = int(current_num)
                if char == 'd':
                    total_seconds += num * 86400
                elif char == 'h':
                    total_seconds += num * 3600
                elif char == 'm':
                    total_seconds += num * 60
                elif char == 's':
                    total_seconds += num
                current_num = ""
    
    if total_seconds > 0:
        return timedelta(seconds=total_seconds)
    return None

def format_duration(td: timedelta) -> str:
    """Formate une timedelta en string lisible"""
    total_seconds = int(td.total_seconds())
    
    days = total_seconds // 86400
    hours = (total_seconds % 86400) // 3600
    minutes = (total_seconds % 3600) // 60
    
    parts = []
    if days > 0:
        parts.append(f"{days}j")
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    
    return " ".join(parts) if parts else "0m"

def format_timestamp(dt: datetime) -> str:
    """Formate un datetime en timestamp Discord"""
    return f"<t:{int(dt.timestamp())}:R>"

# ═══════════════════════════════════════════════════════════════════════════════
# COG DISCORD
# ═══════════════════════════════════════════════════════════════════════════════

class Giveaways(commands.Cog):
    """Système de giveaways avec invitations"""
    
    def __init__(self, bot):
        self.bot = bot
        self.invites_cache = {}  # Cache des invitations du serveur
        self.check_giveaways.start()
    
    def cog_unload(self):
        self.check_giveaways.cancel()
    
    # ─────────────────────────────────────────────────────────────────────────
    # TÂCHES EN ARRIÈRE-PLAN
    # ─────────────────────────────────────────────────────────────────────────
    
    @tasks.loop(seconds=30)
    async def check_giveaways(self):
        """Vérifie les giveaways terminés"""
        data = load_giveaways()
        now = datetime.now()
        
        ended_giveaways = []
        
        for giveaway_id, giveaway in list(data.get("active", {}).items()):
            end_time = datetime.fromisoformat(giveaway["end_time"])
            
            if now >= end_time:
                ended_giveaways.append((giveaway_id, giveaway))
        
        for giveaway_id, giveaway in ended_giveaways:
            await self.end_giveaway(giveaway_id, giveaway)
    
    @check_giveaways.before_loop
    async def before_check(self):
        await self.bot.wait_until_ready()
    
    # ─────────────────────────────────────────────────────────────────────────
    # MÉTHODES INTERNES
    # ─────────────────────────────────────────────────────────────────────────
    
    async def end_giveaway(self, giveaway_id: str, giveaway: Dict):
        """Termine un giveaway et tire les gagnants"""
        data = load_giveaways()
        
        try:
            channel = self.bot.get_channel(giveaway["channel_id"])
            if not channel:
                channel = await self.bot.fetch_channel(giveaway["channel_id"])
            
            message = await channel.fetch_message(giveaway["message_id"])
        except:
            # Message ou channel introuvable
            if giveaway_id in data["active"]:
                data["active"].pop(giveaway_id)
                save_giveaways(data)
            return
        
        # Récupérer les participants via réactions
        participants = []
        for reaction in message.reactions:
            if str(reaction.emoji) == GIVEAWAY_EMOJI:
                async for user in reaction.users():
                    if not user.bot and user.id != giveaway.get("host_id"):
                        # Vérifier les requirements
                        if await self.check_requirements(user, giveaway, channel.guild):
                            # Calculer les entrées bonus
                            entries = self.calculate_entries(user, channel.guild)
                            for _ in range(entries):
                                participants.append(user)
        
        winners_count = giveaway.get("winners", 1)
        prize = giveaway.get("prize", "Prix mystère")
        
        # Tirer les gagnants
        if len(participants) == 0:
            embed = discord.Embed(
                title="🎉 Giveaway Terminé",
                description=f"**{prize}**\n\n❌ Aucun participant valide !",
                color=0xff0000
            )
        else:
            # Enlever les doublons pour les gagnants uniques
            unique_participants = list(set(participants))
            winners = random.sample(unique_participants, min(winners_count, len(unique_participants)))
            
            winners_mentions = ", ".join([w.mention for w in winners])
            
            embed = discord.Embed(
                title="🎉 Giveaway Terminé !",
                description=f"**{prize}**\n\n🏆 **Gagnant(s):** {winners_mentions}",
                color=0x00ff00
            )
            embed.set_footer(text=f"Organisé par {giveaway.get('host_name', 'Inconnu')}")
            
            # Notification des gagnants
            await channel.send(
                f"🎊 Félicitations {winners_mentions} ! Vous avez gagné **{prize}** !",
                reference=message
            )
            
            # Enregistrer les stats
            for winner in winners:
                user_id = str(winner.id)
                if user_id not in data.get("stats", {}):
                    data["stats"][user_id] = {"wins": 0, "participated": 0}
                data["stats"][user_id]["wins"] = data["stats"][user_id].get("wins", 0) + 1
            
            # Badge giveaway winner via achievements
            try:
                from achievements import unlock_badge
                for winner in winners:
                    unlock_badge(winner.id, "giveaway_winner")
            except ImportError:
                pass
        
        # Mettre à jour le message original
        try:
            await message.edit(embed=embed)
        except:
            pass
        
        # Déplacer vers ended
        giveaway["ended_at"] = datetime.now().isoformat()
        giveaway["winner_ids"] = [w.id for w in winners] if participants else []
        data["ended"].append(giveaway)
        
        if giveaway_id in data["active"]:
            del data["active"][giveaway_id]
        
        save_giveaways(data)
    
    async def check_requirements(self, user: discord.User, giveaway: Dict, guild: discord.Guild) -> bool:
        """Vérifie si un utilisateur remplit les conditions"""
        requirements = giveaway.get("requirements", {})
        
        try:
            member = await guild.fetch_member(user.id)
        except:
            return False
        
        # Vérifier le rôle requis
        if "role_id" in requirements and requirements["role_id"]:
            role = guild.get_role(requirements["role_id"])
            if role and role not in member.roles:
                return False
        
        # Vérifier l'ancienneté minimum
        if "min_account_age_days" in requirements:
            age = (datetime.now() - member.created_at.replace(tzinfo=None)).days
            if age < requirements["min_account_age_days"]:
                return False
        
        # Vérifier l'ancienneté serveur
        if "min_server_days" in requirements:
            if member.joined_at:
                server_age = (datetime.now() - member.joined_at.replace(tzinfo=None)).days
                if server_age < requirements["min_server_days"]:
                    return False
        
        # Vérifier les invitations
        if "min_invites" in requirements:
            invites_data = load_invites()
            user_invites = invites_data.get(str(user.id), {}).get("total", 0)
            if user_invites < requirements["min_invites"]:
                return False
        
        return True
    
    def calculate_entries(self, user: discord.User, guild: discord.Guild) -> int:
        """Calcule le nombre d'entrées bonus pour un utilisateur"""
        entries = 1
        
        try:
            member = guild.get_member(user.id)
            if not member:
                return entries
            
            # Bonus pour rôle VIP
            if GIVEAWAY_ROLES.get("vip_role"):
                vip_role = guild.get_role(GIVEAWAY_ROLES["vip_role"])
                if vip_role and vip_role in member.roles:
                    entries = 2
            
            # Bonus pour rôle bonus
            if GIVEAWAY_ROLES.get("bonus_role"):
                bonus_role = guild.get_role(GIVEAWAY_ROLES["bonus_role"])
                if bonus_role and bonus_role in member.roles:
                    entries += 1
        except:
            pass
        
        return entries
    
    def can_manage_giveaways(self, member: discord.Member) -> bool:
        """Vérifie si un membre peut gérer les giveaways"""
        if member.guild_permissions.administrator:
            return True
        
        if GIVEAWAY_ROLES.get("manager_role"):
            manager_role = member.guild.get_role(GIVEAWAY_ROLES["manager_role"])
            if manager_role and manager_role in member.roles:
                return True
        
        return False
    
    # ─────────────────────────────────────────────────────────────────────────
    # COMMANDES DE CRÉATION
    # ─────────────────────────────────────────────────────────────────────────
    
    @commands.command(name="giveaway", aliases=["gstart", "gcreate"])
    @commands.has_permissions(manage_guild=True)
    async def create_giveaway(self, ctx, duration: str, winners: int, *, prize: str):
        """
        Crée un nouveau giveaway
        
        Usage: !giveaway <durée> <nb_gagnants> <prix>
        Durée: 1d, 12h, 30m, 1d12h, etc.
        
        Exemple: !giveaway 1d 1 Nitro Classic
        """
        # Parser la durée
        td = parse_duration(duration)
        if not td:
            await ctx.send("❌ Format de durée invalide. Utilise: 1d, 12h, 30m, 1d12h, etc.")
            return
        
        if winners < 1 or winners > 20:
            await ctx.send("❌ Le nombre de gagnants doit être entre 1 et 20.")
            return
        
        if len(prize) > 256:
            await ctx.send("❌ Le prix est trop long (max 256 caractères).")
            return
        
        end_time = datetime.now() + td
        
        # Créer l'embed
        embed = discord.Embed(
            title="🎉 GIVEAWAY !",
            description=f"**{prize}**\n\n"
                       f"Réagis avec {GIVEAWAY_EMOJI} pour participer !\n\n"
                       f"⏱️ **Fin:** {format_timestamp(end_time)}\n"
                       f"🏆 **Gagnants:** {winners}\n"
                       f"👤 **Organisé par:** {ctx.author.mention}",
            color=GIVEAWAY_COLOR
        )
        embed.set_footer(text=f"ID: {int(datetime.now().timestamp())}")
        
        # Envoyer et ajouter réaction
        msg = await ctx.send(embed=embed)
        await msg.add_reaction(GIVEAWAY_EMOJI)
        
        # Sauvegarder
        data = load_giveaways()
        giveaway_id = str(msg.id)
        
        data["active"][giveaway_id] = {
            "message_id": msg.id,
            "channel_id": ctx.channel.id,
            "guild_id": ctx.guild.id,
            "prize": prize,
            "winners": winners,
            "end_time": end_time.isoformat(),
            "host_id": ctx.author.id,
            "host_name": str(ctx.author),
            "created_at": datetime.now().isoformat(),
            "requirements": {}
        }
        
        save_giveaways(data)
        
        await ctx.message.delete()
    
    @commands.command(name="giveaway_advanced", aliases=["gadvanced"])
    @commands.has_permissions(manage_guild=True)
    async def create_advanced_giveaway(self, ctx):
        """
        Crée un giveaway avec options avancées (interactif)
        """
        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel
        
        await ctx.send("🎉 **Création de giveaway avancé**\n\n📦 Quel est le **prix** ?")
        
        try:
            msg = await self.bot.wait_for('message', timeout=60.0, check=check)
            prize = msg.content
            
            await ctx.send("⏱️ Quelle est la **durée** ? (ex: 1d, 12h, 1d12h)")
            msg = await self.bot.wait_for('message', timeout=60.0, check=check)
            duration = parse_duration(msg.content)
            if not duration:
                await ctx.send("❌ Durée invalide. Annulé.")
                return
            
            await ctx.send("🏆 Combien de **gagnants** ? (1-20)")
            msg = await self.bot.wait_for('message', timeout=60.0, check=check)
            try:
                winners = int(msg.content)
                if winners < 1 or winners > 20:
                    raise ValueError()
            except:
                await ctx.send("❌ Nombre invalide. Annulé.")
                return
            
            await ctx.send("🔒 Y a-t-il un **rôle requis** ? (mentionnez le rôle ou tapez `non`)")
            msg = await self.bot.wait_for('message', timeout=60.0, check=check)
            required_role = None
            if msg.role_mentions:
                required_role = msg.role_mentions[0].id
            
            await ctx.send("📨 **Invitations minimum** requises ? (nombre ou `0` pour aucun)")
            msg = await self.bot.wait_for('message', timeout=60.0, check=check)
            try:
                min_invites = int(msg.content)
            except:
                min_invites = 0
            
        except asyncio.TimeoutError:
            await ctx.send("⏰ Temps écoulé. Giveaway annulé.")
            return
        
        # Créer le giveaway
        end_time = datetime.now() + duration
        
        requirements_text = []
        if required_role:
            role = ctx.guild.get_role(required_role)
            if role:
                requirements_text.append(f"• Rôle requis: {role.mention}")
        if min_invites > 0:
            requirements_text.append(f"• Invitations minimum: {min_invites}")
        
        embed = discord.Embed(
            title="🎉 GIVEAWAY !",
            description=f"**{prize}**\n\n"
                       f"Réagis avec {GIVEAWAY_EMOJI} pour participer !\n\n"
                       f"⏱️ **Fin:** {format_timestamp(end_time)}\n"
                       f"🏆 **Gagnants:** {winners}\n"
                       f"👤 **Organisé par:** {ctx.author.mention}",
            color=GIVEAWAY_COLOR
        )
        
        if requirements_text:
            embed.add_field(name="📋 Conditions", value="\n".join(requirements_text), inline=False)
        
        msg = await ctx.send(embed=embed)
        await msg.add_reaction(GIVEAWAY_EMOJI)
        
        # Sauvegarder
        data = load_giveaways()
        giveaway_id = str(msg.id)
        
        data["active"][giveaway_id] = {
            "message_id": msg.id,
            "channel_id": ctx.channel.id,
            "guild_id": ctx.guild.id,
            "prize": prize,
            "winners": winners,
            "end_time": end_time.isoformat(),
            "host_id": ctx.author.id,
            "host_name": str(ctx.author),
            "created_at": datetime.now().isoformat(),
            "requirements": {
                "role_id": required_role,
                "min_invites": min_invites
            }
        }
        
        save_giveaways(data)
        await ctx.send("✅ Giveaway créé avec succès !")
    
    # ─────────────────────────────────────────────────────────────────────────
    # COMMANDES DE GESTION
    # ─────────────────────────────────────────────────────────────────────────
    
    @commands.command(name="gend", aliases=["gstop"])
    @commands.has_permissions(manage_guild=True)
    async def end_giveaway_cmd(self, ctx, message_id: int = None):
        """Termine un giveaway manuellement"""
        data = load_giveaways()
        
        if message_id:
            giveaway_id = str(message_id)
        else:
            # Chercher le dernier giveaway du channel
            for gid, g in data["active"].items():
                if g["channel_id"] == ctx.channel.id:
                    giveaway_id = gid
                    break
            else:
                await ctx.send("❌ Aucun giveaway actif trouvé dans ce salon.")
                return
        
        if giveaway_id not in data["active"]:
            await ctx.send("❌ Giveaway non trouvé.")
            return
        
        giveaway = data["active"][giveaway_id]
        await self.end_giveaway(giveaway_id, giveaway)
        await ctx.send("✅ Giveaway terminé !")
    
    @commands.command(name="greroll")
    @commands.has_permissions(manage_guild=True)
    async def reroll_giveaway(self, ctx, message_id: int):
        """Relance le tirage d'un giveaway terminé"""
        data = load_giveaways()
        
        # Chercher dans les giveaways terminés
        giveaway = None
        for g in data["ended"]:
            if g["message_id"] == message_id:
                giveaway = g
                break
        
        if not giveaway:
            await ctx.send("❌ Giveaway terminé non trouvé.")
            return
        
        try:
            channel = self.bot.get_channel(giveaway["channel_id"])
            message = await channel.fetch_message(message_id)
        except:
            await ctx.send("❌ Message introuvable.")
            return
        
        # Récupérer les participants
        participants = []
        for reaction in message.reactions:
            if str(reaction.emoji) == GIVEAWAY_EMOJI:
                async for user in reaction.users():
                    if not user.bot and user.id != giveaway.get("host_id"):
                        if user.id not in giveaway.get("winner_ids", []):
                            participants.append(user)
        
        if not participants:
            await ctx.send("❌ Aucun participant disponible pour un reroll.")
            return
        
        new_winner = random.choice(participants)
        await ctx.send(f"🎉 Nouveau gagnant: {new_winner.mention} a gagné **{giveaway['prize']}** !")
    
    @commands.command(name="glist", aliases=["giveaways"])
    async def list_giveaways(self, ctx):
        """Liste les giveaways actifs"""
        data = load_giveaways()
        active = data.get("active", {})
        
        guild_giveaways = [g for g in active.values() if g["guild_id"] == ctx.guild.id]
        
        if not guild_giveaways:
            await ctx.send("📭 Aucun giveaway actif sur ce serveur.")
            return
        
        embed = discord.Embed(
            title="🎉 Giveaways Actifs",
            color=GIVEAWAY_COLOR
        )
        
        for g in guild_giveaways[:10]:
            end_time = datetime.fromisoformat(g["end_time"])
            channel = self.bot.get_channel(g["channel_id"])
            channel_name = channel.mention if channel else "Inconnu"
            
            embed.add_field(
                name=f"📦 {g['prize']}",
                value=f"Salon: {channel_name}\n"
                      f"Fin: {format_timestamp(end_time)}\n"
                      f"Gagnants: {g['winners']}",
                inline=False
            )
        
        if len(guild_giveaways) > 10:
            embed.set_footer(text=f"+ {len(guild_giveaways) - 10} autres giveaways...")
        
        await ctx.send(embed=embed)
    
    @commands.command(name="gdelete", aliases=["gcancel"])
    @commands.has_permissions(manage_guild=True)
    async def delete_giveaway(self, ctx, message_id: int):
        """Supprime un giveaway sans tirer de gagnant"""
        data = load_giveaways()
        giveaway_id = str(message_id)
        
        if giveaway_id not in data["active"]:
            await ctx.send("❌ Giveaway non trouvé.")
            return
        
        giveaway = data["active"].pop(giveaway_id)
        save_giveaways(data)
        
        try:
            channel = self.bot.get_channel(giveaway["channel_id"])
            message = await channel.fetch_message(message_id)
            
            embed = discord.Embed(
                title="🚫 Giveaway Annulé",
                description=f"**{giveaway['prize']}**\n\nCe giveaway a été annulé.",
                color=0xff0000
            )
            await message.edit(embed=embed)
        except:
            pass
        
        await ctx.send("✅ Giveaway supprimé.")
    
    # ─────────────────────────────────────────────────────────────────────────
    # SYSTÈME D'INVITATIONS
    # ─────────────────────────────────────────────────────────────────────────
    
    @commands.Cog.listener()
    async def on_ready(self):
        """Initialise le cache des invitations"""
        for guild in self.bot.guilds:
            try:
                invites = await guild.invites()
                self.invites_cache[guild.id] = {inv.code: inv.uses for inv in invites}
            except:
                self.invites_cache[guild.id] = {}
    
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        """Track les invitations quand un membre rejoint"""
        try:
            # Récupérer les nouvelles invitations
            new_invites = await member.guild.invites()
            old_invites = self.invites_cache.get(member.guild.id, {})
            
            inviter = None
            for invite in new_invites:
                old_uses = old_invites.get(invite.code, 0)
                if invite.uses > old_uses:
                    inviter = invite.inviter
                    break
            
            # Mettre à jour le cache
            self.invites_cache[member.guild.id] = {inv.code: inv.uses for inv in new_invites}
            
            # Enregistrer l'invitation
            if inviter and inviter.id != member.id:
                data = load_invites()
                inviter_id = str(inviter.id)
                
                if inviter_id not in data:
                    data[inviter_id] = {"total": 0, "active": 0, "invited_users": []}
                
                data[inviter_id]["total"] = data[inviter_id].get("total", 0) + 1
                data[inviter_id]["active"] = data[inviter_id].get("active", 0) + 1
                data[inviter_id]["invited_users"].append({
                    "user_id": member.id,
                    "joined_at": datetime.now().isoformat()
                })
                
                save_invites(data)
        except:
            pass
    
    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        """Track quand un membre invité quitte"""
        data = load_invites()
        
        for inviter_id, inviter_data in data.items():
            invited = inviter_data.get("invited_users", [])
            for inv in invited:
                if inv.get("user_id") == member.id:
                    inviter_data["active"] = max(0, inviter_data.get("active", 0) - 1)
                    break
        
        save_invites(data)
        
        # Mettre à jour le cache
        try:
            invites = await member.guild.invites()
            self.invites_cache[member.guild.id] = {inv.code: inv.uses for inv in invites}
        except:
            pass
    
    @commands.command(name="invites", aliases=["myinvites"])
    async def show_invites(self, ctx, member: Optional[discord.Member] = None):
        """Affiche les invitations d'un membre"""
        target = member or ctx.author
        data = load_invites()
        
        user_data = data.get(str(target.id), {"total": 0, "active": 0})
        
        embed = discord.Embed(
            title=f"📨 Invitations de {target.display_name}",
            color=0x3498db
        )
        
        embed.add_field(name="Total", value=str(user_data.get("total", 0)), inline=True)
        embed.add_field(name="Actives", value=str(user_data.get("active", 0)), inline=True)
        embed.add_field(
            name="Parties",
            value=str(user_data.get("total", 0) - user_data.get("active", 0)),
            inline=True
        )
        
        embed.set_thumbnail(url=target.display_avatar.url)
        await ctx.send(embed=embed)
    
    @commands.command(name="invites_leaderboard", aliases=["topinvites"])
    async def invites_leaderboard(self, ctx):
        """Classement des invitations"""
        data = load_invites()
        
        if not data:
            await ctx.send("Aucune donnée d'invitations.")
            return
        
        # Trier par total
        sorted_invites = sorted(
            data.items(),
            key=lambda x: x[1].get("total", 0),
            reverse=True
        )[:10]
        
        embed = discord.Embed(
            title="📨 Top Inviteurs",
            color=0x3498db
        )
        
        medals = ["🥇", "🥈", "🥉"]
        lines = []
        
        for i, (user_id, udata) in enumerate(sorted_invites):
            try:
                member = await self.bot.fetch_user(int(user_id))
                name = member.display_name
            except:
                name = f"Utilisateur #{user_id[:6]}"
            
            medal = medals[i] if i < 3 else f"**{i+1}.**"
            total = udata.get("total", 0)
            active = udata.get("active", 0)
            lines.append(f"{medal} {name} - **{total}** invites ({active} actives)")
        
        embed.description = "\n".join(lines) if lines else "Aucun inviteur."
        await ctx.send(embed=embed)
    
    @commands.command(name="addinvites")
    @commands.has_permissions(administrator=True)
    async def add_invites(self, ctx, member: discord.Member, amount: int):
        """[Admin] Ajoute des invitations à un membre"""
        data = load_invites()
        user_id = str(member.id)
        
        if user_id not in data:
            data[user_id] = {"total": 0, "active": 0, "invited_users": []}
        
        data[user_id]["total"] = max(0, data[user_id].get("total", 0) + amount)
        data[user_id]["active"] = max(0, data[user_id].get("active", 0) + amount)
        
        save_invites(data)
        
        action = "ajoutées" if amount > 0 else "retirées"
        await ctx.send(f"✅ **{abs(amount)}** invitations {action} à {member.mention}.")
    
    @commands.command(name="resetinvites")
    @commands.has_permissions(administrator=True)
    async def reset_invites(self, ctx, member: Optional[discord.Member] = None):
        """[Admin] Remet à zéro les invitations"""
        data = load_invites()
        
        if member:
            user_id = str(member.id)
            if user_id in data:
                data[user_id] = {"total": 0, "active": 0, "invited_users": []}
                save_invites(data)
            await ctx.send(f"✅ Invitations de {member.mention} remises à zéro.")
        else:
            # Reset tout
            def check(m):
                return m.author == ctx.author and m.channel == ctx.channel
            
            await ctx.send("⚠️ Cela va supprimer TOUTES les invitations. Tape `CONFIRMER` pour continuer.")
            
            try:
                msg = await self.bot.wait_for('message', timeout=30.0, check=check)
                if msg.content == "CONFIRMER":
                    save_invites({})
                    await ctx.send("✅ Toutes les invitations ont été réinitialisées.")
                else:
                    await ctx.send("❌ Annulé.")
            except asyncio.TimeoutError:
                await ctx.send("⏰ Temps écoulé. Annulé.")
    
    # ─────────────────────────────────────────────────────────────────────────
    # STATISTIQUES
    # ─────────────────────────────────────────────────────────────────────────
    
    @commands.command(name="gstats", aliases=["giveaway_stats"])
    async def giveaway_stats(self, ctx, member: Optional[discord.Member] = None):
        """Affiche les statistiques de giveaways"""
        target = member or ctx.author
        data = load_giveaways()
        
        user_stats = data.get("stats", {}).get(str(target.id), {"wins": 0, "participated": 0})
        
        embed = discord.Embed(
            title=f"🎉 Stats Giveaway de {target.display_name}",
            color=GIVEAWAY_COLOR
        )
        
        embed.add_field(name="🏆 Victoires", value=str(user_stats.get("wins", 0)), inline=True)
        embed.add_field(name="🎫 Participations", value=str(user_stats.get("participated", 0)), inline=True)
        
        embed.set_thumbnail(url=target.display_avatar.url)
        await ctx.send(embed=embed)

# ═══════════════════════════════════════════════════════════════════════════════
# SETUP
# ═══════════════════════════════════════════════════════════════════════════════

async def setup(bot):
    await bot.add_cog(Giveaways(bot))