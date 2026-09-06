"""
Statut du bot — ce qui se passe vraiment, pas une ligne figée
==============================================================
La liste des membres est la première chose qu'on voit d'un serveur. Le bot
y affichait toujours `lanortrad.com` ; il y raconte maintenant l'atelier.

Le statut tourne entre plusieurs phrases, régénérées à chaque passage :

    Regarde  l'atelier — 🧽 2 · 💬 1 · ✍️ 1
    Regarde  🎉 Tougen Anki 58, prêt à sortir
    Regarde  📖 128 lecteurs
    Regarde  lanortrad.com

Deux sources, dans cet ordre : les fiches Discord si l'équipe en tient,
sinon l'atelier du site. Aucune des deux ne répond ? On retombe sur
l'adresse du site — le statut ne reste jamais vide.

`discord.ActivityType.watching` est volontaire : le texte s'affiche
derrière « Regarde », ce qui rend chaque phrase lisible. Le statut
personnalisé, plus joli, n'est pas garanti pour les bots.
"""
import logging

import discord
from discord.ext import commands, tasks

from bot import site as sitelib
from bot.config import (
    GUILD_ID, MANGAS, SITE_URL, PRESENCE_ENABLED, PRESENCE_INTERVALLE,
)

log = logging.getLogger("lanortrad.presence")

REPLI = SITE_URL.replace("https://", "").replace("http://", "")

# Étapes de travail, sans « sortie » qui est un état, pas un chantier.
ETAPES_TRAVAIL = [e[0] for e in sitelib.STEPS][:-1]


def _nom_court(cle_ou_nom: str) -> str:
    """Nom de série lisible, que l'on parte d'une clé ou d'un nom du site."""
    info = MANGAS.get(cle_ou_nom)
    if info:
        return info["name"]
    return cle_ou_nom


class Presence(commands.Cog):
    """Le statut du bot, mis à jour tout seul."""

    def __init__(self, bot):
        self.bot = bot
        self._index = 0

    async def cog_load(self):
        if PRESENCE_ENABLED:
            self.rotation.start()

    def cog_unload(self):
        if self.rotation.is_running():
            self.rotation.cancel()

    # ─────────────────────────────────────────────
    # De quoi parler
    # ─────────────────────────────────────────────
    def _depuis_fiches(self):
        """(compteur par étape, chapitres prêts) d'après les fiches Discord."""
        cog = self.bot.get_cog("Atelier")
        if cog is None:
            return {}, []
        compte, prets = {}, []
        for fiche in cog._store.get("fiches", {}).values():
            if fiche.get("termine"):
                prets.append(f"{_nom_court(fiche.get('manga'))} "
                             f"{fiche.get('chapitre')}")
                continue
            etape = fiche.get("etape")
            if etape in ETAPES_TRAVAIL:
                compte[etape] = compte.get(etape, 0) + 1
        return compte, prets

    def _depuis_site(self):
        """Même chose, lue sur le site — utile tant qu'aucune fiche n'existe."""
        sync = self.bot.get_cog("SiteSync")
        data = getattr(sync, "data", None)
        if data is None:
            return {}, []
        compte, prets = {}, []
        for item in data.workshop():
            etape = item.get("step")
            if etape == "sortie":
                prets.append(f"{_nom_court(item.get('series'))} "
                             f"{item.get('chapter')}")
            elif etape in ETAPES_TRAVAIL:
                compte[etape] = compte.get(etape, 0) + 1
        return compte, prets

    def _phrases(self) -> list:
        compte, prets = self._depuis_fiches()
        if not compte and not prets:
            compte, prets = self._depuis_site()

        phrases = []

        if compte:
            detail = " · ".join(
                f"{sitelib.STEP_INFO[e][2]} {compte[e]}"
                for e in ETAPES_TRAVAIL if compte.get(e))
            total = sum(compte.values())
            phrases.append(f"l'atelier — {detail}")
            phrases.append(
                f"{total} chapitre{'s' if total > 1 else ''} en fabrication")

        for pret in prets[:2]:
            phrases.append(f"🎉 {pret}, prêt à sortir")

        guild = self.bot.get_guild(GUILD_ID)
        if guild is not None and guild.member_count:
            phrases.append(f"📖 {guild.member_count} lecteurs")

        phrases.append(REPLI)
        return phrases

    # ─────────────────────────────────────────────
    # Rotation
    # ─────────────────────────────────────────────
    @tasks.loop(minutes=PRESENCE_INTERVALLE)
    async def rotation(self):
        try:
            phrases = self._phrases()
        except Exception as e:                     # jamais au prix du bot
            log.warning("Statut non calcule : %s", e)
            phrases = [REPLI]

        texte = phrases[self._index % len(phrases)][:128]
        self._index += 1

        try:
            await self.bot.change_presence(
                activity=discord.Activity(
                    type=discord.ActivityType.watching, name=texte),
                status=discord.Status.online)
        except discord.HTTPException as e:
            log.warning("Statut non applique : %s", e)

    @rotation.before_loop
    async def _avant_rotation(self):
        await self.bot.wait_until_ready()


async def setup(bot):
    await bot.add_cog(Presence(bot))
