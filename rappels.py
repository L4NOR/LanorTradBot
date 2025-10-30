# rappels.py
import discord
from discord.ext import commands, tasks
from datetime import datetime, time, timedelta
import json
import os
import logging
import asyncio

RAPPELS_FILE = "data/rappels.json"
RAPPELS_CHANNEL_ID = 1431607377882382396

# Structure pour stocker les rappels
rappels_actifs = {}

def charger_rappels():
    """Charge les rappels depuis le fichier JSON"""
    global rappels_actifs
    if os.path.exists(RAPPELS_FILE):
        try:
            with open(RAPPELS_FILE, "r", encoding="utf-8") as f:
                rappels_actifs = json.load(f)
                # Convertir les dates string en datetime pour la compatibilité
                for rappel_id, rappel in rappels_actifs.items():
                    if isinstance(rappel.get('date_fin'), str):
                        rappel['date_fin'] = rappel['date_fin']
                    if isinstance(rappel.get('derniere_notification'), str):
                        rappel['derniere_notification'] = rappel['derniere_notification']
            logging.info(f"✅ {len(rappels_actifs)} rappel(s) chargé(s)")
        except Exception as e:
            logging.error(f"Erreur lors du chargement des rappels: {e}")
            rappels_actifs = {}
    else:
        rappels_actifs = {}

def sauvegarder_rappels():
    """Sauvegarde les rappels dans le fichier JSON"""
    try:
        with open(RAPPELS_FILE, "w", encoding="utf-8") as f:
            json.dump(rappels_actifs, f, ensure_ascii=False, indent=4)
        logging.info("💾 Rappels sauvegardés")
    except Exception as e:
        logging.error(f"Erreur lors de la sauvegarde des rappels: {e}")

def generer_id_rappel():
    """Génère un ID unique pour un rappel"""
    if not rappels_actifs:
        return "rappel_1"
    
    ids_existants = [int(r.split('_')[1]) for r in rappels_actifs.keys()]
    return f"rappel_{max(ids_existants) + 1}"

def parser_date(date_str):
    """Parse une date au format JJ/MM ou JJ/MM/AAAA"""
    try:
        # Essayer d'abord JJ/MM/AAAA
        if date_str.count('/') == 2:
            return datetime.strptime(date_str, "%d/%m/%Y")
        # Sinon JJ/MM (année courante)
        else:
            date = datetime.strptime(date_str, "%d/%m")
            date = date.replace(year=datetime.now().year)
            # Si la date est passée, prendre l'année suivante
            if date < datetime.now():
                date = date.replace(year=datetime.now().year + 1)
            return date
    except ValueError:
        return None

def setup(bot):
    """Configure le système de rappels"""
    charger_rappels()
    
    @bot.command(name="set_rappel")
    @commands.has_any_role(1326417422663680090, 1330147432847114321)
    async def set_rappel(ctx, tache: str, manga: str, chapitre: str, user: discord.Member, date_fin: str):
        """
        Crée un rappel pour une tâche
        Usage: !set_rappel trad "Catenaccio" 45 @user 15/10
        """
        taches_valides = ["clean", "trad", "check", "edit", "release"]
        
        if tache.lower() not in taches_valides:
            await ctx.send(f"❌ Tâche invalide. Tâches possibles : {', '.join(taches_valides)}")
            return
        
        # Parser la date
        date_parsed = parser_date(date_fin)
        if not date_parsed:
            await ctx.send("❌ Format de date invalide. Utilisez JJ/MM ou JJ/MM/AAAA")
            return
        
        # Vérifier que la date est dans le futur
        if date_parsed < datetime.now():
            await ctx.send("❌ La date doit être dans le futur")
            return
        
        # Créer le rappel
        rappel_id = generer_id_rappel()
        rappels_actifs[rappel_id] = {
            "tache": tache.lower(),
            "manga": manga,
            "chapitre": chapitre,
            "user_id": user.id,
            "user_name": str(user),
            "date_fin": date_parsed.strftime("%Y-%m-%d"),
            "date_creation": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "createur_id": ctx.author.id,
            "createur_name": str(ctx.author),
            "derniere_notification": None
        }
        
        sauvegarder_rappels()
        
        embed = discord.Embed(
            title="⏰ Rappel créé avec succès",
            description=f"Un rappel a été configuré pour {user.mention}",
            color=discord.Color.green(),
            timestamp=datetime.now()
        )
        embed.add_field(name="📋 Tâche", value=tache.upper(), inline=True)
        embed.add_field(name="📚 Manga", value=manga, inline=True)
        embed.add_field(name="📖 Chapitre", value=chapitre, inline=True)
        embed.add_field(name="👤 Assigné à", value=user.mention, inline=True)
        embed.add_field(name="📅 Date limite", value=date_parsed.strftime("%d/%m/%Y"), inline=True)
        embed.add_field(name="🆔 ID Rappel", value=f"`{rappel_id}`", inline=True)
        embed.add_field(
            name="🔔 Notifications",
            value="Le bot enverra des rappels quotidiens à 12h00, 16h00 et 20h00",
            inline=False
        )
        embed.set_footer(text=f"Créé par {ctx.author.name}")
        
        await ctx.send(embed=embed)
        
        # Notification initiale dans le canal des rappels
        rappel_channel = bot.get_channel(RAPPELS_CHANNEL_ID)
        if rappel_channel:
            await rappel_channel.send(
                f"🔔 **Nouveau rappel créé**\n"
                f"{user.mention} tu as été assigné(e) à la tâche **{tache.upper()}** "
                f"pour **{manga}** chapitre **{chapitre}**.\n"
                f"📅 Date limite : **{date_parsed.strftime('%d/%m/%Y')}**"
            )
    
    @bot.command(name="list_rappels")
    @commands.has_any_role(1326417422663680090, 1330147432847114321)
    async def list_rappels(ctx):
        """Affiche la liste de tous les rappels actifs"""
        if not rappels_actifs:
            await ctx.send("📭 Aucun rappel actif actuellement")
            return
        
        embed = discord.Embed(
            title="📋 Liste des Rappels Actifs",
            description=f"Il y a actuellement **{len(rappels_actifs)}** rappel(s) actif(s)",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        
        for rappel_id, rappel in rappels_actifs.items():
            date_fin = datetime.strptime(rappel['date_fin'], "%Y-%m-%d")
            jours_restants = (date_fin - datetime.now()).days
            
            status_emoji = "🟢" if jours_restants > 3 else "🟡" if jours_restants > 1 else "🔴"
            
            field_value = (
                f"**Tâche:** {rappel['tache'].upper()}\n"
                f"**Manga:** {rappel['manga']}\n"
                f"**Chapitre:** {rappel['chapitre']}\n"
                f"**Assigné à:** <@{rappel['user_id']}>\n"
                f"**Date limite:** {date_fin.strftime('%d/%m/%Y')}\n"
                f"**Jours restants:** {jours_restants} jour(s) {status_emoji}\n"
                f"**ID:** `{rappel_id}`"
            )
            
            embed.add_field(
                name=f"⏰ {rappel['manga']} - Ch.{rappel['chapitre']}",
                value=field_value,
                inline=False
            )
        
        embed.set_footer(text=f"Demandé par {ctx.author.name}")
        await ctx.send(embed=embed)
    
    @bot.command(name="delete_rappel")
    @commands.has_any_role(1326417422663680090, 1330147432847114321)
    async def delete_rappel(ctx, rappel_id: str):
        """
        Supprime un rappel
        Usage: !delete_rappel rappel_1
        """
        if rappel_id not in rappels_actifs:
            await ctx.send(f"❌ Aucun rappel trouvé avec l'ID `{rappel_id}`")
            return
        
        rappel = rappels_actifs[rappel_id]
        del rappels_actifs[rappel_id]
        sauvegarder_rappels()
        
        embed = discord.Embed(
            title="🗑️ Rappel supprimé",
            description=f"Le rappel `{rappel_id}` a été supprimé avec succès",
            color=discord.Color.red(),
            timestamp=datetime.now()
        )
        embed.add_field(name="📋 Tâche", value=rappel['tache'].upper(), inline=True)
        embed.add_field(name="📚 Manga", value=rappel['manga'], inline=True)
        embed.add_field(name="📖 Chapitre", value=rappel['chapitre'], inline=True)
        
        await ctx.send(embed=embed)
    
    @bot.command(name="info_rappel")
    @commands.has_any_role(1326417422663680090, 1330147432847114321)
    async def info_rappel(ctx, rappel_id: str):
        """
        Affiche les détails d'un rappel spécifique
        Usage: !info_rappel rappel_1
        """
        if rappel_id not in rappels_actifs:
            await ctx.send(f"❌ Aucun rappel trouvé avec l'ID `{rappel_id}`")
            return
        
        rappel = rappels_actifs[rappel_id]
        date_fin = datetime.strptime(rappel['date_fin'], "%Y-%m-%d")
        date_creation = datetime.strptime(rappel['date_creation'], "%Y-%m-%d %H:%M:%S")
        jours_restants = (date_fin - datetime.now()).days
        
        embed = discord.Embed(
            title=f"ℹ️ Informations - {rappel_id}",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        
        embed.add_field(name="📋 Tâche", value=rappel['tache'].upper(), inline=True)
        embed.add_field(name="📚 Manga", value=rappel['manga'], inline=True)
        embed.add_field(name="📖 Chapitre", value=rappel['chapitre'], inline=True)
        embed.add_field(name="👤 Assigné à", value=f"<@{rappel['user_id']}>", inline=True)
        embed.add_field(name="📅 Date limite", value=date_fin.strftime('%d/%m/%Y'), inline=True)
        embed.add_field(name="⏳ Jours restants", value=f"{jours_restants} jour(s)", inline=True)
        embed.add_field(name="📆 Créé le", value=date_creation.strftime('%d/%m/%Y à %H:%M'), inline=True)
        embed.add_field(name="👨‍💼 Créé par", value=f"<@{rappel['createur_id']}>", inline=True)
        
        if rappel['derniere_notification']:
            embed.add_field(
                name="🔔 Dernier rappel",
                value=rappel['derniere_notification'],
                inline=True
            )
        
        await ctx.send(embed=embed)
    
    @tasks.loop(minutes=1)
    async def verifier_rappels():
        """Vérifie et envoie les rappels aux heures définies"""
        now = datetime.now()
        current_time = now.time()
        
        # Heures de notification : 12h00, 16h00, 20h00 (avec marge de 1 minute)
        heures_notification = [
            time(12, 0),
            time(16, 0),
            time(20, 0)
        ]
        
        # Vérifier si on est à une heure de notification (avec marge de 1 minute)
        is_notification_time = any(
            abs((datetime.combine(now.date(), current_time) - 
                 datetime.combine(now.date(), heure)).total_seconds()) < 60
            for heure in heures_notification
        )
        
        if not is_notification_time:
            return
        
        rappel_channel = bot.get_channel(RAPPELS_CHANNEL_ID)
        if not rappel_channel:
            logging.error(f"❌ Canal de rappels {RAPPELS_CHANNEL_ID} introuvable")
            return
        
        rappels_a_supprimer = []
        
        for rappel_id, rappel in rappels_actifs.items():
            date_fin = datetime.strptime(rappel['date_fin'], "%Y-%m-%d")
            
            # Vérifier si la date est dépassée
            if date_fin.date() < now.date():
                rappels_a_supprimer.append(rappel_id)
                await rappel_channel.send(
                    f"⚠️ **RAPPEL EXPIRÉ**\n"
                    f"<@{rappel['user_id']}> La date limite pour la tâche **{rappel['tache'].upper()}** "
                    f"de **{rappel['manga']}** chapitre **{rappel['chapitre']}** est dépassée !\n"
                    f"📅 Date limite était le : **{date_fin.strftime('%d/%m/%Y')}**"
                )
                continue
            
            # Vérifier si on a déjà notifié aujourd'hui à cette heure
            derniere_notif = rappel.get('derniere_notification')
            if derniere_notif:
                derniere_notif_dt = datetime.strptime(derniere_notif, "%Y-%m-%d %H:%M:%S")
                # Si la dernière notification est aujourd'hui à la même heure, skip
                if (derniere_notif_dt.date() == now.date() and 
                    abs((derniere_notif_dt.time().hour - current_time.hour)) < 1):
                    continue
            
            jours_restants = (date_fin - now).days
            
            # Déterminer l'urgence
            if jours_restants == 0:
                urgence = "🔴 **URGENT - AUJOURD'HUI**"
            elif jours_restants == 1:
                urgence = "🟠 **URGENT - DEMAIN**"
            elif jours_restants <= 3:
                urgence = "🟡 **Attention - Bientôt**"
            else:
                urgence = "🟢 En cours"
            
            # Envoyer le rappel
            await rappel_channel.send(
                f"🔔 **RAPPEL QUOTIDIEN**\n"
                f"{urgence}\n\n"
                f"<@{rappel['user_id']}> N'oublie pas ta tâche !\n\n"
                f"📋 **Tâche:** {rappel['tache'].upper()}\n"
                f"📚 **Manga:** {rappel['manga']}\n"
                f"📖 **Chapitre:** {rappel['chapitre']}\n"
                f"📅 **Date limite:** {date_fin.strftime('%d/%m/%Y')}\n"
                f"⏳ **Jours restants:** {jours_restants} jour(s)\n\n"
                f"💪 Continue comme ça !"
            )
            
            # Mettre à jour la dernière notification
            rappels_actifs[rappel_id]['derniere_notification'] = now.strftime("%Y-%m-%d %H:%M:%S")
        
        # Supprimer les rappels expirés
        for rappel_id in rappels_a_supprimer:
            del rappels_actifs[rappel_id]
        
        if rappels_a_supprimer:
            sauvegarder_rappels()
    
    @verifier_rappels.before_loop
    async def before_verifier_rappels():
        """Attend que le bot soit prêt avant de démarrer la tâche"""
        await bot.wait_until_ready()
        logging.info("✅ Système de rappels démarré")
    
    # Démarrer la tâche de vérification
    verifier_rappels.start()
    
    logging.info("✅ Module de rappels chargé")