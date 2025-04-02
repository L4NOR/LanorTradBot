# utils.py
import discord
import datetime
import logging
from discord.ext import commands
from config import COLORS, CHANNELS, ROLES

def format_help(command):
    """Formate l'aide d'une commande en embed"""
    embed = discord.Embed(
        title=f"Commande: {command.name}",
        description=command.help or "Aucune description disponible.",
        color=discord.Color(COLORS["info"])
    )
    
    # Ajouter les aliases si présents
    if command.aliases:
        embed.add_field(name="Aliases", value=", ".join(command.aliases), inline=False)
    
    # Ajouter la syntaxe
    signature = command.signature
    embed.add_field(name="Syntaxe", value=f"`{command.name} {signature}`", inline=False)
    
    return embed

def get_user_info(user):
    """Génère un embed avec les informations utilisateur"""
    embed = discord.Embed(
        title=f"Informations sur {user.name}",
        color=discord.Color(COLORS["info"]),
        timestamp=datetime.datetime.utcnow()
    )
    
    # Informations de base
    embed.set_thumbnail(url=user.avatar.url if user.avatar else user.default_avatar.url)
    embed.add_field(name="ID", value=user.id, inline=True)
    embed.add_field(name="Nom d'utilisateur", value=f"{user.name}", inline=True)
    
    # Date de création du compte
    created_at = user.created_at.strftime("%d/%m/%Y à %H:%M:%S")
    embed.add_field(name="Compte créé le", value=created_at, inline=True)
    
    # Date d'arrivée sur le serveur
    joined_at = user.joined_at.strftime("%d/%m/%Y à %H:%M:%S") if user.joined_at else "N/A"
    embed.add_field(name="A rejoint le serveur le", value=joined_at, inline=True)
    
    # Rôles (top 10)
    roles = [role.mention for role in user.roles if role.name != "@everyone"][:10]
    roles_str = ", ".join(roles) if roles else "Aucun rôle"
    embed.add_field(name=f"Rôles ({len(roles)})", value=roles_str, inline=False)
    
    return embed

def format_duration(seconds):
    """Convertit des secondes en format lisible"""
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)
    
    parts = []
    if days > 0:
        parts.append(f"{days} jour{'s' if days > 1 else ''}")
    if hours > 0:
        parts.append(f"{hours} heure{'s' if hours > 1 else ''}")
    if minutes > 0:
        parts.append(f"{minutes} minute{'s' if minutes > 1 else ''}")
    if seconds > 0 or not parts:
        parts.append(f"{seconds} seconde{'s' if seconds > 1 else ''}")
    
    return ", ".join(parts)

async def create_rules_embed():
    """Crée un embed pour les règles du serveur"""
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
            f"• En cas de doute, contactez un modérateur via le salon dédié : <#{CHANNELS['mod_contact']}>"
        ),
        inline=False
    )
    
    embed.set_footer(
        text=f"Dernière mise à jour : {datetime.datetime.now().strftime('%d/%m/%Y')} | Bon séjour parmi nous ! 🌟"
    )
    
    return embed

async def create_welcome_embed(member):
    """Crée un embed de bienvenue pour un nouveau membre"""
    embed = discord.Embed(
        title=f"🌟 Bienvenue sur {member.guild.name} !",
        description=(
            f"Hey {member.mention}, bienvenue dans notre communauté !\n\n"
            "🎉 **Nous sommes ravis de t'accueillir parmi nous !**\n\n"
            "Pour bien commencer :\n"
            f"📜 Lis le règlement dans <#{CHANNELS['rules']}>\n"
            "🎯 Choisis tes rôles dans <#1326212401036529665>\n"
            f"💬 Présente-toi dans <#{CHANNELS['general']}>\n"
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
        value=f"<t:{int(datetime.datetime.now().timestamp())}:F>",
        inline=True
    )
    if member.avatar:
        embed.set_thumbnail(url=member.avatar.url)
    embed.set_footer(text="Nous espérons que tu te plairas parmi nous ! 🎮✨")
    
    return embed

async def create_chapter_announcement_embed(manga_name, chapter_number, chapter_link, description=None):
    """Crée un embed pour annoncer un nouveau chapitre de manga"""
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
    
    return embed

async def create_boost_embed(member):
    """Crée un embed pour annoncer un nouveau boost"""
    embed = discord.Embed(
        title="💎 Nouveau Boost !",
        description=f"Merci {member.mention} d'avoir boosté le serveur !",
        color=discord.Color.purple()
    )
    if member.avatar:
        embed.set_thumbnail(url=member.avatar.url)
    
    return embed

async def handle_command_error(ctx, error):
    """Gère les erreurs de commandes et renvoie un embed approprié"""
    if isinstance(error, commands.CommandNotFound):
        return discord.Embed(
            title="❌ Commande inconnue",
            description=f"Utilisez `{ctx.bot.command_prefix}help` pour voir la liste des commandes.",
            color=discord.Color.red()
        )
    elif isinstance(error, commands.MissingRequiredArgument):
        return discord.Embed(
            title="❌ Argument manquant",
            description=f"Il manque un argument requis. Utilisez `{ctx.bot.command_prefix}help {ctx.command.name}` pour plus d'informations.",
            color=discord.Color.red()
        )
    elif isinstance(error, commands.BadArgument):
        return discord.Embed(
            title="❌ Argument invalide",
            description="L'un des arguments fournis est invalide.",
            color=discord.Color.red()
        )
    elif isinstance(error, commands.MissingPermissions):
        return discord.Embed(
            title="❌ Permissions insuffisantes",
            description="Vous n'avez pas les permissions nécessaires pour exécuter cette commande.",
            color=discord.Color.red()
        )
    else:
        # Log l'erreur pour débogage
        logging.error(f"Erreur non gérée: {type(error).__name__}: {error}")
        return discord.Embed(
            title="❌ Erreur",
            description="Une erreur s'est produite lors de l'exécution de cette commande.",
            color=discord.Color.red()
        )

def get_manga_role(guild, manga_name):
    """Récupère le rôle associé à un manga spécifique"""
    # Définir les IDs de rôles spécifiques pour différents mangas
    manga_role_map = {
        "Catenaccio": ROLES["catenaccio"],
        "Uzugami": ROLES["uzugami"]
    }

    # Obtenir l'ID du rôle en fonction du nom du manga, ou utiliser le rôle par défaut si non spécifié
    role_id = manga_role_map.get(manga_name, ROLES["manga_default"])
    return guild.get_role(role_id)