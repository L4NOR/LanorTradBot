# rappels.py
import discord
from discord.ext import commands, tasks
import json
import os
import datetime
import asyncio
import pytz

RAPPELS_FILE = "data/rappels_tasks.json"
RAPPELS_META_FILE = "data/rappels_tasks_meta.json"
os.makedirs("data", exist_ok=True)

# Structure: {"id": {"user_id": int, "manga": str, "chapitre": int, "task": str, "date_limite": str, "channel_id": int}}
rappeals_actifs = {}

# Charger les rappels depuis le fichier
def charger_rappels():
    global rappeals_actifs
    if os.path.exists(RAPPELS_FILE):
        with open(RAPPELS_FILE, "r", encoding="utf-8") as f:
            contenu = f.read().strip()
            if not contenu:
                rappeals_actifs = {}
            else:
                try:
                    rappeals_actifs = json.loads(contenu)
                except Exception as e:
                    print(f"Erreur lors du chargement des rappels: {e}")
                    rappeals_actifs = {}
    else:
        rappeals_actifs = {}

# Sauvegarder les rappels dans le fichier
def sauvegarder_rappels():
    try:
        with open(RAPPELS_FILE, "w", encoding="utf-8") as f:
            json.dump(rappeals_actifs, f, ensure_ascii=False, indent=4)
        
        # Créer le fichier meta avec les informations de sauvegarde
        meta = {
            "last_saved": datetime.datetime.utcnow().isoformat() + "Z",
            "rappel_count": len(rappeals_actifs),
            "rappels_actifs": list(rappeals_actifs.keys())
        }
        with open(RAPPELS_META_FILE, "w", encoding="utf-8") as mf:
            json.dump(meta, mf, ensure_ascii=False, indent=4)
        
        print(f"✅ Rappels sauvegardés avec succès ({len(rappeals_actifs)} rappels)")
    except Exception as e:
        print(f"❌ Erreur lors de la sauvegarde des rappels: {e}")

# Tâche de rappel avec fuseau horaire français
async def envoyer_rappel(bot):
    # Utiliser le fuseau horaire de Paris pour l'heure française
    tz_paris = pytz.timezone('Europe/Paris')
    now = datetime.datetime.now(tz_paris)
    
    # Un seul rappel par jour à 20h00
    if now.hour == 20 and now.minute == 0:
        for rappel_id, rappel in list(rappeals_actifs.items()):
            try:
                date_limite = datetime.datetime.strptime(rappel["date_limite"], "%Y-%m-%d")
                if now.date() > date_limite.date():
                    continue  # Date dépassée
                
                channel = bot.get_channel(rappel["channel_id"])
                if channel:
                    user = channel.guild.get_member(rappel["user_id"])
                    if user:
                        await channel.send(
                            f"⏰ {user.mention} Tu as une tâche **{rappel['task']}** à réaliser "
                            f"pour le manga **{rappel['manga']}** chapitre **{rappel['chapitre']}** "
                            f"avant le {rappel['date_limite']} !"
                        )
            except Exception as e:
                print(f"Erreur lors de l'envoi du rappel {rappel_id}: {e}")

# Classe Cog pour les rappels
class RappelTask(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        charger_rappels()

    async def cog_load(self):
        """Appelé quand le cog est chargé"""
        self.rappel_loop.start()

    async def cog_unload(self):
        """Appelé quand le cog est déchargé"""
        self.rappel_loop.cancel()

    @tasks.loop(minutes=1)
    async def rappel_loop(self):
        """Boucle qui vérifie les rappels toutes les minutes"""
        await envoyer_rappel(self.bot)

    @rappel_loop.before_loop
    async def before_rappel_loop(self):
        """Attend que le bot soit prêt avant de démarrer la boucle"""
        await self.bot.wait_until_ready()

    @commands.command(name='add_rappel')
    @commands.has_any_role(1326417422663680090, 1330147432847114321)
    async def add_rappel(self, ctx):
        """Créer un rappel de task pour un utilisateur en demandant toutes les informations nécessaires."""
        mangas = {
            "1️⃣": "Ao No Exorcist",
            "2️⃣": "Satsudou",
            "3️⃣": "Tougen Anki",
            "4️⃣": "Catenaccio",
            "5️⃣": "Tokyo Underworld"
        }
        
        tasks = {
            "🧹": "clean",
            "🌍": "traduire",
            "✅": "qcheck",
            "✏️": "edit"
        }

        # Variables pour stocker les choix
        user = None
        manga = None
        task = None
        chapitre = None
        date_limite = None

        # Étape 1: Choix du membre
        embed_user = discord.Embed(
            title="📋 Création d'un rappel - Étape 1/5",
            description="👤 **Pour quel membre souhaitez-vous créer un rappel ?**\n\nMentionnez le membre ou donnez son nom d'utilisateur.",
            color=discord.Color.blue()
        )
        embed_user.set_footer(text="Vous avez 60 secondes pour répondre")
        await ctx.send(embed=embed_user)

        def check_user(m):
            return m.author == ctx.author and m.channel == ctx.channel
        
        try:
            user_msg = await self.bot.wait_for("message", timeout=60, check=check_user)
            if user_msg.mentions:
                user = user_msg.mentions[0]
            else:
                user = discord.utils.find(lambda u: u.name.lower() == user_msg.content.lower(), ctx.guild.members)
            if not user:
                await ctx.send("❌ Utilisateur non trouvé. Annulation.")
                return
        except asyncio.TimeoutError:
            await ctx.send("⏰ Temps écoulé. Création du rappel annulée.")
            return

        # Étape 2: Choix du manga
        embed_manga = discord.Embed(
            title="📋 Création d'un rappel - Étape 2/5",
            description=f"📚 **Quel manga ?**\n\nRéagissez avec l'emoji correspondant :\n\n"
                        f"1️⃣ Ao No Exorcist\n"
                        f"2️⃣ Satsudou\n"
                        f"3️⃣ Tougen Anki\n"
                        f"4️⃣ Catenaccio\n"
                        f"5️⃣ Tokyo Underworld",
            color=discord.Color.blue()
        )
        embed_manga.add_field(name="👤 Membre sélectionné", value=user.mention, inline=False)
        embed_manga.set_footer(text="Réagissez avec l'emoji de votre choix")
        
        manga_msg = await ctx.send(embed=embed_manga)
        for emoji in mangas.keys():
            await manga_msg.add_reaction(emoji)

        def check_manga(reaction, user_react):
            return user_react == ctx.author and str(reaction.emoji) in mangas.keys() and reaction.message.id == manga_msg.id

        try:
            reaction, _ = await self.bot.wait_for("reaction_add", timeout=60, check=check_manga)
            manga = mangas[str(reaction.emoji)]
            await manga_msg.clear_reactions()
        except asyncio.TimeoutError:
            await ctx.send("⏰ Temps écoulé. Création du rappel annulée.")
            await manga_msg.clear_reactions()
            return

        # Étape 3: Choix de la tâche
        embed_task = discord.Embed(
            title="📋 Création d'un rappel - Étape 3/5",
            description=f"✏️ **Quelle tâche ?**\n\nRéagissez avec l'emoji correspondant :\n\n"
                        f"🧹 Clean\n"
                        f"🌍 Traduire\n"
                        f"✅ QCheck\n"
                        f"✏️ Edit",
            color=discord.Color.blue()
        )
        embed_task.add_field(name="👤 Membre", value=user.mention, inline=True)
        embed_task.add_field(name="📚 Manga", value=manga, inline=True)
        embed_task.set_footer(text="Réagissez avec l'emoji de votre choix")
        
        task_msg = await ctx.send(embed=embed_task)
        for emoji in tasks.keys():
            await task_msg.add_reaction(emoji)

        def check_task(reaction, user_react):
            return user_react == ctx.author and str(reaction.emoji) in tasks.keys() and reaction.message.id == task_msg.id

        try:
            reaction, _ = await self.bot.wait_for("reaction_add", timeout=60, check=check_task)
            task = tasks[str(reaction.emoji)]
            await task_msg.clear_reactions()
        except asyncio.TimeoutError:
            await ctx.send("⏰ Temps écoulé. Création du rappel annulée.")
            await task_msg.clear_reactions()
            return

        # Étape 4: Numéro du chapitre
        embed_chap = discord.Embed(
            title="📋 Création d'un rappel - Étape 4/5",
            description="📖 **Pour quel chapitre ?**\n\nEntrez le numéro du chapitre.",
            color=discord.Color.blue()
        )
        embed_chap.add_field(name="👤 Membre", value=user.mention, inline=True)
        embed_chap.add_field(name="📚 Manga", value=manga, inline=True)
        embed_chap.add_field(name="✏️ Tâche", value=task.capitalize(), inline=True)
        embed_chap.set_footer(text="Vous avez 60 secondes pour répondre")
        await ctx.send(embed=embed_chap)

        def check_chap(m):
            return m.author == ctx.author and m.channel == ctx.channel and m.content.isdigit()

        try:
            chap_msg = await self.bot.wait_for("message", timeout=60, check=check_chap)
            chapitre = int(chap_msg.content)
        except asyncio.TimeoutError:
            await ctx.send("⏰ Temps écoulé. Création du rappel annulée.")
            return

        # Étape 5: Date limite
        embed_date = discord.Embed(
            title="📋 Création d'un rappel - Étape 5/5",
            description="📅 **Pour quelle date limite ?**\n\nFormat : `YYYY-MM-DD` (ex: 2025-11-15)",
            color=discord.Color.blue()
        )
        embed_date.add_field(name="👤 Membre", value=user.mention, inline=True)
        embed_date.add_field(name="📚 Manga", value=manga, inline=True)
        embed_date.add_field(name="✏️ Tâche", value=task.capitalize(), inline=True)
        embed_date.add_field(name="📖 Chapitre", value=str(chapitre), inline=True)
        embed_date.set_footer(text="Vous avez 60 secondes pour répondre")
        await ctx.send(embed=embed_date)

        def check_date(m):
            try:
                datetime.datetime.strptime(m.content, "%Y-%m-%d")
                return m.author == ctx.author and m.channel == ctx.channel
            except ValueError:
                return False

        try:
            date_msg = await self.bot.wait_for("message", timeout=60, check=check_date)
            date_limite = date_msg.content
        except asyncio.TimeoutError:
            await ctx.send("⏰ Temps écoulé. Création du rappel annulée.")
            return

        # Vérification de la date
        date_obj = datetime.datetime.strptime(date_limite, "%Y-%m-%d")
        delta = (date_obj.date() - datetime.datetime.now().date()).days
        if delta < 0:
            await ctx.send("❌ La date limite doit être dans le futur. Création annulée.")
            return

        # Confirmation finale
        embed_confirm = discord.Embed(
            title="✅ Confirmation du rappel",
            description="**Récapitulatif du rappel à créer :**\n\nRéagissez avec ✅ pour confirmer ou ❌ pour annuler.",
            color=discord.Color.green()
        )
        embed_confirm.add_field(name="👤 Membre", value=user.mention, inline=True)
        embed_confirm.add_field(name="📚 Manga", value=manga, inline=True)
        embed_confirm.add_field(name="📖 Chapitre", value=str(chapitre), inline=True)
        embed_confirm.add_field(name="✏️ Tâche", value=task.capitalize(), inline=True)
        embed_confirm.add_field(name="📅 Date limite", value=date_limite, inline=True)
        embed_confirm.add_field(name="⏰ Jours restants", value=f"{delta} jour(s)", inline=True)
        embed_confirm.set_footer(text="Réagissez pour confirmer ou annuler")
        
        confirm_msg = await ctx.send(embed=embed_confirm)
        await confirm_msg.add_reaction("✅")
        await confirm_msg.add_reaction("❌")

        def check_confirm(reaction, user_react):
            return user_react == ctx.author and str(reaction.emoji) in ["✅", "❌"] and reaction.message.id == confirm_msg.id

        try:
            reaction, _ = await self.bot.wait_for("reaction_add", timeout=30, check=check_confirm)
            await confirm_msg.clear_reactions()
            
            if str(reaction.emoji) == "✅":
                rappel_id = f"{user.id}_{manga}_{chapitre}_{task}"
                rappeals_actifs[rappel_id] = {
                    "user_id": user.id,
                    "manga": manga,
                    "chapitre": chapitre,
                    "task": task,
                    "date_limite": date_limite,
                    "channel_id": ctx.channel.id
                }
                sauvegarder_rappels()
                
                embed_success = discord.Embed(
                    title="✅ Rappel créé avec succès !",
                    description=f"Un rappel a été créé pour {user.mention}",
                    color=discord.Color.green(),
                    timestamp=datetime.datetime.now()
                )
                embed_success.add_field(name="📚 Manga", value=manga, inline=True)
                embed_success.add_field(name="📖 Chapitre", value=str(chapitre), inline=True)
                embed_success.add_field(name="✏️ Tâche", value=task.capitalize(), inline=True)
                embed_success.add_field(name="📅 Date limite", value=date_limite, inline=True)
                embed_success.add_field(name="🆔 ID", value=f"`{rappel_id}`", inline=False)
                embed_success.set_footer(text=f"Créé par {ctx.author.name}")
                
                await ctx.send(embed=embed_success)
            else:
                embed_cancel = discord.Embed(
                    title="❌ Création annulée",
                    description="La création du rappel a été annulée.",
                    color=discord.Color.red()
                )
                await ctx.send(embed=embed_cancel)
        except asyncio.TimeoutError:
            await ctx.send("⏰ Temps écoulé. Création du rappel annulée.")
            await confirm_msg.clear_reactions()
            return

    @commands.command(name='list_rappels')
    @commands.has_any_role(1326417422663680090, 1330147432847114321)
    async def list_rappels(self, ctx):
        """Liste les rappels actifs"""
        if not rappeals_actifs:
            await ctx.send("📋 Aucun rappel actif.")
            return
        
        embed = discord.Embed(
            title="📋 Rappels actifs",
            color=discord.Color.blue(),
            timestamp=datetime.datetime.now()
        )
        
        for rid, r in rappeals_actifs.items():
            user = ctx.guild.get_member(r["user_id"])
            user_mention = user.mention if user else f"ID: {r['user_id']}"
            
            field_value = (
                f"👤 Utilisateur: {user_mention}\n"
                f"📚 Manga: {r['manga']}\n"
                f"📖 Chapitre: {r['chapitre']}\n"
                f"✏️ Tâche: {r['task']}\n"
                f"📅 Date limite: {r['date_limite']}"
            )
            
            embed.add_field(
                name=f"ID: {rid[:30]}...",
                value=field_value,
                inline=False
            )
        
        embed.set_footer(text=f"Total: {len(rappeals_actifs)} rappel(s)")
        await ctx.send(embed=embed)

    @commands.command(name='delete_rappel')
    @commands.has_any_role(1326417422663680090, 1330147432847114321)
    async def delete_rappel(self, ctx, *, rappel_id: str):
        """Supprime un rappel par son ID"""
        if rappel_id in rappeals_actifs:
            rappel_info = rappeals_actifs[rappel_id]
            del rappeals_actifs[rappel_id]
            sauvegarder_rappels()
            
            embed = discord.Embed(
                title="🗑️ Rappel supprimé",
                description=f"Le rappel **{rappel_id}** a été supprimé.",
                color=discord.Color.red()
            )
            embed.add_field(name="Manga", value=rappel_info.get("manga", "N/A"), inline=True)
            embed.add_field(name="Chapitre", value=str(rappel_info.get("chapitre", "N/A")), inline=True)
            embed.add_field(name="Tâche", value=rappel_info.get("task", "N/A"), inline=True)
            
            await ctx.send(embed=embed)
        else:
            await ctx.send(f"❌ ID de rappel **{rappel_id}** introuvable.")

    @commands.command(name="actualiser_rappels")
    @commands.has_any_role(1326417422663680090, 1330147432847114321)
    async def actualiser_rappels(self, ctx, action: str = "save"):
        """Commande d'administration pour sauvegarder ou recharger l'état des rappels"""
        action = (action or "").lower()
        
        if action in ("save", "sauvegarder", "enregistrer"):
            sauvegarder_rappels()
            meta = {}
            try:
                if os.path.exists(RAPPELS_META_FILE):
                    with open(RAPPELS_META_FILE, "r", encoding="utf-8") as mf:
                        meta = json.load(mf)
            except Exception:
                meta = {}
            
            embed = discord.Embed(
                title="💾 Actualisation des rappels",
                description="Le fichier rappels_tasks.json a été mis à jour avec l'état actuel en mémoire.",
                color=discord.Color(0x2ECC71),
                timestamp=datetime.datetime.utcnow()
            )
            embed.add_field(name="Nombre de rappels", value=str(len(rappeals_actifs)), inline=True)
            embed.add_field(name="Dernière sauvegarde", value=meta.get("last_saved", "N/A"), inline=True)
            
            if rappeals_actifs:
                rappels_list = "\n".join([f"• {rid[:40]}..." for rid in list(rappeals_actifs.keys())[:5]])
                if len(rappeals_actifs) > 5:
                    rappels_list += f"\n... et {len(rappeals_actifs) - 5} autres"
                embed.add_field(name="Rappels enregistrés", value=rappels_list, inline=False)
            
            embed.set_footer(text=f"Demandé par {ctx.author.name}")
            await ctx.send(embed=embed)
        
        elif action in ("reload", "recharge", "recharger"):
            charger_rappels()
            meta = {}
            try:
                if os.path.exists(RAPPELS_META_FILE):
                    with open(RAPPELS_META_FILE, "r", encoding="utf-8") as mf:
                        meta = json.load(mf)
            except Exception:
                meta = {}
            
            embed = discord.Embed(
                title="♻️ Rechargement des rappels",
                description="Le fichier rappels_tasks.json a été rechargé en mémoire.",
                color=discord.Color(0x3498DB),
                timestamp=datetime.datetime.utcnow()
            )
            embed.add_field(name="Nombre de rappels chargés", value=str(len(rappeals_actifs)), inline=True)
            embed.add_field(name="Dernière sauvegarde", value=meta.get("last_saved", "N/A"), inline=True)
            
            if rappeals_actifs:
                rappels_list = "\n".join([f"• {rid[:40]}..." for rid in list(rappeals_actifs.keys())[:5]])
                if len(rappeals_actifs) > 5:
                    rappels_list += f"\n... et {len(rappeals_actifs) - 5} autres"
                embed.add_field(name="Rappels chargés", value=rappels_list, inline=False)
            
            embed.set_footer(text=f"Demandé par {ctx.author.name}")
            await ctx.send(embed=embed)
        
        else:
            await ctx.send("❗ Usage: !actualiser_rappels save ou !actualiser_rappels reload")

# Setup pour discord.py 2.0+
async def setup(bot):
    await bot.add_cog(RappelTask(bot))