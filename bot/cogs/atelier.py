"""
Atelier — la chaîne de fabrication d'un chapitre
==================================================
Le site montre l'avancement au public ; ce cog fait tourner l'atelier côté
équipe. Un chapitre = **une fiche** qui vit dans le salon d'atelier et se
réécrit à chaque étape, plutôt que cinq messages empilés qu'il faut
recoller mentalement.

  /atelier_raws    — ouvre la fiche : les pages japonaises sont là
  /atelier_clean   — le clean est fait      → au tour de la traduction
  /atelier_trad    — la traduction est faite → au tour de l'édition
  /atelier_edit    — l'édition est faite     → au tour du Q-check
  /atelier_qcheck  — le Q-check est fait     → le chapitre est prêt à sortir

  /atelier_fiche   — revoir une fiche
  /atelier_liste   — tout ce qui est en cours, par série
  /atelier_etape   — (staff) corriger l'étape d'une fiche
  /atelier_retirer — supprimer une fiche

Les étapes sont celles du site (`bot/site.py` · STEPS) : le vocabulaire est
le même sur le site, dans les embeds et dans la bouche des gens.

Trois principes :

  • **Chaque étape appartient à son métier.** Un cleaner ne valide pas une
    traduction ; la commande refuse poliment plutôt que de laisser passer.
  • **Une étape validée prévient la suivante.** Le rôle concerné est pingé
    avec un lien vers la fiche — personne n'a à surveiller un salon.
  • **Tout est faisable au bouton.** Prendre, terminer, rendre : les
    commandes ne servent qu'à joindre un aperçu ou une note.

Les fiches survivent aux redémarrages (`data/atelier.json`), boutons compris.
"""
import base64
import datetime
import io
import logging
import time

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands, tasks

from bot import site as sitelib
from bot import siteexport
from bot.config import (
    GUILD_ID, MANGAS, CHANNELS, ROLES, SITE_URL,
    COLOR_NEUTRAL, COLOR_SUCCESS, COLOR_WARNING, COLOR_ERROR,
    ATELIER_CHANNEL, ATELIER_ANNONCE_ETAPE,
    ATELIER_ETAPE_ROLES, ATELIER_ROLES_JOKER,
    ATELIER_RELANCE, ATELIER_RELANCE_JOURS, ATELIER_RELANCE_INTERVALLE,
    ATELIER_RELANCE_MAX,
    ATELIER_SUIVI_PUBLIC, ATELIER_SUIVI_CHANNEL, ATELIER_SUIVI_ROLE,
    ATELIER_SUIVI_ETAPES,
    SITE_REPO, SITE_REPO_BRANCH, SITE_REPO_TOKEN,
    manga_url,
)
from bot.embeds import brand_embed
from bot.storage import JSONStore

log = logging.getLogger("lanortrad.atelier")

GUILD = discord.Object(id=GUILD_ID) if GUILD_ID else None

# Les étapes du site, dans l'ordre : pages → clean → trad → edit → qcheck → sortie
ETAPES = [e[0] for e in sitelib.STEPS]
ETAPE_INFO = sitelib.STEP_INFO          # id → (id, libellé, emoji, description)
DERNIERE = ETAPES[-1]                   # "sortie" : la fiche est alors terminée

MANGA_CHOICES = [
    app_commands.Choice(name=f"{m['emoji']} {m['name']}", value=cle)
    for cle, m in MANGAS.items()
]

EXTENSIONS_OK = ("png", "jpg", "jpeg", "webp", "gif")


# ═══════════════════════════════════════════════════════
# Petits outils
# ═══════════════════════════════════════════════════════

def _suivante(etape: str):
    """L'étape d'après, ou None si on est au bout."""
    try:
        return ETAPES[ETAPES.index(etape) + 1]
    except (ValueError, IndexError):
        return None


def _libelle(etape: str) -> str:
    info = ETAPE_INFO.get(etape)
    return f"{info[2]} {info[1]}" if info else etape


def _nom_manga(cle: str) -> str:
    info = MANGAS.get(cle, {})
    return f"{info.get('emoji', '📖')} {info.get('name', cle)}"


def _peut_valider(member: discord.Member, etape: str) -> bool:
    """Le métier de l'étape, ou un rôle passe-partout (staff)."""
    if member.guild_permissions.administrator:
        return True
    attendus = set(ATELIER_ETAPE_ROLES.get(etape, ())) | set(ATELIER_ROLES_JOKER)
    ids = {ROLES.get(c) for c in attendus} - {None}
    return any(r.id in ids for r in member.roles)


def _role_de(guild, etape: str):
    """Le rôle métier d'une étape (le premier listé), s'il existe."""
    for cle in ATELIER_ETAPE_ROLES.get(etape, ()):
        role_id = ROLES.get(cle)
        if role_id:
            role = guild.get_role(role_id)
            if role is not None:
                return role
    return None


def _cle(manga: str, chapitre: str) -> str:
    return f"{manga}:{str(chapitre).strip()}"


def _immobile_depuis(fiche: dict) -> float:
    """Jours écoulés depuis le dernier mouvement de la fiche.

    Prise de l'étape en cours si quelqu'un l'a prise, sinon dernière
    étape validée, sinon ouverture. Sert au ⏳ et à la relance.
    """
    faites = (fiche.get("etapes") or {}).values()
    dernier = max(fiche.get("pris_le") or 0,
                  max((e.get("le", 0) for e in faites), default=0))
    # `ouvert_le` ne bouge jamais : il ne sert que de repli pour une fiche
    # toute neuve, sinon il ferait passer une fiche endormie pour active.
    if not dernier:
        dernier = fiche.get("ouvert_le") or 0
    return (time.time() - dernier) / 86400 if dernier else 0.0


# ═══════════════════════════════════════════════════════
# Les boutons de la fiche
# ═══════════════════════════════════════════════════════

class FicheView(discord.ui.View):
    """Prendre · terminer · rendre — persistants entre deux redémarrages."""

    def __init__(self):
        super().__init__(timeout=None)

    def _contexte(self, interaction):
        """(cog, fiche) ou (None, None) si le message n'est plus suivi."""
        cog = interaction.client.get_cog("Atelier")
        if cog is None:
            return None, None
        return cog, cog.fiche_du_message(interaction.message.id)

    async def _refus(self, interaction, texte):
        await interaction.response.send_message(texte, ephemeral=True)

    @discord.ui.button(label="Je prends", emoji="🙋",
                       style=discord.ButtonStyle.primary,
                       custom_id="lanortrad:atelier_prendre")
    async def prendre(self, interaction: discord.Interaction, _b):
        cog, fiche = self._contexte(interaction)
        if fiche is None:
            return await self._refus(interaction, "❌ Cette fiche n'est plus suivie.")
        if fiche.get("termine"):
            return await self._refus(interaction, "✅ Ce chapitre est déjà terminé.")

        etape = fiche["etape"]
        if not _peut_valider(interaction.user, etape):
            return await self._refus(
                interaction,
                f"❌ L'étape **{_libelle(etape)}** est réservée à son métier.\n"
                f"On recrute, d'ailleurs : {SITE_URL}/equipe")

        deja = fiche.get("pris_par")
        if deja and deja != interaction.user.id:
            membre = interaction.guild.get_member(deja)
            if membre is not None:
                return await self._refus(
                    interaction,
                    f"⚠️ {membre.display_name} est déjà dessus. "
                    "Il faut qu'iel rende d'abord.")

        fiche["pris_par"] = interaction.user.id
        fiche["pris_le"] = time.time()
        cog.sauver()
        await cog.rafraichir(interaction, fiche)
        log.info("Atelier : %s pris par %s", fiche["cle"], interaction.user)

    @discord.ui.button(label="J'ai terminé", emoji="✅",
                       style=discord.ButtonStyle.success,
                       custom_id="lanortrad:atelier_fini")
    async def fini(self, interaction: discord.Interaction, _b):
        cog, fiche = self._contexte(interaction)
        if fiche is None:
            return await self._refus(interaction, "❌ Cette fiche n'est plus suivie.")
        if fiche.get("termine"):
            return await self._refus(interaction, "✅ Ce chapitre est déjà terminé.")

        etape = fiche["etape"]
        if not _peut_valider(interaction.user, etape):
            return await self._refus(
                interaction,
                f"❌ Seul le métier **{_libelle(etape)}** peut valider cette étape.")

        await interaction.response.defer()
        await cog.avancer(interaction.guild, fiche, etape, interaction.user)
        await cog.rafraichir(interaction, fiche, deja_repondu=True)

    @discord.ui.button(label="Je rends", emoji="↩️",
                       style=discord.ButtonStyle.secondary,
                       custom_id="lanortrad:atelier_rendre")
    async def rendre(self, interaction: discord.Interaction, _b):
        cog, fiche = self._contexte(interaction)
        if fiche is None:
            return await self._refus(interaction, "❌ Cette fiche n'est plus suivie.")

        preneur = fiche.get("pris_par")
        if preneur is None:
            return await self._refus(interaction, "ℹ️ Personne n'est dessus.")
        if preneur != interaction.user.id and not _peut_valider(
                interaction.user, DERNIERE):
            return await self._refus(
                interaction,
                "❌ Seule la personne qui a pris l'étape (ou le staff) peut rendre.")

        fiche["pris_par"] = None
        fiche["pris_le"] = None
        fiche["relances"] = 0
        fiche["relance_le"] = None
        cog.sauver()
        await cog.rafraichir(interaction, fiche)
        log.info("Atelier : %s rendu par %s", fiche["cle"], interaction.user)


# ═══════════════════════════════════════════════════════
# Le cog
# ═══════════════════════════════════════════════════════

class Atelier(commands.Cog):
    """Suivi de la fabrication, étape par étape."""

    def __init__(self, bot):
        self.bot = bot
        self._store = JSONStore("atelier.json", default={"fiches": {}, "messages": {}})
        self._migrer()

    async def cog_load(self):
        self.bot.add_view(FicheView())
        if ATELIER_RELANCE:
            self.relance.start()

    def cog_unload(self):
        if self.relance.is_running():
            self.relance.cancel()

    # ─────────────────────────────────────────────
    # État
    # ─────────────────────────────────────────────
    def _migrer(self):
        """Reprend les « lots » de la première version en fiches."""
        lots = self._store.get("lots")
        if not lots:
            return
        fiches = self._store.setdefault("fiches", {})
        index = self._store.setdefault("messages", {})
        for msg_id, lot in lots.items():
            cle = _cle(lot.get("manga", ""), lot.get("chapitre", ""))
            if cle in fiches:
                continue
            fiches[cle] = {
                "cle": cle,
                "manga": lot.get("manga"),
                "chapitre": str(lot.get("chapitre")),
                "pages": lot.get("pages"),
                "etape": "clean",
                "termine": False,
                "salon": lot.get("salon"),
                "message": lot.get("message"),
                "url": lot.get("url"),
                "image": "raw1.png",
                "ouvert_le": lot.get("depose_le", time.time()),
                "pris_par": lot.get("pris_par"),
                "pris_le": lot.get("pris_le"),
                "etapes": {
                    "pages": {"par": lot.get("auteur"),
                              "le": lot.get("depose_le", time.time()),
                              "note": None, "lien": None},
                },
            }
            index[str(msg_id)] = cle
        self._store.pop("lots", None)
        self._store.save()
        log.info("Atelier : %d lot(s) migre(s) en fiches", len(lots))

    def sauver(self):
        self._store.save()

    def fiche(self, manga: str, chapitre: str):
        return self._store.get("fiches", {}).get(_cle(manga, chapitre))

    def fiche_du_message(self, message_id: int):
        cle = self._store.get("messages", {}).get(str(message_id))
        return self._store.get("fiches", {}).get(cle) if cle else None

    def en_cours(self, manga: str = None):
        fiches = [f for f in self._store.get("fiches", {}).values()
                  if not f.get("termine")]
        if manga:
            fiches = [f for f in fiches if f.get("manga") == manga]
        return sorted(fiches, key=lambda f: f.get("ouvert_le", 0))

    # ─────────────────────────────────────────────
    # L'embed de la fiche
    # ─────────────────────────────────────────────
    def _progression(self, fiche) -> str:
        faites = fiche.get("etapes", {})
        termine = fiche.get("termine")
        cases = []
        for eid in ETAPES:
            emoji = ETAPE_INFO[eid][2]
            if eid in faites or (termine and eid == DERNIERE):
                cases.append(f"{emoji}✅")
            elif not termine and eid == fiche.get("etape"):
                cases.append(f"**{emoji}**")
            else:
                cases.append(emoji)
        return " → ".join(cases)

    def _embed(self, guild, fiche) -> discord.Embed:
        manga = fiche.get("manga", "")
        termine = fiche.get("termine")
        etape = fiche.get("etape")
        info = ETAPE_INFO.get(etape, (etape, etape, "•", ""))

        embed = brand_embed(
            guild,
            title=f"{_nom_manga(manga)} — chapitre {fiche.get('chapitre')}",
            description=self._progression(fiche),
            color=COLOR_SUCCESS if termine else COLOR_NEUTRAL,
            url=manga_url(manga),
        )

        if fiche.get("pages"):
            embed.add_field(name="📄 Pages", value=f"**{fiche['pages']}** pages",
                            inline=True)

        if fiche.get("eta"):
            embed.add_field(name="🎯 Sortie visée",
                            value=f"**{fiche['eta']}**", inline=True)

        if termine:
            embed.add_field(
                name="🎉 Terminé",
                value="Prêt à sortir — `/release` pour publier.", inline=True)
        else:
            embed.add_field(
                name="🔄 Étape en cours",
                value=f"{info[2]} **{info[1]}**"
                      + (f"\n*{info[3]}*" if info[3] else ""),
                inline=False)
            preneur = fiche.get("pris_par")
            dort = _immobile_depuis(fiche)
            valeur = (f"<@{preneur}> · <t:{int(fiche.get('pris_le') or 0)}:R>"
                      if preneur else "*personne pour l'instant*")
            if dort >= ATELIER_RELANCE_JOURS:
                # Factuel, sans désigner de coupable : l'équipe voit que
                # ça dort, la personne reçoit le rappel en privé.
                valeur += f"\n⏳ *rien n'a bougé depuis {dort:.0f} jours*"
            embed.add_field(name="🙋 Sur le coup", value=valeur, inline=True)

        faites = fiche.get("etapes", {})
        if faites:
            lignes = []
            for eid in ETAPES:
                fait = faites.get(eid)
                if not fait:
                    continue
                ligne = f"{ETAPE_INFO[eid][2]} **{ETAPE_INFO[eid][1]}** — <@{fait['par']}>"
                if fait.get("lien"):
                    ligne += f" · [fichier]({fait['lien']})"
                if fait.get("note"):
                    ligne += f"\n> {fait['note']}"
                lignes.append(ligne)
            embed.add_field(name="🧾 Parcours", value="\n".join(lignes), inline=False)

        if fiche.get("image"):
            embed.set_image(url=f"attachment://{fiche['image']}")
        return embed

    # ─────────────────────────────────────────────
    # Mise à jour du message de la fiche
    # ─────────────────────────────────────────────
    async def rafraichir(self, interaction, fiche, *, deja_repondu=False):
        """Réécrit la fiche à partir de l'interaction qui vient d'avoir lieu."""
        embed = self._embed(interaction.guild, fiche)
        try:
            if deja_repondu:
                await interaction.message.edit(embed=embed, view=FicheView())
            else:
                await interaction.response.edit_message(embed=embed, view=FicheView())
        except discord.HTTPException as e:
            log.warning("Fiche %s non rafraichie : %s", fiche.get("cle"), e)

    async def _reecrire(self, guild, fiche, fichier=None):
        """Réécrit la fiche depuis l'extérieur (commande slash)."""
        salon = guild.get_channel(fiche.get("salon") or 0)
        if salon is None:
            return None
        try:
            message = await salon.fetch_message(fiche["message"])
        except (discord.NotFound, discord.HTTPException):
            return None

        if fichier is not None:
            fiche["image"] = fichier.filename
        embed = self._embed(guild, fiche)
        try:
            if fichier is not None:
                await message.edit(embed=embed, attachments=[fichier],
                                   view=FicheView())
            else:
                await message.edit(embed=embed, view=FicheView())
        except discord.HTTPException as e:
            log.warning("Fiche %s non reecrite : %s", fiche.get("cle"), e)
        return message

    # ─────────────────────────────────────────────
    # Avancer d'une étape
    # ─────────────────────────────────────────────
    async def avancer(self, guild, fiche, etape, auteur, *, note=None, lien=None):
        """Valide `etape`, bascule sur la suivante, prévient le métier concerné."""
        fiche.setdefault("etapes", {})[etape] = {
            "par": auteur.id, "le": time.time(), "note": note, "lien": lien,
        }
        suivante = _suivante(etape)
        fiche["pris_par"] = None
        fiche["pris_le"] = None
        fiche["relances"] = 0          # la fiche a bougé : on repart à zéro
        fiche["relance_le"] = None

        if suivante is None or suivante == DERNIERE:
            fiche["etape"] = DERNIERE
            fiche["termine"] = True
        else:
            fiche["etape"] = suivante
        self.sauver()

        log.info("Atelier : %s — %s valide par %s", fiche["cle"], etape, auteur)
        await self._prevenir(guild, fiche)
        await self._suivi_public(guild, fiche)

    async def _prevenir(self, guild, fiche):
        """Une ligne dans le salon pour passer le relais."""
        if not ATELIER_ANNONCE_ETAPE:
            return
        salon = guild.get_channel(fiche.get("salon") or 0)
        if salon is None:
            return

        titre = f"{_nom_manga(fiche['manga'])} ch. {fiche['chapitre']}"
        lien = fiche.get("url", "")

        if fiche.get("termine"):
            texte = (f"🎉 **{titre}** a passé le Q-check — prêt à sortir.\n"
                     f"`/release` quand tu veux. {lien}")
            mentions = discord.AllowedMentions.none()
        else:
            etape = fiche["etape"]
            role = _role_de(guild, etape)
            info = ETAPE_INFO[etape]
            qui = role.mention if role else f"**{info[1]}**"
            texte = (f"{qui} — {info[2]} **{titre}** attend l'étape "
                     f"**{info[1]}**.\n{lien}")
            mentions = discord.AllowedMentions(roles=True)

        try:
            await salon.send(texte, allowed_mentions=mentions)
        except discord.HTTPException as e:
            log.warning("Relais %s non envoye : %s", fiche.get("cle"), e)

    # ─────────────────────────────────────────────
    # Suivi public : les lecteurs voient avancer
    # ─────────────────────────────────────────────
    async def _suivi_public(self, guild, fiche):
        """Une ligne pour les lecteurs abonnés, sans rien d'interne.

        Ni note d'atelier, ni nom d'équipier : le public suit un chapitre,
        pas les gens qui le fabriquent.
        """
        if not ATELIER_SUIVI_PUBLIC:
            return
        etape = fiche.get("etape")
        if etape not in ATELIER_SUIVI_ETAPES:
            return

        salon_id = CHANNELS.get(ATELIER_SUIVI_CHANNEL)
        salon = guild.get_channel(salon_id) if salon_id else None
        if salon is None:
            return

        role_id = ROLES.get(ATELIER_SUIVI_ROLE)
        role = guild.get_role(role_id) if role_id else None
        info = ETAPE_INFO.get(etape, (etape, etape, "•", ""))
        titre = f"{_nom_manga(fiche['manga'])} **ch. {fiche['chapitre']}**"

        if fiche.get("termine"):
            corps = (f"\U0001f389 {titre} est **bouclé**. "
                     "Il ne reste plus qu'à le mettre en ligne.")
        else:
            restantes = len(ETAPES) - 1 - ETAPES.index(etape)
            reste = ("dernière ligne droite" if restantes <= 1
                     else f"encore {restantes} étapes avant la sortie")
            corps = (f"{info[2]} {titre} passe en **{info[1]}**.\n"
                     f"*{info[3]}*\n→ {reste}.")

        texte = (f"{role.mention}\n{corps}" if role else corps)
        try:
            await salon.send(
                texte, allowed_mentions=discord.AllowedMentions(roles=True))
        except discord.HTTPException as e:
            log.warning("Suivi public %s non envoye : %s", fiche.get("cle"), e)

    # ─────────────────────────────────────────────
    # Relance douce — en privé, jamais en public
    # ─────────────────────────────────────────────
    @tasks.loop(hours=ATELIER_RELANCE_INTERVALLE)
    async def relance(self):
        if not ATELIER_RELANCE:
            return
        guild = self.bot.get_guild(GUILD_ID)
        if guild is None:
            return

        for fiche in list(self._store.get("fiches", {}).values()):
            if fiche.get("termine") or not fiche.get("pris_par"):
                continue
            if _immobile_depuis(fiche) < ATELIER_RELANCE_JOURS:
                continue
            if fiche.get("relances", 0) >= ATELIER_RELANCE_MAX:
                continue
            # Un rappel par période, pas un par passage de boucle.
            depuis_rappel = (time.time() - (fiche.get("relance_le") or 0)) / 86400
            if fiche.get("relance_le") and depuis_rappel < ATELIER_RELANCE_JOURS:
                continue

            membre = guild.get_member(fiche["pris_par"])
            if membre is None:
                continue

            info = ETAPE_INFO.get(fiche.get("etape"), ("", "?", "•", ""))
            jours = _immobile_depuis(fiche)
            try:
                await membre.send(
                    f"{info[2]} **Petit rappel, sans pression**\n\n"
                    f"Tu as pris le **{info[1]}** de "
                    f"{_nom_manga(fiche['manga'])} ch. {fiche['chapitre']} "
                    f"il y a {jours:.0f} jours.\n\n"
                    "Si tu es toujours dessus, ignore ce message — il ne "
                    "reviendra pas avant plusieurs jours.\n"
                    "Si tu n'as plus le temps, le bouton **↩️ Je rends** "
                    "libère le chapitre pour quelqu'un d'autre. Personne ne "
                    "te demandera pourquoi.\n\n"
                    f"→ {fiche.get('url', '')}")
                log.info("Atelier : relance envoyee a %s pour %s",
                         membre, fiche["cle"])
            except discord.HTTPException:
                # MP fermés : on note quand même le passage pour ne pas
                # réessayer toutes les douze heures.
                log.info("Atelier : MP impossible pour %s", membre)

            fiche["relances"] = fiche.get("relances", 0) + 1
            fiche["relance_le"] = time.time()
            self.sauver()

    @relance.before_loop
    async def _avant_relance(self):
        await self.bot.wait_until_ready()

    # ─────────────────────────────────────────────
    # Autocomplétion des chapitres ouverts
    # ─────────────────────────────────────────────
    async def _ac_chapitre(self, interaction: discord.Interaction, current: str):
        manga = getattr(interaction.namespace, "manga", None)
        propositions = []
        for fiche in self.en_cours(manga):
            chapitre = str(fiche.get("chapitre"))
            if current and current.lower() not in chapitre.lower():
                continue
            info = ETAPE_INFO.get(fiche.get("etape"), ("", "?", "", ""))
            nom = MANGAS.get(fiche.get("manga"), {}).get("name", "?")
            propositions.append(app_commands.Choice(
                name=f"{nom} ch. {chapitre} — {info[1]}", value=chapitre))
        return propositions[:25]

    # ─────────────────────────────────────────────
    # /atelier_raws — ouvre la fiche
    # ─────────────────────────────────────────────
    def _salon(self, guild, override):
        if override is not None:
            return override
        for cle in (ATELIER_CHANNEL, "raws_archive", "workshop_chat"):
            ch_id = CHANNELS.get(cle)
            if ch_id:
                salon = guild.get_channel(ch_id)
                if salon is not None:
                    return salon
        return None

    @app_commands.command(
        name="atelier_raws",
        description="Ouvre la fiche d'un chapitre : les pages RAW sont là")
    @app_commands.describe(
        manga="La série concernée",
        chapitre="Numéro du chapitre (58, 58.5…)",
        pages="Nombre de pages dans le lot",
        apercu="Une page en aperçu (image)",
        apercu2="Aperçu supplémentaire (facultatif)",
        apercu3="Aperçu supplémentaire (facultatif)",
        apercu4="Aperçu supplémentaire (facultatif)",
        source="D'où viennent les pages (facultatif)",
        note="Précision pour le clean : double page, couleurs, souci…",
        salon="Poster ailleurs que dans le salon d'atelier habituel")
    @app_commands.choices(manga=MANGA_CHOICES)
    @app_commands.guilds(GUILD)
    async def atelier_raws(
        self, interaction: discord.Interaction,
        manga: app_commands.Choice[str],
        chapitre: app_commands.Range[str, 1, 12],
        pages: app_commands.Range[int, 1, 400],
        apercu: discord.Attachment,
        apercu2: discord.Attachment = None,
        apercu3: discord.Attachment = None,
        apercu4: discord.Attachment = None,
        source: app_commands.Range[str, 1, 100] = None,
        note: app_commands.Range[str, 1, 400] = None,
        salon: discord.TextChannel = None,
    ):
        if not _peut_valider(interaction.user, "pages"):
            return await interaction.response.send_message(
                "❌ Seule l'équipe **Pages** peut ouvrir une fiche. "
                f"Les candidatures sont ouvertes : {SITE_URL}/equipe",
                ephemeral=True)

        chapitre = chapitre.strip()
        if self.fiche(manga.value, chapitre) is not None:
            return await interaction.response.send_message(
                f"⚠️ Une fiche existe déjà pour **{_nom_manga(manga.value)} "
                f"ch. {chapitre}**.\n`/atelier_fiche` pour la revoir, "
                "`/atelier_retirer` pour repartir de zéro.", ephemeral=True)

        images = [a for a in (apercu, apercu2, apercu3, apercu4) if a]
        mauvaises = [a.filename for a in images
                     if a.filename.rsplit(".", 1)[-1].lower() not in EXTENSIONS_OK]
        if mauvaises:
            return await interaction.response.send_message(
                "❌ Aperçus refusés (image attendue) : "
                + ", ".join(f"`{n}`" for n in mauvaises)
                + f"\nFormats acceptés : {', '.join(EXTENSIONS_OK)}.",
                ephemeral=True)

        cible = self._salon(interaction.guild, salon)
        if cible is None:
            return await interaction.response.send_message(
                "❌ Aucun salon d'atelier trouvé. Crée un salon `pages-raws` "
                "ou précise-le avec l'option `salon`.", ephemeral=True)

        await interaction.response.defer(ephemeral=True, thinking=True)

        fichiers = []
        for i, piece in enumerate(images, start=1):
            ext = piece.filename.rsplit(".", 1)[-1].lower()
            try:
                fichiers.append(await piece.to_file(filename=f"raw{i}.{ext}"))
            except discord.HTTPException as e:
                return await interaction.followup.send(
                    f"❌ Aperçu `{piece.filename}` illisible : {e}", ephemeral=True)

        fiche = {
            "cle": _cle(manga.value, chapitre),
            "manga": manga.value,
            "chapitre": chapitre,
            "pages": pages,
            "etape": _suivante("pages"),
            "termine": False,
            "salon": cible.id,
            "message": None,
            "url": None,
            "image": fichiers[0].filename,
            "source": source,
            "ouvert_le": time.time(),
            "pris_par": None,
            "pris_le": None,
            "etapes": {"pages": {"par": interaction.user.id, "le": time.time(),
                                 "note": note, "lien": source}},
        }

        embeds = [self._embed(interaction.guild, fiche)]
        for fichier in fichiers[1:]:
            extra = discord.Embed(url=manga_url(manga.value), color=COLOR_NEUTRAL)
            extra.set_image(url=f"attachment://{fichier.filename}")
            embeds.append(extra)

        try:
            message = await cible.send(embeds=embeds, files=fichiers,
                                       view=FicheView())
        except discord.Forbidden:
            return await interaction.followup.send(
                f"❌ Je n'ai pas le droit d'écrire dans {cible.mention}. "
                "Lance `/perms_salons` ou donne-moi l'accès à la main.",
                ephemeral=True)
        except discord.HTTPException as e:
            return await interaction.followup.send(
                f"❌ Discord a refusé le message : ```{e}```", ephemeral=True)

        fiche["message"] = message.id
        fiche["url"] = message.jump_url
        self._store.setdefault("fiches", {})[fiche["cle"]] = fiche
        self._store.setdefault("messages", {})[str(message.id)] = fiche["cle"]
        self.sauver()

        await self._prevenir(interaction.guild, fiche)
        log.info("Atelier : fiche ouverte %s (%d pages) par %s",
                 fiche["cle"], pages, interaction.user)

        await interaction.followup.send(
            embed=brand_embed(
                interaction.guild, title="✅ Fiche ouverte",
                description=(
                    f"{_nom_manga(manga.value)} — chapitre **{chapitre}**, "
                    f"**{pages}** pages, {len(fichiers)} aperçu(s).\n"
                    f"Prochaine étape : **{_libelle(fiche['etape'])}**\n"
                    f"→ {message.jump_url}"),
                color=COLOR_SUCCESS),
            ephemeral=True)

    # ─────────────────────────────────────────────
    # Les quatre étapes suivantes
    # ─────────────────────────────────────────────
    async def _valider(self, interaction, etape, manga, chapitre, apercu, lien, note):
        chapitre = str(chapitre).strip()
        fiche = self.fiche(manga.value, chapitre)
        if fiche is None:
            return await interaction.response.send_message(
                f"❌ Aucune fiche pour **{_nom_manga(manga.value)} ch. {chapitre}**.\n"
                "Elle s'ouvre avec `/atelier_raws`.", ephemeral=True)

        if fiche.get("termine"):
            return await interaction.response.send_message(
                "✅ Ce chapitre est déjà terminé — `/release` pour le publier.",
                ephemeral=True)

        if fiche["etape"] != etape:
            deja = etape in fiche.get("etapes", {})
            return await interaction.response.send_message(
                (f"⚠️ L'étape **{_libelle(etape)}** est déjà validée."
                 if deja else
                 f"⚠️ Ce chapitre en est à **{_libelle(fiche['etape'])}**, "
                 f"pas à **{_libelle(etape)}**.")
                + "\nLe staff peut corriger avec `/atelier_etape`.",
                ephemeral=True)

        if not _peut_valider(interaction.user, etape):
            return await interaction.response.send_message(
                f"❌ L'étape **{_libelle(etape)}** est réservée à son métier.\n"
                f"On recrute : {SITE_URL}/equipe", ephemeral=True)

        if apercu is not None:
            ext = apercu.filename.rsplit(".", 1)[-1].lower()
            if ext not in EXTENSIONS_OK:
                return await interaction.response.send_message(
                    f"❌ `{apercu.filename}` n'est pas une image "
                    f"({', '.join(EXTENSIONS_OK)}).", ephemeral=True)

        await interaction.response.defer(ephemeral=True, thinking=True)

        fichier = None
        if apercu is not None:
            ext = apercu.filename.rsplit(".", 1)[-1].lower()
            try:
                fichier = await apercu.to_file(filename=f"{etape}.{ext}")
            except discord.HTTPException as e:
                return await interaction.followup.send(
                    f"❌ Aperçu illisible : {e}", ephemeral=True)

        await self.avancer(interaction.guild, fiche, etape, interaction.user,
                           note=note, lien=lien)
        await self._reecrire(interaction.guild, fiche, fichier)

        suite = ("le chapitre est **prêt à sortir**" if fiche.get("termine")
                 else f"au tour de **{_libelle(fiche['etape'])}**")
        await interaction.followup.send(
            embed=brand_embed(
                interaction.guild,
                title=f"✅ {_libelle(etape)} validé",
                description=(f"{_nom_manga(manga.value)} — chapitre "
                             f"**{chapitre}** : {suite}.\n→ {fiche.get('url')}"),
                color=COLOR_SUCCESS),
            ephemeral=True)

    @app_commands.command(name="atelier_clean",
                          description="Le clean est fait → passe à la traduction")
    @app_commands.describe(manga="La série", chapitre="Numéro du chapitre",
                           apercu="Une page nettoyée, en aperçu",
                           lien="Lien vers le dossier des pages clean",
                           note="Un mot pour la traduction")
    @app_commands.choices(manga=MANGA_CHOICES)
    @app_commands.guilds(GUILD)
    async def atelier_clean(self, interaction: discord.Interaction,
                            manga: app_commands.Choice[str], chapitre: str,
                            apercu: discord.Attachment = None,
                            lien: app_commands.Range[str, 1, 300] = None,
                            note: app_commands.Range[str, 1, 400] = None):
        await self._valider(interaction, "clean", manga, chapitre, apercu, lien, note)

    @app_commands.command(name="atelier_trad",
                          description="La traduction est faite → passe à l'édition")
    @app_commands.describe(manga="La série", chapitre="Numéro du chapitre",
                           apercu="Un aperçu (facultatif)",
                           lien="Lien vers le script traduit",
                           note="Un mot pour l'édition")
    @app_commands.choices(manga=MANGA_CHOICES)
    @app_commands.guilds(GUILD)
    async def atelier_trad(self, interaction: discord.Interaction,
                           manga: app_commands.Choice[str], chapitre: str,
                           apercu: discord.Attachment = None,
                           lien: app_commands.Range[str, 1, 300] = None,
                           note: app_commands.Range[str, 1, 400] = None):
        await self._valider(interaction, "trad", manga, chapitre, apercu, lien, note)

    @app_commands.command(name="atelier_edit",
                          description="L'édition est faite → passe au Q-check")
    @app_commands.describe(manga="La série", chapitre="Numéro du chapitre",
                           apercu="Une page éditée, en aperçu",
                           lien="Lien vers les pages éditées",
                           note="Un mot pour le Q-check")
    @app_commands.choices(manga=MANGA_CHOICES)
    @app_commands.guilds(GUILD)
    async def atelier_edit(self, interaction: discord.Interaction,
                           manga: app_commands.Choice[str], chapitre: str,
                           apercu: discord.Attachment = None,
                           lien: app_commands.Range[str, 1, 300] = None,
                           note: app_commands.Range[str, 1, 400] = None):
        await self._valider(interaction, "edit", manga, chapitre, apercu, lien, note)

    @app_commands.command(name="atelier_qcheck",
                          description="Le Q-check est fait → le chapitre peut sortir")
    @app_commands.describe(manga="La série", chapitre="Numéro du chapitre",
                           apercu="Un aperçu final (facultatif)",
                           lien="Lien vers la version finale",
                           note="Dernières remarques")
    @app_commands.choices(manga=MANGA_CHOICES)
    @app_commands.guilds(GUILD)
    async def atelier_qcheck(self, interaction: discord.Interaction,
                             manga: app_commands.Choice[str], chapitre: str,
                             apercu: discord.Attachment = None,
                             lien: app_commands.Range[str, 1, 300] = None,
                             note: app_commands.Range[str, 1, 400] = None):
        await self._valider(interaction, "qcheck", manga, chapitre, apercu, lien, note)

    # Autocomplétion partagée par les quatre commandes d'étape
    for _cmd in (atelier_clean, atelier_trad, atelier_edit, atelier_qcheck):
        _cmd.autocomplete("chapitre")(_ac_chapitre)
    del _cmd

    # ─────────────────────────────────────────────
    # /atelier_fiche
    # ─────────────────────────────────────────────
    @app_commands.command(name="atelier_fiche",
                          description="Revoir la fiche d'un chapitre")
    @app_commands.describe(manga="La série", chapitre="Numéro du chapitre")
    @app_commands.choices(manga=MANGA_CHOICES)
    @app_commands.guilds(GUILD)
    async def atelier_fiche(self, interaction: discord.Interaction,
                            manga: app_commands.Choice[str], chapitre: str):
        fiche = self.fiche(manga.value, chapitre)
        if fiche is None:
            return await interaction.response.send_message(
                f"❌ Aucune fiche pour **{_nom_manga(manga.value)} "
                f"ch. {str(chapitre).strip()}**.", ephemeral=True)

        embed = self._embed(interaction.guild, fiche)
        embed.set_image(url=None)          # l'aperçu vit sur le message d'origine
        await interaction.response.send_message(
            content=f"→ {fiche.get('url')}", embed=embed, ephemeral=True)

    atelier_fiche.autocomplete("chapitre")(_ac_chapitre)

    # ─────────────────────────────────────────────
    # /atelier_liste
    # ─────────────────────────────────────────────
    @app_commands.command(name="atelier_liste",
                          description="Tous les chapitres en cours de fabrication")
    @app_commands.describe(manga="Filtrer sur une série",
                           tout="True = montre aussi les chapitres terminés")
    @app_commands.choices(manga=MANGA_CHOICES)
    @app_commands.guilds(GUILD)
    async def atelier_liste(self, interaction: discord.Interaction,
                            manga: app_commands.Choice[str] = None,
                            tout: bool = False):
        fiches = list(self._store.get("fiches", {}).values())
        if manga:
            fiches = [f for f in fiches if f.get("manga") == manga.value]
        if not tout:
            fiches = [f for f in fiches if not f.get("termine")]

        if not fiches:
            return await interaction.response.send_message(
                embed=brand_embed(
                    interaction.guild, title="📭 Atelier vide",
                    description="Aucun chapitre en fabrication."
                                + ("" if tout else "\n`tout:True` pour voir "
                                   "les chapitres déjà terminés."),
                    color=COLOR_WARNING),
                ephemeral=True)

        # Regroupé par série, comme sur le site
        par_serie = {}
        for fiche in fiches:
            par_serie.setdefault(fiche.get("manga"), []).append(fiche)

        blocs = []
        for cle_manga, lot in par_serie.items():
            lot.sort(key=lambda f: f.get("ouvert_le", 0))
            lignes = []
            for fiche in lot[:10]:
                if fiche.get("termine"):
                    etat = "🎉 prêt à sortir"
                else:
                    info = ETAPE_INFO.get(fiche.get("etape"), ("", "?", "•", ""))
                    preneur = fiche.get("pris_par")
                    etat = (f"{info[2]} {info[1]} — <@{preneur}>" if preneur
                            else f"{info[2]} {info[1]} — *libre*")
                    dort = _immobile_depuis(fiche)
                    if dort >= ATELIER_RELANCE_JOURS:
                        etat += f" ⏳ {dort:.0f}j"
                lignes.append(f"**ch. {fiche.get('chapitre')}** · {etat} · "
                              f"[fiche]({fiche.get('url')})")
            blocs.append(f"{_nom_manga(cle_manga)}\n" + "\n".join(lignes))

        libres = sum(1 for f in fiches
                     if not f.get("termine") and not f.get("pris_par"))
        await interaction.response.send_message(
            embed=brand_embed(
                interaction.guild, title="🏭 L'atelier en ce moment",
                description="\n\n".join(blocs)
                + f"\n\n**{libres}** étape(s) sans personne dessus "
                  f"sur {len(fiches)} chapitre(s).",
                color=COLOR_NEUTRAL),
            ephemeral=True)

    # ─────────────────────────────────────────────
    # /atelier_etape — rattrapage staff
    # ─────────────────────────────────────────────
    @app_commands.command(
        name="atelier_etape",
        description="(Staff) Corrige l'étape en cours d'un chapitre")
    @app_commands.describe(manga="La série", chapitre="Numéro du chapitre",
                           etape="L'étape où placer le chapitre")
    @app_commands.choices(
        manga=MANGA_CHOICES,
        etape=[app_commands.Choice(name=f"{e[2]} {e[1]}", value=e[0])
               for e in sitelib.STEPS])
    @app_commands.default_permissions(manage_messages=True)
    @app_commands.guilds(GUILD)
    async def atelier_etape(self, interaction: discord.Interaction,
                            manga: app_commands.Choice[str], chapitre: str,
                            etape: app_commands.Choice[str]):
        fiche = self.fiche(manga.value, chapitre)
        if fiche is None:
            return await interaction.response.send_message(
                "❌ Aucune fiche pour ce chapitre.", ephemeral=True)

        await interaction.response.defer(ephemeral=True, thinking=True)

        # Les étapes avant celle visée comptent comme faites, les autres non.
        cible = ETAPES.index(etape.value)
        faites = fiche.setdefault("etapes", {})
        for i, eid in enumerate(ETAPES):
            if i < cible and eid not in faites:
                faites[eid] = {"par": interaction.user.id, "le": time.time(),
                               "note": "réglé à la main", "lien": None}
            elif i >= cible:
                faites.pop(eid, None)

        fiche["etape"] = etape.value
        fiche["termine"] = etape.value == DERNIERE
        fiche["pris_par"] = None
        fiche["pris_le"] = None
        self.sauver()
        await self._reecrire(interaction.guild, fiche)

        log.info("Atelier : %s force sur %s par %s",
                 fiche["cle"], etape.value, interaction.user)
        await interaction.followup.send(
            embed=brand_embed(
                interaction.guild, title="🔧 Étape corrigée",
                description=(f"{_nom_manga(manga.value)} — chapitre "
                             f"**{fiche['chapitre']}** est maintenant à "
                             f"**{_libelle(etape.value)}**.\n→ {fiche.get('url')}"),
                color=COLOR_SUCCESS),
            ephemeral=True)

    atelier_etape.autocomplete("chapitre")(_ac_chapitre)

    # ─────────────────────────────────────────────
    # /atelier_retirer
    # ─────────────────────────────────────────────
    @app_commands.command(name="atelier_retirer",
                          description="Supprime la fiche d'un chapitre")
    @app_commands.describe(manga="La série", chapitre="Numéro du chapitre",
                           supprimer="True = efface aussi le message dans le salon")
    @app_commands.choices(manga=MANGA_CHOICES)
    @app_commands.guilds(GUILD)
    async def atelier_retirer(self, interaction: discord.Interaction,
                              manga: app_commands.Choice[str], chapitre: str,
                              supprimer: bool = True):
        fiche = self.fiche(manga.value, chapitre)
        if fiche is None:
            return await interaction.response.send_message(
                "❌ Aucune fiche pour ce chapitre.", ephemeral=True)

        ouvreur = (fiche.get("etapes", {}).get("pages") or {}).get("par")
        if (ouvreur != interaction.user.id
                and not _peut_valider(interaction.user, DERNIERE)):
            return await interaction.response.send_message(
                "❌ Seule la personne qui a ouvert la fiche (ou le staff) "
                "peut la retirer.", ephemeral=True)

        await interaction.response.defer(ephemeral=True, thinking=True)

        efface = False
        if supprimer:
            salon = interaction.guild.get_channel(fiche.get("salon") or 0)
            if salon is not None:
                try:
                    message = await salon.fetch_message(fiche["message"])
                    await message.delete()
                    efface = True
                except (discord.NotFound, discord.HTTPException):
                    pass

        self._store.setdefault("fiches", {}).pop(fiche["cle"], None)
        self._store.setdefault("messages", {}).pop(str(fiche.get("message")), None)
        self.sauver()

        await interaction.followup.send(
            embed=brand_embed(
                interaction.guild, title="🗑️ Fiche retirée",
                description=(f"{_nom_manga(manga.value)} — chapitre "
                             f"**{fiche['chapitre']}** ne figure plus dans "
                             "l'atelier."
                             + ("\nLe message a été supprimé." if efface else
                                "\nLe message d'origine est resté en place.")),
                color=COLOR_SUCCESS),
            ephemeral=True)

    atelier_retirer.autocomplete("chapitre")(_ac_chapitre)

    # ═══════════════════════════════════════════════
    # Le pont vers le site
    # ═══════════════════════════════════════════════

    def _noms_site(self) -> dict:
        """clé MANGAS → identifiant exact de la série sur le site.

        On demande au site plutôt que de supposer : une clé inventée
        créerait une entrée fantôme que le site n'afficherait jamais.
        """
        sync = self.bot.get_cog("SiteSync")
        data = getattr(sync, "data", None)
        noms = {}
        for cle, info in MANGAS.items():
            if cle == "oneshot":
                continue                    # l'atelier du site ne suit que les séries
            if data is None:
                noms[cle] = info["name"]    # site injoignable : on fait confiance à la config
                continue
            serie = data.get_series(info["name"])
            if serie is not None:
                noms[cle] = serie.get("id") or info["name"]
        return noms

    async def _atelier_en_ligne(self) -> str:
        """Le fichier atelier.js tel qu'il est publié en ce moment."""
        url = f"{SITE_URL.rstrip('/')}/{siteexport.CHEMIN}"
        delai = aiohttp.ClientTimeout(total=20)
        async with aiohttp.ClientSession(timeout=delai) as session:
            async with session.get(url) as reponse:
                reponse.raise_for_status()
                return await reponse.text()

    async def _preparer(self):
        """(contenu, changements, remarques, contenu actuel)."""
        brut = await self._atelier_en_ligne()
        actuel = sitelib.parse_js_literal(brut, siteexport.VARIABLE)
        fiches = list(self._store.get("fiches", {}).values())
        depuis_bot, remarques = siteexport.entrees_depuis_fiches(
            fiches, self._noms_site())
        fusion, changements = siteexport.fusionner(actuel, depuis_bot)
        return siteexport.rendre(fusion, siteexport.entete(brut)), \
            changements, remarques, brut

    def _resume(self, changements, remarques) -> str:
        texte = "\n".join(changements) if changements else "*rien à signaler*"
        if remarques:
            texte += "\n\n" + "\n".join(remarques)
        return texte[:3900]

    @app_commands.command(
        name="atelier_export",
        description="Génère le atelier.js du site à partir des fiches")
    @app_commands.default_permissions(manage_messages=True)
    @app_commands.guilds(GUILD)
    async def atelier_export(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            contenu, changements, remarques, brut = await self._preparer()
        except Exception as e:
            return await interaction.followup.send(
                embed=brand_embed(
                    interaction.guild, title="❌ Export impossible",
                    description=f"```{type(e).__name__} : {e}```",
                    color=COLOR_ERROR),
                ephemeral=True)

        if contenu == brut:
            return await interaction.followup.send(
                embed=brand_embed(
                    interaction.guild, title="✅ Le site est déjà à jour",
                    description="Les fiches Discord et `atelier.js` disent "
                                "la même chose.\n\n"
                                + self._resume(changements, remarques),
                    color=COLOR_SUCCESS),
                ephemeral=True)

        fichier = discord.File(
            io.BytesIO(contenu.encode("utf-8")), filename="atelier.js")
        await interaction.followup.send(
            embed=brand_embed(
                interaction.guild, title="📝 atelier.js régénéré",
                description=self._resume(changements, remarques)
                + "\n\n→ Remplace `js/data/atelier.js` par le fichier joint, "
                  "ou lance `/atelier_pousser` si le dépôt est configuré.",
                color=COLOR_NEUTRAL),
            file=fichier, ephemeral=True)

    @app_commands.command(
        name="atelier_pousser",
        description="(Admin) Écrit atelier.js dans le dépôt du site")
    @app_commands.describe(
        simulation="True = montre ce qui serait commité, sans rien envoyer")
    @app_commands.default_permissions(administrator=True)
    @app_commands.guilds(GUILD)
    async def atelier_pousser(self, interaction: discord.Interaction,
                              simulation: bool = True):
        if not SITE_REPO or not SITE_REPO_TOKEN:
            manquant = []
            if not SITE_REPO:
                manquant.append("`SITE_REPO=proprietaire/depot`")
            if not SITE_REPO_TOKEN:
                manquant.append("`SITE_REPO_TOKEN=ghp_...`")
            return await interaction.response.send_message(
                embed=brand_embed(
                    interaction.guild, title="⚙️ Dépôt du site non configuré",
                    description=(
                        "À ajouter dans le `.env` du bot, puis redémarrer :\n"
                        + "\n".join(f"• {m}" for m in manquant)
                        + "\n\nLe jeton a besoin du droit **Contents: write** sur "
                          "ce dépôt, et de rien d'autre.\n"
                          "En attendant, `/atelier_export` te donne le fichier "
                          "à déposer à la main."),
                    color=COLOR_WARNING),
                ephemeral=True)

        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            contenu, changements, remarques, brut = await self._preparer()
        except Exception as e:
            return await interaction.followup.send(
                embed=brand_embed(
                    interaction.guild, title="❌ Préparation impossible",
                    description=f"```{type(e).__name__} : {e}```",
                    color=COLOR_ERROR),
                ephemeral=True)

        if contenu == brut:
            return await interaction.followup.send(
                embed=brand_embed(
                    interaction.guild, title="✅ Rien à pousser",
                    description="`atelier.js` dit déjà la même chose que les fiches.",
                    color=COLOR_SUCCESS),
                ephemeral=True)

        if simulation:
            return await interaction.followup.send(
                embed=brand_embed(
                    interaction.guild,
                    title="🔎 Simulation — rien n'a été envoyé",
                    description=(
                        self._resume(changements, remarques)
                        + f"\n\n**Destination :** `{SITE_REPO}` · branche "
                          f"`{SITE_REPO_BRANCH}` · `{siteexport.CHEMIN}`\n"
                          "Pour appliquer : relance avec `simulation:False`."),
                    color=COLOR_WARNING),
                ephemeral=True)

        try:
            lien = await self._commit(contenu, interaction.user)
        except Exception as e:
            return await interaction.followup.send(
                embed=brand_embed(
                    interaction.guild, title="❌ GitHub a refusé",
                    description=f"```{type(e).__name__} : {e}```\n"
                                "Vérifie le dépôt, la branche et les droits du jeton.",
                    color=COLOR_ERROR),
                ephemeral=True)

        log.info("Atelier : atelier.js pousse sur %s par %s",
                 SITE_REPO, interaction.user)
        await interaction.followup.send(
            embed=brand_embed(
                interaction.guild, title="🚀 atelier.js mis à jour",
                description=self._resume(changements, remarques)
                + f"\n\n→ [voir le commit]({lien})",
                color=COLOR_SUCCESS),
            ephemeral=True)

    async def _commit(self, contenu: str, auteur) -> str:
        """Écrit le fichier via l'API Contents de GitHub. Renvoie l'URL du commit."""
        entetes = {
            "Authorization": f"Bearer {SITE_REPO_TOKEN}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "LanorTradBot",
        }
        url = (f"https://api.github.com/repos/{SITE_REPO}"
               f"/contents/{siteexport.CHEMIN}")
        delai = aiohttp.ClientTimeout(total=30)

        async with aiohttp.ClientSession(headers=entetes, timeout=delai) as session:
            async with session.get(url, params={"ref": SITE_REPO_BRANCH}) as r:
                if r.status != 200:
                    raise RuntimeError(
                        f"lecture du fichier : HTTP {r.status} — "
                        f"{(await r.text())[:200]}")
                sha = (await r.json()).get("sha")

            charge = {
                "message": f"atelier : mise a jour depuis Discord ({auteur})",
                "content": base64.b64encode(contenu.encode("utf-8")).decode("ascii"),
                "sha": sha,
                "branch": SITE_REPO_BRANCH,
            }
            async with session.put(url, json=charge) as r:
                if r.status not in (200, 201):
                    raise RuntimeError(
                        f"écriture : HTTP {r.status} — {(await r.text())[:200]}")
                return (await r.json())["commit"]["html_url"]

    @app_commands.command(
        name="atelier_eta",
        description="Fixe la date de sortie visée d'un chapitre")
    @app_commands.describe(manga="La série", chapitre="Numéro du chapitre",
                           date="AAAA-MM-JJ, ou « - » pour retirer la date")
    @app_commands.choices(manga=MANGA_CHOICES)
    @app_commands.guilds(GUILD)
    async def atelier_eta(self, interaction: discord.Interaction,
                          manga: app_commands.Choice[str], chapitre: str,
                          date: app_commands.Range[str, 1, 10]):
        fiche = self.fiche(manga.value, chapitre)
        if fiche is None:
            return await interaction.response.send_message(
                "❌ Aucune fiche pour ce chapitre.", ephemeral=True)
        if not _peut_valider(interaction.user, fiche.get("etape") or DERNIERE):
            return await interaction.response.send_message(
                "❌ Réservé à l'équipe sur ce chapitre.", ephemeral=True)

        date = date.strip()
        if date in ("-", "aucune", "none"):
            fiche.pop("eta", None)
            texte = "La date de sortie visée est retirée."
        else:
            try:
                datetime.date.fromisoformat(date)
            except ValueError:
                return await interaction.response.send_message(
                    "❌ Date attendue au format **AAAA-MM-JJ** "
                    "(ex. `2026-09-13`), ou `-` pour l'enlever.", ephemeral=True)
            fiche["eta"] = date
            texte = f"Sortie visée le **{date}**."

        self.sauver()
        await interaction.response.defer(ephemeral=True, thinking=True)
        await self._reecrire(interaction.guild, fiche)
        await interaction.followup.send(
            embed=brand_embed(
                interaction.guild, title="🎯 Date mise à jour",
                description=(f"{_nom_manga(manga.value)} — chapitre "
                             f"**{fiche['chapitre']}**\n{texte}\n\n"
                             "`/atelier_pousser` pour la reporter sur le site."),
                color=COLOR_SUCCESS),
            ephemeral=True)

    atelier_eta.autocomplete("chapitre")(_ac_chapitre)


async def setup(bot):
    await bot.add_cog(Atelier(bot))
