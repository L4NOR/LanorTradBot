"""
Processus d'accueil natif Discord
===================================
Configure les questions posées au nouveau membre AVANT qu'il entre :
il choisit ses séries, Discord lui attribue les rôles et lui montre les
salons correspondants. Plus fluide qu'un panneau à cliquer une fois entré.

  /onboarding_setup   — écrit les questions et l'écran de bienvenue
  /onboarding_etat    — dit ce qui manque pour que Discord accepte

discord.py n'expose pas cette API : on appelle donc la route brute
`PUT /guilds/{id}/onboarding`. Les rôles sont désignés par leurs **IDs**
(ceux de config.py), jamais par leur nom — pas d'ambiguïté possible.

Deux exigences de Discord, qu'aucun code ne peut contourner :
  • la fonctionnalité Communauté doit être activée
  • au moins un salon par défaut doit être ouvert à l'écriture pour @everyone
"""
import logging

import discord
from discord import app_commands
from discord.ext import commands

from bot.config import (
    GUILD_ID, CHANNELS, ROLES, SITE_URL,
    COLOR_SUCCESS, COLOR_WARNING, COLOR_ERROR,
)
from bot.embeds import brand_embed

log = logging.getLogger("lanortrad.onboarding")

GUILD = discord.Object(id=GUILD_ID) if GUILD_ID else None


# Chaque option : (titre, description, emoji, [clés de ROLES], [clés de CHANNELS])
QUESTIONS = [
    {
        "title": "Quelles séries suis-tu ?",
        "single_select": False,
        "required": False,
        "options": [
            ("Tougen Anki", "Prévenu à chaque nouveau chapitre",
             "🗡️", ["ping_tougen"], ["sorties_fr"]),
            ("Ao No Exorcist", "Prévenu à chaque nouveau chapitre",
             "🩸", ["ping_ao"], ["sorties_fr"]),
            ("Tokyo Underworld", "Prévenu à chaque nouveau chapitre",
             "🏙️", ["ping_tokyo"], ["sorties_fr"]),
            ("Catenaccio", "Prévenu à chaque nouveau chapitre",
             "⚽", ["ping_cat"], ["sorties_fr"]),
            ("Satsudou", "Prévenu à chaque nouveau chapitre",
             "🔪", ["ping_sat"], ["sorties_fr"]),
            ("Oneshots", "Countdown · Kalavinka · In the White · Sake to Sakana…",
             "📜", ["ping_one"], ["sorties_fr"]),
        ],
    },
    {
        "title": "Qu'est-ce qui t'amène ?",
        "single_select": False,
        "required": False,
        "options": [
            ("Lire les chapitres", "Le catalogue et le planning sont sur le site",
             "📚", [], ["site_links", "planning"]),
            ("Dire bonjour", "Présente-toi en arrivant",
             "👋", [], ["presentations", "welcome"]),
            ("Rejoindre l'équipe", "Pages · clean · traduction · édition · q-check",
             "🛠️", [], ["recrutement"]),
            ("Poser une question", "L'équipe répond en privé",
             "🎫", [], ["tickets", "faq"]),
        ],
    },
    {
        "title": "Veux-tu être prévenu·e du reste ?",
        "single_select": False,
        "required": False,
        "options": [
            ("Toutes les sorties", "Un ping à chaque chapitre, toutes séries confondues",
             "🔔", ["ping_all"], ["sorties_fr"]),
            ("Annonces", "Les annonces officielles de l'équipe",
             "📢", ["ping_announcements"], ["announcements"]),
        ],
    },
]

# Salons mis en avant sur l'écran de bienvenue : (clé, description, emoji)
ECRAN_ACCUEIL = [
    ("welcome",       "Comment marche ce serveur", "👋"),
    ("notifications", "Choisis tes séries",        "🔔"),
    ("site_links",    "Lire les chapitres",        "📚"),
]

DESCRIPTION_ACCUEIL = (
    "🩸 Team scantrad française. Choisis tes séries : "
    "on te prévient à chaque nouveau chapitre."
)


class Onboarding(commands.Cog):
    """Processus d'accueil natif."""

    def __init__(self, bot):
        self.bot = bot

    # ─────────────────────────────────────────────
    @staticmethod
    def _salon(guild, cle):
        ch_id = CHANNELS.get(cle)
        return guild.get_channel(ch_id) if ch_id else None

    def _diagnostic(self, guild):
        """Ce qui manque pour que Discord accepte la configuration."""
        manques = []
        if "COMMUNITY" not in guild.features:
            manques.append("La fonctionnalité **Communauté** n'est pas activée "
                           "(Paramètres du serveur → Activer la communauté).")

        everyone = guild.default_role
        publics = [c for c in guild.text_channels
                   if c.permissions_for(everyone).view_channel]
        ecrivables = [c for c in publics
                      if c.permissions_for(everyone).send_messages]

        if not ecrivables:
            manques.append("Aucun salon public **ouvert à l'écriture** : Discord "
                           "en exige au moins un. Ouvre par exemple "
                           "`👋・présentations` à @everyone.")
        if len(publics) < 7:
            manques.append(f"Seulement **{len(publics)}** salons publics visibles ; "
                           "Discord en recommande 7 pour les salons par défaut.")
        return manques, publics, ecrivables

    def _payload(self, guild):
        """Corps de la requête PUT /guilds/{id}/onboarding."""
        prompts, ignores = [], []
        numero = 1

        for question in QUESTIONS:
            options = []
            for titre, desc, emoji, cles_roles, cles_salons in question["options"]:
                role_ids = [str(ROLES[k]) for k in cles_roles if ROLES.get(k)]
                channel_ids = []
                for k in cles_salons:
                    salon = self._salon(guild, k)
                    if salon:
                        channel_ids.append(str(salon.id))
                if not role_ids and not channel_ids:
                    ignores.append(titre)      # Discord refuse une option vide
                    continue
                options.append({
                    "id": str(numero),
                    "title": titre,
                    "description": desc,
                    "emoji": {"name": emoji},
                    "role_ids": role_ids,
                    "channel_ids": channel_ids,
                })
                numero += 1

            if options:
                prompts.append({
                    "id": str(numero),
                    "type": 0,                       # MULTIPLE_CHOICE
                    "title": question["title"],
                    "options": options,
                    "single_select": question["single_select"],
                    "required": question["required"],
                    "in_onboarding": True,
                })
                numero += 1

        _, publics, ecrivables = self._diagnostic(guild)
        # Les salons ouverts d'abord : Discord veut y trouver de quoi discuter
        defauts = ecrivables + [c for c in publics if c not in ecrivables]
        payload = {
            "prompts": prompts,
            "default_channel_ids": [str(c.id) for c in defauts[:10]],
            "enabled": True,
            "mode": 1,                               # ONBOARDING_ADVANCED
        }
        return payload, ignores

    # ─────────────────────────────────────────────
    @app_commands.command(
        name="onboarding_etat",
        description="(Admin) Ce qui manque pour activer le processus d'accueil")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.guilds(GUILD)
    async def onboarding_etat(self, interaction: discord.Interaction):
        guild = interaction.guild
        manques, publics, ecrivables = self._diagnostic(guild)
        payload, ignores = self._payload(guild)

        lignes = [
            f"**Questions prêtes :** {len(payload['prompts'])}",
            f"**Salons publics :** {len(publics)} · dont **{len(ecrivables)}** "
            f"ouverts à l'écriture",
            f"**Salons par défaut retenus :** {len(payload['default_channel_ids'])}",
        ]
        if ignores:
            lignes.append("**Options ignorées** (ni rôle ni salon trouvé) : "
                          + ", ".join(ignores))

        embed = brand_embed(
            guild,
            title="🎓 Processus d'accueil",
            description="\n".join(lignes) + (
                "\n\n**Ce qui bloque :**\n" + "\n".join(f"• {m}" for m in manques)
                if manques else "\n\n✅ Tout est prêt : lance `/onboarding_setup`."
            ),
            color=COLOR_WARNING if manques else COLOR_SUCCESS,
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(
        name="onboarding_preparer",
        description="(Admin) Ouvre un salon à l'écriture, exigé par Discord")
    @app_commands.describe(
        salon="Le salon à ouvrir (par défaut : celui des présentations)")
    @app_commands.default_permissions(administrator=True)
    @app_commands.guilds(GUILD)
    async def onboarding_preparer(self, interaction: discord.Interaction,
                                  salon: discord.TextChannel = None):
        guild = interaction.guild
        cible = salon or self._salon(guild, "presentations")
        if cible is None:
            await interaction.response.send_message(
                "❌ Aucun salon de présentations trouvé. Crée-le, ou précise "
                "un salon avec `salon:`.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True, thinking=True)
        everyone = guild.default_role
        droits = cible.overwrites_for(everyone)
        droits.view_channel = True
        droits.send_messages = True
        droits.read_message_history = True
        try:
            await cible.set_permissions(
                everyone, overwrite=droits,
                reason="Prérequis du processus d'accueil Discord")
        except discord.HTTPException as e:
            await interaction.followup.send(f"❌ Modification refusée : {e}",
                                            ephemeral=True)
            return

        manques, _, ecrivables = self._diagnostic(guild)
        embed = brand_embed(
            guild,
            title="✅ Salon ouvert à l'écriture",
            description=(
                f"{cible.mention} accepte désormais les messages de @everyone.\n"
                f"**Salons ouverts :** {len(ecrivables)}\n\n"
                + ("Il reste :\n" + "\n".join(f"• {m}" for m in manques)
                   if manques else "Tu peux lancer `/onboarding_setup`.")
            ),
            color=COLOR_SUCCESS if not manques else COLOR_WARNING,
        )
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(
        name="onboarding_setup",
        description="(Admin) Écrit les questions d'accueil et l'écran de bienvenue")
    @app_commands.default_permissions(administrator=True)
    @app_commands.guilds(GUILD)
    async def onboarding_setup(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        guild = interaction.guild
        manques, _, _ = self._diagnostic(guild)
        payload, ignores = self._payload(guild)

        if not payload["prompts"]:
            await interaction.followup.send(
                "❌ Aucune question exploitable : ni rôles ni salons trouvés.",
                ephemeral=True)
            return

        route = discord.http.Route(
            "PUT", "/guilds/{guild_id}/onboarding", guild_id=guild.id)
        try:
            await self.bot.http.request(route, json=payload)
        except discord.HTTPException as e:
            details = f"```{e}```\n"
            if manques:
                details += ("**Causes probables :**\n"
                            + "\n".join(f"• {m}" for m in manques))
            else:
                details += ("Vérifie que le bot a bien la permission "
                            "**Gérer le serveur**.")
            embed = brand_embed(
                guild,
                title="❌ Discord a refusé la configuration",
                description=details,
                color=COLOR_ERROR,
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        # Écran de bienvenue — celui-là, discord.py le gère nativement
        ecran = []
        for cle, desc, emoji in ECRAN_ACCUEIL:
            salon = self._salon(guild, cle)
            if salon:
                ecran.append(discord.WelcomeChannel(
                    channel=salon, description=desc, emoji=emoji))
        note_ecran = "non modifié (aucun salon trouvé)"
        if ecran:
            try:
                await guild.edit_welcome_screen(
                    enabled=True, description=DESCRIPTION_ACCUEIL,
                    welcome_channels=ecran)
                note_ecran = f"{len(ecran)} salons mis en avant"
            except discord.HTTPException as e:
                note_ecran = f"refusé ({e})"

        embed = brand_embed(
            guild,
            title="✅ Processus d'accueil configuré",
            description=(
                f"**Questions écrites :** {len(payload['prompts'])}\n"
                f"**Salons par défaut :** {len(payload['default_channel_ids'])}\n"
                f"**Écran de bienvenue :** {note_ecran}\n"
                + (f"**Options ignorées :** {', '.join(ignores)}\n" if ignores else "")
                + "\nIl reste à écrire le **Guide du serveur** à la main "
                  "(message de bienvenue + 3 tâches) : Discord ne l'expose pas "
                  "dans son API.\n"
                  "Paramètres du serveur → Intégration → Processus d'accueil."
            ),
            color=COLOR_SUCCESS,
        )
        log.info("Onboarding configure : %d questions", len(payload["prompts"]))
        await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(Onboarding(bot))
