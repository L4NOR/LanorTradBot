# tickets.py
# ═══════════════════════════════════════════════════════════════════════════════
# SYSTÈME DE TICKETS & CANDIDATURES - Support + Recrutement
# Canal cible: 1326357433588912179
# ═══════════════════════════════════════════════════════════════════════════════

import discord
from discord.ext import commands
from discord.ui import View, Button, Modal, TextInput
import datetime
import logging

from config import ADMIN_ROLES, CHANNELS, COLORS

logger = logging.getLogger(__name__)

# Canal où le panneau sera posté
TICKET_CHANNEL_ID = 1326357433588912179


# ═══════════════════════════════════════════════════════════════════════════════
# MODAL DE CANDIDATURE
# ═══════════════════════════════════════════════════════════════════════════════

class CandidatureModal(Modal):
    """Formulaire de candidature pour rejoindre l'équipe LanorTrad."""

    def __init__(self, bot):
        super().__init__(title="📝 Candidature - LanorTrad")
        self.bot = bot

        self.pseudo = TextInput(
            label="Pseudo",
            style=discord.TextStyle.short,
            required=True,
            placeholder="Votre pseudo"
        )
        self.poste = TextInput(
            label="Poste souhaité",
            style=discord.TextStyle.short,
            required=True,
            placeholder="Traducteur / Cleaner / Éditeur / Checker / Modérateur"
        )
        self.experience = TextInput(
            label="Expérience",
            style=discord.TextStyle.long,
            required=True,
            placeholder="Décrivez votre expérience dans le domaine...",
            max_length=500
        )
        self.disponibilite = TextInput(
            label="Disponibilité",
            style=discord.TextStyle.short,
            required=True,
            placeholder="Ex: 10h/semaine, weekends, tous les jours..."
        )
        self.motivation = TextInput(
            label="Motivation",
            style=discord.TextStyle.long,
            required=True,
            placeholder="Pourquoi souhaitez-vous rejoindre LanorTrad ?",
            max_length=500
        )

        self.add_item(self.pseudo)
        self.add_item(self.poste)
        self.add_item(self.experience)
        self.add_item(self.disponibilite)
        self.add_item(self.motivation)

    async def on_submit(self, interaction: discord.Interaction):
        """Traitement de la candidature soumise."""
        await interaction.response.send_message(
            "✅ Votre candidature a bien été envoyée ! L'équipe l'examinera dans les plus brefs délais.",
            ephemeral=True
        )

        # Envoyer dans le canal de logs pour les admins
        logs_channel = self.bot.get_channel(CHANNELS.get("logs"))
        if not logs_channel:
            logger.error("Canal de logs introuvable")
            return

        embed = discord.Embed(
            title="📝 Nouvelle Candidature",
            color=0x2ECC71,
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )
        embed.set_author(
            name=str(interaction.user),
            icon_url=interaction.user.display_avatar.url
        )
        embed.add_field(name="👤 Pseudo", value=self.pseudo.value, inline=True)
        embed.add_field(name="📌 Poste souhaité", value=self.poste.value, inline=True)
        embed.add_field(name="📅 Disponibilité", value=self.disponibilite.value, inline=True)
        embed.add_field(name="📚 Expérience", value=self.experience.value, inline=False)
        embed.add_field(name="💬 Motivation", value=self.motivation.value, inline=False)
        embed.add_field(name="🔗 Mention", value=interaction.user.mention, inline=True)
        embed.add_field(
            name="📆 Compte créé le",
            value=discord.utils.format_dt(interaction.user.created_at, style="D"),
            inline=True
        )
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        embed.set_footer(text="Candidature LanorTrad")

        # Boutons d'action pour les admins
        view = CandidatureActionView(interaction.user.id, self.pseudo.value, self.poste.value)
        await logs_channel.send(embed=embed, view=view)
        logger.info(f"Candidature reçue de {interaction.user}")


# ═══════════════════════════════════════════════════════════════════════════════
# ACTIONS ADMIN SUR CANDIDATURE
# ═══════════════════════════════════════════════════════════════════════════════

class CandidatureActionView(View):
    """Boutons pour accepter/refuser une candidature."""

    def __init__(self, user_id: int, pseudo: str, poste: str):
        super().__init__(timeout=None)
        self.user_id = user_id
        self.pseudo = pseudo
        self.poste = poste

    @discord.ui.button(label="✅ Accepter", style=discord.ButtonStyle.success, custom_id="candidature_accept")
    async def accept_candidature(self, interaction: discord.Interaction, button: Button):
        """Accepte la candidature."""
        # Vérifier les permissions admin
        user_roles = [role.id for role in interaction.user.roles]
        if not any(role in user_roles for role in ADMIN_ROLES):
            await interaction.response.send_message("❌ Permissions insuffisantes.", ephemeral=True)
            return

        # Notifier le candidat en DM
        try:
            member = interaction.guild.get_member(self.user_id)
            if member:
                dm_embed = discord.Embed(
                    title="🎉 Candidature Acceptée !",
                    description=(
                        f"Félicitations **{self.pseudo}** !\n\n"
                        f"Votre candidature pour le poste de **{self.poste}** a été **acceptée** !\n"
                        "Un membre du staff vous contactera bientôt pour les prochaines étapes."
                    ),
                    color=COLORS["success"]
                )
                dm_embed.set_footer(text="LanorTrad • Recrutement")
                await member.send(embed=dm_embed)
        except discord.Forbidden:
            pass

        # Mettre à jour l'embed
        embed = interaction.message.embeds[0] if interaction.message.embeds else None
        if embed:
            embed.color = COLORS["success"]
            embed.add_field(
                name="✅ ACCEPTÉE",
                value=f"Par {interaction.user.mention} le {datetime.datetime.now().strftime('%d/%m/%Y %H:%M')}",
                inline=False
            )

        for item in self.children:
            item.disabled = True

        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="❌ Refuser", style=discord.ButtonStyle.danger, custom_id="candidature_refuse")
    async def refuse_candidature(self, interaction: discord.Interaction, button: Button):
        """Refuse la candidature."""
        user_roles = [role.id for role in interaction.user.roles]
        if not any(role in user_roles for role in ADMIN_ROLES):
            await interaction.response.send_message("❌ Permissions insuffisantes.", ephemeral=True)
            return

        try:
            member = interaction.guild.get_member(self.user_id)
            if member:
                dm_embed = discord.Embed(
                    title="📝 Candidature Refusée",
                    description=(
                        f"Bonjour **{self.pseudo}**,\n\n"
                        f"Votre candidature pour le poste de **{self.poste}** n'a pas été retenue pour le moment.\n"
                        "N'hésitez pas à retenter plus tard ! Merci pour votre intérêt."
                    ),
                    color=COLORS["error"]
                )
                dm_embed.set_footer(text="LanorTrad • Recrutement")
                await member.send(embed=dm_embed)
        except discord.Forbidden:
            pass

        embed = interaction.message.embeds[0] if interaction.message.embeds else None
        if embed:
            embed.color = COLORS["error"]
            embed.add_field(
                name="❌ REFUSÉE",
                value=f"Par {interaction.user.mention} le {datetime.datetime.now().strftime('%d/%m/%Y %H:%M')}",
                inline=False
            )

        for item in self.children:
            item.disabled = True

        await interaction.response.edit_message(embed=embed, view=self)


# ═══════════════════════════════════════════════════════════════════════════════
# VUE BOUTON FERMER TICKET
# ═══════════════════════════════════════════════════════════════════════════════

class CloseTicketView(View):
    """Bouton pour fermer un ticket."""

    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(label="🔒 Fermer le ticket", style=discord.ButtonStyle.danger, custom_id="ticket_close")
    async def close_ticket(self, interaction: discord.Interaction, button: Button):
        thread = interaction.channel
        if not isinstance(thread, discord.Thread):
            await interaction.response.send_message(
                "❌ Cette action ne fonctionne que dans un ticket.",
                ephemeral=True
            )
            return

        await interaction.response.send_message(
            embed=discord.Embed(
                title="🔒 Ticket Fermé",
                description="Ce ticket a été fermé et archivé.",
                color=discord.Color.red(),
                timestamp=datetime.datetime.now(datetime.timezone.utc)
            ).set_footer(text=f"Fermé par {interaction.user}")
        )

        await thread.edit(archived=True, locked=True)
        logger.info(f"Ticket '{thread.name}' fermé par {interaction.user}")


# ═══════════════════════════════════════════════════════════════════════════════
# VUE PANNEAU PRINCIPAL (BOUTONS TICKET + CANDIDATURE)
# ═══════════════════════════════════════════════════════════════════════════════

class TicketPanelView(View):
    """Panneau principal avec boutons Ticket et Candidature."""

    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(label="📩 Créer un Ticket", style=discord.ButtonStyle.primary, custom_id="ticket_create")
    async def create_ticket(self, interaction: discord.Interaction, button: Button):
        """Crée un nouveau ticket (thread privé)."""
        channel = interaction.channel

        # Vérifier si l'utilisateur a déjà un ticket ouvert
        for thread in channel.threads:
            if thread.name.startswith(f"ticket-{interaction.user.name}") and not thread.archived:
                await interaction.response.send_message(
                    f"❌ Vous avez déjà un ticket ouvert : {thread.mention}",
                    ephemeral=True
                )
                return

        # Vérifier les threads archivés non verrouillés
        async for thread in channel.archived_threads(limit=50):
            if thread.name.startswith(f"ticket-{interaction.user.name}") and not thread.locked:
                await interaction.response.send_message(
                    f"❌ Vous avez un ticket non résolu : {thread.mention}",
                    ephemeral=True
                )
                return

        # Générer un ID unique
        cog = self.bot.get_cog("TicketSystem")
        if cog:
            cog.ticket_counter += 1
            counter = cog.ticket_counter
        else:
            counter = int(datetime.datetime.now().timestamp()) % 10000

        thread_name = f"ticket-{interaction.user.name}-{counter}"

        thread = await channel.create_thread(
            name=thread_name,
            type=discord.ChannelType.private_thread
        )

        await thread.add_user(interaction.user)

        welcome_embed = discord.Embed(
            title="📩 Ticket Ouvert",
            description=(
                f"Bienvenue {interaction.user.mention} !\n\n"
                "Un membre du staff vous répondra dans les plus brefs délais.\n"
                "Veuillez décrire votre demande en détail ci-dessous.\n\n"
                "Pour fermer ce ticket, cliquez sur le bouton 🔒."
            ),
            color=COLORS["info"],
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )
        welcome_embed.set_footer(text=f"Ticket #{counter}")

        await thread.send(embed=welcome_embed, view=CloseTicketView(self.bot))

        await interaction.response.send_message(
            f"✅ Votre ticket a été créé : {thread.mention}",
            ephemeral=True
        )
        logger.info(f"Ticket '{thread_name}' créé par {interaction.user}")

    @discord.ui.button(label="📝 Candidature", style=discord.ButtonStyle.success, custom_id="ticket_candidature")
    async def candidature(self, interaction: discord.Interaction, button: Button):
        """Ouvre le formulaire de candidature."""
        await interaction.response.send_modal(CandidatureModal(self.bot))


# ═══════════════════════════════════════════════════════════════════════════════
# COG PRINCIPAL
# ═══════════════════════════════════════════════════════════════════════════════

class TicketSystem(commands.Cog):
    """Système de tickets et candidatures."""

    def __init__(self, bot):
        self.bot = bot
        self.ticket_counter = 0
        # Enregistrer les views persistantes
        bot.add_view(TicketPanelView(bot))
        bot.add_view(CloseTicketView(bot))

    @commands.command(name="setup_tickets")
    @commands.has_any_role(*ADMIN_ROLES)
    @commands.cooldown(1, 30, commands.BucketType.user)
    async def setup_tickets(self, ctx):
        """Configure le panneau de tickets et candidatures dans le canal dédié."""
        channel = self.bot.get_channel(TICKET_CHANNEL_ID)
        if not channel:
            await ctx.send(f"❌ Canal introuvable (ID: {TICKET_CHANNEL_ID}).")
            return

        embed = discord.Embed(
            title="📩 Support & Recrutement — LanorTrad",
            description=(
                "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                "📩 **Créer un Ticket**\n"
                "Besoin d'aide, une question, un problème ?\n"
                "Ouvrez un ticket et un membre du staff vous répondra.\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                "📝 **Candidature**\n"
                "Vous souhaitez rejoindre l'équipe **LanorTrad** ?\n"
                "Remplissez le formulaire de candidature !\n\n"
                "**Postes disponibles :**\n"
                "• 🌍 Traducteur (JP → FR / EN → FR)\n"
                "• 🧹 Cleaner (nettoyage des scans)\n"
                "• ✏️ Éditeur (typesetting)\n"
                "• ✅ Checker (relecture qualité)\n"
                "• 🛡️ Modérateur (gestion communauté)\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━"
            ),
            color=COLORS["info"]
        )
        embed.set_footer(text="LanorTrad • Support & Recrutement")

        await channel.send(embed=embed, view=TicketPanelView(self.bot))
        await ctx.send(f"✅ Panneau de tickets configuré dans {channel.mention} !")
        logger.info(f"Panneau de tickets configuré par {ctx.author}")

    @commands.command(name="close_ticket")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def close_ticket(self, ctx):
        """Ferme le ticket actuel (admin ou auteur du ticket)."""
        thread = ctx.channel
        if not isinstance(thread, discord.Thread):
            await ctx.send("❌ Cette commande ne peut être utilisée que dans un ticket.")
            return

        # Vérifier les permissions
        user_roles = [role.id for role in ctx.author.roles]
        is_admin = any(role in user_roles for role in ADMIN_ROLES)
        is_owner = thread.owner_id == ctx.author.id

        if not is_admin and not is_owner:
            await ctx.send("❌ Vous n'avez pas la permission de fermer ce ticket.")
            return

        await ctx.send(
            embed=discord.Embed(
                title="🔒 Ticket Fermé",
                description="Ce ticket a été fermé et sera archivé.",
                color=discord.Color.red(),
                timestamp=datetime.datetime.now(datetime.timezone.utc)
            ).set_footer(text=f"Fermé par {ctx.author}")
        )

        await thread.edit(archived=True, locked=True)
        logger.info(f"Ticket '{thread.name}' fermé par {ctx.author} (commande)")


async def setup(bot):
    """Setup pour discord.py 2.0+"""
    await bot.add_cog(TicketSystem(bot))
    logging.info("✅ Cog TicketSystem chargé avec succès")
