# 🩸 LanorTradBot

Le bot du serveur Discord officiel LanorTrad.

> **Le site décide, Discord notifie.**
> Le bot lit les données du site ([lanortradtest.netlify.app](https://lanortradtest.netlify.app))
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

### Administration

`/publier <page>` · `/panneau_alertes` · `/ticket_setup` · `/recrutement_panel` ·
`/raid` · `/lockdown` · `/backup` · `/logs` · `/dis` · `/ping` · `/serveur` ·
`/membre`

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
    ├── info.py        /ping /membre /serveur /site /dis /annonce
    ├── help.py        /aide
    └── errors.py      gestion d'erreurs globale
data/       runtime, ignoré par git
tests/      tests hors-ligne du parseur du site
legacy/     l'ancien bot (v1), conservé tel quel pour référence
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
tournois) vit dans `legacy/`. Elle ne se charge plus : ces fonctionnalités
servaient un serveur communautaire, remplacé par le forum du site. Tout reste
dans l'historique git, rien n'est perdu.

---

🩸 *LanorTrad — là où les chapitres prennent vie.*
