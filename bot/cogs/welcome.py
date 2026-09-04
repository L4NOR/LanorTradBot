"""
Welcome — accueil auto des nouveaux membres
=============================================
Deux comportements selon le serveur :

  🩸 **info** — le salon #bienvenue est une page de référence : on ne la
     pollue pas avec un message par arrivée. Le nouveau reçoit un **MP**
     avec l'essentiel (site, alertes de sorties, support), et le rôle
     « 📖 Lecteur » lui est attribué automatiquement.

  🌍 **community** — embed de bienvenue bilingue posté dans #gates-of-lanor,
     avec renvoi vers la vérification.
"""
import logging

import discord
from discord.ext import commands

from bot.config import (
    CHANNELS, ROLES, COLOR_NEUTRAL, IS_INFO_SERVER, SITE,
)

log = logging.getLogger("lanortrad.welcome")


class Welcome(commands.Cog):
    """Accueil des nouveaux membres."""

    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if member.bot:
            return
        if IS_INFO_SERVER:
            await self._welcome_info(member)
        else:
            await self._welcome_community(member)

    # ─────────────────────────────────────────────
    # Serveur informatif : MP + rôle lecteur
    # ─────────────────────────────────────────────
    async def _welcome_info(self, member: discord.Member):
        role_id = ROLES.get("member")
        if role_id:
            role = member.guild.get_role(role_id)
            if role:
                try:
                    await member.add_roles(role, reason="Arrivée sur le serveur")
                except discord.HTTPException as e:
                    log.warning("Rôle lecteur non attribué à %s : %s", member, e)

        def ref(key, fallback):
            ch_id = CHANNELS.get(key)
            channel = member.guild.get_channel(ch_id) if ch_id else None
            return channel.mention if channel else fallback

        text = (
            f"# 🩸 Bienvenue chez **LanorTrad**\n\n"
            f"Salut {member.display_name} ! Ce serveur sert à **trois choses** :\n\n"
            f"🔔 **Être prévenu·e des sorties**\n"
            f"Choisis tes séries dans {ref('notifications', '#alertes-sorties')}.\n\n"
            f"🎫 **Nous parler**\n"
            f"Une question, un souci, une faute repérée → "
            f"{ref('tickets', '#support')}.\n\n"
            f"📋 **Rejoindre l'équipe**\n"
            f"On recrute → {ref('recrutement', '#recrutement')}.\n\n"
            f"**Pour lire et discuter, tout est sur le site :**\n"
            f"📚 Catalogue → {SITE['catalogue']}\n"
            f"📅 Planning → {SITE['planning']}\n"
            f"💬 Forum → {SITE['forum']}\n\n"
            f"À très vite 🩸"
        )
        try:
            await member.send(text)
        except discord.HTTPException:
            log.info("MP de bienvenue refusé par %s (MP fermés).", member)

    # ─────────────────────────────────────────────
    # Serveur communautaire : embed public
    # ─────────────────────────────────────────────
    async def _welcome_community(self, member: discord.Member):
        welcome_id = CHANNELS.get("welcome")
        if not welcome_id:
            return
        channel = member.guild.get_channel(welcome_id)
        if not channel:
            return

        description = (
            f"🩸 **{member.mention}** vient d'arriver.\n"
            f"🇫🇷 **Bienvenue dans LanorTrad !**\n"
            f"🇬🇧 **Welcome to LanorTrad!**\n\n"
            f"Nous sommes maintenant **{member.guild.member_count}** membres."
        )

        verif_id = CHANNELS.get("verification")
        if verif_id:
            verif = member.guild.get_channel(verif_id)
            if verif:
                description += (
                    f"\n\n⚔ Passe par {verif.mention} pour débloquer le serveur "
                    f"· head to {verif.mention} to unlock the server."
                )

        embed = discord.Embed(description=description, color=COLOR_NEUTRAL)
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(text="Compte créé · Account created")
        embed.timestamp = member.joined_at

        try:
            await channel.send(embed=embed)
        except discord.HTTPException as e:
            log.warning("Welcome non posté : %s", e)


async def setup(bot):
    await bot.add_cog(Welcome(bot))
