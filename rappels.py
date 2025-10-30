# rappels.py
import discord
from discord.ext import commands, tasks
import json
import os
import datetime
import asyncio

RAPPELS_FILE = "data/rappels_tasks.json"
os.makedirs("data", exist_ok=True)

# Structure: {"id": {"user_id": int, "manga": str, "chapitre": int, "date_limite": str, "channel_id": int}}
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
    for rappel_id, rappel in rappeals_actifs.items():
        date_limite = datetime.datetime.strptime(rappel["date_limite"], "%Y-%m-%d")
        if now.date() > date_limite.date():
            continue  # Date dépassée
        if now.hour in heures and now.minute == 0:
            channel = bot.get_channel(rappel["channel_id"])
            user = channel.guild.get_member(rappel["user_id"])
            if channel and user:
                await channel.send(f"⏰ {user.mention} Tu as une tâche à réaliser pour le manga **{rappel['manga']}** chapitre **{rappel['chapitre']}** avant le {rappel['date_limite']} !")

# Tâche asynchrone qui vérifie toutes les minutes
class RappelTask(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        charger_rappels()

    async def cog_load(self):
        self.rappel_loop.start()

    @tasks.loop(minutes=1)
    async def rappel_loop(self):
        await envoyer_rappel(self.bot)

    @commands.command()
    async def add_rappel(self, ctx):
        """Créer un rappel de task pour un utilisateur en demandant toutes les informations nécessaires."""
        mangas = ["Ao No Exorcist", "Satsudou", "Tougen Anki", "Catenaccio", "Tokyo Underworld"]
        tasks = ["traduire", "qcheck", "edit", "clean"]

        await ctx.send("Création d'un rappel. Répondez aux questions ci-dessous.")

        # Demande du membre cible
        await ctx.send("Pour quel membre ? Mentionnez-le ou donnez son nom d'utilisateur.")
        def check_user(m):
            return m.author == ctx.author and m.channel == ctx.channel
        try:
            user_msg = await ctx.bot.wait_for("message", timeout=60, check=check_user)
            if user_msg.mentions:
                user = user_msg.mentions[0]
            else:
                user = discord.utils.find(lambda u: u.name == user_msg.content, ctx.guild.members)
            if not user:
                await ctx.send("Utilisateur non trouvé. Annulation.")
                return
        except asyncio.TimeoutError:
            await ctx.send("Réponse pour le membre expirée.")
            return

        # Choix du manga
        await ctx.send(f"Quel manga ? Choisissez parmi : {', '.join(mangas)}")
        def check_manga(m):
            return m.author == ctx.author and m.channel == ctx.channel and m.content in mangas
        try:
            manga_msg = await ctx.bot.wait_for("message", timeout=60, check=check_manga)
            manga = manga_msg.content
        except asyncio.TimeoutError:
            await ctx.send("Choix du manga expiré.")
            return

        # Choix de la tâche
        await ctx.send(f"Quelle tâche ? Choisissez parmi : {', '.join(tasks)}")
        def check_task(m):
            return m.author == ctx.author and m.channel == ctx.channel and m.content in tasks
        try:
            task_msg = await ctx.bot.wait_for("message", timeout=60, check=check_task)
            task = task_msg.content
        except asyncio.TimeoutError:
            await ctx.send("Choix de la tâche expiré.")
            return

        # Demande du chapitre
        await ctx.send("Pour quel chapitre ? (numéro uniquement)")
        def check_chap(m):
            return m.author == ctx.author and m.channel == ctx.channel and m.content.isdigit()
        try:
            chap_msg = await ctx.bot.wait_for("message", timeout=60, check=check_chap)
            chapitre = int(chap_msg.content)
        except asyncio.TimeoutError:
            await ctx.send("Réponse pour le chapitre expirée.")
            return

        # Demande de la date limite
        await ctx.send("Pour quelle date cela doit-il être réalisé ? (format : YYYY-MM-DD)")
        def check_date(m):
            try:
                datetime.datetime.strptime(m.content, "%Y-%m-%d")
                return m.author == ctx.author and m.channel == ctx.channel
            except ValueError:
                return False
        try:
            date_msg = await ctx.bot.wait_for("message", timeout=60, check=check_date)
            date_limite = date_msg.content
        except asyncio.TimeoutError:
            await ctx.send("Réponse pour la date expirée.")
            return

        date_obj = datetime.datetime.strptime(date_limite, "%Y-%m-%d")
        delta = (date_obj.date() - datetime.datetime.now().date()).days
        if delta < 0:
            await ctx.send("La date limite doit être dans le futur.")
            return

        # Confirmation
        msg = await ctx.send(f"Confirmez-vous la création d'un rappel '{task}' pour {user.mention} sur le manga '{manga}' chapitre {chapitre} à réaliser avant le {date_limite} ? Répondez par 'oui' ou 'non'.")
        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel and m.content.lower() in ["oui", "non"]
        try:
            rep = await ctx.bot.wait_for("message", timeout=30, check=check)
        except asyncio.TimeoutError:
            await ctx.send("Confirmation expirée.")
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
            await ctx.send(f"Rappel créé pour {user.mention} !")
        else:
            await ctx.send("Rappel annulé.")

    @commands.command()
    async def list_rappels(self, ctx):
        """Liste les rappels actifs"""
        if not rappeals_actifs:
            await ctx.send("Aucun rappel actif.")
            return
        msg = "**Rappels actifs :**\n"
        for rid, r in rappeals_actifs.items():
            user = ctx.guild.get_member(r["user_id"])
            msg += f"- {user.mention if user else r['user_id']} | {r['manga']} chapitre {r['chapitre']} jusqu'au {r['date_limite']}\n"
        await ctx.send(msg)

    @commands.command()
    async def delete_rappel(self, ctx, rappel_id: str):
        """Supprime un rappel par son ID"""
        if rappel_id in rappeals_actifs:
            del rappeals_actifs[rappel_id]
            sauvegarder_rappels()
            await ctx.send(f"Rappel {rappel_id} supprimé.")
        else:
            await ctx.send("ID de rappel introuvable.")

# Setup
def setup(bot):
    bot.add_cog(RappelTask(bot))
