import discord
from discord.ext import commands
import os
import logging
import asyncio
from aiohttp import web
from config import TOKEN, PREFIX, INTENTS, PORT
import events
import commands as cmd
import announcements

logging.basicConfig(level=logging.INFO)

async def main():
    bot = commands.Bot(command_prefix=PREFIX, intents=INTENTS)
    
    # Serveur web interne (pour uptime monitor par ex.)
    async def setup_webserver():
        app = web.Application()
        async def health_check(request):
            return web.Response(text="OK", status=200)
        app.router.add_get('/', health_check)
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', PORT)
        await site.start()
        logging.info(f"Serveur web démarré sur le port {PORT}")
    
    bot.setup_webserver = setup_webserver

    # Charger les événements
    events.setup(bot)

    # Charger les commandes (synchrone)
    cmd.setup(bot)

    # Charger le module d'annonces (commande interactive)
    announcements.setup(bot)

    # Charger les rappels (asynchrone)
    import rappels
    await rappels.setup(bot)

    # Charger le système de giveaway (asynchrone)
    import giveaway
    await giveaway.setup(bot)
    
    # ========== NOUVEAUX MODULES COMMUNAUTAIRES ==========
    
    # Charger le système communautaire (reviews, théories)
    import community
    await community.setup(bot)
    logging.info("✅ Module Community chargé")
    
    # Charger le système de badges/achievements
    import achievements
    await achievements.setup(bot)
    logging.info("✅ Module Achievements chargé")
    
    # Charger le système de shop
    import shop
    await shop.setup(bot)
    logging.info("✅ Module Shop chargé")
    
    # Charger le gestionnaire de données admin
    import admin_data
    await admin_data.setup(bot)
    logging.info("✅ Module Admin Data chargé")
    
    # Charger le système de gestion des rôles
    import roles_setup
    await roles_setup.setup(bot)
    logging.info("✅ Module Roles Setup chargé")

    # Charger le système de role selector
    import role_selector
    await role_selector.setup(bot)
    logging.info("✅ Module Role Selector chargé")
    
    # =======================================================

    # Lancer le bot
    try:
        await bot.start(TOKEN)
    except Exception as e:
        logging.error(f"Erreur lors du démarrage du bot: {e}")

if __name__ == "__main__":
    asyncio.run(main())