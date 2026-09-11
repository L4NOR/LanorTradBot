"""
Alertes de sorties — un rôle de ping par série
================================================
Un panneau de boutons : le membre clique sur les séries qu'il suit, et il
est pingé à chaque nouveau chapitre. Reclic = désabonnement.

  /panneau_alertes — (admin) pose le panneau dans le salon des alertes
  /alertes         — ouvre le panneau pour soi, en éphémère
  /suivi_setup     — (admin) crée le rôle ET le salon du suivi de fabrication

Un dernier bouton, à part : **🔔 Suivi de fabrication**. Il ne prévient pas
des sorties mais de l'avancement — « le chapitre passe en édition ». Pour
les gens qui trouvent l'attente moins longue quand ils la voient bouger.

L'avancement a son propre salon. Mélangé aux sorties, il noierait ce que
tout le monde vient y chercher : un salon pour « c'est en ligne », un
autre pour « ça avance ». `/suivi_setup` crée les deux pièces — le rôle
et le salon — et tant que le salon manque, le suivi retombe sur les
alertes plutôt que de disparaître.

Les rôles de séries existent déjà sur le serveur : le bot les retrouve par
leur nom au démarrage (voir resolver.py), il n'en crée aucun. Seuls le rôle
et le salon de suivi peuvent être créés, et seulement sur demande explicite
— `/suivi_setup` ne touche à rien d'autre, et ne recrée rien de ce qui
existe déjà sous ce nom.
"""
import logging

import discord
from discord import app_commands
from discord.ext import commands

from bot.config import (
    GUILD_ID, CHANNELS, ROLES, MANGAS,
    COLOR_NEUTRAL, COLOR_SUCCESS, COLOR_WARNING,
    SITE, ATELIER_SUIVI_ROLE, ATELIER_SUIVI_CHANNEL, ATELIER_SUIVI_CHANNEL_REPLI,
)
from bot.embeds import brand_embed

log = logging.getLogger("lanortrad.alerts")

GUILD = discord.Object(id=GUILD_ID) if GUILD_ID else None

NOM_SUIVI = "🔔 Suivi de fabrication"
NOM_SALON_SUIVI = "🛠️・suivi-fabrication"
SUJET_SALON = (
    "Les chapitres en cours de fabrication, étape par étape. "
    "Le rôle 🔔 Suivi de fabrication se prend dans le salon des alertes."
)


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


async def _assurer_salon(guild: discord.Guild):
    """Le salon du suivi : retrouvé s'il existe, créé sinon.

    Retourne (salon, créé, erreur). Un salon en lecture seule : le bot y
    écrit, tout le monde y lit et peut réagir. Il se range juste sous les
    alertes de sorties, parce que c'est là qu'on ira le chercher.
    """
    salon_id = CHANNELS.get(ATELIER_SUIVI_CHANNEL)
    salon = guild.get_channel(salon_id) if salon_id else None
    if salon is None:
        # Peut-être créé à la main depuis le dernier démarrage : on regarde
        # par le nom avant d'en fabriquer un deuxième.
        salon = discord.utils.find(
            lambda c: "suivi-fabrication" in c.name.lower()
            or "avancement" in c.name.lower(),
            guild.text_channels)
    if salon is not None:
        CHANNELS[ATELIER_SUIVI_CHANNEL] = salon.id
        return salon, False, None

    voisin = guild.get_channel(CHANNELS.get(ATELIER_SUIVI_CHANNEL_REPLI) or 0)
    surcharges = {
        guild.default_role: discord.PermissionOverwrite(
            view_channel=True, read_message_history=True,
            send_messages=False, add_reactions=True,
            create_public_threads=False, create_private_threads=False),
        guild.me: discord.PermissionOverwrite(
            view_channel=True, send_messages=True, embed_links=True,
            manage_messages=True, read_message_history=True),
    }
    try:
        salon = await guild.create_text_channel(
            name=NOM_SALON_SUIVI,
            category=voisin.category if voisin is not None else None,
            topic=SUJET_SALON,
            overwrites=surcharges,
            reason="Salon du suivi de fabrication")
    except discord.Forbidden:
        return None, False, "Il me manque la permission **Gérer les salons**."
    except discord.HTTPException as e:
        return None, False, f"Discord a refusé la création : {e}"

    if voisin is not None and voisin.category_id == salon.category_id:
        try:
            await salon.edit(position=voisin.position + 1)
        except discord.HTTPException:
            pass

    CHANNELS[ATELIER_SUIVI_CHANNEL] = salon.id
    log.info("Salon de suivi cree : %s (%s)", salon.name, salon.id)
    return salon, True, None


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
        salon = interaction.guild.get_channel(
            CHANNELS.get(ATELIER_SUIVI_CHANNEL) or 0)
        ou = f" dans {salon.mention}" if salon is not None else ""
        await _basculer(
            interaction, ROLES.get(ATELIER_SUIVI_ROLE), "Suivi de fabrication",
            ajoute=(f"🔔 Tu suivras maintenant **l'avancement** des chapitres{ou} : "
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
        salon = guild.get_channel(CHANNELS.get(ATELIER_SUIVI_CHANNEL) or 0)
        ou = f" dans {salon.mention}" if salon is not None else ""
        return brand_embed(
            guild,
            title="🔔 Alertes de sorties",
            description=(
                "Choisis les séries pour lesquelles tu veux être **prévenu·e "
                "à chaque nouveau chapitre**.\n"
                "Reclique sur un bouton pour te désabonner.\n\n"
                "**🔔 Suivi de fabrication** est à part : il ne prévient pas "
                "des sorties, mais de l'**avancement** — quand un chapitre "
                f"passe en clean, en traduction, en édition. Ça se passe{ou}, "
                "pas ici : ce salon-ci reste réservé aux sorties.\n\n"
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

    async def _assurer_role(self, guild, auteur):
        """Le rôle de ping : retrouvé s'il existe, créé sinon.

        Retourne (rôle, créé, erreur).
        """
        role = guild.get_role(ROLES.get(ATELIER_SUIVI_ROLE) or 0)
        if role is None:
            # Peut-être créé à la main sous ce nom : on regarde avant.
            role = discord.utils.find(
                lambda r: r.name.strip() == NOM_SUIVI
                or r.name.strip().lower() == "suivi de fabrication",
                guild.roles)
        if role is not None:
            ROLES[ATELIER_SUIVI_ROLE] = role.id
            return role, False, None

        try:
            role = await guild.create_role(
                name=NOM_SUIVI,
                colour=discord.Colour(COLOR_NEUTRAL),
                mentionable=True,
                hoist=False,
                permissions=discord.Permissions.none(),
                reason=f"Suivi de fabrication, demandé par {auteur}")
        except discord.Forbidden:
            return None, False, "Il me manque la permission **Gérer les rôles**."
        except discord.HTTPException as e:
            return None, False, f"Discord a refusé la création du rôle : {e}"

        ROLES[ATELIER_SUIVI_ROLE] = role.id
        log.info("Role de suivi cree : %s (%s)", role.name, role.id)

        # Sous le rôle du bot, sinon il ne pourra plus l'attribuer.
        try:
            await role.edit(position=max(1, guild.me.top_role.position - 1))
        except discord.HTTPException:
            pass
        return role, True, None

    @app_commands.command(
        name="suivi_setup",
        description="(Admin) Crée le rôle et le salon du suivi de fabrication")
    @app_commands.default_permissions(administrator=True)
    @app_commands.guilds(GUILD)
    async def suivi_setup(self, interaction: discord.Interaction):
        guild = interaction.guild
        await interaction.response.defer(ephemeral=True, thinking=True)

        role, role_cree, souci_role = await self._assurer_role(
            guild, interaction.user)
        salon, salon_cree, souci_salon = await _assurer_salon(guild)

        lignes, reste = [], []
        if role is not None:
            lignes.append(
                f"🔔 **Rôle** — {role.mention}"
                + (" · créé à l'instant" if role_cree else
                   f" · **{len(role.members)}** abonné(s)"))
        else:
            lignes.append(f"❌ **Rôle** — {souci_role}")

        if salon is not None:
            lignes.append(
                f"🛠️ **Salon** — {salon.mention}"
                + (" · créé à l'instant, en lecture seule" if salon_cree
                   else " · déjà en place"))
        else:
            lignes.append(f"❌ **Salon** — {souci_salon}")
            repli = guild.get_channel(
                CHANNELS.get(ATELIER_SUIVI_CHANNEL_REPLI) or 0)
            if repli is not None:
                lignes.append(f"↩️ En attendant, le suivi continue dans "
                              f"{repli.mention}.")

        if role_cree:
            reste.append("relance `/panneau_alertes` pour poser un panneau "
                         "avec le bouton — les panneaux déjà postés ne l'ont pas")
        if salon_cree:
            reste.append("le prochain message d'avancement partira dans le "
                         "nouveau salon, rien d'autre à faire")

        description = "\n".join(lignes)
        if reste:
            description += "\n\n**Il reste :**\n" + "\n".join(
                f"• {r}" for r in reste)
        description += ("\n\nRôle et salon sont retrouvés par leur nom aux "
                        "prochains démarrages : rien à noter dans la config.")

        rate = role is None or salon is None
        await interaction.followup.send(
            embed=brand_embed(
                guild,
                title="🔧 Suivi de fabrication"
                      + ("" if rate else " — en place"),
                description=description,
                color=COLOR_WARNING if rate else COLOR_SUCCESS),
            ephemeral=True)


async def setup(bot):
    await bot.add_cog(Alerts(bot))
