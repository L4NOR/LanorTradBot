# rappels.py
import discord
from discord.ext import commands, tasks
import json
import os
import datetime
import asyncio

RAPPELS_FILE = "data/rappels_tasks.json"
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
                except Exception:
                    rappeals_actifs = {}
    else:
        rappeals_actifs = {}

# Sauvegarder les rappels dans le fichier
def sauvegarder_rappels():
    try:
        with open(RAPPELS_FILE, "w", encoding="utf-8") as f:
            json.dump(rappeals_actifs, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"Erreur lors de la sauvegarde des rappels: {e}")

# Tâche de rappel
async def envoyer_rappel(bot):
    now = datetime.datetime.now()
    heures = [12, 16, 20]
    
    if now.hour in heures and now.minute == 0:
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
        mangas = ["Ao No Exorcist", "Satsudou", "Tougen Anki", "Catenaccio", "Tokyo Underworld"]
        tasks = ["traduire", "qcheck", "edit", "clean"]

        await ctx.send("📝 Création d'un rappel. Répondez aux questions ci-dessous.")

        # Demande du membre cible
        await ctx.send("👤 Pour quel membre ? Mentionnez-le ou donnez son nom d'utilisateur.")
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
            await ctx.send("⏰ Réponse pour le membre expirée.")
            return

        # Choix du manga
        await ctx.send(f"📚 Quel manga ? Choisissez parmi : {', '.join(mangas)}")
        def check_manga(m):
            return m.author == ctx.author and m.channel == ctx.channel and m.content in mangas
        try:
            manga_msg = await self.bot.wait_for("message", timeout=60, check=check_manga)
            manga = manga_msg.content
        except asyncio.TimeoutError:
            await ctx.send("⏰ Choix du manga expiré.")
            return

        # Choix de la tâche
        await ctx.send(f"✏️ Quelle tâche ? Choisissez parmi : {', '.join(tasks)}")
        def check_task(m):
            return m.author == ctx.author and m.channel == ctx.channel and m.content in tasks
        try:
            task_msg = await self.bot.wait_for("message", timeout=60, check=check_task)
            task = task_msg.content
        except asyncio.TimeoutError:
            await ctx.send("⏰ Choix de la tâche expiré.")
            return

        # Demande du chapitre
        await ctx.send("📖 Pour quel chapitre ? (numéro uniquement)")
        def check_chap(m):
            return m.author == ctx.author and m.channel == ctx.channel and m.content.isdigit()
        try:
            chap_msg = await self.bot.wait_for("message", timeout=60, check=check_chap)
            chapitre = int(chap_msg.content)
        except asyncio.TimeoutError:
            await ctx.send("⏰ Réponse pour le chapitre expirée.")
            return

        # Demande de la date limite
        await ctx.send("📅 Pour quelle date cela doit-il être réalisé ? (format : YYYY-MM-DD)")
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
            await ctx.send("⏰ Réponse pour la date expirée.")
            return

        date_obj = datetime.datetime.strptime(date_limite, "%Y-%m-%d")
        delta = (date_obj.date() - datetime.datetime.now().date()).days
        if delta < 0:
            await ctx.send("❌ La date limite doit être dans le futur.")
            return

        # Confirmation
        await ctx.send(
            f"✅ Confirmez-vous la création d'un rappel **'{task}'** pour {user.mention} "
            f"sur le manga **'{manga}'** chapitre **{chapitre}** à réaliser avant le **{date_limite}** ?\n"
            f"Répondez par **'oui'** ou **'non'**."
        )
        def check_confirm(m):
            return m.author == ctx.author and m.channel == ctx.channel and m.content.lower() in ["oui", "non"]
        try:
            rep = await self.bot.wait_for("message", timeout=30, check=check_confirm)
        except asyncio.TimeoutError:
            await ctx.send("⏰ Confirmation expirée.")
            return
        
        if rep.content.lower() == "oui":
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
            
            embed = discord.Embed(
                title="✅ Rappel créé !",
                description=f"Un rappel a été créé pour {user.mention}",
                color=discord.Color.green()
            )
            embed.add_field(name="Manga", value=manga, inline=True)
            embed.add_field(name="Chapitre", value=str(chapitre), inline=True)
            embed.add_field(name="Tâche", value=task, inline=True)
            embed.add_field(name="Date limite", value=date_limite, inline=True)
            embed.set_footer(text=f"ID: {rappel_id}")
            
            await ctx.send(embed=embed)
        else:
            await ctx.send("❌ Rappel annulé.")

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

# Setup pour discord.py 2.0+
async def setup(bot):
    await bot.add_cog(RappelTask(bot))