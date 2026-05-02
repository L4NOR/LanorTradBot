# engagement.py
# ═══════════════════════════════════════════════════════════════════════════════
# SYSTÈME D'ENGAGEMENT — Daily reward calendar, Quiz manga, Reading challenges,
# Prédictions, Anniversaires, Compte à rebours sorties (planning).
# ═══════════════════════════════════════════════════════════════════════════════

import discord
from discord.ext import commands, tasks
from discord.ui import View, Button
import asyncio
import logging
import random
import time
from datetime import datetime, timedelta, date

from config import COLORS, ADMIN_ROLES, DATA_DIR, MANGA_EMOJIS
from utils import load_json, save_json
from community import add_xp, get_user_stats

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════════
# CONSTANTES
# ═══════════════════════════════════════════════════════════════════════════════

ENGAGEMENT_FILE = f"{DATA_DIR}/engagement.json"
PLANNING_CHANNEL_ID = 1332363693174034472  # Salon planning (countdown auto)

# ─── Calendrier de récompenses sur 7 jours (cycle) ────────────────────────────
DAILY_CALENDAR = [
    {"day": 1, "xp": 30,  "label": "Jour 1",                    "loot": None},
    {"day": 2, "xp": 60,  "label": "Jour 2",                    "loot": None},
    {"day": 3, "xp": 100, "label": "Jour 3 — Ticket loterie",   "loot": "lottery_ticket"},
    {"day": 4, "xp": 150, "label": "Jour 4",                    "loot": None},
    {"day": 5, "xp": 220, "label": "Jour 5 — Ticket loterie",   "loot": "lottery_ticket"},
    {"day": 6, "xp": 320, "label": "Jour 6",                    "loot": None},
    {"day": 7, "xp": 500, "label": "Jour 7 — JACKPOT",          "loot": "mystery_box_common"},
]

# ─── Quiz manga (questions à choix multiples) ─────────────────────────────────
# answer = index 0-3 dans options
QUIZ_POOL = [
    # Blue Exorcist
    {"manga": "Blue Exorcist", "q": "Quel est le frère jumeau de Rin Okumura ?",
     "options": ["Yukio", "Bon", "Shima", "Konekomaru"], "answer": 0},
    {"manga": "Blue Exorcist", "q": "Qui est le père biologique de Rin ?",
     "options": ["Mephisto", "Shiro", "Satan", "Lucifer"], "answer": 2},
    {"manga": "Blue Exorcist", "q": "Quelle école accueille les apprentis exorcistes ?",
     "options": ["Académie de la Vraie Croix", "Académie Myoboku", "Lycée Karasuno", "Académie Hosen"], "answer": 0},
    {"manga": "Blue Exorcist", "q": "Quelle arme Rin doit-il maintenir scellée ?",
     "options": ["Le katana Kurikara", "Le naginata", "L'épée de Mephisto", "Le shuriken"], "answer": 0},
    # Tougen Anki
    {"manga": "Tougen Anki", "q": "Quel est le prénom du protagoniste de Tougen Anki ?",
     "options": ["Shiki", "Ichiro", "Kazuki", "Renji"], "answer": 0},
    {"manga": "Tougen Anki", "q": "Quel clan affronte les Oni dans Tougen Anki ?",
     "options": ["Les Momotaro", "Les Yakuza", "Les Tengu", "Les Yokai"], "answer": 0},
    {"manga": "Tougen Anki", "q": "Comment s'appelle le pouvoir hérité par les descendants Oni ?",
     "options": ["Hakki", "Jingi", "Reiatsu", "Haki"], "answer": 1},
    # Tokyo Underworld
    {"manga": "Tokyo Underworld", "q": "Dans quel univers se déroule Tokyo Underworld ?",
     "options": ["Une école de magie", "Un Tokyo souterrain où les coupables sont jugés", "Une station spatiale", "L'époque Edo"], "answer": 1},
    {"manga": "Tokyo Underworld", "q": "Quel est le nom de famille des frères jumeaux protagonistes ?",
     "options": ["Saikawa", "Kanda", "Sakaki", "Kiryu"], "answer": 1},
    {"manga": "Tokyo Underworld", "q": "Qui est l'auteur du manga Tokyo Underworld ?",
     "options": ["Kenji Sakaki", "Tatsuki Fujimoto", "Daisuke Morimoto", "Yura Urushibara"], "answer": 0},
    # Catenaccio
    {"manga": "Catenaccio", "q": "De quel sport parle le manga Catenaccio ?",
     "options": ["Basketball", "Football", "Rugby", "Tennis"], "answer": 1},
    {"manga": "Catenaccio", "q": "Que signifie le mot 'catenaccio' en italien ?",
     "options": ["Verrou", "Attaque", "Champion", "Goal"], "answer": 0},
    {"manga": "Catenaccio", "q": "Quel est le nom du protagoniste de Catenaccio ?",
     "options": ["Asahi Sakakibara", "Yatarō Araki", "Tsubasa Ozora", "Isagi Yoichi"], "answer": 1},
    {"manga": "Catenaccio", "q": "À quel poste joue Yatarō Araki ?",
     "options": ["Attaquant", "Gardien de but", "Défenseur central", "Milieu offensif"], "answer": 2},
    # Satsudou
    {"manga": "Satsudou", "q": "Quel est le sujet principal de Satsudou ?",
     "options": ["L'art de l'assassinat", "La cuisine", "Le rugby", "La magie"], "answer": 0},
    {"manga": "Satsudou", "q": "Quel métier ordinaire le héros Akamori veut-il exercer ?",
     "options": ["Policier", "Médecin", "Salaryman", "Professeur"], "answer": 2},
    # Culture team / général
    {"manga": "Général", "q": "Comment appelle-t-on un magazine de prépublication manga ?",
     "options": ["Tankobon", "Doujin", "Magazine de serialisation", "Light novel"], "answer": 2},
    {"manga": "Général", "q": "Que veut dire 'shonen' ?",
     "options": ["Pour jeunes filles", "Pour jeunes garçons", "Pour adultes", "Pour enfants"], "answer": 1},
    {"manga": "Général", "q": "Comment appelle-t-on un volume relié de manga ?",
     "options": ["Tankobon", "Tomodachi", "Tatami", "Tachi"], "answer": 0},
]

# ─── Templates de challenges hebdomadaires ────────────────────────────────────
# Le bot pioche aléatoirement 3 challenges chaque lundi.
CHALLENGE_TEMPLATES = [
    {"id": "messages_50",  "type": "messages",  "name": "📝 Bavard du Royaume",
     "desc": "Envoie 50 messages dans les salons manga", "goal": 50, "reward_xp": 300},
    {"id": "messages_150", "type": "messages",  "name": "📜 Chroniqueur",
     "desc": "Envoie 150 messages cette semaine", "goal": 150, "reward_xp": 600},
    {"id": "daily_5",      "type": "daily",     "name": "🔥 Fidèle Lecteur",
     "desc": "Réclame ta `!daily` 5 jours différents", "goal": 5, "reward_xp": 400},
    {"id": "daily_7",      "type": "daily",     "name": "👑 Lecteur Suprême",
     "desc": "Réclame ta `!daily` chaque jour de la semaine (7/7)", "goal": 7, "reward_xp": 800},
    {"id": "minigame_10",  "type": "minigame",  "name": "🎮 Game Addict",
     "desc": "Joue à 10 mini-jeux", "goal": 10, "reward_xp": 350},
    {"id": "quiz_5",       "type": "quiz",      "name": "🧠 Cerveau de la team",
     "desc": "Réponds correctement à 5 quiz manga", "goal": 5, "reward_xp": 400},
    {"id": "quiz_15",      "type": "quiz",      "name": "🎓 Quiz Master",
     "desc": "Réponds correctement à 15 quiz manga", "goal": 15, "reward_xp": 800},
    {"id": "reaction_10",  "type": "reaction",  "name": "💜 Lecteur Réactif",
     "desc": "Réagis à 10 messages dans les salons manga", "goal": 10, "reward_xp": 250},
    {"id": "reward_3",     "type": "reward",    "name": "🎁 Collectionneur de cadeaux",
     "desc": "Réclame 3 récompenses du calendrier `!reward`", "goal": 3, "reward_xp": 350},
    {"id": "predict_1",    "type": "prediction","name": "🔮 Devin",
     "desc": "Place au moins 1 pari dans une `!prediction`", "goal": 1, "reward_xp": 200},
]

# ─── Données par défaut ───────────────────────────────────────────────────────
DEFAULT_DATA = {
    "daily_calendar": {},
    "quiz_stats": {},
    "challenges": {"week_iso": None, "active": [], "progress": {}, "claimed": {}},
    "predictions": {},
    "next_pred_id": 1,
    "birthdays": {},
    "birthday_celebrated_year": 0,
    "birthday_celebrated": [],
    "countdown_message": None,
}

# ═══════════════════════════════════════════════════════════════════════════════
# DONNÉES EN MÉMOIRE
# ═══════════════════════════════════════════════════════════════════════════════

data = {}


def charger():
    global data
    data = load_json(ENGAGEMENT_FILE, DEFAULT_DATA.copy())
    # Migration : s'assurer que toutes les clés par défaut existent
    for k, v in DEFAULT_DATA.items():
        data.setdefault(k, v if not isinstance(v, (dict, list)) else (v.copy() if isinstance(v, dict) else list(v)))
    data["challenges"].setdefault("week_iso", None)
    data["challenges"].setdefault("active", [])
    data["challenges"].setdefault("progress", {})
    data["challenges"].setdefault("claimed", {})
    logger.info(f"📊 Engagement: chargé ({len(data['birthdays'])} anniversaires, "
                f"{len(data['predictions'])} prédictions)")


def sauvegarder():
    save_json(ENGAGEMENT_FILE, data)


def _user_key(user_id):
    return str(user_id)


# ═══════════════════════════════════════════════════════════════════════════════
# TRACKING DES CHALLENGES (helper appelable depuis n'importe où)
# ═══════════════════════════════════════════════════════════════════════════════

def update_challenge_progress(user_id, ctype, amount=1):
    """Incrémente la progression d'un type de challenge pour un utilisateur.

    ctype ∈ {"messages","daily","minigame","quiz","reaction","reward","prediction"}
    """
    challenges = data.get("challenges", {})
    active = challenges.get("active", [])
    if not active:
        return

    progress = challenges.setdefault("progress", {})
    user_prog = progress.setdefault(_user_key(user_id), {})

    changed = False
    for c in active:
        if c["type"] == ctype:
            cid = c["id"]
            current = user_prog.get(cid, 0)
            if current < c["goal"]:
                user_prog[cid] = min(current + amount, c["goal"])
                changed = True

    if changed:
        sauvegarder()


# ═══════════════════════════════════════════════════════════════════════════════
# QUIZ — Vue avec boutons (QCM)
# ═══════════════════════════════════════════════════════════════════════════════

class QuizView(View):
    def __init__(self, author_id, question, timeout=25, hint=False):
        super().__init__(timeout=timeout)
        self.author_id = author_id
        self.question = question
        self.answered = False
        self.chosen = None
        self.message = None
        self.hint_used = hint

        # Si hint : on désactive 2 mauvaises réponses pour ne laisser
        # que la bonne + 1 leurre. On garde la bonne et on supprime 2
        # des (n-1) mauvaises options.
        disabled_indices = set()
        if hint and len(question["options"]) >= 3:
            correct = question["answer"]
            wrong = [i for i in range(len(question["options"])) if i != correct]
            random.shuffle(wrong)
            # On désactive toutes les mauvaises sauf 1 (ne laisse que 2 choix)
            for idx in wrong[:-1]:
                disabled_indices.add(idx)

        for i, opt in enumerate(question["options"]):
            btn = QuizButton(label=f"{chr(65+i)}. {opt[:75]}", index=i)
            if i in disabled_indices:
                btn.disabled = True
                btn.style = discord.ButtonStyle.secondary
            self.add_item(btn)

    async def on_timeout(self):
        if self.answered or self.message is None:
            return
        for child in self.children:
            child.disabled = True
        try:
            embed = self.message.embeds[0]
            embed.color = COLORS["warning"]
            embed.add_field(
                name="⌛ Temps écoulé",
                value=f"La bonne réponse était : **{chr(65 + self.question['answer'])}. "
                      f"{self.question['options'][self.question['answer']]}**",
                inline=False,
            )
            await self.message.edit(embed=embed, view=self)
        except Exception:
            pass


class QuizButton(Button):
    def __init__(self, label, index):
        super().__init__(label=label, style=discord.ButtonStyle.secondary)
        self.index = index

    async def callback(self, interaction: discord.Interaction):
        view: QuizView = self.view  # type: ignore
        if interaction.user.id != view.author_id:
            await interaction.response.send_message(
                "❌ Ce quiz n'est pas pour toi ! Lance ton propre `!quizmanga`.",
                ephemeral=True,
            )
            return
        if view.answered:
            await interaction.response.defer()
            return

        view.answered = True
        view.chosen = self.index
        question = view.question
        correct = (self.index == question["answer"])

        # Désactiver tous les boutons et highlight
        for child in view.children:
            child.disabled = True
            if isinstance(child, QuizButton):
                if child.index == question["answer"]:
                    child.style = discord.ButtonStyle.success
                elif child.index == self.index:
                    child.style = discord.ButtonStyle.danger

        # Mettre à jour stats
        stats = data["quiz_stats"].setdefault(_user_key(view.author_id), {
            "correct": 0, "total": 0, "best_streak": 0, "current_streak": 0
        })
        stats["total"] += 1
        if correct:
            stats["correct"] += 1
            stats["current_streak"] += 1
            stats["best_streak"] = max(stats["best_streak"], stats["current_streak"])
        else:
            stats["current_streak"] = 0

        # XP
        xp_amount = 0
        if correct:
            xp_amount = 12 + (3 * min(stats["current_streak"], 10))  # base 12 + streak max +30
            try:
                add_xp(view.author_id, xp_amount, "quiz_manga")
            except Exception:
                pass
            update_challenge_progress(view.author_id, "quiz", 1)

        sauvegarder()

        # Embed de résultat
        if correct:
            embed = discord.Embed(
                title="✅ Bonne réponse !",
                description=f"**{question['q']}**\n\n"
                            f"Tu gagnes **{xp_amount} XP** !",
                color=COLORS["success"],
            )
            embed.add_field(name="🔥 Série", value=f"{stats['current_streak']} bonnes réponses d'affilée", inline=True)
            embed.add_field(name="📊 Stats", value=f"{stats['correct']}/{stats['total']}", inline=True)
        else:
            embed = discord.Embed(
                title="❌ Mauvaise réponse",
                description=(f"**{question['q']}**\n\n"
                             f"La bonne réponse était : **{chr(65 + question['answer'])}. "
                             f"{question['options'][question['answer']]}**"),
                color=COLORS["error"],
            )
            embed.add_field(name="💔 Série brisée", value="Réessaie pour rebâtir ta série !", inline=False)
            embed.add_field(name="📊 Stats", value=f"{stats['correct']}/{stats['total']}", inline=True)

        embed.set_footer(text=f"Quiz manga · {question.get('manga', 'Général')}")

        await interaction.response.edit_message(embed=embed, view=view)


# ═══════════════════════════════════════════════════════════════════════════════
# COG PRINCIPAL
# ═══════════════════════════════════════════════════════════════════════════════

class EngagementSystem(commands.Cog):
    """Daily reward calendar, Quiz, Prédictions, Anniversaires, Countdown sorties."""

    def __init__(self, bot):
        self.bot = bot
        charger()

    async def cog_load(self):
        self.birthday_loop.start()
        self.countdown_loop.start()
        self.prediction_cleanup_loop.start()
        logger.info("✅ Tâches engagement démarrées")

    def cog_unload(self):
        self.birthday_loop.cancel()
        self.countdown_loop.cancel()
        self.prediction_cleanup_loop.cancel()

    # ───────────────────────────────────────────────────────────────────────────
    # HOOK on_command_completion : tracker minigame/daily/reward pour challenges
    # ───────────────────────────────────────────────────────────────────────────

    @commands.Cog.listener()
    async def on_command_completion(self, ctx):
        if ctx.command is None:
            return
        name = ctx.command.name

        # Mini-jeux
        minigame_cmds = {
            "reaction", "unscramble", "wordle", "hangman", "chain",
            "coinflip", "slots", "roulette", "duel",
        }
        if name in minigame_cmds:
            update_challenge_progress(ctx.author.id, "minigame", 1)
        elif name == "daily":
            update_challenge_progress(ctx.author.id, "daily", 1)
        elif name in ("reward", "dailyreward"):
            update_challenge_progress(ctx.author.id, "reward", 1)

    # ───────────────────────────────────────────────────────────────────────────
    # HOOK on_message + on_raw_reaction_add : tracker messages/réactions
    # ───────────────────────────────────────────────────────────────────────────

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or message.guild is None:
            return
        try:
            from config import POINTS_ALLOWED_CHANNELS
            if message.channel.id not in POINTS_ALLOWED_CHANNELS:
                return
        except Exception:
            return
        update_challenge_progress(message.author.id, "messages", 1)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if payload.user_id == self.bot.user.id:
            return
        try:
            from config import POINTS_ALLOWED_CHANNELS
            if payload.channel_id not in POINTS_ALLOWED_CHANNELS:
                return
        except Exception:
            return
        update_challenge_progress(payload.user_id, "reaction", 1)

    # ───────────────────────────────────────────────────────────────────────────
    # Helper : limite quotidienne partagée via le cog MiniGames
    # ───────────────────────────────────────────────────────────────────────────
    async def _consume_daily_slot(self, ctx, action_name):
        """Décrémente le pool quotidien partagé via le cog MiniGames.

        Retourne True si l'utilisateur peut continuer, False si la limite est
        atteinte (un message d'erreur a déjà été envoyé par MiniGames).
        """
        mg = self.bot.get_cog("MiniGames")
        if mg is None:
            return True  # cog principal pas chargé : ne pas bloquer
        return await mg._check_daily_limit(ctx, action_name)

    # ═══════════════════════════════════════════════════════════════════════════
    # 🎁 DAILY REWARD CALENDAR — !reward
    # ═══════════════════════════════════════════════════════════════════════════

    @commands.command(name="reward", aliases=["dailyreward"])
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def reward_calendar(self, ctx):
        """Calendrier de récompenses sur 7 jours (cycle hebdomadaire)."""
        uid = _user_key(ctx.author.id)
        today = date.today().isoformat()

        cal_data = data["daily_calendar"].setdefault(uid, {
            "day": 0, "last_claim": None, "cycles_completed": 0
        })

        # Déjà réclamé aujourd'hui ?
        if cal_data.get("last_claim") == today:
            tomorrow = datetime.combine(date.today() + timedelta(days=1), datetime.min.time())
            embed = discord.Embed(
                title="⏱️ Récompense déjà réclamée",
                description=f"Tu as déjà réclamé ta récompense du jour **{cal_data['day']}** !\n"
                            f"Reviens <t:{int(tomorrow.timestamp())}:R>",
                color=COLORS["warning"],
            )
            embed.add_field(
                name="📅 Prochain palier",
                value=self._build_calendar_preview(cal_data["day"]),
                inline=False,
            )
            await ctx.send(embed=embed)
            return

        # Calculer le jour du cycle
        last_claim = cal_data.get("last_claim")
        if last_claim:
            last_dt = date.fromisoformat(last_claim)
            diff = (date.today() - last_dt).days
            if diff == 1:
                # Continuer le cycle
                next_day = cal_data["day"] + 1
                if next_day > 7:
                    cal_data["cycles_completed"] = cal_data.get("cycles_completed", 0) + 1
                    next_day = 1
                cal_data["day"] = next_day
            else:
                # Reset (cycle interrompu)
                cal_data["day"] = 1
        else:
            cal_data["day"] = 1

        cal_data["last_claim"] = today
        reward = DAILY_CALENDAR[cal_data["day"] - 1]

        # Donner l'XP
        try:
            final_xp, mult, level_up, new_level = add_xp(ctx.author.id, reward["xp"], "reward_calendar")
        except Exception:
            final_xp, mult, level_up, new_level = reward["xp"], 1.0, False, 0

        # Donner le loot bonus (item shop)
        loot_msg = ""
        loot_id = reward.get("loot")
        if loot_id:
            try:
                from shop import get_user_inventory, sauvegarder_shop, lottery_data
                inv = get_user_inventory(ctx.author.id)
                inv["items"][loot_id] = inv["items"].get(loot_id, 0) + 1
                if loot_id == "lottery_ticket":
                    if uid not in lottery_data["participants"]:
                        lottery_data["participants"].append(uid)
                sauvegarder_shop()
                loot_msg = f"\n🎁 Bonus : **{loot_id.replace('_', ' ').title()}** ajouté à ton inventaire !"
            except Exception as e:
                logger.warning(f"reward loot drop failed: {e}")

        sauvegarder()

        # Embed visuel du calendrier
        embed = discord.Embed(
            title=f"🎁 Récompense — {reward['label']}",
            description=(
                f"Tu as réclamé ta récompense du **jour {cal_data['day']}/7** !\n"
                f"+ **{final_xp} XP**" + (f" *(x{mult:.1f})*" if mult > 1 else "") + loot_msg
            ),
            color=COLORS["success"],
            timestamp=datetime.now(),
        )
        embed.add_field(
            name="📅 Calendrier de la semaine",
            value=self._build_calendar_preview(cal_data["day"]),
            inline=False,
        )
        if cal_data.get("cycles_completed", 0) > 0:
            embed.add_field(
                name="♻️ Cycles complétés",
                value=f"**{cal_data['cycles_completed']}** cycle(s) terminé(s)",
                inline=True,
            )
        embed.set_thumbnail(url=ctx.author.avatar.url if ctx.author.avatar else None)
        embed.set_footer(text="Reviens chaque jour pour ne pas casser ton cycle !")

        await ctx.send(embed=embed)
        update_challenge_progress(ctx.author.id, "reward", 1)

        if level_up:
            cog = self.bot.get_cog("CommunitySystem")
            if cog:
                try:
                    await cog.announce_level_up(ctx.author.id, new_level, ctx.channel)
                except Exception:
                    pass

    def _build_calendar_preview(self, current_day):
        lines = []
        for d in DAILY_CALENDAR:
            if d["day"] < current_day:
                marker = "✅"
            elif d["day"] == current_day:
                marker = "🟢"
            else:
                marker = "⬜"
            loot_txt = ""
            if d.get("loot"):
                loot_txt = " + 🎁"
            lines.append(f"{marker} **J{d['day']}** — {d['xp']} XP{loot_txt}")
        return "\n".join(lines)

    # ═══════════════════════════════════════════════════════════════════════════
    # 🧠 QUIZ MANGA — !quizmanga
    # ═══════════════════════════════════════════════════════════════════════════

    @commands.command(name="quizmanga", aliases=["qm", "quizm"])
    @commands.cooldown(1, 20, commands.BucketType.user)
    async def quiz_manga(self, ctx):
        """Lance un quiz à choix multiples sur les mangas de la team.

        Si tu as acheté et utilisé `quiz_hint`, une charge sera consommée
        automatiquement pour réduire le quiz à 2 choix.
        """
        if not await self._consume_daily_slot(ctx, "quizmanga"):
            return

        question = random.choice(QUIZ_POOL)

        # Charge d'indice disponible ?
        hint = False
        try:
            from effects import has_hint, consume_hint
            if has_hint(ctx.author.id):
                if consume_hint(ctx.author.id):
                    hint = True
        except Exception as e:
            logger.warning(f"hint consume error: {e}")

        title = "🧠 Quiz Manga LanorTrad" + (" 💡" if hint else "")
        embed = discord.Embed(
            title=title,
            description=f"**{question['q']}**\n\n"
                        + "\n".join(f"**{chr(65+i)}.** {opt}" for i, opt in enumerate(question["options"])),
            color=COLORS["info"],
        )
        footer = f"Manga : {question['manga']} · Tu as 25 secondes pour répondre"
        if hint:
            footer += " · 💡 Indice actif (2 choix)"
        embed.set_footer(text=footer)

        view = QuizView(ctx.author.id, question, timeout=25, hint=hint)
        msg = await ctx.send(embed=embed, view=view)
        view.message = msg

    @commands.command(name="quizstats", aliases=["qms"])
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def quiz_stats(self, ctx, member: discord.Member = None):
        """Affiche tes statistiques de quiz."""
        target = member or ctx.author
        stats = data["quiz_stats"].get(_user_key(target.id))
        if not stats or stats.get("total", 0) == 0:
            await ctx.send(f"❌ {target.display_name} n'a pas encore tenté de quiz ! Lance `!quizmanga`.")
            return

        ratio = stats["correct"] / stats["total"] * 100 if stats["total"] else 0
        embed = discord.Embed(
            title=f"🧠 Stats Quiz — {target.display_name}",
            color=COLORS["info"],
        )
        embed.add_field(name="✅ Bonnes réponses", value=f"**{stats['correct']}**", inline=True)
        embed.add_field(name="📝 Total", value=f"**{stats['total']}**", inline=True)
        embed.add_field(name="🎯 Précision", value=f"**{ratio:.1f}%**", inline=True)
        embed.add_field(name="🔥 Meilleure série", value=f"**{stats.get('best_streak', 0)}**", inline=True)
        embed.add_field(name="⚡ Série actuelle", value=f"**{stats.get('current_streak', 0)}**", inline=True)
        embed.set_thumbnail(url=target.avatar.url if target.avatar else None)
        await ctx.send(embed=embed)

    # ═══════════════════════════════════════════════════════════════════════════
    # 🔮 PRÉDICTIONS — !prediction
    # ═══════════════════════════════════════════════════════════════════════════

    @commands.group(name="prediction", aliases=["predict", "pari"], invoke_without_command=True)
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def prediction_group(self, ctx):
        """Gestion des prédictions communautaires."""
        embed = discord.Embed(
            title="🔮 Système de Prédictions",
            description=(
                "Pariez de l'XP sur l'issue d'événements liés aux mangas !\n\n"
                "**Sous-commandes :**\n"
                "🔹 `!prediction list` — Voir les prédictions ouvertes\n"
                "🔹 `!prediction bet <id> <option> <xp>` — Parier sur une option\n"
                "🔹 `!prediction info <id>` — Détails d'une prédiction\n\n"
                "**Admin :**\n"
                "🔹 `!prediction create <question> | <opt1> | <opt2> | ...`\n"
                "🔹 `!prediction resolve <id> <option_gagnante>`\n"
                "🔹 `!prediction cancel <id>` (rembourse tout le monde)"
            ),
            color=COLORS["info"],
        )
        await ctx.send(embed=embed)

    @prediction_group.command(name="create")
    @commands.has_any_role(*ADMIN_ROLES)
    async def prediction_create(self, ctx, *, content: str):
        """Crée une prédiction. Format : question | option1 | option2 | ..."""
        parts = [p.strip() for p in content.split("|") if p.strip()]
        if len(parts) < 3:
            await ctx.send("❌ Format : `!prediction create Question | Option 1 | Option 2 | ...` (min 2 options)")
            return
        question = parts[0]
        options = parts[1:]
        if len(options) > 6:
            await ctx.send("❌ Maximum 6 options.")
            return

        pred_id = str(data["next_pred_id"])
        data["next_pred_id"] += 1
        data["predictions"][pred_id] = {
            "id": pred_id,
            "question": question,
            "options": options,
            "bets": {},
            "resolved": False,
            "winning_option": None,
            "creator_id": ctx.author.id,
            "channel_id": ctx.channel.id,
            "created_at": datetime.now().isoformat(),
        }
        sauvegarder()

        embed = discord.Embed(
            title=f"🔮 Nouvelle Prédiction · #{pred_id}",
            description=f"**{question}**",
            color=COLORS["info"],
            timestamp=datetime.now(),
        )
        for i, opt in enumerate(options):
            embed.add_field(name=f"{chr(65+i)}. {opt}", value="*0 pari · 0 XP misé*", inline=False)
        embed.set_footer(text=f"Pour parier : !prediction bet {pred_id} <A/B/...> <xp>")
        await ctx.send(embed=embed)

    @prediction_group.command(name="bet")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def prediction_bet(self, ctx, pred_id: str, option: str, xp: int):
        """Parie de l'XP sur une option (ex: !prediction bet 1 A 100)"""
        pred = data["predictions"].get(pred_id)
        if not pred:
            await ctx.send(f"❌ Prédiction `{pred_id}` introuvable.")
            return
        if pred["resolved"]:
            await ctx.send("❌ Cette prédiction est déjà résolue.")
            return
        if xp < 10:
            await ctx.send("❌ Mise minimum : 10 XP.")
            return

        if not await self._consume_daily_slot(ctx, "prediction_bet"):
            return

        # Convertir option (lettre ou numéro) en index
        opt_idx = None
        if len(option) == 1 and option.upper().isalpha():
            opt_idx = ord(option.upper()) - 65
        elif option.isdigit():
            opt_idx = int(option) - 1
        if opt_idx is None or not (0 <= opt_idx < len(pred["options"])):
            await ctx.send(f"❌ Option invalide. Options : A-{chr(64 + len(pred['options']))}")
            return

        # Vérifier que l'utilisateur a assez d'XP
        try:
            from community import get_user_stats, add_xp as comm_add_xp
            stats = get_user_stats(ctx.author.id)
            if stats.get("xp", 0) < xp:
                await ctx.send(f"❌ Tu n'as que **{stats.get('xp', 0)} XP** sur ton solde.")
                return
        except Exception as e:
            await ctx.send(f"❌ Erreur système : {e}")
            return

        uid = _user_key(ctx.author.id)
        if uid in pred["bets"]:
            await ctx.send(f"⚠️ Tu as déjà parié sur cette prédiction (option **{chr(65 + pred['bets'][uid]['option'])}**, "
                           f"**{pred['bets'][uid]['xp']} XP**). Pas de changement possible.")
            return

        # Déduire l'XP (mise en jeu)
        try:
            comm_add_xp(ctx.author.id, -xp, f"prediction_bet_{pred_id}")
        except Exception:
            await ctx.send("❌ Impossible de prélever ta mise.")
            return

        pred["bets"][uid] = {"option": opt_idx, "xp": xp}
        sauvegarder()

        embed = discord.Embed(
            title="🎲 Pari enregistré !",
            description=(f"**Prédiction #{pred_id}** : {pred['question']}\n\n"
                         f"Tu as misé **{xp} XP** sur **{chr(65 + opt_idx)}. {pred['options'][opt_idx]}**.\n"
                         f"Bonne chance ! 🍀"),
            color=COLORS["success"],
        )
        await ctx.send(embed=embed)
        update_challenge_progress(ctx.author.id, "prediction", 1)

    @prediction_group.command(name="list")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def prediction_list(self, ctx):
        """Liste les prédictions ouvertes."""
        opens = [p for p in data["predictions"].values() if not p["resolved"]]
        if not opens:
            await ctx.send("📭 Aucune prédiction ouverte. Reviens plus tard !")
            return
        embed = discord.Embed(
            title="🔮 Prédictions Ouvertes",
            color=COLORS["info"],
        )
        for p in opens[:10]:
            total_xp = sum(b["xp"] for b in p["bets"].values())
            embed.add_field(
                name=f"#{p['id']} — {p['question'][:80]}",
                value=f"💎 **{total_xp} XP** misés · {len(p['bets'])} parieur(s)\n"
                      f"`!prediction info {p['id']}` pour les détails",
                inline=False,
            )
        await ctx.send(embed=embed)

    @prediction_group.command(name="info")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def prediction_info(self, ctx, pred_id: str):
        """Détails d'une prédiction."""
        pred = data["predictions"].get(pred_id)
        if not pred:
            await ctx.send(f"❌ Prédiction `{pred_id}` introuvable.")
            return

        # Compter les paris par option
        per_option = [{"count": 0, "xp": 0} for _ in pred["options"]]
        for b in pred["bets"].values():
            per_option[b["option"]]["count"] += 1
            per_option[b["option"]]["xp"] += b["xp"]
        total_xp = sum(o["xp"] for o in per_option)

        embed = discord.Embed(
            title=f"🔮 Prédiction #{pred_id}",
            description=f"**{pred['question']}**",
            color=COLORS["success"] if pred["resolved"] else COLORS["info"],
        )
        for i, opt in enumerate(pred["options"]):
            o = per_option[i]
            pct = (o["xp"] / total_xp * 100) if total_xp > 0 else 0
            bar_filled = int(pct / 10)
            bar = "█" * bar_filled + "░" * (10 - bar_filled)
            crown = " 👑" if pred["resolved"] and pred["winning_option"] == i else ""
            embed.add_field(
                name=f"{chr(65+i)}. {opt}{crown}",
                value=f"`{bar}` {pct:.0f}%\n👥 {o['count']} pari(s) · 💎 {o['xp']} XP",
                inline=False,
            )
        if pred["resolved"]:
            embed.set_footer(text="✅ Prédiction résolue")
        else:
            embed.set_footer(text=f"Parier : !prediction bet {pred_id} <A/B/...> <xp>")
        await ctx.send(embed=embed)

    @prediction_group.command(name="resolve")
    @commands.has_any_role(*ADMIN_ROLES)
    async def prediction_resolve(self, ctx, pred_id: str, option: str):
        """Résout une prédiction et distribue les gains au prorata."""
        pred = data["predictions"].get(pred_id)
        if not pred:
            await ctx.send(f"❌ Prédiction `{pred_id}` introuvable.")
            return
        if pred["resolved"]:
            await ctx.send("❌ Déjà résolue.")
            return

        # Index option gagnante
        if len(option) == 1 and option.upper().isalpha():
            win_idx = ord(option.upper()) - 65
        elif option.isdigit():
            win_idx = int(option) - 1
        else:
            await ctx.send("❌ Option invalide.")
            return
        if not (0 <= win_idx < len(pred["options"])):
            await ctx.send("❌ Option hors limites.")
            return

        # Calculer les pots
        winners_pot = sum(b["xp"] for b in pred["bets"].values() if b["option"] == win_idx)
        total_pot = sum(b["xp"] for b in pred["bets"].values())

        winners_lines = []
        insured_refunds = []  # (uid, refund)
        if winners_pot > 0:
            for uid, b in pred["bets"].items():
                if b["option"] == win_idx:
                    share = b["xp"] / winners_pot
                    payout = int(total_pot * share)
                    try:
                        from community import add_xp as comm_add_xp
                        comm_add_xp(int(uid), payout, f"prediction_win_{pred_id}")
                    except Exception:
                        pass
                    winners_lines.append(f"<@{uid}> → **+{payout} XP** (mise : {b['xp']})")

        # Assurance : les perdants ayant une prediction_insurance active
        # récupèrent 50% de leur mise.
        try:
            from effects import has_prediction_insurance, consume_prediction_insurance
            from community import add_xp as comm_add_xp
            for uid, b in pred["bets"].items():
                if b["option"] == win_idx:
                    continue  # c'est un gagnant
                if has_prediction_insurance(int(uid), pred_id):
                    refund = int(b["xp"] * 0.5)
                    if refund > 0:
                        try:
                            comm_add_xp(int(uid), refund, f"prediction_insurance_{pred_id}")
                            insured_refunds.append((uid, refund))
                        except Exception:
                            pass
                    consume_prediction_insurance(int(uid), pred_id)
        except Exception as e:
            logger.warning(f"prediction insurance error: {e}")

        pred["resolved"] = True
        pred["winning_option"] = win_idx
        sauvegarder()

        embed = discord.Embed(
            title=f"✅ Prédiction #{pred_id} résolue",
            description=f"**{pred['question']}**\n\n"
                        f"🏆 Réponse : **{chr(65 + win_idx)}. {pred['options'][win_idx]}**",
            color=COLORS["success"],
        )
        embed.add_field(name="💰 Cagnotte totale", value=f"**{total_pot} XP**", inline=True)
        embed.add_field(name="🏆 Gagnants", value=f"**{len([b for b in pred['bets'].values() if b['option'] == win_idx])}**", inline=True)
        if winners_lines:
            embed.add_field(name="📜 Distribution", value="\n".join(winners_lines[:15]) or "—", inline=False)
        else:
            embed.add_field(name="📭 Aucun gagnant", value="Personne n'avait misé sur la bonne option, la cagnotte est perdue.", inline=False)
        if insured_refunds:
            lines = [f"<@{uid}> → **+{refund} XP** *(50%)*" for uid, refund in insured_refunds[:15]]
            embed.add_field(name="📜 Assurances remboursées", value="\n".join(lines), inline=False)
        await ctx.send(embed=embed)

    @prediction_group.command(name="cancel")
    @commands.has_any_role(*ADMIN_ROLES)
    async def prediction_cancel(self, ctx, pred_id: str):
        """Annule une prédiction et rembourse tous les parieurs."""
        pred = data["predictions"].get(pred_id)
        if not pred:
            await ctx.send(f"❌ Prédiction `{pred_id}` introuvable.")
            return
        if pred["resolved"]:
            await ctx.send("❌ Déjà résolue.")
            return

        refunded = 0
        try:
            from community import add_xp as comm_add_xp
            for uid, b in pred["bets"].items():
                comm_add_xp(int(uid), b["xp"], f"prediction_refund_{pred_id}")
                refunded += b["xp"]
        except Exception:
            pass

        pred["resolved"] = True
        pred["winning_option"] = -1
        sauvegarder()

        await ctx.send(f"♻️ Prédiction `#{pred_id}` annulée. **{refunded} XP** remboursés à {len(pred['bets'])} parieur(s).")

    @tasks.loop(hours=24)
    async def prediction_cleanup_loop(self):
        """Supprime les prédictions résolues depuis plus de 14 jours."""
        try:
            cutoff = datetime.now() - timedelta(days=14)
            to_del = []
            for pid, p in data["predictions"].items():
                if p.get("resolved"):
                    try:
                        created = datetime.fromisoformat(p.get("created_at", ""))
                        if created < cutoff:
                            to_del.append(pid)
                    except Exception:
                        pass
            for pid in to_del:
                del data["predictions"][pid]
            if to_del:
                sauvegarder()
                logger.info(f"🧹 {len(to_del)} prédiction(s) résolue(s) nettoyée(s)")
        except Exception:
            logger.exception("prediction_cleanup_loop")

    @prediction_cleanup_loop.before_loop
    async def before_pred_cleanup(self):
        await self.bot.wait_until_ready()

    # ═══════════════════════════════════════════════════════════════════════════
    # 🎂 ANNIVERSAIRES — !birthday
    # ═══════════════════════════════════════════════════════════════════════════

    @commands.group(name="birthday", aliases=["bday", "anniv"], invoke_without_command=True)
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def birthday_group(self, ctx):
        """Gestion des anniversaires."""
        embed = discord.Embed(
            title="🎂 Système d'Anniversaires",
            description=(
                "**Sous-commandes :**\n"
                "🔹 `!birthday set JJ-MM` — Enregistre ton anniversaire\n"
                "🔹 `!birthday remove` — Supprime ton anniversaire\n"
                "🔹 `!birthday upcoming` — Voir les prochains anniversaires\n"
                "🔹 `!birthday me` — Voir ta date enregistrée\n\n"
                "🎁 Le jour de ton anniversaire, tu reçois **+500 XP** et un message du bot !"
            ),
            color=COLORS["info"],
        )
        await ctx.send(embed=embed)

    @birthday_group.command(name="set")
    @commands.cooldown(1, 30, commands.BucketType.user)
    async def bday_set(self, ctx, date_str: str):
        """Enregistre ton anniversaire (format JJ-MM)."""
        try:
            parts = date_str.replace("/", "-").split("-")
            day = int(parts[0])
            month = int(parts[1])
            # Validation : on essaie de créer une date pour valider
            date(2000, month, day)
        except (ValueError, IndexError):
            await ctx.send("❌ Format invalide. Utilise `!birthday set JJ-MM` (ex: `!birthday set 24-12`).")
            return

        uid = _user_key(ctx.author.id)
        data["birthdays"][uid] = f"{month:02d}-{day:02d}"
        sauvegarder()

        embed = discord.Embed(
            title="🎂 Anniversaire enregistré !",
            description=f"Ton anniversaire est noté : **{day:02d}/{month:02d}**.\n"
                        f"Le jour J, le bot t'enverra un message et tu gagneras **+500 XP** !",
            color=COLORS["success"],
        )
        await ctx.send(embed=embed)

    @birthday_group.command(name="remove", aliases=["delete"])
    @commands.cooldown(1, 30, commands.BucketType.user)
    async def bday_remove(self, ctx):
        """Supprime ton anniversaire."""
        uid = _user_key(ctx.author.id)
        if uid in data["birthdays"]:
            del data["birthdays"][uid]
            sauvegarder()
            await ctx.send("✅ Ton anniversaire a été supprimé.")
        else:
            await ctx.send("❌ Tu n'avais pas enregistré d'anniversaire.")

    @birthday_group.command(name="me")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def bday_me(self, ctx):
        """Affiche ta date d'anniversaire enregistrée."""
        uid = _user_key(ctx.author.id)
        bday = data["birthdays"].get(uid)
        if not bday:
            await ctx.send("❌ Tu n'as pas encore enregistré ton anniversaire. Utilise `!birthday set JJ-MM`.")
            return
        m, d = bday.split("-")
        await ctx.send(f"🎂 Ton anniversaire est le **{d}/{m}**.")

    @birthday_group.command(name="upcoming", aliases=["next", "list"])
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def bday_upcoming(self, ctx):
        """Affiche les 10 prochains anniversaires."""
        if not data["birthdays"]:
            await ctx.send("📭 Aucun anniversaire enregistré sur le serveur.")
            return

        today = date.today()
        items = []
        for uid, bday in data["birthdays"].items():
            try:
                m, d = bday.split("-")
                m, d = int(m), int(d)
                # Calculer le prochain anniversaire
                this_year = date(today.year, m, d)
                if this_year < today:
                    next_bday = date(today.year + 1, m, d)
                else:
                    next_bday = this_year
                days_until = (next_bday - today).days
                items.append((uid, m, d, days_until))
            except Exception:
                continue

        items.sort(key=lambda x: x[3])

        embed = discord.Embed(
            title="🎂 Prochains anniversaires",
            color=COLORS["info"],
        )
        for uid, m, d, days_until in items[:10]:
            member = ctx.guild.get_member(int(uid))
            name = member.mention if member else f"<@{uid}>"
            if days_until == 0:
                when = "🎉 **AUJOURD'HUI !**"
            elif days_until == 1:
                when = "Demain"
            else:
                when = f"Dans **{days_until}** jour(s)"
            embed.add_field(
                name=f"{d:02d}/{m:02d}",
                value=f"{name} — {when}",
                inline=False,
            )
        await ctx.send(embed=embed)

    @tasks.loop(hours=1)
    async def birthday_loop(self):
        """Vérifie les anniversaires du jour et célèbre les nouveaux."""
        try:
            today = date.today()
            today_key = f"{today.month:02d}-{today.day:02d}"
            current_year = today.year

            # Reset annuel de la liste des célébrés
            if data.get("birthday_celebrated_year") != current_year:
                data["birthday_celebrated_year"] = current_year
                data["birthday_celebrated"] = []
                sauvegarder()

            celebrated = data.setdefault("birthday_celebrated", [])

            from config import CHANNELS
            channel = self.bot.get_channel(CHANNELS.get("general"))

            for uid, bday in list(data["birthdays"].items()):
                if bday != today_key:
                    continue
                tag = f"{current_year}-{uid}"
                if tag in celebrated:
                    continue

                # Donner l'XP
                try:
                    add_xp(int(uid), 500, "birthday")
                except Exception:
                    pass

                celebrated.append(tag)

                # Annoncer
                if channel:
                    try:
                        member = channel.guild.get_member(int(uid))
                        name = member.mention if member else f"<@{uid}>"
                        embed = discord.Embed(
                            title="🎂 JOYEUX ANNIVERSAIRE ! 🎉",
                            description=(
                                f"Toute la team **LanorTrad** souhaite un joyeux anniversaire à {name} !\n\n"
                                f"🎁 +500 XP offerts pour fêter ça !\n"
                                f"🥳 Profite bien de ta journée !"
                            ),
                            color=0xFF69B4,
                            timestamp=datetime.now(),
                        )
                        embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/3656/3656871.png")
                        await channel.send(content=name, embed=embed)
                    except Exception:
                        logger.exception("birthday announcement failed")

            sauvegarder()
        except Exception:
            logger.exception("birthday_loop")

    @birthday_loop.before_loop
    async def before_birthday(self):
        await self.bot.wait_until_ready()

    # ═══════════════════════════════════════════════════════════════════════════
    # ⏰ COMPTE À REBOURS DES SORTIES — auto dans #planning
    # ═══════════════════════════════════════════════════════════════════════════

    def _get_next_release_per_manga(self):
        """Retourne {manga_name: (date_str, chapter, status_emoji)} de la prochaine sortie par manga."""
        try:
            from planning import planning_data, STATUTS
        except Exception:
            return {}

        today = date.today().isoformat()
        per_manga = {}

        for entry in planning_data.values():
            try:
                manga = entry.get("manga", "?")
                d = entry.get("date", "")
                if not d or d < today:
                    continue
                if entry.get("status") == "sorti":
                    continue
                if manga not in per_manga or d < per_manga[manga][0]:
                    status_info = STATUTS.get(entry.get("status", "prevu"), STATUTS.get("prevu", {}))
                    per_manga[manga] = (d, entry.get("chapter", "?"), status_info.get("emoji", "📅"))
            except Exception:
                continue

        return per_manga

    def _build_countdown_embed(self):
        embed = discord.Embed(
            title="⏰ Prochaines Sorties — Compte à rebours",
            description=(
                "*Les sorties à venir des mangas de la team, en temps réel.*\n"
                "Mis à jour automatiquement toutes les 5 minutes."
            ),
            color=0x10b981,
            timestamp=datetime.now(),
        )

        per_manga = self._get_next_release_per_manga()

        # Ordre fixe par série
        from config import MANGA_ROLES
        ordered_mangas = list(MANGA_ROLES.keys())

        for manga in ordered_mangas:
            emoji = MANGA_EMOJIS.get(manga, "📚")
            if manga not in per_manga:
                embed.add_field(
                    name=f"{emoji} {manga}",
                    value="*Aucune sortie planifiée*",
                    inline=False,
                )
                continue

            date_str, chapter, status_emoji = per_manga[manga]
            try:
                dt = datetime.strptime(date_str, "%Y-%m-%d")
                # On considère 12h00 comme heure de sortie par défaut
                dt = dt.replace(hour=12, minute=0)
                ts = int(dt.timestamp())
                value = (
                    f"📖 **Chapitre {chapter}** {status_emoji}\n"
                    f"📅 <t:{ts}:F>\n"
                    f"⏳ <t:{ts}:R>"
                )
            except Exception:
                value = f"📖 **Chapitre {chapter}** — {date_str}"

            embed.add_field(name=f"{emoji} {manga}", value=value, inline=False)

        embed.set_footer(text="LanorTrad · Compte à rebours auto")
        return embed

    @tasks.loop(minutes=5)
    async def countdown_loop(self):
        """Met à jour (ou crée) le message de compte à rebours dans #planning."""
        try:
            channel = self.bot.get_channel(PLANNING_CHANNEL_ID)
            if channel is None:
                return

            embed = self._build_countdown_embed()
            stored = data.get("countdown_message")

            msg = None
            if stored and stored.get("message_id") and stored.get("channel_id") == PLANNING_CHANNEL_ID:
                try:
                    msg = await channel.fetch_message(stored["message_id"])
                except (discord.NotFound, discord.Forbidden):
                    msg = None

            if msg is None:
                try:
                    msg = await channel.send(embed=embed)
                    data["countdown_message"] = {"channel_id": channel.id, "message_id": msg.id}
                    sauvegarder()
                except Exception:
                    logger.exception("countdown_loop: send failed")
            else:
                try:
                    await msg.edit(embed=embed)
                except discord.HTTPException:
                    pass
        except Exception:
            logger.exception("countdown_loop")

    @countdown_loop.before_loop
    async def before_countdown(self):
        await self.bot.wait_until_ready()
        await asyncio.sleep(15)  # Petit délai pour que planning soit chargé

    @commands.command(name="countdown", aliases=["sorties", "nextrelease"])
    @commands.cooldown(1, 10, commands.BucketType.channel)
    async def countdown_cmd(self, ctx):
        """Affiche le compte à rebours des prochaines sorties."""
        embed = self._build_countdown_embed()
        await ctx.send(embed=embed)

    @commands.command(name="forcecountdown")
    @commands.has_any_role(*ADMIN_ROLES)
    async def force_countdown(self, ctx):
        """[Admin] Force la mise à jour du message de countdown dans le salon planning."""
        # Reset le message stocké pour forcer un nouveau send
        data["countdown_message"] = None
        sauvegarder()
        await self.countdown_loop()
        await ctx.send("✅ Message de countdown rafraîchi dans <#" + str(PLANNING_CHANNEL_ID) + ">.")


# ═══════════════════════════════════════════════════════════════════════════════
# SETUP
# ═══════════════════════════════════════════════════════════════════════════════

async def setup(bot):
    await bot.add_cog(EngagementSystem(bot))
    logger.info("✅ Cog EngagementSystem chargé")
