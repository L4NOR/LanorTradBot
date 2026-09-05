"""
Atelier — dépôt des pages RAW
==============================
Le site affiche où en est chaque chapitre. Ce cog sert à l'étape juste
avant : quand quelqu'un a trouvé et remis au propre les pages japonaises,
il les dépose ici, et le clean sait qu'il peut commencer.

  /atelier_raws    — dépose un lot de pages (manga, chapitre, nombre, aperçu)
  /atelier_liste   — les lots qui attendent encore un preneur
  /atelier_retirer — retire un lot déposé par erreur

Le message posté est un embed avec l'aperçu des pages et deux boutons :
« 🧽 Je prends le clean » et « ↩️ Je rends ». Un clic suffit pour que tout
le monde sache qui s'en occupe — personne n'a besoin de l'écrire, et deux
personnes ne cleanent pas le même chapitre en parallèle.

Les lots survivent aux redémarrages (data/atelier.json), donc les boutons
restent cliquables même après un `pm2 restart`.
"""
import logging
import time

import discord
from discord import app_commands
from discord.ext import commands

from bot.config import (
    GUILD_ID, MANGAS, CHANNELS, ROLES, SITE_URL,
    COLOR_NEUTRAL, COLOR_SUCCESS, COLOR_WARNING,
    ATELIER_CHANNEL, ATELIER_PING_ROLE, ATELIER_DEPOSER_ROLES,
    ATELIER_CLEAN_ROLES,
    manga_url,
)
from bot.embeds import brand_embed
from bot.storage import JSONStore

log = logging.getLogger("lanortrad.atelier")

GUILD = discord.Object(id=GUILD_ID) if GUILD_ID else None

# Étapes de fabrication (mêmes libellés que le site) — l'étape qui suit un
# dépôt de RAW est toujours le clean.
ETAPE_SUIVANTE = ("🧽", "Clean")

CHAMP_STATUT = "📌 Statut"
STATUT_LIBRE = "🟡 Personne dessus — le clean peut démarrer."

MANGA_CHOICES = [
    app_commands.Choice(name=f"{m['emoji']} {m['name']}", value=cle)
    for cle, m in MANGAS.items()
]

EXTENSIONS_OK = ("png", "jpg", "jpeg", "webp", "gif")


def _a_un_role(member: discord.Member, cles) -> bool:
    """True si le membre porte l'un des rôles listés (ou est admin)."""
    if member.guild_permissions.administrator:
        return True
    ids = {ROLES.get(c) for c in cles} - {None}
    return any(r.id in ids for r in member.roles)


def _nom_manga(cle: str) -> str:
    info = MANGAS.get(cle, {})
    return f"{info.get('emoji', '📖')} {info.get('name', cle)}"


class LotView(discord.ui.View):
    """Boutons persistants d'un lot de RAW (prendre / rendre)."""

    def __init__(self):
        super().__init__(timeout=None)

    # ── outils partagés par les deux boutons ──
    def _cog(self, interaction):
        return interaction.client.get_cog("Atelier")

    async def _maj(self, interaction, statut: str):
        """Réécrit le champ Statut de l'embed sans toucher aux aperçus."""
        embeds = list(interaction.message.embeds)
        if not embeds:
            return
        principal = embeds[0]
        for i, champ in enumerate(principal.fields):
            if champ.name == CHAMP_STATUT:
                principal.set_field_at(i, name=CHAMP_STATUT, value=statut,
                                       inline=False)
                break
        else:
            principal.add_field(name=CHAMP_STATUT, value=statut, inline=False)
        await interaction.response.edit_message(embeds=embeds, view=self)

    @discord.ui.button(label="Je prends le clean", emoji="🧽",
                       style=discord.ButtonStyle.success,
                       custom_id="lanortrad:atelier_prendre")
    async def prendre(self, interaction: discord.Interaction, _button):
        cog = self._cog(interaction)
        if cog is None:
            await interaction.response.send_message(
                "❌ Le module atelier n'est pas chargé.", ephemeral=True)
            return

        if not _a_un_role(interaction.user, ATELIER_CLEAN_ROLES):
            await interaction.response.send_message(
                "❌ Ce bouton est réservé à l'équipe clean. Si tu veux nous "
                f"rejoindre, tout est expliqué sur {SITE_URL}/equipe.",
                ephemeral=True)
            return

        lot = cog.lot(interaction.message.id)
        if lot and lot.get("pris_par"):
            deja = interaction.guild.get_member(lot["pris_par"])
            if deja and deja.id != interaction.user.id:
                await interaction.response.send_message(
                    f"⚠️ {deja.display_name} s'en occupe déjà. "
                    "Utilise le bouton « Je rends » s'il faut reprendre.",
                    ephemeral=True)
                return

        cog.marquer(interaction.message.id, interaction.user.id)
        await self._maj(
            interaction,
            f"🧽 Clean pris par {interaction.user.mention} "
            f"· <t:{int(time.time())}:R>")
        log.info("Atelier : lot %s pris par %s",
                 interaction.message.id, interaction.user)

    @discord.ui.button(label="Je rends", emoji="↩️",
                       style=discord.ButtonStyle.secondary,
                       custom_id="lanortrad:atelier_rendre")
    async def rendre(self, interaction: discord.Interaction, _button):
        cog = self._cog(interaction)
        if cog is None:
            await interaction.response.send_message(
                "❌ Le module atelier n'est pas chargé.", ephemeral=True)
            return

        lot = cog.lot(interaction.message.id) or {}
        preneur = lot.get("pris_par")
        if preneur is None:
            await interaction.response.send_message(
                "ℹ️ Ce lot n'est pris par personne.", ephemeral=True)
            return
        if preneur != interaction.user.id and not _a_un_role(
                interaction.user, ("founder", "moderator")):
            await interaction.response.send_message(
                "❌ Seule la personne qui a pris le lot (ou un modérateur) "
                "peut le rendre.", ephemeral=True)
            return

        cog.marquer(interaction.message.id, None)
        await self._maj(interaction, STATUT_LIBRE)
        log.info("Atelier : lot %s rendu par %s",
                 interaction.message.id, interaction.user)


class Atelier(commands.Cog):
    """Dépôt et suivi des pages RAW."""

    def __init__(self, bot):
        self.bot = bot
        self._store = JSONStore("atelier.json", default={"lots": {}})

    async def cog_load(self):
        self.bot.add_view(LotView())

    # ─────────────────────────────────────────────
    # État des lots
    # ─────────────────────────────────────────────
    def lot(self, message_id: int):
        return self._store.get("lots", {}).get(str(message_id))

    def marquer(self, message_id: int, membre_id):
        lots = self._store.setdefault("lots", {})
        entree = lots.get(str(message_id))
        if entree is None:
            return
        entree["pris_par"] = membre_id
        entree["pris_le"] = time.time() if membre_id else None
        self._store.save()

    def _enregistrer(self, message, manga, chapitre, pages, auteur_id):
        lots = self._store.setdefault("lots", {})
        lots[str(message.id)] = {
            "manga": manga,
            "chapitre": chapitre,
            "pages": pages,
            "auteur": auteur_id,
            "salon": message.channel.id,
            "message": message.id,
            "url": message.jump_url,
            "depose_le": time.time(),
            "pris_par": None,
            "pris_le": None,
        }
        self._store.save()

    # ─────────────────────────────────────────────
    # Où poster
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

    # ─────────────────────────────────────────────
    # /atelier_raws
    # ─────────────────────────────────────────────
    @app_commands.command(
        name="atelier_raws",
        description="Dépose un lot de pages RAW pour l'atelier")
    @app_commands.describe(
        manga="La série concernée",
        chapitre="Numéro du chapitre (58, 58.5…)",
        pages="Nombre de pages dans le lot",
        apercu="Une page en aperçu (image)",
        apercu2="Aperçu supplémentaire (facultatif)",
        apercu3="Aperçu supplémentaire (facultatif)",
        apercu4="Aperçu supplémentaire (facultatif)",
        source="D'où viennent les pages (facultatif)",
        note="Précision pour le clean : pages doubles, couleurs, souci…",
        salon="Poster ailleurs que dans le salon habituel")
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
        if not _a_un_role(interaction.user, ATELIER_DEPOSER_ROLES):
            await interaction.response.send_message(
                "❌ Seule l'équipe peut déposer des RAW. Les candidatures "
                f"sont ouvertes sur {SITE_URL}/equipe.", ephemeral=True)
            return

        images = [a for a in (apercu, apercu2, apercu3, apercu4) if a]
        mauvaises = [
            a.filename for a in images
            if a.filename.rsplit(".", 1)[-1].lower() not in EXTENSIONS_OK
        ]
        if mauvaises:
            await interaction.response.send_message(
                "❌ Aperçus refusés (image attendue) : "
                + ", ".join(f"`{n}`" for n in mauvaises)
                + f"\nFormats acceptés : {', '.join(EXTENSIONS_OK)}.",
                ephemeral=True)
            return

        cible = self._salon(interaction.guild, salon)
        if cible is None:
            await interaction.response.send_message(
                "❌ Aucun salon d'atelier trouvé. Crée un salon `pages-raws` "
                "ou précise-le avec l'option `salon`.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True, thinking=True)

        chapitre = chapitre.strip()
        lien = manga_url(manga.value)

        fichiers = []
        for i, piece in enumerate(images, start=1):
            ext = piece.filename.rsplit(".", 1)[-1].lower()
            try:
                fichiers.append(await piece.to_file(filename=f"raw{i}.{ext}"))
            except discord.HTTPException as e:
                await interaction.followup.send(
                    f"❌ Aperçu `{piece.filename}` illisible : {e}",
                    ephemeral=True)
                return

        principal = brand_embed(
            interaction.guild,
            title=f"📥 Pages RAW · {MANGAS[manga.value]['name']} — chapitre {chapitre}",
            description=note or "Les pages sont prêtes à être nettoyées.",
            color=COLOR_NEUTRAL,
            url=lien,
        )
        principal.add_field(name="📄 Pages", value=f"**{pages}** pages", inline=True)
        principal.add_field(name="➡️ Étape suivante",
                            value=f"{ETAPE_SUIVANTE[0]} {ETAPE_SUIVANTE[1]}",
                            inline=True)
        principal.add_field(name="📥 Déposé par",
                            value=interaction.user.mention, inline=True)
        if source:
            principal.add_field(name="🔎 Source", value=source, inline=False)
        principal.add_field(name=CHAMP_STATUT, value=STATUT_LIBRE, inline=False)
        principal.set_image(url=f"attachment://{fichiers[0].filename}")

        # Des embeds qui partagent la même URL sont regroupés en galerie
        # par Discord : c'est ainsi qu'on montre plusieurs pages d'un coup.
        embeds = [principal]
        for fichier in fichiers[1:]:
            extra = discord.Embed(url=lien, color=COLOR_NEUTRAL)
            extra.set_image(url=f"attachment://{fichier.filename}")
            embeds.append(extra)

        role_id = ROLES.get(ATELIER_PING_ROLE) if ATELIER_PING_ROLE else None
        role = interaction.guild.get_role(role_id) if role_id else None

        try:
            message = await cible.send(
                content=role.mention if role else None,
                embeds=embeds, files=fichiers, view=LotView(),
                allowed_mentions=discord.AllowedMentions(roles=True))
        except discord.Forbidden:
            await interaction.followup.send(
                f"❌ Je n'ai pas le droit d'écrire dans {cible.mention}. "
                "Lance `/perms_salons` ou donne-moi l'accès à la main.",
                ephemeral=True)
            return
        except discord.HTTPException as e:
            await interaction.followup.send(
                f"❌ Discord a refusé le message : ```{e}```", ephemeral=True)
            return

        self._enregistrer(message, manga.value, chapitre, pages,
                          interaction.user.id)
        log.info("Atelier : %s ch.%s (%d pages) depose par %s",
                 manga.value, chapitre, pages, interaction.user)

        await interaction.followup.send(
            embed=brand_embed(
                interaction.guild,
                title="✅ Lot déposé",
                description=(
                    f"{_nom_manga(manga.value)} — chapitre **{chapitre}**, "
                    f"**{pages}** pages, {len(fichiers)} aperçu(s).\n"
                    f"→ {message.jump_url}"
                    + (f"\n\n{role.mention} a été prévenu." if role else "")),
                color=COLOR_SUCCESS),
            ephemeral=True)

    # ─────────────────────────────────────────────
    # /atelier_liste
    # ─────────────────────────────────────────────
    @app_commands.command(
        name="atelier_liste",
        description="Les lots de RAW déposés et leur statut")
    @app_commands.describe(
        manga="Filtrer sur une série",
        tout="True = montre aussi les lots déjà pris")
    @app_commands.choices(manga=MANGA_CHOICES)
    @app_commands.guilds(GUILD)
    async def atelier_liste(self, interaction: discord.Interaction,
                            manga: app_commands.Choice[str] = None,
                            tout: bool = False):
        lots = list(self._store.get("lots", {}).values())
        if manga:
            lots = [l for l in lots if l.get("manga") == manga.value]
        if not tout:
            lots = [l for l in lots if not l.get("pris_par")]
        lots.sort(key=lambda l: l.get("depose_le", 0), reverse=True)

        if not lots:
            await interaction.response.send_message(
                embed=brand_embed(
                    interaction.guild,
                    title="📭 Rien en attente",
                    description="Aucun lot de RAW ne dort dans l'atelier."
                                + ("" if tout else
                                   "\nRelance avec `tout:True` pour voir les "
                                   "lots déjà pris."),
                    color=COLOR_WARNING),
                ephemeral=True)
            return

        lignes = []
        for lot in lots[:20]:
            preneur = lot.get("pris_par")
            statut = (f"🧽 <@{preneur}>" if preneur else "🟡 libre")
            lignes.append(
                f"{_nom_manga(lot.get('manga', ''))} **ch. {lot.get('chapitre')}** "
                f"· {lot.get('pages')} p. · {statut} · "
                f"[voir]({lot.get('url')})")

        libres = sum(1 for l in lots if not l.get("pris_par"))
        await interaction.response.send_message(
            embed=brand_embed(
                interaction.guild,
                title="🗂️ Atelier — lots de RAW",
                description="\n".join(lignes)
                + f"\n\n**{libres}** lot(s) sans preneur sur {len(lots)} affiché(s).",
                color=COLOR_NEUTRAL),
            ephemeral=True)

    # ─────────────────────────────────────────────
    # /atelier_retirer
    # ─────────────────────────────────────────────
    @app_commands.command(
        name="atelier_retirer",
        description="Retire un lot de RAW déposé par erreur")
    @app_commands.describe(
        message_id="ID du message du lot (clic droit → Copier l'identifiant)",
        supprimer="True = supprime aussi le message dans le salon")
    @app_commands.guilds(GUILD)
    async def atelier_retirer(self, interaction: discord.Interaction,
                              message_id: str, supprimer: bool = True):
        lot = self.lot(message_id)
        if lot is None:
            await interaction.response.send_message(
                "❌ Aucun lot enregistré sous cet ID.", ephemeral=True)
            return
        if (lot.get("auteur") != interaction.user.id
                and not _a_un_role(interaction.user, ("founder", "moderator"))):
            await interaction.response.send_message(
                "❌ Seul l'auteur du dépôt (ou un modérateur) peut le retirer.",
                ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True, thinking=True)

        efface = False
        if supprimer:
            salon = interaction.guild.get_channel(lot.get("salon", 0))
            if salon is not None:
                try:
                    message = await salon.fetch_message(int(message_id))
                    await message.delete()
                    efface = True
                except (discord.NotFound, discord.HTTPException):
                    pass

        self._store.setdefault("lots", {}).pop(str(message_id), None)
        self._store.save()

        await interaction.followup.send(
            embed=brand_embed(
                interaction.guild,
                title="🗑️ Lot retiré",
                description=(
                    f"{_nom_manga(lot.get('manga', ''))} — chapitre "
                    f"**{lot.get('chapitre')}** ne figure plus dans l'atelier."
                    + ("\nLe message a été supprimé." if efface else
                       "\nLe message d'origine, lui, est resté en place.")),
                color=COLOR_SUCCESS),
            ephemeral=True)


async def setup(bot):
    await bot.add_cog(Atelier(bot))
