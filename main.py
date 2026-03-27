# main.py
# ═══════════════════════════════════════════════════════════════════════════════
# POINT D'ENTRÉE PRINCIPAL DU BOT DISCORD LANORTRAD
# ═══════════════════════════════════════════════════════════════════════════════

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


async def main():
    """Fonction principale pour démarrer le bot."""
    
    bot = commands.Bot(command_prefix=PREFIX, intents=INTENTS)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # SERVEUR WEB INTERNE (pour les health checks)
    # ═══════════════════════════════════════════════════════════════════════════
    
    bot._web_runner = None

    async def setup_webserver():
        """Configure et démarre le serveur web pour les health checks."""
        app = web.Application()

        async def health_check(request):
            return web.Response(text="OK", status=200)

        app.router.add_get('/', health_check)
        runner = web.AppRunner(app)
        await runner.setup()
        bot._web_runner = runner
        site = web.TCPSite(runner, '0.0.0.0', PORT)
        await site.start()
        logging.info(f"Serveur web démarré sur le port {PORT}")

    bot.setup_webserver = setup_webserver

    # ═══════════════════════════════════════════════════════════════════════════
    # CHARGEMENT DES MODULES
    # ═══════════════════════════════════════════════════════════════════════════
    
    # Charger les événements (synchrone)
    import events
    events.setup(bot)
    logging.info("✅ Module Events chargé")

    # Charger les commandes principales (synchrone)
    import commands as cmd
    cmd.setup(bot)
    logging.info("✅ Module Commands chargé")

    # Charger le module d'annonces (synchrone)
    import announcements
    announcements.setup(bot)
    logging.info("✅ Module Announcements chargé")

    # ═══════════════════════════════════════════════════════════════════════════
    # MODULES ASYNCHRONES (COGS)
    # ═══════════════════════════════════════════════════════════════════════════

    # Charger les rappels
    import rappels
    await rappels.setup(bot)
    logging.info("✅ Module Rappels chargé")

    # Charger le système de giveaway
    import giveaway
    await giveaway.setup(bot)
    logging.info("✅ Module Giveaway chargé")
    
    # Charger le système communautaire
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

    # Charger le système de role selector
    import role_selector
    await role_selector.setup(bot)
    logging.info("✅ Module Role Selector chargé")

    # Charger le système d'audit/logs
    import logs
    await logs.setup(bot)
    logging.info("✅ Module Audit Logs chargé")

    # Charger le système de sondages
    import polls
    await polls.setup(bot)
    logging.info("✅ Module Polls chargé")

    # Charger le système de tickets et candidatures
    import tickets
    await tickets.setup(bot)
    logging.info("✅ Module Tickets chargé")

    # Charger les statistiques du serveur
    import stats
    await stats.setup(bot)
    logging.info("✅ Module Stats chargé")

    # Initialiser la base de données
    import database
    logging.info("✅ Module Database initialisé")

    # Charger le système de planning
    import planning
    await planning.setup(bot)
    logging.info("✅ Module Planning chargé")

    # ═══════════════════════════════════════════════════════════════════════════
    # DÉMARRAGE DU BOT
    # ═══════════════════════════════════════════════════════════════════════════

    max_retries = 5
    retry_delay = 60  # secondes

    for attempt in range(1, max_retries + 1):
        try:
            logging.info(f"Démarrage du bot... (tentative {attempt}/{max_retries})")
            await bot.start(TOKEN)
            break  # Connexion réussie puis déconnexion normale
        except discord.LoginFailure:
            logging.error("Token Discord invalide. Vérifiez votre fichier .env")
            break  # Inutile de réessayer avec un mauvais token
        except discord.HTTPException as e:
            if e.status == 429:
                wait = retry_delay * attempt
                logging.warning(f"⚠️ Rate limited par Discord (429). Nouvelle tentative dans {wait}s...")
                await asyncio.sleep(wait)
                # Recréer le bot car la session est corrompue après un 429
                if not bot.is_closed():
                    await bot.close()
                bot = commands.Bot(command_prefix=PREFIX, intents=INTENTS)
                bot._web_runner = None
                bot.setup_webserver = setup_webserver
            else:
                logging.error(f"Erreur HTTP Discord: {e}")
                break
        except Exception as e:
            logging.error(f"Erreur lors du démarrage du bot: {e}")
            break

    # Nettoyage final
    if bot._web_runner:
        await bot._web_runner.cleanup()
    if not bot.is_closed():
        await bot.close()


if __name__ == "__main__":
    asyncio.run(main())