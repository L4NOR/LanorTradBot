"""
Alertes de sorties — un rôle de ping par série
================================================
Un panneau de boutons : le membre clique sur les séries qu'il suit, et il
est pingé à chaque nouveau chapitre. Reclic = désabonnement.

  /panneau_alertes — (admin) pose le panneau dans le salon des alertes
  /alertes         — ouvre le panneau pour soi, en éphémère

Les rôles sont ceux qui existent déjà sur le serveur : le bot les retrouve
par leur nom au démarrage (voir resolver.py), il n'en crée aucun.
"""
import discord
from discord import app_commands
from discord.ext import commands

from bot.config import GUILD_ID, ROLES, MANGAS, COLOR_NEUTRAL, SITE
from bot.embeds import brand_embed

GUILD = discord.Object(id=GUILD_ID) if GUILD_ID else None


class SeriesPanel(discord.ui.View):
    """Un bouton par série."""

    def __init__(self):
        super().__init__(timeout=None)
        # On ajoute dynamiquement les boutons
        for slug, info in MANGAS.items():
            self.add_item(SeriesButton(slug, info))


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
        role_id = ROLES.get(self.info["role_key"])
        if not role_id:
            await interaction.response.send_message(
                f"❌ Rôle non configuré pour {self.info['name']}.",
                ephemeral=True,
            )
            return
        role = interaction.guild.get_role(role_id)
        if not role:
            await interaction.response.send_message("❌ Rôle introuvable.", ephemeral=True)
            return

        member = interaction.user
        try:
            if role in member.roles:
                await member.remove_roles(role, reason="Alertes de sorties")
                await interaction.response.send_message(
                    f"🚫 Ping **{self.info['name']}** retiré.",
                    ephemeral=True,
                )
            else:
                await member.add_roles(role, reason="Alertes de sorties")
                await interaction.response.send_message(
                    f"✅ Ping **{self.info['name']}** ajouté.",
                    ephemeral=True,
                )
        except discord.Forbidden:
            await interaction.response.send_message(
                f"❌ Je n'ai pas pu modifier le ping **{self.info['name']}** "
                "(hiérarchie des rôles).",
                ephemeral=True,
            )


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


async def setup(bot):
    await bot.add_cog(Alerts(bot))
