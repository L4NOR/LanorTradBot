# giveaway.py
# Système de Giveaway avec participation par réaction
import discord
from discord.ext import commands, tasks
import json
import os
import asyncio
import random
from datetime import datetime, timedelta
from config import COLORS

GIVEAWAYS_FILE = "data/giveaways.json"
INVITES_FILE = "data/invites_tracker.json"
os.makedirs("data", exist_ok=True)

# Emoji pour participer aux giveaways
GIVEAWAY_EMOJI = "🎉"

# Stockage des giveaways actifs
giveaways_actifs = {}

# Stockage des invitations
invites_tracker = {}

# Cache des invitations du serveur
server_invites = {}

def charger_giveaways():
    """Charge les giveaways depuis le fichier JSON"""
    global giveaways_actifs
    if os.path.exists(GIVEAWAYS_FILE):
        with open(GIVEAWAYS_FILE, "r", encoding="utf-8") as f:
            contenu = f.read().strip()
            if contenu:
                try:
                    giveaways_actifs = json.loads(contenu)
                    print(f"📦 {len(giveaways_actifs)} giveaway(s) chargé(s)")
                except Exception as e:
                    print(f"Erreur lors du chargement des giveaways: {e}")
                    giveaways_actifs = {}
            else:
                giveaways_actifs = {}
    else:
        giveaways_actifs = {}

def sauvegarder_giveaways():
    """Sauvegarde les giveaways dans le fichier JSON"""
    try:
        with open(GIVEAWAYS_FILE, "w", encoding="utf-8") as f:
            json.dump(giveaways_actifs, f, ensure_ascii=False, indent=4)
        print(f"✅ Giveaways sauvegardés ({len(giveaways_actifs)} giveaway(s))")
    except Exception as e:
        print(f"❌ Erreur lors de la sauvegarde des giveaways: {e}")

def charger_invites():
    """Charge les invitations depuis le fichier JSON"""
    global invites_tracker
    if os.path.exists(INVITES_FILE):
        with open(INVITES_FILE, "r", encoding="utf-8") as f:
            contenu = f.read().strip()
            if contenu:
                try:
                    invites_tracker = json.loads(contenu)
                    print(f"📊 Invitations chargées pour {len(invites_tracker)} utilisateurs")
                except Exception as e:
                    print(f"Erreur lors du chargement des invitations: {e}")
                    invites_tracker = {}
            else:
                invites_tracker = {}
    else:
        invites_tracker = {}

def sauvegarder_invites():
    """Sauvegarde les invitations dans le fichier JSON"""
    try:
        with open(INVITES_FILE, "w", encoding="utf-8") as f:
            json.dump(invites_tracker, f, ensure_ascii=False, indent=4)
        print(f"✅ Invitations sauvegardées")
    except Exception as e:
        print(f"❌ Erreur lors de la sauvegarde des invitations: {e}")

def get_user_invites(user_id):
    """Récupère le nombre d'invitations d'un utilisateur"""
    user_id_str = str(user_id)
    if user_id_str not in invites_tracker:
        invites_tracker[user_id_str] = {
            "total": 0,
            "left": 0,
            "fake": 0,
            "real": 0
        }
    return invites_tracker[user_id_str]

def add_invite(user_id):
    """Ajoute une invitation à un utilisateur"""
    user_id_str = str(user_id)
    invites = get_user_invites(user_id)
    invites["total"] += 1
    invites["real"] += 1
    invites_tracker[user_id_str] = invites
    sauvegarder_invites()
    return invites

def remove_invite(user_id):
    """Retire une invitation à un utilisateur"""
    user_id_str = str(user_id)
    invites = get_user_invites(user_id)
    invites["left"] += 1
    invites["real"] = max(0, invites["real"] - 1)
    invites_tracker[user_id_str] = invites
    sauvegarder_invites()
    return invites

def get_participation_entries(invites_count):
    """Calcule le nombre de participations en fonction des invitations"""
    if invites_count < 5:
        return 1  # Participation de base (tout le monde peut participer)
    elif invites_count < 10:
        return 2
    elif invites_count < 20:
        return 3
    elif invites_count < 30:
        return 5
    elif invites_count < 50:
        return 7
    else:
        return 10  # Maximum


class GiveawaySystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        charger_giveaways()
        charger_invites()
        
    async def cog_load(self):
        """Appelé quand le cog est chargé"""
        # Charger les invitations au démarrage
        for guild in self.bot.guilds:
            try:
                server_invites[guild.id] = await guild.invites()
                print(f"📊 Invitations chargées pour {guild.name}")
            except Exception as e:
                print(f"❌ Erreur lors du chargement des invitations pour {guild.name}: {e}")
        
        self.check_giveaways.start()
        print("✅ Système de giveaway démarré")

    async def cog_unload(self):
        """Appelé quand le cog est déchargé"""
        self.check_giveaways.cancel()
        print("🛑 Système de giveaway arrêté")

    # ==================== TRACKING DES INVITATIONS ====================

    @commands.Cog.listener()
    async def on_member_join(self, member):
        """Détecte qui a invité le nouveau membre"""
        if member.bot:
            return
        
        try:
            guild = member.guild
            new_invites = await guild.invites()
            old_invites = server_invites.get(guild.id, [])
            
            for new_invite in new_invites:
                for old_invite in old_invites:
                    if new_invite.code == old_invite.code and new_invite.uses > old_invite.uses:
                        inviter_id = new_invite.inviter.id
                        add_invite(inviter_id)
                        print(f"✅ {new_invite.inviter.name} a invité {member.name}")
                        break
            
            server_invites[guild.id] = new_invites
            
        except Exception as e:
            print(f"❌ Erreur lors de la détection d'invitation: {e}")

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        """Détecte quand un membre quitte"""
        if member.bot:
            return
        
        try:
            guild = member.guild
            new_invites = await guild.invites()
            old_invites = server_invites.get(guild.id, [])
            
            for new_invite in new_invites:
                for old_invite in old_invites:
                    if new_invite.code == old_invite.code and new_invite.uses < old_invite.uses:
                        inviter_id = new_invite.inviter.id
                        remove_invite(inviter_id)
                        print(f"⚠️ {new_invite.inviter.name} a perdu une invitation ({member.name} a quitté)")
                        break
            
            server_invites[guild.id] = new_invites
            
        except Exception as e:
            print(f"❌ Erreur lors de la détection de départ: {e}")

    # ==================== PARTICIPATION PAR RÉACTION ====================

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        """Gère les réactions pour participer aux giveaways"""
        # Ignorer les réactions du bot
        if payload.user_id == self.bot.user.id:
            return
        
        # Vérifier si c'est l'emoji de giveaway
        if str(payload.emoji) != GIVEAWAY_EMOJI:
            return
        
        # Chercher si ce message est un giveaway actif
        giveaway_found = None
        giveaway_id_found = None
        
        for giveaway_id, giveaway in giveaways_actifs.items():
            if giveaway.get("message_id") == payload.message_id and giveaway.get("status") == "active":
                giveaway_found = giveaway
                giveaway_id_found = giveaway_id
                break
        
        if not giveaway_found:
            return
        
        # Récupérer le membre et le canal
        guild = self.bot.get_guild(payload.guild_id)
        if not guild:
            return
        
        member = guild.get_member(payload.user_id)
        if not member:
            return
        
        channel = guild.get_channel(payload.channel_id)
        if not channel:
            return
        
        user_id = str(payload.user_id)
        
        # Vérifier si déjà participant
        if user_id in giveaway_found.get("participants", {}):
            return  # Déjà inscrit, ne rien faire
        
        # Récupérer les invitations pour calculer les entrées
        user_invites = get_user_invites(payload.user_id)
        real_invites = user_invites["real"]
        
        # Ajouter la participation
        entries = get_participation_entries(real_invites)
        
        if "participants" not in giveaway_found:
            giveaway_found["participants"] = {}
        
        giveaway_found["participants"][user_id] = {
            "entries": entries,
            "invites": real_invites,
            "joined_at": datetime.now().isoformat(),
            "username": member.name
        }
        
        sauvegarder_giveaways()
        
        # Mettre à jour l'embed du giveaway
        await self.update_giveaway_embed(giveaway_id_found)
        
        # Envoyer un MP de confirmation
        try:
            embed = discord.Embed(
                title="✅ Participation Enregistrée !",
                description=f"Vous participez au giveaway **{giveaway_found['prize']}** !",
                color=discord.Color.green(),
                timestamp=datetime.now()
            )
            embed.add_field(name="🎫 Vos chances", value=f"**{entries}** entrée(s)", inline=True)
            embed.add_field(name="📨 Vos invitations", value=f"**{real_invites}**", inline=True)
            
            if entries == 1:
                embed.add_field(
                    name="💡 Astuce",
                    value="Invitez des amis pour augmenter vos chances de gagner !",
                    inline=False
                )
            
            embed.set_footer(text="Bonne chance ! 🍀")
            
            await member.send(embed=embed)
        except discord.Forbidden:
            pass  # L'utilisateur a les MPs désactivés

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        """Gère le retrait de réaction (annulation de participation)"""
        if payload.user_id == self.bot.user.id:
            return
        
        if str(payload.emoji) != GIVEAWAY_EMOJI:
            return
        
        # Chercher le giveaway
        for giveaway_id, giveaway in giveaways_actifs.items():
            if giveaway.get("message_id") == payload.message_id and giveaway.get("status") == "active":
                user_id = str(payload.user_id)
                
                if user_id in giveaway.get("participants", {}):
                    del giveaway["participants"][user_id]
                    sauvegarder_giveaways()
                    await self.update_giveaway_embed(giveaway_id)
                    print(f"🚪 {payload.user_id} s'est retiré du giveaway {giveaway_id}")
                break

    # ==================== MISE À JOUR DE L'EMBED ====================

    async def update_giveaway_embed(self, giveaway_id):
        """Met à jour l'embed du giveaway avec le nombre de participants"""
        if giveaway_id not in giveaways_actifs:
            return
        
        giveaway = giveaways_actifs[giveaway_id]
        
        try:
            channel = self.bot.get_channel(giveaway["channel_id"])
            if not channel:
                return
            
            message = await channel.fetch_message(giveaway["message_id"])
            
            participants = giveaway.get("participants", {})
            total_entries = sum(p.get("entries", 1) for p in participants.values())
            end_time = datetime.fromisoformat(giveaway['end_time'])
            
            embed = discord.Embed(
                title="🎉 GIVEAWAY EN COURS ! 🎉",
                description=f"**{giveaway['prize']}**",
                color=discord.Color.gold(),
                timestamp=datetime.now()
            )
            
            if giveaway.get("description"):
                embed.add_field(name="📝 Description", value=giveaway["description"], inline=False)
            
            embed.add_field(name="🏆 Prix", value=giveaway['prize'], inline=True)
            embed.add_field(name="👥 Gagnants", value=str(giveaway['num_winners']), inline=True)
            embed.add_field(name="⏰ Fin", value=f"<t:{int(end_time.timestamp())}:R>", inline=True)
            
            embed.add_field(
                name="━━━━━━━━━━━━━━━━━━━━",
                value="",
                inline=False
            )
            
            embed.add_field(
                name="📊 Participation",
                value=(
                    f"👥 **{len(participants)}** participant(s)\n"
                    f"🎫 **{total_entries}** entrée(s) totales"
                ),
                inline=False
            )
            
            embed.add_field(
                name="━━━━━━━━━━━━━━━━━━━━",
                value="",
                inline=False
            )
            
            embed.add_field(
                name="🎯 Comment participer ?",
                value=f"Réagissez avec {GIVEAWAY_EMOJI} pour participer !",
                inline=False
            )
            
            embed.add_field(
                name="⚡ Bonus Invitations",
                value=(
                    "Invitez des amis pour augmenter vos chances !\n"
                    "• 0-4 invites = 1 entrée\n"
                    "• 5-9 invites = 2 entrées\n"
                    "• 10-19 invites = 3 entrées\n"
                    "• 20+ invites = encore plus !"
                ),
                inline=False
            )
            
            embed.set_footer(text=f"ID: {giveaway_id} | Bonne chance à tous ! 🍀")
            
            await message.edit(embed=embed)
            
        except Exception as e:
            print(f"❌ Erreur mise à jour embed giveaway: {e}")

    # ==================== VÉRIFICATION ET TIRAGE ====================

    @tasks.loop(minutes=1)
    async def check_giveaways(self):
        """Vérifie les giveaways et tire les gagnants automatiquement"""
        now = datetime.now()
        
        for giveaway_id, giveaway in list(giveaways_actifs.items()):
            if giveaway.get("status") == "active":
                end_time = datetime.fromisoformat(giveaway["end_time"])
                
                if now >= end_time:
                    await self.draw_winners(giveaway_id)

    @check_giveaways.before_loop
    async def before_check_giveaways(self):
        """Attend que le bot soit prêt"""
        await self.bot.wait_until_ready()

    async def draw_winners(self, giveaway_id):
        """Tire les gagnants d'un giveaway"""
        if giveaway_id not in giveaways_actifs:
            return
        
        giveaway = giveaways_actifs[giveaway_id]
        
        try:
            channel = self.bot.get_channel(giveaway["channel_id"])
            if not channel:
                print(f"❌ Canal introuvable pour le giveaway {giveaway_id}")
                return
            
            participants = giveaway.get("participants", {})
            
            if not participants:
                # Aucun participant
                embed = discord.Embed(
                    title="❌ Giveaway Terminé - Aucun Gagnant",
                    description=f"**{giveaway['prize']}**\n\nAucun participant éligible.",
                    color=discord.Color.red(),
                    timestamp=datetime.now()
                )
                await channel.send(embed=embed)
                
                giveaways_actifs[giveaway_id]["status"] = "cancelled"
                sauvegarder_giveaways()
                
                # Mettre à jour le message original
                try:
                    message = await channel.fetch_message(giveaway["message_id"])
                    embed_old = message.embeds[0] if message.embeds else None
                    if embed_old:
                        embed_old.title = "❌ GIVEAWAY TERMINÉ - AUCUN GAGNANT"
                        embed_old.color = discord.Color.red()
                        await message.edit(embed=embed_old)
                except:
                    pass
                return
            
            # Créer une liste pondérée des participants
            weighted_participants = []
            for user_id, data in participants.items():
                entries = data.get("entries", 1)
                weighted_participants.extend([user_id] * entries)
            
            # Tirer les gagnants
            num_winners = min(giveaway["num_winners"], len(participants))
            winners = []
            winners_ids = set()
            
            while len(winners) < num_winners and weighted_participants:
                winner_id = random.choice(weighted_participants)
                
                if winner_id not in winners_ids:
                    winners.append(winner_id)
                    winners_ids.add(winner_id)
                
                # Retirer toutes les entrées de ce gagnant
                weighted_participants = [uid for uid in weighted_participants if uid != winner_id]
            
            # Préparer les mentions
            guild = channel.guild
            winners_mentions = []
            winners_data = []
            
            for winner_id in winners:
                member = guild.get_member(int(winner_id))
                if member:
                    winners_mentions.append(member.mention)
                    winners_data.append({
                        "id": winner_id,
                        "name": member.name,
                        "entries": participants[winner_id].get("entries", 1)
                    })
            
            # Créer l'embed d'annonce des gagnants
            embed = discord.Embed(
                title="🎉🏆 GIVEAWAY TERMINÉ ! 🏆🎉",
                description=f"**{giveaway['prize']}**",
                color=discord.Color.gold(),
                timestamp=datetime.now()
            )
            
            if winners_mentions:
                winners_text = "\n".join([f"🎁 {mention}" for mention in winners_mentions])
                embed.add_field(
                    name=f"🏆 Gagnant{'s' if len(winners) > 1 else ''} ({len(winners)})",
                    value=winners_text,
                    inline=False
                )
            
            embed.add_field(
                name="📊 Statistiques",
                value=(
                    f"👥 **{len(participants)}** participant(s)\n"
                    f"🎫 **{sum(p.get('entries', 1) for p in participants.values())}** entrées totales"
                ),
                inline=True
            )
            
            embed.set_footer(text="Félicitations aux gagnants ! 🎊")
            
            # Envoyer l'annonce avec mention des gagnants
            mention_text = " ".join(winners_mentions)
            await channel.send(f"🎉 **FÉLICITATIONS** {mention_text} ! 🎉", embed=embed)
            
            # Mettre à jour le statut
            giveaways_actifs[giveaway_id]["status"] = "ended"
            giveaways_actifs[giveaway_id]["winners"] = winners_data
            giveaways_actifs[giveaway_id]["ended_at"] = datetime.now().isoformat()
            sauvegarder_giveaways()
            
            # Mettre à jour le message original
            try:
                message = await channel.fetch_message(giveaway["message_id"])
                
                embed_ended = discord.Embed(
                    title="🏆 GIVEAWAY TERMINÉ 🏆",
                    description=f"**{giveaway['prize']}**",
                    color=discord.Color.dark_gold(),
                    timestamp=datetime.now()
                )
                
                embed_ended.add_field(
                    name="🏆 Gagnant(s)",
                    value="\n".join(winners_mentions) if winners_mentions else "Aucun",
                    inline=False
                )
                
                embed_ended.add_field(
                    name="📊 Statistiques finales",
                    value=f"👥 {len(participants)} participants",
                    inline=True
                )
                
                embed_ended.set_footer(text=f"ID: {giveaway_id} | Terminé")
                
                await message.edit(embed=embed_ended)
                
            except Exception as e:
                print(f"❌ Erreur mise à jour message giveaway: {e}")
            
            # Envoyer un MP aux gagnants
            for winner_id in winners:
                try:
                    member = guild.get_member(int(winner_id))
                    if member:
                        embed_dm = discord.Embed(
                            title="🎉 VOUS AVEZ GAGNÉ ! 🎉",
                            description=f"Félicitations ! Vous avez gagné **{giveaway['prize']}** !",
                            color=discord.Color.gold(),
                            timestamp=datetime.now()
                        )
                        embed_dm.add_field(
                            name="📋 Prochaines étapes",
                            value="Un membre du staff vous contactera bientôt pour vous remettre votre prix !",
                            inline=False
                        )
                        embed_dm.set_footer(text=f"Giveaway sur {guild.name}")
                        
                        await member.send(embed=embed_dm)
                except discord.Forbidden:
                    pass
                except Exception as e:
                    print(f"❌ Erreur envoi MP gagnant: {e}")
            
        except Exception as e:
            print(f"❌ Erreur lors du tirage des gagnants: {e}")
            import traceback
            traceback.print_exc()

    # ==================== COMMANDES DE CRÉATION ====================

    @commands.command(name="create_giveaway")
    @commands.has_any_role(1326417422663680090, 1330147432847114321)
    async def create_giveaway(self, ctx):
        """Crée un nouveau giveaway interactif"""
        
        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel
        
        try:
            # Étape 1: Nom du prix
            embed = discord.Embed(
                title="🎁 Création d'un Giveaway - Étape 1/4",
                description="### 🏆 Quel est le prix à gagner ?",
                color=discord.Color.blue()
            )
            embed.add_field(name="💡 Exemple", value="`Nitro Classic 1 mois`", inline=False)
            embed.set_footer(text="⏱️ Vous avez 60 secondes")
            await ctx.send(embed=embed)
            
            msg = await self.bot.wait_for("message", timeout=60, check=check)
            prize = msg.content.strip()
            
            # Étape 2: Nombre de gagnants
            embed = discord.Embed(
                title="🎁 Création d'un Giveaway - Étape 2/4",
                description="### 👥 Combien de gagnants ?",
                color=discord.Color.blue()
            )
            embed.add_field(name="💡 Exemple", value="`1` ou `3`", inline=False)
            embed.add_field(name="✅ Prix", value=prize, inline=False)
            await ctx.send(embed=embed)
            
            msg = await self.bot.wait_for("message", timeout=60, check=check)
            num_winners = int(msg.content.strip())
            
            if num_winners < 1:
                await ctx.send("❌ Le nombre de gagnants doit être au moins 1.")
                return
            
            # Étape 3: Durée
            embed = discord.Embed(
                title="🎁 Création d'un Giveaway - Étape 3/4",
                description="### ⏰ Durée du giveaway ?",
                color=discord.Color.blue()
            )
            embed.add_field(
                name="💡 Format",
                value=(
                    "`10m` = 10 minutes\n"
                    "`2h` = 2 heures\n"
                    "`1d` = 1 jour\n"
                    "`7d` = 7 jours"
                ),
                inline=False
            )
            embed.add_field(
                name="✅ Progression",
                value=f"🏆 {prize}\n👥 {num_winners} gagnant(s)",
                inline=False
            )
            await ctx.send(embed=embed)
            
            msg = await self.bot.wait_for("message", timeout=60, check=check)
            duration_str = msg.content.strip().lower()
            
            # Parser la durée
            duration_seconds = 0
            if duration_str.endswith('m'):
                duration_seconds = int(duration_str[:-1]) * 60
            elif duration_str.endswith('h'):
                duration_seconds = int(duration_str[:-1]) * 3600
            elif duration_str.endswith('d'):
                duration_seconds = int(duration_str[:-1]) * 86400
            else:
                duration_seconds = int(duration_str) * 60  # Par défaut en minutes
            
            if duration_seconds < 60:
                await ctx.send("❌ La durée minimum est de 1 minute.")
                return
            
            end_time = datetime.now() + timedelta(seconds=duration_seconds)
            
            # Formater la durée pour l'affichage
            if duration_seconds >= 86400:
                duration_display = f"{duration_seconds // 86400} jour(s)"
            elif duration_seconds >= 3600:
                duration_display = f"{duration_seconds // 3600} heure(s)"
            else:
                duration_display = f"{duration_seconds // 60} minute(s)"
            
            # Étape 4: Description (optionnelle)
            embed = discord.Embed(
                title="🎁 Création d'un Giveaway - Étape 4/4",
                description="### 📝 Description (optionnelle)",
                color=discord.Color.blue()
            )
            embed.add_field(name="💡 Info", value="Tapez `non` pour ignorer", inline=False)
            await ctx.send(embed=embed)
            
            msg = await self.bot.wait_for("message", timeout=120, check=check)
            description = msg.content.strip() if msg.content.lower() not in ["non", "n", "no"] else None
            
            # Confirmation
            embed = discord.Embed(
                title="🎁 Confirmation du Giveaway",
                description="**Vérifiez les informations**",
                color=discord.Color.gold(),
                timestamp=datetime.now()
            )
            
            embed.add_field(name="🏆 Prix", value=prize, inline=True)
            embed.add_field(name="👥 Gagnants", value=str(num_winners), inline=True)
            embed.add_field(name="⏰ Durée", value=duration_display, inline=True)
            embed.add_field(name="📅 Fin", value=f"<t:{int(end_time.timestamp())}:F>", inline=True)
            
            if description:
                embed.add_field(name="📝 Description", value=description[:200], inline=False)
            
            embed.add_field(
                name="━━━━━━━━━━━━━━━━━━━━",
                value="✅ **Confirmer** | ❌ **Annuler**",
                inline=False
            )
            
            confirm_msg = await ctx.send(embed=embed)
            await confirm_msg.add_reaction("✅")
            await confirm_msg.add_reaction("❌")
            
            def check_reaction(reaction, user):
                return user == ctx.author and str(reaction.emoji) in ["✅", "❌"] and reaction.message.id == confirm_msg.id
            
            reaction, _ = await self.bot.wait_for("reaction_add", timeout=30, check=check_reaction)
            await confirm_msg.clear_reactions()
            
            if str(reaction.emoji) == "❌":
                embed = discord.Embed(title="❌ Création Annulée", color=discord.Color.red())
                await ctx.send(embed=embed)
                return
            
            # Créer le giveaway
            giveaway_id = f"gw_{int(datetime.now().timestamp())}"
            
            # Créer l'embed du giveaway
            giveaway_embed = discord.Embed(
                title="🎉 GIVEAWAY EN COURS ! 🎉",
                description=f"**{prize}**",
                color=discord.Color.gold(),
                timestamp=datetime.now()
            )
            
            if description:
                giveaway_embed.add_field(name="📝 Description", value=description, inline=False)
            
            giveaway_embed.add_field(name="🏆 Prix", value=prize, inline=True)
            giveaway_embed.add_field(name="👥 Gagnants", value=str(num_winners), inline=True)
            giveaway_embed.add_field(name="⏰ Fin", value=f"<t:{int(end_time.timestamp())}:R>", inline=True)
            
            giveaway_embed.add_field(name="━━━━━━━━━━━━━━━━━━━━", value="", inline=False)
            
            giveaway_embed.add_field(
                name="📊 Participation",
                value="👥 **0** participant(s)\n🎫 **0** entrée(s) totales",
                inline=False
            )
            
            giveaway_embed.add_field(name="━━━━━━━━━━━━━━━━━━━━", value="", inline=False)
            
            giveaway_embed.add_field(
                name="🎯 Comment participer ?",
                value=f"Réagissez avec {GIVEAWAY_EMOJI} pour participer !",
                inline=False
            )
            
            giveaway_embed.add_field(
                name="⚡ Bonus Invitations",
                value=(
                    "Invitez des amis pour augmenter vos chances !\n"
                    "• 0-4 invites = 1 entrée\n"
                    "• 5-9 invites = 2 entrées\n"
                    "• 10-19 invites = 3 entrées\n"
                    "• 20-29 invites = 5 entrées\n"
                    "• 30-49 invites = 7 entrées\n"
                    "• 50+ invites = 10 entrées"
                ),
                inline=False
            )
            
            giveaway_embed.set_footer(text=f"ID: {giveaway_id} | Bonne chance à tous ! 🍀")
            
            # Envoyer le message du giveaway
            giveaway_msg = await ctx.send("@everyone 🎁 **NOUVEAU GIVEAWAY !** 🎁", embed=giveaway_embed)
            
            # Ajouter la réaction
            await giveaway_msg.add_reaction(GIVEAWAY_EMOJI)
            
            # Sauvegarder le giveaway
            giveaways_actifs[giveaway_id] = {
                "prize": prize,
                "num_winners": num_winners,
                "description": description,
                "end_time": end_time.isoformat(),
                "channel_id": ctx.channel.id,
                "guild_id": ctx.guild.id,
                "message_id": giveaway_msg.id,
                "participants": {},
                "status": "active",
                "created_by": ctx.author.id,
                "created_at": datetime.now().isoformat()
            }
            
            sauvegarder_giveaways()
            
            # Confirmation
            embed = discord.Embed(
                title="✅ Giveaway Créé !",
                description=f"Le giveaway a été créé avec succès !",
                color=discord.Color.green()
            )
            embed.add_field(name="🆔 ID", value=f"`{giveaway_id}`", inline=True)
            embed.add_field(name="⏰ Fin", value=f"<t:{int(end_time.timestamp())}:R>", inline=True)
            await ctx.send(embed=embed, delete_after=10)
            
        except asyncio.TimeoutError:
            embed = discord.Embed(
                title="⏰ Temps Écoulé",
                description="Création annulée.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
        except ValueError as e:
            embed = discord.Embed(
                title="❌ Erreur",
                description=f"Valeur invalide : {e}",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)

    @commands.command(name="giveaway")
    @commands.has_any_role(1326417422663680090, 1330147432847114321)
    async def quick_giveaway(self, ctx, duration: str, winners: int, *, prize: str):
        """
        Crée un giveaway rapidement.
        Usage: !giveaway <durée> <nb_gagnants> <prix>
        Exemple: !giveaway 1d 1 Nitro Classic
        """
        # Parser la durée
        duration_str = duration.lower()
        duration_seconds = 0
        
        if duration_str.endswith('m'):
            duration_seconds = int(duration_str[:-1]) * 60
        elif duration_str.endswith('h'):
            duration_seconds = int(duration_str[:-1]) * 3600
        elif duration_str.endswith('d'):
            duration_seconds = int(duration_str[:-1]) * 86400
        else:
            await ctx.send("❌ Format de durée invalide. Utilisez `10m`, `2h`, ou `1d`.")
            return
        
        if duration_seconds < 60:
            await ctx.send("❌ La durée minimum est de 1 minute.")
            return
        
        end_time = datetime.now() + timedelta(seconds=duration_seconds)
        giveaway_id = f"gw_{int(datetime.now().timestamp())}"
        
        # Créer l'embed
        embed = discord.Embed(
            title="🎉 GIVEAWAY EN COURS ! 🎉",
            description=f"**{prize}**",
            color=discord.Color.gold(),
            timestamp=datetime.now()
        )
        
        embed.add_field(name="🏆 Prix", value=prize, inline=True)
        embed.add_field(name="👥 Gagnants", value=str(winners), inline=True)
        embed.add_field(name="⏰ Fin", value=f"<t:{int(end_time.timestamp())}:R>", inline=True)
        
        embed.add_field(name="━━━━━━━━━━━━━━━━━━━━", value="", inline=False)
        
        embed.add_field(
            name="📊 Participation",
            value="👥 **0** participant(s)",
            inline=True
        )
        
        embed.add_field(
            name="🎯 Comment participer ?",
            value=f"Réagissez avec {GIVEAWAY_EMOJI} !",
            inline=True
        )
        
        embed.set_footer(text=f"ID: {giveaway_id} | Bonne chance ! 🍀")
        
        giveaway_msg = await ctx.send("@everyone 🎁 **NOUVEAU GIVEAWAY !** 🎁", embed=embed)
        await giveaway_msg.add_reaction(GIVEAWAY_EMOJI)
        
        giveaways_actifs[giveaway_id] = {
            "prize": prize,
            "num_winners": winners,
            "description": None,
            "end_time": end_time.isoformat(),
            "channel_id": ctx.channel.id,
            "guild_id": ctx.guild.id,
            "message_id": giveaway_msg.id,
            "participants": {},
            "status": "active",
            "created_by": ctx.author.id,
            "created_at": datetime.now().isoformat()
        }
        
        sauvegarder_giveaways()

    # ==================== COMMANDES DE GESTION ====================

    @commands.command(name="reroll")
    @commands.has_any_role(1326417422663680090, 1330147432847114321)
    async def reroll(self, ctx, giveaway_id: str, count: int = 1):
        """Retirer un/des nouveau(x) gagnant(s) pour un giveaway terminé"""
        if giveaway_id not in giveaways_actifs:
            await ctx.send("❌ Giveaway introuvable.")
            return
        
        giveaway = giveaways_actifs[giveaway_id]
        
        if giveaway["status"] != "ended":
            await ctx.send("❌ Ce giveaway n'est pas encore terminé.")
            return
        
        participants = giveaway.get("participants", {})
        old_winners = [w["id"] for w in giveaway.get("winners", [])]
        
        # Exclure les anciens gagnants
        eligible = {uid: data for uid, data in participants.items() if uid not in old_winners}
        
        if not eligible:
            await ctx.send("❌ Aucun participant éligible pour un reroll.")
            return
        
        # Créer la liste pondérée
        weighted = []
        for uid, data in eligible.items():
            entries = data.get("entries", 1)
            weighted.extend([uid] * entries)
        
        # Tirer les nouveaux gagnants
        new_winners = []
        new_winners_ids = set()
        
        for _ in range(min(count, len(eligible))):
            if not weighted:
                break
            
            winner_id = random.choice(weighted)
            if winner_id not in new_winners_ids:
                new_winners.append(winner_id)
                new_winners_ids.add(winner_id)
                weighted = [uid for uid in weighted if uid != winner_id]
        
        # Annoncer les nouveaux gagnants
        guild = ctx.guild
        mentions = []
        
        for winner_id in new_winners:
            member = guild.get_member(int(winner_id))
            if member:
                mentions.append(member.mention)
        
        if mentions:
            embed = discord.Embed(
                title="🎲 REROLL ! 🎲",
                description=f"**{giveaway['prize']}**\n\n🏆 Nouveau(x) gagnant(s) :\n" + "\n".join([f"🎁 {m}" for m in mentions]),
                color=discord.Color.gold(),
                timestamp=datetime.now()
            )
            await ctx.send(" ".join(mentions), embed=embed)
        else:
            await ctx.send("❌ Impossible de trouver de nouveaux gagnants.")

    @commands.command(name="end_giveaway")
    @commands.has_any_role(1326417422663680090, 1330147432847114321)
    async def end_giveaway(self, ctx, giveaway_id: str):
        """Termine manuellement un giveaway"""
        if giveaway_id not in giveaways_actifs:
            await ctx.send("❌ Giveaway introuvable.")
            return
        
        giveaway = giveaways_actifs[giveaway_id]
        
        if giveaway["status"] != "active":
            await ctx.send("❌ Ce giveaway n'est plus actif.")
            return
        
        # Confirmation
        embed = discord.Embed(
            title="⚠️ Confirmation",
            description=f"Terminer le giveaway **{giveaway['prize']}** maintenant ?",
            color=discord.Color.orange()
        )
        embed.add_field(name="👥 Participants", value=str(len(giveaway.get("participants", {}))), inline=True)
        
        msg = await ctx.send(embed=embed)
        await msg.add_reaction("✅")
        await msg.add_reaction("❌")
        
        def check(reaction, user):
            return user == ctx.author and str(reaction.emoji) in ["✅", "❌"] and reaction.message.id == msg.id
        
        try:
            reaction, _ = await self.bot.wait_for("reaction_add", timeout=30, check=check)
            await msg.clear_reactions()
            
            if str(reaction.emoji) == "❌":
                await ctx.send("❌ Annulé.")
                return
            
            await self.draw_winners(giveaway_id)
            await ctx.send("✅ Giveaway terminé !")
            
        except asyncio.TimeoutError:
            await msg.clear_reactions()
            await ctx.send("⏰ Temps écoulé.")

    @commands.command(name="delete_giveaway")
    @commands.has_any_role(1326417422663680090, 1330147432847114321)
    async def delete_giveaway(self, ctx, giveaway_id: str):
        """Supprime un giveaway"""
        if giveaway_id not in giveaways_actifs:
            await ctx.send("❌ Giveaway introuvable.")
            return
        
        giveaway = giveaways_actifs[giveaway_id]
        del giveaways_actifs[giveaway_id]
        sauvegarder_giveaways()
        
        # Essayer de supprimer le message
        try:
            channel = self.bot.get_channel(giveaway["channel_id"])
            if channel:
                message = await channel.fetch_message(giveaway["message_id"])
                await message.delete()
        except:
            pass
        
        await ctx.send(f"✅ Giveaway **{giveaway['prize']}** supprimé.")

    @commands.command(name="list_giveaways")
    async def list_giveaways(self, ctx):
        """Liste tous les giveaways"""
        if not giveaways_actifs:
            await ctx.send("📋 Aucun giveaway.")
            return
        
        embed = discord.Embed(
            title="📋 Liste des Giveaways",
            description=f"Total: **{len(giveaways_actifs)}**",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        
        for gw_id, gw in list(giveaways_actifs.items())[:10]:
            status_emoji = "🟢" if gw["status"] == "active" else "🔴" if gw["status"] == "ended" else "⚫"
            end_time = datetime.fromisoformat(gw['end_time'])
            participants = len(gw.get("participants", {}))
            
            embed.add_field(
                name=f"{status_emoji} {gw['prize']}",
                value=(
                    f"**ID:** `{gw_id}`\n"
                    f"👥 {participants} participant(s)\n"
                    f"⏰ <t:{int(end_time.timestamp())}:R>"
                ),
                inline=False
            )
        
        await ctx.send(embed=embed)

    @commands.command(name="giveaway_info")
    async def giveaway_info(self, ctx, giveaway_id: str):
        """Affiche les infos d'un giveaway"""
        if giveaway_id not in giveaways_actifs:
            await ctx.send("❌ Giveaway introuvable.")
            return
        
        gw = giveaways_actifs[giveaway_id]
        participants = gw.get("participants", {})
        total_entries = sum(p.get("entries", 1) for p in participants.values())
        end_time = datetime.fromisoformat(gw['end_time'])
        
        status_text = {
            "active": "🟢 Actif",
            "ended": "🔴 Terminé",
            "cancelled": "⚫ Annulé"
        }
        
        embed = discord.Embed(
            title=f"📊 {gw['prize']}",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        
        embed.add_field(name="🏷️ Statut", value=status_text.get(gw["status"], "Inconnu"), inline=True)
        embed.add_field(name="👥 Gagnants", value=str(gw["num_winners"]), inline=True)
        embed.add_field(name="👥 Participants", value=str(len(participants)), inline=True)
        embed.add_field(name="🎫 Entrées", value=str(total_entries), inline=True)
        embed.add_field(name="⏰ Fin", value=f"<t:{int(end_time.timestamp())}:R>", inline=True)
        
        if gw["status"] == "ended" and gw.get("winners"):
            winners_text = "\n".join([f"🏆 {w.get('name', w.get('id'))}" for w in gw["winners"]])
            embed.add_field(name="🏆 Gagnants", value=winners_text, inline=False)
        
        embed.set_footer(text=f"ID: {giveaway_id}")
        await ctx.send(embed=embed)

    @commands.command(name="giveaway_participants")
    @commands.has_any_role(1326417422663680090, 1330147432847114321)
    async def giveaway_participants(self, ctx, giveaway_id: str):
        """Affiche la liste des participants d'un giveaway"""
        if giveaway_id not in giveaways_actifs:
            await ctx.send("❌ Giveaway introuvable.")
            return
        
        gw = giveaways_actifs[giveaway_id]
        participants = gw.get("participants", {})
        
        if not participants:
            await ctx.send("❌ Aucun participant pour ce giveaway.")
            return
        
        embed = discord.Embed(
            title=f"👥 Participants - {gw['prize']}",
            description=f"Total: **{len(participants)}** participants",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        
        # Trier par nombre d'entrées
        sorted_participants = sorted(
            participants.items(),
            key=lambda x: x[1].get("entries", 1),
            reverse=True
        )[:20]
        
        participants_text = ""
        for user_id, data in sorted_participants:
            member = ctx.guild.get_member(int(user_id))
            name = member.display_name if member else data.get("username", user_id)
            entries = data.get("entries", 1)
            participants_text += f"• **{name}** - {entries} entrée(s)\n"
        
        if len(participants) > 20:
            participants_text += f"\n... et {len(participants) - 20} autre(s)"
        
        embed.add_field(name="Liste", value=participants_text, inline=False)
        embed.set_footer(text=f"ID: {giveaway_id}")
        
        await ctx.send(embed=embed)

    # ==================== COMMANDES INVITATIONS ====================

    @commands.command(name="my_invites")
    async def my_invites(self, ctx):
        """Affiche vos statistiques d'invitations"""
        invites = get_user_invites(ctx.author.id)
        entries = get_participation_entries(invites["real"])
        
        embed = discord.Embed(
            title="📊 Vos Invitations",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        
        embed.add_field(name="✅ Valides", value=f"**{invites['real']}**", inline=True)
        embed.add_field(name="📊 Total", value=f"**{invites['total']}**", inline=True)
        embed.add_field(name="👋 Partis", value=f"**{invites['left']}**", inline=True)
        embed.add_field(name="🎫 Entrées Giveaway", value=f"**{entries}**", inline=True)
        
        embed.add_field(
            name="⚡ Tableau des entrées",
            value=(
                "• 0-4 invites = 1 entrée\n"
                "• 5-9 invites = 2 entrées\n"
                "• 10-19 invites = 3 entrées\n"
                "• 20-29 invites = 5 entrées\n"
                "• 30-49 invites = 7 entrées\n"
                "• 50+ invites = 10 entrées"
            ),
            inline=False
        )
        
        embed.set_thumbnail(url=ctx.author.avatar.url if ctx.author.avatar else None)
        embed.set_footer(text="Invitez plus d'amis pour augmenter vos chances !")
        
        await ctx.send(embed=embed)

    @commands.command(name="leaderboard_invites")
    async def leaderboard_invites(self, ctx):
        """Classement des invitations"""
        sorted_invites = sorted(
            invites_tracker.items(),
            key=lambda x: x[1]["real"],
            reverse=True
        )[:10]
        
        embed = discord.Embed(
            title="🏆 Top 10 Invitations",
            color=discord.Color.gold(),
            timestamp=datetime.now()
        )
        
        medals = ["🥇", "🥈", "🥉"]
        
        for i, (user_id, invites) in enumerate(sorted_invites, 1):
            member = ctx.guild.get_member(int(user_id))
            if member:
                medal = medals[i-1] if i <= 3 else f"**{i}.**"
                entries = get_participation_entries(invites['real'])
                embed.add_field(
                    name=f"{medal} {member.display_name}",
                    value=f"✅ **{invites['real']}** invites | 🎫 **{entries}** entrées",
                    inline=False
                )
        
        await ctx.send(embed=embed)

    @commands.command(name="add_invites")
    @commands.has_any_role(1326417422663680090, 1330147432847114321)
    async def add_invites(self, ctx, member: discord.Member, amount: int):
        """(Admin) Ajoute des invitations à un membre"""
        invites = get_user_invites(member.id)
        invites["real"] += amount
        invites["total"] += amount
        sauvegarder_invites()
        
        await ctx.send(f"✅ **{amount}** invitation(s) ajoutée(s) à {member.mention}. Total: **{invites['real']}**")

    @commands.command(name="remove_invites")
    @commands.has_any_role(1326417422663680090, 1330147432847114321)
    async def remove_invites(self, ctx, member: discord.Member, amount: int):
        """(Admin) Retire des invitations à un membre"""
        invites = get_user_invites(member.id)
        invites["real"] = max(0, invites["real"] - amount)
        sauvegarder_invites()
        
        await ctx.send(f"✅ **{amount}** invitation(s) retirée(s) à {member.mention}. Total: **{invites['real']}**")

    @commands.command(name="reset_user_invites")
    @commands.has_any_role(1326417422663680090, 1330147432847114321)
    async def reset_user_invites(self, ctx, member: discord.Member):
        """(Admin) Réinitialise les invitations d'un membre"""
        user_id = str(member.id)
        if user_id in invites_tracker:
            invites_tracker[user_id] = {"total": 0, "left": 0, "fake": 0, "real": 0}
            sauvegarder_invites()
        
        await ctx.send(f"✅ Invitations de {member.mention} réinitialisées.")

    @commands.command(name="server_invite_stats")
    @commands.has_any_role(1326417422663680090, 1330147432847114321)
    async def server_invite_stats(self, ctx):
        """(Admin) Statistiques globales des invitations"""
        total_invites = sum(inv["total"] for inv in invites_tracker.values())
        total_real = sum(inv["real"] for inv in invites_tracker.values())
        total_left = sum(inv["left"] for inv in invites_tracker.values())
        
        embed = discord.Embed(
            title="📊 Statistiques Globales des Invitations",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        
        embed.add_field(name="👥 Inviteurs", value=f"**{len(invites_tracker)}**", inline=True)
        embed.add_field(name="📊 Total invitations", value=f"**{total_invites}**", inline=True)
        embed.add_field(name="✅ Actives", value=f"**{total_real}**", inline=True)
        embed.add_field(name="👋 Partis", value=f"**{total_left}**", inline=True)
        
        await ctx.send(embed=embed)


async def setup(bot):
    """Setup pour discord.py 2.0+"""
    await bot.add_cog(GiveawaySystem(bot))