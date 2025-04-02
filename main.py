import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
from datetime import datetime
import asyncio
import random
import aiohttp
from aiohttp import web
import logging
 
# Configuration du logging
logging.basicConfig(level=logging.INFO)

# Charger les variables d'environnement
load_dotenv()

# Configuration du bot
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.reactions = True

bot = commands.Bot(command_prefix='!', intents=intents)

# Configuration du serveur web
async def setup_webserver():
    app = web.Application()
    
    async def health_check(request):
        return web.Response(text="OK", status=200)
    
    app.router.add_get('/', health_check)
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', int(os.getenv('PORT', 8080)))
    await site.start()
    logging.info(f"Serveur web démarré sur le port {os.getenv('PORT', 8080)}")

# Events du bot
@bot.event
async def on_ready():
    logging.info(f'Bot connecté en tant que {bot.user.name}')
    await bot.change_presence(activity=discord.Game(name="!help pour les commandes"))
    await setup_webserver()

@bot.event
async def on_raw_reaction_add(payload):
    if payload.message_id == 1333072612527439915:
        if str(payload.emoji) == "✅":
            guild = bot.get_guild(payload.guild_id)
            member = guild.get_member(payload.user_id)
            role = guild.get_role(1332401973290340472)

            if role:
                try:
                    await member.add_roles(role)
                    general_channel = bot.get_channel(1326230396903362759)
                    embed = discord.Embed(
                        title="🎉 Nouveau membre respectueux !",
                        description=f"{member.mention} a accepté le règlement et rejoint notre communauté. Bienvenue à toi ! ✨",
                        color=discord.Color.green()
                    )
                    if member.avatar:
                        embed.set_thumbnail(url=member.avatar.url)
                    await general_channel.send(embed=embed)
                except Exception as e:
                    logging.error(f"Erreur lors de l'ajout du rôle : {e}")

@bot.command(name='sendrules')
@commands.has_permissions(administrator=True)
async def send_rules(ctx):
    rules_channel = bot.get_channel(1326211105332265001)
    
    if rules_channel:
        embed = discord.Embed(
            title="📜 Règlement du Serveur",
            description=(
                "Bienvenue sur notre serveur ! Pour garantir une expérience agréable pour tous, "
                "merci de prendre connaissance de nos règles et de les respecter.\n\n"
                "**Réagissez avec ✅ pour confirmer que vous avez lu et accepté le règlement.**"
            ),
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="📌 Règles Essentielles",
            value=(
                "1. Pas de harcèlement, discrimination ou hate speech\n"
                "2. Pas de NSFW, gore ou contenu choquant\n"
                "3. Pas de spam ou flood\n"
                "4. Pas de publicité non autorisée\n"
                "5. Respectez **strictement** la fonction de chaque salon (une description détaillée est disponible pour chaque salon)."
            ),
            inline=False
        )
        
        embed.add_field(
            name="🤝 Comportement & Communication",
            value=(
                "1. Soyez respectueux et bienveillant\n"
                "2. Évitez les sujets sensibles (politique, religion)\n"
                "3. Pas de langage toxique ou excessivement vulgaire\n"
                "4. Privilégiez un dialogue constructif\n"
                "5. Résolvez les conflits en privé"
            ),
            inline=False
        )

        embed.add_field(
            name="🛡️ Sécurité & Confidentialité",
            value=(
                "1. Ne partagez pas d'informations personnelles\n"
                "2. N'envoyez pas de liens suspects\n"
                "3. Ne contournez pas les sanctions\n"
                "4. Signalez les comportements inappropriés\n"
                "5. Protégez votre compte et vos données"
            ),
            inline=False
        )
        
        embed.add_field(
            name="⚖️ Système de Sanctions",
            value=(
                "1. Avertissement\n"
                "2. Mute temporaire (1h à 24h)\n"
                "3. Bannissement temporaire (1 à 7 jours)\n"
                "4. Bannissement définitif\n"
                "*Note : Selon la gravité, certaines étapes peuvent être ignorées.*"
            ),
            inline=False
        )

        embed.add_field(
            name="📱 Spécificités des Salons textuels",
            value=(
                "• Respectez le thème du salon\n"
                "• Évitez les messages trop longs\n"
                "• Utilisez les fils de discussion si nécessaire"
            ),
            inline=False
        )

        embed.add_field(
            name="🎤 Spécificités des Salons vocaux",
            value=(
                "• Évitez les bruits parasites\n"
                "• Pas de soundboard abusif\n"
                "• Respectez ceux qui parlent"
            ),
            inline=False
        )

        embed.add_field(
            name="❗ Informations Importantes",
            value=(
                "• La modération se réserve le droit de sanctionner tout comportement inadéquat\n"
                "• Les règles peuvent être mises à jour à tout moment\n"
                "• En cas de doute, contactez un modérateur via le salon dédié : <#1332088539076104192>"
            ),
            inline=False
        )
        
        embed.set_footer(
            text="Dernière mise à jour : 26/01/2025 | Bon séjour parmi nous ! 🌟"
        )
        
        rules_message = await rules_channel.send(embed=embed)
        await rules_message.add_reaction("✅")
        
        await ctx.send("Les règles ont été envoyées avec succès.")
    else:
        await ctx.send("Impossible de trouver le canal spécifié.")

@bot.event
async def on_raw_reaction_add(payload):
    if payload.message_id == 1333072612527439915:
        if str(payload.emoji) == "✅":
            guild = bot.get_guild(payload.guild_id)
            member = guild.get_member(payload.user_id)
            
            # First role (existing role)
            first_role = guild.get_role(1332401973290340472)
            
            # Second role (new role to be added)
            second_role = guild.get_role(1332763756115005501)
            
            if first_role and second_role:
                try:
                    # Add both roles
                    await member.add_roles(first_role, second_role)
                    
                    general_channel = bot.get_channel(1326230396903362759)
                    embed = discord.Embed(
                        title="🎉 Nouveau membre respectueux !",
                        description=f"{member.mention} a accepté le règlement et rejoint notre communauté. Bienvenue à toi ! ✨",
                        color=discord.Color.green()
                    )
                    if member.avatar:
                        embed.set_thumbnail(url=member.avatar.url)
                    await general_channel.send(embed=embed)
                except Exception as e:
                    logging.error(f"Erreur lors de l'ajout des rôles : {e}")
    
@bot.event
async def on_ready():
    logging.info(f'Bot connecté en tant que {bot.user.name}')
    await bot.change_presence(activity=discord.Game(name="!help pour les commandes"))
    await setup_webserver()

@bot.event
async def on_member_join(member):
    welcome_channel = bot.get_channel(1326211276732502056)
    if welcome_channel:
        # Message de mention avant l'embed
        welcome_message = f"👋 Hey tout le monde ! Accueillons chaleureusement {member.mention} qui vient de nous rejoindre ! 🎉"
        await welcome_channel.send(welcome_message)
        
        embed = discord.Embed(
            title=f"🌟 Bienvenue sur {member.guild.name} !",
            description=(
                f"Hey {member.mention}, bienvenue dans notre communauté !\n\n"
                "🎉 **Nous sommes ravis de t'accueillir parmi nous !**\n\n"
                "Pour bien commencer :\n"
                "📜 Lis le règlement dans <#1326211105332265001>\n"
                "🎯 Choisis tes rôles dans <#1326212401036529665>\n"
                "💬 Présente-toi dans <#1326230396903362759>\n"
                "🎮 Amuse-toi et fais de belles rencontres !"
            ),
            color=discord.Color.blue()
        )
        embed.add_field(
            name="📊 Statistiques",
            value=f"Tu es notre {len(member.guild.members)} ème membre !",
            inline=True
        )
        embed.add_field(
            name="📅 Date d'arrivée",
            value=f"<t:{int(datetime.now().timestamp())}:F>",
            inline=True
        )
        if member.avatar:
            embed.set_thumbnail(url=member.avatar.url)
        embed.set_footer(text="Nous espérons que tu te plairas parmi nous ! 🎮✨")
        await welcome_channel.send(embed=embed)

@bot.event
async def on_member_update(before, after):
    boost_role_id = 1332117069562384385
    boost_channel_id = 1326212624504848394

    # Check if a boost was added
    if len(before.guild.premium_subscribers) < len(after.guild.premium_subscribers):
        boost_channel = bot.get_channel(boost_channel_id)
        boost_role = after.guild.get_role(boost_role_id)
        
        if boost_channel and boost_role:
            # Send boost announcement message
            boost_message = f"🎉 Woohoo ! {after.mention} vient de booster le serveur ! Un grand merci à toi ! 💜"
            await boost_channel.send(boost_message)
            
            # Create and send boost embed
            embed = discord.Embed(
                title="💎 Nouveau Boost !",
                description=f"Merci {after.mention} d'avoir boosté le serveur !",
                color=discord.Color.purple()
            )
            if after.avatar:
                embed.set_thumbnail(url=after.avatar.url)
            await boost_channel.send(embed=embed)
            
            # Add boost role to the member
            await after.add_roles(boost_role)

    # Check if a boost was removed
    elif len(before.guild.premium_subscribers) > len(after.guild.premium_subscribers):
        boost_role = before.guild.get_role(boost_role_id)
        
        if boost_role:
            # Remove boost role from the member
            await before.remove_roles(boost_role)

# Commandes
bot.remove_command('help')

@bot.command()
async def help(ctx):
    embed = discord.Embed(
        title="🤖 Guide des Commandes",
        description="Découvrez les commandes disponibles sur notre serveur",
        color=0x5865F2,  # Bleu Discord
        timestamp=datetime.now()
    )
    
    embed.add_field(
        name="🎮 Interaction Serveur",
        value="""
```
!help     - Afficher ce menu d'aide
!info     - Informations du serveur
!userinfo - Détails du profil utilisateur
!avatar   - Afficher l'avatar
!ping     - Vérifier la latence
!poll     - Créer un sondage
!memes    - Voir les mêmes disponibles
```
""",
        inline=False
    )
    
    embed.set_footer(
        text=f"Demandé par {ctx.author.name} | Utilisez !help pour plus d'infos",
        icon_url=ctx.author.avatar.url if ctx.author.avatar else None
    )
    
    if ctx.guild.icon:
        embed.set_thumbnail(url=ctx.guild.icon.url)
    
    await ctx.send(embed=embed)

@bot.command()
@commands.has_permissions(manage_messages=True)
async def clear(ctx, amount: int):
    if amount <= 0:
        await ctx.send("Le nombre de messages à supprimer doit être supérieur à 0.")
        return
        
    deleted = await ctx.channel.purge(limit=amount + 1)
    # Message de mention avant l'embed
    clear_message = f"🗑️ {ctx.author.mention} a supprimé des messages dans ce salon."
    await ctx.send(clear_message, delete_after=5)
    
    embed = discord.Embed(
        title="🗑️ Messages supprimés",
        description=f'{len(deleted)-1} messages ont été supprimés.',
        color=discord.Color.red()
    )
    await ctx.send(embed=embed, delete_after=5)

@clear.error
async def clear_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        embed = discord.Embed(
            title="❌ Erreur",
            description="Vous n'avez pas la permission de supprimer des messages.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
    elif isinstance(error, commands.MissingRequiredArgument):
        embed = discord.Embed(
            title="❌ Erreur",
            description="Veuillez spécifier le nombre de messages à supprimer. Exemple : !clear 10",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)

@bot.command()
@commands.has_permissions(kick_members=True)
async def kick(ctx, member: discord.Member, *, reason=None):
    # Message de mention avant l'embed
    kick_message = f"👢 {ctx.author.mention} a expulsé {member.mention} du serveur."
    await ctx.send(kick_message)
    
    await member.kick(reason=reason)
    embed = discord.Embed(
        title="👢 Membre expulsé",
        description=f"{member.mention} a été expulsé par {ctx.author.mention}.\nRaison: {reason or 'Aucune raison spécifiée'}",
        color=discord.Color.red()
    )
    await ctx.send(embed=embed)

@bot.command()
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, *, reason=None):
    # Message de mention avant l'embed
    ban_message = f"🔨 {ctx.author.mention} a banni {member.mention} du serveur."
    await ctx.send(ban_message)
    
    await member.ban(reason=reason)
    embed = discord.Embed(
        title="🔨 Membre banni",
        description=f"{member.mention} a été banni par {ctx.author.mention}.\nRaison: {reason or 'Aucune raison spécifiée'}",
        color=discord.Color.red()
    )
    await ctx.send(embed=embed)

@bot.command()
@commands.has_permissions(ban_members=True)
async def unban(ctx, *, member):
    banned_users = await ctx.guild.bans()
    member_name, member_discriminator = member.split('#')

    for ban_entry in banned_users:
        user = ban_entry.user
        if (user.name, user.discriminator) == (member_name, member_discriminator):
            await ctx.guild.unban(user)
            # Message de mention avant l'embed
            unban_message = f"🔓 {ctx.author.mention} a débanni {user.mention}."
            await ctx.send(unban_message)
            
            embed = discord.Embed(
                title="🔓 Membre débanni",
                description=f"{user.mention} a été débanni par {ctx.author.mention}.",
                color=discord.Color.green()
            )
            await ctx.send(embed=embed)
            return

@bot.command()
@commands.has_permissions(kick_members=True)
async def warn(ctx, member: discord.Member, *, reason=None):
    # Message de mention avant l'embed
    warn_message = f"⚠️ {ctx.author.mention} a averti {member.mention}."
    await ctx.send(warn_message)
    
    embed = discord.Embed(
        title="⚠️ Avertissement",
        description=f"{member.mention} a reçu un avertissement de {ctx.author.mention}.\nRaison: {reason or 'Aucune raison spécifiée'}",
        color=discord.Color.orange()
    )
    await ctx.send(embed=embed)

@bot.command()
async def info(ctx):
    # Message de mention avant l'embed
    info_message = f"ℹ️ {ctx.author.mention} a demandé les informations du serveur."
    await ctx.send(info_message)
    
    embed = discord.Embed(
        title=f"ℹ️ Informations sur {ctx.guild.name}",
        color=discord.Color.blue(),
        timestamp=datetime.now()
    )
    
    embed.add_field(name="📊 Membres", value=ctx.guild.member_count)
    embed.add_field(name="📅 Créé le", value=ctx.guild.created_at.strftime("%d/%m/%Y"))
    embed.add_field(name="👑 Propriétaire", value=ctx.guild.owner.mention)
    
    if ctx.guild.icon:
        embed.set_thumbnail(url=ctx.guild.icon.url)
    
    await ctx.send(embed=embed)

@bot.command()
async def userinfo(ctx, member: discord.Member = None):
    member = member or ctx.author
    # Message de mention avant l'embed
    userinfo_message = f"ℹ️ {ctx.author.mention} a demandé les informations de {member.mention}."
    await ctx.send(userinfo_message)
    
    roles = [role.mention for role in member.roles if role.name != "@everyone"]
    
    embed = discord.Embed(
        title=f"ℹ️ Informations sur {member.name}",
        color=member.color,
        timestamp=datetime.now()
    )
    
    embed.add_field(name="📅 A rejoint le", value=member.joined_at.strftime("%d/%m/%Y"))
    embed.add_field(name="🔰 Compte créé le", value=member.created_at.strftime("%d/%m/%Y"))
    embed.add_field(name="🏷️ Rôles", value=" ".join(roles) if roles else "Aucun rôle", inline=False)
    
    if member.avatar:
        embed.set_thumbnail(url=member.avatar.url)
    await ctx.send(embed=embed)

@bot.command()
async def poll(ctx, *, poll_input=None):
    if not poll_input:
        embed = discord.Embed(
            title="❌ Erreur de création de sondage",
            description=(
                "Utilisation correcte : `!poll \"Votre question\" Option1 Option2 Option3...`\n\n"
                "Règles :\n"
                "• Mettez la question entre guillemets\n"
                "• Ajoutez 2-10 options séparées par des espaces\n"
                "• Exemple : `!poll \"Quel est votre jeu préféré ?\" Minecraft Fortnite Roblox`"
            ),
            color=discord.Color.red()
        )
        return await ctx.send(embed=embed)
    
    # Split the input, first part is the question (in quotes), rest are options
    try:
        parts = poll_input.split('"')
        question = parts[1].strip()
        options = parts[2].strip().split()
    except (IndexError, ValueError):
        embed = discord.Embed(
            title="❌ Format de sondage incorrect",
            description="Assurez-vous de mettre la question entre guillemets.",
            color=discord.Color.red()
        )
        return await ctx.send(embed=embed)

    # Validate options
    if len(options) < 2:
        embed = discord.Embed(
            title="❌ Pas assez d'options",
            description="Un sondage nécessite au moins 2 options.",
            color=discord.Color.red()
        )
        return await ctx.send(embed=embed)

    if len(options) > 10:
        embed = discord.Embed(
            title="❌ Trop d'options",
            description="Un sondage ne peut pas avoir plus de 10 options.",
            color=discord.Color.red()
        )
        return await ctx.send(embed=embed)
    
    # Emoji for reactions
    reactions = ['1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣', '6️⃣', '7️⃣', '8️⃣', '9️⃣', '🔟']
    
    # Prepare poll description
    description = []
    for i, option in enumerate(options):
        description.append(f"{reactions[i]} {option}")
    
    # Create poll embed
    embed = discord.Embed(
        title=f"📊 Sondage : {question}",
        description='\n'.join(description),
        color=discord.Color.blue()
    )
    embed.set_footer(text=f"Sondage créé par {ctx.author.name}")
    
    # Send poll message
    poll_msg = await ctx.send(embed=embed)
    
    # Add reaction emojis
    for i in range(len(options)):
        await poll_msg.add_reaction(reactions[i])

@bot.command()
async def avatar(ctx, member: discord.Member = None):
    member = member or ctx.author
    
    embed = discord.Embed(
        title=f"Avatar de {member.name}",
        color=member.color
    )
    if member.avatar:
        embed.set_image(url=member.avatar.url)
    
    await ctx.send(embed=embed)

@bot.command()
async def ping(ctx):
    # Message de mention avant l'embed
    ping_message = f"🏓 {ctx.author.mention} a vérifié la latence du bot."
    await ctx.send(ping_message)
    
    embed = discord.Embed(
        title="🏓 Pong!",
        description=f"Latence: {round(bot.latency * 1000)}ms",
        color=discord.Color.green()
    )
    await ctx.send(embed=embed)

# Commande pour les annonces de nouveaux chapitres (manga)
@bot.command(name='newchapter_collab')
@commands.has_permissions(administrator=True)
async def announce_new_chapter(ctx, manga_name: str, chapter_number: str, chapter_link: str, *, description: str = None):
    if ctx.channel.id != 1326213946188890142:
        await ctx.send("Cette commande ne peut être utilisée que dans le canal d'annonces approprié.")
        return

    # Define specific role IDs for different mangas
    manga_role_map = {
        "Catenaccio": 1332429989085184010,
        "Uzugami": 1332430247894847529
    }

    # Get the role ID based on manga name, or use default role if not specified
    role_id = manga_role_map.get(manga_name, 1326795946134343692)

    role = ctx.guild.get_role(role_id)

    if not role:
        await ctx.send("Le rôle spécifié n'a pas été trouvé.")
        return

    # Petit rappel en haut du message
    reminder_text = (
        f"{role.mention}\n"
        "───────────────────────\n"
        f"Un nouveau chapitre de {manga_name.upper()} vient d'être publié !\n"
        "Retrouvez tous les détails ci-dessous ⬇️"
    )

    # Créer l'embed avec un design amélioré
    embed = discord.Embed(
        title=f"🔥 NOUVEAU CHAPITRE DE {manga_name.upper()} 🔥",
        description=(
            "Un nouveau chapitre vient d'arriver ! Préparez-vous à plonger dans de nouvelles "
            "aventures palpitantes !\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━"
        ),
        color=0x1E90FF  # Bleu royal
    )

    # Informations sur le chapitre
    embed.add_field(
        name="📖 Chapitre",
        value=f"#{chapter_number}",
        inline=True
    )

    embed.add_field(
        name="⏰ Disponible",
        value="MAINTENANT !",
        inline=True
    )

    # Lien de lecture
    embed.add_field(
        name="📚 Lien de lecture",
        value=f"[Cliquez ici pour lire le chapitre !]({chapter_link})",
        inline=False
    )

    # Séparateur
    embed.add_field(
        name="━━━━━━━━━━━━━━━━━━━━━━━━",
        value="",
        inline=False
    )

    # Description si fournie
    if description:
        embed.add_field(
            name="📝 Aperçu",
            value=f"{description}",
            inline=False
        )

    # Note de bas de page
    embed.set_footer(
        text=(
            "N'oubliez pas de partager vos théories et réactions sur twitter et discord ! "
            "Bonne lecture à tous ! 🎉"
        )
    )

    # Envoyer l'annonce
    announcement = await ctx.send(reminder_text, embed=embed)

    # Ajouter plusieurs réactions
    reactions = ["🔥", "👀", "❤️"]
    for reaction in reactions:
        await announcement.add_reaction(reaction)

    # Supprimer la commande originale
    await ctx.message.delete()
 
@bot.event
async def on_message(message):
    # Ignore messages from the bot itself
    if message.author == bot.user:
        return
    
    # Ignore messages from LanorTrad bot
    if message.author.name == "LanorTrad":
        return
    
    # Check if the message is in the specific channel
    if message.channel.id == 1326357401099702393:
        role = message.guild.get_role(1332446295683633304)
        if role:
            await message.channel.send(f"{role.mention}")
    
    # Ensure other commands can still be processed
    await bot.process_commands(message)

# Lancement du bot
def run_bot():
    try:
        bot.run(os.getenv('TOKEN'))
    except Exception as e:
        logging.error(f"Erreur lors du démarrage du bot: {e}")

if __name__ == "__main__":
    run_bot()
