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
# Configuration automatique de Git + GitHub (compatible Render)
# ─────────────────────────────────────────────────────────────────────────────

# URL du repo GitHub (sans token)
GITHUB_REPO_URL = os.getenv("GITHUB_REPO_URL", "https://github.com/L4NOR/LanorTradBot.git")
GITHUB_BRANCH = os.getenv("GITHUB_BRANCH", "main")

# Construire l'URL avec token pour le push
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
if GITHUB_TOKEN:
    # https://github.com/USER/REPO.git → https://TOKEN@github.com/USER/REPO.git
    PUSH_URL = GITHUB_REPO_URL.replace("https://github.com/", f"https://{GITHUB_TOKEN}@github.com/")
else:
    PUSH_URL = None
    logging.warning("⚠️ GITHUB_TOKEN non défini dans les variables d'environnement - git push désactivé")


def setup_git_repo():
    """
    Initialise git si nécessaire et configure le remote.
    Sur Render, le dossier peut ne pas avoir de .git ou de remote.
    """
    repo_dir = os.path.dirname(os.path.abspath(__file__))

    try:
        # Étape 1 : Vérifier si .git existe, sinon init
        git_dir = os.path.join(repo_dir, ".git")
        if not os.path.exists(git_dir):
            logging.info("📂 Pas de .git trouvé — initialisation du repo git...")
            subprocess.run(
                ["git", "init"],
                capture_output=True, text=True, cwd=repo_dir, timeout=10
            )
            subprocess.run(
                ["git", "checkout", "-b", GITHUB_BRANCH],
                capture_output=True, text=True, cwd=repo_dir, timeout=10
            )
            logging.info(f"✅ Repo git initialisé sur la branche {GITHUB_BRANCH}")

        # Étape 2 : Configurer l'identité git
        subprocess.run(
            ["git", "config", "user.name", "LanorTradBot"],
            capture_output=True, text=True, cwd=repo_dir, timeout=10
        )
        subprocess.run(
            ["git", "config", "user.email", "bot@lanortrad.com"],
            capture_output=True, text=True, cwd=repo_dir, timeout=10
        )

        # Étape 3 : Configurer le remote origin avec le token
        if PUSH_URL:
            # Vérifier si origin existe
            result = subprocess.run(
                ["git", "remote", "get-url", "origin"],
                capture_output=True, text=True, cwd=repo_dir, timeout=10
            )
            if result.returncode != 0:
                # Origin n'existe pas → l'ajouter
                subprocess.run(
                    ["git", "remote", "add", "origin", PUSH_URL],
                    capture_output=True, text=True, cwd=repo_dir, timeout=10
                )
                logging.info("✅ Remote origin ajouté avec authentification")
            else:
                # Origin existe → mettre à jour l'URL avec le token
                subprocess.run(
                    ["git", "remote", "set-url", "origin", PUSH_URL],
                    capture_output=True, text=True, cwd=repo_dir, timeout=10
                )
                logging.info("✅ Remote origin mis à jour avec authentification")

            # Étape 4 : Fetch pour synchroniser avec le remote
            fetch_result = subprocess.run(
                ["git", "fetch", "origin", GITHUB_BRANCH],
                capture_output=True, text=True, cwd=repo_dir, timeout=30
            )
            if fetch_result.returncode == 0:
                # Configurer le tracking de la branche
                subprocess.run(
                    ["git", "branch", f"--set-upstream-to=origin/{GITHUB_BRANCH}", GITHUB_BRANCH],
                    capture_output=True, text=True, cwd=repo_dir, timeout=10
                )
                logging.info(f"✅ Branche {GITHUB_BRANCH} synchronisée avec origin")
            else:
                logging.warning(f"⚠️ Fetch échoué (premier push?) : {fetch_result.stderr.strip()}")

        logging.info("✅ Configuration git complète")
        return True

    except Exception as e:
        logging.error(f"❌ Erreur configuration git: {e}")
        return False


# Exécuter la configuration au chargement du module
setup_git_repo()


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

    # Étape 1: git add data/ (inclut JSON et la BDD SQLite)
    success, stdout, stderr = git_run(["git", "add", "data/"])
    if not success:
        return False, f"Erreur git add: {stderr}"

    # Étape 2: git commit
    success, stdout, stderr = git_run(["git", "commit", "-m", commit_message])
    if not success:
        if "nothing to commit" in stderr or "nothing to commit" in stdout:
            return True, "Aucun changement à commiter."
        return False, f"Erreur git commit: {stderr}"

    # Étape 3: git push (explicitement vers origin/branch)
    success, stdout, stderr = git_run(["git", "push", "origin", GITHUB_BRANCH])
    if not success:
        # Si le push échoue à cause de divergence, tenter un pull --rebase d'abord
        if "rejected" in stderr or "non-fast-forward" in stderr:
            logging.info("🔄 Divergence détectée, tentative de rebase...")
            rb_success, rb_out, rb_err = git_run(["git", "pull", "--rebase", "origin", GITHUB_BRANCH])
            if rb_success:
                success, stdout, stderr = git_run(["git", "push", "origin", GITHUB_BRANCH])
                if not success:
                    return False, f"Erreur git push après rebase: {stderr}"
            else:
                return False, f"Erreur git pull --rebase: {rb_err}"
        else:
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
        # Exporter la BDD en JSON avant la sync
        try:
            from database import db
            db.export_to_json()
            logging.info("📦 Export BDD → JSON effectué avant sync")
        except Exception as e:
            logging.warning(f"⚠️ Export BDD échoué (non bloquant): {e}")

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
