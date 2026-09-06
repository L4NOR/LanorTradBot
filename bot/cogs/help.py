"""
/aide — la liste des commandes, filtrée selon tes permissions
==============================================================
"""
import discord
from discord import app_commands
from discord.ext import commands

from bot.config import GUILD_ID, COLOR_NEUTRAL, SITE
from bot.embeds import brand_embed

GUILD = discord.Object(id=GUILD_ID) if GUILD_ID else None


class Help(commands.Cog):
    """Aide."""

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="aide", description="Toutes les commandes du bot")
    @app_commands.guilds(GUILD)
    async def aide(self, interaction: discord.Interaction):
        perms = interaction.user.guild_permissions
        is_staff = perms.manage_messages or perms.administrator
        is_admin = perms.administrator or perms.manage_guild

        embed = brand_embed(
            interaction.guild,
            title="🩸 Les commandes de LanorTrad",
            description=(
                "Tout passe par les commandes slash : tape `/` et laisse-toi "
                "guider.\n"
                f"📚 Les chapitres se lisent sur **{SITE['accueil']}**"
            ),
            color=COLOR_NEUTRAL,
        )

        embed.add_field(
            name="📖 Suivre les sorties",
            value=(
                "`/planning` — le rythme de parution, jour par jour\n"
                "`/atelier` — où en est chaque prochain chapitre\n"
                "`/sorties` — les derniers chapitres publiés\n"
                "`/alertes` — choisir les séries qui te pinguent\n"
                "*et le 🔔 suivi de fabrication, pour voir les "
                "chapitres avancer entre deux sorties*"
            ),
            inline=False,
        )

        embed.add_field(
            name="📚 Le catalogue",
            value=(
                "`/catalogue` — toutes les séries\n"
                "`/serie <nom>` — la fiche complète d'une série\n"
                "`/site` — tous les liens utiles"
            ),
            inline=False,
        )

        embed.add_field(
            name="🤝 Nous parler",
            value=(
                "`/postuler` — rejoindre la team scantrad\n"
                "*Pour le reste, ouvre un ticket dans le salon support.*"
            ),
            inline=False,
        )

        if is_staff:
            embed.add_field(
                name="🏭 L'atelier — la chaîne de fabrication",
                value=(
                    "`/atelier_raws` — ouvrir la fiche d'un chapitre\n"
                    "`/atelier_clean` `/atelier_trad` `/atelier_edit` "
                    "`/atelier_qcheck` — valider son étape\n"
                    "`/atelier_liste` — tout ce qui est en cours\n"
                    "`/atelier_fiche` — revoir une fiche\n"
                    "`/atelier_eta` — fixer la date de sortie visée\n"
                    "`/atelier_export` — le `atelier.js` du site, "
                    "à jour depuis les fiches\n"
                    "*Chaque étape validée ping le métier suivant.*"
                ),
                inline=False,
            )

            embed.add_field(
                name="🛠️ Équipe",
                value=(
                    "`/release` — publier une sortie à la main\n"
                    "`/site_sync` — forcer la synchro avec le site\n"
                    "`/annonce` — annonce signée, avec ping\n"
                    "`/candidatures` — les candidatures en cours\n"
                    "`/clear` `/lent` `/verrou` `/deverrou`\n"
                    "`/timeout` `/kick` `/ban`\n"
                    "`/warn` `/warns` `/delwarn` `/clearwarns`"
                ),
                inline=False,
            )

        if is_admin:
            embed.add_field(
                name="⚙️ Administration",
                value=(
                    "`/publier <page>` — (re)poster les pages de référence\n"
                    "`/atelier_etape` `/atelier_retirer` — corriger une fiche\n"
                    "`/atelier_pousser` — écrire `atelier.js` dans le dépôt du site\n"
                    "`/panneau_alertes` · `/ticket_setup` · `/recrutement_panel`\n"
                    "`/suivi_setup` — créer le rôle de suivi de fabrication\n"
                    "`/raid` · `/lockdown` — protection du serveur\n"
                    "`/backup` — sauvegarde de la structure\n"
                    "`/logs` — état du cache des messages\n"
                    "`/dis` — faire parler le bot"
                ),
                inline=False,
            )

        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(Help(bot))
