"""
Atelier — la chaîne de fabrication d'un chapitre
==================================================
Le site montre l'avancement au public ; ce cog fait tourner l'atelier côté
équipe. Un chapitre = **une fiche** qui vit dans le salon d'atelier et se
réécrit à chaque étape, plutôt que cinq messages empilés qu'il faut
recoller mentalement.

**Une seule commande à retenir, et elle est pour l'admin :**

  /atelier_raws    — le titre, le numéro, les pages. Ça ouvre la fiche,
                     ça ouvre son fil, ça pose le panneau des métiers.

Ensuite plus rien à taper. Le panneau porte les cinq métiers de la chaîne
et leur couleur dit tout :

  📥 Pages · 🧽 Clean · 💬 Trad · ✍️ Edit · 🔍 Q-check
     vert = c'est fait · bleu = c'est ton tour · gris = pas encore

Un cleaner clique sur 🧽 quand il a fini. Le rôle suivant est pingé, le
bouton d'après passe au bleu, le suivi public avance. Personne n'a à
retenir de nom de commande ni à retaper un numéro de chapitre.

Le reste, pour qui veut regarder :

  /mes_taches      — ton établi : ce que tu as pris, ce qui attend ton métier
  /atelier_fiche   — revoir une fiche
  /atelier_liste   — tout ce qui est en cours, par série, stock compris
  /atelier_avancement — 14 pages sur 20, quand la fiche n'est pas sous la main
  /atelier_stock   — une plage de chapitres déjà avancés, sans fiche
  /atelier_stock_retirer — sortir des chapitres du stock
  /atelier_etape   — (staff) corriger l'étape d'une fiche
  /atelier_retirer — supprimer une fiche

Les étapes sont celles du site (`bot/site.py` · STEPS) : le vocabulaire est
le même sur le site, dans les embeds et dans la bouche des gens.

Les principes :

  • **Rien à taper, rien à retenir.** Il y a eu des commandes par étape
    (`/atelier_clean`, `/atelier_trad`…) : quatre noms à connaître, et il
    fallait rappeler la série et le numéro à chaque fois, pour un
    chapitre dont la fiche était déjà sous les yeux. Un bouton sur cette
    fiche dit la même chose sans rien demander.
  • **Chaque étape appartient à son métier.** Un cleaner ne valide pas une
    traduction ; le bouton refuse poliment plutôt que de laisser passer.
  • **Une étape validée prévient la suivante.** Le rôle concerné est pingé
    avec un lien vers la fiche — personne n'a à surveiller un salon.
  • **Les pages vivent dans le fil de la fiche.** Une commande slash
    plafonne à 25 options et chaque pièce jointe en mange une : on ne
    dépose pas vingt pages par ce chemin. La fiche ouvre donc un fil où
    le glisser-déposer marche normalement (dix fichiers par message), et
    le bot compte les images reçues étape par étape.
  • **Une étape n'est pas binaire.** Entre « pas commencé » et « fini »
    il y a 14 pages sur 20. Le fil compte ce qu'il reçoit, et le bouton
    **📄 Où j'en suis** sert à annoncer le reste quand le travail se fait
    ailleurs ; la fiche en tire une jauge, et le suivi public la montre
    en réécrivant son message au lieu d'en poster un de plus.
  • **Une fiche par chapitre, mais pas pour le stock.** « Les chapitres
    248 à 293 sont nettoyés » ne mérite pas quarante-six fiches : ce
    serait quarante-six messages et un repingage de masse tous les trois
    jours. `/atelier_stock` le dit en une plage (`bot/stock.py`), et la
    fiche n'arrive que quand un chapitre entre vraiment en fabrication.
  • **Une échéance est un repère, pas un couperet.** Prendre une étape,
    c'est prendre une date (`ATELIER_DELAIS`, modulée par le nombre de
    pages). Le bot écrit en privé quand elle approche, puis quand elle
    passe ; la rallonge est à un bouton et ne se paie pas. Au bout du
    compte l'étape retourne au pot commun toute seule — un chapitre
    endormi bloque toute la chaîne derrière lui, et c'est la seule raison.

Rien de tout ça ne se dit en public : les rappels partent en MP, les
retards vont dans le salon d'équipe, et le suivi que voient les lecteurs
ne nomme jamais personne.

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
from bot import stock as stocklib
from bot.config import (
    GUILD_ID, MANGAS, CHANNELS, ROLES, SITE_URL,
    COLOR_NEUTRAL, COLOR_SUCCESS, COLOR_WARNING, COLOR_ERROR,
    ATELIER_CHANNEL, ATELIER_ANNONCE_ETAPE,
    ATELIER_FIL, ATELIER_FIL_ARCHIVE,
    ATELIER_ETAPE_ROLES, ATELIER_ROLES_JOKER,
    ATELIER_RELANCE, ATELIER_RELANCE_JOURS, ATELIER_RELANCE_INTERVALLE,
    ATELIER_RELANCE_MAX,
    ATELIER_DELAIS, ATELIER_DELAI_PAGES, ATELIER_DELAI_PAGES_REF,
    ATELIER_DELAI_PAGES_MIN, ATELIER_DELAI_PAGES_MAX,
    ATELIER_RALLONGE_JOURS, ATELIER_RALLONGE_MAX,
    ATELIER_RAPPEL_RETARD_JOURS,
    ATELIER_LIBERATION, ATELIER_LIBERATION_JOURS,
    ATELIER_RAPPEL_LIBRE_JOURS, ATELIER_RAPPEL_LIBRE_MAX,
    ATELIER_STAFF_CHANNEL,
    ATELIER_SUIVI_PUBLIC, ATELIER_SUIVI_CHANNEL, ATELIER_SUIVI_CHANNEL_REPLI,
    ATELIER_SUIVI_ROLE, ATELIER_SUIVI_ETAPES, ATELIER_SUIVI_EDITE,
    ATELIER_JAUGE, ATELIER_JAUGE_CASES,
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

# Sur un bouton, « Pages trouvées » tient mal à côté de quatre voisins :
# le panneau doit se lire d'un coup d'œil, pas se déchiffrer.
LIBELLE_COURT = {
    "pages":  "Pages",
    "clean":  "Clean",
    "trad":   "Trad",
    "edit":   "Edit",
    "qcheck": "Q-check",
}

MANGA_CHOICES = [
    app_commands.Choice(name=f"{m['emoji']} {m['name']}", value=cle)
    for cle, m in MANGAS.items()
]

EXTENSIONS_OK = ("png", "jpg", "jpeg", "webp", "gif")

# « Qu'est-ce qui est déjà fait ? » — on demande la dernière étape
# TERMINÉE, parce que c'est comme ça que les gens le disent : « pages
# trouvées et clean du 248 au 293 ». Le bot en déduit ce qui attend.
# « sortie » n'y figure pas : un chapitre sorti n'est plus du stock.
FAIT_CHOICES = (
    [app_commands.Choice(name="— rien encore (raws pas trouvées)",
                         value="aucune")]
    + [app_commands.Choice(name=f"{e[2]} {e[1]} — fait", value=e[0])
       for e in sitelib.STEPS if e[0] != "sortie"]
)


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


def _est_du_metier(member: discord.Member, etape: str) -> bool:
    """Le rôle métier de l'étape, sans les rôles passe-partout.

    `_peut_valider` dit qui a le droit ; celui-ci dit à qui ça s'adresse.
    Sans quoi le staff verrait toute la chaîne dans son établi.
    """
    ids = {ROLES.get(c) for c in ATELIER_ETAPE_ROLES.get(etape, ())} - {None}
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


# ═══════════════════════════════════════════════════════
# L'avancement d'une étape
# ═══════════════════════════════════════════════════════
# Deux façons de savoir où en est une étape, et elles coexistent :
#   • le fil compte les pages qu'on y dépose (`depots`) ;
#   • quelqu'un annonce un nombre à la main (`avancement`), parce que le
#     clean se fait dans Photoshop et pas dans Discord.
# On retient la plus avancée des deux : ni l'une ni l'autre ne peut
# défaire du travail que l'autre a déjà vu passer.

def _fait(fiche: dict, etape: str) -> int:
    """Nombre de pages faites pour cette étape, tout compte fait."""
    declare = (fiche.get("avancement") or {}).get(etape) or 0
    depose = (fiche.get("depots") or {}).get(etape, 0) or 0
    return max(int(declare), int(depose))


def _jauge(fait: int, total) -> str:
    """« ▰▰▰▰▰▰▱▱▱▱ 70 % » — vide si on ne sait pas sur combien."""
    if not ATELIER_JAUGE or not total or total <= 0:
        return ""
    part = max(0.0, min(1.0, fait / float(total)))
    pleines = int(round(part * ATELIER_JAUGE_CASES))
    barre = "▰" * pleines + "▱" * (ATELIER_JAUGE_CASES - pleines)
    return f"{barre} {part * 100:.0f} %"


def _ligne_pages(fiche: dict, etape: str) -> str:
    """« 🧽 **14/20** ▰▰▰▰▰▰▱▱▱▱ 70 % » pour une étape donnée."""
    info = ETAPE_INFO.get(etape, (etape, etape, "•", ""))
    fait = _fait(fiche, etape)
    total = fiche.get("pages")
    if not fait:
        return f"{info[2]} *rien de fait pour le {info[1]}*"
    if not total:
        return f"{info[2]} **{fait}** page(s)"
    tete = f"{info[2]} **{fait}/{total}**" + (" ✅" if fait >= total else "")
    jauge = _jauge(fait, total)
    return "\n".join([tete, jauge]) if jauge else tete


def _bloc_pages(fiche: dict) -> str:
    """Le champ « 📄 Pages » de la fiche : le total, puis la jauge en cours."""
    total = fiche.get("pages")
    etape = fiche.get("etape")
    lignes = []
    if total:
        lignes.append(f"**{total}** pages au total")
    if not fiche.get("termine"):
        lignes.append(_ligne_pages(fiche, etape))

    # Une étape validée dont le compte n'est pas au complet — trois raws
    # manquantes, par exemple. Ça se paie six étapes plus loin si personne
    # ne le voit passer : la fiche le garde sous les yeux.
    incomplets = []
    for eid in ETAPES:
        if eid == etape or eid not in (fiche.get("etapes") or {}):
            continue
        fait = _fait(fiche, eid)
        if total and fait and fait < total:
            incomplets.append(f"{ETAPE_INFO[eid][2]} {fait}/{total}")
    if incomplets:
        lignes.append("⚠️ incomplet : " + " · ".join(incomplets))

    if fiche.get("fil"):
        lignes.append(f"→ <#{fiche['fil']}>")
    return "\n".join(lignes)


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
# Les échéances
# ═══════════════════════════════════════════════════════
# Prendre une étape, c'est prendre une échéance : la fiche affiche un
# compte à rebours, le bot écrit en privé quand il approche, et l'étape
# se libère toute seule si elle finit par ne plus avancer. Rien de tout
# cela n'est un couperet — la rallonge est à un bouton.

def _delai_jours(etape: str, pages=None):
    """Le délai d'une étape en jours, modulé par le volume. None si aucun."""
    base = ATELIER_DELAIS.get(etape)
    if not base:
        return None
    if etape in ATELIER_DELAI_PAGES and pages:
        facteur = pages / float(ATELIER_DELAI_PAGES_REF or 1)
        # Un chapitre deux fois plus long ne demande pas deux fois plus de
        # temps : on suit le volume à moitié, et on borne des deux côtés.
        facteur = 0.5 + 0.5 * facteur
        base *= max(ATELIER_DELAI_PAGES_MIN, min(ATELIER_DELAI_PAGES_MAX, facteur))
    return base


def _echeance_pour(fiche: dict, depart=None):
    """L'échéance de l'étape en cours si on la prenait maintenant."""
    jours = _delai_jours(fiche.get("etape"), fiche.get("pages"))
    if jours is None:
        return None
    return (depart or time.time()) + jours * 86400


def _reste_jours(fiche: dict):
    """Jours avant l'échéance (négatif = en retard). None si pas d'échéance."""
    echeance = fiche.get("echeance")
    if not echeance:
        return None
    return (echeance - time.time()) / 86400


def _liberer(fiche: dict):
    """Remet l'étape en cours à disposition et efface le suivi de la prise."""
    fiche["pris_par"] = None
    fiche["pris_le"] = None
    fiche["echeance"] = None
    fiche["rallonges"] = 0
    fiche["rappels"] = []
    fiche["libre_le"] = time.time()
    fiche["rappels_libre"] = 0
    fiche.pop("staff_prevenu", None)
    # Champs de la version précédente : ils ne servent plus à rien une fois
    # l'étape libérée, autant ne pas les traîner.
    fiche.pop("relances", None)
    fiche.pop("relance_le", None)


# ═══════════════════════════════════════════════════════
# Le panneau de la fiche
# ═══════════════════════════════════════════════════════
# Il n'y a plus de commande par étape. Les cinq métiers de la chaîne sont
# là, en boutons, et leur couleur dit tout : vert = fait, bleu = c'est
# ton tour, gris = pas encore. On clique sur le sien quand on a fini,
# point. Un cleaner n'a rien à retenir, rien à taper, rien à chercher.
#
# Les boutons survivent aux redémarrages : leur `custom_id` est fixe, et
# c'est `bot.add_view(FicheView())` qui les rebranche. Seuls le libellé
# et la couleur dépendent de la fiche, et ça ne regarde que l'affichage.

def _contexte(interaction):
    """(cog, fiche) depuis le message cliqué, ou (None, None)."""
    cog = interaction.client.get_cog("Atelier")
    if cog is None:
        return None, None
    message = getattr(interaction, "message", None)
    return cog, (cog.fiche_du_message(message.id) if message else None)


def _contexte_cle(interaction, cle):
    """(cog, fiche) depuis la clé de la fiche.

    Un formulaire n'est pas un clic : Discord ne garantit pas de rattacher
    le message d'origine à sa soumission. On retient donc la clé au moment
    d'ouvrir le formulaire, et on ne dépend plus de rien d'autre.
    """
    cog = interaction.client.get_cog("Atelier")
    if cog is None:
        return None, None
    return cog, cog.fiche_par_cle(cle)


async def _refus(interaction, texte):
    await interaction.response.send_message(texte, ephemeral=True)


class FiniModal(discord.ui.Modal):
    """« C'est fait » — avec, si on veut, un lien et un mot pour la suite.

    Les deux champs sont facultatifs : on peut valider en appuyant sur
    Envoyer sans rien écrire. Ils remplacent les options `lien` et `note`
    des anciennes commandes ; l'aperçu, lui, n'a plus lieu d'être — les
    pages vivent dans le fil.
    """

    def __init__(self, fiche, etape):
        info = ETAPE_INFO.get(etape, (etape, etape, "•", ""))
        super().__init__(title=f"{info[1]} — ch. {fiche.get('chapitre')}"[:45])
        self.etape = etape
        self.cle = fiche.get("cle")
        self.lien = discord.ui.TextInput(
            label="Lien vers ton rendu (facultatif)",
            placeholder="Un Drive, un Mega… ou rien du tout",
            required=False, max_length=300)
        self.note = discord.ui.TextInput(
            label="Un mot pour la suite (facultatif)",
            placeholder="Double page p.12, onomatopées laissées en jap…",
            style=discord.TextStyle.paragraph, required=False, max_length=400)
        self.add_item(self.lien)
        self.add_item(self.note)

    async def on_submit(self, interaction: discord.Interaction):
        cog, fiche = _contexte_cle(interaction, self.cle)
        if fiche is None:
            return await _refus(interaction, "❌ Cette fiche n'est plus suivie.")
        if fiche.get("etape") != self.etape:
            return await _refus(
                interaction, "⚠️ Quelqu'un est passé avant toi : la fiche a "
                             "changé d'étape entre-temps.")

        await interaction.response.defer(ephemeral=True, thinking=True)
        await cog.avancer(interaction.guild, fiche, self.etape,
                          interaction.user,
                          note=str(self.note) or None,
                          lien=str(self.lien) or None)
        # On réécrit la fiche par son message enregistré : la soumission
        # d'un formulaire ne le porte pas forcément avec elle.
        await cog._reecrire(interaction.guild, fiche)

        suite = ("le chapitre est **prêt à sortir**" if fiche.get("termine")
                 else f"au tour de **{_libelle(fiche['etape'])}**")
        await interaction.followup.send(
            f"✅ **{_libelle(self.etape)}** validé — {suite}.", ephemeral=True)


class AvancementModal(discord.ui.Modal, title="Où tu en es"):
    """Le compte de pages, sans passer par une commande."""

    faites = discord.ui.TextInput(
        label="Pages faites pour cette étape",
        placeholder="14", required=True, max_length=4)
    total = discord.ui.TextInput(
        label="Total du chapitre (si ça a changé)",
        placeholder="20", required=False, max_length=4)

    def __init__(self, fiche):
        super().__init__()
        self.cle = fiche.get("cle")

    async def on_submit(self, interaction: discord.Interaction):
        cog, fiche = _contexte_cle(interaction, self.cle)
        if fiche is None:
            return await _refus(interaction, "❌ Cette fiche n'est plus suivie.")
        try:
            faites = int(str(self.faites).strip())
            total = int(str(self.total).strip()) if str(self.total).strip() \
                else fiche.get("pages")
        except ValueError:
            return await _refus(interaction, "❌ Des nombres, tout simplement.")
        if faites < 0 or (total and faites > total):
            return await _refus(
                interaction,
                f"❌ **{faites}** pages faites sur un chapitre qui en compte "
                f"**{total}** — l'un des deux nombres est de trop.")

        etape = fiche.get("etape")
        if total:
            fiche["pages"] = total
        fiche.setdefault("avancement", {})[etape] = faites
        fiche["avancement_le"] = time.time()
        cog.sauver()

        await interaction.response.defer(ephemeral=True, thinking=True)
        await cog._reecrire(interaction.guild, fiche)
        await cog._suivi_public(interaction.guild, fiche, maj=True)
        log.info("Atelier : %s — %s a %d/%s pages (bouton, par %s)",
                 fiche["cle"], etape, faites, fiche.get("pages"),
                 interaction.user)
        await interaction.followup.send(
            "📄 " + _ligne_pages(fiche, etape).replace("\n", " · "),
            ephemeral=True)


class MetierButton(discord.ui.Button):
    """Un maillon de la chaîne. Sa couleur dit où en est le chapitre.

    Vert : c'est fait. Bleu : c'est ton tour, clique quand tu as fini.
    Gris : pas encore. Cliquer sur un maillon qui n'est pas le sien ne
    casse rien — ça raconte juste où en est le chapitre.
    """

    def __init__(self, etape: str, fiche=None):
        info = ETAPE_INFO.get(etape, (etape, etape, "•", ""))
        faites = (fiche or {}).get("etapes", {})
        courante = (fiche or {}).get("etape")

        if etape in faites:
            style = discord.ButtonStyle.success
        elif fiche is not None and etape == courante and not fiche.get("termine"):
            style = discord.ButtonStyle.primary
        else:
            style = discord.ButtonStyle.secondary

        super().__init__(label=LIBELLE_COURT.get(etape, info[1]),
                         emoji=info[2], style=style, row=0,
                         custom_id=f"lanortrad:atelier_etape:{etape}")
        self.etape = etape

    async def callback(self, interaction: discord.Interaction):
        cog, fiche = _contexte(interaction)
        if fiche is None:
            return await _refus(interaction, "❌ Cette fiche n'est plus suivie.")

        fait = fiche.get("etapes", {}).get(self.etape)
        if fait:
            quand = f"<t:{int(fait.get('le') or 0)}:R>" if fait.get("le") else ""
            details = f"✅ **{_libelle(self.etape)}** — <@{fait.get('par')}> {quand}"
            if fait.get("lien"):
                details += f"\n🔗 {fait['lien']}"
            if fait.get("note"):
                details += f"\n> {fait['note']}"
            return await _refus(interaction, details)

        if fiche.get("termine"):
            return await _refus(
                interaction, "🎉 Ce chapitre est bouclé — il ne reste qu'à "
                             "le sortir.")

        courante = fiche.get("etape")
        if self.etape != courante:
            return await _refus(
                interaction,
                f"⏳ Pas encore : le chapitre en est à "
                f"**{_libelle(courante)}**.\nC'est ce bouton-là qui est en "
                "bleu — le tien s'allumera tout seul quand ce sera ton tour.")

        if not _peut_valider(interaction.user, self.etape):
            return await _refus(
                interaction,
                f"❌ **{_libelle(self.etape)}** est réservé à son métier.\n"
                f"On recrute, d'ailleurs : {SITE_URL}/equipe")

        await interaction.response.send_modal(FiniModal(fiche, self.etape))


class PrendreButton(discord.ui.Button):
    """Dire qu'on s'y met — pour que personne ne fasse le travail en double."""

    def __init__(self, fiche=None):
        pris = bool((fiche or {}).get("pris_par"))
        super().__init__(
            label="Je m'y mets", emoji="🙋", row=1,
            style=(discord.ButtonStyle.secondary if pris
                   else discord.ButtonStyle.primary),
            custom_id="lanortrad:atelier_prendre")

    async def callback(self, interaction: discord.Interaction):
        cog, fiche = _contexte(interaction)
        if fiche is None:
            return await _refus(interaction, "❌ Cette fiche n'est plus suivie.")
        if fiche.get("termine"):
            return await _refus(interaction, "✅ Ce chapitre est déjà terminé.")

        etape = fiche["etape"]
        if not _peut_valider(interaction.user, etape):
            return await _refus(
                interaction,
                f"❌ L'étape **{_libelle(etape)}** est réservée à son métier.\n"
                f"On recrute, d'ailleurs : {SITE_URL}/equipe")

        deja = fiche.get("pris_par")
        if deja and deja != interaction.user.id:
            membre = interaction.guild.get_member(deja)
            if membre is not None:
                return await _refus(
                    interaction,
                    f"⚠️ {membre.display_name} est déjà dessus. "
                    "Il faut qu'iel rende d'abord.")

        cog.attribuer(fiche, interaction.user.id)
        await cog.rafraichir(interaction, fiche)
        log.info("Atelier : %s pris par %s", fiche["cle"], interaction.user)


class AvancementButton(discord.ui.Button):
    """« J'en suis à 14 sur 20 » — un chiffre, rien d'autre."""

    def __init__(self):
        super().__init__(label="Où j'en suis", emoji="📄", row=1,
                         style=discord.ButtonStyle.secondary,
                         custom_id="lanortrad:atelier_avancement")

    async def callback(self, interaction: discord.Interaction):
        cog, fiche = _contexte(interaction)
        if fiche is None:
            return await _refus(interaction, "❌ Cette fiche n'est plus suivie.")
        if fiche.get("termine"):
            return await _refus(interaction, "✅ Ce chapitre est déjà terminé.")
        if not _peut_valider(interaction.user, fiche.get("etape")):
            return await _refus(
                interaction, "❌ Cette étape est réservée à son métier.")
        await interaction.response.send_modal(AvancementModal(fiche))


class RendreButton(discord.ui.Button):
    """Rendre l'étape, sans avoir à se justifier."""

    def __init__(self):
        super().__init__(label="Je rends", emoji="↩️", row=1,
                         style=discord.ButtonStyle.secondary,
                         custom_id="lanortrad:atelier_rendre")

    async def callback(self, interaction: discord.Interaction):
        cog, fiche = _contexte(interaction)
        if fiche is None:
            return await _refus(interaction, "❌ Cette fiche n'est plus suivie.")

        preneur = fiche.get("pris_par")
        if preneur is None:
            return await _refus(interaction, "ℹ️ Personne n'est dessus.")
        if preneur != interaction.user.id and not _peut_valider(
                interaction.user, DERNIERE):
            return await _refus(
                interaction,
                "❌ Seule la personne qui a pris l'étape (ou le staff) peut rendre.")

        _liberer(fiche)
        cog.sauver()
        await cog.rafraichir(interaction, fiche)
        log.info("Atelier : %s rendu par %s", fiche["cle"], interaction.user)


class RallongeButton(discord.ui.Button):
    """Repousse l'échéance sans avoir à se justifier."""

    def __init__(self):
        super().__init__(label="Plus de temps", emoji="⏰", row=1,
                         style=discord.ButtonStyle.secondary,
                         custom_id="lanortrad:atelier_rallonge")

    async def callback(self, interaction: discord.Interaction):
        cog, fiche = _contexte(interaction)
        if fiche is None:
            return await _refus(interaction, "❌ Cette fiche n'est plus suivie.")
        if fiche.get("pris_par") != interaction.user.id:
            return await _refus(
                interaction, "ℹ️ Seule la personne qui a pris l'étape peut "
                             "demander du temps.")
        if not fiche.get("echeance"):
            return await _refus(
                interaction, "ℹ️ Cette étape n'a pas d'échéance — prends "
                             "le temps qu'il te faut.")
        if fiche.get("rallonges", 0) >= ATELIER_RALLONGE_MAX:
            return await _refus(
                interaction,
                f"⚠️ Tu as déjà repoussé {ATELIER_RALLONGE_MAX} fois. Ce n'est "
                "pas grave : **↩️ Je rends** libère le chapitre, et tu pourras "
                "le reprendre quand tu auras le temps.")

        # On repart de maintenant si l'échéance est déjà passée : sinon une
        # rallonge prise en retard ne donnerait presque rien.
        base = max(fiche["echeance"], time.time())
        fiche["echeance"] = base + ATELIER_RALLONGE_JOURS * 86400
        fiche["rallonges"] = fiche.get("rallonges", 0) + 1
        fiche["rappels"] = []          # les rappels se réarment sur la nouvelle date
        cog.sauver()
        await cog.rafraichir(interaction, fiche)
        restant = ATELIER_RALLONGE_MAX - fiche["rallonges"]
        await interaction.followup.send(
            f"⏰ C'est noté : tu as **{ATELIER_RALLONGE_JOURS} jours de plus**, "
            f"jusqu'au <t:{int(fiche['echeance'])}:D>.\n"
            + (f"Il te reste {restant} rallonge(s)."
               if restant else
               "C'était la dernière — après, mieux vaut rendre."),
            ephemeral=True)
        log.info("Atelier : %s rallonge de %dj par %s",
                 fiche["cle"], ATELIER_RALLONGE_JOURS, interaction.user)


class FicheView(discord.ui.View):
    """La chaîne en haut, ce qu'on peut faire en bas.

    `FicheView()` sans fiche sert au rebranchement au démarrage : les
    `custom_id` sont les mêmes, seules les couleurs manquent — et elles
    ne servent qu'à l'affichage.
    """

    def __init__(self, fiche=None):
        super().__init__(timeout=None)
        for etape in ETAPES[:-1]:      # « sortie » n'est le métier de personne
            self.add_item(MetierButton(etape, fiche))
        self.add_item(PrendreButton(fiche))
        self.add_item(AvancementButton())
        self.add_item(RendreButton())
        self.add_item(RallongeButton())


# ═══════════════════════════════════════════════════════
# Le cog
# ═══════════════════════════════════════════════════════

class PrendreSelect(discord.ui.Select):
    """Prendre une étape libre sans quitter `/mes_taches`."""

    def __init__(self, fiches):
        options = []
        for fiche in fiches[:25]:
            info = ETAPE_INFO.get(fiche.get("etape"), ("", "?", "•", ""))
            jours = _delai_jours(fiche.get("etape"), fiche.get("pages"))
            detail = info[1]
            if fiche.get("pages"):
                detail += f" · {fiche['pages']} pages"
            if jours:
                detail += f" · {jours:.0f} jours"
            options.append(discord.SelectOption(
                label=(f"{MANGAS.get(fiche['manga'], {}).get('name', '?')} "
                       f"ch. {fiche['chapitre']}")[:100],
                value=fiche["cle"],
                description=detail[:100],
                emoji=info[2] or None))
        super().__init__(placeholder="🙋 Prendre une étape…", options=options,
                         min_values=1, max_values=1)

    async def callback(self, interaction: discord.Interaction):
        cog = interaction.client.get_cog("Atelier")
        fiche = cog._store.get("fiches", {}).get(self.values[0]) if cog else None
        if fiche is None or fiche.get("termine"):
            return await interaction.response.send_message(
                "❌ Cette fiche n'est plus disponible.", ephemeral=True)
        # Quelqu'un a pu la prendre entre l'affichage de la liste et le clic.
        if fiche.get("pris_par"):
            return await interaction.response.send_message(
                "⚠️ Quelqu'un vient de la prendre. `/mes_taches` pour "
                "rafraîchir la liste.", ephemeral=True)
        if not _peut_valider(interaction.user, fiche.get("etape")):
            return await interaction.response.send_message(
                f"❌ L'étape **{_libelle(fiche.get('etape'))}** est réservée "
                "à son métier.", ephemeral=True)

        cog.attribuer(fiche, interaction.user.id)
        await interaction.response.defer(ephemeral=True, thinking=True)
        await cog._reecrire(interaction.guild, fiche)

        echeance = fiche.get("echeance")
        quand = (f"À rendre <t:{int(echeance)}:R>." if echeance
                 else "Pas d'échéance sur cette étape : prends ton temps.")
        await interaction.followup.send(
            embed=brand_embed(
                interaction.guild, title="🙋 C'est à toi",
                description=(f"{_nom_manga(fiche['manga'])} — chapitre "
                             f"**{fiche['chapitre']}**, étape "
                             f"**{_libelle(fiche.get('etape'))}**.\n{quand}\n\n"
                             f"→ {fiche.get('url')}"),
                color=COLOR_SUCCESS),
            ephemeral=True)
        log.info("Atelier : %s pris par %s depuis /mes_taches",
                 fiche["cle"], interaction.user)


class MesTachesView(discord.ui.View):
    """Le menu de prise sous `/mes_taches`. Éphémère : pas de persistance."""

    def __init__(self, libres):
        super().__init__(timeout=180)
        if libres:
            self.add_item(PrendreSelect(libres))
class Atelier(commands.Cog):
    """Suivi de la fabrication, étape par étape."""

    def __init__(self, bot):
        self.bot = bot
        self._store = JSONStore(
            "atelier.json",
            default={"fiches": {}, "messages": {}, "fils": {}, "stock": {}})
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

    def attribuer(self, fiche, membre_id: int):
        """Pose l'étape sur quelqu'un, avec son échéance et des rappels neufs."""
        fiche["pris_par"] = membre_id
        fiche["pris_le"] = time.time()
        fiche["echeance"] = _echeance_pour(fiche)
        fiche["rallonges"] = 0
        fiche["rappels"] = []
        fiche.pop("libre_le", None)
        fiche.pop("rappels_libre", None)
        fiche.pop("staff_prevenu", None)
        fiche.pop("relances", None)
        fiche.pop("relance_le", None)
        self.sauver()

    def fiche(self, manga: str, chapitre: str):
        return self._store.get("fiches", {}).get(_cle(manga, chapitre))

    def fiche_par_cle(self, cle: str):
        return self._store.get("fiches", {}).get(cle) if cle else None

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
    # Le stock — ce qui est fait d'avance
    # ─────────────────────────────────────────────
    # Quarante-six chapitres nettoyés qui attendent la traduction, ce
    # n'est pas quarante-six fiches : c'est une ligne. Le détail vit dans
    # `bot/stock.py`, qui ne connaît rien à Discord.

    def stock(self, manga: str = None) -> list:
        """Les plages d'une série, ou de toutes, triées par numéro."""
        tout = self._store.get("stock", {}) or {}
        if manga is not None:
            return sorted(tout.get(manga, []), key=lambda p: p["de_n"])
        return sorted((p for lot in tout.values() for p in lot),
                      key=lambda p: p["de_n"])

    def _poser_stock(self, manga: str, plage: dict) -> list:
        entrepot = self._store.setdefault("stock", {})
        entrepot[manga] = stocklib.poser(entrepot.get(manga, []), plage)
        self.sauver()
        return entrepot[manga]

    def _retirer_stock(self, manga: str, de_n: float, a_n: float) -> list:
        """Efface des chapitres du stock. Rend ce qu'il reste pour la série."""
        entrepot = self._store.setdefault("stock", {})
        if manga not in entrepot:
            return []
        entrepot[manga] = stocklib.retirer(entrepot[manga], de_n, a_n)
        if not entrepot[manga]:
            entrepot.pop(manga)
        self.sauver()
        return entrepot.get(manga, [])

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

    def _couleur(self, fiche) -> int:
        """Neutre, puis orange quand l'échéance approche, rouge une fois passée."""
        reste = _reste_jours(fiche)
        if reste is None or not fiche.get("pris_par"):
            return COLOR_NEUTRAL
        if reste < 0:
            return COLOR_ERROR
        if reste <= 1:
            return COLOR_WARNING
        return COLOR_NEUTRAL

    def _ligne_echeance(self, fiche) -> str:
        """L'échéance de l'étape en cours, en une ligne."""
        echeance = fiche.get("echeance")
        if not echeance:
            return "⏱️ *pas d'échéance sur cette étape*"
        reste = _reste_jours(fiche)
        rallonges = fiche.get("rallonges", 0)
        suffixe = f" · {rallonges} rallonge(s)" if rallonges else ""
        if reste < 0:
            return f"🔴 **en retard** — c'était <t:{int(echeance)}:R>{suffixe}"
        if reste <= 1:
            return f"🟠 à rendre <t:{int(echeance)}:R>{suffixe}"
        return f"🕒 à rendre <t:{int(echeance)}:R>{suffixe}"

    def _embed(self, guild, fiche) -> discord.Embed:
        manga = fiche.get("manga", "")
        termine = fiche.get("termine")
        etape = fiche.get("etape")
        info = ETAPE_INFO.get(etape, (etape, etape, "•", ""))

        embed = brand_embed(
            guild,
            title=f"{_nom_manga(manga)} — chapitre {fiche.get('chapitre')}",
            description=self._progression(fiche),
            color=COLOR_SUCCESS if termine else self._couleur(fiche),
            url=manga_url(manga),
        )

        if fiche.get("pages") or fiche.get("depots") or fiche.get("avancement"):
            embed.add_field(name="📄 Pages", value=_bloc_pages(fiche), inline=True)

        if fiche.get("eta"):
            embed.add_field(name="🎯 Sortie visée",
                            value=f"**{fiche['eta']}**", inline=True)

        if termine:
            embed.add_field(
                name="🎉 Terminé",
                value="Prêt à sortir — `/release` pour publier.", inline=True)
        else:
            # Le rôle concerné est nommé ici : dans un embed, une mention
            # s'affiche sans pinger. Le panneau dit donc qui est attendu
            # sans réveiller le métier une deuxième fois.
            role = _role_de(guild, etape) if guild else None
            qui = f" — {role.mention}" if role else ""
            embed.add_field(
                name="🔄 Au tour de",
                value=f"{info[2]} **{info[1]}**{qui}"
                      + (f"\n*{info[3]}*" if info[3] else "")
                      + f"\n> Clique sur **{info[2]} "
                        f"{LIBELLE_COURT.get(etape, info[1])}** ci-dessous "
                        "quand c'est fait.",
                inline=False)
            preneur = fiche.get("pris_par")
            dort = _immobile_depuis(fiche)
            if preneur:
                valeur = (f"<@{preneur}> · depuis "
                          f"<t:{int(fiche.get('pris_le') or 0)}:R>")
                valeur += "\n" + self._ligne_echeance(fiche)
            else:
                valeur = "*personne pour l'instant*"
                jours = _delai_jours(etape, fiche.get("pages"))
                if jours:
                    valeur += f"\n⏱️ *compte {jours:.0f} jours une fois pris*"
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
            vue = FicheView(fiche)
            if deja_repondu:
                await interaction.message.edit(embed=embed, view=vue)
            else:
                await interaction.response.edit_message(embed=embed, view=vue)
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
                                   view=FicheView(fiche))
            else:
                await message.edit(embed=embed, view=FicheView(fiche))
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
        _liberer(fiche)                # la fiche a bougé : le suivi repart à zéro

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
    # Le suivi a son salon à lui (`suivi-fabrication`) : « alertes-sorties »
    # sert à prendre ses rôles de série et à recevoir les sorties, deux
    # publics qui ne se recouvrent pas. Tant que le salon dédié n'existe
    # pas, on retombe sur l'ancien plutôt que de se taire.

    def _salon_suivi(self, guild):
        for cle in (ATELIER_SUIVI_CHANNEL, ATELIER_SUIVI_CHANNEL_REPLI):
            salon_id = CHANNELS.get(cle)
            if not salon_id:
                continue
            salon = guild.get_channel(salon_id)
            if salon is not None:
                return salon
        return None

    def _texte_suivi(self, fiche) -> str:
        """Ce que lit un abonné : un chapitre qui avance, personne d'autre."""
        etape = fiche.get("etape")
        info = ETAPE_INFO.get(etape, (etape, etape, "•", ""))
        titre = f"{_nom_manga(fiche['manga'])} **ch. {fiche['chapitre']}**"

        if fiche.get("termine"):
            return (f"\U0001f389 {titre} est **bouclé**. "
                    "Il ne reste plus qu'à le mettre en ligne.")

        restantes = len(ETAPES) - 1 - ETAPES.index(etape)
        reste = ("dernière ligne droite" if restantes <= 1
                 else f"encore {restantes} étapes avant la sortie")
        lignes = [f"{info[2]} {titre} passe en **{info[1]}**.", f"*{info[3]}*"]

        # La jauge : c'est tout l'intérêt pour qui attend. Pas de nom, pas
        # de date d'échéance — juste le nombre de pages passées.
        total = fiche.get("pages")
        fait = _fait(fiche, etape)
        if total and fait:
            jauge = _jauge(fait, total)
            ligne = f"**{fait}/{total}** pages"
            lignes.append(f"{jauge} · {ligne}" if jauge else ligne)
        lignes.append(f"→ {reste}.")
        return "\n".join(lignes)

    async def _suivi_public(self, guild, fiche, *, maj=False):
        """Une ligne pour les lecteurs abonnés, sans rien d'interne.

        Ni note d'atelier, ni nom d'équipier : le public suit un chapitre,
        pas les gens qui le fabriquent.

        `maj=True` : l'avancement a bougé sans changer d'étape. On réécrit
        le message déjà posté au lieu d'en empiler un autre — la jauge
        monte sous les yeux de qui regarde, et personne n'est repingé.
        """
        if not ATELIER_SUIVI_PUBLIC:
            return
        etape = fiche.get("etape")
        if etape not in ATELIER_SUIVI_ETAPES:
            return

        salon = self._salon_suivi(guild)
        if salon is None:
            return

        corps = self._texte_suivi(fiche)
        suivi = fiche.get("suivi") or {}

        if maj:
            # Rien à réécrire (message effacé, étape changée entre-temps,
            # fiche d'avant cette version) : on ne poste surtout pas, ce
            # serait un ping de plus pour une jauge qui bouge.
            if not ATELIER_SUIVI_EDITE or suivi.get("etape") != etape:
                return
            salon_suivi = guild.get_channel(suivi.get("salon") or 0) or salon
            if not suivi.get("message"):
                return
            try:
                message = await salon_suivi.fetch_message(suivi["message"])
                # La première ligne porte la mention du rôle : on la garde
                # telle quelle, `allowed_mentions` empêchant qu'elle repingue.
                tete = (message.content.split("\n", 1)[0] + "\n"
                        if message.content.startswith("<@&") else "")
                await message.edit(
                    content=tete + corps,
                    allowed_mentions=discord.AllowedMentions.none())
            except (discord.NotFound, discord.HTTPException) as e:
                log.debug("Suivi public %s non reecrit : %s", fiche.get("cle"), e)
            return

        role_id = ROLES.get(ATELIER_SUIVI_ROLE)
        role = guild.get_role(role_id) if role_id else None
        texte = (f"{role.mention}\n{corps}" if role else corps)
        try:
            message = await salon.send(
                texte, allowed_mentions=discord.AllowedMentions(roles=True))
        except discord.HTTPException as e:
            return log.warning("Suivi public %s non envoye : %s",
                               fiche.get("cle"), e)

        fiche["suivi"] = {"salon": salon.id, "message": message.id,
                          "etape": etape}
        self.sauver()

    # ─────────────────────────────────────────────
    # Le fil du chapitre
    # ─────────────────────────────────────────────
    # Une commande slash ne prend pas vingt pièces jointes : chaque
    # pièce y est une option nommée, et le plafond est de 25 options
    # pour la commande entière. Les pages passent donc par un fil
    # attaché à la fiche, où le glisser-déposer marche normalement.
    # Le bot compte ce qui arrive et le reporte sur la fiche.

    async def _ouvrir_fil(self, message, fiche):
        """Crée le fil de la fiche et y explique quoi déposer."""
        if not ATELIER_FIL:
            return None
        try:
            fil = await message.create_thread(
                name=f"{MANGAS.get(fiche['manga'], {}).get('name', '?')} "
                     f"ch. {fiche['chapitre']}"[:100],
                auto_archive_duration=ATELIER_FIL_ARCHIVE)
        except discord.HTTPException as e:
            # Pas de droit de créer un fil, ou salon inéligible : la fiche
            # marche très bien sans, on ne bloque pas l'ouverture.
            log.warning("Fil de %s non cree : %s", fiche.get("cle"), e)
            return None

        fiche["fil"] = fil.id
        # Le fil d'un message public porte l'id de ce message, mais on
        # indexe quand même : on ne fait pas reposer la relecture des
        # dépôts sur une coïncidence d'identifiants.
        self._store.setdefault("fils", {})[str(fil.id)] = fiche["cle"]
        self.sauver()

        attendu = (f"les **{fiche['pages']}** pages" if fiche.get("pages")
                   else "les pages")
        try:
            await fil.send(
                f"📥 **Le dossier du chapitre**\n\n"
                f"Dépose {attendu} ici — Discord en prend **dix par message**, "
                "donc deux ou trois glisser-déposer suffisent. Le compte "
                "s'affiche tout seul sur la fiche.\n\n"
                "Le fil sert à toute la chaîne : le clean, la traduction et "
                "l'édition déposent leur rendu au même endroit, et le bot "
                "compte séparément pour chaque étape.")
        except discord.HTTPException as e:
            log.warning("Message d'accueil du fil %s non envoye : %s",
                        fiche.get("cle"), e)
        return fil

    def fiche_du_fil(self, fil_id: int):
        cle = self._store.get("fils", {}).get(str(fil_id))
        return self._store.get("fiches", {}).get(cle) if cle else None

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Compte les pages déposées dans le fil d'une fiche."""
        if message.author.bot or not message.attachments:
            return
        if not isinstance(message.channel, discord.Thread):
            return
        fiche = self.fiche_du_fil(message.channel.id)
        if fiche is None or fiche.get("termine"):
            return

        images = [p for p in message.attachments
                  if p.filename.rsplit(".", 1)[-1].lower() in EXTENSIONS_OK]
        if not images:
            return

        etape = fiche.get("etape")
        depots = fiche.setdefault("depots", {})
        avant = depots.get(etape, 0)
        depots[etape] = avant + len(images)
        self.sauver()

        # Fiche ouverte sans aperçu : la première page déposée l'illustre.
        # On la ré-héberge plutôt que de pointer l'URL du message, les
        # liens de pièces jointes Discord expirant au bout de quelques heures.
        fichier = None
        if not fiche.get("image"):
            ext = images[0].filename.rsplit(".", 1)[-1].lower()
            try:
                fichier = await images[0].to_file(filename=f"apercu.{ext}")
            except discord.HTTPException:
                fichier = None

        await self._reecrire(message.guild, fiche, fichier)
        await self._suivi_public(message.guild, fiche, maj=True)

        attendu = fiche.get("pages")
        if attendu and avant < attendu <= depots[etape]:
            info = ETAPE_INFO.get(etape, (etape, etape, "•", ""))
            try:
                await message.channel.send(
                    f"✅ **{depots[etape]}/{attendu}** — le compte y est "
                    f"pour le **{info[1]}**.")
            except discord.HTTPException:
                pass
        log.info("Atelier : %d page(s) deposee(s) sur %s (%s)",
                 len(images), fiche["cle"], etape)

    # ─────────────────────────────────────────────
    # Relance douce — en privé, jamais en public
    # ─────────────────────────────────────────────
    # Un seul passage s'occupe des deux façons dont un chapitre s'endort :
    # quelqu'un l'a pris et l'échéance file, ou personne ne l'a pris et le
    # métier ne le sait plus. Le premier cas se règle en MP, le second par
    # un rappel dans le salon. Aucun nom n'est cité en public.

    @tasks.loop(hours=ATELIER_RELANCE_INTERVALLE)
    async def relance(self):
        if not ATELIER_RELANCE:
            return
        guild = self.bot.get_guild(GUILD_ID)
        if guild is None:
            return

        for fiche in list(self._store.get("fiches", {}).values()):
            if fiche.get("termine"):
                continue
            try:
                if fiche.get("pris_par"):
                    await self._suivre_prise(guild, fiche)
                else:
                    await self._suivre_libre(guild, fiche)
            except Exception:
                log.exception("Atelier : suivi de %s impossible", fiche.get("cle"))

    async def _suivre_prise(self, guild, fiche):
        """L'étape est prise : on regarde où en est son échéance."""
        # Fiche prise avant l'arrivée des délais : on lui en donne une à
        # partir de sa date de prise, sans quoi elle n'en aurait jamais.
        if not fiche.get("echeance") and fiche.get("pris_le"):
            fiche["echeance"] = _echeance_pour(fiche, fiche["pris_le"])
            self.sauver()

        membre = guild.get_member(fiche["pris_par"])
        if membre is None:
            return

        if not fiche.get("echeance"):
            return await self._relance_sans_echeance(fiche, membre)

        reste = _reste_jours(fiche)

        if ATELIER_LIBERATION and reste <= -ATELIER_LIBERATION_JOURS:
            return await self._liberer_etape(guild, fiche, membre)

        if reste <= -ATELIER_RAPPEL_RETARD_JOURS:
            etiquette = "retard"
        elif reste <= 0:
            etiquette = "jour_j"
        elif reste <= 1:
            etiquette = "veille"
        else:
            return

        envoyes = fiche.setdefault("rappels", [])
        if etiquette in envoyes:
            return
        envoyes.append(etiquette)
        self.sauver()

        await self._mp_echeance(fiche, membre, etiquette)
        if etiquette == "retard":
            await self._prevenir_staff(guild, fiche, membre)

    async def _mp_echeance(self, fiche, membre, etiquette):
        """Le rappel privé, dans le ton qui va avec le moment."""
        info = ETAPE_INFO.get(fiche.get("etape"), ("", "?", "•", ""))
        titre = f"{_nom_manga(fiche['manga'])} ch. {fiche['chapitre']}"
        echeance = int(fiche["echeance"])
        rallonge = (f"Le bouton **⏰ Plus de temps** ajoute "
                    f"{ATELIER_RALLONGE_JOURS} jours, sans avoir à se justifier.")
        rendre = ("Le bouton **↩️ Je rends** libère le chapitre pour "
                  "quelqu'un d'autre. Personne ne te demandera pourquoi.")

        if etiquette == "veille":
            corps = (f"{info[2]} **Ça arrive bientôt**\n\n"
                     f"Le **{info[1]}** de {titre} est à rendre "
                     f"<t:{echeance}:R>.\n\n"
                     f"Si c'est trop juste : {rallonge[0].lower()}{rallonge[1:]}")
        elif etiquette == "jour_j":
            corps = (f"{info[2]} **L'échéance est là**\n\n"
                     f"Le **{info[1]}** de {titre} était à rendre "
                     f"<t:{echeance}:R>. Rien de grave — c'est un repère, "
                     "pas un couperet.\n\n"
                     f"{rallonge}\n{rendre}")
        else:
            marge = ATELIER_LIBERATION_JOURS - ATELIER_RAPPEL_RETARD_JOURS
            fin = (f"\n\nSans nouvelle, l'étape se libérera toute seule d'ici "
                   f"{marge} jours et retournera au pot commun. Ce n'est pas "
                   "un reproche : tu pourras la reprendre quand tu veux."
                   if ATELIER_LIBERATION else "")
            corps = (f"{info[2]} **On en est où ?**\n\n"
                     f"Le **{info[1]}** de {titre} a dépassé son échéance "
                     f"de {abs(_reste_jours(fiche)):.0f} jours.\n\n"
                     f"{rallonge}\n{rendre}{fin}")

        try:
            await membre.send(f"{corps}\n\n→ {fiche.get('url', '')}")
            log.info("Atelier : rappel %s envoye a %s pour %s",
                     etiquette, membre, fiche["cle"])
        except discord.HTTPException:
            # MP fermés : le rappel reste marqué comme envoyé, sinon on
            # réessaierait à chaque passage pour rien.
            log.info("Atelier : MP impossible pour %s", membre)

    async def _relance_sans_echeance(self, fiche, membre):
        """Étape sans délai configuré : l'ancienne relance douce suffit."""
        if fiche.get("relances", 0) >= ATELIER_RELANCE_MAX:
            return
        if _immobile_depuis(fiche) < ATELIER_RELANCE_JOURS:
            return
        depuis = (time.time() - (fiche.get("relance_le") or 0)) / 86400
        if fiche.get("relance_le") and depuis < ATELIER_RELANCE_JOURS:
            return

        info = ETAPE_INFO.get(fiche.get("etape"), ("", "?", "•", ""))
        try:
            await membre.send(
                f"{info[2]} **Petit rappel, sans pression**\n\n"
                f"Tu as pris le **{info[1]}** de "
                f"{_nom_manga(fiche['manga'])} ch. {fiche['chapitre']} "
                f"il y a {_immobile_depuis(fiche):.0f} jours.\n\n"
                "Si tu es toujours dessus, ignore ce message — il ne "
                "reviendra pas avant plusieurs jours.\n"
                "Si tu n'as plus le temps, le bouton **↩️ Je rends** "
                "libère le chapitre pour quelqu'un d'autre.\n\n"
                f"→ {fiche.get('url', '')}")
        except discord.HTTPException:
            log.info("Atelier : MP impossible pour %s", membre)

        fiche["relances"] = fiche.get("relances", 0) + 1
        fiche["relance_le"] = time.time()
        self.sauver()

    async def _liberer_etape(self, guild, fiche, membre):
        """L'étape retourne au pot commun, et le métier est repingé."""
        info = ETAPE_INFO.get(fiche.get("etape"), ("", "?", "•", ""))
        titre = f"{_nom_manga(fiche['manga'])} ch. {fiche['chapitre']}"
        _liberer(fiche)
        self.sauver()

        try:
            await membre.send(
                f"{info[2]} **Le {info[1]} de {titre} est reparti "
                "au pot commun**\n\n"
                "Ce n'est pas un reproche et ça ne compte nulle part : un "
                "chapitre qui dort bloque toute la chaîne derrière lui, alors "
                "le bot le remet à disposition tout seul.\n\n"
                "Si tu veux le reprendre, le bouton **🙋 Je prends** est "
                "toujours là.\n\n"
                f"→ {fiche.get('url', '')}")
        except discord.HTTPException:
            log.info("Atelier : MP de liberation impossible pour %s", membre)

        await self._reecrire(guild, fiche)
        await self._reping(guild, fiche, libere=True)
        log.info("Atelier : %s libere automatiquement (etait a %s)",
                 fiche["cle"], membre)

    async def _suivre_libre(self, guild, fiche):
        """Personne n'a pris l'étape : le métier finit par l'oublier."""
        if not ATELIER_RAPPEL_LIBRE_JOURS:
            return
        # `libre_le` date la mise à disposition ; sans lui (fiche d'avant la
        # mise à jour), l'immobilité de la fiche fait le même office.
        depuis = ((time.time() - fiche["libre_le"]) / 86400
                  if fiche.get("libre_le") else _immobile_depuis(fiche))
        if depuis < ATELIER_RAPPEL_LIBRE_JOURS:
            return

        envoyes = fiche.get("rappels_libre", 0)
        if envoyes >= ATELIER_RAPPEL_LIBRE_MAX:
            # On a assez insisté auprès du métier : au staff de trancher.
            if not fiche.get("staff_prevenu"):
                fiche["staff_prevenu"] = True
                self.sauver()
                await self._prevenir_staff(guild, fiche, None)
            return

        fiche["rappels_libre"] = envoyes + 1
        fiche["libre_le"] = time.time()
        self.sauver()
        await self._reping(guild, fiche, jours=depuis)

    async def _reping(self, guild, fiche, *, libere=False, jours=None):
        """Repose la main sur l'épaule du métier, dans le salon d'atelier."""
        salon = guild.get_channel(fiche.get("salon") or 0)
        if salon is None:
            return
        etape = fiche.get("etape")
        role = _role_de(guild, etape)
        info = ETAPE_INFO.get(etape, (etape, etape, "•", ""))
        qui = role.mention if role else f"**{info[1]}**"
        titre = f"{_nom_manga(fiche['manga'])} ch. {fiche['chapitre']}"

        if libere:
            texte = (f"{qui} — {info[2]} **{titre}** est de nouveau libre : "
                     f"l'étape **{info[1]}** attend quelqu'un.\n"
                     f"{fiche.get('url', '')}")
        else:
            texte = (f"{qui} — {info[2]} **{titre}** attend toujours son "
                     f"**{info[1]}**"
                     + (f", depuis {jours:.0f} jours" if jours else "")
                     + f".\n{fiche.get('url', '')}")

        try:
            await salon.send(texte,
                             allowed_mentions=discord.AllowedMentions(roles=True))
        except discord.HTTPException as e:
            log.warning("Rappel %s non envoye : %s", fiche.get("cle"), e)

    async def _prevenir_staff(self, guild, fiche, membre):
        """Le staff voit ce qui coince. Salon d'équipe, jamais public."""
        salon_id = CHANNELS.get(ATELIER_STAFF_CHANNEL)
        salon = guild.get_channel(salon_id) if salon_id else None
        if salon is None:
            return
        info = ETAPE_INFO.get(fiche.get("etape"), ("", "?", "•", ""))
        titre = f"{_nom_manga(fiche['manga'])} ch. {fiche['chapitre']}"

        if membre is not None:
            retard = abs(_reste_jours(fiche) or 0)
            corps = (f"⚠️ **{titre}** — le **{info[1]}** de "
                     f"{membre.mention} a {retard:.0f} jours de retard.\n"
                     "La personne a été prévenue en privé"
                     + (f" ; l'étape se libérera toute seule d'ici "
                        f"{max(0, ATELIER_LIBERATION_JOURS - retard):.0f} jours."
                        if ATELIER_LIBERATION else "."))
        else:
            corps = (f"⚠️ **{titre}** — l'étape **{info[1]}** n'a trouvé "
                     f"personne après {ATELIER_RAPPEL_LIBRE_MAX} rappels au "
                     "métier. À voir : relancer à la main, ou confier le "
                     "chapitre à quelqu'un.")

        try:
            await salon.send(
                f"{corps}\n{fiche.get('url', '')}",
                allowed_mentions=discord.AllowedMentions(users=False))
        except discord.HTTPException as e:
            log.warning("Alerte staff %s non envoyee : %s", fiche.get("cle"), e)

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
        pages="Nombre de pages que compte le chapitre",
        trouvees="Pages déjà récupérées, si le lot est incomplet (défaut : toutes)",
        apercu="Une page en aperçu (facultatif : le fil accueille les pages)",
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
        trouvees: app_commands.Range[int, 0, 400] = None,
        apercu: discord.Attachment = None,
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

        if trouvees is not None and trouvees > pages:
            return await interaction.response.send_message(
                f"❌ **{trouvees}** pages trouvées pour un chapitre qui en "
                f"compte **{pages}** : l'un des deux nombres est de trop.",
                ephemeral=True)

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
            "image": fichiers[0].filename if fichiers else None,
            "source": source,
            "ouvert_le": time.time(),
            "libre_le": time.time(),
            "pris_par": None,
            "pris_le": None,
            "depots": {},
            # Le lot peut être incomplet : trois raws manquantes se voient
            # tout de suite sur la fiche plutôt qu'au moment de l'édition.
            "avancement": {"pages": pages if trouvees is None else trouvees},
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
                                       view=FicheView(fiche))
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

        # Ce chapitre avait peut-être une plage de stock à son nom. La
        # fiche est plus précise qu'une plage : elle prend la main, et le
        # stock se réduit d'autant plutôt que d'annoncer deux vérités.
        couvert = stocklib.contient(self.stock(manga.value), chapitre)
        if couvert is not None:
            n = stocklib.num(chapitre)
            self._retirer_stock(manga.value, n, n)

        # Le fil ouvert, la fiche le mentionne : on la réécrit une fois.
        fil = await self._ouvrir_fil(message, fiche)
        if fil is not None:
            await self._reecrire(interaction.guild, fiche)

        await self._prevenir(interaction.guild, fiche)
        # Le suivi public commence ici. `avancer()` n'est jamais appelé pour
        # l'étape « pages » — sans cette ligne, les abonnés n'apprenaient
        # jamais qu'un chapitre entrait en clean, alors que l'étape figure
        # bien dans ATELIER_SUIVI_ETAPES. C'est aussi le message que les
        # dépôts du fil réécriront ensuite, jauge comprise.
        await self._suivi_public(interaction.guild, fiche)
        log.info("Atelier : fiche ouverte %s (%d pages) par %s",
                 fiche["cle"], pages, interaction.user)

        await interaction.followup.send(
            embed=brand_embed(
                interaction.guild, title="✅ Fiche ouverte",
                description=(
                    f"{_nom_manga(manga.value)} — chapitre **{chapitre}**, "
                    f"**{pages}** pages.\n"
                    + (f"⚠️ **{trouvees}** seulement de récupérées — "
                       "`/atelier_avancement` pour compléter.\n"
                       if trouvees is not None and trouvees < pages else "")
                    + ("📦 Ce chapitre était en stock — il en sort, la fiche "
                       "fait foi.\n" if couvert is not None else "")
                    + (f"Prochaine étape : **{_libelle(fiche['etape'])}**\n")
                    + (f"📥 Dépose les pages dans <#{fiche['fil']}> — "
                       "dix par message.\n" if fiche.get("fil") else "")
                    + f"→ {message.jump_url}"),
                color=COLOR_SUCCESS),
            ephemeral=True)

    # ─────────────────────────────────────────────
    # /atelier_avancement — la moitié du chemin, ça se dit
    # ─────────────────────────────────────────────
    # Le fil compte ce qu'on y dépose, mais le clean se fait dans
    # Photoshop et la traduction dans un doc : le travail existe souvent
    # avant d'arriver ici. Cette commande dit simplement où on en est.
    @app_commands.command(
        name="atelier_avancement",
        description="Où en est une étape : 14 pages sur 20")
    @app_commands.describe(
        manga="La série", chapitre="Numéro du chapitre",
        faites="Nombre de pages faites pour l'étape",
        etape="Quelle étape (par défaut : celle en cours)",
        total="Corrige le nombre de pages du chapitre, si besoin")
    @app_commands.choices(
        manga=MANGA_CHOICES,
        etape=[app_commands.Choice(name=f"{e[2]} {e[1]}", value=e[0])
               for e in sitelib.STEPS if e[0] != "sortie"])
    @app_commands.guilds(GUILD)
    async def atelier_avancement(
        self, interaction: discord.Interaction,
        manga: app_commands.Choice[str], chapitre: str,
        faites: app_commands.Range[int, 0, 400],
        etape: app_commands.Choice[str] = None,
        total: app_commands.Range[int, 1, 400] = None,
    ):
        fiche = self.fiche(manga.value, chapitre)
        if fiche is None:
            return await interaction.response.send_message(
                f"❌ Aucune fiche pour **{_nom_manga(manga.value)} "
                f"ch. {str(chapitre).strip()}**.\n"
                "Elle s'ouvre avec `/atelier_raws`.", ephemeral=True)

        cible = etape.value if etape else (fiche.get("etape") or "pages")
        if cible == DERNIERE:
            return await interaction.response.send_message(
                "❌ La **sortie** ne se compte pas en pages.", ephemeral=True)
        if not _peut_valider(interaction.user, cible):
            return await interaction.response.send_message(
                f"❌ L'étape **{_libelle(cible)}** est réservée à son métier.\n"
                f"On recrute : {SITE_URL}/equipe", ephemeral=True)

        attendu = total or fiche.get("pages")
        if attendu and faites > attendu:
            return await interaction.response.send_message(
                f"❌ **{faites}** pages faites sur un chapitre qui en compte "
                f"**{attendu}**. Passe `total:` si c'est le total qui a changé.",
                ephemeral=True)

        if total:
            fiche["pages"] = total
        fiche.setdefault("avancement", {})[cible] = faites
        fiche["avancement_le"] = time.time()
        self.sauver()

        await interaction.response.defer(ephemeral=True, thinking=True)
        await self._reecrire(interaction.guild, fiche)
        # Étape en cours : les abonnés voient la jauge monter sur le message
        # déjà posté. Une étape corrigée après coup ne réveille personne.
        if cible == fiche.get("etape"):
            await self._suivi_public(interaction.guild, fiche, maj=True)

        log.info("Atelier : %s — %s a %d/%s pages (par %s)",
                 fiche["cle"], cible, faites, fiche.get("pages"),
                 interaction.user)

        retenu = _fait(fiche, cible)
        reste = (fiche["pages"] - retenu) if fiche.get("pages") else None
        # Le fil a peut-être déjà reçu plus que le nombre annoncé : on ne
        # défait pas du travail qu'on a vu passer, mais on le dit.
        ecart = ""
        if retenu > faites:
            ecart = (f"\n*Le fil a déjà reçu **{retenu}** pages pour cette "
                     "étape : c'est ce compte-là qui reste affiché.*")
        await interaction.followup.send(
            embed=brand_embed(
                interaction.guild, title="📄 Avancement noté",
                description=(
                    f"{_nom_manga(manga.value)} — chapitre "
                    f"**{fiche['chapitre']}**\n"
                    + _ligne_pages(fiche, cible) + ecart
                    + (f"\n\nIl reste **{reste}** page(s)." if reste
                       else "\n\nL'étape est au complet.")
                    + f"\n→ {fiche.get('url')}"),
                color=COLOR_SUCCESS),
            ephemeral=True)

    atelier_avancement.autocomplete("chapitre")(_ac_chapitre)

    # ─────────────────────────────────────────────
    # /atelier_stock — ce qui est fait d'avance
    # ─────────────────────────────────────────────
    # « Pages trouvées et clean du 248 au 293 » : quarante-six chapitres
    # qui attendent la traduction. Une fiche chacun, ce serait quarante-six
    # messages, quarante-six fils, et le métier repingué tous les trois
    # jours pour rien. Une plage le dit en une ligne, sans réveiller
    # personne — la fiche viendra quand le chapitre entrera vraiment en
    # fabrication.
    @app_commands.command(
        name="atelier_stock",
        description="Déclare une plage de chapitres déjà avancés (sans fiche)")
    @app_commands.describe(
        manga="La série",
        du="Premier chapitre de la plage (44, 45.5…)",
        au="Dernier chapitre de la plage",
        fait="La dernière étape TERMINÉE sur ces chapitres",
        note="Une précision qui vaut pour toute la plage (facultatif)")
    @app_commands.choices(manga=MANGA_CHOICES, fait=FAIT_CHOICES)
    @app_commands.guilds(GUILD)
    async def atelier_stock(
        self, interaction: discord.Interaction,
        manga: app_commands.Choice[str],
        du: app_commands.Range[str, 1, 12],
        au: app_commands.Range[str, 1, 12],
        fait: app_commands.Choice[str],
        note: app_commands.Range[str, 1, 300] = None,
    ):
        try:
            de_n, a_n = stocklib.num(du), stocklib.num(au)
        except ValueError:
            return await interaction.response.send_message(
                "❌ Les chapitres s'écrivent en chiffres — `44`, `45.5`, `293`.",
                ephemeral=True)

        etape_faite = None if fait.value == "aucune" else fait.value
        # Le droit suit le travail : c'est le métier qui a fait l'étape
        # qui l'annonce (le staff passe partout, comme ailleurs).
        garde = etape_faite or "pages"
        if not _peut_valider(interaction.user, garde):
            return await interaction.response.send_message(
                f"❌ L'étape **{_libelle(garde)}** est réservée à son métier.\n"
                f"On recrute : {SITE_URL}/equipe", ephemeral=True)

        plage = stocklib.plage(du, au, etape_faite, note=note,
                               le=time.time(), par=interaction.user.id)
        restant = self._poser_stock(manga.value, plage)

        log.info("Atelier : stock %s %s→%s (%s fait) par %s",
                 manga.value, plage["de"], plage["a"],
                 etape_faite or "rien", interaction.user)

        lignes = [stocklib.ligne(p) for p in restant]
        # Les fiches ouvertes sur ces chapitres priment : elles sont plus
        # précises que la plage, et on ne veut pas deux vérités.
        doublons = [f["chapitre"] for f in self.en_cours(manga.value)
                    if stocklib.contient([plage], f.get("chapitre"))]

        await interaction.response.send_message(
            embed=brand_embed(
                interaction.guild, title="📦 Stock mis à jour",
                description=(
                    f"{_nom_manga(manga.value)}\n\n" + "\n".join(lignes)
                    + ("\n\n⚠️ Fiche(s) déjà ouverte(s) sur cette plage : "
                       + ", ".join(f"ch. {c}" for c in doublons)
                       + "\nLa fiche fait foi pour ces chapitres — "
                         "`/atelier_stock_retirer` pour les sortir du stock."
                       if doublons else "")
                    + "\n\n`/atelier_pousser` pour le reporter sur le site."),
                color=COLOR_SUCCESS),
            ephemeral=True)

    @app_commands.command(
        name="atelier_stock_retirer",
        description="Efface une plage de chapitres du stock")
    @app_commands.describe(manga="La série",
                           du="Premier chapitre à retirer",
                           au="Dernier chapitre à retirer (défaut : le même)")
    @app_commands.choices(manga=MANGA_CHOICES)
    @app_commands.guilds(GUILD)
    async def atelier_stock_retirer(
        self, interaction: discord.Interaction,
        manga: app_commands.Choice[str],
        du: app_commands.Range[str, 1, 12],
        au: app_commands.Range[str, 1, 12] = None,
    ):
        try:
            de_n = stocklib.num(du)
            a_n = stocklib.num(au) if au else de_n
        except ValueError:
            return await interaction.response.send_message(
                "❌ Les chapitres s'écrivent en chiffres — `44`, `45.5`, `293`.",
                ephemeral=True)
        if de_n > a_n:
            de_n, a_n = a_n, de_n

        avant = self.stock(manga.value)
        if not avant:
            return await interaction.response.send_message(
                f"📭 **{_nom_manga(manga.value)}** n'a rien en stock.",
                ephemeral=True)
        if not _peut_valider(interaction.user, DERNIERE):
            return await interaction.response.send_message(
                "❌ Retirer du stock est réservé au staff.", ephemeral=True)

        restant = self._retirer_stock(manga.value, de_n, a_n)
        log.info("Atelier : stock %s — %s→%s retire par %s",
                 manga.value, stocklib.label(de_n), stocklib.label(a_n),
                 interaction.user)

        corps = ("\n".join(stocklib.ligne(p) for p in restant) if restant
                 else "*plus rien en stock pour cette série.*")
        await interaction.response.send_message(
            embed=brand_embed(
                interaction.guild, title="📦 Stock allégé",
                description=(f"{_nom_manga(manga.value)} — chapitres "
                             f"**{stocklib.label(de_n)} → "
                             f"{stocklib.label(a_n)}** retirés.\n\n{corps}"),
                color=COLOR_SUCCESS),
            ephemeral=True)

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

        entrepot = {cle: lot for cle, lot in
                    (self._store.get("stock", {}) or {}).items()
                    if lot and (not manga or cle == manga.value)}

        if not fiches and not entrepot:
            return await interaction.response.send_message(
                embed=brand_embed(
                    interaction.guild, title="📭 Atelier vide",
                    description="Aucun chapitre en fabrication."
                                + ("" if tout else "\n`tout:True` pour voir "
                                   "les chapitres déjà terminés.")
                                + "\n`/atelier_stock` pour déclarer ce qui "
                                  "est déjà fait d'avance.",
                    color=COLOR_WARNING),
                ephemeral=True)

        # Regroupé par série, comme sur le site — fiches et stock ensemble :
        # une série peut n'avoir que l'un ou que l'autre.
        par_serie = {}
        for fiche in fiches:
            par_serie.setdefault(fiche.get("manga"), []).append(fiche)
        for cle_manga in entrepot:
            par_serie.setdefault(cle_manga, [])

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
                    reste = _reste_jours(fiche)
                    if preneur and reste is not None:
                        etat += (f" 🔴 {abs(reste):.0f}j de retard" if reste < 0
                                 else f" 🕒 {reste:.0f}j")
                    dort = _immobile_depuis(fiche)
                    if dort >= ATELIER_RELANCE_JOURS:
                        etat += f" ⏳ {dort:.0f}j"
                lignes.append(f"**ch. {fiche.get('chapitre')}** · {etat} · "
                              f"[fiche]({fiche.get('url')})")
            reste_fiches = len(lot) - len(lignes)
            if reste_fiches > 0:
                lignes.append(f"*…et {reste_fiches} fiche(s) de plus.*")

            # Le stock ferme le bloc : il se lit comme une réserve derrière
            # les chapitres en cours, pas comme du travail en attente d'être
            # pris tout de suite.
            for p in sorted(entrepot.get(cle_manga, []),
                            key=lambda x: x["de_n"]):
                lignes.append("📦 " + stocklib.ligne(p))
            blocs.append(f"{_nom_manga(cle_manga)}\n" + "\n".join(lignes))

        libres = sum(1 for f in fiches
                     if not f.get("termine") and not f.get("pris_par"))
        en_stock = sum(stocklib.compte(p)
                       for lot in entrepot.values() for p in lot)
        pied = (f"\n\n**{libres}** étape(s) sans personne dessus "
                f"sur {len(fiches)} fiche(s).")
        if en_stock:
            pied += (f"\n📦 **~{en_stock}** chapitre(s) d'avance en stock — "
                     "`/atelier_stock` pour le corriger.")
        await interaction.response.send_message(
            embed=brand_embed(
                interaction.guild, title="🏭 L'atelier en ce moment",
                description=("\n\n".join(blocs) + pied)[:4096],
                color=COLOR_NEUTRAL),
            ephemeral=True)

    # ─────────────────────────────────────────────
    # /mes_taches — l'établi personnel
    # ─────────────────────────────────────────────
    def _propositions(self, membre):
        """Les étapes libres qu'on peut proposer à cette personne.

        Son métier d'abord. Si elle n'en a pas mais peut quand même valider
        (staff), on lui montre tout plutôt que rien.
        """
        strictes, larges = [], []
        for fiche in self.en_cours():
            if fiche.get("pris_par"):
                continue
            etape = fiche.get("etape")
            if _est_du_metier(membre, etape):
                strictes.append(fiche)
            elif _peut_valider(membre, etape):
                larges.append(fiche)
        return strictes or larges

    @app_commands.command(
        name="mes_taches",
        description="Ce que tu as pris, et ce qui attend ton métier")
    @app_commands.guilds(GUILD)
    async def mes_taches(self, interaction: discord.Interaction):
        moi = interaction.user.id
        prises = [f for f in self.en_cours() if f.get("pris_par") == moi]
        # L'échéance la plus proche en premier ; celles qui n'en ont pas
        # ferment la marche.
        prises.sort(key=lambda f: f.get("echeance") or float("inf"))
        libres = self._propositions(interaction.user)

        retard = sum(1 for f in prises if (_reste_jours(f) or 0) < 0)
        embed = brand_embed(
            interaction.guild,
            title="🎒 Ton établi",
            color=COLOR_ERROR if retard else
                  (COLOR_NEUTRAL if prises else COLOR_WARNING),
        )

        if prises:
            lignes = []
            for fiche in prises:
                info = ETAPE_INFO.get(fiche.get("etape"), ("", "?", "•", ""))
                lignes.append(
                    f"{info[2]} **{_nom_manga(fiche['manga'])} ch. "
                    f"{fiche['chapitre']}** — {info[1]}\n"
                    f"{self._ligne_echeance(fiche)} · [fiche]({fiche.get('url')})")
            embed.add_field(name=f"🙋 Tu as pris ({len(prises)})",
                            value="\n\n".join(lignes[:8])[:1024], inline=False)
        else:
            embed.add_field(
                name="🙋 Tu as pris",
                value="*rien pour l'instant — l'établi est vide.*", inline=False)

        if libres:
            lignes = []
            for fiche in libres[:8]:
                info = ETAPE_INFO.get(fiche.get("etape"), ("", "?", "•", ""))
                jours = _delai_jours(fiche.get("etape"), fiche.get("pages"))
                delai = f" · {jours:.0f} j" if jours else ""
                pages = f" · {fiche['pages']} p." if fiche.get("pages") else ""
                lignes.append(
                    f"{info[2]} **{_nom_manga(fiche['manga'])} ch. "
                    f"{fiche['chapitre']}** — {info[1]}{pages}{delai}")
            reste = len(libres) - len(lignes)
            valeur = "\n".join(lignes)
            if reste > 0:
                valeur += f"\n*…et {reste} autre(s).*"
            embed.add_field(name=f"🫱 Libre pour toi ({len(libres)})",
                            value=valeur[:1024], inline=False)
        else:
            embed.add_field(
                name="🫱 Libre pour toi",
                value="*rien n'attend ton métier — tout est pris.*", inline=False)

        if retard:
            embed.description = (
                f"⚠️ **{retard}** de tes étapes ont dépassé leur échéance. "
                "Le bouton **⏰ Plus de temps** existe pour ça, et **↩️ Je "
                "rends** aussi — aucun des deux ne se paie.")

        await interaction.response.send_message(
            embed=embed, view=MesTachesView(libres), ephemeral=True)

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
        _liberer(fiche)
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
        self._store.setdefault("fils", {}).pop(str(fiche.get("fil")), None)
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
        noms = self._noms_site()
        depuis_bot, remarques = siteexport.entrees_depuis_fiches(fiches, noms)
        # Le stock complète : une série sans fiche ouverte a quand même de
        # quoi dire au site si elle a des chapitres d'avance.
        depuis_stock, notes_stock = siteexport.entrees_depuis_stock(
            self._store.get("stock", {}), noms, deja=depuis_bot)
        depuis_bot.update(depuis_stock)
        remarques.extend(notes_stock)
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
