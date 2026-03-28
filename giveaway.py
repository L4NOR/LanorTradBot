# giveaway.py
# ═══════════════════════════════════════════════════════════════════════════════
# SYSTÈME DE GIVEAWAYS AMÉLIORÉ - Boutons, Embeds riches, Conditions
# ═══════════════════════════════════════════════════════════════════════════════

import discord
from discord.ext import commands, tasks
from config import (
    ADMIN_ROLES, DATA_FILES, GIVEAWAY_ROLES, GIVEAWAY_EMOJI, GIVEAWAY_COLOR, COLORS
)
from utils import load_json, save_json, safe_api_call
import json
import os
import random
import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any

# ═══════════════════════════════════════════════════════════════════════════════
# FICHIERS DE DONNÉES
# ═══════════════════════════════════════════════════════════════════════════════

GIVEAWAYS_FILE = DATA_FILES["giveaways"]
INVITES_FILE = DATA_FILES["invites"]

# ═══════════════════════════════════════════════════════════════════════════════
# FONCTIONS UTILITAIRES
# ═══════════════════════════════════════════════════════════════════════════════

def ensure_data_dir():
    os.makedirs("data", exist_ok=True)

def load_giveaways() -> Dict:
    ensure_data_dir()
    if os.path.exists(GIVEAWAYS_FILE):
        try:
            with open(GIVEAWAYS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {"active": {}, "ended": [], "stats": {}}
    return {"active": {}, "ended": [], "stats": {}}

def save_giveaways(data: Dict):
    ensure_data_dir()
    with open(GIVEAWAYS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def load_invites() -> Dict:
    ensure_data_dir()
    if os.path.exists(INVITES_FILE):
        try:
            with open(INVITES_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}
    return {}

def save_invites(data: Dict):
    ensure_data_dir()
    with open(INVITES_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def parse_duration(duration_str: str) -> Optional[timedelta]:
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
    return f"<t:{int(dt.timestamp())}:R>"

def format_timestamp_full(dt: datetime) -> str:
    return f"<t:{int(dt.timestamp())}:F>"


# ═══════════════════════════════════════════════════════════════════════════════
# VUES DISCORD (BOUTONS)
# ═══════════════════════════════════════════════════════════════════════════════

class GiveawayView(discord.ui.View):
    """Vue persistante avec boutons pour les giveaways"""

    def __init__(self, giveaway_id: str, bot=None):
        super().__init__(timeout=None)
        self.giveaway_id = giveaway_id
        self.bot = bot

    @discord.ui.button(
        label="🎉 Participer",
        style=discord.ButtonStyle.green,
        custom_id="giveaway_join"
    )
    async def join_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Bouton de participation au giveaway"""
        data = load_giveaways()
        giveaway = data["active"].get(self.giveaway_id)

        if not giveaway:
            await interaction.response.send_message(
                "❌ Ce giveaway est terminé !",
                ephemeral=True
            )
            return

        user_id = interaction.user.id

        # Vérifier si l'utilisateur est l'organisateur
        if user_id == giveaway.get("host_id"):
            await interaction.response.send_message(
                "❌ Tu ne peux pas participer à ton propre giveaway !",
                ephemeral=True
            )
            return

        # Vérifier les conditions
        requirements = giveaway.get("requirements", {})
        requirement_check = await self.check_user_requirements(interaction.user, requirements, interaction.guild)
        if not requirement_check["passed"]:
            await interaction.response.send_message(
                f"❌ Tu ne remplis pas les conditions :\n{requirement_check['reason']}",
                ephemeral=True
            )
            return

        # Ajouter/retirer le participant
        participants = giveaway.get("participants", [])

        if user_id in participants:
            participants.remove(user_id)
            giveaway["participants"] = participants
            data["active"][self.giveaway_id] = giveaway
            save_giveaways(data)

            await interaction.response.send_message(
                "🚫 Tu as retiré ta participation au giveaway.",
                ephemeral=True
            )
        else:
            participants.append(user_id)
            giveaway["participants"] = participants
            data["active"][self.giveaway_id] = giveaway
            save_giveaways(data)

            # Calculer entrées bonus
            entries = calculate_entries(interaction.user, interaction.guild)
            entry_text = f" (**{entries} entrée(s)** grâce à tes rôles !)" if entries > 1 else ""

            await interaction.response.send_message(
                f"✅ Tu participes au giveaway pour **{giveaway['prize']}** !{entry_text}",
                ephemeral=True
            )

        # Mettre à jour le compteur dans l'embed
        try:
            embed = interaction.message.embeds[0] if interaction.message.embeds else None
            if embed:
                new_embed = update_giveaway_embed(giveaway, len(participants))
                await interaction.message.edit(embed=new_embed, view=self)
        except:
            pass

    @discord.ui.button(
        label="📋 Participants",
        style=discord.ButtonStyle.grey,
        custom_id="giveaway_participants"
    )
    async def participants_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Affiche le nombre de participants"""
        data = load_giveaways()
        giveaway = data["active"].get(self.giveaway_id)

        if not giveaway:
            await interaction.response.send_message("❌ Ce giveaway est terminé !", ephemeral=True)
            return

        participants = giveaway.get("participants", [])
        nb = len(participants)

        if nb == 0:
            await interaction.response.send_message("📭 Aucun participant pour le moment.", ephemeral=True)
            return

        # Afficher les participants (max 20)
        lines = []
        for i, uid in enumerate(participants[:20], 1):
            lines.append(f"`{i}.` <@{uid}>")
        if nb > 20:
            lines.append(f"*...et {nb - 20} autres*")

        embed = discord.Embed(
            title=f"📋 Participants ({nb})",
            description="\n".join(lines),
            color=GIVEAWAY_COLOR
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(
        label="ℹ️ Conditions",
        style=discord.ButtonStyle.grey,
        custom_id="giveaway_info"
    )
    async def info_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Affiche les conditions du giveaway"""
        data = load_giveaways()
        giveaway = data["active"].get(self.giveaway_id)

        if not giveaway:
            await interaction.response.send_message("❌ Ce giveaway est terminé !", ephemeral=True)
            return

        requirements = giveaway.get("requirements", {})
        conditions = format_requirements(requirements, interaction.guild)

        embed = discord.Embed(
            title="ℹ️ Informations du Giveaway",
            color=GIVEAWAY_COLOR
        )
        embed.add_field(name="🎁 Prix", value=giveaway["prize"], inline=True)
        embed.add_field(name="🏆 Gagnants", value=str(giveaway.get("winners", 1)), inline=True)
        embed.add_field(name="⏰ Fin", value=format_timestamp(datetime.fromisoformat(giveaway["end_time"])), inline=True)

        if conditions:
            embed.add_field(name="📋 Conditions", value=conditions, inline=False)
        else:
            embed.add_field(name="📋 Conditions", value="Aucune condition requise !", inline=False)

        # Vérifier si l'utilisateur remplit les conditions
        check = await self.check_user_requirements(interaction.user, requirements, interaction.guild)
        if check["passed"]:
            embed.add_field(name="✅ Ton éligibilité", value="Tu remplis toutes les conditions !", inline=False)
        else:
            embed.add_field(name="❌ Ton éligibilité", value=check["reason"], inline=False)

        await interaction.response.send_message(embed=embed, ephemeral=True)

    async def check_user_requirements(self, user, requirements, guild):
        """Vérifie les conditions pour un utilisateur"""
        reasons = []

        try:
            member = guild.get_member(user.id) or await guild.fetch_member(user.id)
        except:
            return {"passed": False, "reason": "Impossible de vérifier ton profil."}

        # Rôle requis
        if requirements.get("role_id"):
            role = guild.get_role(requirements["role_id"])
            if role and role not in member.roles:
                reasons.append(f"• Rôle requis : {role.mention}")

        # Âge du compte
        if requirements.get("min_account_age_days"):
            age = (datetime.now() - member.created_at.replace(tzinfo=None)).days
            if age < requirements["min_account_age_days"]:
                reasons.append(f"• Compte de +{requirements['min_account_age_days']} jours requis (tu as {age}j)")

        # Ancienneté serveur
        if requirements.get("min_server_days"):
            if member.joined_at:
                server_age = (datetime.now() - member.joined_at.replace(tzinfo=None)).days
                if server_age < requirements["min_server_days"]:
                    reasons.append(f"• Membre depuis +{requirements['min_server_days']} jours requis (tu as {server_age}j)")

        # Invitations
        if requirements.get("min_invites"):
            invites_data = load_invites()
            user_invites = invites_data.get(str(user.id), {}).get("total", 0)
            if user_invites < requirements["min_invites"]:
                reasons.append(f"• {requirements['min_invites']} invitations requises (tu en as {user_invites})")

        # Niveau minimum
        if requirements.get("min_level"):
            try:
                from community import get_user_stats, calculate_level
                stats = get_user_stats(user.id)
                level = calculate_level(stats.get("total_xp", stats.get("total_points_earned", 0)))
                if level < requirements["min_level"]:
                    reasons.append(f"• Niveau {requirements['min_level']} requis (tu es niveau {level})")
            except:
                pass

        # Messages minimum
        if requirements.get("min_messages"):
            try:
                from community import get_user_stats
                stats = get_user_stats(user.id)
                msg_count = stats.get("messages_count", 0)
                if msg_count < requirements["min_messages"]:
                    reasons.append(f"• {requirements['min_messages']} messages requis (tu en as {msg_count})")
            except:
                pass

        if reasons:
            return {"passed": False, "reason": "\n".join(reasons)}
        return {"passed": True, "reason": ""}


def calculate_entries(user: discord.User, guild: discord.Guild) -> int:
    """Calcule le nombre d'entrées bonus pour un utilisateur"""
    entries = 1
    try:
        member = guild.get_member(user.id)
        if not member:
            return entries

        if GIVEAWAY_ROLES.get("vip_role"):
            vip_role = guild.get_role(GIVEAWAY_ROLES["vip_role"])
            if vip_role and vip_role in member.roles:
                entries = 2

        if GIVEAWAY_ROLES.get("bonus_role"):
            bonus_role = guild.get_role(GIVEAWAY_ROLES["bonus_role"])
            if bonus_role and bonus_role in member.roles:
                entries += 1
    except:
        pass
    return entries


def format_requirements(requirements: Dict, guild: discord.Guild = None) -> str:
    """Formate les conditions en texte lisible"""
    lines = []
    if requirements.get("role_id"):
        if guild:
            role = guild.get_role(requirements["role_id"])
            lines.append(f"🏷️ Rôle requis : {role.mention if role else 'Inconnu'}")
        else:
            lines.append(f"🏷️ Rôle requis")

    if requirements.get("min_level"):
        lines.append(f"⭐ Niveau minimum : **{requirements['min_level']}**")

    if requirements.get("min_messages"):
        lines.append(f"💬 Messages minimum : **{requirements['min_messages']}**")

    if requirements.get("min_invites"):
        lines.append(f"📨 Invitations minimum : **{requirements['min_invites']}**")

    if requirements.get("min_account_age_days"):
        lines.append(f"📅 Âge du compte : **{requirements['min_account_age_days']}** jours")

    if requirements.get("min_server_days"):
        lines.append(f"🏠 Membre depuis : **{requirements['min_server_days']}** jours")

    return "\n".join(lines) if lines else ""


def create_giveaway_embed(prize, end_time, winners, host, participants_count=0, requirements=None, guild=None):
    """Crée l'embed riche pour un giveaway"""
    embed = discord.Embed(
        title="🎉 GIVEAWAY !",
        description=f"# 🎁 {prize}",
        color=GIVEAWAY_COLOR,
        timestamp=end_time
    )

    embed.add_field(name="⏰ Fin", value=format_timestamp(end_time), inline=True)
    embed.add_field(name="🏆 Gagnants", value=str(winners), inline=True)
    embed.add_field(name="👥 Participants", value=str(participants_count), inline=True)

    embed.add_field(name="👤 Organisé par", value=f"{host.mention}", inline=True)

    # Conditions
    if requirements:
        conditions = format_requirements(requirements, guild)
        if conditions:
            embed.add_field(name="📋 Conditions", value=conditions, inline=False)

    embed.add_field(
        name="💡 Comment participer",
        value="Clique sur le bouton **🎉 Participer** ci-dessous !",
        inline=False
    )

    if guild and guild.icon:
        embed.set_thumbnail(url=guild.icon.url)

    embed.set_footer(text="Fin du giveaway")

    return embed


def update_giveaway_embed(giveaway: Dict, participants_count: int) -> discord.Embed:
    """Met à jour l'embed d'un giveaway existant"""
    end_time = datetime.fromisoformat(giveaway["end_time"])
    requirements = giveaway.get("requirements", {})

    embed = discord.Embed(
        title="🎉 GIVEAWAY !",
        description=f"# 🎁 {giveaway['prize']}",
        color=GIVEAWAY_COLOR,
        timestamp=end_time
    )

    embed.add_field(name="⏰ Fin", value=format_timestamp(end_time), inline=True)
    embed.add_field(name="🏆 Gagnants", value=str(giveaway.get("winners", 1)), inline=True)
    embed.add_field(name="👥 Participants", value=str(participants_count), inline=True)

    embed.add_field(name="👤 Organisé par", value=f"<@{giveaway.get('host_id', 0)}>", inline=True)

    conditions = format_requirements(requirements)
    if conditions:
        embed.add_field(name="📋 Conditions", value=conditions, inline=False)

    embed.add_field(
        name="💡 Comment participer",
        value="Clique sur le bouton **🎉 Participer** ci-dessous !",
        inline=False
    )

    embed.set_footer(text="Fin du giveaway")

    return embed


# ═══════════════════════════════════════════════════════════════════════════════
# COG DISCORD
# ═══════════════════════════════════════════════════════════════════════════════

class Giveaways(commands.Cog):
    """Système de giveaways avec boutons et conditions"""

    def __init__(self, bot):
        self.bot = bot
        self.invites_cache = {}
        self.check_giveaways.start()

    def cog_unload(self):
        self.check_giveaways.cancel()

    # ─────────────────────────────────────────────────────────────────────────
    # RESTAURATION DES VUES AU REDÉMARRAGE
    # ─────────────────────────────────────────────────────────────────────────

    @commands.Cog.listener()
    async def on_ready(self):
        """Restaure les vues des giveaways actifs et initialise les invitations"""
        # Restaurer les vues persistantes
        data = load_giveaways()
        for giveaway_id in data.get("active", {}):
            view = GiveawayView(giveaway_id, self.bot)
            self.bot.add_view(view, message_id=int(giveaway_id))

        # Initialiser le cache des invitations
        for guild in self.bot.guilds:
            try:
                invites = await guild.invites()
                self.invites_cache[guild.id] = {inv.code: inv.uses for inv in invites}
            except:
                self.invites_cache[guild.id] = {}

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
            if giveaway_id in data["active"]:
                data["active"].pop(giveaway_id)
                save_giveaways(data)
            return

        guild = channel.guild

        # Récupérer les participants depuis les données (boutons)
        participant_ids = giveaway.get("participants", [])

        # Construire la liste avec entrées bonus - optimisé anti-rate-limit
        participants = []
        fetch_count = 0
        for uid in participant_ids:
            try:
                member = guild.get_member(uid)
                if not member:
                    # Limiter les fetch API : max 10 fetch par giveaway, skip le reste
                    if fetch_count >= 10:
                        continue
                    member = await safe_api_call(guild.fetch_member, uid)
                    fetch_count += 1
                    if fetch_count % 3 == 0:
                        await asyncio.sleep(2)  # Pause tous les 3 fetch
                if member:
                    entries = calculate_entries(member, guild)
                    for _ in range(entries):
                        participants.append(member)
            except:
                continue

        winners_count = giveaway.get("winners", 1)
        prize = giveaway.get("prize", "Prix mystère")

        # Tirer les gagnants
        if len(participants) == 0:
            embed = discord.Embed(
                title="🎉 Giveaway Terminé",
                description=f"# 🎁 {prize}\n\n❌ Aucun participant valide !",
                color=0xff0000,
                timestamp=datetime.now()
            )
            embed.set_footer(text=f"Organisé par {giveaway.get('host_name', 'Inconnu')}")
        else:
            unique_participants = list(set(participants))
            winners = random.sample(unique_participants, min(winners_count, len(unique_participants)))

            winners_mentions = ", ".join([w.mention for w in winners])

            embed = discord.Embed(
                title="🎉 Giveaway Terminé !",
                description=f"# 🎁 {prize}\n\n🏆 **Gagnant(s):** {winners_mentions}",
                color=0x00ff00,
                timestamp=datetime.now()
            )
            embed.add_field(name="👥 Participants", value=str(len(participant_ids)), inline=True)
            embed.add_field(name="👤 Organisateur", value=f"<@{giveaway.get('host_id', 0)}>", inline=True)
            embed.set_footer(text=f"Organisé par {giveaway.get('host_name', 'Inconnu')}")

            # Notification des gagnants
            congrats_embed = discord.Embed(
                title="🎊 Félicitations !",
                description=f"{winners_mentions}\n\nVous avez gagné **{prize}** !\nContactez <@{giveaway.get('host_id', 0)}> pour récupérer votre prix.",
                color=0xFFD700
            )
            await channel.send(embed=congrats_embed, reference=message)

            # Enregistrer les stats
            for winner in winners:
                user_id = str(winner.id)
                if user_id not in data.get("stats", {}):
                    data["stats"][user_id] = {"wins": 0, "participated": 0}
                data["stats"][user_id]["wins"] = data["stats"][user_id].get("wins", 0) + 1

            # Badge giveaway winner
            try:
                from achievements import unlock_badge
                for winner in winners:
                    unlock_badge(winner.id, "giveaway_winner")
            except ImportError:
                pass

        # Mettre à jour le message original (désactiver les boutons)
        try:
            disabled_view = discord.ui.View()
            disabled_button = discord.ui.Button(
                label="🎉 Terminé",
                style=discord.ButtonStyle.grey,
                disabled=True
            )
            disabled_view.add_item(disabled_button)
            await message.edit(embed=embed, view=disabled_view)
        except:
            try:
                await message.edit(embed=embed, view=None)
            except:
                pass

        # Déplacer vers ended
        giveaway["ended_at"] = datetime.now().isoformat()
        giveaway["winner_ids"] = [w.id for w in winners] if participants else []
        data["ended"].append(giveaway)

        if giveaway_id in data["active"]:
            del data["active"][giveaway_id]

        save_giveaways(data)

    # ─────────────────────────────────────────────────────────────────────────
    # COMMANDES DE CRÉATION
    # ─────────────────────────────────────────────────────────────────────────

    @commands.command(name="giveaway", aliases=["gstart", "gcreate"])
    @commands.has_permissions(manage_guild=True)
    async def create_giveaway(self, ctx, duration: str, winners: int, *, prize: str):
        """
        Crée un nouveau giveaway avec boutons

        Usage: !giveaway <durée> <nb_gagnants> <prix>
        Durée: 1d, 12h, 30m, 1d12h, etc.

        Exemple: !giveaway 1d 1 Nitro Classic
        """
        td = parse_duration(duration)
        if not td:
            await ctx.send("❌ Format de durée invalide. Utilise: `1d`, `12h`, `30m`, `1d12h`, etc.")
            return

        if winners < 1 or winners > 20:
            await ctx.send("❌ Le nombre de gagnants doit être entre 1 et 20.")
            return

        if len(prize) > 256:
            await ctx.send("❌ Le prix est trop long (max 256 caractères).")
            return

        end_time = datetime.now() + td

        embed = create_giveaway_embed(
            prize=prize,
            end_time=end_time,
            winners=winners,
            host=ctx.author,
            participants_count=0,
            guild=ctx.guild
        )

        # Créer les boutons
        msg = await ctx.send(embed=embed)

        giveaway_id = str(msg.id)
        view = GiveawayView(giveaway_id, self.bot)
        await msg.edit(view=view)
        self.bot.add_view(view, message_id=msg.id)

        # Sauvegarder
        data = load_giveaways()
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
            "participants": [],
            "requirements": {}
        }
        save_giveaways(data)

        try:
            await ctx.message.delete()
        except:
            pass

    @commands.command(name="giveaway_advanced", aliases=["gadvanced"])
    @commands.has_permissions(manage_guild=True)
    async def create_advanced_giveaway(self, ctx):
        """
        Crée un giveaway avec conditions de participation (interactif)
        """
        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel

        try:
            # Étape 1: Prix
            embed = discord.Embed(
                title="🎉 Création de giveaway avancé",
                description="**Étape 1/6** — Quel est le **prix** ?",
                color=GIVEAWAY_COLOR
            )
            await ctx.send(embed=embed)
            msg = await self.bot.wait_for('message', timeout=60.0, check=check)
            prize = msg.content

            # Étape 2: Durée
            embed = discord.Embed(
                title="🎉 Création de giveaway avancé",
                description="**Étape 2/6** — Quelle est la **durée** ?\n*Ex: `1d`, `12h`, `1d12h`, `30m`*",
                color=GIVEAWAY_COLOR
            )
            await ctx.send(embed=embed)
            msg = await self.bot.wait_for('message', timeout=60.0, check=check)
            duration = parse_duration(msg.content)
            if not duration:
                await ctx.send("❌ Durée invalide. Annulé.")
                return

            # Étape 3: Nombre de gagnants
            embed = discord.Embed(
                title="🎉 Création de giveaway avancé",
                description="**Étape 3/6** — Combien de **gagnants** ? (1-20)",
                color=GIVEAWAY_COLOR
            )
            await ctx.send(embed=embed)
            msg = await self.bot.wait_for('message', timeout=60.0, check=check)
            try:
                winners = int(msg.content)
                if winners < 1 or winners > 20:
                    raise ValueError()
            except:
                await ctx.send("❌ Nombre invalide. Annulé.")
                return

            # Étape 4: Rôle requis
            embed = discord.Embed(
                title="🎉 Création de giveaway avancé",
                description="**Étape 4/6** — **Rôle requis** ?\n*Mentionne le rôle ou tape `non`*",
                color=GIVEAWAY_COLOR
            )
            await ctx.send(embed=embed)
            msg = await self.bot.wait_for('message', timeout=60.0, check=check)
            required_role = None
            if msg.role_mentions:
                required_role = msg.role_mentions[0].id

            # Étape 5: Niveau minimum
            embed = discord.Embed(
                title="🎉 Création de giveaway avancé",
                description="**Étape 5/6** — **Niveau minimum** requis ?\n*Nombre ou `0` pour aucun*",
                color=GIVEAWAY_COLOR
            )
            await ctx.send(embed=embed)
            msg = await self.bot.wait_for('message', timeout=60.0, check=check)
            try:
                min_level = int(msg.content)
            except:
                min_level = 0

            # Étape 6: Messages minimum
            embed = discord.Embed(
                title="🎉 Création de giveaway avancé",
                description="**Étape 6/6** — **Messages minimum** requis ?\n*Nombre ou `0` pour aucun*",
                color=GIVEAWAY_COLOR
            )
            await ctx.send(embed=embed)
            msg = await self.bot.wait_for('message', timeout=60.0, check=check)
            try:
                min_messages = int(msg.content)
            except:
                min_messages = 0

        except asyncio.TimeoutError:
            await ctx.send("⏰ Temps écoulé. Giveaway annulé.")
            return

        # Construire les requirements
        requirements = {}
        if required_role:
            requirements["role_id"] = required_role
        if min_level > 0:
            requirements["min_level"] = min_level
        if min_messages > 0:
            requirements["min_messages"] = min_messages

        end_time = datetime.now() + duration

        embed = create_giveaway_embed(
            prize=prize,
            end_time=end_time,
            winners=winners,
            host=ctx.author,
            participants_count=0,
            requirements=requirements,
            guild=ctx.guild
        )

        msg = await ctx.send(embed=embed)

        giveaway_id = str(msg.id)
        view = GiveawayView(giveaway_id, self.bot)
        await msg.edit(view=view)
        self.bot.add_view(view, message_id=msg.id)

        # Sauvegarder
        data = load_giveaways()
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
            "participants": [],
            "requirements": requirements
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

        giveaway = None
        for g in data["ended"]:
            if g["message_id"] == message_id:
                giveaway = g
                break

        if not giveaway:
            await ctx.send("❌ Giveaway terminé non trouvé.")
            return

        # Utiliser les participants stockés
        participant_ids = giveaway.get("participants", [])
        old_winners = giveaway.get("winner_ids", [])

        eligible = [uid for uid in participant_ids if uid not in old_winners]

        if not eligible:
            # Fallback: essayer via les réactions (ancien système)
            try:
                channel = self.bot.get_channel(giveaway["channel_id"])
                message = await channel.fetch_message(message_id)
                for reaction in message.reactions:
                    if str(reaction.emoji) == GIVEAWAY_EMOJI:
                        async for user in reaction.users():
                            if not user.bot and user.id != giveaway.get("host_id") and user.id not in old_winners:
                                eligible.append(user.id)
            except:
                pass

        if not eligible:
            await ctx.send("❌ Aucun participant disponible pour un reroll.")
            return

        winner_id = random.choice(eligible)
        await ctx.send(f"🎉 Nouveau gagnant: <@{winner_id}> a gagné **{giveaway['prize']}** !")

    @commands.command(name="glist", aliases=["giveaways"])
    @commands.cooldown(1, 5, commands.BucketType.user)
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
            color=GIVEAWAY_COLOR,
            timestamp=datetime.now()
        )

        for g in guild_giveaways[:10]:
            end_time = datetime.fromisoformat(g["end_time"])
            channel = self.bot.get_channel(g["channel_id"])
            channel_name = channel.mention if channel else "Inconnu"
            nb_participants = len(g.get("participants", []))

            conditions = []
            reqs = g.get("requirements", {})
            if reqs.get("min_level"):
                conditions.append(f"Nv.{reqs['min_level']}")
            if reqs.get("min_messages"):
                conditions.append(f"{reqs['min_messages']} msgs")
            if reqs.get("role_id"):
                conditions.append("Rôle requis")

            conditions_text = f"\n📋 {', '.join(conditions)}" if conditions else ""

            embed.add_field(
                name=f"🎁 {g['prize']}",
                value=f"📍 {channel_name}\n"
                      f"⏰ Fin: {format_timestamp(end_time)}\n"
                      f"🏆 {g['winners']} gagnant(s) • 👥 {nb_participants} participant(s)"
                      f"{conditions_text}",
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
                description=f"**{giveaway['prize']}**\n\nCe giveaway a été annulé par un administrateur.",
                color=0xff0000,
                timestamp=datetime.now()
            )
            await message.edit(embed=embed, view=None)
        except:
            pass

        await ctx.send("✅ Giveaway supprimé.")

    # ─────────────────────────────────────────────────────────────────────────
    # SYSTÈME D'INVITATIONS
    # ─────────────────────────────────────────────────────────────────────────

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        """Track les invitations quand un membre rejoint"""
        try:
            new_invites = await member.guild.invites()
            old_invites = self.invites_cache.get(member.guild.id, {})

            inviter = None
            for invite in new_invites:
                old_uses = old_invites.get(invite.code, 0)
                if invite.uses > old_uses:
                    inviter = invite.inviter
                    break

            self.invites_cache[member.guild.id] = {inv.code: inv.uses for inv in new_invites}

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

        try:
            invites = await member.guild.invites()
            self.invites_cache[member.guild.id] = {inv.code: inv.uses for inv in invites}
        except:
            pass

    @commands.command(name="invites", aliases=["myinvites"])
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def show_invites(self, ctx, member: Optional[discord.Member] = None):
        """Affiche les invitations d'un membre"""
        target = member or ctx.author
        data = load_invites()
        user_data = data.get(str(target.id), {"total": 0, "active": 0})

        embed = discord.Embed(
            title=f"📨 Invitations de {target.display_name}",
            color=COLORS["info"]
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

        sorted_invites = sorted(
            data.items(),
            key=lambda x: x[1].get("total", 0),
            reverse=True
        )[:10]

        embed = discord.Embed(title="📨 Top Inviteurs", color=COLORS["info"])
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
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def giveaway_stats(self, ctx, member: Optional[discord.Member] = None):
        """Affiche les statistiques de giveaways"""
        target = member or ctx.author
        data = load_giveaways()
        stats = data.get("stats", {}).get(str(target.id), {"wins": 0, "participated": 0})

        embed = discord.Embed(
            title=f"🎉 Stats Giveaway de {target.display_name}",
            color=GIVEAWAY_COLOR
        )
        embed.add_field(name="🏆 Victoires", value=str(stats.get("wins", 0)), inline=True)
        embed.add_field(name="🎫 Participations", value=str(stats.get("participated", 0)), inline=True)
        embed.set_thumbnail(url=target.display_avatar.url)
        await ctx.send(embed=embed)


# ═══════════════════════════════════════════════════════════════════════════════
# SETUP
# ═══════════════════════════════════════════════════════════════════════════════

async def setup(bot):
    await bot.add_cog(Giveaways(bot))
