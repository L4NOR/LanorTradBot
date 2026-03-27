# polls.py
# ═══════════════════════════════════════════════════════════════════════════════
# SYSTÈME DE SONDAGES AVANCÉ - Avec boutons, durée, résultats live
# ═══════════════════════════════════════════════════════════════════════════════

import discord
from discord.ext import commands, tasks
from discord.ui import View, Button
import datetime
import logging
import asyncio

from config import ADMIN_ROLES, COLORS, DATA_FILES
from utils import load_json, save_json, paginate

logger = logging.getLogger(__name__)

# Fichiers de données
POLLS_FILE = DATA_FILES.get("polls", "data/polls.json")

# Stockage en mémoire
active_polls = {}

# Emojis numérotés pour les options
OPTION_EMOJIS = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
BAR_FILLED = "🟩"
BAR_EMPTY = "⬜"


def charger_polls():
    """Charge les sondages depuis le fichier."""
    global active_polls
    active_polls = load_json(POLLS_FILE, {})
    logger.info(f"📊 {len(active_polls)} sondage(s) chargé(s)")


def sauvegarder_polls():
    """Sauvegarde les sondages."""
    save_json(POLLS_FILE, active_polls)


def generate_poll_bar(votes, total, size=10):
    """Génère une barre de progression pour un sondage."""
    if total <= 0:
        return BAR_EMPTY * size + " 0%"
    pct = votes / total
    filled = int(size * pct)
    return BAR_FILLED * filled + BAR_EMPTY * (size - filled) + f" {int(pct * 100)}%"


def build_poll_embed(poll_data):
    """Construit l'embed d'un sondage avec résultats live."""
    total_votes = sum(len(v) for v in poll_data["votes"].values())

    # Couleur selon état
    if poll_data.get("closed", False):
        color = COLORS["error"]
        status = "🔒 TERMINÉ"
    else:
        color = COLORS["info"]
        status = "🟢 EN COURS"

    embed = discord.Embed(
        title=f"📊 {poll_data['question']}",
        color=color,
        timestamp=datetime.datetime.fromisoformat(poll_data["created_at"])
    )

    # Options avec barres
    for i, option in enumerate(poll_data["options"]):
        option_key = str(i)
        vote_count = len(poll_data["votes"].get(option_key, []))
        bar = generate_poll_bar(vote_count, total_votes)
        emoji = OPTION_EMOJIS[i] if i < len(OPTION_EMOJIS) else f"**{i+1}.**"
        embed.add_field(
            name=f"{emoji} {option}",
            value=f"{bar} ({vote_count} vote{'s' if vote_count > 1 else ''})",
            inline=False
        )

    # Infos
    embed.add_field(
        name="📈 Infos",
        value=(
            f"**{total_votes}** vote(s) au total\n"
            f"🏷️ Status: {status}\n"
            f"👤 Créé par: <@{poll_data['author_id']}>"
        ),
        inline=False
    )

    # Durée si applicable
    if poll_data.get("ends_at"):
        ends_at = datetime.datetime.fromisoformat(poll_data["ends_at"])
        if not poll_data.get("closed", False):
            embed.add_field(
                name="⏰ Fin",
                value=f"<t:{int(ends_at.timestamp())}:R>",
                inline=True
            )

    # Multi-vote ?
    if poll_data.get("multi_vote", False):
        embed.add_field(name="🔄 Multi-vote", value="Activé", inline=True)

    # Anonyme ?
    if poll_data.get("anonymous", False):
        embed.add_field(name="🕶️ Anonyme", value="Oui", inline=True)

    embed.set_footer(text=f"ID: {poll_data['id']} • Sondage LanorTrad")
    return embed


class PollVoteButton(Button):
    """Bouton pour voter dans un sondage."""

    def __init__(self, poll_id: str, option_index: int, option_label: str):
        emoji = OPTION_EMOJIS[option_index] if option_index < len(OPTION_EMOJIS) else None
        label = option_label[:40]
        super().__init__(
            style=discord.ButtonStyle.primary,
            label=label,
            emoji=emoji,
            custom_id=f"poll_{poll_id}_{option_index}"
        )
        self.poll_id = poll_id
        self.option_index = option_index

    async def callback(self, interaction: discord.Interaction):
        poll = active_polls.get(self.poll_id)
        if not poll:
            await interaction.response.send_message("❌ Ce sondage n'existe plus.", ephemeral=True)
            return

        if poll.get("closed", False):
            await interaction.response.send_message("🔒 Ce sondage est terminé.", ephemeral=True)
            return

        user_id = str(interaction.user.id)
        option_key = str(self.option_index)
        multi_vote = poll.get("multi_vote", False)

        # Vérifier si déjà voté pour cette option
        voters = poll["votes"].get(option_key, [])
        if user_id in voters:
            # Retirer le vote
            voters.remove(user_id)
            poll["votes"][option_key] = voters
            sauvegarder_polls()

            embed = build_poll_embed(poll)
            await interaction.response.edit_message(embed=embed)
            await interaction.followup.send(
                f"🔄 Vote retiré pour **{poll['options'][self.option_index]}**",
                ephemeral=True
            )
            return

        # Si pas multi-vote, retirer le vote précédent
        if not multi_vote:
            for key, voter_list in poll["votes"].items():
                if user_id in voter_list:
                    voter_list.remove(user_id)

        # Ajouter le vote
        if option_key not in poll["votes"]:
            poll["votes"][option_key] = []
        poll["votes"][option_key].append(user_id)
        sauvegarder_polls()

        # Mettre à jour l'embed
        embed = build_poll_embed(poll)
        await interaction.response.edit_message(embed=embed)
        await interaction.followup.send(
            f"✅ Voté pour **{poll['options'][self.option_index]}**",
            ephemeral=True
        )


class PollView(View):
    """Vue avec boutons de vote pour un sondage."""

    def __init__(self, poll_id: str, options: list):
        super().__init__(timeout=None)
        for i, option in enumerate(options):
            if i >= 10:
                break
            self.add_item(PollVoteButton(poll_id, i, option))


class PollSystem(commands.Cog):
    """Système de sondages avancé avec boutons interactifs."""

    def __init__(self, bot):
        self.bot = bot
        charger_polls()
        # Restaurer les views persistantes
        for poll_id, poll_data in active_polls.items():
            if not poll_data.get("closed", False):
                view = PollView(poll_id, poll_data["options"])
                bot.add_view(view)
        self.poll_expiry_loop.start()

    def cog_unload(self):
        self.poll_expiry_loop.cancel()
        sauvegarder_polls()

    # ─────────────────────────────────────────────────────────────────────────
    # LOOP - EXPIRATION DES SONDAGES
    # ─────────────────────────────────────────────────────────────────────────

    @tasks.loop(minutes=1)
    async def poll_expiry_loop(self):
        """Vérifie et ferme les sondages expirés."""
        now = datetime.datetime.now(datetime.timezone.utc)
        for poll_id, poll_data in list(active_polls.items()):
            if poll_data.get("closed", False):
                continue
            if not poll_data.get("ends_at"):
                continue

            ends_at = datetime.datetime.fromisoformat(poll_data["ends_at"])
            if now >= ends_at:
                poll_data["closed"] = True
                sauvegarder_polls()

                # Mettre à jour le message
                try:
                    channel = self.bot.get_channel(poll_data["channel_id"])
                    if channel:
                        msg = await channel.fetch_message(poll_data["message_id"])
                        embed = build_poll_embed(poll_data)
                        # Désactiver les boutons
                        view = View()
                        await msg.edit(embed=embed, view=view)

                        # Annoncer la fin
                        total_votes = sum(len(v) for v in poll_data["votes"].values())
                        if total_votes > 0:
                            # Trouver le gagnant
                            winner_idx = max(poll_data["votes"], key=lambda k: len(poll_data["votes"][k]))
                            winner_option = poll_data["options"][int(winner_idx)]
                            winner_votes = len(poll_data["votes"][winner_idx])

                            result_embed = discord.Embed(
                                title="📊 Sondage terminé !",
                                description=(
                                    f"**{poll_data['question']}**\n\n"
                                    f"🏆 **Gagnant:** {winner_option}\n"
                                    f"📈 Avec **{winner_votes}** vote(s) sur **{total_votes}**"
                                ),
                                color=COLORS["success"]
                            )
                            result_embed.set_footer(text=f"ID: {poll_id}")
                            await channel.send(embed=result_embed)
                    await asyncio.sleep(2)
                except Exception as e:
                    logger.error(f"Erreur fermeture poll {poll_id}: {e}")

    @poll_expiry_loop.before_loop
    async def before_poll_expiry(self):
        await self.bot.wait_until_ready()

    # ─────────────────────────────────────────────────────────────────────────
    # COMMANDE PRINCIPALE - !poll
    # ─────────────────────────────────────────────────────────────────────────

    @commands.command(name="poll")
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def create_poll(self, ctx, *, args: str = None):
        """
        Crée un sondage interactif avec boutons.

        Usage rapide: !poll Question ? | Option 1 | Option 2 | Option 3
        Usage interactif: !poll (sans arguments, mode guidé)
        Options: ajouter --durée 1h ou --multi pour multi-vote, --anon pour anonyme
        """
        if args:
            await self._create_poll_quick(ctx, args)
        else:
            await self._create_poll_interactive(ctx)

    async def _create_poll_quick(self, ctx, args: str):
        """Création rapide de sondage en une ligne."""
        # Parser les flags
        multi_vote = "--multi" in args
        anonymous = "--anon" in args
        duration = None

        # Extraire --durée
        import re
        duration_match = re.search(r'--dur[ée]e?\s+(\S+)', args)
        if duration_match:
            from utils import parse_duration
            duration = parse_duration(duration_match.group(1))
            args = args[:duration_match.start()] + args[duration_match.end():]

        # Nettoyer les flags
        args = args.replace("--multi", "").replace("--anon", "").strip()

        # Séparer question et options
        parts = [p.strip() for p in args.split("|")]
        if len(parts) < 3:
            await ctx.send(
                "❌ Format: `!poll Question ? | Option 1 | Option 2`\n"
                "Flags: `--durée 1h` `--multi` `--anon`",
                delete_after=15
            )
            return

        question = parts[0]
        options = parts[1:]

        if len(options) > 10:
            await ctx.send("❌ Maximum 10 options.", delete_after=10)
            return

        await self._finalize_poll(ctx, question, options, duration, multi_vote, anonymous)

    async def _create_poll_interactive(self, ctx):
        """Création interactive de sondage étape par étape."""
        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel

        try:
            # Question
            embed = discord.Embed(
                title="📊 Création de sondage",
                description="Quelle est la **question** du sondage ?",
                color=COLORS["info"]
            )
            await ctx.send(embed=embed)
            msg = await self.bot.wait_for('message', check=check, timeout=60)
            question = msg.content.strip()

            # Options
            embed = discord.Embed(
                title="📊 Options",
                description=(
                    "Listez les options, une par ligne.\n"
                    "Envoyez `fin` quand vous avez terminé.\n"
                    "Minimum 2, maximum 10."
                ),
                color=COLORS["info"]
            )
            await ctx.send(embed=embed)

            options = []
            while len(options) < 10:
                msg = await self.bot.wait_for('message', check=check, timeout=60)
                if msg.content.lower().strip() == "fin":
                    if len(options) < 2:
                        await ctx.send("❌ Il faut au moins 2 options.")
                        continue
                    break
                options.append(msg.content.strip()[:100])
                await msg.add_reaction("✅")

            # Durée
            embed = discord.Embed(
                title="📊 Durée",
                description=(
                    "Durée du sondage ? (ex: `1h`, `30m`, `1d`, `2h30m`)\n"
                    "Tapez `non` pour un sondage sans limite."
                ),
                color=COLORS["info"]
            )
            await ctx.send(embed=embed)
            msg = await self.bot.wait_for('message', check=check, timeout=60)

            duration = None
            if msg.content.lower().strip() != "non":
                from utils import parse_duration
                duration = parse_duration(msg.content.strip())
                if not duration:
                    await ctx.send("⚠️ Durée non reconnue, sondage sans limite de temps.")

            # Multi-vote
            embed = discord.Embed(
                title="📊 Multi-vote",
                description="Autoriser le vote sur plusieurs options ? (`oui` / `non`)",
                color=COLORS["info"]
            )
            await ctx.send(embed=embed)
            msg = await self.bot.wait_for('message', check=check, timeout=30)
            multi_vote = msg.content.lower().strip() in ["oui", "yes", "o", "y"]

            await self._finalize_poll(ctx, question, options, duration, multi_vote, False)

        except asyncio.TimeoutError:
            await ctx.send("⏰ Temps écoulé. Sondage annulé.", delete_after=10)

    async def _finalize_poll(self, ctx, question, options, duration, multi_vote, anonymous):
        """Finalise et envoie le sondage."""
        now = datetime.datetime.now(datetime.timezone.utc)
        poll_id = f"poll_{int(now.timestamp())}"

        ends_at = None
        if duration:
            ends_at = (now + duration).isoformat()

        poll_data = {
            "id": poll_id,
            "question": question,
            "options": options,
            "votes": {str(i): [] for i in range(len(options))},
            "author_id": ctx.author.id,
            "channel_id": ctx.channel.id,
            "message_id": None,
            "created_at": now.isoformat(),
            "ends_at": ends_at,
            "multi_vote": multi_vote,
            "anonymous": anonymous,
            "closed": False,
        }

        embed = build_poll_embed(poll_data)
        view = PollView(poll_id, options)

        msg = await ctx.send(embed=embed, view=view)
        poll_data["message_id"] = msg.id

        active_polls[poll_id] = poll_data
        sauvegarder_polls()

        # Supprimer le message de la commande si possible
        try:
            await ctx.message.delete()
        except:
            pass

    # ─────────────────────────────────────────────────────────────────────────
    # COMMANDES DE GESTION
    # ─────────────────────────────────────────────────────────────────────────

    @commands.command(name="poll_close", aliases=["close_poll", "endpoll"])
    @commands.has_any_role(*ADMIN_ROLES)
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def close_poll(self, ctx, poll_id: str):
        """Ferme un sondage manuellement."""
        poll = active_polls.get(poll_id)
        if not poll:
            await ctx.send("❌ Sondage introuvable.", delete_after=10)
            return

        if poll.get("closed"):
            await ctx.send("⚠️ Ce sondage est déjà fermé.", delete_after=10)
            return

        poll["closed"] = True
        sauvegarder_polls()

        # Mettre à jour le message original
        try:
            channel = self.bot.get_channel(poll["channel_id"])
            if channel:
                msg = await channel.fetch_message(poll["message_id"])
                embed = build_poll_embed(poll)
                await msg.edit(embed=embed, view=View())
        except:
            pass

        # Résultats
        total_votes = sum(len(v) for v in poll["votes"].values())
        embed = discord.Embed(
            title="🔒 Sondage fermé",
            description=f"**{poll['question']}**\n\n{total_votes} vote(s) enregistré(s)",
            color=COLORS["success"]
        )

        if total_votes > 0:
            winner_idx = max(poll["votes"], key=lambda k: len(poll["votes"][k]))
            winner = poll["options"][int(winner_idx)]
            winner_votes = len(poll["votes"][winner_idx])
            embed.add_field(
                name="🏆 Résultat",
                value=f"**{winner}** avec {winner_votes} vote(s) ({int(winner_votes/total_votes*100)}%)"
            )

        await ctx.send(embed=embed)

    @commands.command(name="poll_delete", aliases=["delete_poll"])
    @commands.has_any_role(*ADMIN_ROLES)
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def delete_poll(self, ctx, poll_id: str):
        """Supprime un sondage."""
        if poll_id in active_polls:
            poll = active_polls.pop(poll_id)
            sauvegarder_polls()

            # Supprimer le message
            try:
                channel = self.bot.get_channel(poll["channel_id"])
                if channel:
                    msg = await channel.fetch_message(poll["message_id"])
                    await msg.delete()
            except:
                pass

            await ctx.send(f"✅ Sondage `{poll_id}` supprimé.", delete_after=10)
        else:
            await ctx.send("❌ Sondage introuvable.", delete_after=10)

    @commands.command(name="poll_list", aliases=["polls", "list_polls"])
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def list_polls(self, ctx):
        """Liste les sondages actifs."""
        if not active_polls:
            await ctx.send("📊 Aucun sondage actif.")
            return

        pages = []
        items = list(active_polls.items())
        per_page = 5

        for i in range(0, len(items), per_page):
            page_items = items[i:i + per_page]
            embed = discord.Embed(
                title="📊 Sondages",
                description=f"{len(active_polls)} sondage(s) au total",
                color=COLORS["info"],
                timestamp=datetime.datetime.now(datetime.timezone.utc)
            )

            for pid, pdata in page_items:
                total = sum(len(v) for v in pdata["votes"].values())
                status = "🔒 Terminé" if pdata.get("closed") else "🟢 Actif"
                embed.add_field(
                    name=f"{status} | {pdata['question'][:50]}",
                    value=(
                        f"🆔 `{pid}`\n"
                        f"📈 {total} vote(s) • {len(pdata['options'])} option(s)\n"
                        f"👤 <@{pdata['author_id']}>"
                    ),
                    inline=False
                )

            pages.append(embed)

        await paginate(ctx, pages)

    @commands.command(name="poll_results", aliases=["poll_result"])
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def poll_results(self, ctx, poll_id: str):
        """Affiche les résultats détaillés d'un sondage."""
        poll = active_polls.get(poll_id)
        if not poll:
            await ctx.send("❌ Sondage introuvable.", delete_after=10)
            return

        total_votes = sum(len(v) for v in poll["votes"].values())

        embed = discord.Embed(
            title=f"📊 Résultats: {poll['question']}",
            color=COLORS["info"],
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )

        # Trier par nombre de votes
        sorted_options = sorted(
            range(len(poll["options"])),
            key=lambda i: len(poll["votes"].get(str(i), [])),
            reverse=True
        )

        for rank, idx in enumerate(sorted_options, 1):
            option = poll["options"][idx]
            vote_count = len(poll["votes"].get(str(idx), []))
            bar = generate_poll_bar(vote_count, total_votes, 12)

            medal = ""
            if rank == 1:
                medal = "🥇"
            elif rank == 2:
                medal = "🥈"
            elif rank == 3:
                medal = "🥉"

            embed.add_field(
                name=f"{medal} #{rank} — {option}",
                value=f"{bar} ({vote_count} vote{'s' if vote_count > 1 else ''})",
                inline=False
            )

        embed.add_field(
            name="📈 Total",
            value=f"**{total_votes}** vote(s) enregistré(s)",
            inline=False
        )
        embed.set_footer(text=f"ID: {poll_id}")

        await ctx.send(embed=embed)


async def setup(bot):
    """Setup pour discord.py 2.0+"""
    await bot.add_cog(PollSystem(bot))
    logging.info("✅ Cog PollSystem chargé avec succès")
