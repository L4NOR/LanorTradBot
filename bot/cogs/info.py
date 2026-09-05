"""
Utils — /ping · /userinfo · /serverinfo · /say
================================================
Commandes utilitaires de base.
"""
import discord
from discord import app_commands
from discord.ext import commands

from bot.config import (
    GUILD_ID, CHANNELS, ROLES, COLOR_NEUTRAL, ANNOUNCE_DEFAULT_PING, SITE,
)
from bot.embeds import brand_embed


GUILD = discord.Object(id=GUILD_ID) if GUILD_ID else None


class Utils(commands.Cog):
    """Commandes utilitaires."""

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="ping", description="Latence du bot")
    @app_commands.guilds(GUILD)
    async def ping(self, interaction: discord.Interaction):
        latency = round(self.bot.latency * 1000)
        embed = discord.Embed(
            title="🏓 Pong!",
            description=f"Latence : **{latency}ms**",
            color=COLOR_NEUTRAL,
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="membre", description="Infos sur un membre")
    @app_commands.describe(member="Le membre (optionnel, par défaut toi)")
    @app_commands.guilds(GUILD)
    async def userinfo(
        self,
        interaction: discord.Interaction,
        member: discord.Member = None,
    ):
        member = member or interaction.user

        embed = discord.Embed(
            title=f"👤 {member.display_name}",
            color=member.color if member.color.value else COLOR_NEUTRAL,
            timestamp=interaction.created_at,
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="ID", value=f"`{member.id}`", inline=True)
        embed.add_field(
            name="Compte créé",
            value=f"<t:{int(member.created_at.timestamp())}:R>",
            inline=True,
        )
        if member.joined_at:
            embed.add_field(
                name="A rejoint",
                value=f"<t:{int(member.joined_at.timestamp())}:R>",
                inline=True,
            )
        roles = [r.mention for r in reversed(member.roles) if r.name != "@everyone"]
        if roles:
            value = " ".join(roles[:30])
            if len(roles) > 30:
                value += f"\n*+ {len(roles) - 30} autres*"
            embed.add_field(name=f"Rôles ({len(roles)})", value=value, inline=False)

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="serveur", description="Stats du serveur")
    @app_commands.guilds(GUILD)
    async def serverinfo(self, interaction: discord.Interaction):
        guild = interaction.guild

        text_count = len([c for c in guild.channels if isinstance(c, discord.TextChannel)])
        voice_count = len([c for c in guild.channels if isinstance(c, discord.VoiceChannel)])
        forum_count = len([c for c in guild.channels if isinstance(c, discord.ForumChannel)])

        embed = discord.Embed(
            title=f"📊 {guild.name}",
            description=guild.description or "*Aucune description.*",
            color=COLOR_NEUTRAL,
        )
        embed.add_field(name="👥 Membres", value=guild.member_count, inline=True)
        embed.add_field(name="🎭 Rôles", value=len(guild.roles), inline=True)
        embed.add_field(name="📂 Catégories", value=len(guild.categories), inline=True)
        embed.add_field(name="💬 Salons texte", value=text_count, inline=True)
        embed.add_field(name="🔊 Salons vocaux", value=voice_count, inline=True)
        embed.add_field(name="📚 Forums", value=forum_count, inline=True)
        embed.add_field(name="🚀 Boosts", value=guild.premium_subscription_count, inline=True)
        embed.add_field(name="💎 Niveau boost", value=f"Niveau {guild.premium_tier}", inline=True)
        embed.add_field(
            name="📅 Créé",
            value=f"<t:{int(guild.created_at.timestamp())}:R>",
            inline=True,
        )
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
        if guild.banner:
            embed.set_image(url=guild.banner.url)

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="dis", description="(Admin) Fait parler le bot")
    @app_commands.describe(
        message="Le texte à dire",
        channel="Le salon où poster (optionnel, par défaut ici)",
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.guilds(GUILD)
    async def say(
        self,
        interaction: discord.Interaction,
        message: str,
        channel: discord.TextChannel = None,
    ):
        target = channel or interaction.channel
        try:
            await target.send(message)
            await interaction.response.send_message(
                f"✅ Message posté dans {target.mention}",
                ephemeral=True,
            )
        except discord.Forbidden:
            await interaction.response.send_message(
                f"❌ Permissions insuffisantes pour {target.mention}.",
                ephemeral=True,
            )

    @app_commands.command(name="annonce", description="(Mod) Poste une annonce stylée")
    @app_commands.describe(
        title="Titre de l'annonce",
        message="Contenu (utilise \\n pour des retours à la ligne)",
        channel="Salon cible (défaut: #announcements ou ici)",
        ping="Rôle à mentionner (défaut : le rôle 📢 Announcements)",
        sans_ping="True = ne mentionne personne",
        image="URL d'une image à afficher (optionnel)",
    )
    @app_commands.default_permissions(manage_messages=True)
    @app_commands.guilds(GUILD)
    async def announce(
        self,
        interaction: discord.Interaction,
        title: str,
        message: str,
        channel: discord.TextChannel = None,
        ping: discord.Role = None,
        sans_ping: bool = False,
        image: str = None,
    ):
        # Cible : param explicite > #announcements configuré > salon courant
        target = channel
        if target is None:
            ann_id = CHANNELS.get("announcements")
            target = interaction.guild.get_channel(ann_id) if ann_id else None
        target = target or interaction.channel

        # Ping : param explicite > rôle d'annonces configuré > rien
        if sans_ping:
            mention = None
        elif ping is not None:
            mention = ping.mention
        else:
            role_id = ROLES.get(ANNOUNCE_DEFAULT_PING) if ANNOUNCE_DEFAULT_PING else None
            mention = f"<@&{role_id}>" if role_id else None

        embed = brand_embed(
            interaction.guild,
            title=f"📢 {title}",
            description=message.replace("\\n", "\n"),
            color=COLOR_NEUTRAL,
        )
        if image:
            embed.set_image(url=image)
        embed.set_author(name=interaction.user.display_name,
                         icon_url=interaction.user.display_avatar.url)

        try:
            sent = await target.send(
                content=mention,
                embed=embed,
                allowed_mentions=discord.AllowedMentions(roles=bool(mention)),
            )
        except discord.Forbidden:
            await interaction.response.send_message(
                f"❌ Permissions insuffisantes pour {target.mention}.", ephemeral=True)
            return
        except discord.HTTPException:
            await interaction.response.send_message(
                "❌ Discord a refusé l'envoi (URL d'image invalide ?).", ephemeral=True)
            return

        # Salon d'annonces Discord : on publie vers les serveurs abonnés
        published = ""
        if isinstance(target, discord.TextChannel) and target.is_news():
            try:
                await sent.publish()
                published = " et publiée aux serveurs abonnés"
            except discord.HTTPException:
                pass

        await interaction.response.send_message(
            f"✅ Annonce postée dans {target.mention}{published}.", ephemeral=True)

    @app_commands.command(name="site", description="Tous les liens LanorTrad")
    @app_commands.guilds(GUILD)
    async def site(self, interaction: discord.Interaction):
        embed = brand_embed(
            interaction.guild,
            title="🌐 Le site LanorTrad",
            description=(
                f"**[📚 Catalogue]({SITE['catalogue']})** — toutes les séries\n"
                f"**[📅 Planning]({SITE['planning']})** — le rythme de parution\n"
                f"**[💬 Forum]({SITE['forum']})** — c'est là qu'on discute\n"
                f"**[👥 L'équipe]({SITE['equipe']})** — qui fait quoi"
            ),
            color=COLOR_NEUTRAL,
        )
        embed.set_footer(text="Tout est gratuit. Toujours.")
        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(Utils(bot))
