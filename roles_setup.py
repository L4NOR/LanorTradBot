# roles_setup.py
# Commande pour restructurer les rôles du serveur Discord LanorTrad
import discord
from discord.ext import commands
import asyncio
from datetime import datetime
import logging

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION DES RÔLES - Structure complète
# ═══════════════════════════════════════════════════════════════════════════════

# Format: Liste de catégories, chaque catégorie contient:
# - "category": nom de la catégorie (pour affichage)
# - "separator": nom du rôle séparateur (optionnel)
# - "color": couleur hex de la catégorie
# - "roles": liste des rôles avec name, hoist, mentionable

ROLES_STRUCTURE = [
    # ─────────────────────────────────────────────────────────────────────────
    # DIRECTION - Fondateurs et direction
    # ─────────────────────────────────────────────────────────────────────────
    {
        "category": "DIRECTION",
        "separator": "════════ DIRECTION ════════",
        "color": 0x5BB85B,
        "roles": [
            {"name": "Maître des Origines", "hoist": True, "mentionable": False},
            {"name": "Règne Absolu", "hoist": True, "mentionable": False},
            {"name": "Vénérable", "hoist": True, "mentionable": False},
        ]
    },
    
    # ─────────────────────────────────────────────────────────────────────────
    # BOT - Bots du serveur
    # ─────────────────────────────────────────────────────────────────────────
    {
        "category": "BOT",
        "separator": "════════ BOT ════════",
        "color": 0x5BB85B,
        "roles": [
            {"name": "DoubleM", "hoist": False, "mentionable": False},
            {"name": "Nadeko", "hoist": False, "mentionable": False},
            {"name": "MEE6", "hoist": False, "mentionable": False},
        ]
    },
    
    # ─────────────────────────────────────────────────────────────────────────
    # STAFF - Équipe de modération
    # ─────────────────────────────────────────────────────────────────────────
    {
        "category": "STAFF",
        "separator": "════════ STAFF ════════",
        "color": 0x698B88,
        "roles": [
            {"name": "Gardiens de l'Ombre", "hoist": True, "mentionable": False},
            {"name": "Staff - membre", "hoist": True, "mentionable": True},
            {"name": "Goûteur", "hoist": True, "mentionable": False},
        ]
    },
    
    # ─────────────────────────────────────────────────────────────────────────
    # ÉQUIPE SCANTRAD - Équipe de traduction
    # ─────────────────────────────────────────────────────────────────────────
    {
        "category": "ÉQUIPE SCANTRAD",
        "separator": "═══ ÉQUIPE SCANTRAD ═══",
        "color": 0xC27C0E,
        "roles": [
            {"name": "Chef de Projet", "hoist": True, "mentionable": True},
            {"name": "Traducteur", "hoist": True, "mentionable": True},
            {"name": "Éditeur", "hoist": True, "mentionable": True},
            {"name": "Cleaner", "hoist": True, "mentionable": True},
            {"name": "Correcteur", "hoist": True, "mentionable": True},
            {"name": "QCheck", "hoist": True, "mentionable": True},
        ]
    },
    
    # ─────────────────────────────────────────────────────────────────────────
    # PARTENAIRES
    # ─────────────────────────────────────────────────────────────────────────
    {
        "category": "PARTENAIRES",
        "separator": "════════ PARTENAIRES ════════",
        "color": 0xBB844B,
        "roles": [
            {"name": "Partenaire", "hoist": True, "mentionable": True},
        ]
    },
    
    # ─────────────────────────────────────────────────────────────────────────
    # SÉLECTION TRADUCTION - Projets de traduction
    # ─────────────────────────────────────────────────────────────────────────
    {
        "category": "SÉLECTION TRADUCTION",
        "separator": "═══ SÉLECTION TRADUCTION ═══",
        "color": 0x7289DA,
        "roles": [
            {"name": "Gestion Traduction", "hoist": False, "mentionable": True},
            {"name": "Catenaccio", "hoist": False, "mentionable": True},
        ]
    },
    
    # ─────────────────────────────────────────────────────────────────────────
    # BOOSTERS - Soutiens Nitro
    # ─────────────────────────────────────────────────────────────────────────
    {
        "category": "BOOSTERS",
        "separator": "════════ BOOSTERS ════════",
        "color": 0xFF73FA,
        "roles": [
            {"name": "Booster", "hoist": True, "mentionable": False},
        ]
    },
    
    # ─────────────────────────────────────────────────────────────────────────
    # SONDAGE
    # ─────────────────────────────────────────────────────────────────────────
    {
        "category": "SONDAGE",
        "separator": "════════ SONDAGE ════════",
        "color": 0x9B59B6,
        "roles": [
            {"name": "Sondage", "hoist": False, "mentionable": True},
        ]
    },
    
    # ─────────────────────────────────────────────────────────────────────────
    # LECTEURS AVANCÉS
    # ─────────────────────────────────────────────────────────────────────────
    {
        "category": "LECTEURS AVANCÉS",
        "separator": "═══ LECTEURS AVANCÉS ═══",
        "color": 0x5CC24F,
        "roles": [
            {"name": "Lecteur Avancé", "hoist": True, "mentionable": False},
        ]
    },
    
    # ─────────────────────────────────────────────────────────────────────────
    # LECTEUR - MANGA
    # ─────────────────────────────────────────────────────────────────────────
    {
        "category": "LECTEUR - MANGA",
        "separator": "═══ LECTEUR - MANGA ═══",
        "color": 0x3498DB,
        "roles": [
            {"name": "Lecteurs Sujudan", "hoist": False, "mentionable": True},
            {"name": "Lecteurs OFF", "hoist": False, "mentionable": True},
            {"name": "Lecteurs -NightOwl", "hoist": False, "mentionable": True},
            {"name": "Lecteur Fan des Thérons", "hoist": False, "mentionable": True},
        ]
    },
    
    # ─────────────────────────────────────────────────────────────────────────
    # PROJETS / MANGA
    # ─────────────────────────────────────────────────────────────────────────
    {
        "category": "PROJETS / MANGA",
        "separator": "═══ PROJETS / MANGA ═══",
        "color": 0xE91E63,
        "roles": [
            {"name": "📚 Tougen Anki", "hoist": False, "mentionable": True},
            {"name": "📚 Ao No Exorcist", "hoist": False, "mentionable": True},
            {"name": "📚 Tokyo Underworld", "hoist": False, "mentionable": True},
            {"name": "📚 Satsudou", "hoist": False, "mentionable": True},
            {"name": "📚 Catenaccio", "hoist": False, "mentionable": True},
        ]
    },
    
    # ─────────────────────────────────────────────────────────────────────────
    # COMMUNITY
    # ─────────────────────────────────────────────────────────────────────────
    {
        "category": "COMMUNITY",
        "separator": "════════ COMMUNITY ════════",
        "color": 0x5D7571,
        "roles": [
            {"name": "Définir", "hoist": False, "mentionable": False},
            {"name": "QCommunautaire", "hoist": False, "mentionable": False},
            {"name": "GiftGiver", "hoist": False, "mentionable": False},
            {"name": "Théoricien", "hoist": False, "mentionable": False},
            {"name": "Twittos", "hoist": False, "mentionable": False},
            {"name": "Sans -rôles", "hoist": False, "mentionable": False},
        ]
    },
    
    # ─────────────────────────────────────────────────────────────────────────
    # NOTIFICATIONS
    # ─────────────────────────────────────────────────────────────────────────
    {
        "category": "NOTIFICATIONS",
        "separator": "════════ NOTIFICATIONS ════════",
        "color": 0xE67E22,
        "roles": [
            {"name": "🔔 Annonces", "hoist": False, "mentionable": True},
            {"name": "🎉 Événements", "hoist": False, "mentionable": True},
            {"name": "🎁 Giveaway", "hoist": False, "mentionable": True},
            {"name": "🤝 Partenaires", "hoist": False, "mentionable": True},
        ]
    },
    
    # ─────────────────────────────────────────────────────────────────────────
    # COMPORTEMENT
    # ─────────────────────────────────────────────────────────────────────────
    {
        "category": "COMPORTEMENT",
        "separator": "════════ COMPORTEMENT ════════",
        "color": 0x1ABC9C,
        "roles": [
            {"name": "✅ Vérifié", "hoist": False, "mentionable": False},
            {"name": "⚠️ Avertissement", "hoist": False, "mentionable": False},
            {"name": "🔇 Mute", "hoist": False, "mentionable": False},
        ]
    },
]

# ═══════════════════════════════════════════════════════════════════════════════
# RÔLES PROTÉGÉS - Ne jamais supprimer
# ═══════════════════════════════════════════════════════════════════════════════

PROTECTED_ROLES = [
    "@everyone",
    "Server Booster",
    # Ajouter les noms des bots à protéger
    "DoubleM",
    "Nadeko", 
    "MEE6",
    "Dyno",
    "Carl-bot",
]

# Noms partiels de bots à protéger (si le nom contient ces mots)
PROTECTED_BOT_KEYWORDS = ["bot", "Bot", "BOT"]


class RolesSetup(commands.Cog):
    """🔧 Module de gestion et restructuration des rôles du serveur."""
    
    def __init__(self, bot):
        self.bot = bot
    
    def is_protected(self, role: discord.Role) -> bool:
        """Vérifie si un rôle est protégé."""
        # Rôle @everyone
        if role.is_default():
            return True
        
        # Rôle géré par une intégration (bots, Nitro, etc.)
        if role.managed:
            return True
        
        # Nom dans la liste protégée
        if role.name in PROTECTED_ROLES:
            return True
        
        # Contient un mot-clé de bot
        for keyword in PROTECTED_BOT_KEYWORDS:
            if keyword in role.name:
                return True
        
        return False
    
    def get_role_count(self) -> tuple:
        """Compte le nombre de rôles et séparateurs dans la structure."""
        separators = sum(1 for cat in ROLES_STRUCTURE if cat.get("separator"))
        roles = sum(len(cat.get("roles", [])) for cat in ROLES_STRUCTURE)
        return separators, roles
    
    # ═══════════════════════════════════════════════════════════════════════════
    # COMMANDE : APERÇU DE LA STRUCTURE
    # ═══════════════════════════════════════════════════════════════════════════
    
    @commands.command(name="roles_preview")
    @commands.has_permissions(manage_roles=True)
    async def roles_preview(self, ctx):
        """
        👁️ Affiche un aperçu de la structure des rôles sans faire de changements.
        """
        separators, roles = self.get_role_count()
        
        embed = discord.Embed(
            title="👁️ Aperçu de la Structure des Rôles",
            description=(
                f"**{len(ROLES_STRUCTURE)}** catégories\n"
                f"**{separators}** séparateurs\n"
                f"**{roles}** rôles\n"
                f"**{separators + roles}** rôles au total"
            ),
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        
        for category in ROLES_STRUCTURE:
            cat_name = category["category"]
            separator = category.get("separator", "")
            color = category.get("color", 0)
            cat_roles = category.get("roles", [])
            
            # Construire la liste des rôles
            roles_list = []
            if separator:
                roles_list.append(f"📌 `{separator}`")
            
            for role in cat_roles:
                indicators = ""
                if role.get("hoist"):
                    indicators += " 👑"
                if role.get("mentionable"):
                    indicators += " 📢"
                roles_list.append(f"• {role['name']}{indicators}")
            
            field_value = "\n".join(roles_list) if roles_list else "*(vide)*"
            if len(field_value) > 1024:
                field_value = field_value[:1020] + "..."
            
            color_hex = f"#{color:06X}" if color else "Défaut"
            embed.add_field(
                name=f"🎨 {cat_name} ({color_hex})",
                value=field_value,
                inline=False
            )
        
        embed.set_footer(text="👑 = Hoist | 📢 = Mentionnable")
        await ctx.send(embed=embed)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # COMMANDE : LISTE DES RÔLES ACTUELS
    # ═══════════════════════════════════════════════════════════════════════════
    
    @commands.command(name="roles_current")
    @commands.has_permissions(manage_roles=True)
    async def roles_current(self, ctx):
        """
        📜 Liste tous les rôles actuels du serveur avec leur statut de protection.
        """
        guild = ctx.guild
        roles = sorted(guild.roles, key=lambda r: r.position, reverse=True)
        
        protected_count = 0
        deletable_count = 0
        
        embed = discord.Embed(
            title=f"📜 Rôles de {guild.name}",
            description=f"Total: **{len(roles)}** rôles",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        
        roles_text = ""
        for role in roles[:30]:
            is_protected = self.is_protected(role)
            if is_protected:
                protected_count += 1
                icon = "🔒"
            else:
                deletable_count += 1
                icon = "🗑️"
            
            color_hex = f"#{role.color.value:06X}" if role.color.value else "---"
            members = len(role.members)
            hoist = "👑" if role.hoist else ""
            
            roles_text += f"`{role.position:02d}` {icon}{hoist} **{role.name}** ({members}) {color_hex}\n"
        
        if len(roles) > 30:
            roles_text += f"\n*...et {len(roles) - 30} autres rôles*"
        
        embed.add_field(name="🎭 Rôles (par position)", value=roles_text or "Aucun", inline=False)
        
        embed.add_field(
            name="📊 Résumé",
            value=(
                f"🔒 Protégés: **{protected_count}**\n"
                f"🗑️ Supprimables: **{deletable_count}**"
            ),
            inline=False
        )
        
        embed.add_field(
            name="📌 Légende",
            value="🔒 = Protégé | 🗑️ = Supprimable | 👑 = Hoist",
            inline=False
        )
        
        embed.set_footer(text=f"Demandé par {ctx.author.name}")
        await ctx.send(embed=embed)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # COMMANDE : SUPPRIMER LES ANCIENS RÔLES
    # ═══════════════════════════════════════════════════════════════════════════
    
    @commands.command(name="roles_delete_old")
    @commands.has_permissions(administrator=True)
    async def roles_delete_old(self, ctx):
        """
        🗑️ Supprime tous les rôles non-protégés du serveur.
        ⚠️ ATTENTION: Cette action est irréversible!
        """
        guild = ctx.guild
        
        # Compter les rôles à supprimer
        deletable_roles = [r for r in guild.roles if not self.is_protected(r)]
        
        if not deletable_roles:
            await ctx.send("✅ Aucun rôle à supprimer.")
            return
        
        # Demande de confirmation
        embed = discord.Embed(
            title="⚠️ CONFIRMATION REQUISE",
            description=(
                f"Cette commande va **SUPPRIMER** les rôles suivants:\n\n"
                f"**{len(deletable_roles)}** rôles seront supprimés.\n\n"
                "**Liste des rôles à supprimer:**\n"
                + "\n".join([f"• {r.name}" for r in deletable_roles[:20]])
                + (f"\n*...et {len(deletable_roles) - 20} autres*" if len(deletable_roles) > 20 else "")
                + "\n\n⚠️ **Cette action est IRRÉVERSIBLE!**\n\n"
                "Tapez `CONFIRMER SETUP` pour continuer."
            ),
            color=discord.Color.red(),
            timestamp=datetime.now()
        )
        
        await ctx.send(embed=embed)
        
        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel
        
        try:
            msg = await self.bot.wait_for("message", timeout=30.0, check=check)
            
            if msg.content != "CONFIRMER SETUP":
                await ctx.send("❌ Confirmation incorrecte. Opération annulée.")
                return
            
            # Supprimer les rôles
            progress_embed = discord.Embed(
                title="🗑️ Suppression en cours...",
                description="Veuillez patienter...",
                color=discord.Color.orange()
            )
            progress_msg = await ctx.send(embed=progress_embed)
            
            deleted = 0
            errors = 0
            
            for role in deletable_roles:
                try:
                    await role.delete(reason=f"Restructuration par {ctx.author}")
                    deleted += 1
                    await asyncio.sleep(0.5)  # Rate limit
                except discord.Forbidden:
                    errors += 1
                    logging.warning(f"Permission refusée pour supprimer le rôle: {role.name}")
                except discord.HTTPException as e:
                    errors += 1
                    logging.error(f"Erreur HTTP lors de la suppression de {role.name}: {e}")
            
            # Résultat
            final_embed = discord.Embed(
                title="✅ Suppression Terminée",
                description=(
                    f"**{deleted}** rôles supprimés\n"
                    f"**{errors}** erreurs"
                ),
                color=discord.Color.green() if errors == 0 else discord.Color.orange(),
                timestamp=datetime.now()
            )
            await progress_msg.edit(embed=final_embed)
            
        except asyncio.TimeoutError:
            await ctx.send("⏰ Temps écoulé. Opération annulée.")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # COMMANDE : CRÉER LA NOUVELLE STRUCTURE
    # ═══════════════════════════════════════════════════════════════════════════
    
    @commands.command(name="roles_create")
    @commands.has_permissions(administrator=True)
    async def roles_create(self, ctx):
        """
        ✨ Crée la nouvelle structure de rôles.
        Les rôles sont créés en ordre inverse pour respecter la hiérarchie.
        """
        guild = ctx.guild
        separators, roles_count = self.get_role_count()
        total = separators + roles_count
        
        # Confirmation
        embed = discord.Embed(
            title="✨ Création de la Structure",
            description=(
                f"Cette commande va créer **{total}** nouveaux rôles:\n"
                f"• **{separators}** séparateurs\n"
                f"• **{roles_count}** rôles\n\n"
                "**Réagissez avec ✅ pour confirmer.**"
            ),
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        
        confirm_msg = await ctx.send(embed=embed)
        await confirm_msg.add_reaction("✅")
        await confirm_msg.add_reaction("❌")
        
        def check(reaction, user):
            return (
                user == ctx.author 
                and str(reaction.emoji) in ["✅", "❌"] 
                and reaction.message.id == confirm_msg.id
            )
        
        try:
            reaction, _ = await self.bot.wait_for("reaction_add", timeout=30.0, check=check)
            
            if str(reaction.emoji) == "❌":
                await confirm_msg.clear_reactions()
                await ctx.send("❌ Opération annulée.")
                return
            
            await confirm_msg.clear_reactions()
            
            # Créer les rôles en ordre INVERSE (du bas vers le haut)
            progress_embed = discord.Embed(
                title="✨ Création en cours...",
                description="Veuillez patienter...",
                color=discord.Color.blue()
            )
            await confirm_msg.edit(embed=progress_embed)
            
            created = 0
            errors = 0
            created_roles = []
            
            # Inverser la structure pour créer du bas vers le haut
            for category in reversed(ROLES_STRUCTURE):
                color = category.get("color", 0)
                separator = category.get("separator")
                cat_roles = category.get("roles", [])
                
                # Créer les rôles de la catégorie (en ordre inverse)
                for role_data in reversed(cat_roles):
                    try:
                        # Vérifier si le rôle existe déjà
                        existing = discord.utils.get(guild.roles, name=role_data["name"])
                        if existing:
                            created_roles.append(existing)
                            continue
                        
                        role = await guild.create_role(
                            name=role_data["name"],
                            color=discord.Color(color) if color else discord.Color.default(),
                            hoist=role_data.get("hoist", False),
                            mentionable=role_data.get("mentionable", False),
                            reason=f"Structure créée par {ctx.author}"
                        )
                        created += 1
                        created_roles.append(role)
                        await asyncio.sleep(0.3)
                    except Exception as e:
                        errors += 1
                        logging.error(f"Erreur création {role_data['name']}: {e}")
                
                # Créer le séparateur
                if separator:
                    try:
                        existing = discord.utils.get(guild.roles, name=separator)
                        if existing:
                            created_roles.append(existing)
                        else:
                            role = await guild.create_role(
                                name=separator,
                                color=discord.Color(color) if color else discord.Color.default(),
                                hoist=True,  # Séparateurs toujours visibles
                                mentionable=False,
                                reason=f"Séparateur créé par {ctx.author}"
                            )
                            created += 1
                            created_roles.append(role)
                            await asyncio.sleep(0.3)
                    except Exception as e:
                        errors += 1
                        logging.error(f"Erreur création séparateur {separator}: {e}")
            
            # Résultat
            final_embed = discord.Embed(
                title="✅ Création Terminée",
                description=(
                    f"**{created}** rôles créés\n"
                    f"**{errors}** erreurs\n\n"
                    "Utilisez `!roles_reorder` pour organiser les positions."
                ),
                color=discord.Color.green() if errors == 0 else discord.Color.orange(),
                timestamp=datetime.now()
            )
            await confirm_msg.edit(embed=final_embed)
            
        except asyncio.TimeoutError:
            await confirm_msg.clear_reactions()
            await ctx.send("⏰ Temps écoulé. Opération annulée.")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # COMMANDE : RÉORGANISER LES RÔLES
    # ═══════════════════════════════════════════════════════════════════════════
    
    @commands.command(name="roles_reorder")
    @commands.has_permissions(administrator=True)
    async def roles_reorder(self, ctx):
        """
        📊 Réorganise les positions des rôles selon la structure définie.
        """
        guild = ctx.guild
        
        embed = discord.Embed(
            title="📊 Réorganisation des Rôles",
            description=(
                "Cette commande va réorganiser les positions des rôles "
                "selon la structure définie.\n\n"
                "**Réagissez avec ✅ pour confirmer.**"
            ),
            color=discord.Color.orange(),
            timestamp=datetime.now()
        )
        
        confirm_msg = await ctx.send(embed=embed)
        await confirm_msg.add_reaction("✅")
        await confirm_msg.add_reaction("❌")
        
        def check(reaction, user):
            return (
                user == ctx.author 
                and str(reaction.emoji) in ["✅", "❌"] 
                and reaction.message.id == confirm_msg.id
            )
        
        try:
            reaction, _ = await self.bot.wait_for("reaction_add", timeout=30.0, check=check)
            await confirm_msg.clear_reactions()
            
            if str(reaction.emoji) == "❌":
                await ctx.send("❌ Opération annulée.")
                return
            
            # Réorganiser
            progress_embed = discord.Embed(
                title="⏳ Réorganisation en cours...",
                color=discord.Color.blue()
            )
            await confirm_msg.edit(embed=progress_embed)
            
            # Position de départ: juste en dessous du rôle le plus haut du bot
            bot_top_role = guild.me.top_role
            position = bot_top_role.position - 1
            
            role_positions = {}
            found = 0
            
            for category in ROLES_STRUCTURE:
                separator = category.get("separator")
                cat_roles = category.get("roles", [])
                
                # Séparateur
                if separator:
                    role = discord.utils.get(guild.roles, name=separator)
                    if role and not role.managed:
                        role_positions[role] = position
                        position -= 1
                        found += 1
                
                # Rôles
                for role_data in cat_roles:
                    role = discord.utils.get(guild.roles, name=role_data["name"])
                    if role and not role.managed:
                        role_positions[role] = position
                        position -= 1
                        found += 1
            
            if role_positions:
                try:
                    await guild.edit_role_positions(role_positions)
                    
                    final_embed = discord.Embed(
                        title="✅ Réorganisation Terminée",
                        description=f"**{found}** rôles ont été réorganisés.",
                        color=discord.Color.green(),
                        timestamp=datetime.now()
                    )
                    await confirm_msg.edit(embed=final_embed)
                except discord.Forbidden:
                    await ctx.send("❌ Permission insuffisante pour réorganiser les rôles.")
                except Exception as e:
                    await ctx.send(f"❌ Erreur: {e}")
            else:
                await ctx.send("❌ Aucun rôle trouvé à réorganiser.")
            
        except asyncio.TimeoutError:
            await confirm_msg.clear_reactions()
            await ctx.send("⏰ Temps écoulé. Opération annulée.")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # COMMANDE : SETUP COMPLET
    # ═══════════════════════════════════════════════════════════════════════════
    
    @commands.command(name="roles_setup")
    @commands.has_permissions(administrator=True)
    async def roles_setup(self, ctx):
        """
        🔄 Effectue le setup complet: suppression → création → réorganisation.
        ⚠️ ATTENTION: Cette commande supprime tous les anciens rôles!
        """
        guild = ctx.guild
        deletable_roles = [r for r in guild.roles if not self.is_protected(r)]
        separators, roles_count = self.get_role_count()
        
        embed = discord.Embed(
            title="🔄 SETUP COMPLET DES RÔLES",
            description=(
                "Cette commande va effectuer les actions suivantes:\n\n"
                f"1️⃣ **Supprimer** {len(deletable_roles)} rôles existants\n"
                f"2️⃣ **Créer** {separators + roles_count} nouveaux rôles\n"
                f"3️⃣ **Réorganiser** les positions\n\n"
                "⚠️ **CETTE ACTION EST IRRÉVERSIBLE!**\n\n"
                "Tapez `CONFIRMER SETUP` pour continuer."
            ),
            color=discord.Color.red(),
            timestamp=datetime.now()
        )
        
        await ctx.send(embed=embed)
        
        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel
        
        try:
            msg = await self.bot.wait_for("message", timeout=30.0, check=check)
            
            if msg.content != "CONFIRMER SETUP":
                await ctx.send("❌ Confirmation incorrecte. Opération annulée.")
                return
            
            # ÉTAPE 1: Suppression
            step1_embed = discord.Embed(
                title="🔄 Étape 1/3: Suppression des anciens rôles...",
                color=discord.Color.orange()
            )
            progress_msg = await ctx.send(embed=step1_embed)
            
            deleted = 0
            for role in deletable_roles:
                try:
                    await role.delete(reason=f"Setup complet par {ctx.author}")
                    deleted += 1
                    await asyncio.sleep(0.5)
                except Exception as e:
                    logging.warning(f"Impossible de supprimer {role.name}: {e}")
            
            # ÉTAPE 2: Création
            step2_embed = discord.Embed(
                title="🔄 Étape 2/3: Création des nouveaux rôles...",
                description=f"✅ {deleted} rôles supprimés",
                color=discord.Color.orange()
            )
            await progress_msg.edit(embed=step2_embed)
            
            created = 0
            for category in reversed(ROLES_STRUCTURE):
                color = category.get("color", 0)
                separator = category.get("separator")
                cat_roles = category.get("roles", [])
                
                for role_data in reversed(cat_roles):
                    try:
                        await guild.create_role(
                            name=role_data["name"],
                            color=discord.Color(color) if color else discord.Color.default(),
                            hoist=role_data.get("hoist", False),
                            mentionable=role_data.get("mentionable", False),
                            reason=f"Setup par {ctx.author}"
                        )
                        created += 1
                        await asyncio.sleep(0.3)
                    except Exception as e:
                        logging.warning(f"Impossible de créer {role_data['name']}: {e}")
                
                if separator:
                    try:
                        await guild.create_role(
                            name=separator,
                            color=discord.Color(color) if color else discord.Color.default(),
                            hoist=True,
                            mentionable=False,
                            reason=f"Setup par {ctx.author}"
                        )
                        created += 1
                        await asyncio.sleep(0.3)
                    except Exception as e:
                        logging.warning(f"Impossible de créer séparateur {separator}: {e}")
            
            # ÉTAPE 3: Réorganisation
            step3_embed = discord.Embed(
                title="🔄 Étape 3/3: Réorganisation des positions...",
                description=f"✅ {deleted} rôles supprimés\n✅ {created} rôles créés",
                color=discord.Color.orange()
            )
            await progress_msg.edit(embed=step3_embed)
            
            bot_top_role = guild.me.top_role
            position = bot_top_role.position - 1
            role_positions = {}
            
            for category in ROLES_STRUCTURE:
                separator = category.get("separator")
                cat_roles = category.get("roles", [])
                
                if separator:
                    role = discord.utils.get(guild.roles, name=separator)
                    if role:
                        role_positions[role] = position
                        position -= 1
                
                for role_data in cat_roles:
                    role = discord.utils.get(guild.roles, name=role_data["name"])
                    if role:
                        role_positions[role] = position
                        position -= 1
            
            reordered = 0
            if role_positions:
                try:
                    await guild.edit_role_positions(role_positions)
                    reordered = len(role_positions)
                except Exception as e:
                    logging.error(f"Erreur lors de la réorganisation: {e}")
            
            # RÉSULTAT FINAL
            final_embed = discord.Embed(
                title="✅ SETUP TERMINÉ",
                description=(
                    f"✅ **{deleted}** rôles supprimés\n"
                    f"✅ **{created}** rôles créés\n"
                    f"✅ **{reordered}** rôles réorganisés"
                ),
                color=discord.Color.green(),
                timestamp=datetime.now()
            )
            await progress_msg.edit(embed=final_embed)
            
        except asyncio.TimeoutError:
            await ctx.send("⏰ Temps écoulé. Opération annulée.")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # COMMANDE : EXPORTER LES IDS
    # ═══════════════════════════════════════════════════════════════════════════
    
    @commands.command(name="roles_export")
    @commands.has_permissions(manage_roles=True)
    async def roles_export(self, ctx):
        """
        📤 Exporte les IDs des rôles pour utilisation dans config.py
        """
        guild = ctx.guild
        
        output = "# Configuration des rôles générée automatiquement\n"
        output += f"# Serveur: {guild.name}\n"
        output += f"# Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
        output += "ROLE_IDS = {\n"
        
        for category in ROLES_STRUCTURE:
            cat_name = category["category"]
            output += f"\n    # {cat_name}\n"
            
            separator = category.get("separator")
            if separator:
                role = discord.utils.get(guild.roles, name=separator)
                if role:
                    safe_name = separator.replace("═", "").replace(" ", "_").strip("_")
                    output += f'    "sep_{safe_name}": {role.id},\n'
            
            for role_data in category.get("roles", []):
                role = discord.utils.get(guild.roles, name=role_data["name"])
                if role:
                    safe_name = role_data["name"].replace(" ", "_").replace("📚", "").replace("🔔", "").replace("🎉", "").replace("🎁", "").replace("🤝", "").replace("✅", "").replace("⚠️", "").replace("🔇", "").strip("_")
                    output += f'    "{safe_name}": {role.id},\n'
        
        output += "}\n"
        
        # Envoyer en fichier si trop long
        if len(output) > 1900:
            import io
            await ctx.send(
                "📤 Configuration exportée:",
                file=discord.File(fp=io.BytesIO(output.encode()), filename="role_ids.py")
            )
        else:
            await ctx.send(f"```python\n{output}\n```")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # COMMANDE : AIDE ROLES
    # ═══════════════════════════════════════════════════════════════════════════
    
    @commands.command(name="roles_help")
    async def roles_help(self, ctx):
        """
        📖 Affiche l'aide pour les commandes de gestion des rôles.
        """
        embed = discord.Embed(
            title="📖 Aide - Gestion des Rôles",
            description="Commandes disponibles pour gérer la structure des rôles du serveur.",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        
        commands_info = [
            ("!roles_preview", "👁️ Aperçu de la structure définie", "manage_roles"),
            ("!roles_current", "📜 Liste les rôles actuels du serveur", "manage_roles"),
            ("!roles_create", "✨ Crée les nouveaux rôles", "administrator"),
            ("!roles_reorder", "📊 Réorganise les positions", "administrator"),
            ("!roles_delete_old", "🗑️ Supprime les anciens rôles", "administrator"),
            ("!roles_setup", "🔄 Setup complet (suppr + création + ordre)", "administrator"),
            ("!roles_export", "📤 Exporte les IDs des rôles", "manage_roles"),
        ]
        
        for cmd_name, description, permission in commands_info:
            embed.add_field(
                name=f"`{cmd_name}`",
                value=f"{description}\n*Permission: {permission}*",
                inline=False
            )
        
        embed.set_footer(text="⚠️ Les commandes admin sont irréversibles!")
        await ctx.send(embed=embed)


async def setup(bot):
    """Setup pour discord.py 2.0+"""
    await bot.add_cog(RolesSetup(bot))
    logging.info("🔧 Cog RolesSetup chargé avec succès")