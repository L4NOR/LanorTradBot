# role_selector.py
# Système de sélection de rôles MODERNE pour remplacer DraftBot
import discord
from discord.ext import commands
from discord.ui import Button, View, Select
import asyncio
from typing import Optional

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION DES RÔLES PAR CATÉGORIE
# ═══════════════════════════════════════════════════════════════════════════════

ROLE_CATEGORIES = {
    "manga": {
        "title": "📚 MANGAS",
        "description": "Recevez des notifications pour vos mangas préférés !",
        "color": 0x3498DB,  # Bleu
        "emoji": "📚",
        "parent_role_id": 1465027922833440833,  # Rôle parent "manga"
        "roles": [
            {"name": "Ao No Exorcist", "emoji": "🔥", "id": 1465027919951958220},
            {"name": "Satsudou", "emoji": "⚔️", "id": 1465027916999032976},
            {"name": "Tokyo Underworld", "emoji": "🏙️", "id": 1465027914050437184},
            {"name": "Tougen Anki", "emoji": "👹", "id": 1465027911235928155},
            {"name": "Catenaccio", "emoji": "⚽", "id": 1465027907968831541},
        ]
    },
    "notifications": {
        "title": "🔔 NOTIFICATIONS",
        "description": "Choisissez les notifications que vous souhaitez recevoir",
        "color": 0xE67E22,  # Orange
        "emoji": "🔔",
        "parent_role_id": 1465027873751433520,  # Rôle parent "notifications"
        "roles": [
            {"name": "Annonces", "emoji": "📢", "id": 1465027871339708439},
            {"name": "Événements", "emoji": "🎉", "id": 1465027869196423239},
            {"name": "Giveaway", "emoji": "🎁", "id": 1465027866826772785},
            {"name": "Partenaires", "emoji": "💛", "id": 1465027864318447658},
            {"name": "Twittos", "emoji": "🐦", "id": 1465027861365919756},
            {"name": "Tiktok", "emoji": "🎵", "id": 1465027858853527644},
            {"name": "Spoilers", "emoji": "👀", "id": 1465027856508649543},
        ]
    },
    "community": {
        "title": "🎨 COMMUNAUTÉ",
        "description": "Partagez vos passions avec la communauté !",
        "color": 0x2ECC71,  # Vert
        "emoji": "🎨",
        "parent_role_id": 1465027902419636296,  # Rôle parent "communauté"
        "roles": [
            {"name": "Artiste", "emoji": "🎨", "id": 1465027899466846260},
            {"name": "Collectionneurs", "emoji": "📚", "id": 1465027897336004638},
            {"name": "Musique", "emoji": "🎧", "id": 1465027894668689642},
            {"name": "Photographie", "emoji": "📷", "id": 1465027891942129714},
            {"name": "Jeux vidéo", "emoji": "🎮", "id": 1465027882253287607},
        ]
    }
}

# ═══════════════════════════════════════════════════════════════════════════════
# COMPOSANTS UI
# ═══════════════════════════════════════════════════════════════════════════════

class RoleButton(Button):
    """Bouton pour toggle un rôle individuel"""
    
    def __init__(self, role_name: str, emoji: str, category_key: str, parent_role_id: int):
        super().__init__(
            style=discord.ButtonStyle.secondary,
            label=role_name,
            emoji=emoji,
            custom_id=f"role_btn_{role_name}"
        )
        self.role_name = role_name
        self.category_key = category_key
        self.parent_role_id = parent_role_id
    
    async def callback(self, interaction: discord.Interaction):
        """Toggle le rôle quand le bouton est cliqué"""
        # Defer pour éviter le timeout
        await interaction.response.defer(ephemeral=True)
        
        role = discord.utils.get(interaction.guild.roles, name=self.role_name)
        
        if not role:
            await interaction.followup.send(
                f"❌ Le rôle **{self.role_name}** n'existe pas. Contactez un administrateur.",
                ephemeral=True
            )
            return
        
        member = interaction.user
        parent_role = interaction.guild.get_role(self.parent_role_id)
        
        try:
            if role in member.roles:
                # Retirer le rôle
                await member.remove_roles(role)
                
                # Vérifier si l'utilisateur a encore d'autres rôles de cette catégorie
                category_data = ROLE_CATEGORIES[self.category_key]
                has_other_roles = False
                for role_info in category_data["roles"]:
                    other_role = discord.utils.get(interaction.guild.roles, name=role_info["name"])
                    if other_role and other_role in member.roles and other_role != role:
                        has_other_roles = True
                        break
                
                # Si plus aucun rôle de cette catégorie, retirer le rôle parent
                if not has_other_roles and parent_role and parent_role in member.roles:
                    await member.remove_roles(parent_role)
                
                await interaction.followup.send(
                    f"✅ Le rôle **{role.name}** vous a été retiré !",
                    ephemeral=True
                )
            else:
                # Ajouter le rôle
                await member.add_roles(role)
                
                # Ajouter automatiquement le rôle parent si pas déjà présent
                if parent_role and parent_role not in member.roles:
                    await member.add_roles(parent_role)
                
                await interaction.followup.send(
                    f"✅ Vous avez reçu le rôle **{role.name}** !",
                    ephemeral=True
                )
        except discord.Forbidden:
            await interaction.followup.send(
                "❌ Je n'ai pas la permission de gérer ce rôle.",
                ephemeral=True
            )
        except Exception as e:
            print(f"❌ Erreur dans RoleButton callback: {e}")
            try:
                await interaction.followup.send(
                    f"❌ Une erreur s'est produite: {str(e)}",
                    ephemeral=True
                )
            except:
                pass


class RoleSelect(Select):
    """Menu déroulant pour sélectionner plusieurs rôles"""
    
    def __init__(self, category_key: str, category_data: dict):
        options = []
        
        for role_info in category_data["roles"]:
            options.append(
                discord.SelectOption(
                    label=role_info["name"],
                    value=role_info["name"],
                    emoji=role_info["emoji"],
                    description=f"Toggle le rôle {role_info['name']}"
                )
            )
        
        super().__init__(
            placeholder="🎯 Sélectionnez vos rôles...",
            min_values=0,
            max_values=len(options),
            options=options,
            custom_id=f"select_{category_key}"
        )
        
        self.category_key = category_key
        self.category_data = category_data
    
    async def callback(self, interaction: discord.Interaction):
        """Gère la sélection multiple de rôles avec attribution automatique du rôle parent"""
        # IMPORTANT: Defer immédiatement pour éviter le timeout de 3 secondes
        await interaction.response.defer(ephemeral=True)
        
        member = interaction.user
        
        # Récupérer tous les rôles de cette catégorie
        category_role_names = [r["name"] for r in self.category_data["roles"]]
        category_roles = [discord.utils.get(interaction.guild.roles, name=name) 
                         for name in category_role_names]
        category_roles = [r for r in category_roles if r]  # Filtrer les None
        
        # Récupérer le rôle parent
        parent_role_id = self.category_data.get("parent_role_id")
        parent_role = interaction.guild.get_role(parent_role_id) if parent_role_id else None
        
        # Rôles à ajouter/retirer
        to_add = []
        to_remove = []
        
        for role in category_roles:
            if role.name in self.values:
                if role not in member.roles:
                    to_add.append(role)
            else:
                if role in member.roles:
                    to_remove.append(role)
        
        try:
            if to_add:
                await member.add_roles(*to_add)
            if to_remove:
                await member.remove_roles(*to_remove)
            
            # Gestion du rôle parent
            if parent_role:
                # Vérifier si l'utilisateur a au moins un rôle de cette catégorie après les modifications
                has_category_role = False
                for role in category_roles:
                    if role in member.roles or role in to_add:
                        if role not in to_remove:
                            has_category_role = True
                            break
                
                if has_category_role:
                    # Ajouter le rôle parent si l'utilisateur a au moins un rôle de cette catégorie
                    if parent_role not in member.roles:
                        await member.add_roles(parent_role)
                else:
                    # Retirer le rôle parent si l'utilisateur n'a plus aucun rôle de cette catégorie
                    if parent_role in member.roles:
                        await member.remove_roles(parent_role)
            
            # Message de confirmation
            added = [r.name for r in to_add]
            removed = [r.name for r in to_remove]
            
            msg_parts = []
            if added:
                msg_parts.append(f"**Ajoutés:** {', '.join(added)}")
            if removed:
                msg_parts.append(f"**Retirés:** {', '.join(removed)}")
            
            if msg_parts:
                await interaction.followup.send(
                    "✅ Rôles mis à jour !\n" + "\n".join(msg_parts),
                    ephemeral=True
                )
            else:
                await interaction.followup.send(
                    "ℹ️ Aucun changement détecté.",
                    ephemeral=True
                )
        
        except discord.Forbidden:
            await interaction.followup.send(
                "❌ Je n'ai pas la permission de gérer ces rôles.",
                ephemeral=True
            )
        except Exception as e:
            # Gestion d'erreur générique pour éviter les crashs silencieux
            print(f"❌ Erreur dans RoleSelect callback: {e}")
            try:
                await interaction.followup.send(
                    f"❌ Une erreur s'est produite: {str(e)}",
                    ephemeral=True
                )
            except:
                pass


class MyRolesButton(Button):
    """Bouton pour voir ses rôles actuels"""
    
    def __init__(self):
        super().__init__(
            style=discord.ButtonStyle.primary,
            label="Mes Rôles",
            emoji="📋",
            custom_id="my_roles_btn"
        )
    
    async def callback(self, interaction: discord.Interaction):
        """Affiche les rôles auto-assignables de l'utilisateur"""
        # Defer pour éviter tout timeout potentiel
        await interaction.response.defer(ephemeral=True)
        
        member = interaction.user
        
        # Collecter tous les rôles auto-assignables
        auto_assignable_roles = set()
        for category_data in ROLE_CATEGORIES.values():
            for role_info in category_data["roles"]:
                auto_assignable_roles.add(role_info["name"])
        
        # Trouver les rôles de l'utilisateur qui sont auto-assignables
        user_auto_roles = {}
        for category_key, category_data in ROLE_CATEGORIES.items():
            category_roles = []
            for role_info in category_data["roles"]:
                role = discord.utils.get(member.roles, name=role_info["name"])
                if role:
                    category_roles.append(f"{role_info['emoji']} {role.name}")
            
            if category_roles:
                user_auto_roles[category_key] = category_roles
        
        # Créer l'embed
        embed = discord.Embed(
            title="📋 Vos Rôles",
            color=discord.Color.blue()
        )
        
        if user_auto_roles:
            for category_key, roles in user_auto_roles.items():
                category_data = ROLE_CATEGORIES[category_key]
                embed.add_field(
                    name=f"{category_data['emoji']} {category_data['title']}",
                    value="\n".join(roles),
                    inline=False
                )
        else:
            embed.description = "Vous n'avez aucun rôle auto-assignable pour le moment."
        
        await interaction.followup.send(embed=embed, ephemeral=True)


class RoleSelectView(View):
    """Vue contenant un menu déroulant"""
    
    def __init__(self, category_key: str, category_data: dict):
        super().__init__(timeout=None)
        self.add_item(RoleSelect(category_key, category_data))


class MyRolesView(View):
    """Vue contenant le bouton Mes Rôles"""
    
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(MyRolesButton())


# ═══════════════════════════════════════════════════════════════════════════════
# COG PRINCIPAL
# ═══════════════════════════════════════════════════════════════════════════════

class RoleSelector(commands.Cog):
    """Système de sélection de rôles moderne"""
    
    def __init__(self, bot):
        self.bot = bot
    
    async def cog_load(self):
        """Charge les vues persistantes"""
        for category_key in ROLE_CATEGORIES.keys():
            self.bot.add_view(RoleSelectView(category_key, ROLE_CATEGORIES[category_key]))
        
        self.bot.add_view(MyRolesView())
        print("✅ Vues persistantes chargées")
    
    @commands.command(name="setup_roles")
    @commands.has_permissions(administrator=True)
    async def setup_roles(self, ctx, channel: Optional[discord.TextChannel] = None):
        """
        Configure le système de rôles dans un salon
        
        Usage: !setup_roles [#channel]
        Si aucun channel n'est spécifié, utilise le channel actuel
        """
        target_channel = channel or ctx.channel
        
        # Confirmation
        confirm_embed = discord.Embed(
            title="⚠️ CONFIRMATION",
            description=(
                f"Cette commande va poster le système de rôles dans {target_channel.mention}.\n\n"
                "Voulez-vous continuer ?"
            ),
            color=discord.Color.orange()
        )
        
        confirm_msg = await ctx.send(embed=confirm_embed)
        await confirm_msg.add_reaction("✅")
        await confirm_msg.add_reaction("❌")
        
        def check(reaction, user):
            return (user == ctx.author and 
                   str(reaction.emoji) in ["✅", "❌"] and 
                   reaction.message.id == confirm_msg.id)
        
        try:
            reaction, _ = await self.bot.wait_for("reaction_add", timeout=30.0, check=check)
            await confirm_msg.delete()
            
            if str(reaction.emoji) == "❌":
                await ctx.send("❌ Opération annulée.")
                return
            
            # Message d'introduction
            intro_embed = discord.Embed(
                title="🎭 SÉLECTION DE RÔLES",
                description=(
                    "Bienvenue dans le système de sélection de rôles !\n\n"
                    "Utilisez les menus déroulants ci-dessous pour choisir vos rôles.\n"
                    "Vous pouvez sélectionner plusieurs rôles à la fois dans chaque catégorie.\n\n"
                    "**Comment ça marche ?**\n"
                    "• Cliquez sur un menu déroulant\n"
                    "• Sélectionnez les rôles que vous voulez\n"
                    "• Les rôles non sélectionnés seront automatiquement retirés\n\n"
                    "Utilisez le bouton **Mes Rôles** pour voir vos rôles actuels !"
                ),
                color=discord.Color.purple()
            )
            intro_embed.set_footer(text="✨ Système de rôles by LanorTrad")
            
            await target_channel.send(embed=intro_embed)
            
            # Créer un embed et menu pour chaque catégorie
            message_links = []
            
            for category_key, category_data in ROLE_CATEGORIES.items():
                # Créer l'embed
                embed = discord.Embed(
                    title=category_data["title"],
                    description=category_data["description"],
                    color=category_data["color"]
                )
                
                # Lister les rôles disponibles
                roles_text = []
                for role_info in category_data["roles"]:
                    roles_text.append(f"{role_info['emoji']} **{role_info['name']}**")
                
                embed.add_field(
                    name="Rôles disponibles",
                    value="\n".join(roles_text),
                    inline=False
                )
                
                # Créer la vue avec le menu déroulant
                view = RoleSelectView(category_key, category_data)
                
                # Envoyer le message
                msg = await target_channel.send(embed=embed, view=view)
                message_links.append(msg.jump_url)
                
                # Petit délai pour éviter le rate limit
                await asyncio.sleep(0.5)
            
            # Footer avec le bouton Mes Rôles
            footer_embed = discord.Embed(
                title="",
                description="Cliquez sur le bouton ci-dessous pour voir vos rôles actuels",
                color=discord.Color.blue()
            )
            
            view = MyRolesView()
            footer_msg = await target_channel.send(embed=footer_embed, view=view)
            message_links.append(footer_msg.jump_url)
            
            # Message de succès
            success_embed = discord.Embed(
                title="✅ Système de Rôles Configuré",
                description=f"Le système a été posté dans {target_channel.mention} avec succès !",
                color=discord.Color.green()
            )
            
            success_embed.add_field(
                name="📎 Liens des messages",
                value="\n".join([f"[Message {i+1}]({link})" for i, link in enumerate(message_links)]),
                inline=False
            )
            
            await ctx.send(embed=success_embed)
        
        except asyncio.TimeoutError:
            await confirm_msg.delete()
            await ctx.send("⏰ Temps écoulé. Opération annulée.")
    
    @commands.command(name="sync_roles")
    @commands.has_permissions(administrator=True)
    async def sync_roles(self, ctx):
        """
        Vérifie et crée les rôles manquants
        
        Cette commande vérifie si tous les rôles définis dans la configuration
        existent sur le serveur et propose de créer ceux qui manquent.
        """
        missing_roles = []
        existing_roles = []
        
        # Vérifier tous les rôles
        for category_data in ROLE_CATEGORIES.values():
            for role_info in category_data["roles"]:
                role = discord.utils.get(ctx.guild.roles, name=role_info["name"])
                if role:
                    existing_roles.append(role_info["name"])
                else:
                    missing_roles.append(role_info)
        
        # Créer l'embed de rapport
        report_embed = discord.Embed(
            title="📊 Rapport de Synchronisation",
            color=discord.Color.blue()
        )
        
        report_embed.add_field(
            name=f"✅ Rôles existants ({len(existing_roles)})",
            value="\n".join(existing_roles) if existing_roles else "Aucun",
            inline=False
        )
        
        if missing_roles:
            missing_text = "\n".join([f"{r['emoji']} {r['name']}" for r in missing_roles])
            report_embed.add_field(
                name=f"❌ Rôles manquants ({len(missing_roles)})",
                value=missing_text,
                inline=False
            )
            
            report_embed.set_footer(text="Réagissez avec ✅ pour créer les rôles manquants")
        else:
            report_embed.description = "🎉 Tous les rôles existent déjà !"
        
        report_msg = await ctx.send(embed=report_embed)
        
        if not missing_roles:
            return
        
        # Demander confirmation pour créer
        await report_msg.add_reaction("✅")
        await report_msg.add_reaction("❌")
        
        def check(reaction, user):
            return (user == ctx.author and 
                   str(reaction.emoji) in ["✅", "❌"] and 
                   reaction.message.id == report_msg.id)
        
        try:
            reaction, _ = await self.bot.wait_for("reaction_add", timeout=30.0, check=check)
            await report_msg.clear_reactions()
            
            if str(reaction.emoji) == "❌":
                await ctx.send("❌ Création annulée.")
                return
            
            # Créer les rôles manquants
            created = []
            failed = []
            
            progress_msg = await ctx.send("⏳ Création des rôles en cours...")
            
            for role_info in missing_roles:
                try:
                    new_role = await ctx.guild.create_role(
                        name=role_info["name"],
                        mentionable=True,
                        reason="Synchronisation du système de rôles"
                    )
                    created.append(f"✅ {role_info['emoji']} {new_role.mention}")
                    await asyncio.sleep(0.5)  # Rate limit protection
                except Exception as e:
                    failed.append(f"❌ {role_info['name']}: {str(e)}")
            
            await progress_msg.delete()
            
            # Rapport final
            final_embed = discord.Embed(
                title="✅ Synchronisation Terminée",
                color=discord.Color.green()
            )
            
            if created:
                final_embed.add_field(
                    name=f"Rôles créés ({len(created)})",
                    value="\n".join(created),
                    inline=False
                )
            
            if failed:
                final_embed.add_field(
                    name=f"Échecs ({len(failed)})",
                    value="\n".join(failed),
                    inline=False
                )
                final_embed.color = discord.Color.orange()
            
            await ctx.send(embed=final_embed)
        
        except asyncio.TimeoutError:
            await report_msg.clear_reactions()
            await ctx.send("⏰ Temps écoulé. Opération annulée.")
    
    @commands.command(name="roles_stats")
    @commands.has_permissions(administrator=True)
    async def roles_stats(self, ctx):
        """Affiche les statistiques d'attribution des rôles"""
        embed = discord.Embed(
            title="📊 Statistiques des Rôles",
            description="Nombre de membres par rôle",
            color=discord.Color.blue()
        )
        
        total_members = ctx.guild.member_count
        
        for category_key, category_data in ROLE_CATEGORIES.items():
            stats_text = []
            
            for role_info in category_data["roles"]:
                role = discord.utils.get(ctx.guild.roles, name=role_info["name"])
                if role:
                    count = len(role.members)
                    percentage = (count / total_members * 100) if total_members > 0 else 0
                    stats_text.append(
                        f"{role_info['emoji']} **{role.name}**: {count} ({percentage:.1f}%)"
                    )
                else:
                    stats_text.append(f"{role_info['emoji']} **{role_info['name']}**: ❌ N'existe pas")
            
            embed.add_field(
                name=f"{category_data['emoji']} {category_data['title']}",
                value="\n".join(stats_text),
                inline=False
            )
        
        embed.set_footer(text=f"Total: {total_members} membres")
        
        await ctx.send(embed=embed)


async def setup(bot):
    """Setup pour discord.py 2.0+"""
    await bot.add_cog(RoleSelector(bot))
    print("✅ Cog RoleSelector chargé avec succès")