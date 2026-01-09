# community.py
# Système communautaire : Reviews, Théories, Interactions avec les chapitres
import discord
from discord.ext import commands
import json
import os
import asyncio
from datetime import datetime
from config import COLORS

# Fichiers de données
REVIEWS_FILE = "data/reviews.json"
THEORIES_FILE = "data/theories.json"
CHAPTERS_FILE = "data/chapters_community.json"
USER_STATS_FILE = "data/user_stats.json"
os.makedirs("data", exist_ok=True)

# Données en mémoire
reviews_data = {}
theories_data = {}
chapters_data = {}
user_stats = {}

# Emojis pour les notes
RATING_EMOJIS = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣"]
REACTION_EMOJIS = ["🔥", "😭", "😱", "🤯", "❤️", "😂", "💀"]

# Points gagnés par action
POINTS = {
    "review": 10,
    "theory": 15,
    "theory_vote": 2,
    "first_review": 25,
    "first_theory": 30,
}

def charger_donnees():
    """Charge toutes les données communautaires"""
    global reviews_data, theories_data, chapters_data, user_stats
    
    for file_path, data_dict, name in [
        (REVIEWS_FILE, reviews_data, "reviews"),
        (THEORIES_FILE, theories_data, "théories"),
        (CHAPTERS_FILE, chapters_data, "chapitres"),
        (USER_STATS_FILE, user_stats, "stats utilisateurs")
    ]:
        if os.path.exists(file_path):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    contenu = f.read().strip()
                    if contenu:
                        loaded = json.loads(contenu)
                        if name == "reviews":
                            reviews_data.update(loaded)
                        elif name == "théories":
                            theories_data.update(loaded)
                        elif name == "chapitres":
                            chapters_data.update(loaded)
                        elif name == "stats utilisateurs":
                            user_stats.update(loaded)
                print(f"✅ {name} chargé(s)")
            except Exception as e:
                print(f"❌ Erreur chargement {name}: {e}")

def sauvegarder_donnees():
    """Sauvegarde toutes les données"""
    try:
        with open(REVIEWS_FILE, "w", encoding="utf-8") as f:
            json.dump(reviews_data, f, ensure_ascii=False, indent=4)
        with open(THEORIES_FILE, "w", encoding="utf-8") as f:
            json.dump(theories_data, f, ensure_ascii=False, indent=4)
        with open(CHAPTERS_FILE, "w", encoding="utf-8") as f:
            json.dump(chapters_data, f, ensure_ascii=False, indent=4)
        with open(USER_STATS_FILE, "w", encoding="utf-8") as f:
            json.dump(user_stats, f, ensure_ascii=False, indent=4)
        print("✅ Données communautaires sauvegardées")
    except Exception as e:
        print(f"❌ Erreur sauvegarde: {e}")

def get_user_stats(user_id):
    """Récupère ou crée les stats d'un utilisateur"""
    user_id_str = str(user_id)
    if user_id_str not in user_stats:
        user_stats[user_id_str] = {
            "points": 0,
            "reviews_count": 0,
            "theories_count": 0,
            "theories_votes_given": 0,
            "theories_votes_received": 0,
            "badges": [],
            "joined_at": datetime.now().isoformat()
        }
    return user_stats[user_id_str]

def add_points(user_id, amount, reason=""):
    """Ajoute des points à un utilisateur"""
    stats = get_user_stats(user_id)
    stats["points"] += amount
    sauvegarder_donnees()
    return stats["points"]

def get_manga_emoji(manga_name):
    """Récupère l'emoji d'un manga"""
    emojis = {
        "ao no exorcist": "👹",
        "satsudou": "🩸",
        "tougen anki": "😈",
        "catenaccio": "⚽",
        "tokyo underworld": "🗼"
    }
    return emojis.get(manga_name.lower(), "📚")


class CommunitySystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        charger_donnees()
        
    # ==================== COMMANDES ADMIN ====================
    
    @commands.command(name="newchapter")
    @commands.has_any_role(1326417422663680090, 1330147432847114321)
    async def newchapter(self, ctx, message_id: int, manga: str, chapitre: str):
        """
        Lie une annonce de chapitre au système communautaire.
        Usage: !newchapter <message_id> <manga> <chapitre>
        Exemple: !newchapter 123456789 "Tougen Anki" 221
        """
        # Vérifier que le message existe
        try:
            target_message = await ctx.channel.fetch_message(message_id)
        except discord.NotFound:
            await ctx.send("❌ Message introuvable dans ce salon.")
            return
        except discord.HTTPException as e:
            await ctx.send(f"❌ Erreur lors de la récupération du message: {e}")
            return
        
        # Créer l'entrée du chapitre
        chapter_key = f"{manga.lower()}_{chapitre}"
        
        chapters_data[chapter_key] = {
            "manga": manga,
            "chapter": chapitre,
            "message_id": message_id,
            "channel_id": ctx.channel.id,
            "guild_id": ctx.guild.id,
            "created_at": datetime.now().isoformat(),
            "reviews": {},
            "reactions": {},
            "theories_linked": []
        }
        
        sauvegarder_donnees()
        
        # Créer l'embed d'interaction
        manga_emoji = get_manga_emoji(manga)
        
        embed = discord.Embed(
            title=f"{manga_emoji} {manga} - Chapitre {chapitre}",
            description=(
                "**📝 Partagez votre avis sur ce chapitre !**\n\n"
                f"⭐ **Noter** : `!review {manga} {chapitre} <1-5> [commentaire]`\n"
                f"💭 **Théorie** : `!theory {manga} <votre théorie>`\n"
                f"📊 **Voir les avis** : `!chapter_reviews {manga} {chapitre}`\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━"
            ),
            color=discord.Color.gold(),
            timestamp=datetime.now()
        )
        
        embed.add_field(
            name="📊 Statistiques",
            value="⭐ Note moyenne: --\n📝 Reviews: 0\n💭 Théories: 0",
            inline=True
        )
        
        embed.add_field(
            name="🏆 Points à gagner",
            value=f"+{POINTS['review']} pts (review)\n+{POINTS['first_review']} pts (1er review)",
            inline=True
        )
        
        embed.set_footer(text=f"ID: {chapter_key}")
        
        # Envoyer le message d'interaction
        interaction_msg = await ctx.send(embed=embed)
        
        # Ajouter les réactions rapides
        for emoji in REACTION_EMOJIS:
            await interaction_msg.add_reaction(emoji)
        
        # Sauvegarder l'ID du message d'interaction
        chapters_data[chapter_key]["interaction_message_id"] = interaction_msg.id
        sauvegarder_donnees()
        
        # Confirmation
        confirm_embed = discord.Embed(
            title="✅ Chapitre Lié !",
            description=f"Le chapitre **{chapitre}** de **{manga}** est maintenant lié au système communautaire.",
            color=discord.Color.green()
        )
        confirm_embed.add_field(name="🆔 Message d'annonce", value=f"`{message_id}`", inline=True)
        confirm_embed.add_field(name="🆔 Clé", value=f"`{chapter_key}`", inline=True)
        
        await ctx.send(embed=confirm_embed, delete_after=10)
    
    # ==================== REVIEWS ====================
    
    @commands.command(name="review")
    async def review(self, ctx, manga: str, chapitre: str, note: int, *, commentaire: str = None):
        """
        Laisse une review sur un chapitre.
        Usage: !review <manga> <chapitre> <note 1-5> [commentaire]
        """
        if note < 1 or note > 5:
            await ctx.send("❌ La note doit être entre 1 et 5.")
            return
        
        chapter_key = f"{manga.lower()}_{chapitre}"
        
        if chapter_key not in chapters_data:
            await ctx.send(f"❌ Chapitre introuvable. Assurez-vous que le chapitre a été lié avec `!newchapter`.")
            return
        
        user_id = str(ctx.author.id)
        is_first_review = len(chapters_data[chapter_key]["reviews"]) == 0
        already_reviewed = user_id in chapters_data[chapter_key]["reviews"]
        
        # Créer/mettre à jour la review
        chapters_data[chapter_key]["reviews"][user_id] = {
            "note": note,
            "commentaire": commentaire,
            "created_at": datetime.now().isoformat(),
            "username": ctx.author.name
        }
        
        # Ajouter aux reviews globales
        if chapter_key not in reviews_data:
            reviews_data[chapter_key] = {}
        reviews_data[chapter_key][user_id] = chapters_data[chapter_key]["reviews"][user_id]
        
        # Mettre à jour les stats utilisateur
        stats = get_user_stats(ctx.author.id)
        
        points_gagnes = 0
        if not already_reviewed:
            stats["reviews_count"] += 1
            points_gagnes = POINTS["review"]
            
            if is_first_review:
                points_gagnes = POINTS["first_review"]
        
        if points_gagnes > 0:
            add_points(ctx.author.id, points_gagnes)
        
        sauvegarder_donnees()
        
        # Calculer la moyenne
        reviews = chapters_data[chapter_key]["reviews"]
        moyenne = sum(r["note"] for r in reviews.values()) / len(reviews)
        
        # Créer l'embed de confirmation
        stars = "⭐" * note + "☆" * (5 - note)
        manga_emoji = get_manga_emoji(manga)
        
        embed = discord.Embed(
            title=f"{manga_emoji} Review Enregistrée !",
            description=f"**{manga}** - Chapitre {chapitre}",
            color=discord.Color.green(),
            timestamp=datetime.now()
        )
        
        embed.add_field(name="📊 Votre Note", value=stars, inline=True)
        embed.add_field(name="📈 Moyenne", value=f"⭐ {moyenne:.1f}/5 ({len(reviews)} avis)", inline=True)
        
        if commentaire:
            embed.add_field(name="💬 Commentaire", value=commentaire[:500], inline=False)
        
        if points_gagnes > 0:
            bonus_text = " (🎉 Premier review !)" if is_first_review else ""
            embed.add_field(name="🏆 Points Gagnés", value=f"+{points_gagnes} pts{bonus_text}", inline=False)
        
        embed.set_footer(text=f"Total: {stats['points']} points | {stats['reviews_count']} reviews")
        embed.set_thumbnail(url=ctx.author.avatar.url if ctx.author.avatar else None)
        
        await ctx.send(embed=embed)
        
        # Mettre à jour le message d'interaction si existant
        await self.update_chapter_embed(chapter_key)
    
    @commands.command(name="chapter_reviews")
    async def chapter_reviews(self, ctx, manga: str, chapitre: str):
        """Affiche toutes les reviews d'un chapitre"""
        chapter_key = f"{manga.lower()}_{chapitre}"
        
        if chapter_key not in chapters_data:
            await ctx.send(f"❌ Chapitre introuvable.")
            return
        
        chapter = chapters_data[chapter_key]
        reviews = chapter.get("reviews", {})
        
        manga_emoji = get_manga_emoji(manga)
        
        if not reviews:
            embed = discord.Embed(
                title=f"{manga_emoji} {manga} - Chapitre {chapitre}",
                description="Aucune review pour ce chapitre.\n\nSoyez le premier à donner votre avis !",
                color=discord.Color.blue()
            )
            embed.add_field(
                name="💡 Comment reviewer ?",
                value=f"`!review {manga} {chapitre} <note 1-5> [commentaire]`",
                inline=False
            )
            await ctx.send(embed=embed)
            return
        
        # Calculer les stats
        moyenne = sum(r["note"] for r in reviews.values()) / len(reviews)
        distribution = {i: 0 for i in range(1, 6)}
        for r in reviews.values():
            distribution[r["note"]] += 1
        
        embed = discord.Embed(
            title=f"{manga_emoji} {manga} - Chapitre {chapitre}",
            description=f"**⭐ Note Moyenne: {moyenne:.1f}/5** ({len(reviews)} avis)",
            color=discord.Color.gold(),
            timestamp=datetime.now()
        )
        
        # Distribution des notes
        dist_text = ""
        for i in range(5, 0, -1):
            bar_length = int((distribution[i] / len(reviews)) * 10) if reviews else 0
            bar = "█" * bar_length + "░" * (10 - bar_length)
            dist_text += f"{'⭐' * i}{'☆' * (5-i)} {bar} {distribution[i]}\n"
        
        embed.add_field(name="📊 Distribution", value=f"```{dist_text}```", inline=False)
        
        # Dernières reviews (max 5)
        recent_reviews = sorted(reviews.items(), key=lambda x: x[1]["created_at"], reverse=True)[:5]
        
        for user_id, review in recent_reviews:
            member = ctx.guild.get_member(int(user_id))
            name = member.display_name if member else review.get("username", "Inconnu")
            stars = "⭐" * review["note"]
            
            value = f"{stars}\n"
            if review.get("commentaire"):
                value += f"*\"{review['commentaire'][:100]}{'...' if len(review.get('commentaire', '')) > 100 else ''}\"*"
            else:
                value += "*Pas de commentaire*"
            
            embed.add_field(name=f"💬 {name}", value=value, inline=False)
        
        if len(reviews) > 5:
            embed.set_footer(text=f"Affichage des 5 dernières reviews sur {len(reviews)}")
        
        await ctx.send(embed=embed)
    
    # ==================== THÉORIES ====================
    
    @commands.command(name="theory")
    async def theory(self, ctx, manga: str, *, contenu: str):
        """
        Poste une théorie sur un manga.
        Usage: !theory <manga> <votre théorie>
        """
        if len(contenu) < 20:
            await ctx.send("❌ Votre théorie doit faire au moins 20 caractères.")
            return
        
        if len(contenu) > 1500:
            await ctx.send("❌ Votre théorie est trop longue (max 1500 caractères).")
            return
        
        manga_lower = manga.lower()
        user_id = str(ctx.author.id)
        
        # Créer l'ID unique de la théorie
        theory_id = f"theory_{int(datetime.now().timestamp())}_{user_id[:8]}"
        
        # Vérifier si c'est la première théorie du manga
        manga_theories = [t for t in theories_data.values() if t.get("manga", "").lower() == manga_lower]
        is_first = len(manga_theories) == 0
        
        # Créer la théorie
        theories_data[theory_id] = {
            "id": theory_id,
            "manga": manga,
            "author_id": user_id,
            "author_name": ctx.author.name,
            "contenu": contenu,
            "created_at": datetime.now().isoformat(),
            "votes_up": [],
            "votes_down": [],
            "status": "active",  # active, confirmed, debunked
            "channel_id": ctx.channel.id,
            "message_id": None
        }
        
        # Mettre à jour les stats
        stats = get_user_stats(ctx.author.id)
        stats["theories_count"] += 1
        
        points_gagnes = POINTS["first_theory"] if is_first else POINTS["theory"]
        add_points(ctx.author.id, points_gagnes)
        
        sauvegarder_donnees()
        
        # Créer l'embed de la théorie
        manga_emoji = get_manga_emoji(manga)
        
        embed = discord.Embed(
            title=f"💭 Nouvelle Théorie - {manga_emoji} {manga}",
            description=contenu,
            color=discord.Color.purple(),
            timestamp=datetime.now()
        )
        
        embed.add_field(name="👤 Auteur", value=ctx.author.mention, inline=True)
        embed.add_field(name="📊 Votes", value="👍 0 | 👎 0", inline=True)
        embed.add_field(name="🏷️ Statut", value="🔮 En attente", inline=True)
        
        bonus_text = " (🎉 Première théorie !)" if is_first else ""
        embed.add_field(name="🏆 Points", value=f"+{points_gagnes} pts{bonus_text}", inline=False)
        
        embed.set_footer(text=f"ID: {theory_id} | Votez avec 👍 ou 👎")
        embed.set_thumbnail(url=ctx.author.avatar.url if ctx.author.avatar else None)
        
        # Envoyer et ajouter les réactions
        theory_msg = await ctx.send(embed=embed)
        await theory_msg.add_reaction("👍")
        await theory_msg.add_reaction("👎")
        
        # Sauvegarder l'ID du message
        theories_data[theory_id]["message_id"] = theory_msg.id
        sauvegarder_donnees()
    
    @commands.command(name="theories")
    async def list_theories(self, ctx, manga: str = None):
        """Liste les théories (optionnel: filtrer par manga)"""
        if manga:
            filtered = {k: v for k, v in theories_data.items() 
                       if v.get("manga", "").lower() == manga.lower() and v.get("status") == "active"}
        else:
            filtered = {k: v for k, v in theories_data.items() if v.get("status") == "active"}
        
        if not filtered:
            msg = f"Aucune théorie trouvée" + (f" pour **{manga}**" if manga else "") + "."
            await ctx.send(f"❌ {msg}")
            return
        
        # Trier par score (votes up - votes down)
        sorted_theories = sorted(
            filtered.items(),
            key=lambda x: len(x[1].get("votes_up", [])) - len(x[1].get("votes_down", [])),
            reverse=True
        )[:10]
        
        title = f"💭 Théories" + (f" - {get_manga_emoji(manga)} {manga}" if manga else " Populaires")
        
        embed = discord.Embed(
            title=title,
            description=f"Top {len(sorted_theories)} théories les plus populaires",
            color=discord.Color.purple(),
            timestamp=datetime.now()
        )
        
        for i, (tid, theory) in enumerate(sorted_theories, 1):
            score = len(theory.get("votes_up", [])) - len(theory.get("votes_down", []))
            score_emoji = "🔥" if score >= 5 else "👍" if score >= 0 else "👎"
            
            manga_emoji = get_manga_emoji(theory.get("manga", ""))
            
            # Tronquer le contenu
            contenu = theory["contenu"][:100] + "..." if len(theory["contenu"]) > 100 else theory["contenu"]
            
            embed.add_field(
                name=f"{i}. {manga_emoji} {theory.get('manga', 'N/A')} | {score_emoji} {score}",
                value=f"*\"{contenu}\"*\n— {theory.get('author_name', 'Inconnu')} | `{tid[:20]}...`",
                inline=False
            )
        
        embed.set_footer(text="Utilisez !theory_info <id> pour plus de détails")
        await ctx.send(embed=embed)
    
    @commands.command(name="theory_info")
    async def theory_info(self, ctx, theory_id: str):
        """Affiche les détails d'une théorie"""
        # Recherche flexible de l'ID
        found_id = None
        for tid in theories_data.keys():
            if tid.startswith(theory_id) or theory_id in tid:
                found_id = tid
                break
        
        if not found_id:
            await ctx.send("❌ Théorie introuvable.")
            return
        
        theory = theories_data[found_id]
        manga_emoji = get_manga_emoji(theory.get("manga", ""))
        
        score = len(theory.get("votes_up", [])) - len(theory.get("votes_down", []))
        
        status_map = {
            "active": "🔮 En attente",
            "confirmed": "✅ Confirmée",
            "debunked": "❌ Réfutée"
        }
        
        embed = discord.Embed(
            title=f"💭 Théorie - {manga_emoji} {theory.get('manga', 'N/A')}",
            description=theory["contenu"],
            color=discord.Color.purple(),
            timestamp=datetime.fromisoformat(theory["created_at"])
        )
        
        author = ctx.guild.get_member(int(theory["author_id"]))
        author_name = author.mention if author else theory.get("author_name", "Inconnu")
        
        embed.add_field(name="👤 Auteur", value=author_name, inline=True)
        embed.add_field(name="📊 Score", value=f"👍 {len(theory.get('votes_up', []))} | 👎 {len(theory.get('votes_down', []))}", inline=True)
        embed.add_field(name="🏷️ Statut", value=status_map.get(theory.get("status", "active"), "🔮 En attente"), inline=True)
        
        embed.set_footer(text=f"ID: {found_id}")
        
        await ctx.send(embed=embed)
    
    @commands.command(name="theory_status")
    @commands.has_any_role(1326417422663680090, 1330147432847114321)
    async def theory_status(self, ctx, theory_id: str, status: str):
        """
        Change le statut d'une théorie (admin).
        Status: confirmed, debunked, active
        """
        valid_status = ["confirmed", "debunked", "active"]
        if status.lower() not in valid_status:
            await ctx.send(f"❌ Statut invalide. Choisissez parmi: {', '.join(valid_status)}")
            return
        
        # Recherche flexible
        found_id = None
        for tid in theories_data.keys():
            if tid.startswith(theory_id) or theory_id in tid:
                found_id = tid
                break
        
        if not found_id:
            await ctx.send("❌ Théorie introuvable.")
            return
        
        theories_data[found_id]["status"] = status.lower()
        sauvegarder_donnees()
        
        status_emoji = {"confirmed": "✅", "debunked": "❌", "active": "🔮"}
        await ctx.send(f"{status_emoji.get(status.lower(), '🔮')} Statut de la théorie mis à jour: **{status}**")
    
    # ==================== LISTENERS ====================
    
    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        """Gère les votes sur les théories"""
        if payload.user_id == self.bot.user.id:
            return
        
        emoji = str(payload.emoji)
        if emoji not in ["👍", "👎"]:
            return
        
        # Chercher si c'est une théorie
        for theory_id, theory in theories_data.items():
            if theory.get("message_id") == payload.message_id:
                user_id = str(payload.user_id)
                
                # Retirer l'ancien vote si existant
                if user_id in theory.get("votes_up", []):
                    theory["votes_up"].remove(user_id)
                if user_id in theory.get("votes_down", []):
                    theory["votes_down"].remove(user_id)
                
                # Ajouter le nouveau vote
                if emoji == "👍":
                    if "votes_up" not in theory:
                        theory["votes_up"] = []
                    theory["votes_up"].append(user_id)
                else:
                    if "votes_down" not in theory:
                        theory["votes_down"] = []
                    theory["votes_down"].append(user_id)
                
                # Donner des points au votant
                voter_stats = get_user_stats(payload.user_id)
                voter_stats["theories_votes_given"] += 1
                add_points(payload.user_id, POINTS["theory_vote"])
                
                # Donner des points à l'auteur si upvote
                if emoji == "👍":
                    author_stats = get_user_stats(int(theory["author_id"]))
                    author_stats["theories_votes_received"] += 1
                    add_points(int(theory["author_id"]), 1)
                
                sauvegarder_donnees()
                break
    
    # ==================== HELPERS ====================
    
    async def update_chapter_embed(self, chapter_key):
        """Met à jour l'embed d'interaction d'un chapitre"""
        if chapter_key not in chapters_data:
            return
        
        chapter = chapters_data[chapter_key]
        
        if "interaction_message_id" not in chapter:
            return
        
        try:
            channel = self.bot.get_channel(chapter["channel_id"])
            if not channel:
                return
            
            message = await channel.fetch_message(chapter["interaction_message_id"])
            
            reviews = chapter.get("reviews", {})
            moyenne = sum(r["note"] for r in reviews.values()) / len(reviews) if reviews else 0
            
            manga_emoji = get_manga_emoji(chapter["manga"])
            
            embed = discord.Embed(
                title=f"{manga_emoji} {chapter['manga']} - Chapitre {chapter['chapter']}",
                description=(
                    "**📝 Partagez votre avis sur ce chapitre !**\n\n"
                    f"⭐ **Noter** : `!review {chapter['manga']} {chapter['chapter']} <1-5> [commentaire]`\n"
                    f"💭 **Théorie** : `!theory {chapter['manga']} <votre théorie>`\n"
                    f"📊 **Voir les avis** : `!chapter_reviews {chapter['manga']} {chapter['chapter']}`\n\n"
                    "━━━━━━━━━━━━━━━━━━━━━━━━"
                ),
                color=discord.Color.gold(),
                timestamp=datetime.now()
            )
            
            stars = f"⭐ {moyenne:.1f}/5" if reviews else "⭐ --"
            embed.add_field(
                name="📊 Statistiques",
                value=f"{stars}\n📝 Reviews: {len(reviews)}\n💭 Théories: {len(chapter.get('theories_linked', []))}",
                inline=True
            )
            
            embed.add_field(
                name="🏆 Points à gagner",
                value=f"+{POINTS['review']} pts (review)\n+{POINTS['theory']} pts (théorie)",
                inline=True
            )
            
            embed.set_footer(text=f"ID: {chapter_key}")
            
            await message.edit(embed=embed)
            
        except Exception as e:
            print(f"❌ Erreur mise à jour embed: {e}")
    
    @commands.command(name="my_reviews")
    async def my_reviews(self, ctx):
        """Affiche vos reviews"""
        user_id = str(ctx.author.id)
        
        user_reviews = []
        for chapter_key, chapter in chapters_data.items():
            if user_id in chapter.get("reviews", {}):
                user_reviews.append({
                    "key": chapter_key,
                    "manga": chapter["manga"],
                    "chapter": chapter["chapter"],
                    "review": chapter["reviews"][user_id]
                })
        
        if not user_reviews:
            await ctx.send("❌ Vous n'avez pas encore laissé de review.")
            return
        
        embed = discord.Embed(
            title=f"📝 Vos Reviews",
            description=f"Vous avez laissé **{len(user_reviews)}** review(s)",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        
        for r in user_reviews[:10]:
            manga_emoji = get_manga_emoji(r["manga"])
            stars = "⭐" * r["review"]["note"]
            
            value = f"{stars}"
            if r["review"].get("commentaire"):
                value += f"\n*\"{r['review']['commentaire'][:50]}...\"*" if len(r["review"].get("commentaire", "")) > 50 else f"\n*\"{r['review']['commentaire']}\"*"
            
            embed.add_field(
                name=f"{manga_emoji} {r['manga']} Ch.{r['chapter']}",
                value=value,
                inline=True
            )
        
        embed.set_thumbnail(url=ctx.author.avatar.url if ctx.author.avatar else None)
        await ctx.send(embed=embed)


async def setup(bot):
    """Setup pour discord.py 2.0+"""
    await bot.add_cog(CommunitySystem(bot))
