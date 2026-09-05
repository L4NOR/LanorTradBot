"""
Attribution de rôles en masse
===============================
Donne un rôle à **tous les membres** du serveur d'un coup — typiquement le
rôle de base après une reconstruction, quand les anciens rôles ont sauté.

  /roles_base              — attribue le(s) rôle(s) de base (simulation)
  /roles_base simulation:False   — applique pour de vrai
  /roles_base role:@X      — attribue n'importe quel rôle à tout le monde

Par défaut la commande tourne en **simulation** : elle dit ce qu'elle ferait
sans rien changer. C'est volontaire — une attribution de masse se relit
avant de se lancer.

Les bots sont ignorés, les membres qui ont déjà le rôle aussi, et le rythme
est volontairement lent pour ne pas se faire jeter par Discord.
"""
import asyncio
import logging

import discord
from discord import app_commands
from discord.ext import commands

from bot.config import (
    GUILD_ID, ROLES, BASE_ROLES,
    COLOR_NEUTRAL, COLOR_SUCCESS, COLOR_WARNING,
)
from bot.embeds import brand_embed

log = logging.getLogger("lanortrad.bulkroles")

GUILD = discord.Object(id=GUILD_ID) if GUILD_ID else None

PAUSE = 0.35        # secondes entre deux attributions
PROGRESS_EVERY = 25  # rafraîchit le compte rendu tous les N membres


class BulkRoles(commands.Cog):
    """Attribution de rôles à l'ensemble des membres."""

    def __init__(self, bot):
        self.bot = bot
        self._running = False

    def _base_roles(self, guild):
        """Rôles de base configurés qui existent réellement sur le serveur."""
        found = []
        for key in BASE_ROLES:
            role_id = ROLES.get(key)
            role = guild.get_role(role_id) if role_id else None
            if role:
                found.append(role)
        return found

    async def _members(self, guild):
        """Liste complète des membres, en forçant le chargement si besoin."""
        if not guild.chunked:
            try:
                await guild.chunk()
            except (discord.ClientException, asyncio.TimeoutError):
                return [m async for m in guild.fetch_members(limit=None)]
        return list(guild.members)

    @app_commands.command(
        name="roles_base",
        description="(Admin) Donne un rôle à tous les membres du serveur")
    @app_commands.describe(
        role="Le rôle à attribuer (par défaut : le rôle de base configuré)",
        simulation="True = montre ce qui serait fait, sans rien changer")
    @app_commands.default_permissions(manage_roles=True)
    @app_commands.guilds(GUILD)
    async def roles_base(self, interaction: discord.Interaction,
                         role: discord.Role = None, simulation: bool = True):
        if self._running:
            await interaction.response.send_message(
                "⏳ Une attribution est déjà en cours.", ephemeral=True)
            return

        guild = interaction.guild
        targets = [role] if role else self._base_roles(guild)
        if not targets:
            await interaction.response.send_message(
                "❌ Aucun rôle de base trouvé. Précise-en un avec `role:`, "
                "ou vérifie que le rôle existe sur le serveur.", ephemeral=True)
            return

        # Le bot ne peut attribuer qu'un rôle situé sous le sien
        too_high = [r for r in targets if r >= guild.me.top_role]
        if too_high:
            await interaction.response.send_message(
                "🚫 " + ", ".join(r.mention for r in too_high)
                + " est au-dessus du rôle du bot : remonte le rôle du bot "
                  "dans Paramètres du serveur → Rôles.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True, thinking=True)

        members = await self._members(guild)
        humains = [m for m in members if not m.bot]
        a_faire = [
            (m, [r for r in targets if r not in m.roles])
            for m in humains
        ]
        a_faire = [(m, roles) for m, roles in a_faire if roles]

        noms = ", ".join(r.mention for r in targets)

        if simulation:
            embed = brand_embed(
                guild,
                title="🔎 Simulation — rien n'a été modifié",
                description=(
                    f"**Rôle(s) :** {noms}\n"
                    f"**Membres humains :** {len(humains)}\n"
                    f"**À qui il manque le rôle :** {len(a_faire)}\n"
                    f"**Déjà en règle :** {len(humains) - len(a_faire)}\n\n"
                    f"⏱️ Durée estimée : environ "
                    f"{max(1, round(len(a_faire) * PAUSE / 60))} min\n\n"
                    "Pour appliquer : relance avec `simulation:False`."
                ),
                color=COLOR_WARNING,
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        if not a_faire:
            await interaction.followup.send(
                f"✅ Tout le monde a déjà {noms}.", ephemeral=True)
            return

        self._running = True
        ok, echecs = 0, []
        log.info("Attribution de masse : %s → %d membres", noms, len(a_faire))

        try:
            message = await interaction.followup.send(
                f"⏳ Attribution en cours… 0 / {len(a_faire)}", ephemeral=True)

            for i, (member, roles) in enumerate(a_faire, start=1):
                try:
                    await member.add_roles(*roles, reason=f"Attribution de masse "
                                                          f"par {interaction.user}")
                    ok += 1
                except discord.HTTPException as e:
                    echecs.append(f"{member} ({e.status if hasattr(e, 'status') else e})")

                if i % PROGRESS_EVERY == 0:
                    try:
                        await message.edit(
                            content=f"⏳ Attribution en cours… {i} / {len(a_faire)}")
                    except discord.HTTPException:
                        pass
                await asyncio.sleep(PAUSE)
        finally:
            self._running = False

        embed = brand_embed(
            guild,
            title="✅ Attribution terminée",
            description=(
                f"**Rôle(s) :** {noms}\n"
                f"**Attribués :** {ok}\n"
                f"**Échecs :** {len(echecs)}"
                + ("\n\n" + "\n".join(f"• {e}" for e in echecs[:10]) if echecs else "")
            ),
            color=COLOR_SUCCESS if not echecs else COLOR_WARNING,
        )
        log.info("Attribution terminée : %d ok, %d échecs", ok, len(echecs))
        try:
            await message.edit(content=None, embed=embed)
        except discord.HTTPException:
            await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(
        name="roles_retirer",
        description="(Admin) Retire un rôle à tous les membres qui l'ont")
    @app_commands.describe(role="Le rôle à retirer",
                           simulation="True = montre ce qui serait fait")
    @app_commands.default_permissions(administrator=True)
    @app_commands.guilds(GUILD)
    async def roles_retirer(self, interaction: discord.Interaction,
                            role: discord.Role, simulation: bool = True):
        guild = interaction.guild
        if role >= guild.me.top_role:
            await interaction.response.send_message(
                f"🚫 {role.mention} est au-dessus du rôle du bot.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True, thinking=True)
        await self._members(guild)
        porteurs = [m for m in role.members if not m.bot]

        if simulation:
            await interaction.followup.send(
                f"🔎 **Simulation** — {len(porteurs)} membre(s) portent "
                f"{role.mention}. Rien n'a été modifié.\n"
                "Pour appliquer : relance avec `simulation:False`.", ephemeral=True)
            return

        ok = 0
        for member in porteurs:
            try:
                await member.remove_roles(role, reason=f"Retrait de masse par "
                                                       f"{interaction.user}")
                ok += 1
            except discord.HTTPException:
                pass
            await asyncio.sleep(PAUSE)

        await interaction.followup.send(
            f"✅ {role.mention} retiré à **{ok}** membre(s).", ephemeral=True)


async def setup(bot):
    await bot.add_cog(BulkRoles(bot))
