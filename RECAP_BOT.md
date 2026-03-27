# LANORTRAD BOT - DOCUMENTATION COMPLETE

> Bot Discord pour la communaute de traduction manga LanorTrad
> `discord.py 2.4.0` | Prefix: `!` | Langue: Francais

---

## TABLE DES MATIERES

1. [Architecture & Fichiers](#architecture--fichiers)
2. [Configuration](#configuration)
3. [Commandes Publiques](#commandes-publiques)
4. [Commandes Admin](#commandes-admin)
5. [Systemes Automatiques](#systemes-automatiques)
6. [Donnees & Stockage](#donnees--stockage)
7. [Permissions & Roles](#permissions--roles)

---

## ARCHITECTURE & FICHIERS

### Modules Python (17 fichiers)

| Fichier | Cog/Classe | Description |
|---------|-----------|-------------|
| `main.py` | — | Point d'entree, charge tous les modules, serveur web health check (port 8080) |
| `config.py` | — | Configuration centralisee (IDs, constantes, emojis) |
| `commands.py` | — | Commandes de base (help, info, tasks, moderation, bulk roles) + menu help interactif |
| `community.py` | `CommunitySystem` | Systeme XP/niveaux, daily, mini-jeux (trivia, guess) |
| `achievements.py` | `Achievements` | Badges et recompenses |
| `planning.py` | `PlanningSystem` | Planning sorties chapitres (calendrier mensuel, batch status, auto-nettoyage) |
| `shop.py` | `Shop` | Boutique, inventaire, loterie hebdomadaire |
| `giveaway.py` | `GiveawayCog` | Giveaways bases sur les invitations |
| `stats.py` | `StatsDisplay` | Dashboard statistiques serveur |
| `announcements.py` | — | Annonces de chapitres |
| `rappels.py` | `RappelTask` | Rappels de deadlines (channel fixe ou DM selon preference utilisateur) |
| `role_selector.py` | `RoleSelector` | Selection de roles par boutons |
| `polls.py` | `Polls` | Systeme de sondages avance |
| `tickets.py` | `Tickets` | Candidatures et tickets support |
| `logs.py` | `AuditLogs` | Logs d'audit (join/leave/edit/delete/ban/voice) |
| `events.py` | — | Evenements (welcome, reglement, erreurs) |
| `database.py` | `Database` | Couche SQLite + migration JSON |
| `admin_data.py` | `DataManager` | Import/export/backup des donnees |
| `utils.py` | — | Fonctions utilitaires (pagination, embeds, JSON) |

### Ordre de chargement (main.py)

1. events (sync)
2. commands (sync)
3. announcements (sync)
4. rappels, giveaway, community, achievements, shop, admin_data, role_selector, logs, polls, tickets, stats, planning (async COGs)

### Dependances

```
discord.py==2.4.0
python-dotenv==1.0.1
pytz==2024.2
aiohttp==3.11.11
```

---

## CONFIGURATION

### Variables d'environnement (.env)

| Variable | Description |
|----------|-------------|
| `DISCORD_TOKEN` | Token du bot |
| `COMMAND_PREFIX` | Prefix (defaut: `!`) |
| `PORT` | Port health check (defaut: 8080) |

### IDs des Channels

| Channel | ID |
|---------|-----|
| Reglement | 1326211105332265001 |
| Bienvenue | 1326211276732502056 |
| General | 1326230396903362759 |
| Annonces chapitres | 1326213946188890142 |
| Planning | 1332363693174034472 |
| Rappels | 1431607377882382396 |
| Tickets | 1326357433588912179 |
| Contact modo | 1332088539076104192 |
| Logs/Test | 1330221808753840159 |
| Roles | 1326212401036529665 |
| Boost | 1326212624504848394 |
| Partenaires | 1326357401099702393 |

### Channels Manga

| Manga | Channel ID |
|-------|-----------|
| Tougen Anki | 1330144191816142941 |
| Tokyo Underworld | 1330143657264943266 |
| Satsudou | 1330142974646026371 |
| Ao No Exorcist | 1329589897920512020 |
| Catenaccio | 1330182024832614541 |

### Emojis Manga

| Manga | Emoji |
|-------|-------|
| Ao No Exorcist | 👹 |
| Satsudou | 🩸 |
| Tougen Anki | 😈 |
| Catenaccio | ⚽ |
| Tokyo Underworld | 🗼 |

### Roles Manga (pour ping)

| Manga | Role ID |
|-------|---------|
| Catenaccio | 1465027907968831541 |
| Satsudou | 1465027916999032976 |
| Ao No Exorcist | 1465027919951958220 |
| Tokyo Underworld | 1465027914050437184 |
| Tougen Anki | 1465027911235928155 |

### Couleurs

| Usage | Hex |
|-------|-----|
| Succes | `0x2ECC71` |
| Erreur | `0xE74C3C` |
| Info | `0x3498DB` |
| Warning | `0xF1C40F` |
| Boost | `0x9B59B6` |
| Giveaway | `0xff6b6b` |

---

## COMMANDES PUBLIQUES

### General

| Commande | Usage | Description |
|----------|-------|-------------|
| `!help` | `!help [commande]` | Menu d'aide interactif avec categories et emojis |
| `!info` | `!info` | Informations sur le serveur |
| `!userinfo` | `!userinfo [@membre]` | Details du profil d'un membre |
| `!ping` | `!ping` | Latence du bot (cooldown: 300s) |
| `!avancee` | `!avancee` | Avancee des chapitres manga (clean/trad/check/edit) |

### Communaute & XP

| Commande | Aliases | Description |
|----------|---------|-------------|
| `!xp` | `!points`, `!pts`, `!balance`, `!niveau`, `!level` | Voir son XP et niveau |
| `!profile` | `!profil` | Profil complet avec stats |
| `!leaderboard` | `!lb`, `!top` | Classement XP (paginable) |
| `!daily` | — | Bonus quotidien (20-50 XP + streak) |
| `!trivia` | — | Quiz manga (easy/medium/hard) |
| `!guess` | — | Jeu de devinette (30 XP) |

### Badges

| Commande | Aliases | Description |
|----------|---------|-------------|
| `!badges` | `!achievements`, `!mes_badges` | Voir les badges d'un membre |
| `!badge_info` | `!badgeinfo` | Details d'un badge |
| `!all_badges` | `!listbadges`, `!badges_list` | Liste tous les badges |
| `!badge_stats` | `!mystats` | Progression statistiques |
| `!leaderboard_badges` | `!top_badges` | Top collectionneurs |

### Boutique

| Commande | Aliases | Description |
|----------|---------|-------------|
| `!shop` | `!boutique`, `!magasin` | Parcourir la boutique |
| `!item_info` | `!shopinfo`, `!info_article` | Details d'un item |
| `!buy` | `!acheter` | Acheter un item |
| `!inventory` | `!inv`, `!inventaire` | Voir l'inventaire |
| `!use` | `!utiliser` | Utiliser un consommable |
| `!lottery` | `!loterie` | Infos loterie |

### Giveaways & Invitations

| Commande | Aliases | Description |
|----------|---------|-------------|
| `!invites` | `!myinvites` | Stats d'invitations |
| `!invites_leaderboard` | `!topinvites` | Classement invitations |
| `!glist` | `!giveaways` | Giveaways actifs |
| `!gstats` | `!giveaway_stats` | Statistiques giveaways |

### Planning

| Commande | Description |
|----------|-------------|
| `!planning` | Planning du mois en cours (tous les mangas) |
| `!planning [manga]` | Planning filtre par manga |

### Rappels

| Commande | Aliases | Description |
|----------|---------|-------------|
| `!rappel_pref` | `!rappel_preference`, `!pref_rappel` | Choisir ou recevoir ses rappels (channel ou DM) |

### Sondages

| Commande | Aliases | Description |
|----------|---------|-------------|
| `!poll` | — | Creer un sondage (rapide ou interactif) |
| `!poll_list` | `!polls`, `!list_polls` | Sondages actifs |
| `!poll_results` | `!poll_result` | Resultats d'un sondage |

### Statistiques

| Commande | Aliases | Description |
|----------|---------|-------------|
| `!serverstats` | `!sstats`, `!server_stats`, `!dashboard` | Dashboard multi-pages |
| `!membercount` | `!mc` | Nombre de membres rapide |
| `!topcontrib` | `!contributors`, `!top_contrib` | Top contributeurs |

---

## COMMANDES ADMIN

### Gestion des Taches (TASK_ROLES)

| Commande | Usage | Description |
|----------|-------|-------------|
| `!task` | `!task <action> <manga> <chap...>` | MAJ tache (clean/trad/check/edit) |
| `!claim` | `!claim <manga> <chap> <tache>` | Prendre une tache |
| `!unclaim` | `!unclaim <manga> <chap> <tache>` | Liberer une tache |
| `!task_status` | `!task_status <manga> <chap>` | Etat des taches d'un chapitre |
| `!task_all` | `!task_all [manga]` | Toutes les taches (filtrable) |
| `!delete_task` | `!delete_task <manga> <chap>` | Supprimer taches d'un chapitre |
| `!fix_tasks` | `!fix_tasks` | Normaliser les cles |
| `!actualiser` | `!actualiser` | Sauvegarder/exporter les donnees |

### Planning (TASK_ROLES)

| Commande | Aliases | Description |
|----------|---------|-------------|
| `!planning_add` | `!add_planning` | Ajouter sortie(s) — multi-chapitres (`220-222`, `220,221`) |
| `!planning_status` | `!planning_update` | Changer le statut (prevu/en_cours/trad_done/edit_done/check_done/pret/sorti/retarde) |
| `!planning_batch_status` | `!batch_status` | Changer le statut de plusieurs entrees d'un coup (par manga+chapitres ou par IDs) |
| `!planning_date` | `!planning_reschedule` | Modifier la date |
| `!planning_teaser` | `!planning_spoil`, `!teaser` | Ajouter/modifier teaser (spoiler) |
| `!planning_notes` | `!planning_note` | Ajouter/modifier les notes |
| `!planning_full` | `!planning_all`, `!planning_list` | Liste admin avec IDs |
| `!planning_post` | `!planning_refresh` | Forcer le rafraichissement des messages |

### Planning (ADMIN_ROLES)

| Commande | Aliases | Description |
|----------|---------|-------------|
| `!planning_remove` | `!planning_delete`, `!del_planning` | Supprimer une entree (avec confirmation) |

### Rappels (ADMIN_ROLES)

| Commande | Description |
|----------|-------------|
| `!add_rappel` | Creer un rappel (interactif: user, manga, chapitres, tache, deadline) |
| `!list_rappels` | Liste des rappels actifs (avec preference notif) |
| `!delete_rappel <id>` | Supprimer un rappel |
| `!test_rappel` | Tester l'envoi immediat |

### Giveaways (manage_guild / administrator)

| Commande | Aliases | Description |
|----------|---------|-------------|
| `!giveaway` | `!gstart`, `!gcreate` | Creer giveaway rapide |
| `!giveaway_advanced` | `!gadvanced` | Giveaway interactif avance |
| `!gend` | `!gstop` | Terminer un giveaway |
| `!greroll` | — | Retirer des gagnants |
| `!gdelete` | `!gcancel` | Supprimer un giveaway |
| `!addinvites` | — | Ajouter des invitations |
| `!resetinvites` | — | Reset invitations |

### Boutique (ADMIN_ROLES)

| Commande | Description |
|----------|-------------|
| `!shop_add` | Ajouter un item (interactif) |
| `!shop_remove <item>` | Supprimer un item |
| `!give_item @user <item>` | Donner un item |
| `!set_points @user <montant>` | Definir les points |

### Communaute (ADMIN_ROLES)

| Commande | Aliases | Description |
|----------|---------|-------------|
| `!give_xp` | `!give_points`, `!addxp` | Donner de l'XP |
| `!reset_xp` | `!reset_points` | Reset l'XP d'un membre |

### Badges (administrator)

| Commande | Description |
|----------|-------------|
| `!give_badge @user <nom>` | Attribuer un badge |
| `!remove_badge @user <nom>` | Retirer un badge |
| `!set_stat @user <stat> <valeur>` | Modifier une stat utilisateur |
| `!check_badges @user` | Verifier et attribuer badges gagnes |

### Annonces (ADMIN_ROLES)

| Commande | Description |
|----------|-------------|
| `!announce_chapter` | Annonce de chapitre (interactif) |
| `!test_announce` | Test dans channel de test |

### Sondages (ADMIN_ROLES)

| Commande | Aliases | Description |
|----------|---------|-------------|
| `!poll_close` | `!close_poll`, `!endpoll` | Fermer un sondage |
| `!poll_delete` | `!delete_poll` | Supprimer un sondage |

### Moderation (permissions Discord)

| Commande | Permission | Description |
|----------|-----------|-------------|
| `!clear <nb>` | manage_messages | Supprimer des messages |
| `!kick @user [raison]` | kick_members | Expulser |
| `!ban @user [raison]` | ban_members | Bannir |
| `!unban nom#tag` | ban_members | Debannir |
| `!warn @user [raison]` | kick_members | Avertir |

### Roles en masse (ADMIN_ROLES)

| Commande | Aliases | Description |
|----------|---------|-------------|
| `!bulk_role` | `!assign_roles` | Assigner role a plusieurs |
| `!multi_bulk_role` | `!assign_multi_roles` | Assigner plusieurs roles a plusieurs |
| `!bulk_remove_role` | `!remove_roles` | Retirer role de plusieurs |
| `!multi_bulk_remove_role` | `!remove_multi_roles` | Retirer plusieurs roles |
| `!bulk_role_channel` | `!assign_role_channel` | Assigner role aux membres d'un channel |
| `!multi_bulk_role_channel` | `!assign_multi_roles_channel` | Multi-roles aux membres d'un channel |
| `!list_member_ids` | `!get_ids`, `!member_ids` | Lister IDs des membres |

### Donnees (ADMIN_ROLES)

| Commande | Description |
|----------|-------------|
| `!data [action] [cible]` | Gestionnaire interactif de donnees |
| `!data_list` | Liste modules de donnees |
| `!backup` | Sauvegarde + export complet |

### Logs (ADMIN_ROLES)

| Commande | Description |
|----------|-------------|
| `!set_logs [channel]` | Definir le channel d'audit |
| `!audit_test` | Tester les logs d'audit |

### Tickets (ADMIN_ROLES)

| Commande | Description |
|----------|-------------|
| `!setup_tickets` | Configurer panneau tickets/candidatures |
| `!close_ticket` | Fermer un ticket |

### Roles (administrator)

| Commande | Description |
|----------|-------------|
| `!setup_roles [channel]` | Configurer panneau de selection de roles |
| `!sync_roles` | Verifier et lister roles manquants |
| `!roles_stats` | Statistiques attributions de roles |

---

## SYSTEMES AUTOMATIQUES

### Taches de fond (Background Tasks)

| Tache | Module | Intervalle | Description |
|-------|--------|-----------|-------------|
| `daily_planning_check` | planning.py | 1 heure | Refresh labels (minuit), notifs sorties (9h), auto-nettoyage entrees "sorti" > 30j |
| `check_rappels` | rappels.py | 1 minute | Envoi rappels quotidiens a 21h (Paris) dans channel ou DM selon pref |
| `check_giveaways` | giveaway.py | 30 secondes | Verifie et termine les giveaways expires |
| `poll_expiry_loop` | polls.py | 1 minute | Ferme les sondages expires |
| `weekly_lottery` | shop.py | 168 heures | Tirage loterie hebdomadaire |
| `check_expirations` | shop.py | 1 heure | Retire roles/boosts expires |
| `voice_check_loop` | community.py | 15 minutes | XP vocal (5 XP / 15 min en vocal) |
| `seniority_bonus_loop` | community.py | 24 heures | Bonus XP anciennete hebdomadaire (lundi) |

### Protection anti Rate-Limit Discord

Tous les modules respectent des delais entre appels API Discord pour eviter le Cloudflare Error 1015 (rate limit / ban temporaire IP) :

| Module | Operation | Delai entre appels |
|--------|-----------|--------------------|
| `planning.py` | Refresh messages (batch, cleanup, refresh) | 2s |
| `commands.py` | Bulk add/remove roles | 1.5s |
| `role_selector.py` | Envoi messages de selection | 1.5s |
| `shop.py` | Retrait roles expires + DM notification | 1.5s + 1s |
| `giveaway.py` | Fetch participants (fetch_member) | 1s |
| `community.py` | Annonce level-up (voice + anciennete) | 1.5s |
| `polls.py` | Traitement polls expires | 2s |
| `events.py` | Erreur 429 (rate limit) : attente automatique | retry_after |

### Evenements Discord

| Evenement | Module | Action |
|-----------|--------|--------|
| `on_ready` | events.py | Status "!help pour les commandes" + webserver |
| `on_ready` | giveaway.py | Restore views + init invitations |
| `on_member_join` | events.py | Message de bienvenue + log |
| `on_member_join` | giveaway.py | Tracking invitations |
| `on_member_remove` | logs.py | Log de depart |
| `on_member_remove` | giveaway.py | Tracking depart invites |
| `on_member_ban` | logs.py | Log de ban |
| `on_member_unban` | logs.py | Log de deban |
| `on_member_update` | logs.py | Log changements roles |
| `on_raw_reaction_add` | events.py | Acceptation reglement (reaction → roles member + access) |
| `on_message` | community.py | Gain XP (1-3 XP, cooldown 60s, channels autorises) |
| `on_message` | achievements.py | Tracking messages pour badges sociaux |
| `on_message` | events.py | Gestion pings partenaires (cooldown) |
| `on_message_delete` | logs.py | Log dans channel logs |
| `on_bulk_message_delete` | logs.py | Log suppressions en masse |
| `on_voice_state_update` | logs.py | Log mouvements vocaux |
| `on_guild_channel_create` | logs.py | Log creation channels |
| `on_guild_channel_delete` | logs.py | Log suppression channels |
| `on_command_error` | events.py | Gestion globale des erreurs + handling 429 rate limit |

---

## SYSTEME XP & NIVEAUX

### Sources d'XP

| Source | XP | Conditions |
|--------|-----|-----------|
| Message | 1-3 | Cooldown 60s, channels autorises |
| Daily bonus | 20-50 | 1x/jour, +5/jour de streak (max +50) |
| Vocal | 5 | Par tranche de 15 min |
| Reaction chapitre | 10 | Sur annonces |
| Trivia (easy) | 20 | Bonne reponse |
| Trivia (medium) | 50 | Bonne reponse |
| Trivia (hard) | 100 | Bonne reponse |
| Guess | 30 | Bonne reponse |
| Anciennete | 50-200 | Bonus hebdomadaire |

### Calcul de niveau

- Base: 100 XP pour niveau 1
- Croissance: 1.15x par niveau
- Max: 100
- Formule: `XP_requis(n) = 100 * 1.15^(n-1)`

---

## SYSTEME DE PLANNING

### Statuts

| Cle | Emoji | Label | Couleur |
|-----|-------|-------|---------|
| `prevu` | 📅 | Prevu | Bleu |
| `en_cours` | 🔄 | En cours | Orange |
| `trad_done` | 🌍 | Trad terminee | Violet |
| `edit_done` | ✏️ | Edit termine | Orange |
| `check_done` | ✅ | Check termine | Vert |
| `pret` | 🚀 | Pret a sortir | Turquoise |
| `sorti` | 📢 | Sorti | Vert |
| `retarde` | ⚠️ | Retarde | Rouge |

### Fonctionnalites

- **1 message par manga par mois** dans #planning (delete + recreate a chaque modif)
- **Calendrier ASCII** avec marqueurs jour courant et jours de sortie
- **Barre de progression** globale par manga/mois
- **Batch status** : modifier plusieurs entrees d'un coup (par manga + chapitres `47-54` ou par IDs)
- **Auto-nettoyage** : entrees "sorti" > 30 jours supprimees automatiquement
- **Multi-embeds** : si contenu > 4096 chars, split en plusieurs embeds
- **Recherche fuzzy** : resolution ID par nom partiel, chapitre, tolerant accents/casse
- **Confirmation suppression** : boutons Confirmer/Annuler avant suppression

### Format chapitres multiples

| Format | Exemple | Resultat |
|--------|---------|----------|
| Unique | `220` | [220] |
| Liste | `220,221,222` | [220, 221, 222] |
| Plage | `220-222` | [220, 221, 222] |
| Mixte | `220,223,225-227` | [220, 223, 225, 226, 227] |

---

## SYSTEME DE RAPPELS

### Fonctionnalites

- **Preference par utilisateur** : chaque personne choisit channel fixe ou DM
- **Channel fixe** : tous les rappels channel vont dans #rappels (1431607377882382396)
- **Fallback** : si DMs fermes, fallback automatique vers le channel
- **Bouton "Marquer comme fait"** : met a jour le statut de la tache directement
- **Envoi quotidien** a 21h (heure de Paris)
- **Indicateurs d'urgence** : rouge (J-1), jaune (J-3), vert (> J-3)
- **Preferences stockees** dans `data/rappels_prefs.json`

---

## SYSTEME DE BADGES

### Raretes

| Rarete | Couleur |
|--------|---------|
| Common | `0x9e9e9e` (gris) |
| Uncommon | `0x4caf50` (vert) |
| Rare | `0x2196f3` (bleu) |
| Epic | `0x9c27b0` (violet) |
| Legendary | `0xff9800` (orange) |

---

## BOUTIQUE & LOTERIE

### Types d'items

| Type | Description |
|------|-------------|
| Role | Roles VIP temporaires (duree en jours) |
| Consommable | Boosters XP, cosmetiques |
| Ticket loterie | Pour participer au tirage hebdomadaire |
| Mystery box | Boite aleatoire (loot tables) |

---

## DONNEES & STOCKAGE

### Fichiers JSON (`data/`)

| Fichier | Description |
|---------|-------------|
| `etat_taches.json` | Statuts des taches (clean/trad/check/edit) |
| `etat_taches_meta.json` | Metadata des taches |
| `rappels_tasks.json` | Rappels de deadlines |
| `rappels_tasks_meta.json` | Metadata des rappels |
| `rappels_prefs.json` | Preferences notification rappels (channel/dm) |
| `user_stats.json` | XP, niveaux, activite des membres |
| `chapters_community.json` | Suivi reactions chapitres |
| `shop_items.json` | Items de la boutique |
| `shop_inventory.json` | Inventaires des utilisateurs |
| `purchases.json` | Historique d'achats |
| `lottery.json` | Donnees loterie hebdomadaire |
| `user_badges.json` | Badges des utilisateurs |
| `badges_config.json` | Configuration des badges |
| `giveaways.json` | Giveaways actifs et termines |
| `invites_tracker.json` | Suivi des invitations |
| `polls.json` | Sondages actifs |
| `planning.json` | Planning des sorties |
| `planning_meta.json` | Metadata du planning |
| `planning_messages.json` | IDs messages planning Discord |
| `dm_reminder_notified.json` | Suivi DM rappels roles |

### Base de donnees SQLite

**Fichier**: `data/lanortrad.db`

**Tables**: tasks, user_stats, polls, reminders, giveaways, user_badges, user_inventory, purchases, audit_log

---

## PERMISSIONS & ROLES

### ADMIN_ROLES (3 IDs)

```
1465027983445331990
1465027980974620833
1465027978324086846
```

Acces a toutes les commandes admin.

### TASK_ROLES

```
ADMIN_ROLES + 1465027945189081113 (staff)
```

Acces aux commandes de taches et planning.

### Roles speciaux

| Role | ID | Description |
|------|-----|-------------|
| Member | 1465027926054535324 | Attribue apres acceptation reglement |
| Access | 1465027850120986967 | Acces aux channels |
| Booster | 1335403910113923162 | Serveur boosters |

---

## SELECTION DE ROLES (Boutons interactifs)

### Mangas

| Bouton | Role |
|--------|------|
| 🔥 Ao No Exorcist | Role manga |
| ⚔️ Satsudou | Role manga |
| 🏙️ Tokyo Underworld | Role manga |
| 👹 Tougen Anki | Role manga |
| ⚽ Catenaccio | Role manga |

### Notifications

| Bouton | Role |
|--------|------|
| 📢 Annonces | annonces |
| 🎉 Evenements | evenements |
| 🎁 Giveaway | giveaway |
| 💛 Partenaires | partenaires_ping |
| 🐦 Twittos | twittos |
| 🎵 Tiktok | tiktok |
| 👀 Spoilers | spoilers |

### Communaute

| Bouton | Role |
|--------|------|
| 🎨 Artiste | artiste |
| 📚 Collectionneurs | collectionneurs |
| 🎧 Musique | musique |
| 📷 Photographie | photographie |
| 🎮 Jeux video | jeux_video |

---

## RESUME DES NOMBRES

| Element | Nombre |
|---------|--------|
| Fichiers Python | 17 |
| Commandes publiques | ~35 |
| Commandes admin | ~45 |
| Background tasks | 8 |
| Event listeners | 18+ |
| Fichiers de donnees | 20 JSON + 1 SQLite |
| Mangas geres | 5 |
| Roles selectionnables | 17 |
| Statuts de badge | 5 (Common → Legendary) |
| Statuts de planning | 8 |

---

*Derniere mise a jour: 27 Mars 2026*
