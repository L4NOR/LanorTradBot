# LANORTRAD BOT - DOCUMENTATION COMPLETE

> Bot Discord pour la communauté de traduction manga LanorTrad
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

### Modules Python (16 fichiers)

| Fichier | Cog/Classe | Description |
|---------|-----------|-------------|
| `main.py` | — | Point d'entree, charge tous les modules, serveur web health check (port 8080) |
| `config.py` | — | Configuration centralisee (IDs, constantes, emojis) |
| `commands.py` | — | Commandes de base (help, info, tasks, avancee) + menu help interactif |
| `community.py` | `CommunityCog` | Systeme XP/niveaux, daily, mini-jeux (trivia, guess) |
| `achievements.py` | `Achievements` | Badges et recompenses |
| `planning.py` | `PlanningSystem` | Planning sorties chapitres (calendrier mensuel) |
| `shop.py` | `Shop` | Boutique, inventaire, loterie hebdomadaire |
| `giveaway.py` | `GiveawayCog` | Giveaways bases sur les invitations |
| `stats.py` | `ServerStats` | Dashboard statistiques serveur |
| `announcements.py` | — | Annonces de chapitres |
| `rappels.py` | `Rappels` | Rappels de deadlines pour les taches |
| `role_selector.py` | `RoleSelector` | Selection de roles par boutons |
| `polls.py` | `Polls` | Systeme de sondages avance |
| `tickets.py` | `Tickets` | Candidatures et tickets support |
| `logs.py` | `AuditLog` | Logs d'audit (join/leave/edit/delete) |
| `github_sync.py` | `GitHubSync` | Sync automatique des donnees vers GitHub |
| `events.py` | — | Evenements (welcome, reglement) |
| `database.py` | `Database` | Couche SQLite + migration JSON |
| `admin_data.py` | `AdminData` | Import/export des donnees |
| `utils.py` | — | Fonctions utilitaires (pagination, embeds, JSON) |

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
| `GITHUB_TOKEN` | Token pour sync GitHub |
| `GITHUB_REPO_URL` | URL du repo |
| `GITHUB_BRANCH` | Branche (defaut: main) |

### IDs des Channels

| Channel | ID |
|---------|-----|
| Reglement | 1326211105332265001 |
| Bienvenue | 1326211276732502056 |
| General | 1326230396903362759 |
| Annonces chapitres | 1326213946188890142 |
| Planning | 1332363693174034472 |
| Tickets | 1326357433588912179 |
| Contact modo | 1332088539076104192 |
| Logs | 1330221808753840159 |

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

### Roles Notification

| Role | ID |
|------|-----|
| Annonces | 1465027871339708439 |
| Evenements | 1465027869196423239 |
| Giveaway | 1465027866826772785 |
| Partenaires | 1465027864318447658 |

### Couleurs

| Usage | Hex |
|-------|-----|
| Succes | `0x2ECC71` |
| Erreur | `0xE74C3C` |
| Info | `0x3498DB` |
| Warning | `0xF1C40F` |
| Boost | `0x9B59B6` |

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
| `!trivia` | — | Quiz manga (easy/medium/hard → 20/50/100 XP) |
| `!guess` | — | Jeu de devinette (30 XP) |

### Badges

| Commande | Description |
|----------|-------------|
| `!badges [@membre]` | Voir les badges d'un membre |
| `!all_badges` | Liste tous les badges disponibles |
| `!badge_info <nom>` | Details d'un badge |
| `!display_badge <nom>` | Afficher un badge (max 3) |
| `!remove_badge <nom>` | Retirer un badge affiche |
| `!leaderboard_badges` | Top collectionneurs |

### Boutique

| Commande | Description |
|----------|-------------|
| `!shop [categorie]` | Parcourir la boutique |
| `!buy <item>` | Acheter un item |
| `!inventory [@membre]` | Voir l'inventaire |
| `!use <item>` | Utiliser un consommable |

### Giveaways & Invitations

| Commande | Aliases | Description |
|----------|---------|-------------|
| `!my_invites` | — | Stats d'invitations |
| `!leaderboard_invites` | — | Classement invitations |
| `!list_giveaways` | — | Giveaways actifs |
| `!giveaway_info <id>` | — | Details d'un giveaway |

### Planning

| Commande | Aliases | Description |
|----------|---------|-------------|
| `!planning [mois] [annee]` | — | Calendrier mensuel des sorties |
| `!planning_full` | `!planning_all` | Planning complet (passe + futur) |
| `!next_release` | `!prochaine_sortie`, `!next` | Prochaine sortie prevue |

### Statistiques

| Commande | Aliases | Description |
|----------|---------|-------------|
| `!serverstats` | `!sstats`, `!server_stats`, `!dashboard` | Dashboard multi-pages |

### Sondages

| Commande | Description |
|----------|-------------|
| `!poll "question" "opt1" "opt2" ...` | Creer un sondage (2-10 options) |
| `!poll_duration "question" <duree> ...` | Sondage avec timer |
| `!poll_info <id>` | Details du sondage |
| `!poll_results <id>` | Resultats finaux |

---

## COMMANDES ADMIN

### Gestion des Taches (TASK_ROLES)

| Commande | Usage | Description |
|----------|-------|-------------|
| `!task` | `!task <action> <manga> <chap...>` | MAJ tache (clean/trad/check/edit) |
| `!task_status` | `!task_status <manga> <chap>` | Etat des taches d'un chapitre |
| `!task_all` | `!task_all [manga]` | Toutes les taches |
| `!delete_task` | `!delete_task <manga> <chap>` | Supprimer taches d'un chapitre |
| `!fix_tasks` | `!fix_tasks` | Normaliser les cles |
| `!actualiser` | `!actualiser` | Sauvegarder/exporter les donnees |

### Planning (TASK_ROLES)

| Commande | Aliases | Description |
|----------|---------|-------------|
| `!planning_add` | `!add_planning` | Ajouter sortie(s) — supporte multi-chapitres (`220-222`, `220,221`) |
| `!planning_status` | `!planning_update` | Changer le statut (prevu/en_cours/trad_done/check_done/pret/sorti/retarde) |
| `!planning_date` | `!planning_reschedule` | Modifier la date |
| `!planning_teaser` | `!planning_spoil`, `!teaser` | Ajouter/modifier teaser (spoiler) |
| `!planning_post` | `!planning_refresh` | Poster/rafraichir dans le channel planning |

### Planning (ADMIN_ROLES)

| Commande | Aliases | Description |
|----------|---------|-------------|
| `!planning_remove` | `!planning_delete`, `!del_planning` | Supprimer une entree |

### Rappels (ADMIN_ROLES)

| Commande | Description |
|----------|-------------|
| `!add_rappel` | Creer un rappel (interactif: user, manga, chapitres, tache, deadline) |
| `!list_rappels` | Liste des rappels actifs |
| `!delete_rappel <id>` | Supprimer un rappel |
| `!actualiser_rappels <save/load>` | Sauvegarder/recharger |
| `!test_rappel` | Tester l'envoi |

### Giveaways (ADMIN_ROLES)

| Commande | Description |
|----------|-------------|
| `!create_giveaway` | Creer giveaway (interactif) |
| `!giveaway <duree> <nb_gagnants> <prix>` | Creer giveaway rapide |
| `!end_giveaway <id>` | Terminer et tirer gagnants |
| `!delete_giveaway <id>` | Supprimer |
| `!reroll <id> [nb]` | Retirer des gagnants |
| `!giveaway_participants <id>` | Liste des participants |
| `!add_invites @user <nb>` | Ajouter des invitations |
| `!remove_invites @user <nb>` | Retirer des invitations |
| `!reset_user_invites @user` | Reset invitations |
| `!server_invite_stats` | Stats globales invitations |

### Boutique (ADMIN_ROLES)

| Commande | Description |
|----------|-------------|
| `!shop_add` | Ajouter un item (interactif) |
| `!shop_remove <item>` | Supprimer un item |
| `!give_item @user <item>` | Donner un item |
| `!set_points @user <montant>` | Definir les points |
| `!add_points_admin @user <montant>` | Ajouter/retirer des points |

### Communaute (ADMIN_ROLES)

| Commande | Aliases | Description |
|----------|---------|-------------|
| `!give_xp` | `!give_points`, `!addxp` | Donner de l'XP |
| `!reset_xp` | `!reset_points` | Reset l'XP d'un membre |

### Annonces (ADMIN_ROLES)

| Commande | Description |
|----------|-------------|
| `!announce_chapter` | Annonce de chapitre (interactif: manga, chapitres, lien, description) |
| `!test_announce` | Test dans channel de test |

### Sondages (ADMIN_ROLES)

| Commande | Description |
|----------|-------------|
| `!close_poll <id>` | Fermer un sondage |

### Donnees (ADMIN_ROLES)

| Commande | Description |
|----------|-------------|
| `!export_data [module]` | Exporter les fichiers JSON |
| `!reload_data [module]` | Recharger depuis fichiers |
| `!data_stats` | Tailles et compteurs des donnees |

---

## SYSTEMES AUTOMATIQUES

### Taches de fond (Background Tasks)

| Tache | Intervalle | Description |
|-------|-----------|-------------|
| `daily_planning_check` | Toutes les heures (execute a 9h Paris) | Rappels sorties aujourd'hui/demain |
| `send_reminders` | Toutes les heures | DM rappels de deadlines (J-1) |
| `check_giveaways` | Toutes les minutes | Termine les giveaways expires |
| `auto_sync_task` | Toutes les 30 min | Commit & push donnees vers GitHub |
| `weekly_seniority` | Dimanche minuit UTC | Bonus XP anciennete |
| `weekly_lottery` | Dimanche 18h UTC | Tirage loterie |
| `check_deletions` | Toutes les 5 min | Surveillance messages supprimes |

### Evenements Discord

| Evenement | Action |
|-----------|--------|
| `on_ready` | Status "!help pour les commandes" |
| `on_member_join` | Message de bienvenue + log |
| `on_member_remove` | Log de depart |
| `on_raw_reaction_add` | Acceptation reglement (reaction check sur reglement → attribution roles member + access) |
| `on_message` | Gain XP (1-3 XP, cooldown 60s) |
| `on_voice_state_update` | Tracking temps vocal (5 XP / 15 min) |
| `on_message_delete` | Log dans channel logs |
| `on_message_edit` | Log dans channel logs |
| `on_member_update` | Log changements roles/pseudo |

---

## SYSTEME XP & NIVEAUX

### Sources d'XP

| Source | XP | Conditions |
|--------|-----|-----------|
| Message | 1-3 | Cooldown 60s, channels autorises uniquement |
| Daily bonus | 20-50 | 1x par jour, +5 par jour de streak (max +50) |
| Vocal | 5 | Par tranche de 15 minutes |
| Reaction chapitre | 10 | Sur les messages de chapitres |
| Trivia (easy) | 20 | Bonne reponse |
| Trivia (medium) | 50 | Bonne reponse |
| Trivia (hard) | 100 | Bonne reponse |
| Guess | 30 | Bonne reponse |
| Anciennete | 50-200 | Bonus hebdomadaire automatique |

### Calcul de niveau

- Base: 100 XP pour le niveau 1
- Facteur de croissance: 1.15x par niveau
- Niveau max: 100
- Formule: `XP_requis(n) = 100 * 1.15^(n-1)`

### Channels autorises pour l'XP

General + les 5 channels manga

---

## SYSTEME DE PLANNING

### Statuts

| Cle | Emoji | Label | Couleur |
|-----|-------|-------|---------|
| `prevu` | 📅 | Prevu | Bleu |
| `en_cours` | 🔄 | En cours | Orange |
| `trad_done` | 🌍 | Trad terminee | Violet |
| `check_done` | ✅ | Check termine | Vert |
| `pret` | 🚀 | Pret a sortir | Turquoise |
| `sorti` | 📢 | Sorti | Vert |
| `retarde` | ⚠️ | Retarde | Rouge |

### Format chapitres multiples

| Format | Exemple | Resultat |
|--------|---------|----------|
| Unique | `220` | [220] |
| Liste | `220,221,222` | [220, 221, 222] |
| Plage | `220-222` | [220, 221, 222] |
| Mixte | `220,223,225-227` | [220, 223, 225, 226, 227] |

### Affichage calendrier

```
 LUN   MAR   MER   JEU   VEN   SAM   DIM
---------------------------------------
                                    1
   2     3     4     5     6     7     8
   9    10    11    12    13   [14]   15
  16    17    18    19    20    21    22
  23    24    25    26    27   *28*   29
 *30*   31

[XX] = Aujourd'hui  *XX* = Jour de sortie
```

---

## SYSTEME DE BADGES

### Categories de badges

| Badge | Categorie | Rarete |
|-------|-----------|--------|
| first_task | Contribution | Common |
| task_master | Contribution | Rare |
| speed_demon | Contribution | Epic |
| perfectionist | Contribution | Legendary |
| newcomer | Anciennete | Common |
| veteran | Anciennete | Rare |
| eternal_member | Anciennete | Epic |
| sociable | Communaute | Common |
| voice_enthusiast | Communaute | Uncommon |
| theory_crafter | Communaute | Rare |
| lucky_strike | Shop/Loterie | Uncommon |
| generous_soul | Shop/Loterie | Rare |

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

### Loot Tables (Mystery Box)

| Rarete | Contenu |
|--------|---------|
| Common | 50-100 points, 1 ticket loterie |
| Uncommon | 150-250 points, 2 tickets |
| Rare | 500-750 points, boosters |

---

## DONNEES & STOCKAGE

### Fichiers JSON (`data/`)

| Fichier | Description |
|---------|-------------|
| `etat_taches.json` | Statuts des taches (clean/trad/check/edit) |
| `etat_taches_meta.json` | Metadata des taches |
| `rappels_tasks.json` | Rappels de deadlines |
| `rappels_tasks_meta.json` | Metadata des rappels |
| `user_stats.json` | XP, niveaux, activite des membres |
| `chapters_community.json` | Suivi reactions chapitres |
| `shop_items.json` | Items de la boutique |
| `shop_inventory.json` | Inventaires des utilisateurs |
| `purchases.json` | Historique d'achats |
| `lottery.json` | Donnees loterie hebdomadaire |
| `user_badges.json` | Badges des utilisateurs |
| `badges_config.json` | Configuration des badges |
| `user_inventory.json` | Items des utilisateurs |
| `giveaways.json` | Giveaways actifs et termines |
| `invites_tracker.json` | Suivi des invitations |
| `polls.json` | Sondages actifs |
| `planning.json` | Planning des sorties |
| `planning_meta.json` | Metadata du planning |
| `dm_reminder_notified.json` | Suivi DM rappels |

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

## HELP - CATEGORIES

| Categorie | Emoji | Type | Nb cmds |
|-----------|-------|------|---------|
| General | 🎮 | Public | 5 |
| Communaute | 🌟 | Public | 6 |
| Badges | 🏆 | Public | 6 |
| Shop | 🛒 | Public | 4 |
| Giveaways | 🎁 | Public | 4 |
| Planning | 📅 | Public | 2 |
| Taches | 📋 | Admin | 6 |
| Rappels | ⏰ | Admin | 5 |
| Giveaways Admin | 🎁 | Admin | — |
| Planning Admin | 📅 | Admin | — |
| Shop Admin | 🛒 | Admin | — |
| Annonces | 📢 | Admin | — |
| Donnees | 💾 | Admin | — |

---

## RESUME DES NOMBRES

| Element | Nombre |
|---------|--------|
| Fichiers Python | 16+ |
| Commandes publiques | ~25 |
| Commandes admin | ~35 |
| Background tasks | 7 |
| Event listeners | 8+ |
| Fichiers de donnees | 17 JSON + 1 SQLite |
| Mangas geres | 5 |
| Roles selectionnables | 17 |
| Statuts de badge | 5 (Common → Legendary) |
| Statuts de planning | 7 |

---

*Derniere mise a jour: 14 Mars 2026*
