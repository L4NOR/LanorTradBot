"""
Permissions — rôles et salons, appliquées depuis Discord
==========================================================
Jusqu'ici les permissions n'étaient posées qu'à la création de la structure.
Ces deux commandes les réappliquent à tout moment, sans script local :

  /perms_roles   — les permissions serveur de chaque rôle
  /perms_salons  — les droits par salon (lecture seule, panneau, équipe, staff)

Le modèle tient en une phrase : **le serveur est en lecture seule**, sauf
le salon des présentations. Tout le reste se lit, se réagit, mais ne
s'écrit pas — c'est ce qui distingue ce serveur du forum du site.

Les deux commandes tournent en **simulation par défaut**.
"""
import asyncio
import logging

import discord
from discord import app_commands
from discord.ext import commands

from bot.config import (
    GUILD_ID, CHANNELS, ROLES,
    COLOR_SUCCESS, COLOR_WARNING, COLOR_ERROR,
)
from bot.embeds import brand_embed

log = logging.getLogger("lanortrad.permissions")

GUILD = discord.Object(id=GUILD_ID) if GUILD_ID else None

PAUSE = 0.4   # entre deux appels, pour ne pas se faire limiter

# ── Qui est staff, qui est équipe ──
CLES_STAFF = ["founder", "moderator"]
CLES_EQUIPE = ["raw_provider", "cleaner", "translator", "typesetter", "qc", "trial"]


# ── Permissions serveur, par rôle ──
def _perms_moderation():
    return discord.Permissions(
        view_channel=True, read_message_history=True, send_messages=True,
        embed_links=True, attach_files=True, add_reactions=True,
        manage_messages=True, manage_threads=True, mention_everyone=True,
        kick_members=True, ban_members=True, moderate_members=True,
        manage_nicknames=True, view_audit_log=True,
        use_application_commands=True, connect=True, speak=True,
    )


def _perms_everyone():
    """Base de tout le monde : on lit, on réagit, on n'écrit pas."""
    return discord.Permissions(
        view_channel=True, read_message_history=True, add_reactions=True,
        use_external_emojis=True, use_application_commands=True,
        change_nickname=True, connect=True, speak=True,
    )


PLAN_ROLES = {
    "founder":   discord.Permissions(administrator=True),
    "moderator": _perms_moderation(),
    # Les métiers n'ont pas de pouvoir global : leur rôle sert à ouvrir
    # les salons de l'atelier, via les droits par salon.
    "raw_provider": discord.Permissions.none(),
    "cleaner":      discord.Permissions.none(),
    "translator":   discord.Permissions.none(),
    "typesetter":   discord.Permissions.none(),
    "qc":           discord.Permissions.none(),
    "trial":        discord.Permissions.none(),
    "member":       discord.Permissions.none(),
    "ping_tougen":        discord.Permissions.none(),
    "ping_ao":            discord.Permissions.none(),
    "ping_tokyo":         discord.Permissions.none(),
    "ping_cat":           discord.Permissions.none(),
    "ping_sat":           discord.Permissions.none(),
    "ping_one":           discord.Permissions.none(),
    "ping_all":           discord.Permissions.none(),
    "ping_announcements": discord.Permissions.none(),
}


# ── Droits par salon ──
# lecture : on lit et on réagit · panneau : on lit, on clique, on ne réagit pas
# ouvert  : on écrit · equipe : réservé à l'atelier · staff : réservé au staff
PLAN_SALONS = {
    "welcome": "lecture", "rules": "lecture", "faq": "lecture",
    "site_links": "lecture", "site_forum": "lecture", "incidents": "lecture",
    "sorties_fr": "lecture", "planning": "lecture", "announcements": "lecture",

    "notifications": "panneau", "tickets": "panneau", "recrutement": "panneau",

    "presentations": "ouvert",

    "workshop_chat": "equipe", "pipeline": "equipe",
    "raws_archive": "equipe", "glossary": "equipe",

    "tests_techniques": "staff",
    "server_logs": "staff", "message_logs": "staff",
    "automod_logs": "staff", "bot_logs": "staff",
}


class Permissions(commands.Cog):
    """Application des permissions."""

    def __init__(self, bot):
        self.bot = bot

    # ─────────────────────────────────────────────
    def _roles(self, guild, cles):
        out = []
        for cle in cles:
            role_id = ROLES.get(cle)
            role = guild.get_role(role_id) if role_id else None
            if role:
                out.append(role)
        return out

    def _overwrites(self, guild, preset):
        """Construit les droits d'un salon selon le préréglage."""
        everyone = guild.default_role
        staff = self._roles(guild, CLES_STAFF)
        equipe = self._roles(guild, CLES_EQUIPE)
        ow = {}

        if preset == "lecture":
            ow[everyone] = discord.PermissionOverwrite(
                view_channel=True, read_message_history=True, add_reactions=True,
                send_messages=False, create_public_threads=False,
                create_private_threads=False, send_messages_in_threads=False)
            for r in staff + equipe:
                ow[r] = discord.PermissionOverwrite(
                    send_messages=True, embed_links=True, attach_files=True,
                    manage_messages=True)

        elif preset == "panneau":
            ow[everyone] = discord.PermissionOverwrite(
                view_channel=True, read_message_history=True, add_reactions=False,
                send_messages=False, create_public_threads=False,
                create_private_threads=False)
            for r in staff:
                ow[r] = discord.PermissionOverwrite(send_messages=True)

        elif preset == "ouvert":
            ow[everyone] = discord.PermissionOverwrite(
                view_channel=True, read_message_history=True, add_reactions=True,
                send_messages=True, create_public_threads=False)
            for r in staff:
                ow[r] = discord.PermissionOverwrite(manage_messages=True)

        elif preset == "equipe":
            ow[everyone] = discord.PermissionOverwrite(view_channel=False)
            for r in staff + equipe:
                ow[r] = discord.PermissionOverwrite(
                    view_channel=True, read_message_history=True,
                    send_messages=True, embed_links=True, attach_files=True)

        elif preset == "staff":
            ow[everyone] = discord.PermissionOverwrite(view_channel=False)
            for r in staff:
                ow[r] = discord.PermissionOverwrite(
                    view_channel=True, read_message_history=True,
                    send_messages=True, embed_links=True, attach_files=True)

        # Le bot garde toujours l'accès, même sur les salons fermés
        if guild.me.top_role and not guild.me.guild_permissions.administrator:
            ow[guild.me.top_role] = discord.PermissionOverwrite(
                view_channel=True, read_message_history=True,
                send_messages=True, embed_links=True, manage_messages=True)
        return ow

    # ─────────────────────────────────────────────
    # /perms_roles
    # ─────────────────────────────────────────────
    @app_commands.command(
        name="perms_roles",
        description="(Admin) Applique les permissions serveur de chaque rôle")
    @app_commands.describe(
        everyone="Remet aussi @everyone en lecture seule",
        simulation="True = montre ce qui changerait, sans rien appliquer")
    @app_commands.default_permissions(administrator=True)
    @app_commands.guilds(GUILD)
    async def perms_roles(self, interaction: discord.Interaction,
                          everyone: bool = True, simulation: bool = True):
        guild = interaction.guild
        sommet = guild.me.top_role
        a_changer, hors_portee, absents = [], [], []

        for cle, perms in PLAN_ROLES.items():
            role_id = ROLES.get(cle)
            role = guild.get_role(role_id) if role_id else None
            if role is None:
                absents.append(cle)
                continue
            if role >= sommet:
                hors_portee.append(role)
                continue
            if role.permissions.value != perms.value:
                a_changer.append((role, perms))

        base = _perms_everyone()
        everyone_change = everyone and guild.default_role.permissions.value != base.value

        if simulation:
            lignes = [f"• {r.mention} → `{p.value}`" for r, p in a_changer[:20]] or \
                     ["*Tous les rôles sont déjà conformes.*"]
            if everyone_change:
                lignes.insert(0, "• **@everyone** → lecture seule "
                                 "(voir, lire, réagir ; pas d'écriture)")
            remarques = []
            if hors_portee:
                remarques.append("⚠️ Au-dessus du bot, ignorés : "
                                 + ", ".join(r.mention for r in hors_portee))
            if absents:
                remarques.append("ℹ️ Sans rôle : " + ", ".join(f"`{a}`" for a in absents))

            await interaction.response.send_message(
                embed=brand_embed(
                    guild, title="🔎 Permissions des rôles — simulation",
                    description="\n".join(lignes)
                    + ("\n\n" + "\n".join(remarques) if remarques else "")
                    + "\n\nPour appliquer : `simulation:False`.",
                    color=COLOR_WARNING),
                ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True, thinking=True)
        ok, echecs = 0, []
        if everyone_change:
            try:
                await guild.default_role.edit(
                    permissions=base, reason=f"Permissions par {interaction.user}")
                ok += 1
            except discord.HTTPException as e:
                echecs.append(f"@everyone ({e})")
            await asyncio.sleep(PAUSE)

        for role, perms in a_changer:
            try:
                await role.edit(permissions=perms,
                                reason=f"Permissions par {interaction.user}")
                ok += 1
            except discord.HTTPException as e:
                echecs.append(f"{role.name} ({e})")
            await asyncio.sleep(PAUSE)

        log.info("Permissions roles : %d appliquees, %d echecs", ok, len(echecs))
        await interaction.followup.send(
            embed=brand_embed(
                guild, title="✅ Permissions des rôles appliquées",
                description=f"**Rôles modifiés :** {ok}\n"
                            f"**Échecs :** {len(echecs)}"
                            + ("\n\n" + "\n".join(f"• {e}" for e in echecs[:8])
                               if echecs else ""),
                color=COLOR_SUCCESS if not echecs else COLOR_WARNING),
            ephemeral=True)

    # ─────────────────────────────────────────────
    # /perms_salons
    # ─────────────────────────────────────────────
    @app_commands.command(
        name="perms_salons",
        description="(Admin) Applique les droits de chaque salon")
    @app_commands.describe(
        simulation="True = montre ce qui changerait, sans rien appliquer")
    @app_commands.default_permissions(administrator=True)
    @app_commands.guilds(GUILD)
    async def perms_salons(self, interaction: discord.Interaction,
                           simulation: bool = True):
        guild = interaction.guild
        prevu, absents = [], []
        for cle, preset in PLAN_SALONS.items():
            ch_id = CHANNELS.get(cle)
            salon = guild.get_channel(ch_id) if ch_id else None
            if salon is None:
                absents.append(cle)
                continue
            prevu.append((salon, preset))

        if not prevu:
            await interaction.response.send_message(
                "❌ Aucun salon reconnu — vérifie les IDs dans la config.",
                ephemeral=True)
            return

        if simulation:
            groupes = {}
            for salon, preset in prevu:
                groupes.setdefault(preset, []).append(salon.mention)
            libelles = {
                "lecture": "📖 lecture seule (lire + réagir)",
                "panneau": "🔘 panneau (lire, cliquer, pas de réaction)",
                "ouvert":  "💬 ouvert à l'écriture",
                "equipe":  "🛠️ réservé à l'équipe",
                "staff":   "🔒 réservé au staff",
            }
            lignes = [f"**{libelles.get(k, k)}**\n" + " ".join(v)
                      for k, v in groupes.items()]
            if absents:
                lignes.append("ℹ️ Salons introuvables : "
                              + ", ".join(f"`{a}`" for a in absents))
            await interaction.response.send_message(
                embed=brand_embed(
                    guild, title="🔎 Droits des salons — simulation",
                    description="\n\n".join(lignes)
                    + "\n\nPour appliquer : `simulation:False`.",
                    color=COLOR_WARNING),
                ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True, thinking=True)
        ok, echecs = 0, []
        for salon, preset in prevu:
            try:
                await salon.edit(overwrites=self._overwrites(guild, preset),
                                 reason=f"Droits par {interaction.user}")
                ok += 1
            except discord.HTTPException as e:
                echecs.append(f"{salon.name} ({e})")
            await asyncio.sleep(PAUSE)

        log.info("Droits salons : %d appliques, %d echecs", ok, len(echecs))
        await interaction.followup.send(
            embed=brand_embed(
                guild, title="✅ Droits des salons appliqués",
                description=f"**Salons traités :** {ok}\n"
                            f"**Échecs :** {len(echecs)}"
                            + (f"\n**Introuvables :** {len(absents)}" if absents else "")
                            + ("\n\n" + "\n".join(f"• {e}" for e in echecs[:8])
                               if echecs else ""),
                color=COLOR_SUCCESS if not echecs else COLOR_WARNING),
            ephemeral=True)


async def setup(bot):
    await bot.add_cog(Permissions(bot))
