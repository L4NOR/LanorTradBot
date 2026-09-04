"""
Gestionnaire d'erreurs global pour les slash commands
======================================================
Au lieu de laisser une commande planter en silence (l'utilisateur voit
juste "L'application ne répond pas"), on intercepte chaque erreur :
  - message clair et bilingue à l'utilisateur (ephemeral)
  - trace complète loggée côté serveur
"""
import logging

import discord
from discord import app_commands
from discord.ext import commands

log = logging.getLogger("lanortrad.errors")


class ErrorHandler(commands.Cog):
    """Capture les erreurs des slash commands."""

    def __init__(self, bot):
        self.bot = bot
        # On branche notre handler sur l'arbre de commandes
        self._previous = bot.tree.on_error
        bot.tree.on_error = self.on_app_command_error

    async def cog_unload(self):
        # Restaure le handler d'origine si le cog est déchargé
        self.bot.tree.on_error = self._previous

    async def on_app_command_error(
        self,
        interaction: discord.Interaction,
        error: app_commands.AppCommandError,
    ):
        # ─── Erreurs "attendues" → message court ───
        if isinstance(error, app_commands.CommandOnCooldown):
            msg = f"⏳ Doucement — réessaie dans **{error.retry_after:.0f}s**."
        elif isinstance(error, app_commands.MissingPermissions):
            msg = "🚫 Tu n'as pas la permission d'utiliser cette commande."
        elif isinstance(error, app_commands.BotMissingPermissions):
            perms = ", ".join(error.missing_permissions)
            msg = f"🚫 Il me manque des permissions : `{perms}`."
        elif isinstance(error, app_commands.CheckFailure):
            msg = "🚫 Tu ne peux pas utiliser cette commande ici."
        else:
            # ─── Erreur inattendue → log complet + message générique ───
            cmd = interaction.command.name if interaction.command else "?"
            log.exception("Erreur dans /%s : %s", cmd, error)
            msg = (
                "❌ Une erreur interne est survenue. Le staff a été notifié.\n"
                "🇬🇧 An internal error occurred. Staff has been notified."
            )

        # Répond proprement, que l'interaction soit déjà déférée ou non
        try:
            if interaction.response.is_done():
                await interaction.followup.send(msg, ephemeral=True)
            else:
                await interaction.response.send_message(msg, ephemeral=True)
        except discord.HTTPException:
            pass


async def setup(bot):
    await bot.add_cog(ErrorHandler(bot))
