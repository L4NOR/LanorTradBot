# giveaway.py
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
        return 0  # Pas éligible
    elif invites_count < 10:
        return 1  # Participation de base
    elif invites_count < 20:
        return 2
    elif invites_count < 30:
        return 3
    elif invites_count < 50:
        return 5
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

    @commands.Cog.listener()
    async def on_member_join(self, member):
        """Détecte qui a invité le nouveau membre"""
        if member.bot:
            return
        
        try:
            guild = member.guild
            
            # Récupérer les nouvelles invitations
            new_invites = await guild.invites()
            
            # Comparer avec l'ancien cache
            old_invites = server_invites.get(guild.id, [])
            
            # Trouver quelle invitation a été utilisée
            for new_invite in new_invites:
                for old_invite in old_invites:
                    if new_invite.code == old_invite.code and new_invite.uses > old_invite.uses:
                        # Cette invitation a été utilisée
                        inviter_id = new_invite.inviter.id
                        add_invite(inviter_id)
                        
                        # Message de confirmation (optionnel)
                        print(f"✅ {new_invite.inviter.name} a invité {member.name}")
                        break
            
            # Mettre à jour le cache
            server_invites[guild.id] = new_invites
            
        except Exception as e:
            print(f"❌ Erreur lors de la détection d'invitation: {e}")

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        """Détecte quand un membre quitte (retire une invitation)"""
        if member.bot:
            return
        
        try:
            guild = member.guild
            
            # Récupérer les nouvelles invitations
            new_invites = await guild.invites()
            
            # Comparer avec l'ancien cache
            old_invites = server_invites.get(guild.id, [])
            
            # Trouver quelle invitation a perdu une utilisation
            for new_invite in new_invites:
                for old_invite in old_invites:
                    if new_invite.code == old_invite.code and new_invite.uses < old_invite.uses:
                        # Cette invitation a perdu une utilisation
                        inviter_id = new_invite.inviter.id
                        remove_invite(inviter_id)
                        
                        print(f"⚠️ {new_invite.inviter.name} a perdu une invitation ({member.name} a quitté)")
                        break
            
            # Mettre à jour le cache
            server_invites[guild.id] = new_invites
            
        except Exception as e:
            print(f"❌ Erreur lors de la détection de départ: {e}")

    @tasks.loop(minutes=5)
    async def check_giveaways(self):
        """Vérifie les giveaways et tire les gagnants automatiquement"""
        now = datetime.now()
        
        for giveaway_id, giveaway in list(giveaways_actifs.items()):
            if giveaway.get("status") == "active":
                end_time = datetime.fromisoformat(giveaway["end_time"])
                
                if now >= end_time:
                    # Le giveaway est terminé, tirer les gagnants
                    await self.draw_winners(giveaway_id, giveaway)

    async def draw_winners(self, giveaway_id, giveaway):
        """Tire les gagnants d'un giveaway"""
        try:
            channel = self.bot.get_channel(giveaway["channel_id"])
            if not channel:
                print(f"❌ Canal introuvable pour le giveaway {giveaway_id}")
                return
            
            participants = giveaway.get("participants", {})
            
            if not participants:
                embed = discord.Embed(
                    title="❌ Giveaway Annulé",
                    description=f"**{giveaway['prize']}**\n\nAucun participant éligible.",
                    color=discord.Color.red()
                )
                await channel.send(embed=embed)
                giveaways_actifs[giveaway_id]["status"] = "cancelled"
                sauvegarder_giveaways()
                return
            
            # Créer une liste pondérée des participants
            weighted_participants = []
            for user_id, entries in participants.items():
                weighted_participants.extend([user_id] * entries)
            
            # Tirer les gagnants
            num_winners = min(giveaway["num_winners"], len(participants))
            winners = []
            
            for _ in range(num_winners):
                if not weighted_participants:
                    break
                
                winner_id = random.choice(weighted_participants)
                winners.append(winner_id)
                
                # Retirer toutes les entrées de ce gagnant pour éviter qu'il gagne plusieurs fois
                weighted_participants = [uid for uid in weighted_participants if uid != winner_id]
            
            # Annoncer les gagnants
            guild = channel.guild
            winners_mentions = []
            for winner_id in winners:
                member = guild.get_member(int(winner_id))
                if member:
                    winners_mentions.append(member.mention)
            
            embed = discord.Embed(
                title="🎉 GIVEAWAY TERMINÉ ! 🎉",
                description=f"**{giveaway['prize']}**",
                color=discord.Color.gold(),
                timestamp=datetime.now()
            )
            
            if winners_mentions:
                embed.add_field(
                    name="🏆 Gagnants",
                    value="\n".join([f"🎁 {mention}" for mention in winners_mentions]),
                    inline=False
                )
            
            embed.add_field(
                name="📊 Statistiques",
                value=f"Participants: **{len(participants)}**\nTotal d'entrées: **{sum(participants.values())}**",
                inline=False
            )
            
            embed.set_footer(text="Félicitations aux gagnants ! 🎊")
            
            # Mention des gagnants
            mention_text = " ".join(winners_mentions)
            await channel.send(f"🎉 Félicitations {mention_text} ! 🎉", embed=embed)
            
            # Mettre à jour le statut
            giveaways_actifs[giveaway_id]["status"] = "ended"
            giveaways_actifs[giveaway_id]["winners"] = winners
            sauvegarder_giveaways()
            
        except Exception as e:
            print(f"❌ Erreur lors du tirage des gagnants: {e}")
            import traceback
            traceback.print_exc()

    @check_giveaways.before_loop
    async def before_check_giveaways(self):
        """Attend que le bot soit prêt"""
        await self.bot.wait_until_ready()

    @commands.command(name="create_giveaway")
    @commands.has_any_role(1326417422663680090, 1330147432847114321)
    async def create_giveaway(self, ctx):
        """Crée un nouveau giveaway interactif"""
        
        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel
        
        try:
            # Étape 1: Nom du prix
            embed_prize = discord.Embed(
                title="🎁 Création d'un Giveaway - Étape 1/6",
                description="### 🏆 Quel est le prix ?\n\n**Entrez le nom du prix à gagner**",
                color=discord.Color.blue()
            )
            embed_prize.add_field(
                name="💡 Exemple",
                value="`Tougen Anki Crimson Inferno (Steam Key)`",
                inline=False
            )
            embed_prize.set_footer(text="⏱️ Vous avez 60 secondes")
            await ctx.send(embed=embed_prize)
            
            prize_msg = await self.bot.wait_for("message", timeout=60, check=check)
            prize = prize_msg.content.strip()
            
            # Étape 2: Nombre de gagnants
            embed_winners = discord.Embed(
                title="🎁 Création d'un Giveaway - Étape 2/6",
                description="### 👥 Nombre de gagnants ?\n\n**Entrez le nombre de gagnants**",
                color=discord.Color.blue()
            )
            embed_winners.add_field(name="💡 Exemple", value="`3`", inline=False)
            embed_winners.add_field(name="✅ Prix", value=prize, inline=False)
            await ctx.send(embed=embed_winners)
            
            winners_msg = await self.bot.wait_for("message", timeout=60, check=check)
            num_winners = int(winners_msg.content.strip())
            
            # Étape 3: Niveau minimum requis
            embed_level = discord.Embed(
                title="🎁 Création d'un Giveaway - Étape 3/6",
                description="### 📊 Niveau minimum requis (Draftbot) ?\n\n**Entrez le niveau minimum**",
                color=discord.Color.blue()
            )
            embed_level.add_field(name="💡 Exemple", value="`10`", inline=False)
            embed_level.add_field(name="✅ Progression", value=f"🏆 {prize}\n👥 {num_winners} gagnant(s)", inline=False)
            await ctx.send(embed=embed_level)
            
            level_msg = await self.bot.wait_for("message", timeout=60, check=check)
            min_level = int(level_msg.content.strip())
            
            # Étape 4: Invitations minimum requises
            embed_invites = discord.Embed(
                title="🎁 Création d'un Giveaway - Étape 4/6",
                description="### 📨 Invitations minimum requises ?\n\n**Entrez le nombre minimum d'invitations**",
                color=discord.Color.blue()
            )
            embed_invites.add_field(name="💡 Exemple", value="`5`", inline=False)
            embed_invites.add_field(
                name="✅ Progression",
                value=f"🏆 {prize}\n👥 {num_winners} gagnant(s)\n📊 Niveau {min_level}+",
                inline=False
            )
            await ctx.send(embed=embed_invites)
            
            invites_msg = await self.bot.wait_for("message", timeout=60, check=check)
            min_invites = int(invites_msg.content.strip())
            
            # Étape 5: Durée du giveaway
            embed_duration = discord.Embed(
                title="🎁 Création d'un Giveaway - Étape 5/6",
                description="### ⏰ Durée du giveaway ?\n\n**Entrez la durée en jours**",
                color=discord.Color.blue()
            )
            embed_duration.add_field(name="💡 Exemple", value="`7` (pour 7 jours)", inline=False)
            embed_duration.add_field(
                name="✅ Progression",
                value=f"🏆 {prize}\n👥 {num_winners} gagnant(s)\n📊 Niveau {min_level}+\n📨 {min_invites} invitations min.",
                inline=False
            )
            await ctx.send(embed=embed_duration)
            
            duration_msg = await self.bot.wait_for("message", timeout=60, check=check)
            duration_days = int(duration_msg.content.strip())
            
            # Calculer la date de fin
            end_time = datetime.now() + timedelta(days=duration_days)
            
            # Étape 6: Description (optionnelle)
            embed_desc = discord.Embed(
                title="🎁 Création d'un Giveaway - Étape 6/6",
                description="### 📝 Description (optionnelle) ?\n\n**Entrez une description ou `non` pour ignorer**",
                color=discord.Color.blue()
            )
            embed_desc.add_field(
                name="💡 Exemple",
                value="`Gagnez une clé Steam du jeu Tougen Anki Crimson Inferno !`",
                inline=False
            )
            await ctx.send(embed=embed_desc)
            
            desc_msg = await self.bot.wait_for("message", timeout=120, check=check)
            description = desc_msg.content.strip() if desc_msg.content.lower() not in ["non", "n", "no"] else None
            
            # Confirmation
            embed_confirm = discord.Embed(
                title="🎁 Confirmation du Giveaway",
                description="**Vérifiez les informations avant de confirmer**",
                color=discord.Color.gold(),
                timestamp=datetime.now()
            )
            
            embed_confirm.add_field(name="🏆 Prix", value=prize, inline=False)
            embed_confirm.add_field(name="👥 Nombre de gagnants", value=str(num_winners), inline=True)
            embed_confirm.add_field(name="📊 Niveau minimum", value=f"{min_level}+", inline=True)
            embed_confirm.add_field(name="📨 Invitations minimum", value=str(min_invites), inline=True)
            embed_confirm.add_field(name="⏰ Durée", value=f"{duration_days} jour(s)", inline=True)
            embed_confirm.add_field(name="📅 Date de fin", value=f"<t:{int(end_time.timestamp())}:F>", inline=True)
            
            if description:
                embed_confirm.add_field(name="📝 Description", value=description, inline=False)
            
            embed_confirm.add_field(
                name="━━━━━━━━━━━━━━━━━━━━",
                value="✅ **Confirmer** | ❌ **Annuler**",
                inline=False
            )
            
            confirm_msg = await ctx.send(embed=embed_confirm)
            await confirm_msg.add_reaction("✅")
            await confirm_msg.add_reaction("❌")
            
            def check_reaction(reaction, user):
                return user == ctx.author and str(reaction.emoji) in ["✅", "❌"] and reaction.message.id == confirm_msg.id
            
            reaction, _ = await self.bot.wait_for("reaction_add", timeout=30, check=check_reaction)
            await confirm_msg.clear_reactions()
            
            if str(reaction.emoji) == "❌":
                embed_cancel = discord.Embed(
                    title="❌ Création Annulée",
                    description="La création du giveaway a été annulée.",
                    color=discord.Color.red()
                )
                await ctx.send(embed=embed_cancel)
                return
            
            # Créer le giveaway
            giveaway_id = f"giveaway_{int(datetime.now().timestamp())}"
            
            giveaways_actifs[giveaway_id] = {
                "prize": prize,
                "num_winners": num_winners,
                "min_level": min_level,
                "min_invites": min_invites,
                "duration_days": duration_days,
                "end_time": end_time.isoformat(),
                "description": description,
                "channel_id": ctx.channel.id,
                "message_id": None,
                "participants": {},
                "status": "active",
                "created_by": ctx.author.id,
                "created_at": datetime.now().isoformat()
            }
            
            # Créer l'embed du giveaway
            giveaway_embed = discord.Embed(
                title="🎉 GIVEAWAY EN COURS ! 🎉",
                description=f"**{prize}**",
                color=discord.Color.gold(),
                timestamp=datetime.now()
            )
            
            if description:
                giveaway_embed.add_field(name="📝 Description", value=description, inline=False)
            
            giveaway_embed.add_field(name="🏆 Prix", value=prize, inline=False)
            giveaway_embed.add_field(name="👥 Nombre de gagnants", value=str(num_winners), inline=True)
            giveaway_embed.add_field(name="⏰ Se termine", value=f"<t:{int(end_time.timestamp())}:R>", inline=True)
            
            giveaway_embed.add_field(
                name="━━━━━━━━━━━━━━━━━━━━",
                value="",
                inline=False
            )
            
            giveaway_embed.add_field(
                name="📋 Conditions de participation",
                value=(
                    f"📊 **Niveau Draftbot:** {min_level}+\n"
                    f"📨 **Invitations:** {min_invites}+ (plus d'invitations = plus de chances !)\n\n"
                    f"**Système de chances:**\n"
                    f"• 5-9 invites = 1 participation\n"
                    f"• 10-19 invites = 2 participations\n"
                    f"• 20-29 invites = 3 participations\n"
                    f"• 30-49 invites = 5 participations\n"
                    f"• 50+ invites = 10 participations"
                ),
                inline=False
            )
            
            giveaway_embed.add_field(
                name="━━━━━━━━━━━━━━━━━━━━",
                value="",
                inline=False
            )
            
            giveaway_embed.add_field(
                name="🎯 Comment participer ?",
                value=f"Utilisez la commande `!enter_giveaway {giveaway_id}`",
                inline=False
            )
            
            giveaway_embed.set_footer(text=f"ID: {giveaway_id} | Bonne chance à tous ! 🍀")
            
            giveaway_msg = await ctx.send("@everyone 🎁 **NOUVEAU GIVEAWAY !** 🎁", embed=giveaway_embed)
            
            # Sauvegarder l'ID du message
            giveaways_actifs[giveaway_id]["message_id"] = giveaway_msg.id
            sauvegarder_giveaways()
            
            # Message de confirmation
            embed_success = discord.Embed(
                title="✅ Giveaway Créé !",
                description=f"Le giveaway a été créé avec succès !\n\nID: `{giveaway_id}`",
                color=discord.Color.green()
            )
            await ctx.send(embed=embed_success)
            
        except asyncio.TimeoutError:
            embed_timeout = discord.Embed(
                title="⏰ Temps Écoulé",
                description="La création du giveaway a été annulée (temps d'attente dépassé).",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed_timeout)
        except ValueError:
            embed_error = discord.Embed(
                title="❌ Erreur",
                description="Valeur invalide. Veuillez recommencer.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed_error)

    @commands.command(name="enter_giveaway")
    async def enter_giveaway(self, ctx, giveaway_id: str):
        """Participe à un giveaway"""
        if giveaway_id not in giveaways_actifs:
            await ctx.send("❌ Giveaway introuvable.")
            return
        
        giveaway = giveaways_actifs[giveaway_id]
        
        if giveaway["status"] != "active":
            await ctx.send("❌ Ce giveaway n'est plus actif.")
            return
        
        user_id = str(ctx.author.id)
        
        # Vérifier si déjà participant
        if user_id in giveaway["participants"]:
            await ctx.send("❌ Vous participez déjà à ce giveaway !")
            return
        
        # Vérifier les invitations
        user_invites = get_user_invites(ctx.author.id)
        real_invites = user_invites["real"]
        
        if real_invites < giveaway["min_invites"]:
            embed = discord.Embed(
                title="❌ Conditions non remplies",
                description=f"Vous n'avez pas assez d'invitations.",
                color=discord.Color.red()
            )
            embed.add_field(
                name="📊 Vos invitations",
                value=f"**{real_invites}** / {giveaway['min_invites']} requises",
                inline=True
            )
            embed.add_field(
                name="💡 Comment obtenir des invitations ?",
                value="Invitez des amis sur le serveur avec votre lien d'invitation !",
                inline=False
            )
            await ctx.send(embed=embed)
            return
        
        # NOTE: Pour le niveau Draftbot, vous devrez implémenter une vérification
        # En attendant, on suppose que l'utilisateur a le bon niveau
        # Vous pouvez vérifier via les rôles que Draftbot attribue
        
        # Calculer le nombre de participations
        entries = get_participation_entries(real_invites)
        
        # Ajouter la participation
        giveaway["participants"][user_id] = entries
        sauvegarder_giveaways()
        
        # Confirmation
        embed = discord.Embed(
            title="✅ Participation Enregistrée !",
            description=f"Vous participez maintenant au giveaway **{giveaway['prize']}** !",
            color=discord.Color.green(),
            timestamp=datetime.now()
        )
        embed.add_field(name="🎫 Vos participations", value=f"**{entries}** participation(s)", inline=True)
        embed.add_field(name="📨 Vos invitations", value=f"**{real_invites}** invitations", inline=True)
        embed.add_field(
            name="🍀 Bonne chance !",
            value=f"Plus d'invitations = plus de chances de gagner !",
            inline=False
        )
        embed.set_footer(text=f"ID: {giveaway_id}")
        
        await ctx.send(embed=embed)

    @commands.command(name="giveaway_info")
    async def giveaway_info(self, ctx, giveaway_id: str):
        """Affiche les informations d'un giveaway"""
        if giveaway_id not in giveaways_actifs:
            await ctx.send("❌ Giveaway introuvable.")
            return
        
        giveaway = giveaways_actifs[giveaway_id]
        
        embed = discord.Embed(
            title="📊 Informations du Giveaway",
            description=f"**{giveaway['prize']}**",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        
        embed.add_field(name="🏆 Prix", value=giveaway['prize'], inline=False)
        embed.add_field(name="👥 Nombre de gagnants", value=str(giveaway['num_winners']), inline=True)
        embed.add_field(name="📊 Status", value=giveaway['status'].upper(), inline=True)
        
        end_time = datetime.fromisoformat(giveaway['end_time'])
        embed.add_field(name="⏰ Se termine", value=f"<t:{int(end_time.timestamp())}:R>", inline=True)
        
        participants_count = len(giveaway['participants'])
        total_entries = sum(giveaway['participants'].values())
        
        embed.add_field(name="👥 Participants", value=str(participants_count), inline=True)
        embed.add_field(name="🎫 Total de participations", value=str(total_entries), inline=True)
        
        embed.add_field(
            name="📋 Conditions",
            value=(
                f"📊 Niveau: {giveaway['min_level']}+\n"
                f"📨 Invitations: {giveaway['min_invites']}+"
            ),
            inline=False
        )
        
        embed.set_footer(text=f"ID: {giveaway_id}")
        
        await ctx.send(embed=embed)

    @commands.command(name="my_invites")
    async def my_invites(self, ctx):
        """Affiche vos statistiques d'invitations"""
        user_invites = get_user_invites(ctx.author.id)
        
        embed = discord.Embed(
            title="📊 Vos Statistiques d'Invitations",
            description=f"Statistiques pour {ctx.author.mention}",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        
        embed.add_field(name="✅ Invitations valides", value=f"**{user_invites['real']}**", inline=True)
        embed.add_field(name="📊 Total d'invitations", value=f"**{user_invites['total']}**", inline=True)
        embed.add_field(name="👋 Membres partis", value=f"**{user_invites['left']}**", inline=True)
        
        # Calculer les participations pour les giveaways
        entries = get_participation_entries(user_invites['real'])
        
        embed.add_field(
            name="🎫 Participations aux giveaways",
            value=f"**{entries}** participation(s) si vous rejoignez un giveaway",
            inline=False
        )
        
        embed.add_field(
            name="📈 Tableau des participations",
            value=(
                "• 5-9 invites = 1 participation\n"
                "• 10-19 invites = 2 participations\n"
                "• 20-29 invites = 3 participations\n"
                "• 30-49 invites = 5 participations\n"
                "• 50+ invites = 10 participations"
            ),
            inline=False
        )
        
        embed.set_footer(text="Invitez plus d'amis pour augmenter vos chances !")
        embed.set_thumbnail(url=ctx.author.avatar.url if ctx.author.avatar else None)
        
        await ctx.send(embed=embed)

    @commands.command(name="leaderboard_invites")
    async def leaderboard_invites(self, ctx):
        """Affiche le classement des invitations"""
        # Trier par invitations réelles
        sorted_invites = sorted(
            invites_tracker.items(),
            key=lambda x: x[1]["real"],
            reverse=True
        )[:10]
        
        embed = discord.Embed(
            title="🏆 Classement des Invitations",
            description="Top 10 des inviteurs du serveur !",
            color=discord.Color.gold(),
            timestamp=datetime.now()
        )
        
        medals = ["🥇", "🥈", "🥉"]
        
        for i, (user_id, invites) in enumerate(sorted_invites, 1):
            member = ctx.guild.get_member(int(user_id))
            if member:
                medal = medals[i-1] if i <= 3 else f"**{i}.**"
                embed.add_field(
                    name=f"{medal} {member.display_name}",
                    value=f"✅ **{invites['real']}** invitations | 🎫 **{get_participation_entries(invites['real'])}** participations",
                    inline=False
                )
        
        embed.set_footer(text="Continuez à inviter pour grimper dans le classement !")
        
        await ctx.send(embed=embed)

    @commands.command(name="end_giveaway")
    @commands.has_any_role(1326417422663680090, 1330147432847114321)
    async def end_giveaway(self, ctx, giveaway_id: str):
        """Termine manuellement un giveaway et tire les gagnants"""
        if giveaway_id not in giveaways_actifs:
            await ctx.send("❌ Giveaway introuvable.")
            return
        
        giveaway = giveaways_actifs[giveaway_id]
        
        if giveaway["status"] != "active":
            await ctx.send("❌ Ce giveaway n'est plus actif.")
            return
        
        # Confirmation
        embed_confirm = discord.Embed(
            title="⚠️ Confirmation",
            description=f"Voulez-vous vraiment terminer le giveaway **{giveaway['prize']}** maintenant ?",
            color=discord.Color.orange()
        )
        embed_confirm.add_field(
            name="📊 Participants",
            value=f"**{len(giveaway['participants'])}** participant(s)",
            inline=True
        )
        
        confirm_msg = await ctx.send(embed=embed_confirm)
        await confirm_msg.add_reaction("✅")
        await confirm_msg.add_reaction("❌")
        
        def check_reaction(reaction, user):
            return user == ctx.author and str(reaction.emoji) in ["✅", "❌"] and reaction.message.id == confirm_msg.id
        
        try:
            reaction, _ = await self.bot.wait_for("reaction_add", timeout=30, check=check_reaction)
            await confirm_msg.clear_reactions()
            
            if str(reaction.emoji) == "❌":
                await ctx.send("❌ Opération annulée.")
                return
            
            # Tirer les gagnants
            await self.draw_winners(giveaway_id, giveaway)
            await ctx.send("✅ Giveaway terminé et gagnants tirés !")
            
        except asyncio.TimeoutError:
            await confirm_msg.clear_reactions()
            await ctx.send("⏰ Temps écoulé. Opération annulée.")

    @commands.command(name="list_giveaways")
    async def list_giveaways(self, ctx):
        """Liste tous les giveaways"""
        if not giveaways_actifs:
            await ctx.send("📋 Aucun giveaway en cours.")
            return
        
        embed = discord.Embed(
            title="📋 Liste des Giveaways",
            description=f"Total: **{len(giveaways_actifs)}** giveaway(s)",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        
        for giveaway_id, giveaway in list(giveaways_actifs.items())[:10]:
            status_emoji = "🟢" if giveaway["status"] == "active" else "🔴"
            end_time = datetime.fromisoformat(giveaway['end_time'])
            
            embed.add_field(
                name=f"{status_emoji} {giveaway['prize']}",
                value=(
                    f"**ID:** `{giveaway_id}`\n"
                    f"👥 {giveaway['num_winners']} gagnant(s)\n"
                    f"📊 {len(giveaway['participants'])} participant(s)\n"
                    f"⏰ <t:{int(end_time.timestamp())}:R>"
                ),
                inline=False
            )
        
        await ctx.send(embed=embed)

async def setup(bot):
    """Setup pour discord.py 2.0+"""
    await bot.add_cog(GiveawaySystem(bot))
