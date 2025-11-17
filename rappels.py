# rappels.py
import discord
from discord.ext import commands, tasks
import json
import os
import datetime
import asyncio
import pytz
import logging

RAPPELS_FILE = "data/rappels_tasks.json"
RAPPELS_META_FILE = "data/rappels_tasks_meta.json"
os.makedirs("data", exist_ok=True)

# Structure: {"id": {"user_id": int, "manga": str, "chapitres": [int], "task": str, "date_limite": str, "channel_id": int}}
rappeals_actifs = {}

# Variable pour éviter d'envoyer plusieurs rappels dans la même minute
last_rappel_time = None

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
                    print(f"📋 {len(rappeals_actifs)} rappel(s) chargé(s)")
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

# Fonction pour obtenir l'emoji du manga
def get_manga_emoji(manga_name):
    emojis = {
        "Ao No Exorcist": "👹",
        "Satsudou": "🩸",
        "Tougen Anki": "😈",
        "Catenaccio": "⚽",
        "Tokyo Underworld": "🗼"
    }
    return emojis.get(manga_name, "📚")

# Fonction pour obtenir l'emoji de la tâche
def get_task_emoji(task_name):
    emojis = {
        "clean": "🧹",
        "traduire": "🌍",
        "qcheck": "✅",
        "edit": "✏️"
    }
    return emojis.get(task_name, "📝")

# Tâche de rappel avec fuseau horaire français
async def envoyer_rappel(bot):
    global last_rappel_time
    
    tz_paris = pytz.timezone('Europe/Paris')
    now = datetime.datetime.now(tz_paris)
    
    # Vérifier si c'est l'heure du rappel (21h) et qu'on n'a pas déjà envoyé aujourd'hui
    current_date = now.date()
    
    # Ne s'exécuter qu'une seule fois par jour à 21h
    if now.hour == 21 and (last_rappel_time is None or last_rappel_time != current_date):
        print(f"🔔 Déclenchement des rappels à {now.strftime('%Y-%m-%d %H:%M:%S')}")
        last_rappel_time = current_date
        
        rappels_envoyes = 0
        rappels_ignores = 0
        rappels_erreurs = 0
        
        for rappel_id, rappel in list(rappeals_actifs.items()):
            try:
                # Parser la date limite
                date_limite_str = rappel.get("date_limite", "")
                if not date_limite_str:
                    print(f"⚠️ Rappel {rappel_id} n'a pas de date limite définie")
                    rappels_erreurs += 1
                    continue
                
                date_limite = datetime.datetime.strptime(date_limite_str, "%Y-%m-%d")
                
                # CORRECTION: Comparer uniquement les dates, pas les heures
                # Et envoyer le rappel SI on est avant ou égal à la date limite
                if now.date() > date_limite.date():
                    print(f"⏩ Rappel {rappel_id} ignoré (date dépassée: {date_limite_str})")
                    rappels_ignores += 1
                    continue
                
                channel = bot.get_channel(rappel["channel_id"])
                if not channel:
                    print(f"❌ Canal {rappel['channel_id']} introuvable pour le rappel {rappel_id}")
                    rappels_erreurs += 1
                    continue
                
                user = channel.guild.get_member(rappel["user_id"])
                if not user:
                    print(f"❌ Utilisateur {rappel['user_id']} introuvable pour le rappel {rappel_id}")
                    rappels_erreurs += 1
                    continue
                
                manga_emoji = get_manga_emoji(rappel["manga"])
                task_emoji = get_task_emoji(rappel["task"])
                chapitres = rappel.get("chapitres", [rappel.get("chapitre", 0)])
                chapitres_str = ", ".join([f"#{c}" for c in chapitres])
                
                # Calculer les jours restants
                jours_restants = (date_limite.date() - now.date()).days
                
                # Déterminer l'urgence
                if jours_restants <= 1:
                    urgence = "🔴 URGENT"
                    urgence_color = discord.Color.red()
                elif jours_restants <= 3:
                    urgence = "🟡 Bientôt"
                    urgence_color = discord.Color.gold()
                else:
                    urgence = "🟢 À venir"
                    urgence_color = discord.Color.green()
                
                embed = discord.Embed(
                    title=f"{task_emoji} Rappel de Tâche",
                    description=f"{user.mention}, n'oublie pas ta tâche !",
                    color=urgence_color,
                    timestamp=datetime.datetime.now()
                )
                embed.add_field(name=f"{manga_emoji} Manga", value=rappel['manga'], inline=True)
                embed.add_field(name="📖 Chapitres", value=chapitres_str, inline=True)
                embed.add_field(name=f"{task_emoji} Tâche", value=rappel['task'].capitalize(), inline=True)
                embed.add_field(name="📅 Date limite", value=date_limite_str, inline=True)
                embed.add_field(name="⏰ Temps restant", value=f"{urgence} - {jours_restants} jour(s)", inline=True)
                embed.set_footer(text="Bon courage ! 💪")
                
                # Message de mention avant l'embed
                mention_message = f"🔔 **Rappel quotidien** {user.mention} !"
                await channel.send(mention_message)
                await channel.send(embed=embed)
                
                print(f"✅ Rappel envoyé pour {user.name} - {rappel['manga']} ch.{chapitres_str} (deadline: {date_limite_str})")
                rappels_envoyes += 1
            
            except Exception as e:
                print(f"❌ Erreur lors de l'envoi du rappel {rappel_id}: {e}")
                import traceback
                traceback.print_exc()
                rappels_erreurs += 1
        
        print(f"📊 Résumé: {rappels_envoyes} envoyé(s), {rappels_ignores} ignoré(s), {rappels_erreurs} erreur(s)")

# Classe Cog pour les rappels
class RappelTask(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        charger_rappels()
        print(f"📋 {len(rappeals_actifs)} rappel(s) chargé(s)")

    async def cog_load(self):
        """Appelé quand le cog est chargé"""
        self.rappel_loop.start()
        print("✅ Boucle de rappels démarrée")

    async def cog_unload(self):
        """Appelé quand le cog est déchargé"""
        self.rappel_loop.cancel()
        print("🛑 Boucle de rappels arrêtée")

    @tasks.loop(minutes=1)
    async def rappel_loop(self):
        """Boucle qui vérifie les rappels toutes les minutes"""
        try:
            await envoyer_rappel(self.bot)
        except Exception as e:
            print(f"❌ Erreur dans rappel_loop: {e}")
            import traceback
            traceback.print_exc()

    @rappel_loop.before_loop
    async def before_rappel_loop(self):
        """Attend que le bot soit prêt avant de démarrer la boucle"""
        await self.bot.wait_until_ready()
        print("🤖 Bot prêt, démarrage de la surveillance des rappels...")

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

        user = None
        manga = None
        task = None
        chapitres = []
        date_limite = None

        # Étape 1: Choix du membre
        embed_user = discord.Embed(
            title="📋 Création d'un Rappel - Étape 1/5",
            description="### 👤 Sélection du Membre\n\n**Mentionnez le membre** ou **tapez son nom d'utilisateur**",
            color=discord.Color.blue()
        )
        embed_user.add_field(
            name="💡 Exemple",
            value="`@Utilisateur` ou `NomUtilisateur`",
            inline=False
        )
        embed_user.set_footer(text="⏱️ Vous avez 60 secondes pour répondre", icon_url=ctx.author.avatar.url if ctx.author.avatar else None)
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
        manga_list = "\n".join([f"{emoji} **{name}**" for emoji, name in mangas.items()])
        embed_manga = discord.Embed(
            title="📋 Création d'un Rappel - Étape 2/5",
            description=f"### 📚 Quel Manga ?\n\n{manga_list}",
            color=discord.Color.blue()
        )
        embed_manga.add_field(name="✅ Membre sélectionné", value=user.mention, inline=False)
        embed_manga.set_footer(text="🖱️ Cliquez sur l'emoji correspondant", icon_url=ctx.author.avatar.url if ctx.author.avatar else None)
        
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
        task_list = "\n".join([f"{emoji} **{name.capitalize()}**" for emoji, name in tasks.items()])
        embed_task = discord.Embed(
            title="📋 Création d'un Rappel - Étape 3/5",
            description=f"### ✏️ Quelle Tâche ?\n\n{task_list}",
            color=discord.Color.blue()
        )
        embed_task.add_field(name="✅ Progression", value=f"👤 {user.mention}\n📚 {get_manga_emoji(manga)} {manga}", inline=False)
        embed_task.set_footer(text="🖱️ Cliquez sur l'emoji correspondant", icon_url=ctx.author.avatar.url if ctx.author.avatar else None)
        
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

        # Étape 4: Numéros des chapitres (plusieurs possibles)
        embed_chap = discord.Embed(
            title="📋 Création d'un Rappel - Étape 4/5",
            description="### 📖 Pour Quel(s) Chapitre(s) ?\n\n**Entrez les numéros des chapitres** séparés par des espaces ou des virgules",
            color=discord.Color.blue()
        )
        embed_chap.add_field(
            name="💡 Exemples",
            value="`214 215 216` ou `214, 215, 216` ou `214`",
            inline=False
        )
        embed_chap.add_field(
            name="✅ Progression",
            value=f"👤 {user.mention}\n📚 {get_manga_emoji(manga)} {manga}\n{get_task_emoji(task)} {task.capitalize()}",
            inline=False
        )
        embed_chap.set_footer(text="⏱️ Vous avez 60 secondes pour répondre", icon_url=ctx.author.avatar.url if ctx.author.avatar else None)
        await ctx.send(embed=embed_chap)

        def check_chap(m):
            return m.author == ctx.author and m.channel == ctx.channel

        try:
            chap_msg = await self.bot.wait_for("message", timeout=60, check=check_chap)
            # Nettoyer et parser les chapitres
            chap_str = chap_msg.content.replace(',', ' ')
            chapitres = [int(c) for c in chap_str.split() if c.isdigit()]
            
            if not chapitres:
                await ctx.send("❌ Aucun chapitre valide trouvé. Annulation.")
                return
        except asyncio.TimeoutError:
            await ctx.send("⏰ Temps écoulé. Création du rappel annulée.")
            return

        # Étape 5: Date limite
        chapitres_str = ", ".join([f"#{c}" for c in chapitres])
        embed_date = discord.Embed(
            title="📋 Création d'un Rappel - Étape 5/5",
            description="### 📅 Date Limite\n\n**Entrez la date limite** au format `AAAA-MM-JJ`",
            color=discord.Color.blue()
        )
        embed_date.add_field(
            name="💡 Exemple",
            value="`2025-11-15`",
            inline=False
        )
        embed_date.add_field(
            name="✅ Progression",
            value=(
                f"👤 {user.mention}\n"
                f"📚 {get_manga_emoji(manga)} {manga}\n"
                f"📖 Chapitres: {chapitres_str}\n"
                f"{get_task_emoji(task)} {task.capitalize()}"
            ),
            inline=False
        )
        embed_date.set_footer(text="⏱️ Vous avez 60 secondes pour répondre", icon_url=ctx.author.avatar.url if ctx.author.avatar else None)
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

        # Déterminer l'urgence
        if delta <= 1:
            urgence_emoji = "🔴"
            urgence_text = "URGENT"
            urgence_color = discord.Color.red()
        elif delta <= 3:
            urgence_emoji = "🟡"
            urgence_text = "Bientôt"
            urgence_color = discord.Color.gold()
        else:
            urgence_emoji = "🟢"
            urgence_text = "À venir"
            urgence_color = discord.Color.green()

        # Confirmation finale avec embed amélioré
        embed_confirm = discord.Embed(
            title="✅ Confirmation du Rappel",
            description="**Vérifiez les informations avant de confirmer**",
            color=urgence_color,
            timestamp=datetime.datetime.now()
        )
        
        # Informations principales
        embed_confirm.add_field(name="👤 Membre", value=user.mention, inline=True)
        embed_confirm.add_field(name=f"{get_manga_emoji(manga)} Manga", value=manga, inline=True)
        embed_confirm.add_field(name=f"{get_task_emoji(task)} Tâche", value=task.capitalize(), inline=True)
        
        # Chapitres et date
        embed_confirm.add_field(name="📖 Chapitres", value=chapitres_str, inline=True)
        embed_confirm.add_field(name="📅 Date limite", value=f"`{date_limite}`", inline=True)
        embed_confirm.add_field(name="⏰ Urgence", value=f"{urgence_emoji} {urgence_text}\n({delta} jour{'s' if delta > 1 else ''})", inline=True)
        
        embed_confirm.add_field(
            name="━━━━━━━━━━━━━━━━━━━━",
            value="✅ **Confirmer** | ❌ **Annuler**",
            inline=False
        )
        
        embed_confirm.set_footer(
            text=f"Créé par {ctx.author.name} | Réagissez dans les 30 secondes",
            icon_url=ctx.author.avatar.url if ctx.author.avatar else None
        )
        
        if user.avatar:
            embed_confirm.set_thumbnail(url=user.avatar.url)
        
        confirm_msg = await ctx.send(embed=embed_confirm)
        await confirm_msg.add_reaction("✅")
        await confirm_msg.add_reaction("❌")

        def check_confirm(reaction, user_react):
            return user_react == ctx.author and str(reaction.emoji) in ["✅", "❌"] and reaction.message.id == confirm_msg.id

        try:
            reaction, _ = await self.bot.wait_for("reaction_add", timeout=30, check=check_confirm)
            await confirm_msg.clear_reactions()
            
            if str(reaction.emoji) == "✅":
                # Créer un ID unique pour le rappel
                rappel_id = f"{user.id}_{manga.replace(' ', '_')}_{'-'.join(map(str, chapitres))}_{task}"
                rappeals_actifs[rappel_id] = {
                    "user_id": user.id,
                    "manga": manga,
                    "chapitres": chapitres,
                    "task": task,
                    "date_limite": date_limite,
                    "channel_id": ctx.channel.id
                }
                sauvegarder_rappels()
                
                # Embed de succès
                embed_success = discord.Embed(
                    title="🎉 Rappel Créé avec Succès !",
                    description=f"Le rappel a été créé pour {user.mention}",
                    color=discord.Color.green(),
                    timestamp=datetime.datetime.now()
                )
                
                embed_success.add_field(name=f"{get_manga_emoji(manga)} Manga", value=manga, inline=True)
                embed_success.add_field(name="📖 Chapitres", value=chapitres_str, inline=True)
                embed_success.add_field(name=f"{get_task_emoji(task)} Tâche", value=task.capitalize(), inline=True)
                embed_success.add_field(name="📅 Date limite", value=date_limite, inline=True)
                embed_success.add_field(name="⏰ Rappel quotidien", value="21h00 (heure française)", inline=True)
                embed_success.add_field(name="🆔 ID du rappel", value=f"`{rappel_id[:50]}...`", inline=False)
                
                embed_success.set_footer(
                    text=f"Créé par {ctx.author.name}",
                    icon_url=ctx.author.avatar.url if ctx.author.avatar else None
                )
                
                if user.avatar:
                    embed_success.set_thumbnail(url=user.avatar.url)
                
                await ctx.send(embed=embed_success)
            else:
                embed_cancel = discord.Embed(
                    title="❌ Création Annulée",
                    description="La création du rappel a été annulée.",
                    color=discord.Color.red()
                )
                embed_cancel.set_footer(text=f"Annulé par {ctx.author.name}")
                await ctx.send(embed=embed_cancel)
        except asyncio.TimeoutError:
            await ctx.send("⏰ Temps écoulé. Création du rappel annulée.")
            await confirm_msg.clear_reactions()
            return

    @commands.command(name='list_rappels')
    @commands.has_any_role(1326417422663680090, 1330147432847114321)
    async def list_rappels(self, ctx):
        """Liste les rappels actifs avec pagination"""
        if not rappeals_actifs:
            embed = discord.Embed(
                title="📋 Rappels Actifs",
                description="🔍 Aucun rappel actif pour le moment.",
                color=discord.Color.blue()
            )
            await ctx.send(embed=embed)
            return
        
        # Créer des pages d'embeds (3 rappels par page)
        rappels_list = list(rappeals_actifs.items())
        pages = []
        items_per_page = 3
        
        for i in range(0, len(rappels_list), items_per_page):
            embed = discord.Embed(
                title="📋 Liste des Rappels Actifs",
                description=f"Total: **{len(rappels_list)}** rappel(s)",
                color=discord.Color.blue(),
                timestamp=datetime.datetime.now()
            )
            
            page_rappels = rappels_list[i:i+items_per_page]
            
            for rid, r in page_rappels:
                user = ctx.guild.get_member(r["user_id"])
                user_mention = user.mention if user else f"ID: {r['user_id']}"
                
                chapitres = r.get("chapitres", [r.get("chapitre", 0)])
                chapitres_str = ", ".join([f"#{c}" for c in chapitres])
                
                # Calculer les jours restants
                try:
                    date_limite = datetime.datetime.strptime(r["date_limite"], "%Y-%m-%d")
                    delta = (date_limite.date() - datetime.datetime.now().date()).days
                    
                    if delta <= 1:
                        urgence = "🔴 URGENT"
                    elif delta <= 3:
                        urgence = "🟡 Bientôt"
                    else:
                        urgence = "🟢 À venir"
                    
                    temps_restant = f"{urgence} ({delta} jour{'s' if delta > 1 else ''})"
                except:
                    temps_restant = "N/A"
                
                manga_emoji = get_manga_emoji(r["manga"])
                task_emoji = get_task_emoji(r["task"])
                
                field_value = (
                    f"👤 {user_mention}\n"
                    f"{manga_emoji} **{r['manga']}** - Chapitres {chapitres_str}\n"
                    f"{task_emoji} Tâche: **{r['task'].capitalize()}**\n"
                    f"📅 Date limite: `{r['date_limite']}`\n"
                    f"⏰ {temps_restant}"
                )
                
                embed.add_field(
                    name=f"ID: `{rid[:40]}...`",
                    value=field_value,
                    inline=False
                )
                embed.add_field(name="━━━━━━━━━━━━━━━━━━━━", value="", inline=False)
            
            embed.set_footer(
                text=f"Page {len(pages) + 1}/{(len(rappels_list) + items_per_page - 1) // items_per_page} | Demandé par {ctx.author.name}",
                icon_url=ctx.author.avatar.url if ctx.author.avatar else None
            )
            pages.append(embed)
        
        # Système de pagination
        if len(pages) == 1:
            await ctx.send(embed=pages[0])
            return
        
        current_page = 0
        message = await ctx.send(embed=pages[current_page])
        
        await message.add_reaction('⬅️')
        await message.add_reaction('➡️')
        await message.add_reaction('❌')
        
        def check(reaction, user):
            return user == ctx.author and str(reaction.emoji) in ['⬅️', '➡️', '❌'] and reaction.message.id == message.id
        
        while True:
            try:
                reaction, user = await self.bot.wait_for('reaction_add', timeout=60.0, check=check)
                
                if str(reaction.emoji) == '⬅️':
                    if current_page > 0:
                        current_page -= 1
                        await message.edit(embed=pages[current_page])
                elif str(reaction.emoji) == '➡️':
                    if current_page < len(pages) - 1:
                        current_page += 1
                        await message.edit(embed=pages[current_page])
                elif str(reaction.emoji) == '❌':
                    await message.clear_reactions()
                    break
                
                await message.remove_reaction(reaction, user)
            
            except asyncio.TimeoutError:
                await message.clear_reactions()
                break

    @commands.command(name='delete_rappel')
    @commands.has_any_role(1326417422663680090, 1330147432847114321)
    async def delete_rappel(self, ctx, *, rappel_id: str):
        """Supprime un rappel par son ID"""
        if rappel_id in rappeals_actifs:
            rappel_info = rappeals_actifs[rappel_id]
            del rappeals_actifs[rappel_id]
            sauvegarder_rappels()
            
            chapitres = rappel_info.get("chapitres", [rappel_info.get("chapitre", 0)])
            chapitres_str = ", ".join([f"#{c}" for c in chapitres])
            
            embed = discord.Embed(
                title="🗑️ Rappel Supprimé",
                description=f"Le rappel a été supprimé avec succès.",
                color=discord.Color.red(),
                timestamp=datetime.datetime.now()
            )
            embed.add_field(name=f"{get_manga_emoji(rappel_info.get('manga', ''))} Manga", value=rappel_info.get("manga", "N/A"), inline=True)
            embed.add_field(name="📖 Chapitres", value=chapitres_str, inline=True)
            embed.add_field(name=f"{get_task_emoji(rappel_info.get('task', ''))} Tâche", value=rappel_info.get("task", "N/A").capitalize(), inline=True)
            embed.add_field(name="🆔 ID", value=f"`{rappel_id[:50]}...`", inline=False)
            embed.set_footer(text=f"Supprimé par {ctx.author.name}")
            
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
                title="💾 Sauvegarde des Rappels",
                description="✅ Les rappels ont été sauvegardés avec succès !",
                color=discord.Color(0x2ECC71),
                timestamp=datetime.datetime.utcnow()
            )
            embed.add_field(name="📊 Nombre de rappels", value=f"**{len(rappeals_actifs)}** rappel(s)", inline=True)
            embed.add_field(name="⏰ Dernière sauvegarde", value=meta.get("last_saved", "N/A"), inline=True)
            
            if rappeals_actifs:
                rappels_preview = "\n".join([f"• `{rid[:40]}...`" for rid in list(rappeals_actifs.keys())[:5]])
                if len(rappeals_actifs) > 5:
                    rappels_preview += f"\n... et {len(rappeals_actifs) - 5} autre(s)"
                embed.add_field(name="📋 Rappels enregistrés", value=rappels_preview, inline=False)
            
            embed.set_footer(text=f"Demandé par {ctx.author.name}", icon_url=ctx.author.avatar.url if ctx.author.avatar else None)
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
                title="♻️ Rechargement des Rappels",
                description="✅ Les rappels ont été rechargés depuis le fichier !",
                color=discord.Color(0x3498DB),
                timestamp=datetime.datetime.utcnow()
            )
            embed.add_field(name="📊 Nombre de rappels chargés", value=f"**{len(rappeals_actifs)}** rappel(s)", inline=True)
            embed.add_field(name="⏰ Dernière sauvegarde", value=meta.get("last_saved", "N/A"), inline=True)
            
            if rappeals_actifs:
                rappels_preview = "\n".join([f"• `{rid[:40]}...`" for rid in list(rappeals_actifs.keys())[:5]])
                if len(rappeals_actifs) > 5:
                    rappels_preview += f"\n... et {len(rappeals_actifs) - 5} autre(s)"
                embed.add_field(name="📋 Rappels chargés", value=rappels_preview, inline=False)
            
            embed.set_footer(text=f"Demandé par {ctx.author.name}", icon_url=ctx.author.avatar.url if ctx.author.avatar else None)
            await ctx.send(embed=embed)
        
        else:
            embed = discord.Embed(
                title="❌ Action Invalide",
                description="**Usage:** `!actualiser_rappels save` ou `!actualiser_rappels reload`",
                color=discord.Color.red()
            )
            embed.add_field(name="💾 save", value="Sauvegarder l'état actuel des rappels", inline=False)
            embed.add_field(name="♻️ reload", value="Recharger les rappels depuis le fichier", inline=False)
            await ctx.send(embed=embed)

    @commands.command(name='test_rappel')
    @commands.has_any_role(1326417422663680090, 1330147432847114321)
    async def test_rappel(self, ctx):
        """Teste l'envoi d'un rappel immédiatement (pour debug)"""
        await ctx.send("🧪 Test de l'envoi des rappels en cours...")
        await envoyer_rappel(self.bot)
        await ctx.send("✅ Test terminé ! Vérifiez si les rappels ont été envoyés.")

# Setup pour discord.py 2.0+
async def setup(bot):
    await bot.add_cog(RappelTask(bot))