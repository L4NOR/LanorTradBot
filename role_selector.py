# role_selector.py
# ═══════════════════════════════════════════════════════════════════════════════
# SYSTÈME DE SÉLECTION DE RÔLES AVEC UI MODERNE
# ═══════════════════════════════════════════════════════════════════════════════

import discord
from discord.ext import commands
from discord.ui import Button, View, Select
import asyncio
from typing import Optional
from config import ADMIN_ROLES, ROLE_CATEGORIES


class RoleButton(Button):
    """Bouton pour toggle un rôle individuel."""
    
    def __init__(self, role_name: str, emoji: str, role_id: int, category_key: str, parent_role_id: int):
        super().__init__(
            style=discord.ButtonStyle.secondary,
            label=role_name,
            emoji=emoji,
            custom_id=f"role_btn_{role_id}"
        )
        self.role_name = role_name
        self.role_id = role_id
        self.category_key = category_key
        self.parent_role_id = parent_role_id
    
    async def callback(self, interaction: discord.Interaction):
        """Toggle le rôle quand le bouton est cliqué."""
        await interaction.response.defer(ephemeral=True)
        
        role = interaction.guild.get_role(self.role_id)
        
        if not role:
            await interaction.followup.send(
                f"❌ Le rôle **{self.role_name}** n'existe pas (ID: {self.role_id}). Contactez un administrateur.",
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
                    other_role = interaction.guild.get_role(role_info["id"])
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
            await interaction.followup.send(
                f"❌ Une erreur s'est produite: {str(e)}",
                ephemeral=True
            )


class RoleSelect(Select):
    """Menu déroulant pour sélectionner plusieurs rôles."""
    
    def __init__(self, category_key: str, category_data: dict):
        options = []
        
        for role_info in category_data["roles"]:
            if role_info.get("coming_soon"):
                continue
            options.append(
                discord.SelectOption(
                    label=role_info["name"],
                    value=str(role_info["id"]),
                    emoji=role_info["emoji"],
                    description=f"Toggle le rôle {role_info['name']}"
                )
            )
        
        super().__init__(
            placeholder="⚠️ Resélectionnez TOUS vos rôles souhaités (sinon perdus)",
            min_values=0,
            max_values=len(options),
            options=options,
            custom_id=f"select_{category_key}"
        )
        
        self.category_key = category_key
        self.category_data = category_data
    
    async def callback(self, interaction: discord.Interaction):
        """Gère la sélection multiple de rôles."""
        await interaction.response.defer(ephemeral=True)
        
        member = interaction.user
        
        # Créer un dict ID -> role object pour tous les rôles de cette catégorie
        category_roles_by_id = {}
        for role_info in self.category_data["roles"]:
            role = interaction.guild.get_role(role_info["id"])
            if role:
                category_roles_by_id[str(role_info["id"])] = role
        
        # Rôles sélectionnés (IDs)
        selected_ids = set(self.values)
        
        # Rôles actuels de l'utilisateur dans cette catégorie
        current_roles = set()
        for role_id, role in category_roles_by_id.items():
            if role in member.roles:
                current_roles.add(role_id)
        
        # Calculer les différences
        roles_to_add = selected_ids - current_roles
        roles_to_remove = current_roles - selected_ids
        
        added = []
        removed = []
        
        try:
            # Ajouter les nouveaux rôles en un seul appel API (au lieu d'un par rôle)
            roles_add_objects = [category_roles_by_id[rid] for rid in roles_to_add if rid in category_roles_by_id]
            if roles_add_objects:
                await member.add_roles(*roles_add_objects)
                added = [r.name for r in roles_add_objects]

            # Retirer les rôles non sélectionnés en un seul appel API
            roles_remove_objects = [category_roles_by_id[rid] for rid in roles_to_remove if rid in category_roles_by_id]
            if roles_remove_objects:
                if roles_add_objects:
                    await asyncio.sleep(0.5)  # Petit délai entre add et remove
                await member.remove_roles(*roles_remove_objects)
                removed = [r.name for r in roles_remove_objects]
            
            # Gérer le rôle parent
            parent_role = interaction.guild.get_role(self.category_data["parent_role_id"])
            if parent_role:
                has_roles_in_category = len(selected_ids) > 0
                
                if has_roles_in_category and parent_role not in member.roles:
                    await member.add_roles(parent_role)
                elif not has_roles_in_category and parent_role in member.roles:
                    await member.remove_roles(parent_role)
            
            # Construire le message de confirmation
            messages = []
            if added:
                messages.append(f"✅ Ajoutés: **{', '.join(added)}**")
            if removed:
                messages.append(f"❌ Retirés: **{', '.join(removed)}**")
            
            if messages:
                await interaction.followup.send("\n".join(messages), ephemeral=True)
            else:
                await interaction.followup.send("ℹ️ Aucun changement effectué.", ephemeral=True)
        
        except discord.Forbidden:
            await interaction.followup.send(
                "❌ Je n'ai pas la permission de gérer ces rôles.",
                ephemeral=True
            )
        except Exception as e:
            await interaction.followup.send(
                f"❌ Une erreur s'est produite: {str(e)}",
                ephemeral=True
            )


class RoleSelectView(View):
    """Vue contenant le menu déroulant de sélection de rôles."""
    
    def __init__(self, category_key: str, category_data: dict):
        super().__init__(timeout=None)
        self.add_item(RoleSelect(category_key, category_data))


class MyRolesButton(Button):
    """Bouton pour afficher ses rôles actuels."""
    
    def __init__(self):
        super().__init__(
            style=discord.ButtonStyle.primary,
            label="Mes Rôles",
            emoji="📋",
            custom_id="my_roles_button"
        )
    
    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        member = interaction.user
        
        embed = discord.Embed(
            title=f"📋 Rôles de {member.display_name}",
            color=member.color if member.color != discord.Color.default() else discord.Color.blue()
        )
        
        for category_key, category_data in ROLE_CATEGORIES.items():
            user_roles_in_category = []
            
            for role_info in category_data["roles"]:
                role = interaction.guild.get_role(role_info["id"])
                if role and role in member.roles:
                    user_roles_in_category.append(f"{role_info['emoji']} {role.name}")
            
            if user_roles_in_category:
                embed.add_field(
                    name=f"{category_data['emoji']} {category_data['title']}",
                    value="\n".join(user_roles_in_category),
                    inline=False
                )
        
        if not embed.fields:
            embed.description = "Vous n'avez sélectionné aucun rôle pour le moment."
        
        embed.set_thumbnail(url=member.avatar.url if member.avatar else None)
        await interaction.followup.send(embed=embed, ephemeral=True)


class MyRolesView(View):
    """Vue avec le bouton Mes Rôles."""
    
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(MyRolesButton())


class RoleSelector(commands.Cog):
    """Système de sélection de rôles avec interface moderne."""
    
    def __init__(self, bot):
        self.bot = bot
        
        # Enregistrer les vues persistantes
        for category_key, category_data in ROLE_CATEGORIES.items():
            bot.add_view(RoleSelectView(category_key, category_data))
        bot.add_view(MyRolesView())
    
    @commands.command(name="setup_roles")
    @commands.has_permissions(administrator=True)
    async def setup_roles(self, ctx, channel: Optional[discord.TextChannel] = None):
        """Configure le système de sélection de rôles dans un canal."""
        target_channel = channel or ctx.channel
        
        # Confirmation
        confirm_embed = discord.Embed(
            title="⚙️ Configuration du Système de Rôles",
            description=f"Cela va poster le système de sélection de rôles dans {target_channel.mention}.\n\n"
                       "Réagissez avec ✅ pour confirmer ou ❌ pour annuler.",
            color=discord.Color.gold()
        )
        confirm_msg = await ctx.send(embed=confirm_embed)
        await confirm_msg.add_reaction('✅')
        await confirm_msg.add_reaction('❌')
        
        def check(reaction, user):
            return user == ctx.author and str(reaction.emoji) in ['✅', '❌'] and reaction.message.id == confirm_msg.id
        
        try:
            reaction, user = await self.bot.wait_for('reaction_add', timeout=30.0, check=check)
            
            await confirm_msg.delete()
            
            if str(reaction.emoji) == '❌':
                await ctx.send("❌ Opération annulée.")
                return
            
            message_links = []
            
            # Poster chaque catégorie
            for category_key, category_data in ROLE_CATEGORIES.items():
                embed = discord.Embed(
                    title=category_data['title'],
                    description=category_data['description'],
                    color=category_data['color']
                )
                
                # Lister les rôles disponibles
                roles_text = []
                for role_info in category_data["roles"]:
                    role = ctx.guild.get_role(role_info["id"])
                    if role_info.get("coming_soon"):
                        roles_text.append(f"{role_info['emoji']} **{role_info['name']}** 🔒 *(bientôt disponible)*")
                    elif role:
                        roles_text.append(f"{role_info['emoji']} **{role_info['name']}**")
                    else:
                        roles_text.append(f"{role_info['emoji']} ~~{role_info['name']}~~ (Non trouvé)")
                
                embed.add_field(
                    name="Rôles disponibles",
                    value="\n".join(roles_text),
                    inline=False
                )

                embed.add_field(
                    name="⚠️ Important",
                    value=(
                        "Le menu remplace **toute ta sélection** de cette catégorie à chaque validation.\n"
                        "Pour ajouter un nouveau rôle **sans perdre les autres**, "
                        "resélectionne aussi tous ceux que tu as déjà.\n"
                        "Si tu ne coches que le nouveau, les anciens rôles de cette catégorie seront retirés."
                    ),
                    inline=False
                )

                # Créer la vue avec le menu déroulant
                view = RoleSelectView(category_key, category_data)
                
                # Envoyer le message
                msg = await target_channel.send(embed=embed, view=view)
                message_links.append(msg.jump_url)
                
                await asyncio.sleep(1.5)
            
            # Footer avec le bouton Mes Rôles
            footer_embed = discord.Embed(
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
        """Vérifie et liste les rôles manquants."""
        missing_roles = []
        existing_roles = []
        
        for category_data in ROLE_CATEGORIES.values():
            for role_info in category_data["roles"]:
                role = ctx.guild.get_role(role_info["id"])
                if role:
                    existing_roles.append(f"{role_info['emoji']} {role.name} (ID: {role_info['id']})")
                else:
                    missing_roles.append(role_info)
        
        report_embed = discord.Embed(
            title="📊 Rapport de Synchronisation",
            color=discord.Color.blue()
        )
        
        report_embed.add_field(
            name=f"✅ Rôles existants ({len(existing_roles)})",
            value="\n".join(existing_roles[:10]) + (f"\n*...et {len(existing_roles) - 10} autres*" if len(existing_roles) > 10 else "") if existing_roles else "Aucun",
            inline=False
        )
        
        if missing_roles:
            missing_text = "\n".join([f"{r['emoji']} {r['name']} (ID attendu: {r['id']})" for r in missing_roles])
            report_embed.add_field(
                name=f"❌ Rôles manquants ({len(missing_roles)})",
                value=missing_text,
                inline=False
            )
            report_embed.description = "⚠️ Les IDs sont définis dans config.py. Mettez à jour la configuration si nécessaire."
        else:
            report_embed.description = "🎉 Tous les rôles existent !"
        
        await ctx.send(embed=report_embed)
    
    @commands.command(name="roles_stats")
    @commands.has_permissions(administrator=True)
    async def roles_stats(self, ctx):
        """Affiche les statistiques d'attribution des rôles."""
        embed = discord.Embed(
            title="📊 Statistiques des Rôles",
            description="Nombre de membres par rôle",
            color=discord.Color.blue()
        )
        
        total_members = ctx.guild.member_count
        
        for category_key, category_data in ROLE_CATEGORIES.items():
            stats_text = []
            
            for role_info in category_data["roles"]:
                role = ctx.guild.get_role(role_info["id"])
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
    """Setup pour discord.py 2.0+."""
    await bot.add_cog(RoleSelector(bot))
