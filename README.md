# 🩸 LanorTradBot

Le bot du serveur Discord officiel LanorTrad.

> **Le site décide, Discord notifie.**
> Le bot lit les données du site ([lanortrad.com](https://lanortrad.com))
> et les recopie dans Discord. Rien ne se ressaisit à la main, rien ne peut
> diverger.

Le serveur est **informatif** : il prévient des sorties, met en relation avec
l'équipe, et recrute. La communauté, elle, vit sur le forum du site — c'est
pour ça qu'il n'y a volontairement aucun salon de discussion.

---

## Démarrer

```bash
pip install -r requirements.txt
```

```bash
cp .env.example .env
```

Renseigne `DISCORD_TOKEN` dans `.env`, puis :

```bash
python -m bot.main
```

En production, PM2 lance `run_v2.py`, qui fait la même chose.

Le bot demande sur quel serveur il travaille. Pour éviter la question :

```bash
python -m bot.main --server prod
```

| Mode | Effet |
|---|---|
| `--server prod` \| `--server test` | choisit le serveur sans poser la question |
| `--no-tasks` | en ligne, commandes actives, **aucune boucle automatique** |
| `--safe` | en ligne et **ne fait rien** (3 cogs seulement) |

Équivalents en variables d'environnement : `LANOR_SERVER`, `LANOR_NO_TASKS`,
`LANOR_SAFE_MODE`.

Le bot ne sert **qu'un serveur à la fois** : tout événement venant d'ailleurs
est ignoré, et toute commande lancée depuis un autre serveur est refusée.

---

## Les commandes

### Pour les lecteurs

| Commande | Ce qu'elle fait |
|---|---|
| `/planning` | le rythme de parution, jour par jour |
| `/atelier` | où en est chaque prochain chapitre, avec la jauge en 6 étapes |
| `/sorties` | les derniers chapitres publiés |
| `/catalogue` | toutes les séries |
| `/serie <nom>` | fiche complète : genres, auteur, note, couverture, étape en cours |
| `/alertes` | choisir les séries qui te pinguent |
| `/site` | tous les liens utiles |
| `/postuler` | rejoindre la team scantrad |
| `/aide` | la liste des commandes |

### Pour l'équipe

`/release` · `/site_sync` · `/annonce` · `/candidatures` · `/clear` · `/lent` ·
`/verrou` · `/deverrou` · `/timeout` · `/kick` · `/ban` · `/warn` · `/warns` ·
`/delwarn` · `/clearwarns`

### L'atelier

Un chapitre = **une fiche** qui se réécrit à chaque étape, dans le salon d'équipe.

| Commande | Ce qu'elle fait |
|---|---|
| `/atelier_raws` | ouvre la fiche et son fil : les pages se déposent dans le fil |
| `/atelier_clean` · `/atelier_trad` · `/atelier_edit` · `/atelier_qcheck` | valide une étape et passe le relais à la suivante |
| `/mes_taches` | ton établi : ce que tu as pris, ce qui attend ton métier |
| `/atelier_liste` | tout ce qui est en cours, par série |
| `/atelier_fiche` · `/atelier_eta` | revoir une fiche · fixer la sortie visée |
| `/atelier_etape` · `/atelier_retirer` | (staff) corriger l'étape · supprimer la fiche |
| `/atelier_export` · `/atelier_pousser` | régénérer `atelier.js` · l'écrire dans le dépôt du site |

Les pages ne passent pas par la commande : une commande slash plafonne à 25
options et chaque pièce jointe en consomme une. `/atelier_raws` ouvre donc un
**fil sur la fiche**, où l'on glisse les pages normalement — dix par message.
Le bot compte les images reçues et affiche `14/20` sur la fiche, séparément
pour chaque étape : le clean, la traduction et l'édition déposent leur rendu
au même endroit. L'aperçu de la commande est devenu facultatif ; sans lui, la
première page déposée illustre la fiche.

Prendre une étape, c'est prendre une **échéance** — 5 jours pour un clean,
4 pour une traduction, 5 pour une édition, 2 pour un Q-check, ajustés au
nombre de pages. La fiche affiche le compte à rebours ; le bot écrit en
privé la veille, puis le jour dit, puis deux jours après. Le bouton
**⏰ Plus de temps** ajoute trois jours sans avoir à se justifier, et
**↩️ Je rends** libère le chapitre sans que personne ne demande pourquoi.
Passé six jours de retard, l'étape retourne au pot commun toute seule.

Une étape que personne ne prend repingue son métier tous les trois jours,
puis passe la main au staff. Rien de tout ça n'est public : les rappels
partent en MP, les retards vont dans le salon d'équipe. Tous les délais se
règlent dans `bot/config.py` (bloc `ATELIER_`).
### Gestion des rôles

| Commande | Ce qu'elle fait |
|---|---|
| `/roles_ajouter` | un ou plusieurs rôles à des membres précis, aux porteurs d'un rôle, ou à tout le monde |
| `/roles_base` | le rôle de base à tous les membres, avec progression |
| `/roles_retirer` | retire un rôle à tous ceux qui l'ont |
| `/roles_ranger` | remet la hiérarchie dans l'ordre prévu |

Toutes tournent en **simulation par défaut** : `simulation:False` pour appliquer.

### Configuration du serveur

| Commande | Ce qu'elle fait |
|---|---|
| `/perms_roles` | permissions serveur de chaque rôle, et @everyone en lecture seule |
| `/perms_salons` | droits des 22 salons (lecture · panneau · ouvert · équipe · staff) |
| `/onboarding_etat` | ce qui bloque le processus d'accueil Discord |
| `/onboarding_preparer` | ouvre un salon à l'écriture, prérequis de Discord |
| `/onboarding_setup` | écrit les questions d'accueil et l'écran de bienvenue |
| `/publier <page>` | (re)poste les pages de référence |

### Administration

`/panneau_alertes` · `/ticket_setup` · `/recrutement_panel` · `/raid` ·
`/lockdown` · `/backup` · `/logs` · `/dis` · `/ping` · `/serveur` · `/membre`

---

## Ce qui tourne tout seul

| Automatisme | Déclencheur |
|---|---|
| 📅 Calendrier hebdo + atelier, épinglés et mis à jour | toutes les 15 min |
| 🆕 Publication d'un nouveau chapitre, avec couverture et ping | un chapitre de plus dans `chapters.js` |
| 🔍 Annonce d'un avancement d'étape (salon équipe) | changement dans `atelier.js` |
| 🩹 Alerte panne du site dans `#incidents`, puis retour à la normale | 3 échecs de lecture d'affilée |
| 🕒 Relance sur les chapitres qui dorment depuis 21 jours | une fois par semaine |
| 👋 Accueil en MP des nouveaux + rôle lecteur | à l'arrivée |
| 🛡️ Anti-raid, anti-flood, automod | en continu |
| 💾 Sauvegarde de la structure du serveur | chaque semaine |

---

## Architecture

```
bot/
├── main.py        point d'entrée · cloison entre serveurs · modes de lancement
├── config.py      tous les réglages
├── servers.py     registre prod / test + la question au lancement
├── site.py        client du site — la source de vérité
├── resolver.py    retrouve salons et rôles par leur NOM (aucun ID à coller)
├── storage.py     persistance JSON atomique
├── msgcache.py    cache SQLite des messages (logs qui survivent au redémarrage)
├── embeds.py      fabrique d'embeds : une seule identité visuelle
└── cogs/
    ├── sitesync.py    planning · atelier · catalogue · publication auto
    ├── releases.py    /release manuel + historique
    ├── alerts.py      panneau des rôles de séries
    ├── content.py     pages de référence (bienvenue, règles, FAQ, lexique…)
    ├── welcome.py     accueil des nouveaux
    ├── tickets.py     support privé par threads
    ├── recruit.py     candidature → test → attribution du rôle
    ├── moderation.py  sanctions
    ├── warns.py       avertissements persistants
    ├── guard.py       automod + anti-raid + anti-flood
    ├── logs.py        journalisation
    ├── backup.py      sauvegardes de la structure
    ├── bulkroles.py   attribution de rôles en masse
    ├── rolesorder.py  rangement de la hiérarchie
    ├── permissions.py droits des rôles et des salons
    ├── onboarding.py  processus d'accueil natif Discord
    ├── info.py        /ping /membre /serveur /site /dis /annonce
    ├── help.py        /aide
    └── errors.py      gestion d'erreurs globale
run_v2.py   point d'entrée PM2
data/       runtime, ignoré par git
tests/      tests hors-ligne du parseur du site
```

### Aucun ID à coller

`resolver.py` retrouve chaque salon par le fragment de son nom et chaque rôle
par son nom exact, puis met le résultat en cache dans `data/resolved_ids.json`.
Au démarrage, les logs disent ce qui a été trouvé :

```
🔎 [info] IDs résolus : 21 salons · 18 rôles (manquants : 0 salons, 2 rôles)
🎭 rôles séries rattachés : ping_tougen → « 🗡️ ⋆ Tougen Anki », …
```

Les **5 rôles de séries existants** sont rattachés par leur nom et ne sont
jamais recréés : les membres restent abonnés quoi qu'il arrive.

### Les pages de référence

`/publier <page>` (re)poste les textes explicatifs du serveur : bienvenue,
règles, FAQ, le site, le forum, le lexique scantrad, le recrutement. Republier
**édite** les messages existants au lieu d'en empiler de nouveaux, et les
mentions de salons se recalculent toutes seules.

---

## Tests

```bash
python -m tests.test_site
```

Vérifie hors-ligne que le parseur avale bien les fichiers JS du site : clés
sans guillemets, virgules traînantes, commentaires, format compact des
chapitres.

---

## L'ancien bot

La v1 (25 000 lignes, 152 commandes : mini-jeux, boutique, économie, XP,
tournois) a été retirée : ces fonctionnalités servaient un serveur
communautaire, remplacé par le forum du site.

Rien n'est perdu — elle reste accessible en une commande :

```bash
git checkout v1-avant-v2 -- .
```

---

🩸 *LanorTrad — là où les chapitres prennent vie.*
