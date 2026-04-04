# rappels.py
# ===============================================================================
# SYSTEME DE RAPPELS DE TACHES
# Envoie les rappels dans un channel fixe OU en DM selon la preference utilisateur
# ===============================================================================

import discord
from discord.ext import commands, tasks
from discord.ui import View, Select
from config import ADMIN_ROLES, DATA_FILES, DATA_DIR, CHANNELS
from utils import load_json, save_json, save_with_meta, get_manga_emoji, get_task_emoji, paginate
import datetime
import asyncio
import pytz
import logging

# Fichiers de donnees
RAPPELS_FILE = DATA_FILES["rappels"]
RAPPELS_META_FILE = DATA_FILES["rappels_meta"]
RAPPELS_PREFS_FILE = f"{DATA_DIR}/rappels_prefs.json"

# Channel fixe pour les rappels
RAPPELS_CHANNEL_ID = CHANNELS.get("rappels", 1431607377882382396)

# Structure: {"id": {"user_id": int, "manga": str, "chapitres": [int], "task": str, "date_limite": str}}
rappels_actifs = {}

# Preferences utilisateur: {"user_id_str": "channel" | "dm"}
rappels_prefs = {}

# Variable pour eviter d'envoyer plusieurs rappels dans la meme minute
last_rappel_time = None


# ===============================================================================
# CHARGEMENT / SAUVEGARDE
# ===============================================================================

def charger_rappels():
    """Charge les rappels depuis le fichier."""
    global rappels_actifs
    rappels_actifs = load_json(RAPPELS_FILE, {})
    logging.info(f"📋 {len(rappels_actifs)} rappel(s) chargé(s)")


def sauvegarder_rappels():
    """Sauvegarde les rappels dans le fichier."""
    success = save_with_meta(RAPPELS_FILE, rappels_actifs, RAPPELS_META_FILE)
    if success:
        logging.info(f"✅ Rappels sauvegardés ({len(rappels_actifs)} rappels)")
    else:
        logging.error("❌ Erreur lors de la sauvegarde des rappels")


def charger_prefs():
    """Charge les preferences de notification des utilisateurs."""
    global rappels_prefs
    rappels_prefs = load_json(RAPPELS_PREFS_FILE, {})
    logging.info(f"📋 {len(rappels_prefs)} préférence(s) de rappel chargée(s)")


def sauvegarder_prefs():
    """Sauvegarde les preferences."""
    save_json(RAPPELS_PREFS_FILE, rappels_prefs)


def get_user_pref(user_id):
    """Retourne la preference d'un utilisateur ('channel' ou 'dm'). Defaut: 'channel'."""
    return rappels_prefs.get(str(user_id), "channel")


# ===============================================================================
# BOUTON "MARQUER COMME FAIT"
# ===============================================================================

class RappelDoneButton(discord.ui.Button):
    """Bouton pour marquer un rappel comme fait."""

    def __init__(self, rappel_id: str, manga: str, chapitres: list, task: str):
        super().__init__(
            label="✅ Marquer comme fait",
            style=discord.ButtonStyle.success,
            custom_id=f"rappel_done_{rappel_id[:80]}"
        )
        self.rappel_id = rappel_id
        self.manga = manga
        self.chapitres = chapitres
        self.task = task

    async def callback(self, interaction: discord.Interaction):
        # Mettre a jour les taches
        try:
            import commands as cmd
            task_mapping = {"traduire": "trad", "qcheck": "check"}
            task_key = task_mapping.get(self.task, self.task)

            for chap in self.chapitres:
                key = f"{self.manga}_{chap}"
                if key in cmd.etat_taches_global:
                    cmd.etat_taches_global[key][task_key] = "✅ Terminé"
                else:
                    cmd.etat_taches_global[key] = {
                        "clean": "❌ Non commencé",
                        "trad": "❌ Non commencé",
                        "check": "❌ Non commencé",
                        "edit": "❌ Non commencé"
                    }
                    cmd.etat_taches_global[key][task_key] = "✅ Terminé"
            cmd.sauvegarder_etat_taches()
        except Exception as e:
            logging.error(f"Erreur mise à jour tâche depuis rappel: {e}")

        # Supprimer le rappel
        if self.rappel_id in rappels_actifs:
            del rappels_actifs[self.rappel_id]
            sauvegarder_rappels()

        # Desactiver le bouton
        self.disabled = True
        self.label = "✅ Fait !"
        self.style = discord.ButtonStyle.secondary

        chapitres_str = ", ".join([f"#{c}" for c in self.chapitres])
        embed = discord.Embed(
            title="✅ Tâche marquée comme terminée !",
            description=f"**{self.manga}** - Chapitres {chapitres_str}\nTâche: **{self.task.capitalize()}**",
            color=discord.Color.green()
        )
        await interaction.response.edit_message(embed=embed, view=self.view)


class RappelDoneView(discord.ui.View):
    """View persistante pour le bouton 'Marquer comme fait'."""

    def __init__(self, rappel_id: str, manga: str, chapitres: list, task: str):
        super().__init__(timeout=None)
        self.add_item(RappelDoneButton(rappel_id, manga, chapitres, task))


# ===============================================================================
# SELECT PREFERENCE (channel / DM)
# ===============================================================================

class RappelPrefSelect(Select):
    def __init__(self, current_pref: str):
        options = [
            discord.SelectOption(
                label="Channel",
                value="channel",
                emoji="📢",
                description="Rappels envoyés dans le channel dédié",
                default=(current_pref == "channel")
            ),
            discord.SelectOption(
                label="Message Privé",
                value="dm",
                emoji="📩",
                description="Rappels envoyés en DM",
                default=(current_pref == "dm")
            ),
        ]
        super().__init__(placeholder="🔔 Choisir le mode de rappel...", options=options)

    async def callback(self, interaction: discord.Interaction):
        choice = self.values[0]
        rappels_prefs[str(interaction.user.id)] = choice
        sauvegarder_prefs()

        if choice == "dm":
            desc = "📩 Tes rappels seront envoyés **en message privé**."
        else:
            desc = f"📢 Tes rappels seront envoyés dans <#{RAPPELS_CHANNEL_ID}>."

        embed = discord.Embed(
            title="✅ Préférence enregistrée !",
            description=desc,
            color=discord.Color.green()
        )
        await interaction.response.edit_message(embed=embed, view=None)


class RappelPrefView(View):
    def __init__(self, current_pref: str):
        super().__init__(timeout=60)
        self.add_item(RappelPrefSelect(current_pref))


# ===============================================================================
# ENVOI DES RAPPELS
# ===============================================================================

async def envoyer_rappel(bot, force=False):
    """Tache de rappel avec fuseau horaire francais. force=True pour ignorer la verification d'heure."""
    global last_rappel_time

    tz_paris = pytz.timezone('Europe/Paris')
    now = datetime.datetime.now(tz_paris)

    # Verifier si c'est l'heure du rappel (21h) et qu'on n'a pas deja envoye aujourd'hui
    current_date = now.date()

    # Ne s'executer qu'une seule fois par jour a 21h (sauf si force=True)
    if force or (now.hour == 21 and (last_rappel_time is None or last_rappel_time != current_date)):
        logging.info(f"🔔 Déclenchement des rappels à {now.strftime('%Y-%m-%d %H:%M:%S')}{' (FORCÉ)' if force else ''}")
        if not force:
            last_rappel_time = current_date

        rappels_envoyes = 0
        rappels_ignores = 0
        rappels_erreurs = 0

        # Recuperer le channel fixe
        rappel_channel = bot.get_channel(RAPPELS_CHANNEL_ID)

        for rappel_id, rappel in list(rappels_actifs.items()):
            try:
                # Parser la date limite
                date_limite_str = rappel.get("date_limite", "")
                if not date_limite_str:
                    logging.warning(f"⚠️ Rappel {rappel_id} n'a pas de date limite définie")
                    rappels_erreurs += 1
                    continue

                date_limite = datetime.datetime.strptime(date_limite_str, "%Y-%m-%d")

                # Comparer uniquement les dates
                if now.date() > date_limite.date():
                    logging.info(f"⏩ Rappel {rappel_id} ignoré (date dépassée: {date_limite_str})")
                    rappels_ignores += 1
                    continue

                user_id = rappel["user_id"]

                # Recuperer le membre depuis n'importe quel guild du bot
                user = None
                for guild in bot.guilds:
                    user = guild.get_member(user_id)
                    if user:
                        break

                if not user:
                    logging.error(f"❌ Utilisateur {user_id} introuvable pour le rappel {rappel_id}")
                    rappels_erreurs += 1
                    continue

                manga_emoji = get_manga_emoji(rappel["manga"])
                task_emoji = get_task_emoji(rappel["task"])
                chapitres = rappel.get("chapitres", [rappel.get("chapitre", 0)])
                chapitres_str = ", ".join([f"#{c}" for c in chapitres])

                # Calculer les jours restants
                jours_restants = (date_limite.date() - now.date()).days

                # Determiner l'urgence
                if jours_restants <= 1:
                    urgence = "🔴 URGENT"
                    urgence_color = discord.Color.red()
                elif jours_restants <= 3:
                    urgence = "🟡 Bientôt"
                    urgence_color = discord.Color.gold()
                else:
                    urgence = "🟢 À venir"
                    urgence_color = discord.Color.green()

                # Construire l'embed
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

                # View avec bouton "Marquer comme fait"
                view = RappelDoneView(rappel_id, rappel["manga"], chapitres, rappel["task"])

                # -- Envoyer selon la preference --
                pref = get_user_pref(user_id)

                if pref == "dm":
                    # Envoyer en DM uniquement
                    try:
                        dm_embed = discord.Embed(
                            title=f"{task_emoji} Rappel - {rappel['manga']}",
                            description=f"N'oublie pas ta tâche **{rappel['task'].capitalize()}** !",
                            color=urgence_color
                        )
                        dm_embed.add_field(name="📖 Chapitres", value=chapitres_str, inline=True)
                        dm_embed.add_field(name="📅 Date limite", value=f"{date_limite_str} ({urgence})", inline=True)
                        dm_embed.set_footer(text="Clique sur le bouton quand c'est fait ! 💪")
                        await user.send(embed=dm_embed, view=view)
                        logging.info(f"📩 Rappel DM envoyé à {user.name}")
                    except discord.Forbidden:
                        # Fallback : envoyer dans le channel si DMs fermes
                        logging.warning(f"⚠️ DMs fermés pour {user.name}, fallback vers channel")
                        if rappel_channel:
                            await rappel_channel.send(f"🔔 {user.mention}", embed=embed, view=view)
                    except Exception as e:
                        logging.error(f"❌ Erreur DM rappel pour {user.name}: {e}")
                        if rappel_channel:
                            await rappel_channel.send(f"🔔 {user.mention}", embed=embed, view=view)
                else:
                    # Envoyer dans le channel fixe
                    if rappel_channel:
                        await rappel_channel.send(f"🔔 {user.mention}", embed=embed, view=view)
                    else:
                        logging.error(f"❌ Channel rappels {RAPPELS_CHANNEL_ID} introuvable")
                        rappels_erreurs += 1
                        continue

                logging.info(f"✅ Rappel envoyé pour {user.name} ({pref}) - {rappel['manga']} ch.{chapitres_str}")
                rappels_envoyes += 1
                await asyncio.sleep(1.5)  # Délai anti-rate-limit entre chaque rappel

            except Exception as e:
                logging.error(f"❌ Erreur lors de l'envoi du rappel {rappel_id}: {e}")
                import traceback
                traceback.print_exc()
                rappels_erreurs += 1

        logging.info(f"📊 Résumé: {rappels_envoyes} envoyé(s), {rappels_ignores} ignoré(s), {rappels_erreurs} erreur(s)")


# ===============================================================================
# COG PRINCIPAL
# ===============================================================================

class RappelTask(commands.Cog):
    """Système de rappels pour les tâches de traduction."""

    def __init__(self, bot):
        self.bot = bot
        charger_rappels()
        charger_prefs()
        # Restaurer les views persistantes pour les rappels actifs
        for rappel_id, rappel in rappels_actifs.items():
            chapitres = rappel.get("chapitres", [rappel.get("chapitre", 0)])
            view = RappelDoneView(rappel_id, rappel["manga"], chapitres, rappel["task"])
            bot.add_view(view)
        self.check_rappels.start()

    def cog_unload(self):
        self.check_rappels.cancel()
        sauvegarder_rappels()

    @tasks.loop(minutes=1)
    async def check_rappels(self):
        """Verifie les rappels a envoyer."""
        try:
            await envoyer_rappel(self.bot)
        except Exception as e:
            logging.error(f"Erreur dans check_rappels: {e}")

    @check_rappels.before_loop
    async def before_check(self):
        await self.bot.wait_until_ready()

    # -------------------------------------------------------------------------
    # COMMANDE PREFERENCE RAPPELS (accessible a tous)
    # -------------------------------------------------------------------------

    @commands.command(name='rappel_pref', aliases=['rappel_preference', 'pref_rappel'])
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def rappel_pref(self, ctx):
        """🔔 Choisis où recevoir tes rappels : dans le channel ou en DM."""
        current = get_user_pref(ctx.author.id)

        if current == "dm":
            current_text = "📩 **Message Privé**"
        else:
            current_text = f"📢 **Channel** (<#{RAPPELS_CHANNEL_ID}>)"

        embed = discord.Embed(
            title="🔔  Préférence de rappels",
            description=(
                f"**Mode actuel :** {current_text}\n\n"
                f"Choisis comment tu veux recevoir tes rappels de tâches :"
            ),
            color=discord.Color.blue()
        )
        view = RappelPrefView(current)
        await ctx.send(embed=embed, view=view)

    # -------------------------------------------------------------------------
    # COMMANDE ADMIN - AJOUTER UN RAPPEL
    # -------------------------------------------------------------------------

    @commands.command(name='add_rappel')
    @commands.has_any_role(*ADMIN_ROLES)
    async def add_rappel(self, ctx):
        """Ajoute un rappel de manière interactive."""

        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel

        try:
            # Demander l'utilisateur
            embed = discord.Embed(
                title="➕ Nouveau Rappel",
                description="Mentionnez l'utilisateur concerné (ex: @User)",
                color=discord.Color.blue()
            )
            await ctx.send(embed=embed)
            msg = await self.bot.wait_for('message', check=check, timeout=60)

            if not msg.mentions:
                await ctx.send("❌ Aucun utilisateur mentionné. Annulation.")
                return
            user = msg.mentions[0]

            # Demander le manga
            embed = discord.Embed(
                title="📚 Manga",
                description="Quel manga ?\n`Tougen Anki`, `Ao No Exorcist`, `Satsudou`, `Tokyo Underworld`, `Catenaccio`",
                color=discord.Color.blue()
            )
            await ctx.send(embed=embed)
            msg = await self.bot.wait_for('message', check=check, timeout=60)
            manga = msg.content.strip()

            # Demander les chapitres
            embed = discord.Embed(
                title="📖 Chapitres",
                description="Numéro(s) de chapitre(s) séparés par des espaces (ex: `216 217 218`)",
                color=discord.Color.blue()
            )
            await ctx.send(embed=embed)
            msg = await self.bot.wait_for('message', check=check, timeout=60)
            chapitres_raw = msg.content.strip().replace(',', ' ').split()
            chapitres = [int(c) for c in chapitres_raw if c.isdigit()]

            if not chapitres:
                await ctx.send("❌ Aucun chapitre valide. Annulation.")
                return

            # Demander la tache
            embed = discord.Embed(
                title="🔧 Tâche",
                description="Quelle tâche ?\n`clean`, `traduire`, `qcheck`, `edit`",
                color=discord.Color.blue()
            )
            await ctx.send(embed=embed)
            msg = await self.bot.wait_for('message', check=check, timeout=60)
            task = msg.content.strip().lower()

            # Demander la date limite
            embed = discord.Embed(
                title="📅 Date limite",
                description="Format: `AAAA-MM-JJ` (ex: `2026-03-31`)",
                color=discord.Color.blue()
            )
            await ctx.send(embed=embed)
            msg = await self.bot.wait_for('message', check=check, timeout=60)
            date_limite = msg.content.strip()

            # Valider le format de date
            try:
                datetime.datetime.strptime(date_limite, "%Y-%m-%d")
            except ValueError:
                await ctx.send("❌ Format de date invalide. Utilisez `AAAA-MM-JJ`.")
                return

            # Creer le rappel
            rappel_id = f"{manga}_{chapitres[0]}_{task}_{user.id}"
            rappels_actifs[rappel_id] = {
                "user_id": user.id,
                "manga": manga,
                "chapitres": chapitres,
                "task": task,
                "date_limite": date_limite,
            }
            sauvegarder_rappels()

            # Confirmation
            chapitres_str = ", ".join([f"#{c}" for c in chapitres])
            pref = get_user_pref(user.id)
            pref_text = "📩 DM" if pref == "dm" else f"📢 <#{RAPPELS_CHANNEL_ID}>"

            embed = discord.Embed(
                title="✅ Rappel Créé",
                description="Le rappel a été configuré avec succès !",
                color=discord.Color.green(),
                timestamp=datetime.datetime.now()
            )
            embed.add_field(name="👤 Utilisateur", value=user.mention, inline=True)
            embed.add_field(name=f"{get_manga_emoji(manga)} Manga", value=manga, inline=True)
            embed.add_field(name="📖 Chapitres", value=chapitres_str, inline=True)
            embed.add_field(name=f"{get_task_emoji(task)} Tâche", value=task.capitalize(), inline=True)
            embed.add_field(name="📅 Date limite", value=date_limite, inline=True)
            embed.add_field(name="🔔 Notification", value=pref_text, inline=True)
            embed.add_field(name="🆔 ID", value=f"`{rappel_id[:50]}...`", inline=False)
            embed.set_footer(text=f"Créé par {ctx.author.name}")

            await ctx.send(embed=embed)

        except asyncio.TimeoutError:
            await ctx.send("⏰ Temps écoulé. Commande annulée.")
        except Exception as e:
            await ctx.send(f"❌ Erreur: {e}")

    # -------------------------------------------------------------------------
    # COMMANDE ADMIN - LISTE DES RAPPELS
    # -------------------------------------------------------------------------

    @commands.command(name='list_rappels')
    @commands.has_any_role(*ADMIN_ROLES)
    async def list_rappels(self, ctx):
        """Liste tous les rappels actifs."""
        if not rappels_actifs:
            embed = discord.Embed(
                title="📋 Liste des Rappels",
                description="Aucun rappel actif.",
                color=discord.Color.blue()
            )
            await ctx.send(embed=embed)
            return

        # Pagination
        items_per_page = 5
        rappels_list = list(rappels_actifs.items())
        pages = []

        for i in range(0, len(rappels_list), items_per_page):
            page_rappels = rappels_list[i:i + items_per_page]

            embed = discord.Embed(
                title="📋 Liste des Rappels",
                description=f"**{len(rappels_actifs)}** rappel(s) actif(s)",
                color=discord.Color.blue(),
                timestamp=datetime.datetime.now()
            )

            for rid, r in page_rappels:
                user = ctx.guild.get_member(r["user_id"])
                user_mention = user.mention if user else f"<@{r['user_id']}>"

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
                pref = get_user_pref(r["user_id"])
                pref_icon = "📩" if pref == "dm" else "📢"

                field_value = (
                    f"👤 {user_mention} {pref_icon}\n"
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

            embed.set_footer(
                text=f"Page {len(pages) + 1}/{(len(rappels_list) + items_per_page - 1) // items_per_page}",
                icon_url=ctx.author.avatar.url if ctx.author.avatar else None
            )
            pages.append(embed)

        # Afficher avec pagination unifiee
        await paginate(ctx, pages)

    # -------------------------------------------------------------------------
    # COMMANDE ADMIN - SUPPRIMER UN RAPPEL
    # -------------------------------------------------------------------------

    @commands.command(name='delete_rappel')
    @commands.has_any_role(*ADMIN_ROLES)
    async def delete_rappel(self, ctx, *, rappel_id: str):
        """Supprime un rappel par son ID."""
        if rappel_id in rappels_actifs:
            rappel_info = rappels_actifs[rappel_id]
            del rappels_actifs[rappel_id]
            sauvegarder_rappels()

            chapitres = rappel_info.get("chapitres", [rappel_info.get("chapitre", 0)])
            chapitres_str = ", ".join([f"#{c}" for c in chapitres])

            embed = discord.Embed(
                title="🗑️ Rappel Supprimé",
                description="Le rappel a été supprimé avec succès.",
                color=discord.Color.red(),
                timestamp=datetime.datetime.now()
            )
            embed.add_field(
                name=f"{get_manga_emoji(rappel_info.get('manga', ''))} Manga",
                value=rappel_info.get("manga", "N/A"),
                inline=True
            )
            embed.add_field(name="📖 Chapitres", value=chapitres_str, inline=True)
            embed.add_field(
                name=f"{get_task_emoji(rappel_info.get('task', ''))} Tâche",
                value=rappel_info.get("task", "N/A").capitalize(),
                inline=True
            )
            embed.set_footer(text=f"Supprimé par {ctx.author.name}")

            await ctx.send(embed=embed)
        else:
            await ctx.send(f"❌ ID de rappel **{rappel_id}** introuvable.")

    # -------------------------------------------------------------------------
    # COMMANDE ADMIN - TEST RAPPELS
    # -------------------------------------------------------------------------

    @commands.command(name='test_rappel')
    @commands.has_any_role(*ADMIN_ROLES)
    async def test_rappel(self, ctx):
        """Teste l'envoi d'un rappel immédiatement (bypass la vérification d'heure)."""
        await ctx.send("🧪 Test de l'envoi des rappels en cours...")
        await envoyer_rappel(self.bot, force=True)
        await ctx.send("✅ Test terminé ! Vérifiez si les rappels ont été envoyés.")


async def setup(bot):
    """Setup pour discord.py 2.0+."""
    await bot.add_cog(RappelTask(bot))
