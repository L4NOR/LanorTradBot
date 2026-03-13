# stats.py
# ═══════════════════════════════════════════════════════════════════════════════
# STATISTIQUES DU SERVEUR - Dashboard complet
# ═══════════════════════════════════════════════════════════════════════════════

import discord
from discord.ext import commands
import datetime
import logging

from config import ADMIN_ROLES, COLORS, MANGA_CHANNELS, MANGA_EMOJIS
from utils import paginate, generate_progress_bar

logger = logging.getLogger(__name__)


class ServerStats(commands.Cog):
    """Statistiques complètes du serveur."""

    def __init__(self, bot):
        self.bot = bot
        logger.info("✅ Module ServerStats initialisé")

    # ─────────────────────────────────────────────────────────────────────────
    # COMMANDE PRINCIPALE - !serverstats
    # ─────────────────────────────────────────────────────────────────────────

    @commands.command(name="serverstats", aliases=["sstats", "server_stats", "dashboard"])
    @commands.cooldown(1, 15, commands.BucketType.user)
    async def server_stats(self, ctx):
        """Affiche un dashboard complet des statistiques du serveur."""
        guild = ctx.guild
        if not guild:
            return

        pages = []

        # ═══════════════ PAGE 1: VUE D'ENSEMBLE ═══════════════

        embed1 = discord.Embed(
            title=f"📊 Statistiques — {guild.name}",
            color=COLORS["info"],
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )
        if guild.icon:
            embed1.set_thumbnail(url=guild.icon.url)

        # Membres
        total_members = guild.member_count
        bots = sum(1 for m in guild.members if m.bot)
        humans = total_members - bots
        online = sum(1 for m in guild.members if m.status != discord.Status.offline and not m.bot)

        embed1.add_field(
            name="👥 Membres",
            value=(
                f"👤 Total: **{total_members}**\n"
                f"🧑 Humains: **{humans}**\n"
                f"🤖 Bots: **{bots}**\n"
                f"🟢 En ligne: **{online}**"
            ),
            inline=True
        )

        # Canaux
        text_channels = len(guild.text_channels)
        voice_channels = len(guild.voice_channels)
        categories = len(guild.categories)
        threads = len(guild.threads)

        embed1.add_field(
            name="📁 Canaux",
            value=(
                f"💬 Texte: **{text_channels}**\n"
                f"🎤 Vocal: **{voice_channels}**\n"
                f"📂 Catégories: **{categories}**\n"
                f"🧵 Fils: **{threads}**"
            ),
            inline=True
        )

        # Serveur
        embed1.add_field(
            name="🏠 Serveur",
            value=(
                f"👑 Propriétaire: {guild.owner.mention if guild.owner else 'N/A'}\n"
                f"📅 Créé: {discord.utils.format_dt(guild.created_at, style='D')}\n"
                f"🔓 Vérification: {str(guild.verification_level).capitalize()}\n"
                f"💎 Boosts: **{guild.premium_subscription_count}** (Nv. {guild.premium_tier})"
            ),
            inline=False
        )

        # Rôles
        embed1.add_field(
            name="🏷️ Rôles",
            value=f"**{len(guild.roles)}** rôles au total",
            inline=True
        )

        # Emojis
        embed1.add_field(
            name="😀 Emojis",
            value=f"**{len(guild.emojis)}/{guild.emoji_limit}** emojis",
            inline=True
        )

        # Stickers
        embed1.add_field(
            name="🏷️ Stickers",
            value=f"**{len(guild.stickers)}/{guild.sticker_limit}** stickers",
            inline=True
        )

        embed1.set_footer(text="Page 1/3 • Vue d'ensemble")
        pages.append(embed1)

        # ═══════════════ PAGE 2: ACTIVITÉ MEMBRES ═══════════════

        embed2 = discord.Embed(
            title=f"📈 Activité — {guild.name}",
            color=COLORS["success"],
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )

        # Status des membres
        status_counts = {"online": 0, "idle": 0, "dnd": 0, "offline": 0}
        for m in guild.members:
            if m.bot:
                continue
            status_counts[str(m.status)] = status_counts.get(str(m.status), 0) + 1

        embed2.add_field(
            name="🔵 Statuts des membres",
            value=(
                f"🟢 En ligne: **{status_counts.get('online', 0)}**\n"
                f"🟡 Inactif: **{status_counts.get('idle', 0)}**\n"
                f"🔴 Ne pas déranger: **{status_counts.get('dnd', 0)}**\n"
                f"⚫ Hors ligne: **{status_counts.get('offline', 0)}**"
            ),
            inline=True
        )

        # Membres en vocal
        voice_members = sum(len(vc.members) for vc in guild.voice_channels)
        embed2.add_field(
            name="🎤 En vocal",
            value=f"**{voice_members}** membre(s) actuellement en vocal",
            inline=True
        )

        # Ancienneté des membres
        now = datetime.datetime.now(datetime.timezone.utc)
        new_members_7d = sum(
            1 for m in guild.members
            if m.joined_at and (now - m.joined_at).days <= 7 and not m.bot
        )
        new_members_30d = sum(
            1 for m in guild.members
            if m.joined_at and (now - m.joined_at).days <= 30 and not m.bot
        )

        embed2.add_field(
            name="📅 Nouveaux membres",
            value=(
                f"📆 7 derniers jours: **{new_members_7d}**\n"
                f"📅 30 derniers jours: **{new_members_30d}**"
            ),
            inline=False
        )

        # Top 5 rôles les plus populaires (hors @everyone et rôles admin)
        role_counts = []
        for role in guild.roles:
            if role.name == "@everyone":
                continue
            if len(role.members) > 0:
                role_counts.append((role, len(role.members)))

        role_counts.sort(key=lambda x: x[1], reverse=True)
        top_roles = role_counts[:8]

        if top_roles:
            roles_text = "\n".join([
                f"**{i+1}.** {role.mention} — {count} membre(s)"
                for i, (role, count) in enumerate(top_roles)
            ])
            embed2.add_field(name="🏷️ Top Rôles", value=roles_text, inline=False)

        embed2.set_footer(text="Page 2/3 • Activité")
        pages.append(embed2)

        # ═══════════════ PAGE 3: STATS PROJETS MANGA ═══════════════

        embed3 = discord.Embed(
            title=f"📚 Projets Manga — {guild.name}",
            color=0x1E90FF,
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )

        # Stats par manga depuis le système de tâches
        try:
            import commands as cmd
            tasks_data = cmd.etat_taches_global

            manga_stats = {}
            for key, tasks in tasks_data.items():
                parts = key.rsplit("_", 1)
                if len(parts) != 2:
                    continue
                manga_name = parts[0]
                if manga_name.lower() not in manga_stats:
                    manga_stats[manga_name.lower()] = {
                        "total": 0, "done": 0, "in_progress": 0, "name": manga_name
                    }

                stats = manga_stats[manga_name.lower()]
                stats["total"] += 1

                taches = ["clean", "trad", "check", "edit"]
                all_done = True
                any_progress = False

                for t in taches:
                    val = tasks.get(t, "❌ Non commencé")
                    if isinstance(val, dict):
                        any_progress = True
                        all_done = False
                    elif val == "✅ Terminé":
                        pass
                    else:
                        all_done = False

                if all_done:
                    stats["done"] += 1
                elif any_progress:
                    stats["in_progress"] += 1

            if manga_stats:
                for manga_key, stats in manga_stats.items():
                    emoji = MANGA_EMOJIS.get(stats["name"], "📚")
                    bar = generate_progress_bar(stats["done"], stats["total"])

                    embed3.add_field(
                        name=f"{emoji} {stats['name']}",
                        value=(
                            f"📊 {stats['done']}/{stats['total']} chapitres terminés\n"
                            f"🔄 {stats['in_progress']} en cours\n"
                            f"{bar}"
                        ),
                        inline=True
                    )
            else:
                embed3.add_field(
                    name="📊 Aucune donnée",
                    value="Aucune tâche enregistrée pour le moment.",
                    inline=False
                )
        except Exception as e:
            embed3.add_field(
                name="📊 Projets",
                value="Données non disponibles.",
                inline=False
            )
            logger.error(f"Erreur stats projets: {e}")

        # Stats XP globales
        try:
            from community import user_stats, calculate_level
            if user_stats:
                total_xp = sum(s.get("total_xp", 0) for s in user_stats.values())
                active_users = sum(1 for s in user_stats.values() if s.get("total_xp", 0) > 0)
                avg_level = sum(
                    calculate_level(s.get("total_xp", 0))
                    for s in user_stats.values()
                ) / max(len(user_stats), 1)

                embed3.add_field(
                    name="⭐ Communauté XP",
                    value=(
                        f"📈 XP total distribué: **{total_xp:,}**\n"
                        f"👥 Utilisateurs actifs: **{active_users}**\n"
                        f"📊 Niveau moyen: **{avg_level:.1f}**"
                    ),
                    inline=False
                )
        except Exception as e:
            logger.error(f"Erreur stats XP: {e}")

        embed3.set_footer(text="Page 3/3 • Projets")
        pages.append(embed3)

        await paginate(ctx, pages)

    # ─────────────────────────────────────────────────────────────────────────
    # COMMANDE - STATS RAPIDES
    # ─────────────────────────────────────────────────────────────────────────

    @commands.command(name="membercount", aliases=["mc"])
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def member_count(self, ctx):
        """Affiche le nombre de membres rapidement."""
        guild = ctx.guild
        humans = sum(1 for m in guild.members if not m.bot)
        online = sum(1 for m in guild.members if m.status != discord.Status.offline and not m.bot)

        embed = discord.Embed(
            title=f"👥 {guild.name}",
            color=COLORS["info"]
        )
        embed.add_field(name="👤 Membres", value=f"**{humans}**", inline=True)
        embed.add_field(name="🟢 En ligne", value=f"**{online}**", inline=True)
        embed.add_field(name="💎 Boosts", value=f"**{guild.premium_subscription_count}**", inline=True)

        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)

        await ctx.send(embed=embed)

    # ─────────────────────────────────────────────────────────────────────────
    # COMMANDE - TOP CONTRIBUTEURS
    # ─────────────────────────────────────────────────────────────────────────

    @commands.command(name="topcontrib", aliases=["contributors", "top_contrib"])
    @commands.cooldown(1, 15, commands.BucketType.user)
    async def top_contributors(self, ctx):
        """Affiche les top contributeurs du projet."""
        try:
            import commands as cmd
            tasks_data = cmd.etat_taches_global

            # Compter les contributions par personne
            contributions = {}

            for key, tasks in tasks_data.items():
                for task_name, task_val in tasks.items():
                    if isinstance(task_val, dict) and task_val.get("claimed_by"):
                        user_id = task_val["claimed_by"]
                        if user_id not in contributions:
                            contributions[user_id] = {"claimed": 0, "done": 0}
                        contributions[user_id]["claimed"] += 1
                        if task_val.get("status") == "✅ Terminé":
                            contributions[user_id]["done"] += 1
                    elif task_val == "✅ Terminé":
                        pass  # Pas de tracking de qui l'a fait dans l'ancien format

            if not contributions:
                await ctx.send("📊 Aucune contribution trackée pour le moment.")
                return

            # Trier par nombre de claims
            sorted_contribs = sorted(
                contributions.items(),
                key=lambda x: x[1]["claimed"],
                reverse=True
            )[:10]

            embed = discord.Embed(
                title="🏆 Top Contributeurs",
                color=COLORS["info"],
                timestamp=datetime.datetime.now(datetime.timezone.utc)
            )

            medals = ["🥇", "🥈", "🥉"]
            for i, (user_id, stats) in enumerate(sorted_contribs):
                try:
                    user = await self.bot.fetch_user(user_id)
                    name = user.display_name
                except:
                    name = f"User {user_id}"

                medal = medals[i] if i < 3 else f"**{i+1}.**"
                embed.add_field(
                    name=f"{medal} {name}",
                    value=f"📋 {stats['claimed']} tâche(s) réclamée(s) • ✅ {stats['done']} terminée(s)",
                    inline=False
                )

            await ctx.send(embed=embed)

        except Exception as e:
            await ctx.send("❌ Erreur lors du calcul des contributions.")
            logger.error(f"Erreur topcontrib: {e}")


async def setup(bot):
    """Setup pour discord.py 2.0+"""
    await bot.add_cog(ServerStats(bot))
    logging.info("✅ Cog ServerStats chargé avec succès")
