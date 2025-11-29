# announcements.py
# Commande interactive pour annoncer de nouveaux chapitres
import asyncio
import discord
from discord.ext import commands
from config import CHANNELS
import utils

ADMIN_ROLES = [1326417422663680090, 1330147432847114321]


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
            await ctx.send("📚 Quel est le nom de l'œuvre ? (ex: Tougen Anki)")
            msg = await bot.wait_for('message', check=check, timeout=60)
            manga_name = msg.content.strip()

            await ctx.send("🔢 S'agit-il d'un one-shot ? (oui/non). Répondez `oui` si c'est un one-shot.")
            msg = await bot.wait_for('message', check=check, timeout=30)
            is_oneshot = msg.content.strip().lower() in ("oui", "o", "yes", "y")

            if is_oneshot:
                chapters_str = "One-shot"
            else:
                await ctx.send("📝 Indiquez le(s) numéro(s) de chapitre séparés par des espaces ou des virgules (ex: `216 217 218`).")
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

            await ctx.send("🔗 Fournissez le lien vers la page de lecture (URL complète)")
            msg = await bot.wait_for('message', check=check, timeout=60)
            link = msg.content.strip()
            if not (link.startswith('http://') or link.startswith('https://')):
                await ctx.send("Le lien ne semble pas valide (doit commencer par http:// ou https://). Annulation.")
                return

            await ctx.send("✍️ Souhaitez-vous ajouter une description optionnelle ? Envoyez le texte ou `non` pour ignorer.")
            msg = await bot.wait_for('message', check=check, timeout=120)
            descr = msg.content.strip()
            if descr.lower() in ("non", "n", "no"):
                descr = None

            # Construire et envoyer l'embed
            # utils.create_chapter_announcement_embed attend (manga_name, chapter_number, chapter_link, description=None)
            chapter_param = chapters_str if not is_oneshot else "One-shot"
            embed = await utils.create_chapter_announcement_embed(manga_name, chapter_param, link, description=descr)

            target_channel = ctx.guild.get_channel(CHANNELS.get('chapter_announcements'))
            if not target_channel:
                await ctx.send("⚠️ Le canal d'annonces n'a pas été trouvé dans la configuration.")
                return

            sent = await target_channel.send(embed=embed)

            # Ajout de réactions d'engagement (optionnel)
            reactions = ['🔥', '👀', '❤', '🙂']
            for r in reactions:
                try:
                    await sent.add_reaction(r)
                except Exception:
                    pass

            await ctx.send(f"✅ Annonce publiée dans {target_channel.mention} !")

        except asyncio.TimeoutError:
            await ctx.send("⏱️ Temps écoulé. Commande annulée.")
        except commands.MissingAnyRole:
            await ctx.send("❌ Vous n'avez pas la permission d'utiliser cette commande.")
        except Exception as e:
            await ctx.send(f"❌ Erreur lors de la création de l'annonce : {e}")

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
            await ctx.send("📚 [TEST] Quel est le nom de l'œuvre ? (ex: Tougen Anki)")
            msg = await bot.wait_for('message', check=check, timeout=60)
            manga_name = msg.content.strip()

            await ctx.send("🔢 [TEST] S'agit-il d'un one-shot ? (oui/non). Répondez `oui` si c'est un one-shot.")
            msg = await bot.wait_for('message', check=check, timeout=30)
            is_oneshot = msg.content.strip().lower() in ("oui", "o", "yes", "y")

            if is_oneshot:
                chapters_str = "One-shot"
            else:
                await ctx.send("📝 [TEST] Indiquez le(s) numéro(s) de chapitre séparés par des espaces ou des virgules (ex: `216 217 218`).")
                msg = await bot.wait_for('message', check=check, timeout=60)
                raw = msg.content.strip()
                raw_norm = raw.replace(',', ' ')
                parts = [p for p in raw_norm.split() if p]
                chapters_str = ", ".join(parts)
                if not chapters_str:
                    await ctx.send("Aucun chapitre fourni. Annulation.")
                    return

            await ctx.send("🔗 [TEST] Fournissez le lien vers la page de lecture (URL complète)")
            msg = await bot.wait_for('message', check=check, timeout=60)
            link = msg.content.strip()
            if not (link.startswith('http://') or link.startswith('https://')):
                await ctx.send("Le lien ne semble pas valide (doit commencer par http:// ou https://). Annulation.")
                return

            await ctx.send("✍️ [TEST] Souhaitez-vous ajouter une description optionnelle ? Envoyez le texte ou `non` pour ignorer.")
            msg = await bot.wait_for('message', check=check, timeout=120)
            descr = msg.content.strip()
            if descr.lower() in ("non", "n", "no"):
                descr = None

            chapter_param = chapters_str if not is_oneshot else "One-shot"
            embed = await utils.create_chapter_announcement_embed(manga_name, chapter_param, link, description=descr)

            target_channel = ctx.guild.get_channel(TEST_CHANNEL_ID)
            if not target_channel:
                await ctx.send(f"⚠️ Le canal de test `{TEST_CHANNEL_ID}` n'a pas été trouvé sur ce serveur.")
                return

            sent = await target_channel.send(embed=embed)
            reactions = ['🔥', '👀', '❤', '🙂']
            for r in reactions:
                try:
                    await sent.add_reaction(r)
                except Exception:
                    pass

            await ctx.send(f"✅ Annonce de test publiée dans {target_channel.mention} !")

        except asyncio.TimeoutError:
            await ctx.send("⏱️ Temps écoulé. Commande de test annulée.")
        except commands.MissingAnyRole:
            await ctx.send("❌ Vous n'avez pas la permission d'utiliser cette commande.")
        except Exception as e:
            await ctx.send(f"❌ Erreur lors de la création de l'annonce de test : {e}")
