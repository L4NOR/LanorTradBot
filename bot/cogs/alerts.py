"""
Alertes de sorties — un rôle de ping par série
================================================
Un panneau de boutons : le membre clique sur les séries qu'il suit, et il
est pingé à chaque nouveau chapitre. Reclic = désabonnement.

  /panneau_alertes — (admin) pose le panneau dans le salon des alertes
  /alertes         — ouvre le panneau pour soi, en éphémère
  /suivi_setup     — (admin) crée le rôle « 🔔 Suivi de fabrication »

Un dernier bouton, à part : **🔔 Suivi de fabrication**. Il ne prévient pas
des sorties mais de l'avancement — « le chapitre passe en édition ». Pour
les gens qui trouvent l'attente moins longue quand ils la voient bouger.

Les rôles de séries existent déjà sur le serveur : le bot les retrouve par
leur nom au démarrage (voir resolver.py), il n'en crée aucun. Seul le rôle
de suivi peut être créé, et seulement sur demande explicite.
"""
import logging

import discord
from discord import app_commands
from discord.ext import commands

from bot.config import (
    GUILD_ID, ROLES, MANGAS, COLOR_NEUTRAL, COLOR_SUCCESS, COLOR_WARNING,
    SITE, ATELIER_SUIVI_ROLE,
)
from bot.embeds import brand_embed

log = logging.getLogger("lanortrad.alerts")

GUILD = discord.Object(id=GUILD_ID) if GUILD_ID else None

NOM_SUIVI = "🔔 Suivi de fabrication"


async def _basculer(interaction: discord.Interaction, role_id, libelle: str,
                    *, ajoute: str, retire: str):
    """Ajoute ou retire un rôle, avec des messages qui disent quoi faire."""
    if not role_id:
        return await interaction.response.send_message(
            f"❌ Le rôle **{libelle}** n'existe pas encore sur ce serveur.",
            ephemeral=True)
    role = interaction.guild.get_role(role_id)
    if role is None:
        return await interaction.response.send_message(
            f"❌ Rôle **{libelle}** introuvable.", ephemeral=True)

    membre = interaction.user
    try:
        if role in membre.roles:
            await membre.remove_roles(role, reason="Panneau d'alertes")
            await interaction.response.send_message(retire, ephemeral=True)
        else:
            await membre.add_roles(role, reason="Panneau d'alertes")
            await interaction.response.send_message(ajoute, ephemeral=True)
    except discord.Forbidden:
        await interaction.response.send_message(
            f"❌ Je n'ai pas pu modifier **{libelle}** — mon rôle doit être "
            "au-dessus du sien dans la liste.", ephemeral=True)


class SeriesPanel(discord.ui.View):
    """Un bouton par série, plus le suivi de fabrication en dessous."""

    def __init__(self):
        super().__init__(timeout=None)
        for slug, info in MANGAS.items():
            self.add_item(SeriesButton(slug, info))
        self.add_item(SuiviButton())


class SeriesButton(discord.ui.Button):
    def __init__(self, slug, info):
        super().__init__(
            label=info["name"],
            emoji=info["emoji"],
            style=discord.ButtonStyle.secondary,
            custom_id=f"lanortrad:serie:{slug}",
        )
        self.slug = slug
        self.info = info

    async def callback(self, interaction: discord.Interaction):
        await _basculer(
            interaction, ROLES.get(self.info["role_key"]), self.info["name"],
            ajoute=f"✅ Ping **{self.info['name']}** ajouté.",
            retire=f"🚫 Ping **{self.info['name']}** retiré.")


class SuiviButton(discord.ui.Button):
    """L'avancement des chapitres, pas seulement leur sortie."""

    def __init__(self):
        super().__init__(
            label="Suivi de fabrication",
            emoji="🔔",
            style=discord.ButtonStyle.primary,
            custom_id="lanortrad:suivi_fabrication",
            row=2,
        )

    async def callback(self, interaction: discord.Interaction):
        await _basculer(
            interaction, ROLES.get(ATELIER_SUIVI_ROLE), "Suivi de fabrication",
            ajoute=("🔔 Tu suivras maintenant **l'avancement** des chapitres : "
                    "clean, traduction, édition, Q-check.\n"
                    "*Ça fait quelques messages par semaine. Reclique sur le "
                    "bouton quand tu en as assez.*"),
            retire="🚫 Tu ne suis plus l'avancement des chapitres.")


# ═══════════════════════════════════════════════════════
# COG
# ═══════════════════════════════════════════════════════

class Alerts(commands.Cog):
    """Panneau des alertes de sorties."""

    def __init__(self, bot):
        self.bot = bot
        self.bot.add_view(SeriesPanel())

    def _embed(self, guild) -> discord.Embed:
        return brand_embed(
            guild,
            title="🔔 Alertes de sorties",
            description=(
                "Choisis les séries pour lesquelles tu veux être **prévenu·e "
                "à chaque nouveau chapitre**.\n"
                "Reclique sur un bouton pour te désabonner.\n\n"
                "**🔔 Suivi de fabrication** est à part : il ne prévient pas "
                "des sorties, mais de l'**avancement** — quand un chapitre "
                "passe en clean, en traduction, en édition.\n\n"
                f"📚 Les chapitres se lisent sur {SITE['catalogue']}"
            ),
            color=COLOR_NEUTRAL,
        )

    @app_commands.command(
        name="panneau_alertes",
        description="(Admin) Pose le panneau des alertes dans ce salon")
    @app_commands.default_permissions(administrator=True)
    @app_commands.guilds(GUILD)
    async def panneau_alertes(self, interaction: discord.Interaction):
        await interaction.channel.send(
            embed=self._embed(interaction.guild), view=SeriesPanel())
        await interaction.response.send_message(
            "✅ Panneau des alertes posté.", ephemeral=True)

    @app_commands.command(
        name="alertes",
        description="Choisis les séries qui te préviennent à chaque sortie")
    @app_commands.guilds(GUILD)
    async def alertes(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            embed=self._embed(interaction.guild), view=SeriesPanel(),
            ephemeral=True)

    @app_commands.command(
        name="suivi_setup",
        description="(Admin) Crée le rôle « Suivi de fabrication »")
    @app_commands.default_permissions(administrator=True)
    @app_commands.guilds(GUILD)
    async def suivi_setup(self, interaction: discord.Interaction):
        guild = interaction.guild
        existant = guild.get_role(ROLES.get(ATELIER_SUIVI_ROLE) or 0)
        if existant is None:
            # Peut-être créé à la main sous ce nom : on regarde avant.
            existant = discord.utils.find(
                lambda r: r.name.strip() == NOM_SUIVI
                or r.name.strip().lower() == "suivi de fabrication",
                guild.roles)

        if existant is not None:
            ROLES[ATELIER_SUIVI_ROLE] = existant.id
            return await interaction.response.send_message(
                embed=brand_embed(
                    guild, title="✅ Le rôle existe déjà",
                    description=(
                        f"{existant.mention} est branché sur le suivi.\n"
                        f"**{len(existant.members)}** membre(s) abonné(s).\n\n"
                        "Si le bouton manque sur le panneau, relance "
                        "`/panneau_alertes` pour en poser un neuf."),
                    color=COLOR_SUCCESS),
                ephemeral=True)

        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            role = await guild.create_role(
                name=NOM_SUIVI,
                colour=discord.Colour(COLOR_NEUTRAL),
                mentionable=True,
                hoist=False,
                permissions=discord.Permissions.none(),
                reason=f"Suivi de fabrication, demandé par {interaction.user}")
        except discord.Forbidden:
            return await interaction.followup.send(
                embed=brand_embed(
                    guild, title="❌ Création refusée",
                    description="Il me manque la permission **Gérer les rôles**.",
                    color=COLOR_WARNING),
                ephemeral=True)

        ROLES[ATELIER_SUIVI_ROLE] = role.id
        log.info("Role de suivi cree : %s (%s)", role.name, role.id)

        # Sous le rôle du bot, sinon il ne pourra plus l'attribuer.
        try:
            await role.edit(position=max(1, guild.me.top_role.position - 1))
        except discord.HTTPException:
            pass

        await interaction.followup.send(
            embed=brand_embed(
                guild, title="🔔 Rôle créé",
                description=(
                    f"{role.mention} est prêt. Aucune permission, aucun "
                    "affichage séparé : il ne sert qu'à être pingé.\n\n"
                    "**Il reste une chose à faire :** relance "
                    "`/panneau_alertes` pour poser un panneau contenant le "
                    "nouveau bouton — les panneaux déjà postés ne l'ont pas.\n\n"
                    "Le bot retrouvera ce rôle par son nom aux prochains "
                    "démarrages, rien à noter dans la config."),
                color=COLOR_SUCCESS),
            ephemeral=True)


async def setup(bot):
    await bot.add_cog(Alerts(bot))
