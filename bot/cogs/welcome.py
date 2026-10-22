"""
Welcome — accueil auto des nouveaux membres
=============================================
Deux comportements selon le serveur :

  🩸 **info** — le nouveau reçoit un **MP** avec l'essentiel (site, alertes
     de sorties, support), le rôle « 📖 Lecteur », et une mention dans
     #bienvenue, #règles et #faq. Ces salons sont des pages de référence :
     les mentions s'effacent d'elles-mêmes au bout de
     WELCOME_PING_DELETE_AFTER minutes.

  🌍 **community** — embed de bienvenue bilingue posté dans #gates-of-lanor,
     avec renvoi vers la vérification.
"""
import logging
import re
from datetime import datetime, timedelta, timezone

import discord
from discord.ext import commands, tasks

from bot.config import (
    CHANNELS, ROLES, BASE_ROLES, COLOR_NEUTRAL, GUILD_ID, IS_INFO_SERVER, SITE,
    WELCOME_PING_CHANNELS, WELCOME_PING_DELETE_AFTER,
)

log = logging.getLogger("lanortrad.welcome")

# Un message par salon : le meme texte repete trois fois serait du bruit.
# {membre} = la mention · {alertes} {support} {recrutement} = les salons
MESSAGES_ARRIVEE = {
    "welcome": (
        "🩸 Bienvenue {membre} !\n"
        "Tu es le/la **{numero}e** à nous rejoindre. Tout est expliqué "
        "juste au-dessus — et pour être prévenu·e des sorties, ça se passe "
        "dans {alertes}."
    ),
    "rules": (
        "📜 {membre} — deux minutes de lecture, et on n'en reparle plus."
    ),
    "faq": (
        "❓ {membre} — la réponse à ta question est probablement déjà ici. "
        "Sinon, {support} est là pour ça."
    ),
}

# Le ménage reconnaît un ping d'arrivée à son texte : le modèle ci-dessus,
# champs compris. Les pages de référence que le bot poste dans ces mêmes
# salons n'y ressemblent pas, elles ne sont donc jamais touchées.
MOTIFS_ARRIVEE = {
    cle: re.compile(
        ".+?".join(re.escape(bout) for bout in re.split(r"\{\w+\}", modele)),
        re.S)
    for cle, modele in MESSAGES_ARRIVEE.items()
}


class Welcome(commands.Cog):
    """Accueil des nouveaux membres."""

    def __init__(self, bot):
        self.bot = bot

    async def cog_load(self):
        if IS_INFO_SERVER and WELCOME_PING_DELETE_AFTER:
            self.menage.start()

    def cog_unload(self):
        if self.menage.is_running():
            self.menage.cancel()

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
        # Mêmes rôles que /roles_base : un seul endroit décide de la liste
        roles = [member.guild.get_role(ROLES[k]) for k in BASE_ROLES if ROLES.get(k)]
        roles = [r for r in roles if r and r not in member.roles]
        if roles:
            try:
                await member.add_roles(*roles, reason="Arrivée sur le serveur")
            except discord.HTTPException as e:
                log.warning("Rôle de base non attribué à %s : %s", member, e)

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

        await self._ping_salons(member)

    async def _ping_salons(self, member: discord.Member):
        """Mentionne l'arrivant dans les salons de reference."""
        refs = {
            "membre": member.mention,
            "numero": member.guild.member_count,
            "alertes": self._mention(member.guild, "notifications", "#alertes-sorties"),
            "support": self._mention(member.guild, "tickets", "#support"),
            "recrutement": self._mention(member.guild, "recrutement", "#recrutement"),
        }

        for cle in WELCOME_PING_CHANNELS:
            ch_id = CHANNELS.get(cle)
            salon = member.guild.get_channel(ch_id) if ch_id else None
            modele = MESSAGES_ARRIVEE.get(cle)
            if salon is None or not modele:
                continue
            try:
                await salon.send(
                    modele.format(**refs),
                    allowed_mentions=discord.AllowedMentions(users=True),
                )
            except discord.HTTPException as e:
                log.warning("Ping d'arrivée impossible dans #%s : %s",
                            getattr(salon, "name", cle), e)

    # Pas de delete_after à l'envoi : il vit en mémoire, et un redémarrage
    # du bot l'oublie. On repasse plutôt dans les salons pour effacer ce qui
    # a fait son temps — les pings postés avant un redémarrage, ou avant
    # que ce ménage existe, partent donc aussi.
    @tasks.loop(minutes=10)
    async def menage(self):
        guild = self.bot.get_guild(GUILD_ID)
        if guild is None:
            return
        limite = (datetime.now(timezone.utc)
                  - timedelta(minutes=WELCOME_PING_DELETE_AFTER))

        for cle in WELCOME_PING_CHANNELS:
            ch_id = CHANNELS.get(cle)
            salon = guild.get_channel(ch_id) if ch_id else None
            motif = MOTIFS_ARRIVEE.get(cle)
            if not isinstance(salon, discord.TextChannel) or motif is None:
                continue

            def est_ping(m, motif=motif):
                return (m.author.id == self.bot.user.id
                        and motif.fullmatch(m.content) is not None)

            # Un par un (bulk=False) : une suppression groupée remonterait
            # dans les logs comme une purge. 200 messages lus par passage ;
            # s'il en reste au-delà, le passage suivant les atteindra.
            try:
                effaces = await salon.purge(
                    limit=200, before=limite, check=est_ping, bulk=False,
                    reason="Ping d'arrivée expiré")
            except discord.HTTPException as e:
                log.warning("Ménage des arrivées impossible dans #%s : %s",
                            salon.name, e)
                continue
            if effaces:
                log.info("%d ping(s) d'arrivée effacé(s) dans #%s",
                         len(effaces), salon.name)

    @menage.before_loop
    async def _avant_menage(self):
        await self.bot.wait_until_ready()

    @staticmethod
    def _mention(guild, cle, defaut):
        ch_id = CHANNELS.get(cle)
        salon = guild.get_channel(ch_id) if ch_id else None
        return salon.mention if salon else defaut

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
