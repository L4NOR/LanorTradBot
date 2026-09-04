"""
Contenus de référence — les pages fixes du serveur
====================================================
Reprend les messages explicatifs que le bot « template » postait à la
création du serveur, mais côté bot : on peut les republier à tout moment,
et ils se mettent à jour tout seuls (mentions de salons, liens du site).

  /publier <page>   — (staff) poste ou remplace une page dans son salon
  /publier tout     — remet en place l'ensemble des pages

Pages disponibles : bienvenue · règles · faq · le-site · forum · lexique
                    · recrutement

Le bot retient l'ID du message posté : republier **édite** le message
existant au lieu d'en empiler un nouveau.
"""
import logging

import discord
from discord import app_commands
from discord.ext import commands

from bot.config import GUILD_ID, CHANNELS, SITE, RECRUIT_POSTS, RECRUIT_TEST_DELAY
from bot.storage import JSONStore

log = logging.getLogger("lanortrad.content")

GUILD = discord.Object(id=GUILD_ID) if GUILD_ID else None

SEP = "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"


def _postes():
    return "\n\n".join(
        f"{emoji}  **{label.upper()}**\n{desc}"
        for key, label, emoji, role_key, desc in RECRUIT_POSTS
    )


# ═══════════════════════════════════════════════════════
# Les pages
# ═══════════════════════════════════════════════════════
# {alertes} {support} {recrutement} {incidents} sont remplacés par les
# mentions réelles des salons au moment de la publication.

PAGES = {
    "bienvenue": {
        "channel": "welcome",
        "title": "👋 Bienvenue",
        "body": (
            "# 🩸 Bienvenue chez **LanorTrad**\n\n"
            "On est **trois**. On traduit, on nettoie, on relit, et on publie "
            "des mangas en français — gratuitement, sur notre temps libre.\n\n"
            f"{SEP}\n\n"
            "## ✿ CE SERVEUR SERT À TROIS CHOSES\n\n"
            "🔔  **Être prévenu·e des sorties**\n"
            "Choisis tes séries dans {alertes} : tu reçois un ping dès qu'un "
            "chapitre sort, et seulement pour celles qui t'intéressent.\n\n"
            "🎫  **Nous parler en privé**\n"
            "Une question, une faute repérée, un signalement → {support}.\n\n"
            "📋  **Rejoindre l'équipe**\n"
            "On recrute en permanence → {recrutement}.\n\n"
            f"{SEP}\n\n"
            "## ✿ ET POUR DISCUTER ?\n\n"
            "**Sur le site, pas ici.** Le forum de la communauté est là :\n"
            f"🔗 {SITE['forum']}\n\n"
            "Théories, réactions, suggestions de séries, entraide : tout s'y "
            "passe, avec un vrai compte et des fils qui ne se perdent pas au "
            "bout de trois jours. On a préféré **un seul endroit vivant** "
            "plutôt que deux à moitié morts.\n\n"
            f"{SEP}\n\n"
            "## ✿ LIRE LES CHAPITRES\n\n"
            f"📚  Catalogue → {SITE['catalogue']}\n"
            f"📅  Planning → {SITE['planning']}\n"
            f"👥  L'équipe → {SITE['equipe']}\n\n"
            "🩸  *LanorTrad — là où les chapitres prennent vie.*"
        ),
    },
    "règles": {
        "channel": "rules",
        "title": "📜 Règles",
        "body": (
            "# 📜 Les règles, version courte\n\n"
            f"{SEP}\n\n"
            "**1 · Respect.** Pas d'insulte, pas de harcèlement, pas de "
            "discrimination. Aucune tolérance, aucune exception.\n\n"
            "**2 · Pas de spoiler** hors contexte. Sur le forum du site, "
            "utilise les balises prévues.\n\n"
            "**3 · Pas de pub.** Ni serveur, ni site concurrent, ni lien "
            "d'affiliation.\n\n"
            "**4 · Ne redistribue pas nos scans.** Ni sur un autre site, ni "
            "sur une plateforme de lecture. On traduit gratuitement : on "
            "demande juste ça.\n\n"
            "**5 · Un ticket = une demande.** N'en ouvre pas trois pour la "
            "même chose.\n\n"
            "**6 · Les MP à l'équipe, non.** Passe par {support} : c'est "
            "suivi, tracé, et quelqu'un finit toujours par répondre.\n\n"
            f"{SEP}\n\n"
            "En restant sur ce serveur, tu acceptes ces règles. Le staff peut "
            "sanctionner sans préavis en cas d'abus.\n\n"
            "🩸  *LanorTrad*"
        ),
    },
    "faq": {
        "channel": "faq",
        "title": "❓ FAQ",
        "body": (
            "# ❓ Questions fréquentes\n\n"
            f"{SEP}\n\n"
            "**Où est-ce que je lis les chapitres ?**\n"
            f"Sur le site : {SITE['catalogue']} — gratuitement, sans compte "
            "obligatoire.\n\n"
            "**Pourquoi il n'y a pas de salon de discussion ici ?**\n"
            f"Parce qu'il y en a déjà un, en mieux : {SITE['forum']}. Deux "
            "endroits communautaires, ça finit toujours par en tuer un.\n\n"
            "**Quand sort le prochain chapitre ?**\n"
            f"Le planning est à jour en direct : {SITE['planning']} — tu y "
            "vois même à quelle étape en est chaque chapitre. Sur Discord, "
            "`/planning` et `/atelier` te donnent la même chose.\n\n"
            "**Pourquoi c'est parfois long ?**\n"
            "Un chapitre passe une bonne dizaine d'heures entre nos mains : "
            "pages, clean, traduction, édition, q-check. À trois, sur notre "
            "temps libre.\n\n"
            "**Comment je suis prévenu·e des sorties ?**\n"
            "Prends les rôles de tes séries dans {alertes}.\n\n"
            "**Je peux aider ?**\n"
            "Oui, et avec plaisir → {recrutement}. Aucune expérience "
            "obligatoire pour le clean et le q-check : on forme.\n\n"
            "**J'ai trouvé une faute dans un chapitre.**\n"
            "Dis-le-nous dans {support} : on corrige et on republie.\n\n"
            "**Le site ne marche pas.**\n"
            "Regarde {incidents} : si c'est de notre côté, c'est écrit là.\n\n"
            "🩸  *LanorTrad*"
        ),
    },
    "le-site": {
        "channel": "site_links",
        "title": "🌐 Le site",
        "body": (
            "# 🌐 Le site LanorTrad\n\n"
            f"{SEP}\n\n"
            f"## 🏠 Accueil\n{SITE['accueil']}\n"
            "Les tendances, les derniers chapitres, et ta lecture en cours.\n\n"
            f"## 📚 Catalogue\n{SITE['catalogue']}\n"
            "Toutes les séries et les oneshots. Filtres par statut, type et "
            "genre — et un bouton « Surprends-moi » quand tu ne sais pas quoi "
            "lire.\n\n"
            f"## 📅 Planning\n{SITE['planning']}\n"
            "Le jour de parution de chaque série, et l'avancement en direct "
            "de chaque chapitre : pages → clean → traduction → édition → "
            "q-check → sortie.\n\n"
            f"## 💬 Forum\n{SITE['forum']}\n"
            "Annonces · Discussions · Suggestions · Aide · Off-topic.\n\n"
            f"## 👥 L'équipe\n{SITE['equipe']}\n"
            "Lanor (édition & clean) · Taichoskii (traduction) · Zerox (q-check).\n\n"
            "🩸  *Tout est gratuit. Toujours.*"
        ),
    },
    "forum": {
        "channel": "site_forum",
        "title": "💬 Le forum",
        "body": (
            "# 💬 La discussion, c'est sur le forum\n\n"
            f"👉  **{SITE['forum']}**\n\n"
            f"{SEP}\n\n"
            "## ✿ POURQUOI LÀ-BAS ET PAS ICI\n\n"
            "• Les fils **ne se perdent pas** au bout de trois jours\n"
            "• On peut **chercher** dans les anciennes discussions\n"
            "• Ça reste lisible pour ceux qui arrivent des mois plus tard\n"
            "• Et surtout : **un seul endroit vivant** vaut mieux que deux à "
            "moitié morts\n\n"
            f"{SEP}\n\n"
            "## ✿ LES RUBRIQUES\n\n"
            "📢  **Annonces** — les annonces officielles\n"
            "💬  **Discussions** — mangas, manhwas, webtoons\n"
            "💡  **Suggestions** — propose une série à traduire\n"
            "🛟  **Aide** — une question, un souci\n"
            "🎲  **Off-topic** — tout le reste\n\n"
            "*Compte créé en 30 secondes. À tout de suite.*\n\n"
            "🩸  *LanorTrad*"
        ),
    },
    "lexique": {
        "channel": "faq",
        "title": "📚 Lexique scantrad",
        "body": (
            "# 📚 Le lexique du scantrad\n\n"
            "Tu débutes ? Voici les termes qu'on emploie tout le temps, dans "
            "l'ordre où un chapitre les traverse.\n\n"
            f"{SEP}\n\n"
            "📥  **PAGES / RAW**\n"
            "Le chapitre original japonais, récupéré et remis au propre.\n\n"
            "🧽  **CLEAN**\n"
            "On efface les textes d'origine et on redessine ce qui passait "
            "dessous — décors, trames, onomatopées.\n\n"
            "💬  **TRADUCTION**\n"
            "Le chapitre passe du japonais au français, réplique par réplique.\n\n"
            "✍️  **EDIT (typesetting)**\n"
            "Le texte français est placé dans les bulles, avec les bonnes "
            "polices et les bonnes tailles.\n\n"
            "🔍  **Q-CHECK**\n"
            "Dernière relecture avant publication : fautes, sens, cohérence, "
            "oublis. Rien ne sort sans ce feu vert.\n\n"
            "🎉  **SORTIE**\n"
            "C'est en ligne. Bonne lecture.\n\n"
            f"{SEP}\n\n"
            "**SCANLATION** — le pipeline complet, de la RAW à la sortie.\n"
            "**ONESHOT** — une histoire complète en un seul chapitre.\n"
            "**ARC** — un ensemble de chapitres formant une même intrigue.\n\n"
            f"📅  Tu peux suivre chaque étape en direct : {SITE['planning']}\n"
            "Ou taper `/atelier` ici.\n\n"
            "🩸  *LanorTrad*"
        ),
    },
    "recrutement": {
        "channel": "recrutement",
        "title": "📋 Recrutement",
        "body": (
            "# 🤝 Rejoindre la team LanorTrad\n\n"
            "On recrute **en permanence**. On est trois : chaque paire de "
            "mains en plus, c'est un chapitre qui sort plus vite.\n\n"
            f"{SEP}\n\n"
            "## ✿ LES POSTES\n\n"
            + _postes() + "\n\n"
            f"{SEP}\n\n"
            "## ✿ COMMENT ÇA SE PASSE\n\n"
            "**1️⃣**  Tu remplis le formulaire ci-dessous (2 minutes)\n"
            "**2️⃣**  Le staff t'envoie un **test technique**\n"
            f"**3️⃣**  Tu as **{RECRUIT_TEST_DELAY} h** pour le rendre\n"
            "**4️⃣**  Retour détaillé, puis période d'essai sur 1-2 chapitres\n"
            "**5️⃣**  Si l'essai passe : intégration officielle 🩸\n\n"
            f"{SEP}\n\n"
            "⚠️  **Engagement attendu** : environ un chapitre par semaine.\n"
            "On préfère **la régularité à la rapidité**.\n\n"
            "*Aucune expérience obligatoire pour le clean et le q-check : "
            "on forme.*\n\n"
            "🩸  *We're a team. Everyone matters.*"
        ),
    },
}


class Content(commands.Cog):
    """Publication et mise à jour des pages de référence."""

    def __init__(self, bot):
        self.bot = bot
        self._store = JSONStore("content.json", default={"messages": {}})

    def _refs(self, guild) -> dict:
        """Mentions réelles des salons cités dans les pages."""
        def mention(key, fallback):
            ch_id = CHANNELS.get(key)
            channel = guild.get_channel(ch_id) if ch_id else None
            return channel.mention if channel else fallback

        return {
            "alertes": mention("notifications", "#alertes-sorties"),
            "support": mention("tickets", "#support"),
            "recrutement": mention("recrutement", "#recrutement"),
            "incidents": mention("incidents", "#incidents"),
        }

    @staticmethod
    def _split(text: str, limit: int = 1900):
        """Découpe un long texte sans casser les paragraphes."""
        if len(text) <= limit:
            return [text]
        chunks, current = [], ""
        for block in text.split("\n\n"):
            if len(current) + len(block) + 2 > limit:
                chunks.append(current.rstrip())
                current = ""
            current += block + "\n\n"
        if current.strip():
            chunks.append(current.rstrip())
        return chunks

    async def publish(self, guild, page_key: str) -> str:
        """Publie ou met à jour une page. Retourne une ligne de compte rendu."""
        page = PAGES[page_key]
        ch_id = CHANNELS.get(page["channel"])
        channel = guild.get_channel(ch_id) if ch_id else None
        if channel is None:
            return f"⏭️ `{page_key}` — salon introuvable (`{page['channel']}`)"

        body = page["body"].format(**self._refs(guild))
        parts = self._split(body)
        stored = self._store.setdefault("messages", {})
        known = stored.get(page_key, [])

        # Même découpage qu'avant : on édite au lieu de republier
        if len(known) == len(parts):
            try:
                for msg_id, content in zip(known, parts):
                    message = await channel.fetch_message(int(msg_id))
                    await message.edit(content=content)
                return f"♻️ `{page_key}` — mise à jour dans {channel.mention}"
            except (discord.NotFound, discord.HTTPException):
                pass       # message supprimé entre-temps : on republie

        ids = []
        try:
            for content in parts:
                message = await channel.send(content)
                ids.append(message.id)
            try:
                await message.pin(reason="Page de référence")
            except discord.HTTPException:
                pass
        except discord.Forbidden:
            return f"❌ `{page_key}` — je ne peux pas écrire dans {channel.mention}"
        except discord.HTTPException as e:
            return f"❌ `{page_key}` — {e}"

        stored[page_key] = ids
        self._store.save()
        log.info("Page %s publiée dans #%s", page_key, channel.name)
        return f"✅ `{page_key}` — publiée dans {channel.mention}"

    @app_commands.command(
        name="publier",
        description="(Staff) Publie ou met à jour une page de référence")
    @app_commands.describe(page="La page à publier (ou « tout »)")
    @app_commands.choices(page=[
        app_commands.Choice(name="Tout republier", value="tout"),
    ] + [
        app_commands.Choice(name=f"{info['title']}", value=key)
        for key, info in PAGES.items()
    ])
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.guilds(GUILD)
    async def publier(self, interaction: discord.Interaction,
                      page: app_commands.Choice[str]):
        await interaction.response.defer(ephemeral=True, thinking=True)
        keys = list(PAGES) if page.value == "tout" else [page.value]
        lines = [await self.publish(interaction.guild, key) for key in keys]
        await interaction.followup.send("\n".join(lines), ephemeral=True)


async def setup(bot):
    await bot.add_cog(Content(bot))
