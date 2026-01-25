# roles_setup.py
# Commande pour restructurer les rôles du serveur Discord LanorTrad
import discord
from discord.ext import commands
import asyncio
from datetime import datetime
import logging

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION DES RÔLES - Structure complète basée sur les screenshots
# ═══════════════════════════════════════════════════════════════════════════════

ROLES_STRUCTURE = [
    # ─────────────────────────────────────────────────────────────────────────
    # DIRECTION - Fondateurs et direction (Or royal #FFD700)
    # ─────────────────────────────────────────────────────────────────────────
    {
        "category": "DIRECTION",
        "separator": "══════ 👑 DIRECTION ══════",
        "color": 0xFFD700,
        "roles": [
            {"name": "✨ Maître des Origines", "hoist": True, "mentionable": False},
            {"name": "👑 Équipe LanorTrad", "hoist": True, "mentionable": False},
            {"name": "⭐ Princesa", "hoist": True, "mentionable": False},
        ]
    },
    
    # ─────────────────────────────────────────────────────────────────────────
    # BOTS - Bots du serveur (#7F8C8D)
    # ─────────────────────────────────────────────────────────────────────────
    {
        "category": "BOTS",
        "separator": "══════ 🤖 BOTS ══════",
        "color": 0x7F8C8D,
        "roles": [
            # Les rôles des bots sont généralement créés automatiquement
            # On ne crée pas de rôles ici, juste le séparateur
        ]
    },
    
    # ─────────────────────────────────────────────────────────────────────────
    # STAFF - Équipe de modération (Rouge foncé #C0392B)
    # ─────────────────────────────────────────────────────────────────────────
    {
        "category": "STAFF",
        "separator": "══════ ♡ STAFF ══════",
        "color": 0xC0392B,
        "roles": [
            {"name": "♡ Gardiens de l'Ordre", "hoist": True, "mentionable": False},
            {"name": "🎉 Staff Animation", "hoist": True, "mentionable": True},
            {"name": "🤝 Collabs", "hoist": True, "mentionable": True},
        ]
    },
    
    # ─────────────────────────────────────────────────────────────────────────
    # ÉQUIPE SCANTRAD - Équipe de traduction (Violet manga #9B59B6)
    # ─────────────────────────────────────────────────────────────────────────
    {
        "category": "ÉQUIPE SCANTRAD",
        "separator": "══════ 🌸 ÉQUIPE SCANTRAD ══════",
        "color": 0x9B59B6,
        "roles": [
            {"name": "📜 Alchimiste des Mots", "hoist": True, "mentionable": True},
            {"name": "🎨 Purificateur d'Art", "hoist": True, "mentionable": True},
            {"name": "🌸 Artisan des Pages", "hoist": True, "mentionable": True},
            {"name": "🔍 Détective des Fautes", "hoist": True, "mentionable": True},
        ]
    },
    
    # ─────────────────────────────────────────────────────────────────────────
    # PARTENAIRES (#16A085)
    # ─────────────────────────────────────────────────────────────────────────
    {
        "category": "PARTENAIRES",
        "separator": "══════ 💛 PARTENAIRES ══════",
        "color": 0x16A085,
        "roles": [
            {"name": "💛 Kamina Traduction", "hoist": True, "mentionable": True},
        ]
    },
    
    # ─────────────────────────────────────────────────────────────────────────
    # SOUTIEN - Boosters (#E84393)
    # ─────────────────────────────────────────────────────────────────────────
    {
        "category": "SOUTIEN",
        "separator": "══════ 🚀 SOUTIEN ══════",
        "color": 0xE84393,
        "roles": [
            {"name": "🚀 Booster", "hoist": True, "mentionable": False},
        ]
    },
    
    # ─────────────────────────────────────────────────────────────────────────
    # LECTEURS PREMIUM (#F1C40F)
    # ─────────────────────────────────────────────────────────────────────────
    {
        "category": "LECTEURS PREMIUM",
        "separator": "══════ 👑 LECTEURS PREMIUM ══════",
        "color": 0xF1C40F,
        "roles": [
            {"name": "👑 Lecteurs Suprême", "hoist": True, "mentionable": False},
            {"name": "🏆 Lecteurs VIP", "hoist": True, "mentionable": False},
            {"name": "📘 Lecteurs Réguliers", "hoist": True, "mentionable": False},
            {"name": "📖 Lecteurs", "hoist": True, "mentionable": False},
        ]
    },
    
    # ─────────────────────────────────────────────────────────────────────────
    # PROJETS / MANGAS (#3498DB)
    # ─────────────────────────────────────────────────────────────────────────
    {
        "category": "PROJETS / MANGAS",
        "separator": "══════ 📚 PROJETS / MANGAS ══════",
        "color": 0x3498DB,
        "roles": [
            {"name": "🔥 Ao No Exorcist", "hoist": False, "mentionable": True},
            {"name": "🔴 Satsudou", "hoist": False, "mentionable": True},
            {"name": "🏙️ Tokyo Underworld", "hoist": False, "mentionable": True},
            {"name": "👹 Tougen Anki", "hoist": False, "mentionable": True},
            {"name": "⚽ Catenaccio", "hoist": False, "mentionable": True},
            {"name": "🤝 Projets Collab", "hoist": False, "mentionable": True},
        ]
    },
    
    # ─────────────────────────────────────────────────────────────────────────
    # COMMUNAUTÉ (#2ECC71)
    # ─────────────────────────────────────────────────────────────────────────
    {
        "category": "COMMUNAUTÉ",
        "separator": "══════ 🎮 COMMUNAUTÉ ══════",
        "color": 0x2ECC71,
        "roles": [
            {"name": "🎨 Artiste", "hoist": False, "mentionable": False},
            {"name": "📚 Collectionneurs", "hoist": False, "mentionable": False},
            {"name": "🎧 Musique", "hoist": False, "mentionable": False},
            {"name": "📷 Photographie", "hoist": False, "mentionable": False},
            {"name": "🎮 Jeux vidéo", "hoist": False, "mentionable": False},
        ]
    },
    
    # ─────────────────────────────────────────────────────────────────────────
    # NOTIFICATIONS (#E67E22)
    # ─────────────────────────────────────────────────────────────────────────
    {
        "category": "NOTIFICATIONS",
        "separator": "══════ 📣 NOTIFICATIONS ══════",
        "color": 0xE67E22,
        "roles": [
            {"name": "📢 Annonces", "hoist": False, "mentionable": True},
            {"name": "🎉 Événements", "hoist": False, "mentionable": True},
            {"name": "🎁 Giveaway", "hoist": False, "mentionable": True},
            {"name": "💛 Partenaires", "hoist": False, "mentionable": True},
            {"name": "🐦 Twittos", "hoist": False, "mentionable": True},
            {"name": "🎵 Tiktok", "hoist": False, "mentionable": True},
            {"name": "👀 Spoilers", "hoist": False, "mentionable": True},
        ]
    },
    
    # ─────────────────────────────────────────────────────────────────────────
    # COMPORTEMENT (#1ABC9C)
    # ─────────────────────────────────────────────────────────────────────────
    {
        "category": "COMPORTEMENT",
        "separator": "══════ 🌸 COMPORTEMENT ══════",
        "color": 0x1ABC9C,
        "roles": [
            {"name": "✅ Lecteurs Respectueux", "hoist": False, "mentionable": False},
        ]
    },
]

# ═══════════════════════════════════════════════════════════════════════════════
# RÔLES PROTÉGÉS - Ne jamais supprimer
# ═══════════════════════════════════════════════════════════════════════════════

PROTECTED_ROLES = [
    "@everyone",
    "Server Booster",
    # Bots
    "DraftBot",
    "DoubleM",
    "Nadeko", 
    "MEE6",
    "Dyno",
    "Carl-bot",
    "BOTS",
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
            
            field_value = "\n".join(roles_list) if roles_list else "*(vide - séparateur uniquement)*"
            if len(field_value) > 1024:
                field_value = field_value[:1020] + "..."
            
            color_hex = f"#{color:06X}" if color else "Défaut"
            embed.add_field(
                name=f"🎨 {cat_name} ({color_hex})",
                value=field_value,
                inline=False
            )
        
        embed.set_footer(text="👑 = Affiché séparément | 📢 = Mentionnable")
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
                "Tapez `CONFIRMER` pour continuer."
            ),
            color=discord.Color.red(),
            timestamp=datetime.now()
        )
        
        await ctx.send(embed=embed)
        
        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel
        
        try:
            msg = await self.bot.wait_for("message", timeout=30.0, check=check)
            
            if msg.content != "CONFIRMER":
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
            skipped = 0
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
                            skipped += 1
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
                            skipped += 1
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
                    f"**{skipped}** rôles existants (ignorés)\n"
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
                    safe_name = cat_name.replace(" ", "_").replace("/", "_")
                    output += f'    "sep_{safe_name}": {role.id},\n'
            
            for role_data in category.get("roles", []):
                role = discord.utils.get(guild.roles, name=role_data["name"])
                if role:
                    # Nettoyer le nom pour en faire une clé valide
                    safe_name = role_data["name"]
                    for char in ["📜", "🎨", "🌸", "🔍", "✨", "👑", "⭐", "♡", "🎉", "🤝", "💛", "🚀", "🏆", "📘", "📖", "🔥", "🔴", "🏙️", "👹", "⚽", "📚", "🎧", "📷", "🎮", "📢", "🎁", "🐦", "🎵", "👀", "✅", "🤖"]:
                        safe_name = safe_name.replace(char, "")
                    safe_name = safe_name.strip().replace(" ", "_").replace("'", "")
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

        # ═══════════════════════════════════════════════════════════════════════════
    # COMMANDE : MODIFIER PERMISSIONS DE SALON
    # ═══════════════════════════════════════════════════════════════════════════
    
    @commands.command(name="perms_setup")
    @commands.has_permissions(manage_channels=True)
    async def perms_setup(self, ctx):
        """
        🔐 Configure les permissions d'un rôle pour un salon de manière interactive.
        """
        # ÉTAPE 1: Sélection du salon
        embed_channel = discord.Embed(
            title="🔐 Configuration des Permissions",
            description=(
                "**Étape 1/3:** Sélection du salon\n\n"
                "Mentionnez le salon dont vous voulez modifier les permissions.\n"
                "Exemple: #général ou copiez l'ID du salon"
            ),
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        embed_channel.set_footer(text="Tapez 'annuler' pour annuler | Timeout: 60s")
        await ctx.send(embed=embed_channel)
        
        def check_msg(m):
            return m.author == ctx.author and m.channel == ctx.channel
        
        try:
            # Attendre le salon
            msg = await self.bot.wait_for("message", timeout=60.0, check=check_msg)
            
            if msg.content.lower() == "annuler":
                await ctx.send("❌ Opération annulée.")
                return
            
            # Récupérer le salon
            channel = None
            if msg.channel_mentions:
                channel = msg.channel_mentions[0]
            elif msg.content.isdigit():
                channel = ctx.guild.get_channel(int(msg.content))
            
            if not channel:
                await ctx.send("❌ Salon invalide. Opération annulée.")
                return
            
            # ÉTAPE 2: Sélection du rôle
            embed_role = discord.Embed(
                title="🔐 Configuration des Permissions",
                description=(
                    f"**Étape 2/3:** Sélection du rôle\n\n"
                    f"📍 **Salon sélectionné:** {channel.mention}\n\n"
                    "Mentionnez le rôle ou tapez son nom.\n"
                    "Exemple: @Lecteurs ou Lecteurs"
                ),
                color=discord.Color.blue(),
                timestamp=datetime.now()
            )
            embed_role.set_footer(text="Tapez 'annuler' pour annuler | Timeout: 60s")
            await ctx.send(embed=embed_role)
            
            # Attendre le rôle
            msg = await self.bot.wait_for("message", timeout=60.0, check=check_msg)
            
            if msg.content.lower() == "annuler":
                await ctx.send("❌ Opération annulée.")
                return
            
            # Récupérer le rôle
            role = None
            if msg.role_mentions:
                role = msg.role_mentions[0]
            else:
                role = discord.utils.get(ctx.guild.roles, name=msg.content)
            
            if not role:
                await ctx.send("❌ Rôle invalide. Opération annulée.")
                return
            
            # ÉTAPE 3: Sélection des permissions
            permissions_display = {
                "1": ("✅ Voir le salon", "view_channel", True),
                "2": ("💬 Envoyer des messages", "send_messages", True),
                "3": ("🔗 Intégrer des liens", "embed_links", True),
                "4": ("📎 Joindre des fichiers", "attach_files", True),
                "5": ("😀 Utiliser émojis externes", "use_external_emojis", True),
                "6": ("💭 Ajouter des réactions", "add_reactions", True),
                "7": ("📜 Voir l'historique", "read_message_history", True),
                "8": ("🎤 Se connecter (vocal)", "connect", True),
                "9": ("🔊 Parler (vocal)", "speak", True),
                "10": ("📹 Caméra (vocal)", "stream", True),
                "11": ("🎥 Utiliser activités", "use_embedded_activities", True),
                "12": ("❌ Aucune permission", "none", False),
                "13": ("🚫 Bloquer tout accès", "block", False),
            }
            
            embed_perms = discord.Embed(
                title="🔐 Configuration des Permissions",
                description=(
                    f"**Étape 3/3:** Choix des permissions\n\n"
                    f"📍 **Salon:** {channel.mention}\n"
                    f"👥 **Rôle:** {role.mention}\n\n"
                    "**Sélectionnez les permissions à activer:**\n"
                    "*(Tapez les numéros séparés par des espaces)*\n\n"
                ),
                color=discord.Color.blue(),
                timestamp=datetime.now()
            )
            
            # Organiser les permissions en colonnes
            perms_text_1 = ""
            perms_text_2 = ""
            perms_text_3 = ""
            
            for i, (num, (label, _, _)) in enumerate(permissions_display.items()):
                line = f"`{num}` {label}\n"
                if i < 5:
                    perms_text_1 += line
                elif i < 10:
                    perms_text_2 += line
                else:
                    perms_text_3 += line
            
            embed_perms.add_field(name="📋 Permissions (1)", value=perms_text_1, inline=True)
            embed_perms.add_field(name="📋 Permissions (2)", value=perms_text_2, inline=True)
            embed_perms.add_field(name="📋 Options spéciales", value=perms_text_3, inline=True)
            
            embed_perms.add_field(
                name="💡 Exemples",
                value=(
                    "`1 2 3 4` = Voir + Envoyer + Liens + Fichiers\n"
                    "`12` = Aucune permission (neutre)\n"
                    "`13` = Bloquer complètement l'accès"
                ),
                inline=False
            )
            
            embed_perms.set_footer(text="Tapez 'annuler' pour annuler | Timeout: 120s")
            await ctx.send(embed=embed_perms)
            
            # Attendre les permissions
            msg = await self.bot.wait_for("message", timeout=120.0, check=check_msg)
            
            if msg.content.lower() == "annuler":
                await ctx.send("❌ Opération annulée.")
                return
            
            # Parser les choix
            choices = msg.content.split()
            
            # Construire l'overwrite
            overwrite = discord.PermissionOverwrite()
            
            # Vérifier les options spéciales
            if "13" in choices:
                # Bloquer tout
                overwrite.view_channel = False
                overwrite.send_messages = False
                overwrite.read_message_history = False
                selected_perms = ["🚫 **Accès bloqué**"]
            elif "12" in choices:
                # Neutre (hérite du serveur)
                overwrite = None
                selected_perms = ["⚪ **Permissions héritées** (aucune modification)"]
            else:
                # Permissions personnalisées
                selected_perms = []
                for choice in choices:
                    if choice in permissions_display:
                        label, perm_name, value = permissions_display[choice]
                        setattr(overwrite, perm_name, value)
                        selected_perms.append(label)
            
            # Confirmation finale
            if selected_perms:
                confirm_embed = discord.Embed(
                    title="⚠️ Confirmation Requise",
                    description=(
                        "**Résumé des modifications:**\n\n"
                        f"📍 **Salon:** {channel.mention}\n"
                        f"👥 **Rôle:** {role.mention}\n\n"
                        "**Permissions sélectionnées:**\n"
                        + "\n".join(selected_perms) +
                        "\n\n**Tapez `CONFIRMER` pour appliquer les changements.**"
                    ),
                    color=discord.Color.orange(),
                    timestamp=datetime.now()
                )
                confirm_embed.set_footer(text="Tapez autre chose pour annuler | Timeout: 30s")
                await ctx.send(embed=confirm_embed)
                
                # Attendre confirmation
                msg = await self.bot.wait_for("message", timeout=30.0, check=check_msg)
                
                if msg.content != "CONFIRMER":
                    await ctx.send("❌ Opération annulée.")
                    return
                
                # Appliquer les permissions
                try:
                    if overwrite is None:
                        # Supprimer l'overwrite (retour aux permissions héritées)
                        await channel.set_permissions(role, overwrite=None, reason=f"Permissions réinitialisées par {ctx.author}")
                    else:
                        await channel.set_permissions(role, overwrite=overwrite, reason=f"Permissions modifiées par {ctx.author}")
                    
                    success_embed = discord.Embed(
                        title="✅ Permissions Appliquées",
                        description=(
                            f"Les permissions ont été mises à jour avec succès!\n\n"
                            f"📍 **Salon:** {channel.mention}\n"
                            f"👥 **Rôle:** {role.mention}\n\n"
                            "**Permissions appliquées:**\n"
                            + "\n".join(selected_perms)
                        ),
                        color=discord.Color.green(),
                        timestamp=datetime.now()
                    )
                    success_embed.set_footer(text=f"Modifié par {ctx.author.name}", icon_url=ctx.author.avatar.url if ctx.author.avatar else None)
                    await ctx.send(embed=success_embed)
                    
                except discord.Forbidden:
                    await ctx.send("❌ Je n'ai pas la permission de modifier les permissions de ce salon.")
                except Exception as e:
                    await ctx.send(f"❌ Erreur lors de l'application des permissions: {e}")
            else:
                await ctx.send("❌ Aucune permission sélectionnée.")
        
        except asyncio.TimeoutError:
            await ctx.send("⏰ Temps écoulé. Opération annulée.")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # COMMANDE : VOIR LES PERMISSIONS D'UN SALON
    # ═══════════════════════════════════════════════════════════════════════════
    
    @commands.command(name="perms_view")
    @commands.has_permissions(manage_channels=True)
    async def perms_view(self, ctx, channel: discord.TextChannel = None):
        """
        👁️ Affiche les permissions configurées pour un salon.
        Usage: !perms_view #salon
        """
        channel = channel or ctx.channel
        
        embed = discord.Embed(
            title=f"🔐 Permissions de #{channel.name}",
            description=f"Permissions configurées pour {channel.mention}",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        
        # Compter les overwrites
        overwrites_count = len(channel.overwrites)
        
        if overwrites_count == 0:
            embed.add_field(
                name="📊 Statut",
                value="Aucune permission personnalisée configurée.\nToutes les permissions sont héritées.",
                inline=False
            )
        else:
            embed.add_field(
                name="📊 Statistiques",
                value=f"**{overwrites_count}** rôle(s)/membre(s) avec permissions personnalisées",
                inline=False
            )
            
            # Lister les overwrites (max 10)
            overwrites_list = []
            for target, overwrite in list(channel.overwrites.items())[:10]:
                if isinstance(target, discord.Role):
                    icon = "👥"
                    name = target.name
                else:
                    icon = "👤"
                    name = target.display_name
                
                perms = []
                if overwrite.view_channel is True:
                    perms.append("✅ Voir")
                elif overwrite.view_channel is False:
                    perms.append("🚫 Voir")
                
                if overwrite.send_messages is True:
                    perms.append("✅ Écrire")
                elif overwrite.send_messages is False:
                    perms.append("🚫 Écrire")
                
                if overwrite.connect is True:
                    perms.append("✅ Connecter")
                elif overwrite.connect is False:
                    perms.append("🚫 Connecter")
                
                perms_str = " • ".join(perms) if perms else "⚪ Héritées"
                overwrites_list.append(f"{icon} **{name}**\n└ {perms_str}")
            
            if overwrites_count > 10:
                overwrites_list.append(f"*...et {overwrites_count - 10} autre(s)*")
            
            embed.add_field(
                name="🔑 Permissions Personnalisées",
                value="\n\n".join(overwrites_list),
                inline=False
            )
        
        embed.add_field(
            name="💡 Commandes",
            value=(
                "`!perms_setup` - Configurer les permissions\n"
                "`!perms_copy` - Copier les permissions vers un autre salon\n"
                "`!perms_reset` - Réinitialiser les permissions"
            ),
            inline=False
        )
        
        embed.set_footer(text=f"Demandé par {ctx.author.name}", icon_url=ctx.author.avatar.url if ctx.author.avatar else None)
        await ctx.send(embed=embed)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # COMMANDE : COPIER LES PERMISSIONS
    # ═══════════════════════════════════════════════════════════════════════════
    
    @commands.command(name="perms_copy")
    @commands.has_permissions(manage_channels=True)
    async def perms_copy(self, ctx):
        """
        📋 Copie les permissions d'un salon vers un autre.
        """
        embed = discord.Embed(
            title="📋 Copie de Permissions",
            description=(
                "**Étape 1/2:** Salon source\n\n"
                "Mentionnez le salon DONT vous voulez copier les permissions."
            ),
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        await ctx.send(embed=embed)
        
        def check_msg(m):
            return m.author == ctx.author and m.channel == ctx.channel
        
        try:
            # Salon source
            msg = await self.bot.wait_for("message", timeout=60.0, check=check_msg)
            
            source_channel = None
            if msg.channel_mentions:
                source_channel = msg.channel_mentions[0]
            elif msg.content.isdigit():
                source_channel = ctx.guild.get_channel(int(msg.content))
            
            if not source_channel:
                await ctx.send("❌ Salon invalide.")
                return
            
            # Salon cible
            embed2 = discord.Embed(
                title="📋 Copie de Permissions",
                description=(
                    f"**Étape 2/2:** Salon cible\n\n"
                    f"📍 **Source:** {source_channel.mention}\n\n"
                    "Mentionnez le salon VERS lequel copier les permissions."
                ),
                color=discord.Color.blue(),
                timestamp=datetime.now()
            )
            await ctx.send(embed=embed2)
            
            msg = await self.bot.wait_for("message", timeout=60.0, check=check_msg)
            
            target_channel = None
            if msg.channel_mentions:
                target_channel = msg.channel_mentions[0]
            elif msg.content.isdigit():
                target_channel = ctx.guild.get_channel(int(msg.content))
            
            if not target_channel:
                await ctx.send("❌ Salon invalide.")
                return
            
            # Copier les permissions
            copied = 0
            for target, overwrite in source_channel.overwrites.items():
                try:
                    await target_channel.set_permissions(target, overwrite=overwrite, reason=f"Permissions copiées depuis #{source_channel.name} par {ctx.author}")
                    copied += 1
                except:
                    pass
            
            success_embed = discord.Embed(
                title="✅ Permissions Copiées",
                description=(
                    f"**{copied}** permission(s) copiée(s)\n\n"
                    f"📍 **De:** {source_channel.mention}\n"
                    f"📍 **Vers:** {target_channel.mention}"
                ),
                color=discord.Color.green(),
                timestamp=datetime.now()
            )
            await ctx.send(embed=success_embed)
        
        except asyncio.TimeoutError:
            await ctx.send("⏰ Temps écoulé.")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # COMMANDE : AIDE ROLES
    # ═══════════════════════════════════════════════════════════════════════════
    
    @commands.command(name="roles_help")
    async def roles_help(self, ctx):
        """
        📖 Affiche l'aide pour les commandes de gestion des rôles.
        """
        embed = discord.Embed(
            title="📖 Aide - Gestion des Rôles & Permissions",
            description="Commandes disponibles pour gérer la structure des rôles et permissions du serveur.",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        
        # Commandes de rôles
        embed.add_field(
            name="🎭 Gestion des Rôles",
            value=(
                "`!roles_preview` - Aperçu de la structure\n"
                "`!roles_current` - Liste des rôles actuels\n"
                "`!roles_create` - Créer les nouveaux rôles\n"
                "`!roles_reorder` - Réorganiser les positions\n"
                "`!roles_delete_old` - Supprimer les anciens\n"
                "`!roles_setup` - Setup complet\n"
                "`!roles_export` - Exporter les IDs"
            ),
            inline=False
        )
        
        # Commandes de permissions
        embed.add_field(
            name="🔐 Gestion des Permissions",
            value=(
                "`!perms_setup` - Configurer les permissions d'un salon\n"
                "`!perms_view [#salon]` - Voir les permissions d'un salon\n"
                "`!perms_copy` - Copier les permissions entre salons"
            ),
            inline=False
        )
        
        embed.set_footer(text="⚠️ Les commandes admin sont irréversibles!")
        await ctx.send(embed=embed)


async def setup(bot):
    """Setup pour discord.py 2.0+"""
    await bot.add_cog(RolesSetup(bot))
    logging.info("🔧 Cog RolesSetup chargé avec succès")