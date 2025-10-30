# main.py
import discord
from discord.ext import commands
import os
import logging
import asyncio
from aiohttp import web
from config import TOKEN, PREFIX, INTENTS, PORT
import events
import commands as cmd

# Configuration du logging
logging.basicConfig(level=logging.INFO)

def main():
    # Configuration du bot
    bot = commands.Bot(command_prefix=PREFIX, intents=INTENTS)
    
    # Configuration du serveur web
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
    
    # Ajout de la méthode setup_webserver au bot
    bot.setup_webserver = setup_webserver
    
    # Chargement des événements
    events.setup(bot)
    
    # Chargement des commandes
    cmd.setup(bot)
    
    # Chargement du système de rappels
    import rappels
    await rappels.setup(bot)
    
    # Lancement du bot
    try:
        bot.run(TOKEN)
    except Exception as e:
        logging.error(f"Erreur lors du démarrage du bot: {e}")

if __name__ == "__main__":
    main()