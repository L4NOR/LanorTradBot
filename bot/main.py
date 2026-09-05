"""
LanorTradBot — point d'entrée
===============================
    python -m bot.main                  → demande sur quel serveur
    python -m bot.main --server prod    → sans question
    python -m bot.main --server test    → bac à sable
    python -m bot.main --safe           → en ligne, mais ne fait rien
    python -m bot.main --no-tasks       → commandes actives, boucles à l'arrêt

Le bot ne sert **qu'un serveur à la fois** : tout événement venant d'ailleurs
est ignoré, et toute commande lancée depuis un autre serveur est refusée.
"""
import logging
import os
import sys

import discord
from discord.ext import commands, tasks

from bot import resolver, servers
from bot.config import TOKEN, GUILD_ID, SERVER, SITE_URL


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("lanortrad")


def _flag(name: str, env: str) -> bool:
    return name in sys.argv or os.environ.get(env, "").lower() in ("1", "true", "yes")


SAFE_MODE = _flag("--safe", "LANOR_SAFE_MODE")
NO_TASKS = SAFE_MODE or _flag("--no-tasks", "LANOR_NO_TASKS")


COGS = [
    "bot.cogs.errors",        # en premier : branche le gestionnaire global
    # ─── Le site ───
    "bot.cogs.sitesync",      # planning · atelier · catalogue · auto-publication
    "bot.cogs.releases",      # /release manuel + historique
    # ─── Accueil ───
    "bot.cogs.welcome",
    "bot.cogs.alerts",        # panneau de rôles par série
    "bot.cogs.content",
    "bot.cogs.onboarding",
    "bot.cogs.bulkroles",
    # ─── Contact ───
    "bot.cogs.tickets",
    "bot.cogs.recruit",
    # ─── Protection ───
    "bot.cogs.moderation",
    "bot.cogs.warns",
    "bot.cogs.guard",         # automod + anti-raid + anti-flood
    "bot.cogs.logs",
    "bot.cogs.backup",
    # ─── Divers ───
    "bot.cogs.info",          # /ping /membre /serveur /dis /annonce
    "bot.cogs.help",
]

SAFE_COGS = ["bot.cogs.errors", "bot.cogs.info", "bot.cogs.help"]


intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True
intents.reactions = True


class LanorTradBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix=commands.when_mentioned,   # tout passe par les slash
            intents=intents,
            help_command=None,
            description="LanorTrad — le bot du serveur officiel",
        )

    # ─── Cloison : un seul serveur servi ───
    @staticmethod
    def _foreign(args) -> bool:
        for arg in args:
            guild_id = getattr(arg, "guild_id", None)
            if guild_id is None:
                guild = getattr(arg, "guild", None)
                guild_id = getattr(guild, "id", None)
                if guild_id is None and isinstance(guild, int):
                    guild_id = guild
            if guild_id is None and type(arg).__name__ == "Guild":
                guild_id = getattr(arg, "id", None)
            if guild_id is not None:
                return int(guild_id) != GUILD_ID
        return False

    def dispatch(self, event_name, *args, **kwargs):
        if args and self._foreign(args):
            return
        super().dispatch(event_name, *args, **kwargs)

    async def _check_interaction(self, interaction: discord.Interaction) -> bool:
        if interaction.guild_id and interaction.guild_id != GUILD_ID:
            await interaction.response.send_message(
                f"🚫 Ce bot tourne sur **{SERVER['name']}**, pas sur ce serveur.",
                ephemeral=True)
            return False
        return True

    def _stop_loops(self):
        stopped = []
        for cog in self.cogs.values():
            for name in dir(cog):
                attr = getattr(cog, name, None)
                if isinstance(attr, tasks.Loop) and attr.is_running():
                    attr.cancel()
                    stopped.append(f"{cog.__class__.__name__}.{name}")
        if stopped:
            log.info("⏸️  %d boucle(s) arrêtée(s) : %s", len(stopped), ", ".join(stopped))

    async def setup_hook(self):
        if SAFE_MODE:
            log.warning("🦺 MODE SAFE : le bot se connecte et ne fait rien d'autre.")
        elif NO_TASKS:
            log.warning("⏸️  MODE NO-TASKS : boucles automatiques désactivées.")

        for cog in (SAFE_COGS if SAFE_MODE else COGS):
            try:
                await self.load_extension(cog)
                log.info("  [OK]   %s", cog)
            except Exception as e:
                log.error("  [ERR]  %s : %s: %s", cog, type(e).__name__, e)

        if NO_TASKS:
            self._stop_loops()

        self.tree.interaction_check = self._check_interaction

        try:
            synced = await self.tree.sync(guild=discord.Object(id=GUILD_ID))
            log.info("🔄 %d commandes synchronisées sur %s", len(synced), SERVER["name"])
        except Exception as e:
            log.error("Synchronisation des commandes KO : %s", e)

    async def on_ready(self):
        log.info("🩸 Connecté en tant que %s (%s)", self.user, self.user.id)

        guild = self.get_guild(GUILD_ID)
        if guild is None:
            log.error("Le bot n'est pas sur le serveur %s (%s) !",
                      SERVER["name"], GUILD_ID)
        elif not SAFE_MODE:
            try:
                resolver.resolve(guild)
            except Exception as e:
                log.error("Résolution des IDs KO : %s", e)

            if not NO_TASKS:
                sync_cog = self.get_cog("SiteSync")
                if sync_cog is not None:
                    try:
                        if await sync_cog.refresh():
                            await sync_cog.refresh_boards(guild)
                    except Exception as e:
                        log.warning("Première synchro du site KO : %s", e)

        if SAFE_MODE:
            activity, status = discord.Game("🦺 mode safe"), discord.Status.idle
        elif NO_TASKS:
            activity, status = discord.Game("⏸️ maintenance"), discord.Status.idle
        else:
            activity = discord.Activity(
                type=discord.ActivityType.watching,
                name=SITE_URL.replace("https://", ""))
            status = discord.Status.online
        await self.change_presence(activity=activity, status=status)
        log.info("✅ Prêt.")


def run():
    print("=" * 62)
    print("    🩸 LANORTRAD BOT" + (
        "  ─  MODE SAFE" if SAFE_MODE else
        "  ─  MODE NO-TASKS" if NO_TASKS else ""))
    print(servers.banner(SERVER))
    LanorTradBot().run(TOKEN)


if __name__ == "__main__":
    run()
