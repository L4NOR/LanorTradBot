import discord
from discord.ext import commands
import os
import logging
import asyncio
from aiohttp import web
from config import TOKEN, PREFIX, INTENTS, PORT, DATA_DIR

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

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


async def create_bot():
    """Crée et configure une nouvelle instance du bot avec tous les modules."""
    bot = commands.Bot(command_prefix=PREFIX, intents=INTENTS)
    bot._web_runner = None
    await setup_modules(bot)
    return bot


async def main():
    """Fonction principale pour démarrer le bot."""

    # ═══════════════════════════════════════════════════════════════════════════
    # SERVEUR WEB INTERNE (pour les health checks)
    # ═══════════════════════════════════════════════════════════════════════════

    web_runner = None

    async def setup_webserver():
        """Configure et démarre le serveur web pour les health checks."""
        nonlocal web_runner
        if web_runner is not None:
            return  # Déjà démarré
        app = web.Application()

        async def health_check(request):
            return web.Response(text="OK", status=200)

        app.router.add_get('/', health_check)
        runner = web.AppRunner(app)
        await runner.setup()
        web_runner = runner
        site = web.TCPSite(runner, '0.0.0.0', PORT)
        await site.start()
        logging.info(f"Serveur web démarré sur le port {PORT}")

    # ═══════════════════════════════════════════════════════════════════════════
    # DÉMARRAGE DU SERVEUR WEB (avant le bot pour satisfaire Render)
    # ═══════════════════════════════════════════════════════════════════════════

    await setup_webserver()

    # ═══════════════════════════════════════════════════════════════════════════
    # CRÉER ET DÉMARRER LE BOT
    # ═══════════════════════════════════════════════════════════════════════════

    bot = await create_bot()

    try:
        logging.info("Démarrage du bot...")
        await bot.start(TOKEN)
    except discord.LoginFailure:
        logging.error("Token Discord invalide. Vérifiez votre fichier .env")
    except Exception as e:
        logging.error(f"Erreur lors du démarrage du bot: {e}")
    finally:
        if web_runner:
            await web_runner.cleanup()
        if not bot.is_closed():
            await bot.close()


if __name__ == "__main__":
    asyncio.run(main())
