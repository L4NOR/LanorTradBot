import discord
from discord.ext import commands
import os
import signal
import logging
import traceback
from aiohttp import web
from config import TOKEN, PREFIX, INTENTS, PORT, DATA_DIR

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Capturer les signaux pour savoir pourquoi le process s'arrête
def signal_handler(signum, frame):
    sig_name = signal.Signals(signum).name
    logging.warning(f"⚠️ SIGNAL REÇU: {sig_name} ({signum})")
    logging.warning(f"⚠️ Stack trace au moment du signal:\n{''.join(traceback.format_stack(frame))}")

signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)

# Créer le dossier data au démarrage
os.makedirs(DATA_DIR, exist_ok=True)


async def setup_modules(bot):
    """Charge tous les modules sur l'instance du bot."""
    import events
    events.setup(bot)
    logging.info("✅ Module Events chargé")

    import commands as cmd
    cmd.setup(bot)
    logging.info("✅ Module Commands chargé")

    import announcements
    announcements.setup(bot)
    logging.info("✅ Module Announcements chargé")

    import rappels
    await rappels.setup(bot)
    logging.info("✅ Module Rappels chargé")

    import giveaway
    await giveaway.setup(bot)
    logging.info("✅ Module Giveaway chargé")

    import community
    await community.setup(bot)
    logging.info("✅ Module Community chargé")

    import achievements
    await achievements.setup(bot)
    logging.info("✅ Module Achievements chargé")

    import shop
    await shop.setup(bot)
    logging.info("✅ Module Shop chargé")

    import admin_data
    await admin_data.setup(bot)
    logging.info("✅ Module Admin Data chargé")

    import role_selector
    await role_selector.setup(bot)
    logging.info("✅ Module Role Selector chargé")

    import logs
    await logs.setup(bot)
    logging.info("✅ Module Audit Logs chargé")

    import polls
    await polls.setup(bot)
    logging.info("✅ Module Polls chargé")

    import tickets
    await tickets.setup(bot)
    logging.info("✅ Module Tickets chargé")

    import stats
    await stats.setup(bot)
    logging.info("✅ Module Stats chargé")

    import database
    logging.info("✅ Module Database initialisé")

    import planning
    await planning.setup(bot)
    logging.info("✅ Module Planning chargé")


class LanorBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix=PREFIX, intents=INTENTS)
        self.web_runner = None

    async def setup_hook(self):
        """Chargement async au démarrage"""
        await setup_modules(self)
        await self.start_webserver()

    async def start_webserver(self):
        """Serveur web interne (health check VPS)"""
        if self.web_runner is not None:
            return

        app = web.Application()

        async def health_check(request):
            return web.Response(text="OK", status=200)

        # Route simple (PAS de webhook ici ⚠️)
        app.router.add_get('/', health_check)

        self.web_runner = web.AppRunner(app)
        await self.web_runner.setup()

        site = web.TCPSite(self.web_runner, '0.0.0.0', PORT)
        await site.start()

        logging.info(f"🌐 Serveur web démarré sur le port {PORT}")

    async def close(self):
        """Fermeture propre du bot"""
        logging.warning(f"⚠️ bot.close() APPELÉ - Stack trace:")
        logging.warning(''.join(traceback.format_stack()))
        if self.web_runner:
            await self.web_runner.cleanup()
        await super().close()


# ═══════════════════════════════════════════════════════════════
# LANCEMENT DU BOT
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    try:
        bot = LanorBot()
        logging.info("🚀 Démarrage du bot...")
        bot.run(TOKEN)
        logging.warning("⚠️ bot.run() A RETOURNÉ NORMALEMENT - le bot s'est arrêté sans erreur")
    except SystemExit as e:
        logging.error(f"❌ SystemExit reçu: code={e.code}")
    except KeyboardInterrupt:
        logging.warning("⚠️ KeyboardInterrupt reçu")
    except Exception as e:
        logging.error(f"❌ Erreur fatale: {type(e).__name__}: {e}")
        logging.error(traceback.format_exc())
