"""
Rangement de la hiérarchie des rôles
======================================
Remet les rôles dans un ordre qui se lit : l'équipe en haut, les métiers
dans l'ordre du pipeline, puis les rôles discrets (lecteur, pings).

  /roles_ranger   — applique l'ordre (simulation par défaut)

Deux principes derrière l'ordre choisi :

  • **Le rôle du bot doit rester au-dessus de tout ce qu'il attribue.**
    C'est la cause n°1 des « je n'ai pas pu modifier ce rôle ».
  • **Seuls les rôles porteurs de sens social sont affichés séparément**
    dans la liste des membres. Cent lecteurs affichés en bloc n'apprennent
    rien à personne ; une équipe de cinq, si.
"""
import logging

import discord
from discord import app_commands
from discord.ext import commands

from bot.config import GUILD_ID, ROLES, COLOR_SUCCESS, COLOR_WARNING, COLOR_ERROR
from bot.embeds import brand_embed

log = logging.getLogger("lanortrad.rolesorder")

GUILD = discord.Object(id=GUILD_ID) if GUILD_ID else None

# Du plus haut au plus bas. Clé de ROLES → (affiché séparément, mentionnable)
ORDRE = [
    ("founder",            True,  True),
    ("moderator",          True,  True),
    # ── l'équipe, dans l'ordre du pipeline du site ──
    ("raw_provider",       True,  True),
    ("cleaner",            True,  True),
    ("translator",         True,  True),
    ("typesetter",         True,  True),
    ("qc",                 True,  True),
    ("trial",              True,  False),
    # ── rôles discrets ──
    ("member",             False, False),
    ("ping_tougen",        False, True),
    ("ping_ao",            False, True),
    ("ping_tokyo",         False, True),
    ("ping_cat",           False, True),
    ("ping_sat",           False, True),
    ("ping_one",           False, True),
    ("ping_all",           False, True),
    ("ping_announcements", False, True),
]


class RolesOrder(commands.Cog):
    """Ordre et affichage des rôles."""

    def __init__(self, bot):
        self.bot = bot

    def _plan(self, guild):
        """Retourne (rôles ordonnés, clés introuvables, rôles hors de portée)."""
        ordonnes, absents, hors_portee = [], [], []
        sommet = guild.me.top_role
        for cle, hoist, mentionable in ORDRE:
            role_id = ROLES.get(cle)
            role = guild.get_role(role_id) if role_id else None
            if role is None:
                absents.append(cle)
                continue
            if role >= sommet:
                hors_portee.append(role)
                continue
            ordonnes.append((role, hoist, mentionable))
        return ordonnes, absents, hors_portee

    @app_commands.command(
        name="roles_ranger",
        description="(Admin) Range les rôles dans l'ordre prévu")
    @app_commands.describe(
        affichage="Ajuste aussi « afficher séparément » et « mentionnable »",
        simulation="True = montre l'ordre prévu, sans rien changer")
    @app_commands.default_permissions(administrator=True)
    @app_commands.guilds(GUILD)
    async def roles_ranger(self, interaction: discord.Interaction,
                           affichage: bool = True, simulation: bool = True):
        guild = interaction.guild
        ordonnes, absents, hors_portee = self._plan(guild)

        if not ordonnes:
            await interaction.response.send_message(
                "❌ Aucun rôle à ranger : vérifie les IDs dans la config.",
                ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True, thinking=True)

        apercu = "\n".join(
            f"`{i:>2}` {role.mention}"
            + ("  ·  affiché à part" if hoist else "")
            for i, (role, hoist, _) in enumerate(ordonnes, start=1)
        )
        remarques = []
        if hors_portee:
            remarques.append(
                "⚠️ Au-dessus du rôle du bot, donc intouchables : "
                + ", ".join(r.mention for r in hors_portee)
                + " — remonte le rôle du bot pour les inclure.")
        if absents:
            remarques.append("ℹ️ Clés sans rôle sur ce serveur : "
                             + ", ".join(f"`{a}`" for a in absents))

        if simulation:
            embed = brand_embed(
                guild,
                title="🔎 Ordre prévu — rien n'a été modifié",
                description=(
                    f"Le rôle du bot ({guild.me.top_role.mention}) reste "
                    "au-dessus de tout ce qui suit.\n\n" + apercu
                    + ("\n\n" + "\n".join(remarques) if remarques else "")
                    + "\n\nPour appliquer : relance avec `simulation:False`."
                ),
                color=COLOR_WARNING,
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        # Positions décroissantes en partant de juste sous le rôle du bot
        depart = guild.me.top_role.position - 1
        positions = {}
        for decalage, (role, _, _) in enumerate(ordonnes):
            place = depart - decalage
            if place < 1:            # 0 est réservé à @everyone
                break
            positions[role] = place

        try:
            await guild.edit_role_positions(
                positions=positions, reason=f"Rangement par {interaction.user}")
        except discord.HTTPException as e:
            await interaction.followup.send(
                embed=brand_embed(
                    guild, title="❌ Discord a refusé le rangement",
                    description=f"```{e}```\nLe rôle du bot est-il bien "
                                "au-dessus des rôles concernés ?",
                    color=COLOR_ERROR),
                ephemeral=True)
            return

        ajustes = 0
        if affichage:
            for role, hoist, mentionable in ordonnes:
                if role.hoist == hoist and role.mentionable == mentionable:
                    continue
                try:
                    await role.edit(hoist=hoist, mentionable=mentionable,
                                    reason="Rangement des rôles")
                    ajustes += 1
                except discord.HTTPException:
                    pass

        embed = brand_embed(
            guild,
            title="✅ Rôles rangés",
            description=(
                f"**Rôles repositionnés :** {len(positions)}\n"
                f"**Affichage ajusté :** {ajustes}\n\n" + apercu
                + ("\n\n" + "\n".join(remarques) if remarques else "")
            ),
            color=COLOR_SUCCESS,
        )
        log.info("Roles ranges : %d positions, %d affichages", len(positions), ajustes)
        await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(RolesOrder(bot))
