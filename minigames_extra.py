# minigames_extra.py
# ═══════════════════════════════════════════════════════════════════════════════
# MINI-JEUX SUPPLÉMENTAIRES — devinettes, quotes, rebus, anagram, guessmanga,
# opening, character (20Q-style), click, memory, ttt, connect4
# ═══════════════════════════════════════════════════════════════════════════════
# Tous ces jeux utilisent le système d'effets (`effects.apply_minigame_xp`)
# pour le streak multiplier et le featured daily x2.

import discord
from discord.ext import commands
from discord.ui import View, Button
import random
import asyncio
import time
from config import COLORS
from database import db
from minigames import (
    normalize,
    pick_themed_manga_word,
    announce_level_up_safe,
)
from minigames_data import (
    MANGA_WORD_THEMES,
    RIDDLES, QUOTES, EMOJI_REBUS, ANAGRAMS,
    PANELS, OPENINGS, CHARACTERS, CHARACTER_QUESTIONS,
    MEMORY_EMOJIS,
)
from effects import apply_minigame_xp, is_featured
import logging

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════════
# CONSTANTES
# ═══════════════════════════════════════════════════════════════════════════════

EXTRA_XP = {
    # Récompenses divisées par ~2 — incite à jouer plus pour le même gain
    "devinette":  9,
    "quoteguess": 8,
    "emojirebus": 8,
    "anagram":    10,
    "guessmanga": 8,
    "opening":    8,
    "character":  11,
    "click":      6,
    "memory":     9,
    "ttt":        5,
    "connect4":   8,
}

# ═══════════════════════════════════════════════════════════════════════════════
# DATA POOLS — importées depuis minigames_data.py
# ═══════════════════════════════════════════════════════════════════════════════


# ═══════════════════════════════════════════════════════════════════════════════
# UTILITAIRE COMMUN — match de réponse
# ═══════════════════════════════════════════════════════════════════════════════

def answer_match(user_input, entry):
    """Vérifie si user_input correspond à la 'answer' ou aux 'alts' d'une entrée."""
    norm = normalize(user_input.strip())
    candidates = [normalize(entry["answer"])] + [normalize(a) for a in entry.get("alts", [])]
    return norm in candidates


def _set_game_active(cog, channel_id, game_name, owner_id=None):
    """Marque un jeu actif via le cog MiniGames si possible (évite les overlap)."""
    try:
        from minigames import MiniGames  # noqa
    except Exception:
        return
    mg = cog.bot.get_cog("MiniGames")
    if mg:
        mg._set_game(channel_id, game_name, owner_id=owner_id)


def _clear_game_active(cog, channel_id):
    mg = cog.bot.get_cog("MiniGames")
    if mg:
        mg._clear_game(channel_id)


def _is_game_active(cog, channel_id):
    mg = cog.bot.get_cog("MiniGames")
    if mg:
        return mg._is_game_active(channel_id)
    return False


async def _consume_daily_slot(cog, ctx, game_name):
    """Décrémente le pool quotidien partagé via le cog MiniGames.

    Retourne True si le joueur peut jouer, False si la limite est atteinte
    (un message d'erreur a déjà été envoyé par MiniGames._check_daily_limit).
    """
    mg = cog.bot.get_cog("MiniGames")
    if mg is None:
        return True  # cog principal pas chargé : ne pas bloquer
    return await mg._check_daily_limit(ctx, game_name)


# ═══════════════════════════════════════════════════════════════════════════════
# VIEWS PARTAGÉES
# ═══════════════════════════════════════════════════════════════════════════════

class InvitationView(View):
    """Vue d'invitation à boutons (Accepter / Refuser) pour un membre cible."""

    def __init__(self, target_id, timeout=60):
        super().__init__(timeout=timeout)
        self.target_id = target_id
        self.accepted = None  # None = en attente, True/False = répondu
        self.message = None

    @discord.ui.button(label="✅ Accepter", style=discord.ButtonStyle.success)
    async def accept(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.target_id:
            await interaction.response.send_message("❌ Cette invitation ne t'est pas adressée.", ephemeral=True)
            return
        self.accepted = True
        for c in self.children:
            c.disabled = True
        await interaction.response.edit_message(view=self)
        self.stop()

    @discord.ui.button(label="❌ Refuser", style=discord.ButtonStyle.danger)
    async def refuse(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.target_id:
            await interaction.response.send_message("❌ Cette invitation ne t'est pas adressée.", ephemeral=True)
            return
        self.accepted = False
        for c in self.children:
            c.disabled = True
        await interaction.response.edit_message(view=self)
        self.stop()

    async def on_timeout(self):
        if self.accepted is None and self.message:
            for c in self.children:
                c.disabled = True
            try:
                await self.message.edit(view=self)
            except Exception:
                pass


# ═══════════════════════════════════════════════════════════════════════════════
# COG
# ═══════════════════════════════════════════════════════════════════════════════

class MiniGamesExtra(commands.Cog):
    """Mini-jeux supplémentaires (devinettes, anagrammes, ttt, connect4, etc.)."""

    def __init__(self, bot):
        self.bot = bot

    # ───────────────────────────────────────────────────────────────────────────
    # Helper : finalise XP et envoie le message de victoire/défaite uniforme
    # ───────────────────────────────────────────────────────────────────────────

    async def _finish_win(self, ctx, source, base_xp, embed):
        final, mult, level_up, new_level, info = apply_minigame_xp(
            ctx.author.id, base_xp, won=True, source=source
        )
        try:
            db.record_minigame(ctx.author.id, source, True, final)
        except Exception:
            pass

        bonus_lines = [f"**+{final} XP** gagnés !"]
        if info["streak"] >= 3:
            bonus_lines.append(f"🔥 Streak **x{info['streak']}** (bonus x{info['streak_mult']:.1f})")
        if info["featured"]:
            bonus_lines.append("⭐ **Jeu vedette du jour** — XP doublée !")

        embed.add_field(name="\u200b", value="\n".join(bonus_lines), inline=False)
        await ctx.send(embed=embed)

        if level_up:
            await announce_level_up_safe(self.bot, ctx.author.id, new_level)

    async def _finish_loss(self, ctx, source, embed):
        _final, _mult, _lvl, _nl, info = apply_minigame_xp(
            ctx.author.id, 0, won=False, source=source
        )
        try:
            db.record_minigame(ctx.author.id, source, False, 0)
        except Exception:
            pass
        if info["shielded"]:
            embed.add_field(name="🛡️ Bouclier", value="Ton streak a été protégé !", inline=False)
        await ctx.send(embed=embed)

    # ═════════════════════════════════════════════════════════════════════════
    # 🧠 DEVINETTE
    # ═════════════════════════════════════════════════════════════════════════

    @commands.command(name="devinette", aliases=["riddle"])
    @commands.cooldown(1, 15, commands.BucketType.user)
    async def devinette(self, ctx):
        """[Solo] Devine la réponse à une énigme manga."""
        if _is_game_active(self, ctx.channel.id):
            return await ctx.send("❌ Un jeu est déjà en cours dans ce channel !")
        if not await _consume_daily_slot(self, ctx, "devinette"):
            return
        _set_game_active(self, ctx.channel.id, "devinette", owner_id=ctx.author.id)
        try:
            riddle = random.choice(RIDDLES)
            featured = is_featured("devinette")
            embed = discord.Embed(
                title="🧠 Devinette" + (" ⭐" if featured else ""),
                description=(
                    f"👤 {ctx.author.mention}\n\n"
                    f"❓ *{riddle['q']}*\n\n"
                    f"⏱️ **45 secondes** pour répondre dans le chat."
                ),
                color=COLORS["info"],
            )
            if featured:
                embed.set_footer(text="⭐ Jeu vedette du jour — XP doublée !")
            await ctx.send(embed=embed)

            def check(m):
                return m.channel.id == ctx.channel.id and m.author.id == ctx.author.id

            try:
                msg = await self.bot.wait_for("message", check=check, timeout=45)
            except asyncio.TimeoutError:
                lose = discord.Embed(
                    title="🧠 Devinette — Temps écoulé !",
                    description=f"La réponse était : **{riddle['answer']}**",
                    color=COLORS["error"],
                )
                await self._finish_loss(ctx, "devinette", lose)
                return

            if answer_match(msg.content, riddle):
                win = discord.Embed(
                    title="🧠 Devinette — Bonne réponse !",
                    description=f"{ctx.author.mention} a trouvé : **{riddle['answer']}** ✅",
                    color=COLORS["success"],
                )
                await self._finish_win(ctx, "devinette", EXTRA_XP["devinette"], win)
            else:
                lose = discord.Embed(
                    title="🧠 Devinette — Mauvaise réponse",
                    description=f"La bonne réponse était : **{riddle['answer']}**",
                    color=COLORS["error"],
                )
                await self._finish_loss(ctx, "devinette", lose)
        finally:
            _clear_game_active(self, ctx.channel.id)

    # ═════════════════════════════════════════════════════════════════════════
    # 💬 QUOTEGUESS
    # ═════════════════════════════════════════════════════════════════════════

    @commands.command(name="quoteguess", aliases=["quote"])
    @commands.cooldown(1, 15, commands.BucketType.user)
    async def quoteguess(self, ctx):
        """[Solo] Devine de quel manga vient cette réplique."""
        if _is_game_active(self, ctx.channel.id):
            return await ctx.send("❌ Un jeu est déjà en cours dans ce channel !")
        if not await _consume_daily_slot(self, ctx, "quoteguess"):
            return
        _set_game_active(self, ctx.channel.id, "quoteguess", owner_id=ctx.author.id)
        try:
            quote = random.choice(QUOTES)
            featured = is_featured("quoteguess")
            embed = discord.Embed(
                title="💬 Quote Guess" + (" ⭐" if featured else ""),
                description=(
                    f"👤 {ctx.author.mention}\n\n"
                    f"📜 *{quote['text']}*\n\n"
                    f"De quel manga vient cette réplique ?\n"
                    f"⏱️ **30 secondes** pour répondre."
                ),
                color=COLORS["info"],
            )
            if featured:
                embed.set_footer(text="⭐ Jeu vedette du jour — XP doublée !")
            await ctx.send(embed=embed)

            def check(m):
                return m.channel.id == ctx.channel.id and m.author.id == ctx.author.id

            try:
                msg = await self.bot.wait_for("message", check=check, timeout=30)
            except asyncio.TimeoutError:
                lose = discord.Embed(
                    title="💬 Quote — Temps écoulé !",
                    description=f"C'était une réplique de **{quote['answer']}**",
                    color=COLORS["error"],
                )
                await self._finish_loss(ctx, "quoteguess", lose)
                return

            if answer_match(msg.content, quote):
                win = discord.Embed(
                    title="💬 Quote — Bien joué !",
                    description=f"{ctx.author.mention} a reconnu **{quote['answer']}** ✅",
                    color=COLORS["success"],
                )
                await self._finish_win(ctx, "quoteguess", EXTRA_XP["quoteguess"], win)
            else:
                lose = discord.Embed(
                    title="💬 Quote — Manqué",
                    description=f"C'était **{quote['answer']}**",
                    color=COLORS["error"],
                )
                await self._finish_loss(ctx, "quoteguess", lose)
        finally:
            _clear_game_active(self, ctx.channel.id)

    # ═════════════════════════════════════════════════════════════════════════
    # 🧩 EMOJI REBUS
    # ═════════════════════════════════════════════════════════════════════════

    @commands.command(name="emojirebus", aliases=["rebus"])
    @commands.cooldown(1, 15, commands.BucketType.user)
    async def emojirebus(self, ctx):
        """[Solo] Devine le manga/personnage codé en emojis."""
        if _is_game_active(self, ctx.channel.id):
            return await ctx.send("❌ Un jeu est déjà en cours dans ce channel !")
        if not await _consume_daily_slot(self, ctx, "emojirebus"):
            return
        _set_game_active(self, ctx.channel.id, "emojirebus", owner_id=ctx.author.id)
        try:
            rebus = random.choice(EMOJI_REBUS)
            featured = is_featured("emojirebus")
            embed = discord.Embed(
                title="🧩 Emoji Rebus" + (" ⭐" if featured else ""),
                description=(
                    f"👤 {ctx.author.mention}\n\n"
                    f"## {rebus['emoji']}\n\n"
                    f"À quoi ces emojis font-ils référence ?\n"
                    f"⏱️ **30 secondes** pour répondre."
                ),
                color=COLORS["info"],
            )
            if featured:
                embed.set_footer(text="⭐ Jeu vedette du jour — XP doublée !")
            await ctx.send(embed=embed)

            def check(m):
                return m.channel.id == ctx.channel.id and m.author.id == ctx.author.id

            try:
                msg = await self.bot.wait_for("message", check=check, timeout=30)
            except asyncio.TimeoutError:
                lose = discord.Embed(
                    title="🧩 Rebus — Temps écoulé !",
                    description=f"La réponse était : **{rebus['answer']}**",
                    color=COLORS["error"],
                )
                await self._finish_loss(ctx, "emojirebus", lose)
                return

            if answer_match(msg.content, rebus):
                win = discord.Embed(
                    title="🧩 Rebus — Trouvé !",
                    description=f"{ctx.author.mention} a décodé **{rebus['answer']}** ✅",
                    color=COLORS["success"],
                )
                await self._finish_win(ctx, "emojirebus", EXTRA_XP["emojirebus"], win)
            else:
                lose = discord.Embed(
                    title="🧩 Rebus — Manqué",
                    description=f"La réponse était : **{rebus['answer']}**",
                    color=COLORS["error"],
                )
                await self._finish_loss(ctx, "emojirebus", lose)
        finally:
            _clear_game_active(self, ctx.channel.id)

    # ═════════════════════════════════════════════════════════════════════════
    # 🔠 ANAGRAM
    # ═════════════════════════════════════════════════════════════════════════

    @commands.command(name="anagram", aliases=["anagramme"])
    @commands.cooldown(1, 15, commands.BucketType.user)
    async def anagram(self, ctx):
        """[Solo] Démêle l'anagramme — un titre/mot dont les lettres sont mélangées."""
        if _is_game_active(self, ctx.channel.id):
            return await ctx.send("❌ Un jeu est déjà en cours dans ce channel !")
        if not await _consume_daily_slot(self, ctx, "anagram"):
            return
        _set_game_active(self, ctx.channel.id, "anagram", owner_id=ctx.author.id)
        try:
            entry = random.choice(ANAGRAMS)
            answer = entry["answer"]
            # Mélanger en gardant les espaces
            letters = list(answer.replace(" ", ""))
            random.shuffle(letters)
            scrambled = " ".join(l.upper() for l in letters)

            featured = is_featured("anagram")
            embed = discord.Embed(
                title="🔠 Anagramme" + (" ⭐" if featured else ""),
                description=(
                    f"👤 {ctx.author.mention}\n\n"
                    f"💡 **Indice :** *{entry['clue']}*\n\n"
                    f"# `{scrambled}`\n\n"
                    f"📏 {len(answer.replace(' ', ''))} lettres "
                    f"({'plusieurs mots' if ' ' in answer else 'un seul mot'})\n"
                    f"⏱️ **45 secondes** pour répondre."
                ),
                color=COLORS["info"],
            )
            if featured:
                embed.set_footer(text="⭐ Jeu vedette du jour — XP doublée !")
            await ctx.send(embed=embed)

            def check(m):
                return m.channel.id == ctx.channel.id and m.author.id == ctx.author.id

            try:
                msg = await self.bot.wait_for("message", check=check, timeout=45)
            except asyncio.TimeoutError:
                lose = discord.Embed(
                    title="🔠 Anagramme — Temps écoulé !",
                    description=f"La réponse était : **{answer}**",
                    color=COLORS["error"],
                )
                await self._finish_loss(ctx, "anagram", lose)
                return

            if normalize(msg.content) == normalize(answer):
                win = discord.Embed(
                    title="🔠 Anagramme — Trouvé !",
                    description=f"{ctx.author.mention} a démêlé **{answer}** ✅",
                    color=COLORS["success"],
                )
                await self._finish_win(ctx, "anagram", EXTRA_XP["anagram"], win)
            else:
                lose = discord.Embed(
                    title="🔠 Anagramme — Manqué",
                    description=f"La réponse était : **{answer}**",
                    color=COLORS["error"],
                )
                await self._finish_loss(ctx, "anagram", lose)
        finally:
            _clear_game_active(self, ctx.channel.id)

    # ═════════════════════════════════════════════════════════════════════════
    # 📖 GUESSMANGA (panel)
    # ═════════════════════════════════════════════════════════════════════════

    @commands.command(name="guessmanga", aliases=["panel"])
    @commands.cooldown(1, 15, commands.BucketType.user)
    async def guessmanga(self, ctx):
        """[Solo] Devine le manga à partir d'un panel/description."""
        if _is_game_active(self, ctx.channel.id):
            return await ctx.send("❌ Un jeu est déjà en cours dans ce channel !")
        if not await _consume_daily_slot(self, ctx, "guessmanga"):
            return
        _set_game_active(self, ctx.channel.id, "guessmanga", owner_id=ctx.author.id)
        try:
            panel = random.choice(PANELS)
            featured = is_featured("guessmanga")
            embed = discord.Embed(
                title="📖 Guess the Manga" + (" ⭐" if featured else ""),
                description=(
                    f"👤 {ctx.author.mention}\n\n"
                    f"🖼️ *{panel['caption']}*\n\n"
                    f"De quel manga vient ce panel ?\n"
                    f"⏱️ **30 secondes** pour répondre."
                ),
                color=COLORS["info"],
            )
            if panel.get("url"):
                embed.set_image(url=panel["url"])
            if featured:
                embed.set_footer(text="⭐ Jeu vedette du jour — XP doublée !")
            await ctx.send(embed=embed)

            def check(m):
                return m.channel.id == ctx.channel.id and m.author.id == ctx.author.id

            try:
                msg = await self.bot.wait_for("message", check=check, timeout=30)
            except asyncio.TimeoutError:
                lose = discord.Embed(
                    title="📖 Guess Manga — Temps écoulé !",
                    description=f"La réponse était : **{panel['answer']}**",
                    color=COLORS["error"],
                )
                await self._finish_loss(ctx, "guessmanga", lose)
                return

            if answer_match(msg.content, panel):
                win = discord.Embed(
                    title="📖 Guess Manga — Bien vu !",
                    description=f"{ctx.author.mention} a reconnu **{panel['answer']}** ✅",
                    color=COLORS["success"],
                )
                await self._finish_win(ctx, "guessmanga", EXTRA_XP["guessmanga"], win)
            else:
                lose = discord.Embed(
                    title="📖 Guess Manga — Manqué",
                    description=f"La réponse était : **{panel['answer']}**",
                    color=COLORS["error"],
                )
                await self._finish_loss(ctx, "guessmanga", lose)
        finally:
            _clear_game_active(self, ctx.channel.id)

    # ═════════════════════════════════════════════════════════════════════════
    # 🎵 OPENING / OST
    # ═════════════════════════════════════════════════════════════════════════

    @commands.command(name="opening", aliases=["ost"])
    @commands.cooldown(1, 15, commands.BucketType.user)
    async def opening(self, ctx):
        """[Solo] Devine l'anime à partir d'un opening."""
        if _is_game_active(self, ctx.channel.id):
            return await ctx.send("❌ Un jeu est déjà en cours dans ce channel !")
        if not await _consume_daily_slot(self, ctx, "opening"):
            return
        _set_game_active(self, ctx.channel.id, "opening", owner_id=ctx.author.id)
        try:
            opening = random.choice(OPENINGS)
            featured = is_featured("opening")
            embed = discord.Embed(
                title="🎵 Opening Quiz" + (" ⭐" if featured else ""),
                description=(
                    f"👤 {ctx.author.mention}\n\n"
                    f"🎶 **{opening['clip']}**\n\n"
                    f"De quel anime vient cet opening ?\n"
                    f"⏱️ **30 secondes** pour répondre."
                ),
                color=COLORS["info"],
            )
            if featured:
                embed.set_footer(text="⭐ Jeu vedette du jour — XP doublée !")
            await ctx.send(embed=embed)

            def check(m):
                return m.channel.id == ctx.channel.id and m.author.id == ctx.author.id

            try:
                msg = await self.bot.wait_for("message", check=check, timeout=30)
            except asyncio.TimeoutError:
                lose = discord.Embed(
                    title="🎵 Opening — Temps écoulé !",
                    description=f"C'était l'opening de **{opening['answer']}**",
                    color=COLORS["error"],
                )
                await self._finish_loss(ctx, "opening", lose)
                return

            if answer_match(msg.content, opening):
                win = discord.Embed(
                    title="🎵 Opening — Trouvé !",
                    description=f"{ctx.author.mention} a reconnu **{opening['answer']}** ✅",
                    color=COLORS["success"],
                )
                await self._finish_win(ctx, "opening", EXTRA_XP["opening"], win)
            else:
                lose = discord.Embed(
                    title="🎵 Opening — Manqué",
                    description=f"C'était **{opening['answer']}**",
                    color=COLORS["error"],
                )
                await self._finish_loss(ctx, "opening", lose)
        finally:
            _clear_game_active(self, ctx.channel.id)

    # ═════════════════════════════════════════════════════════════════════════
    # 🎭 CHARACTER (20 questions inversé)
    # ═════════════════════════════════════════════════════════════════════════

    @commands.command(name="character", aliases=["akinator", "twentyq"])
    @commands.cooldown(1, 30, commands.BucketType.user)
    async def character(self, ctx):
        """[Solo] Le bot pense à un personnage et tu poses des questions Oui/Non."""
        if _is_game_active(self, ctx.channel.id):
            return await ctx.send("❌ Un jeu est déjà en cours dans ce channel !")
        if not await _consume_daily_slot(self, ctx, "character"):
            return
        _set_game_active(self, ctx.channel.id, "character", owner_id=ctx.author.id)
        try:
            target = random.choice(CHARACTERS)
            candidates = list(CHARACTERS)
            asked = []
            max_questions = 10

            featured = is_featured("character")

            embed = discord.Embed(
                title="🎭 Akinator Manga" + (" ⭐" if featured else ""),
                description=(
                    f"Je pense à un personnage des mangas LanorTrad.\n"
                    f"Tu as **{max_questions} questions Oui/Non** pour le deviner.\n\n"
                    f"À chaque tour, je te propose une question, tu réponds **oui** ou **non**.\n"
                    f"Quand tu penses savoir, tape **`!guess <nom>`** pour deviner.\n"
                    f"Tape **`stop`** pour abandonner.\n\n"
                    f"⏱️ 60 secondes max par tour."
                ),
                color=COLORS["info"],
            )
            if featured:
                embed.set_footer(text="⭐ Jeu vedette du jour — XP doublée !")
            await ctx.send(embed=embed)

            available_qs = list(CHARACTER_QUESTIONS)
            for q_num in range(1, max_questions + 1):
                if not available_qs:
                    break
                question = random.choice(available_qs)
                available_qs.remove(question)
                asked.append(question)

                q_embed = discord.Embed(
                    title=f"🎭 Question {q_num}/{max_questions}",
                    description=f"❓ {question[0]}\n\n*Réponds par **oui** ou **non** (ou `!guess <nom>` pour deviner, `stop` pour abandonner)*",
                    color=COLORS["info"],
                )
                await ctx.send(embed=q_embed)

                def check(m):
                    if m.channel.id != ctx.channel.id or m.author.id != ctx.author.id:
                        return False
                    txt = normalize(m.content.strip())
                    return (
                        txt in ("oui", "o", "yes", "y", "non", "n", "no", "stop")
                        or txt.startswith("!guess ")
                    )

                try:
                    reply = await self.bot.wait_for("message", check=check, timeout=60)
                except asyncio.TimeoutError:
                    lose = discord.Embed(
                        title="🎭 Akinator — Temps écoulé",
                        description=f"Je pensais à : **{target['name']}** ({target['manga']})",
                        color=COLORS["error"],
                    )
                    await self._finish_loss(ctx, "character", lose)
                    return

                content = reply.content.strip()
                norm_c = normalize(content)

                if norm_c == "stop":
                    lose = discord.Embed(
                        title="🎭 Akinator — Abandon",
                        description=f"Je pensais à : **{target['name']}** ({target['manga']})",
                        color=COLORS["error"],
                    )
                    await self._finish_loss(ctx, "character", lose)
                    return

                if norm_c.startswith("!guess "):
                    guess_name = content[7:].strip()
                    if normalize(guess_name) == normalize(target["name"]) or normalize(guess_name) in normalize(target["name"]):
                        # Bonus pour avoir deviné en peu de questions
                        bonus = max(1, max_questions - q_num + 1)
                        base = EXTRA_XP["character"] + bonus * 2
                        win = discord.Embed(
                            title="🎭 Akinator — Tu as deviné !",
                            description=(
                                f"Bravo ! C'était bien **{target['name']}** ({target['manga']})\n"
                                f"🎯 Deviné en **{q_num}** question(s)"
                            ),
                            color=COLORS["success"],
                        )
                        await self._finish_win(ctx, "character", base, win)
                        return
                    else:
                        await ctx.send(f"❌ Non, ce n'est pas **{guess_name}**. Continue !")
                        continue

                # Réponse oui/non
                yes = norm_c in ("oui", "o", "yes", "y")
                actual = bool(target["tags"].get(question[1], False))
                truth = "Oui" if actual else "Non"
                user_said = "Oui" if yes else "Non"

                # Filtrer les candidats (juste à titre indicatif pour le joueur)
                candidates = [c for c in candidates if bool(c["tags"].get(question[1], False)) == actual]

                hint_embed = discord.Embed(
                    title=f"🎭 Réponse {q_num}/{max_questions}",
                    description=(
                        f"❓ {question[0]}\n"
                        f"➡️ Réalité : **{truth}**\n"
                        f"📊 Personnages encore possibles : **{len(candidates)}**"
                    ),
                    color=COLORS["info"],
                )
                if user_said != truth:
                    hint_embed.set_footer(text=f"⚠️ Tu pensais : {user_said}. Ça change ta théorie !")
                await ctx.send(embed=hint_embed)

            # 10 questions épuisées sans guess
            lose = discord.Embed(
                title="🎭 Akinator — Questions épuisées",
                description=f"Tu n'as pas deviné à temps. C'était : **{target['name']}** ({target['manga']})",
                color=COLORS["error"],
            )
            await self._finish_loss(ctx, "character", lose)
        finally:
            _clear_game_active(self, ctx.channel.id)

    # ═════════════════════════════════════════════════════════════════════════
    # ⚡ CLICK / FASTCLICK
    # ═════════════════════════════════════════════════════════════════════════

    @commands.command(name="click", aliases=["fastclick"])
    @commands.cooldown(1, 15, commands.BucketType.user)
    async def click(self, ctx):
        """[Solo] Clique sur les 5 boutons dans l'ordre le plus vite possible."""
        if _is_game_active(self, ctx.channel.id):
            return await ctx.send("❌ Un jeu est déjà en cours dans ce channel !")
        if not await _consume_daily_slot(self, ctx, "click"):
            return
        _set_game_active(self, ctx.channel.id, "click", owner_id=ctx.author.id)
        try:
            view = ClickView(ctx.author.id, total=5)
            featured = is_featured("click")

            embed = discord.Embed(
                title="⚡ Fast Click" + (" ⭐" if featured else ""),
                description=(
                    f"👤 {ctx.author.mention}\n\n"
                    f"Clique sur les boutons **dans l'ordre 1 → 2 → 3 → 4 → 5** !\n"
                    f"Une erreur = défaite. Chronomètre lancé au premier clic.\n"
                    f"⏱️ 20 secondes max."
                ),
                color=COLORS["info"],
            )
            if featured:
                embed.set_footer(text="⭐ Jeu vedette du jour — XP doublée !")

            view.message = await ctx.send(embed=embed, view=view)
            await view.wait()

            if view.failed:
                lose = discord.Embed(
                    title="⚡ Fast Click — Raté",
                    description=f"Tu as cliqué dans le mauvais ordre.",
                    color=COLORS["error"],
                )
                await self._finish_loss(ctx, "click", lose)
            elif view.completed:
                elapsed = view.end_time - view.start_time
                bonus = max(0, int((5.0 - elapsed) * 2))
                win = discord.Embed(
                    title="⚡ Fast Click — Réussi !",
                    description=f"⚡ Temps : **{elapsed:.2f}s** (+{bonus} XP bonus de vitesse)",
                    color=COLORS["success"],
                )
                await self._finish_win(ctx, "click", EXTRA_XP["click"] + bonus, win)
            else:
                lose = discord.Embed(
                    title="⚡ Fast Click — Temps écoulé",
                    description="Tu n'as pas terminé à temps.",
                    color=COLORS["error"],
                )
                await self._finish_loss(ctx, "click", lose)
        finally:
            _clear_game_active(self, ctx.channel.id)

    # ═════════════════════════════════════════════════════════════════════════
    # 🃏 MEMORY
    # ═════════════════════════════════════════════════════════════════════════

    @commands.command(name="memory")
    @commands.cooldown(1, 20, commands.BucketType.user)
    async def memory(self, ctx):
        """[Solo] Memory — retrouve les paires d'emojis cachés (grille 4x4)."""
        if _is_game_active(self, ctx.channel.id):
            return await ctx.send("❌ Un jeu est déjà en cours dans ce channel !")
        if not await _consume_daily_slot(self, ctx, "memory"):
            return
        _set_game_active(self, ctx.channel.id, "memory", owner_id=ctx.author.id)
        try:
            view = MemoryView(ctx.author.id)
            featured = is_featured("memory")

            embed = discord.Embed(
                title="🃏 Memory" + (" ⭐" if featured else ""),
                description=(
                    f"👤 {ctx.author.mention}\n\n"
                    f"Trouve les **8 paires** d'emojis cachées dans la grille.\n"
                    f"Clique sur 2 cartes : si elles correspondent, elles restent visibles.\n"
                    f"⏱️ 3 minutes max."
                ),
                color=COLORS["info"],
            )
            if featured:
                embed.set_footer(text="⭐ Jeu vedette du jour — XP doublée !")

            view.message = await ctx.send(embed=embed, view=view)
            await view.wait()

            if view.completed:
                elapsed = view.end_time - view.start_time
                # Bonus d'XP en fonction du temps et des essais
                speed_bonus = max(0, int((120 - elapsed) * 0.15))
                tries_penalty = max(0, view.tries - 12)
                bonus = max(0, speed_bonus - tries_penalty * 1)
                win = discord.Embed(
                    title="🃏 Memory — Toutes les paires trouvées !",
                    description=(
                        f"⚡ Temps : **{elapsed:.0f}s**\n"
                        f"🎯 Essais : **{view.tries}**\n"
                        f"💎 Bonus de performance : **+{bonus} XP**"
                    ),
                    color=COLORS["success"],
                )
                await self._finish_win(ctx, "memory", EXTRA_XP["memory"] + bonus, win)
            else:
                lose = discord.Embed(
                    title="🃏 Memory — Temps écoulé",
                    description=f"Paires trouvées : **{view.pairs_found}/8**",
                    color=COLORS["error"],
                )
                await self._finish_loss(ctx, "memory", lose)
        finally:
            _clear_game_active(self, ctx.channel.id)

    # ═════════════════════════════════════════════════════════════════════════
    # ❌⭕ TIC-TAC-TOE
    # ═════════════════════════════════════════════════════════════════════════

    @commands.command(name="ttt", aliases=["tictactoe", "morpion"])
    @commands.cooldown(1, 30, commands.BucketType.user)
    async def ttt(self, ctx, adversaire: discord.Member = None):
        """Morpion 1v1 — `!ttt @adversaire`. L'adversaire valide via bouton."""
        if adversaire is None:
            return await ctx.send("❌ Usage : `!ttt @adversaire`")
        if adversaire.bot or adversaire.id == ctx.author.id:
            return await ctx.send("❌ Tu ne peux pas jouer contre toi-même ou un bot.")

        if not await _consume_daily_slot(self, ctx, "ttt"):
            return

        # Invitation par bouton
        accepted = await self._invite(ctx, adversaire, game_label="Morpion")
        if not accepted:
            return

        view = TTTView(ctx.author.id, adversaire.id)
        view.message = await ctx.send(
            content=f"{ctx.author.mention} ❌ vs ⭕ {adversaire.mention} — c'est à **{ctx.author.display_name}** de jouer.",
            view=view,
        )
        await view.wait()

        if view.winner_id:
            winner = ctx.guild.get_member(view.winner_id)
            win = discord.Embed(
                title="❌⭕ Morpion — Victoire !",
                description=f"{winner.mention if winner else 'Inconnu'} remporte la partie !",
                color=COLORS["success"],
            )
            await self._finish_win(ctx if winner == ctx.author else type("X", (), {"author": winner, "channel": ctx.channel, "guild": ctx.guild, "send": ctx.send})(), "ttt", EXTRA_XP["ttt"], win)
        elif view.draw:
            await ctx.send(embed=discord.Embed(
                title="❌⭕ Morpion — Égalité",
                description="Personne ne gagne, personne ne perd.",
                color=COLORS["warning"],
            ))
        else:
            await ctx.send(embed=discord.Embed(
                title="❌⭕ Morpion — Abandon / timeout",
                description="La partie a été abandonnée.",
                color=COLORS["error"],
            ))

    # ═════════════════════════════════════════════════════════════════════════
    # 🟡🔴 CONNECT 4
    # ═════════════════════════════════════════════════════════════════════════

    @commands.command(name="connect4", aliases=["c4", "puissance4"])
    @commands.cooldown(1, 30, commands.BucketType.user)
    async def connect4(self, ctx, adversaire: discord.Member = None):
        """Puissance 4 — `!connect4 @adversaire`."""
        if adversaire is None:
            return await ctx.send("❌ Usage : `!connect4 @adversaire`")
        if adversaire.bot or adversaire.id == ctx.author.id:
            return await ctx.send("❌ Tu ne peux pas jouer contre toi-même ou un bot.")

        if not await _consume_daily_slot(self, ctx, "connect4"):
            return

        accepted = await self._invite(ctx, adversaire, game_label="Puissance 4")
        if not accepted:
            return

        view = Connect4View(ctx.author.id, adversaire.id)
        view.message = await ctx.send(
            content=f"{ctx.author.mention} 🟡 vs 🔴 {adversaire.mention}",
            embed=view.render_embed(),
            view=view,
        )
        await view.wait()

        if view.winner_id:
            winner = ctx.guild.get_member(view.winner_id)
            win = discord.Embed(
                title="🟡🔴 Puissance 4 — Victoire !",
                description=f"{winner.mention if winner else 'Inconnu'} aligne 4 jetons !",
                color=COLORS["success"],
            )
            fake_ctx = type("Ctx", (), {
                "author": winner,
                "channel": ctx.channel,
                "guild": ctx.guild,
                "send": ctx.send,
            })()
            await self._finish_win(fake_ctx, "connect4", EXTRA_XP["connect4"], win)
        elif view.draw:
            await ctx.send(embed=discord.Embed(
                title="🟡🔴 Puissance 4 — Grille pleine, égalité",
                color=COLORS["warning"],
            ))
        else:
            await ctx.send(embed=discord.Embed(
                title="🟡🔴 Puissance 4 — Partie interrompue",
                color=COLORS["error"],
            ))

    # ═════════════════════════════════════════════════════════════════════════
    # ⭐ FEATURED INFO
    # ═════════════════════════════════════════════════════════════════════════

    @commands.command(name="featured", aliases=["jeuvedette"])
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def featured_cmd(self, ctx):
        """Affiche le mini-jeu vedette du jour (XP doublée)."""
        from effects import get_featured_game, FEATURED_MULTIPLIER
        feat = get_featured_game()
        embed = discord.Embed(
            title="⭐ Jeu Vedette du Jour",
            description=(
                f"Le jeu vedette d'aujourd'hui est : **`!{feat}`**\n\n"
                f"💎 Joue à ce mini-jeu et gagne **x{FEATURED_MULTIPLIER:.0f}** d'XP "
                f"sur tes victoires !\n\n"
                f"*Le jeu vedette change chaque jour à minuit.*"
            ),
            color=COLORS["info"],
        )
        await ctx.send(embed=embed)

    # ═════════════════════════════════════════════════════════════════════════
    # 🔥 STREAK INFO
    # ═════════════════════════════════════════════════════════════════════════

    @commands.command(name="streak", aliases=["combo"])
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def streak_cmd(self, ctx, member: discord.Member = None):
        """Affiche le streak (combo de victoires) d'un joueur."""
        from effects import get_streak, get_streak_multiplier, STREAK_TIERS
        target = member or ctx.author
        s = get_streak(target.id)

        embed = discord.Embed(
            title=f"🔥 Streak — {target.display_name}",
            color=COLORS["info"],
        )
        embed.add_field(name="🔥 Combo actuel", value=f"**{s.get('count', 0)}**", inline=True)
        embed.add_field(name="🏆 Record", value=f"**{s.get('best', 0)}**", inline=True)
        embed.add_field(name="📈 Multiplicateur", value=f"**x{get_streak_multiplier(s.get('count', 0)):.1f}**", inline=True)

        tiers_text = "\n".join([f"• {n}+ wins → **x{m:.1f}**" for n, m in reversed(STREAK_TIERS)])
        embed.add_field(name="📊 Paliers", value=tiers_text, inline=False)

        if s.get("shielded"):
            embed.add_field(name="🛡️ Bouclier", value="Actif — protège ton prochain échec", inline=False)

        embed.set_footer(text="Le streak monte à chaque victoire en mini-jeu et casse à la défaite (sauf bouclier).")
        await ctx.send(embed=embed)

    # ═════════════════════════════════════════════════════════════════════════
    # 🛠️ INVITATION HELPER
    # ═════════════════════════════════════════════════════════════════════════

    async def _invite(self, ctx, target, game_label="Partie"):
        """Affiche une invitation à boutons et retourne True si acceptée."""
        view = InvitationView(target.id, timeout=60)
        embed = discord.Embed(
            title=f"🎮 Invitation — {game_label}",
            description=(
                f"{ctx.author.mention} défie {target.mention} à une partie de **{game_label}** !\n"
                f"⏱️ 60 secondes pour répondre."
            ),
            color=COLORS["warning"],
        )
        view.message = await ctx.send(content=target.mention, embed=embed, view=view)
        await view.wait()

        if view.accepted is True:
            return True
        elif view.accepted is False:
            await ctx.send(f"❌ {target.display_name} a refusé l'invitation.")
            return False
        else:
            await ctx.send(f"⌛ {target.display_name} n'a pas répondu à temps.")
            return False


# ═══════════════════════════════════════════════════════════════════════════════
# CLICK VIEW
# ═══════════════════════════════════════════════════════════════════════════════

class ClickView(View):
    def __init__(self, owner_id, total=5):
        super().__init__(timeout=20)
        self.owner_id = owner_id
        self.total = total
        self.expected = 1
        self.failed = False
        self.completed = False
        self.start_time = None
        self.end_time = None
        self.message = None

        # Mélanger les positions des boutons
        order = list(range(1, total + 1))
        random.shuffle(order)
        for n in order:
            self.add_item(ClickButton(label=str(n), number=n))

    async def on_timeout(self):
        if not self.completed and not self.failed:
            for c in self.children:
                c.disabled = True
            try:
                await self.message.edit(view=self)
            except Exception:
                pass


class ClickButton(Button):
    def __init__(self, label, number):
        super().__init__(label=label, style=discord.ButtonStyle.primary)
        self.number = number

    async def callback(self, interaction: discord.Interaction):
        view: ClickView = self.view  # type: ignore
        if interaction.user.id != view.owner_id:
            await interaction.response.send_message("❌ Ce n'est pas ta partie.", ephemeral=True)
            return
        if view.failed or view.completed:
            await interaction.response.defer()
            return

        if view.start_time is None:
            view.start_time = time.time()

        if self.number != view.expected:
            view.failed = True
            self.style = discord.ButtonStyle.danger
            for c in view.children:
                c.disabled = True
            await interaction.response.edit_message(view=view)
            view.stop()
            return

        self.style = discord.ButtonStyle.success
        self.disabled = True
        view.expected += 1

        if view.expected > view.total:
            view.completed = True
            view.end_time = time.time()
            for c in view.children:
                c.disabled = True
            await interaction.response.edit_message(view=view)
            view.stop()
        else:
            await interaction.response.edit_message(view=view)


# ═══════════════════════════════════════════════════════════════════════════════
# MEMORY VIEW
# ═══════════════════════════════════════════════════════════════════════════════

class MemoryView(View):
    def __init__(self, owner_id):
        super().__init__(timeout=180)
        self.owner_id = owner_id
        self.cards = (MEMORY_EMOJIS * 2)[:16]
        random.shuffle(self.cards)
        self.revealed = [False] * 16
        self.first_pick = None
        self.tries = 0
        self.pairs_found = 0
        self.completed = False
        self.start_time = time.time()
        self.end_time = None
        self.message = None
        self.locked = False

        for i in range(16):
            self.add_item(MemoryButton(index=i, row=i // 4))

    async def on_timeout(self):
        if not self.completed:
            for c in self.children:
                c.disabled = True
            try:
                await self.message.edit(view=self)
            except Exception:
                pass


class MemoryButton(Button):
    def __init__(self, index, row):
        super().__init__(label="❔", style=discord.ButtonStyle.secondary, row=row)
        self.index = index

    async def callback(self, interaction: discord.Interaction):
        view: MemoryView = self.view  # type: ignore
        if interaction.user.id != view.owner_id:
            await interaction.response.send_message("❌ Ce n'est pas ta partie.", ephemeral=True)
            return
        if view.locked or view.revealed[self.index] or view.completed:
            await interaction.response.defer()
            return

        # Révéler la carte
        view.revealed[self.index] = True
        self.label = view.cards[self.index]
        self.style = discord.ButtonStyle.primary

        if view.first_pick is None:
            view.first_pick = self.index
            await interaction.response.edit_message(view=view)
            return

        # Deuxième carte
        view.tries += 1
        first = view.first_pick
        view.first_pick = None

        if view.cards[first] == view.cards[self.index]:
            # Paire trouvée
            for c in view.children:
                if isinstance(c, MemoryButton) and c.index in (first, self.index):
                    c.style = discord.ButtonStyle.success
                    c.disabled = True
            view.pairs_found += 1

            if view.pairs_found >= 8:
                view.completed = True
                view.end_time = time.time()
                view.stop()

            await interaction.response.edit_message(view=view)
        else:
            # Pas de match — re-cacher après 1.2s
            view.locked = True
            await interaction.response.edit_message(view=view)
            await asyncio.sleep(1.2)
            for c in view.children:
                if isinstance(c, MemoryButton) and c.index in (first, self.index):
                    c.label = "❔"
                    c.style = discord.ButtonStyle.secondary
            view.revealed[first] = False
            view.revealed[self.index] = False
            view.locked = False
            try:
                await view.message.edit(view=view)
            except Exception:
                pass


# ═══════════════════════════════════════════════════════════════════════════════
# TIC-TAC-TOE VIEW
# ═══════════════════════════════════════════════════════════════════════════════

class TTTView(View):
    def __init__(self, p1_id, p2_id):
        super().__init__(timeout=180)
        self.p1_id = p1_id  # ❌
        self.p2_id = p2_id  # ⭕
        self.board = [None] * 9
        self.current = p1_id
        self.winner_id = None
        self.draw = False
        self.message = None

        for i in range(9):
            self.add_item(TTTButton(index=i, row=i // 3))

    def _check_winner(self):
        lines = [
            (0, 1, 2), (3, 4, 5), (6, 7, 8),
            (0, 3, 6), (1, 4, 7), (2, 5, 8),
            (0, 4, 8), (2, 4, 6),
        ]
        for a, b, c in lines:
            if self.board[a] and self.board[a] == self.board[b] == self.board[c]:
                return self.board[a]
        return None

    async def on_timeout(self):
        if self.winner_id is None and not self.draw:
            for c in self.children:
                c.disabled = True
            try:
                await self.message.edit(view=self)
            except Exception:
                pass


class TTTButton(Button):
    def __init__(self, index, row):
        super().__init__(label="\u200b", style=discord.ButtonStyle.secondary, row=row)
        self.index = index

    async def callback(self, interaction: discord.Interaction):
        view: TTTView = self.view  # type: ignore
        if interaction.user.id != view.current:
            await interaction.response.send_message("❌ Ce n'est pas ton tour.", ephemeral=True)
            return
        if view.board[self.index] is not None:
            await interaction.response.defer()
            return

        symbol = "❌" if view.current == view.p1_id else "⭕"
        view.board[self.index] = symbol
        self.label = symbol
        self.style = discord.ButtonStyle.danger if symbol == "❌" else discord.ButtonStyle.primary
        self.disabled = True

        winner = view._check_winner()
        if winner:
            view.winner_id = view.current
            for c in view.children:
                c.disabled = True
            await interaction.response.edit_message(content=f"🏆 **{symbol}** remporte la partie !", view=view)
            view.stop()
            return

        if all(cell is not None for cell in view.board):
            view.draw = True
            for c in view.children:
                c.disabled = True
            await interaction.response.edit_message(content="🤝 Égalité !", view=view)
            view.stop()
            return

        view.current = view.p2_id if view.current == view.p1_id else view.p1_id
        next_symbol = "❌" if view.current == view.p1_id else "⭕"
        await interaction.response.edit_message(
            content=f"À <@{view.current}> de jouer ({next_symbol})",
            view=view,
        )


# ═══════════════════════════════════════════════════════════════════════════════
# CONNECT 4 VIEW (7 colonnes × 6 lignes)
# ═══════════════════════════════════════════════════════════════════════════════

C4_COLS = 7
C4_ROWS = 6


class Connect4View(View):
    def __init__(self, p1_id, p2_id):
        super().__init__(timeout=300)
        self.p1_id = p1_id  # 🟡
        self.p2_id = p2_id  # 🔴
        self.board = [[None] * C4_COLS for _ in range(C4_ROWS)]
        self.current = p1_id
        self.winner_id = None
        self.draw = False
        self.message = None

        for col in range(C4_COLS):
            self.add_item(C4Button(column=col))

    def render_embed(self):
        rows = []
        for r in range(C4_ROWS):
            line = ""
            for c in range(C4_COLS):
                cell = self.board[r][c]
                if cell == "p1":
                    line += "🟡"
                elif cell == "p2":
                    line += "🔴"
                else:
                    line += "⚫"
            rows.append(line)
        rows.append("1️⃣2️⃣3️⃣4️⃣5️⃣6️⃣7️⃣")
        symbol = "🟡" if self.current == self.p1_id else "🔴"
        embed = discord.Embed(
            title="🟡🔴 Puissance 4",
            description="\n".join(rows) + f"\n\nÀ <@{self.current}> de jouer ({symbol})",
            color=COLORS["info"],
        )
        return embed

    def _drop(self, col):
        for r in range(C4_ROWS - 1, -1, -1):
            if self.board[r][col] is None:
                key = "p1" if self.current == self.p1_id else "p2"
                self.board[r][col] = key
                return r
        return None

    def _check_winner(self):
        for r in range(C4_ROWS):
            for c in range(C4_COLS):
                cell = self.board[r][c]
                if cell is None:
                    continue
                # Horizontal
                if c + 3 < C4_COLS and all(self.board[r][c + i] == cell for i in range(4)):
                    return cell
                # Vertical
                if r + 3 < C4_ROWS and all(self.board[r + i][c] == cell for i in range(4)):
                    return cell
                # Diag ↘
                if r + 3 < C4_ROWS and c + 3 < C4_COLS and all(self.board[r + i][c + i] == cell for i in range(4)):
                    return cell
                # Diag ↗
                if r - 3 >= 0 and c + 3 < C4_COLS and all(self.board[r - i][c + i] == cell for i in range(4)):
                    return cell
        return None

    async def on_timeout(self):
        if self.winner_id is None and not self.draw:
            for c in self.children:
                c.disabled = True
            try:
                await self.message.edit(view=self)
            except Exception:
                pass


class C4Button(Button):
    def __init__(self, column):
        super().__init__(label=str(column + 1), style=discord.ButtonStyle.secondary, row=column // 4)
        self.column = column

    async def callback(self, interaction: discord.Interaction):
        view: Connect4View = self.view  # type: ignore
        if interaction.user.id != view.current:
            await interaction.response.send_message("❌ Ce n'est pas ton tour.", ephemeral=True)
            return

        row = view._drop(self.column)
        if row is None:
            await interaction.response.send_message("❌ Cette colonne est pleine.", ephemeral=True)
            return

        winner_key = view._check_winner()
        if winner_key:
            view.winner_id = view.p1_id if winner_key == "p1" else view.p2_id
            for c in view.children:
                c.disabled = True
            await interaction.response.edit_message(embed=view.render_embed(), view=view)
            view.stop()
            return

        if all(view.board[0][c] is not None for c in range(C4_COLS)):
            view.draw = True
            for c in view.children:
                c.disabled = True
            await interaction.response.edit_message(embed=view.render_embed(), view=view)
            view.stop()
            return

        view.current = view.p2_id if view.current == view.p1_id else view.p1_id
        await interaction.response.edit_message(embed=view.render_embed(), view=view)


# ═══════════════════════════════════════════════════════════════════════════════
# SETUP
# ═══════════════════════════════════════════════════════════════════════════════

async def setup(bot):
    await bot.add_cog(MiniGamesExtra(bot))