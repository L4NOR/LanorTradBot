# github_sync.py
# ═══════════════════════════════════════════════════════════════════════════════
# SYNCHRONISATION GITHUB AUTOMATIQUE - Commit & Push des données
# ═══════════════════════════════════════════════════════════════════════════════

import discord
from discord.ext import commands, tasks
import subprocess
import os
import logging
from datetime import datetime
from config import ADMIN_ROLES, COLORS, GITHUB_SYNC

# Historique des syncs
sync_history = []
MAX_HISTORY = 20

# ─────────────────────────────────────────────────────────────────────────────
# Configuration automatique de l'authentification GitHub
# ─────────────────────────────────────────────────────────────────────────────

def setup_git_auth():
    """
    Configure l'authentification GitHub pour le push.
    Utilise GITHUB_TOKEN depuis les variables d'environnement.
    Compatible avec Render et autres hébergeurs cloud.
    """
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        logging.warning("⚠️ GITHUB_TOKEN non défini - le git push pourrait échouer")
        return False

    repo_dir = os.path.dirname(os.path.abspath(__file__))

    # Récupérer l'URL remote actuelle
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            capture_output=True, text=True, cwd=repo_dir, timeout=10
        )
        if result.returncode != 0:
            logging.error("❌ Impossible de récupérer l'URL remote git")
            return False

        current_url = result.stdout.strip()

        # Si l'URL contient déjà un token, ne rien faire
        if "@" in current_url and "github.com" in current_url:
            logging.info("✅ Authentification GitHub déjà configurée")
            return True

        # Transformer https://github.com/USER/REPO.git
        # en https://<TOKEN>@github.com/USER/REPO.git
        if current_url.startswith("https://github.com/"):
            new_url = current_url.replace(
                "https://github.com/",
                f"https://{token}@github.com/"
            )
            subprocess.run(
                ["git", "remote", "set-url", "origin", new_url],
                capture_output=True, text=True, cwd=repo_dir, timeout=10
            )
            logging.info("✅ Authentification GitHub configurée avec succès")
            return True
        else:
            logging.warning(f"⚠️ URL remote non standard: {current_url}")
            return False

    except Exception as e:
        logging.error(f"❌ Erreur configuration auth GitHub: {e}")
        return False


def setup_git_identity():
    """Configure l'identité git si pas déjà définie (nécessaire pour commit)"""
    repo_dir = os.path.dirname(os.path.abspath(__file__))

    # Vérifier si user.name est défini
    result = subprocess.run(
        ["git", "config", "user.name"],
        capture_output=True, text=True, cwd=repo_dir, timeout=10
    )
    if not result.stdout.strip():
        subprocess.run(
            ["git", "config", "user.name", "LanorTradBot"],
            capture_output=True, text=True, cwd=repo_dir, timeout=10
        )

    # Vérifier si user.email est défini
    result = subprocess.run(
        ["git", "config", "user.email"],
        capture_output=True, text=True, cwd=repo_dir, timeout=10
    )
    if not result.stdout.strip():
        subprocess.run(
            ["git", "config", "user.email", "bot@lanortrad.com"],
            capture_output=True, text=True, cwd=repo_dir, timeout=10
        )

    logging.info("✅ Identité git configurée")


# Exécuter la configuration au chargement du module
setup_git_auth()
setup_git_identity()


def git_run(cmd, cwd=None):
    """Exécute une commande git et retourne le résultat"""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=cwd or os.path.dirname(os.path.abspath(__file__)),
            timeout=30
        )
        return result.returncode == 0, result.stdout.strip(), result.stderr.strip()
    except subprocess.TimeoutExpired:
        return False, "", "Timeout: la commande a pris trop de temps"
    except Exception as e:
        return False, "", str(e)


def git_has_changes():
    """Vérifie s'il y a des changements dans le dossier data/"""
    success, stdout, _ = git_run(["git", "status", "--porcelain", "data/"])
    if success and stdout:
        return True
    return False


def git_get_changed_files():
    """Retourne la liste des fichiers modifiés dans data/"""
    success, stdout, _ = git_run(["git", "status", "--porcelain", "data/"])
    if success and stdout:
        files = []
        for line in stdout.strip().split("\n"):
            if line.strip():
                # Format: "XY filename"
                parts = line.strip().split(None, 1)
                if len(parts) >= 2:
                    files.append(parts[1])
                else:
                    files.append(line.strip())
        return files
    return []


def git_sync(commit_message=None):
    """
    Effectue un git add + commit + push pour le dossier data/
    Retourne (success, message)
    """
    prefix = GITHUB_SYNC.get("commit_prefix", "🔄 sync:")
    if not commit_message:
        commit_message = f"{prefix} mise à jour données {datetime.now().strftime('%d/%m/%Y %H:%M')}"
    else:
        commit_message = f"{prefix} {commit_message}"

    # Étape 1: git add data/
    success, stdout, stderr = git_run(["git", "add", "data/"])
    if not success:
        return False, f"Erreur git add: {stderr}"

    # Étape 2: git commit
    success, stdout, stderr = git_run(["git", "commit", "-m", commit_message])
    if not success:
        if "nothing to commit" in stderr or "nothing to commit" in stdout:
            return True, "Aucun changement à commiter."
        return False, f"Erreur git commit: {stderr}"

    # Étape 3: git push
    success, stdout, stderr = git_run(["git", "push"])
    if not success:
        return False, f"Erreur git push: {stderr}"

    return True, f"Sync réussi: {commit_message}"


def get_last_commit_info():
    """Récupère les infos du dernier commit"""
    success, stdout, _ = git_run(["git", "log", "-1", "--format=%h|%s|%cr"])
    if success and stdout:
        parts = stdout.split("|", 2)
        if len(parts) >= 3:
            return {
                "hash": parts[0],
                "message": parts[1],
                "time_ago": parts[2]
            }
    return None


class GitHubSync(commands.Cog):
    """Synchronisation automatique avec GitHub"""

    def __init__(self, bot):
        self.bot = bot
        self.auto_sync_loop.start()
        logging.info("✅ Module GitHubSync initialisé")

    def cog_unload(self):
        self.auto_sync_loop.cancel()

    # ─────────────────────────────────────────────────────────────────────────
    # AUTO-SYNC (toutes les 30 minutes)
    # ─────────────────────────────────────────────────────────────────────────

    @tasks.loop(seconds=GITHUB_SYNC.get("auto_sync_interval", 1800))
    async def auto_sync_loop(self):
        """Vérifie et sync automatiquement toutes les 30 min"""
        if not git_has_changes():
            return

        changed_files = git_get_changed_files()
        nb_files = len(changed_files)

        success, message = git_sync(f"auto-sync {nb_files} fichier(s) modifié(s)")

        sync_entry = {
            "time": datetime.now().isoformat(),
            "type": "auto",
            "success": success,
            "message": message,
            "files": changed_files
        }
        sync_history.append(sync_entry)
        if len(sync_history) > MAX_HISTORY:
            sync_history.pop(0)

        if success:
            logging.info(f"🔄 Auto-sync: {nb_files} fichier(s) synchronisé(s)")

            # Notification dans le channel de sync
            sync_channel_id = GITHUB_SYNC.get("sync_channel")
            if sync_channel_id:
                channel = self.bot.get_channel(sync_channel_id)
                if channel:
                    embed = discord.Embed(
                        title="🔄 Auto-sync GitHub",
                        description=f"**{nb_files}** fichier(s) synchronisé(s) avec succès",
                        color=COLORS["success"],
                        timestamp=datetime.now()
                    )
                    files_text = "\n".join([f"• `{f}`" for f in changed_files[:10]])
                    if len(changed_files) > 10:
                        files_text += f"\n• *+{len(changed_files) - 10} autres...*"
                    embed.add_field(name="📁 Fichiers", value=files_text, inline=False)
                    embed.set_footer(text="Synchronisation automatique")

                    try:
                        await channel.send(embed=embed)
                    except:
                        pass
        else:
            logging.error(f"❌ Auto-sync échoué: {message}")

    @auto_sync_loop.before_loop
    async def before_auto_sync(self):
        await self.bot.wait_until_ready()

    # ─────────────────────────────────────────────────────────────────────────
    # COMMANDES MANUELLES
    # ─────────────────────────────────────────────────────────────────────────

    @commands.command(name="sync")
    @commands.has_any_role(*ADMIN_ROLES)
    async def manual_sync(self, ctx, *, message: str = None):
        """
        Force la synchronisation des données avec GitHub

        Usage: !sync [message de commit optionnel]
        """
        if not git_has_changes():
            embed = discord.Embed(
                title="✅ Tout est à jour",
                description="Aucun changement à synchroniser.",
                color=COLORS["info"]
            )
            last_commit = get_last_commit_info()
            if last_commit:
                embed.add_field(
                    name="📋 Dernier commit",
                    value=f"`{last_commit['hash']}` {last_commit['message']}\n*{last_commit['time_ago']}*"
                )
            await ctx.send(embed=embed)
            return

        # Afficher les fichiers qui vont être sync
        changed_files = git_get_changed_files()
        nb_files = len(changed_files)

        loading_embed = discord.Embed(
            title="🔄 Synchronisation en cours...",
            description=f"Envoi de **{nb_files}** fichier(s) vers GitHub...",
            color=COLORS["warning"]
        )
        loading_msg = await ctx.send(embed=loading_embed)

        commit_msg = message or f"sync manuelle par {ctx.author.name} — {nb_files} fichier(s)"
        success, result_message = git_sync(commit_msg)

        sync_entry = {
            "time": datetime.now().isoformat(),
            "type": "manual",
            "user": str(ctx.author),
            "success": success,
            "message": result_message,
            "files": changed_files
        }
        sync_history.append(sync_entry)
        if len(sync_history) > MAX_HISTORY:
            sync_history.pop(0)

        if success:
            embed = discord.Embed(
                title="✅ Synchronisation réussie !",
                description=f"**{nb_files}** fichier(s) envoyé(s) vers GitHub",
                color=COLORS["success"],
                timestamp=datetime.now()
            )
            files_text = "\n".join([f"• `{f}`" for f in changed_files[:15]])
            if len(changed_files) > 15:
                files_text += f"\n• *+{len(changed_files) - 15} autres...*"
            embed.add_field(name="📁 Fichiers synchronisés", value=files_text, inline=False)
            embed.set_footer(text=f"Par {ctx.author.name}")
        else:
            embed = discord.Embed(
                title="❌ Erreur de synchronisation",
                description=f"```{result_message}```",
                color=COLORS["error"]
            )

        await loading_msg.edit(embed=embed)

    @commands.command(name="sync_status", aliases=["gitstatus"])
    @commands.has_any_role(*ADMIN_ROLES)
    async def sync_status(self, ctx):
        """Affiche l'état de la synchronisation GitHub"""
        embed = discord.Embed(
            title="📊 Statut GitHub Sync",
            color=COLORS["info"],
            timestamp=datetime.now()
        )

        # Dernier commit
        last_commit = get_last_commit_info()
        if last_commit:
            embed.add_field(
                name="📋 Dernier commit",
                value=f"`{last_commit['hash']}` {last_commit['message']}\n*{last_commit['time_ago']}*",
                inline=False
            )

        # Changements en attente
        changed = git_get_changed_files()
        if changed:
            files_text = "\n".join([f"• `{f}`" for f in changed[:10]])
            if len(changed) > 10:
                files_text += f"\n• *+{len(changed) - 10} autres...*"
            embed.add_field(
                name=f"⚠️ {len(changed)} changement(s) en attente",
                value=files_text,
                inline=False
            )
        else:
            embed.add_field(
                name="✅ Tout est synchronisé",
                value="Aucun changement en attente.",
                inline=False
            )

        # Auto-sync info
        interval = GITHUB_SYNC.get("auto_sync_interval", 1800)
        embed.add_field(
            name="⏰ Auto-sync",
            value=f"Toutes les {interval // 60} minutes",
            inline=True
        )

        await ctx.send(embed=embed)

    @commands.command(name="sync_log", aliases=["synclog"])
    @commands.has_any_role(*ADMIN_ROLES)
    async def sync_log(self, ctx, count: int = 5):
        """Affiche l'historique des synchronisations"""
        if not sync_history:
            await ctx.send("📭 Aucun historique de synchronisation disponible.")
            return

        count = min(count, 10)
        recent = list(reversed(sync_history[-count:]))

        embed = discord.Embed(
            title="📜 Historique des Sync",
            color=COLORS["info"],
            timestamp=datetime.now()
        )

        for entry in recent:
            time_str = datetime.fromisoformat(entry["time"]).strftime("%d/%m %H:%M")
            status = "✅" if entry["success"] else "❌"
            sync_type = "🤖 Auto" if entry["type"] == "auto" else "👤 Manuel"
            user_str = f" par {entry.get('user', 'bot')}" if entry.get("user") else ""
            nb_files = len(entry.get("files", []))

            embed.add_field(
                name=f"{status} {sync_type} — {time_str}{user_str}",
                value=f"{nb_files} fichier(s) • {entry.get('message', 'N/A')[:80]}",
                inline=False
            )

        embed.set_footer(text=f"Affichage des {len(recent)} dernières syncs")
        await ctx.send(embed=embed)


async def setup(bot):
    """Setup pour discord.py 2.0+"""
    await bot.add_cog(GitHubSync(bot))
    logging.info("✅ Cog GitHubSync chargé avec succès")
