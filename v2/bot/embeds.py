"""
Factory d'embeds — identité visuelle cohérente "Black Ink"
===========================================================
Centralise la construction des embeds pour que TOUT le bot ait le même
style : footer signé + icône du serveur, timestamp, couleur d'accent.

Usage :
    from bot.embeds import brand_embed
    embed = brand_embed(interaction.guild, title="…", description="…")
"""
import datetime

import discord

from bot.config import COLOR_NEUTRAL, SITE_URL, DISCORD_INVITE

FOOTER_TEXT = "LanorTrad · 黒墨 Black Ink Society"


def brand_embed(guild=None, *, title=None, description=None,
                color=COLOR_NEUTRAL, url=None, timestamp=True) -> discord.Embed:
    """Embed signé LanorTrad (footer + icône serveur + timestamp)."""
    embed = discord.Embed(title=title, description=description, color=color, url=url)
    if timestamp:
        embed.timestamp = datetime.datetime.now(datetime.timezone.utc)
    icon = guild.icon.url if (guild and guild.icon) else None
    embed.set_footer(text=FOOTER_TEXT, icon_url=icon)
    return embed


class LinkRow(discord.ui.View):
    """Rangée de boutons-liens (lecture / site / discord).

    Les boutons de style `link` n'ont pas de custom_id et fonctionnent
    indéfiniment sans persistance : on peut donc créer la vue à la volée.
    """

    def __init__(self, read_url: str, *, read_label="📖 Lire le chapitre",
                 site_url: str = None, invite_url: str = None):
        super().__init__(timeout=None)
        self.add_item(discord.ui.Button(label=read_label, url=read_url,
                                        style=discord.ButtonStyle.link))
        site = site_url or SITE_URL
        if site:
            self.add_item(discord.ui.Button(label="🌐 Site", url=site,
                                            style=discord.ButtonStyle.link))
        invite = invite_url or DISCORD_INVITE
        if invite:
            self.add_item(discord.ui.Button(label="💬 Discord", url=invite,
                                            style=discord.ButtonStyle.link))
