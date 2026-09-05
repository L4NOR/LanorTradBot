"""
Attribution de rôles en masse
===============================
Trois commandes, toutes en **simulation par défaut** : elles disent ce
qu'elles feraient sans rien changer, et il faut `simulation:False` pour
qu'elles agissent. Une attribution de masse se relit avant de se lancer.

  /roles_base      — le(s) rôle(s) de base à TOUS les membres
  /roles_ajouter   — un ou plusieurs rôles à des membres précis
  /roles_retirer   — retire un rôle à tous ceux qui l'ont

Les bots sont ignorés, ceux qui ont déjà le rôle sont sautés, et le rythme
est volontairement lent pour ne pas se faire limiter par Discord.
"""
import asyncio
import logging
import re

import discord
from discord import app_commands
from discord.ext import commands

from bot.config import (
    GUILD_ID, ROLES, BASE_ROLES,
    COLOR_SUCCESS, COLOR_WARNING,
)
from bot.embeds import brand_embed

log = logging.getLogger("lanortrad.bulkroles")

GUILD = discord.Object(id=GUILD_ID) if GUILD_ID else None

PAUSE = 0.35          # secondes entre deux attributions
PROGRESS_EVERY = 25   # rafraîchit le compte rendu tous les N membres


class BulkRoles(commands.Cog):
    """Attribution de rôles à plusieurs membres."""

    def __init__(self, bot):
        self.bot = bot
        self._running = False

    # ─────────────────────────────────────────────
    # Utilitaires
    # ─────────────────────────────────────────────
    def _base_roles(self, guild):
        """Rôles de base configurés qui existent réellement sur le serveur."""
        found = []
        for key in BASE_ROLES:
            role_id = ROLES.get(key)
            role = guild.get_role(role_id) if role_id else None
            if role:
                found.append(role)
        return found

    async def _members(self, guild):
        """Liste complète des membres, en forçant le chargement si besoin."""
        if not guild.chunked:
            try:
                await guild.chunk()
            except (discord.ClientException, asyncio.TimeoutError):
                return [m async for m in guild.fetch_members(limit=None)]
        return list(guild.members)

    @staticmethod
    def _extraire_ids(texte):
        """Récupère les identifiants dans une suite de mentions ou d'IDs bruts."""
        if not texte:
            return []
        vus, ids = set(), []
        for mention, brut in re.findall(r"<@!?(\d{15,25})>|(\d{15,25})", texte):
            uid = int(mention or brut)
            if uid not in vus:
                vus.add(uid)
                ids.append(uid)
        return ids

    def _trop_haut(self, guild, roles):
        return [r for r in roles if r >= guild.me.top_role]

    async def _appliquer(self, travail, auteur, retrait=False):
        """Applique les changements. Retourne (succès, liste d'échecs)."""
        ok, echecs = 0, []
        for membre, roles in travail:
            try:
                if retrait:
                    await membre.remove_roles(*roles, reason=f"Retrait par {auteur}")
                else:
                    await membre.add_roles(*roles, reason=f"Attribution par {auteur}")
                ok += 1
            except discord.HTTPException as e:
                echecs.append(f"{membre} ({e})")
            await asyncio.sleep(PAUSE)
        return ok, echecs

    # ─────────────────────────────────────────────
    # /roles_base — tout le serveur
    # ─────────────────────────────────────────────
    @app_commands.command(
        name="roles_base",
        description="(Admin) Donne le rôle de base à tous les membres du serveur")
    @app_commands.describe(
        role="Le rôle à attribuer (par défaut : le rôle de base configuré)",
        simulation="True = montre ce qui serait fait, sans rien changer")
    @app_commands.default_permissions(manage_roles=True)
    @app_commands.guilds(GUILD)
    async def roles_base(self, interaction: discord.Interaction,
                         role: discord.Role = None, simulation: bool = True):
        if self._running:
            await interaction.response.send_message(
                "⏳ Une attribution est déjà en cours.", ephemeral=True)
            return

        guild = interaction.guild
        cibles_roles = [role] if role else self._base_roles(guild)
        if not cibles_roles:
            await interaction.response.send_message(
                "❌ Aucun rôle de base trouvé. Précise-en un avec `role:`.",
                ephemeral=True)
            return

        trop_haut = self._trop_haut(guild, cibles_roles)
        if trop_haut:
            await interaction.response.send_message(
                "🚫 " + ", ".join(r.mention for r in trop_haut)
                + " est au-dessus du rôle du bot : remonte-le dans "
                  "Paramètres du serveur → Rôles.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True, thinking=True)
        membres = [m for m in await self._members(guild) if not m.bot]
        travail = [(m, [r for r in cibles_roles if r not in m.roles]) for m in membres]
        travail = [(m, rs) for m, rs in travail if rs]
        noms = ", ".join(r.mention for r in cibles_roles)

        if simulation:
            embed = brand_embed(
                guild,
                title="🔎 Simulation — rien n'a été modifié",
                description=(
                    f"**Rôle(s) :** {noms}\n"
                    f"**Membres humains :** {len(membres)}\n"
                    f"**À qui il manque le rôle :** {len(travail)}\n"
                    f"**Déjà en règle :** {len(membres) - len(travail)}\n\n"
                    f"⏱️ Durée estimée : environ "
                    f"{max(1, round(len(travail) * PAUSE / 60))} min\n\n"
                    "Pour appliquer : relance avec `simulation:False`."
                ),
                color=COLOR_WARNING,
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        if not travail:
            await interaction.followup.send(
                f"✅ Tout le monde a déjà {noms}.", ephemeral=True)
            return

        self._running = True
        ok, echecs = 0, []
        try:
            message = await interaction.followup.send(
                f"⏳ Attribution en cours… 0 / {len(travail)}", ephemeral=True)
            for i, (membre, roles) in enumerate(travail, start=1):
                try:
                    await membre.add_roles(
                        *roles, reason=f"Attribution de masse par {interaction.user}")
                    ok += 1
                except discord.HTTPException as e:
                    echecs.append(f"{membre} ({e})")
                if i % PROGRESS_EVERY == 0:
                    try:
                        await message.edit(
                            content=f"⏳ Attribution en cours… {i} / {len(travail)}")
                    except discord.HTTPException:
                        pass
                await asyncio.sleep(PAUSE)
        finally:
            self._running = False

        embed = brand_embed(
            guild,
            title="✅ Attribution terminée",
            description=(
                f"**Rôle(s) :** {noms}\n"
                f"**Attribués :** {ok}\n"
                f"**Échecs :** {len(echecs)}"
                + ("\n\n" + "\n".join(f"• {e}" for e in echecs[:8]) if echecs else "")
            ),
            color=COLOR_SUCCESS if not echecs else COLOR_WARNING,
        )
        log.info("Attribution de masse : %d ok, %d echecs", ok, len(echecs))
        try:
            await message.edit(content=None, embed=embed)
        except discord.HTTPException:
            await interaction.followup.send(embed=embed, ephemeral=True)

    # ─────────────────────────────────────────────
    # /roles_ajouter — des membres précis
    # ─────────────────────────────────────────────
    @app_commands.command(
        name="roles_ajouter",
        description="(Staff) Donne un ou plusieurs rôles à plusieurs membres")
    @app_commands.describe(
        role="Le rôle à donner",
        membres="Mentionne-les, ou colle leurs IDs séparés par des espaces",
        depuis_role="Ou : tous ceux qui portent déjà ce rôle",
        tout_le_monde="Ou : TOUS les membres humains du serveur",
        role2="Un deuxième rôle à donner en même temps (facultatif)",
        role3="Un troisième rôle (facultatif)",
        simulation="True = montre ce qui serait fait, sans rien changer")
    @app_commands.default_permissions(manage_roles=True)
    @app_commands.guilds(GUILD)
    async def roles_ajouter(self, interaction: discord.Interaction,
                            role: discord.Role, membres: str = None,
                            depuis_role: discord.Role = None,
                            tout_le_monde: bool = False,
                            role2: discord.Role = None, role3: discord.Role = None,
                            simulation: bool = True):
        guild = interaction.guild
        a_donner = [r for r in (role, role2, role3) if r]

        trop_haut = self._trop_haut(guild, a_donner)
        if trop_haut:
            await interaction.response.send_message(
                "🚫 " + ", ".join(r.mention for r in trop_haut)
                + " est au-dessus du rôle du bot : remonte-le dans "
                  "Paramètres du serveur → Rôles.", ephemeral=True)
            return

        if not membres and not depuis_role and not tout_le_monde:
            await interaction.response.send_message(
                "❌ Indique des `membres`, un `depuis_role`, "
                "ou coche `tout_le_monde`.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True, thinking=True)
        await self._members(guild)

        cibles, introuvables = {}, []
        for uid in self._extraire_ids(membres):
            membre = guild.get_member(uid)
            if membre:
                cibles[membre.id] = membre
            else:
                introuvables.append(str(uid))
        if depuis_role:
            for membre in depuis_role.members:
                cibles[membre.id] = membre
        if tout_le_monde:
            for membre in guild.members:
                cibles[membre.id] = membre

        cibles = [m for m in cibles.values() if not m.bot]
        travail = [(m, [r for r in a_donner if r not in m.roles]) for m in cibles]
        travail = [(m, rs) for m, rs in travail if rs]

        noms = ", ".join(r.mention for r in a_donner)
        alerte = ""
        if introuvables:
            alerte = "\n⚠️ Introuvables sur le serveur : " + ", ".join(introuvables[:10])

        if not cibles:
            await interaction.followup.send(
                "❌ Aucun membre reconnu." + alerte, ephemeral=True)
            return

        if simulation:
            apercu = ", ".join(m.mention for m, _ in travail[:15])
            if len(travail) > 15:
                apercu += f" *et {len(travail) - 15} autres*"
            embed = brand_embed(
                guild,
                title="🔎 Simulation — rien n'a été modifié",
                description=(
                    f"**Rôle(s) :** {noms}\n"
                    f"**Membres visés :** {len(cibles)}\n"
                    f"**À modifier :** {len(travail)}\n"
                    f"**Déjà en règle :** {len(cibles) - len(travail)}\n\n"
                    + (apercu + "\n\n" if travail else "")
                    + "Pour appliquer : relance avec `simulation:False`." + alerte
                ),
                color=COLOR_WARNING,
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        if not travail:
            await interaction.followup.send(
                f"✅ Tous ces membres ont déjà {noms}." + alerte, ephemeral=True)
            return

        ok, echecs = await self._appliquer(travail, interaction.user)
        embed = brand_embed(
            guild,
            title="✅ Rôles attribués",
            description=(
                f"**Rôle(s) :** {noms}\n"
                f"**Membres modifiés :** {ok}\n"
                f"**Échecs :** {len(echecs)}" + alerte
                + ("\n\n" + "\n".join(f"• {e}" for e in echecs[:8]) if echecs else "")
            ),
            color=COLOR_SUCCESS if not echecs else COLOR_WARNING,
        )
        log.info("Attribution ciblee : %d membres", ok)
        await interaction.followup.send(embed=embed, ephemeral=True)

    # ─────────────────────────────────────────────
    # /roles_retirer
    # ─────────────────────────────────────────────
    @app_commands.command(
        name="roles_retirer",
        description="(Admin) Retire un rôle à tous les membres qui l'ont")
    @app_commands.describe(role="Le rôle à retirer",
                           simulation="True = montre ce qui serait fait")
    @app_commands.default_permissions(administrator=True)
    @app_commands.guilds(GUILD)
    async def roles_retirer(self, interaction: discord.Interaction,
                            role: discord.Role, simulation: bool = True):
        guild = interaction.guild
        if role >= guild.me.top_role:
            await interaction.response.send_message(
                f"🚫 {role.mention} est au-dessus du rôle du bot.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True, thinking=True)
        await self._members(guild)
        porteurs = [m for m in role.members if not m.bot]

        if simulation:
            await interaction.followup.send(
                f"🔎 **Simulation** — {len(porteurs)} membre(s) portent "
                f"{role.mention}. Rien n'a été modifié.\n"
                "Pour appliquer : relance avec `simulation:False`.", ephemeral=True)
            return

        ok, echecs = await self._appliquer(
            [(m, [role]) for m in porteurs], interaction.user, retrait=True)
        await interaction.followup.send(
            f"✅ {role.mention} retiré à **{ok}** membre(s)."
            + (f" — {len(echecs)} échec(s)." if echecs else ""), ephemeral=True)


async def setup(bot):
    await bot.add_cog(BulkRoles(bot))
