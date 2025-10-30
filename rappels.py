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
    async def add_rappel(self, ctx, user: discord.Member, manga: str, chapitre: int, date_limite: str):
        """Créer un rappel de task pour un utilisateur jusqu'à la date limite (format: YYYY-MM-DD)"""
        try:
            date_obj = datetime.datetime.strptime(date_limite, "%Y-%m-%d")
        except ValueError:
            await ctx.send("Format de date invalide. Utilisez YYYY-MM-DD.")
            return
        delta = (date_obj.date() - datetime.datetime.now().date()).days
        if delta < 0:
            await ctx.send("La date limite doit être dans le futur.")
            return
        # Confirmation
        msg = await ctx.send(f"Êtes-vous sûr de vouloir recevoir un rappel de task chaque jour pour {user.mention} pendant {delta} jours (jusqu'au {date_limite}) ? Répondez par 'oui' ou 'non'.")
        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel and m.content.lower() in ["oui", "non"]
        try:
            rep = await ctx.bot.wait_for("message", timeout=30, check=check)
        except asyncio.TimeoutError:
            await ctx.send("Confirmation expirée.")
            return
        if rep.content.lower() == "oui":
            rappel_id = f"{user.id}_{manga}_{chapitre}"
            rappeals_actifs[rappel_id] = {
                "user_id": user.id,
                "manga": manga,
                "chapitre": chapitre,
                "date_limite": date_limite,
                "channel_id": 1431607377882382396
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
