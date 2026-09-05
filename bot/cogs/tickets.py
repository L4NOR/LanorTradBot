"""
Tickets — support privé via threads
=====================================
/ticket_setup (admin) poste un panneau avec un menu de catégories.
Un membre choisit une catégorie → un thread PRIVÉ est créé dans #tickets,
il y est ajouté, et un bouton "Fermer" permet de clôturer.

Vues persistantes (panneau + bouton fermer) → survivent aux redémarrages.
"""
import logging

import discord
from discord import app_commands
from discord.ext import commands

from bot.config import (
    GUILD_ID, CHANNELS, TICKET_TYPES, TICKET_PING_ROLE_ID,
    COLOR_NEUTRAL, COLOR_SUCCESS,
)
from bot.embeds import brand_embed
from bot.storage import JSONStore

log = logging.getLogger("lanortrad.tickets")

GUILD = discord.Object(id=GUILD_ID) if GUILD_ID else None

_TYPE_BY_KEY = {key: (label, emoji, desc) for (key, label, emoji, desc) in TICKET_TYPES}

# Store partagé : thread_id (str) → {"user": id, "type": key}
_store = JSONStore("tickets.json", default={"open": {}})


async def _log_ticket(bot, guild, text: str):
    ch_id = CHANNELS.get("bot_logs")
    if not ch_id:
        return
    channel = guild.get_channel(ch_id)
    if channel:
        try:
            await channel.send(text)
        except discord.HTTPException:
            pass


class CloseTicketView(discord.ui.View):
    """Bouton persistant de fermeture de ticket."""

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🔒 Fermer le ticket", style=discord.ButtonStyle.danger,
                       custom_id="lanorbot:ticket_close")
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        thread = interaction.channel
        if not isinstance(thread, discord.Thread):
            await interaction.response.send_message("❌ Pas dans un ticket.", ephemeral=True)
            return

        entry = _store.get("open", {}).get(str(thread.id))
        is_opener = entry and entry.get("user") == interaction.user.id
        is_staff = interaction.user.guild_permissions.manage_threads
        if not (is_opener or is_staff):
            await interaction.response.send_message(
                "🚫 Seul l'auteur du ticket ou le staff peut le fermer.", ephemeral=True
            )
            return

        await interaction.response.send_message(
            f"🔒 Ticket fermé par {interaction.user.mention}."
        )
        _store.get("open", {}).pop(str(thread.id), None)
        _store.save()
        await _log_ticket(interaction.client, interaction.guild,
                          f"🔒 Ticket `{thread.name}` fermé par {interaction.user}.")
        try:
            await thread.edit(archived=True, locked=True)
        except discord.HTTPException:
            pass


class TicketTypeSelect(discord.ui.Select):
    """Menu de choix de catégorie de ticket."""

    def __init__(self):
        options = [
            discord.SelectOption(label=label, value=key, emoji=emoji, description=desc[:100])
            for (key, label, emoji, desc) in TICKET_TYPES
        ]
        super().__init__(
            placeholder="Ouvrir un ticket · Open a ticket…",
            min_values=1, max_values=1, options=options,
            custom_id="lanorbot:ticket_open",
        )

    async def callback(self, interaction: discord.Interaction):
        key = self.values[0]
        label, emoji, _ = _TYPE_BY_KEY.get(key, (key, "🎫", ""))

        tickets_id = CHANNELS.get("tickets")
        channel = interaction.guild.get_channel(tickets_id) if tickets_id else None
        if channel is None:
            await interaction.response.send_message(
                "❌ Salon tickets non configuré.", ephemeral=True)
            return

        # Anti-doublon : un ticket ouvert max par membre
        for tid, e in list(_store.get("open", {}).items()):
            if e.get("user") == interaction.user.id:
                existing = interaction.guild.get_thread(int(tid))
                if existing and not existing.archived:
                    await interaction.response.send_message(
                        f"⚠️ Tu as déjà un ticket ouvert : {existing.mention}", ephemeral=True)
                    return
                _store.get("open", {}).pop(tid, None)  # nettoyage des périmés

        await interaction.response.defer(ephemeral=True, thinking=True)

        try:
            thread = await channel.create_thread(
                name=f"{emoji}・{label.lower()}-{interaction.user.name}"[:100],
                type=discord.ChannelType.private_thread,
                invitable=False,
                reason=f"Ticket {key} de {interaction.user}",
            )
            await thread.add_user(interaction.user)
        except discord.Forbidden:
            await interaction.followup.send(
                "❌ Je n'ai pas la permission de créer des threads privés ici.", ephemeral=True)
            return
        except discord.HTTPException as ex:
            log.error("Création ticket KO : %s", ex)
            await interaction.followup.send("❌ Création du ticket impossible.", ephemeral=True)
            return

        _store.setdefault("open", {})[str(thread.id)] = {"user": interaction.user.id, "type": key}
        _store.save()

        embed = brand_embed(
            interaction.guild,
            title=f"{emoji} Ticket · {label}",
            description=(
                f"Bonjour {interaction.user.mention} 👋\n"
                "Explique ta demande en détail, le staff va te répondre ici.\n\n"
                "🇬🇧 Describe your request — staff will reply shortly."
            ),
            color=COLOR_NEUTRAL,
        )
        ping = ""
        if TICKET_PING_ROLE_ID:
            ping = f"<@&{TICKET_PING_ROLE_ID}>"
        await thread.send(
            content=f"{interaction.user.mention} {ping}".strip(),
            embed=embed,
            view=CloseTicketView(),
            allowed_mentions=discord.AllowedMentions(users=True, roles=True),
        )
        await _log_ticket(interaction.client, interaction.guild,
                          f"🎫 Ticket `{key}` ouvert par {interaction.user} → {thread.mention}")
        await interaction.followup.send(f"✅ Ton ticket est ouvert : {thread.mention}", ephemeral=True)


class TicketPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketTypeSelect())


class Tickets(commands.Cog):
    """Système de tickets via threads privés."""

    def __init__(self, bot):
        self.bot = bot
        self.bot.add_view(TicketPanelView())
        self.bot.add_view(CloseTicketView())

    @app_commands.command(name="ticket_setup",
                          description="(Admin) Poste le panneau d'ouverture de tickets")
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.bot_has_permissions(create_private_threads=True)
    @app_commands.guilds(GUILD)
    async def ticket_setup(self, interaction: discord.Interaction):
        types_txt = "\n".join(f"{e} **{l}** — {d}" for (k, l, e, d) in TICKET_TYPES)
        embed = brand_embed(
            interaction.guild,
            title="🎫 Centre de support · Support center",
            description=(
                "Choisis une catégorie dans le menu pour ouvrir un **ticket privé**.\n"
                "Pick a category below to open a **private ticket**.\n\n"
                + types_txt
            ),
            color=COLOR_NEUTRAL,
        )
        await interaction.channel.send(embed=embed, view=TicketPanelView())
        await interaction.response.send_message("✅ Panneau tickets posté.", ephemeral=True)

    @app_commands.command(name="close", description="Ferme le ticket courant")
    @app_commands.guilds(GUILD)
    async def close(self, interaction: discord.Interaction):
        thread = interaction.channel
        if not isinstance(thread, discord.Thread) or str(thread.id) not in _store.get("open", {}):
            await interaction.response.send_message(
                "❌ Cette commande s'utilise dans un ticket ouvert.", ephemeral=True)
            return
        entry = _store.get("open", {}).get(str(thread.id))
        if not (entry.get("user") == interaction.user.id
                or interaction.user.guild_permissions.manage_threads):
            await interaction.response.send_message(
                "🚫 Seul l'auteur ou le staff peut fermer ce ticket.", ephemeral=True)
            return
        await interaction.response.send_message(f"🔒 Ticket fermé par {interaction.user.mention}.")
        _store.get("open", {}).pop(str(thread.id), None)
        _store.save()
        await _log_ticket(self.bot, interaction.guild,
                          f"🔒 Ticket `{thread.name}` fermé par {interaction.user}.")
        try:
            await thread.edit(archived=True, locked=True)
        except discord.HTTPException:
            pass


async def setup(bot):
    await bot.add_cog(Tickets(bot))
