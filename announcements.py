# announcements.py
# Commande interactive pour annoncer de nouveaux chapitres
import asyncio
import discord
from discord.ext import commands
from config import CHANNELS
import utils

ADMIN_ROLES = [1465027983445331990, 1465027980974620833, 1465027978324086846]


def setup(bot):
    @bot.command(name="announce_chapter")
    @commands.has_any_role(*ADMIN_ROLES)
    async def announce_chapter(ctx):
        """Commande interactive : demande les infos et publie l'annonce de chapitre."""
        author = ctx.author
        channel = ctx.channel
        bot = ctx.bot

        def check(m):
            return m.author == author and m.channel == channel

        try:
            embed_prompt = discord.Embed(title="📚 Quel est le nom de l'œuvre ?", description="(ex: Tougen Anki)", color=discord.Color.blue())
            await ctx.send(embed=embed_prompt)
            msg = await bot.wait_for('message', check=check, timeout=60)
            manga_name = msg.content.strip()
            embed_prompt = discord.Embed(title="🔢 One-shot ?", description="Répondez `oui` si c'est un one-shot.", color=discord.Color.blue())
            await ctx.send(embed=embed_prompt)
            msg = await bot.wait_for('message', check=check, timeout=30)
            is_oneshot = msg.content.strip().lower() in ("oui", "o", "yes", "y")

            if is_oneshot:
                chapters_str = "One-shot"
            else:
                embed_prompt = discord.Embed(title="📝 Numéros de chapitres", description="Indiquez le(s) numéro(s) de chapitre séparés par des espaces ou des virgules (ex: `216 217 218`).", color=discord.Color.blue())
                await ctx.send(embed=embed_prompt)
                msg = await bot.wait_for('message', check=check, timeout=60)
                raw = msg.content.strip()
                # Nettoyage : remplacer virgules par espaces puis normaliser
                raw_norm = raw.replace(',', ' ')
                parts = [p for p in raw_norm.split() if p]
                # Garder tels quels (utilisateur peut entrer des labels non numériques)
                chapters_str = ", ".join(parts)
                if not chapters_str:
                    await ctx.send("Aucun chapitre fourni. Annulation.")
                    return

            embed_prompt = discord.Embed(title="🔗 Lien de lecture", description="Fournissez le lien vers la page de lecture (URL complète)", color=discord.Color.blue())
            await ctx.send(embed=embed_prompt)
            msg = await bot.wait_for('message', check=check, timeout=60)
            link = msg.content.strip()
            if not (link.startswith('http://') or link.startswith('https://')):
                embed_err = discord.Embed(title="❌ Lien invalide", description="Le lien ne semble pas valide (doit commencer par http:// ou https://). Annulation.", color=discord.Color.red())
                await ctx.send(embed=embed_err)
                return
            embed_prompt = discord.Embed(title="✍️ Description optionnelle", description="Envoyez le texte ou `non` pour ignorer.", color=discord.Color.blue())
            await ctx.send(embed=embed_prompt)
            msg = await bot.wait_for('message', check=check, timeout=120)
            descr = msg.content.strip()
            if descr.lower() in ("non", "n", "no"):
                descr = None

            # Construire et envoyer l'embed
            # utils.create_chapter_announcement_embed attend (manga_name, chapter_number, chapter_link, description=None)
            chapter_param = chapters_str if not is_oneshot else "One-shot"
            embed = await utils.create_chapter_announcement_embed(manga_name, chapter_param, link, description=descr)

            # Poster uniquement dans le canal dédié (ID forcé)
            TARGET_CHANNEL_ID = 1326213946188890142
            target_channel = ctx.guild.get_channel(TARGET_CHANNEL_ID)
            if not target_channel:
                embed_err = discord.Embed(title="⚠️ Canal introuvable", description=f"Le canal cible `{TARGET_CHANNEL_ID}` n'a pas été trouvé sur ce serveur.", color=discord.Color.orange())
                await ctx.send(embed=embed_err)
                return

            sent = await target_channel.send(embed=embed)

            # Ajout de réactions d'engagement (optionnel)
            reactions = ['🔥', '👀', '❤']
            for r in reactions:
                try:
                    await sent.add_reaction(r)
                except Exception:
                    pass

            embed_success = discord.Embed(title="✅ Annonce publiée", description=f"Annonce publiée dans {target_channel.mention}.", color=discord.Color.green())
            await ctx.send(embed=embed_success)

        except asyncio.TimeoutError:
            embed_err = discord.Embed(title="⏱️ Temps écoulé", description="Commande annulée par timeout.", color=discord.Color.red())
            await ctx.send(embed=embed_err)
        except commands.MissingAnyRole:
            embed_err = discord.Embed(title="❌ Permission manquante", description="Vous n'avez pas la permission d'utiliser cette commande.", color=discord.Color.red())
            await ctx.send(embed=embed_err)
        except Exception as e:
            embed_err = discord.Embed(title="❌ Erreur", description=f"Erreur lors de la création de l'annonce : {e}", color=discord.Color.red())
            await ctx.send(embed=embed_err)

    @bot.command(name="test_announce")
    @commands.has_any_role(*ADMIN_ROLES)
    async def test_announce(ctx):
        """Test : crée un aperçu de l'annonce et l'envoie dans le canal de test (fixe)."""
        TEST_CHANNEL_ID = 1330221808753840159
        author = ctx.author
        channel = ctx.channel
        bot = ctx.bot

        def check(m):
            return m.author == author and m.channel == channel

        try:
            embed_prompt = discord.Embed(title="📚 [TEST] Quel est le nom de l'œuvre ?", description="(ex: Tougen Anki)", color=discord.Color.blue())
            await ctx.send(embed=embed_prompt)
            msg = await bot.wait_for('message', check=check, timeout=60)
            manga_name = msg.content.strip()

            embed_prompt = discord.Embed(title="🔢 [TEST] One-shot ?", description="Répondez `oui` si c'est un one-shot.", color=discord.Color.blue())
            await ctx.send(embed=embed_prompt)
            msg = await bot.wait_for('message', check=check, timeout=30)
            is_oneshot = msg.content.strip().lower() in ("oui", "o", "yes", "y")

            if is_oneshot:
                chapters_str = "One-shot"
            else:
                embed_prompt = discord.Embed(title="📝 [TEST] Numéros de chapitres", description="Indiquez le(s) numéro(s) de chapitre séparés par des espaces ou des virgules (ex: `216 217 218`).", color=discord.Color.blue())
                await ctx.send(embed=embed_prompt)
                msg = await bot.wait_for('message', check=check, timeout=60)
                raw = msg.content.strip()
                raw_norm = raw.replace(',', ' ')
                parts = [p for p in raw_norm.split() if p]
                chapters_str = ", ".join(parts)
                if not chapters_str:
                    await ctx.send("Aucun chapitre fourni. Annulation.")
                    return

            embed_prompt = discord.Embed(title="🔗 [TEST] Lien de lecture", description="Fournissez le lien vers la page de lecture (URL complète)", color=discord.Color.blue())
            await ctx.send(embed=embed_prompt)
            msg = await bot.wait_for('message', check=check, timeout=60)
            link = msg.content.strip()
            if not (link.startswith('http://') or link.startswith('https://')):
                embed_err = discord.Embed(title="❌ Lien invalide", description="Le lien ne semble pas valide (doit commencer par http:// ou https://). Annulation.", color=discord.Color.red())
                await ctx.send(embed=embed_err)
                return

            embed_prompt = discord.Embed(title="✍️ [TEST] Description optionnelle", description="Envoyez le texte ou `non` pour ignorer.", color=discord.Color.blue())
            await ctx.send(embed=embed_prompt)
            msg = await bot.wait_for('message', check=check, timeout=120)
            descr = msg.content.strip()
            if descr.lower() in ("non", "n", "no"):
                descr = None

            chapter_param = chapters_str if not is_oneshot else "One-shot"
            embed = await utils.create_chapter_announcement_embed(manga_name, chapter_param, link, description=descr)

            target_channel = ctx.guild.get_channel(TEST_CHANNEL_ID)
            if not target_channel:
                embed_err = discord.Embed(title="⚠️ Canal de test introuvable", description=f"Le canal de test `{TEST_CHANNEL_ID}` n'a pas été trouvé sur ce serveur.", color=discord.Color.orange())
                await ctx.send(embed=embed_err)
                return

            sent = await target_channel.send(embed=embed)
            reactions = ['🔥', '👀', '❤']
            for r in reactions:
                try:
                    await sent.add_reaction(r)
                except Exception:
                    pass

            embed_success = discord.Embed(title="✅ Annonce de test publiée", description=f"Annonce de test publiée dans {target_channel.mention}.", color=discord.Color.green())
            await ctx.send(embed=embed_success)

        except asyncio.TimeoutError:
            embed_err = discord.Embed(title="⏱️ Temps écoulé", description="Commande de test annulée par timeout.", color=discord.Color.red())
            await ctx.send(embed=embed_err)
        except commands.MissingAnyRole:
            embed_err = discord.Embed(title="❌ Permission manquante", description="Vous n'avez pas la permission d'utiliser cette commande.", color=discord.Color.red())
            await ctx.send(embed=embed_err)
        except Exception as e:
            embed_err = discord.Embed(title="❌ Erreur", description=f"Erreur lors de la création de l'annonce de test : {e}", color=discord.Color.red())
            await ctx.send(embed=embed_err)