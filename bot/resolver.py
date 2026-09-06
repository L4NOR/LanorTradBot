"""
Résolution automatique des IDs salons / rôles
==============================================
Plus besoin de coller des IDs à la main dans `bot_config.py` : au démarrage,
le bot retrouve chaque salon par son *slug* (la partie après `・`) et chaque
rôle par son nom exact, puis remplit `CHANNELS` / `ROLES` **en place**.

Ordre de priorité :
  1. ID déjà renseigné dans bot_config.py (ou data/resolved_ids.json)
     → conservé s'il pointe vers un salon/rôle qui existe encore
  2. sinon : résolution par nom
  3. sinon : la clé reste à None (les cogs gèrent le cas proprement)

Le résultat est réécrit dans `data/resolved_ids.json` pour que le prochain
démarrage soit instantané, et pour que `reset_rebuild.py` reste compatible.
"""
import json
import logging
import os

import re
import unicodedata

import discord

from bot.config import CHANNELS, ROLES, MANGAS, KEEP_ROLE_IDS, PROFILE

log = logging.getLogger("lanortrad.resolver")

_DATA_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
_RESOLVED_PATH = os.path.join(_DATA_DIR, "resolved_ids.json")


# ═══════════════════════════════════════════════════════
# 📂 SALONS — clé bot_config → slug(s) recherché(s)
# ═══════════════════════════════════════════════════════
# La valeur peut être un slug ou un tuple de slugs (variantes accentuées).
# Le slug doit être suffisamment SPÉCIFIQUE : la recherche est un
# "contient", et le premier salon qui matche gagne.

# Chaque clé accepte plusieurs candidats : le 1er trouvé gagne.
# C'est ce qui permet aux MÊMES cogs de servir les deux serveurs — le salon
# « 🎫・tickets » du serveur communautaire et « 🎫・support » de l'informatif
# répondent à la même clé `tickets`.
CHANNEL_SLUGS = {
    # ─── Entrée ───
    "welcome":          ("gates-of-lanor", "bienvenue"),
    "about":            ("about-lanortrad", "bienvenue"),
    "rules":            ("oath-pacte", "oath", "règles", "regles"),
    "verification":     "verification",
    "notifications":    ("notifications", "alertes-sorties"),
    "faq":              ("lexique-faq", "lexique", "faq"),
    "presentations":    ("présentations", "presentations", "introductions"),

    # ─── Broadcast ───
    "announcements":    ("announcements", "annonces"),
    "events":           "events",
    "social_media":     "social-media",
    "partners":         "partners",

    # ─── Le site (serveur informatif) ───
    "site_links":       "le-site",
    "site_forum":       "forum-du-site",
    "incidents":        "incidents",

    # ─── Releases ───
    "sorties_fr":       ("sorties-fr", "nouveaux-chapitres"),
    "translations_en":  "translations-en",
    "planning":         "planning",
    "releases_forum":   "releases",      # optionnel (mode forum, cf. RELEASE_FORUM_MODE)

    # ─── Perks ───
    "vip_lounge":       "vip-lounge",
    "early_access":     "early-access",
    "perks_rewards":    "perks-rewards",

    # ─── Communauté ───
    "discussion":       "discussion-chat",
    "introductions":    "introductions",
    "creations":        ("créations", "creations"),
    "mangas_talk":      "mangas-talk",
    "starboard":        "starboard",
    "off_topic":        "off-topic",

    # ─── Oneshots ───
    "oneshots_forum":   "oneshots-vault",
    "oneshots_talk":    "oneshots-talk",

    # ─── Arena ───
    "bot_commands":     "bot-commands",
    "quiz":             "quiz-manga",
    "economy":          ("économie", "economie"),
    "polls":            "polls",

    # ─── Support ───
    "tickets":          ("tickets", "support"),
    "suggestions":      "suggestions",
    "recrutement":      "recrutement",
    "tests_techniques": ("tests-techniques", "tests-candidats"),

    # ─── Atelier / workshop ───
    "workshop_chat":    ("workshop-chat", "・atelier"),
    "tech_discussions": "tech-discussions",
    "glossary":         ("glossary-db", "glossaire"),
    "raws_archive":     ("raws-archive", "pages-raws"),
    "pipeline":         "pipeline",

    # ─── Staff ───
    "staff_chat":       ("staff-chat", "・atelier"),
    "moderation":       ("modération", "moderation"),
    "projets_internes": ("projets-internes", "projets"),

    # ─── Logs ───
    "logs":             "server-logs",   # alias historique
    "server_logs":      "server-logs",
    "message_logs":     "message-logs",
    "automod_logs":     "automod-logs",
    "bot_logs":         "bot-logs",

    # ─── Bots ───
    "bump":             "bump",
}


# ═══════════════════════════════════════════════════════
# 🎭 RÔLES — clé bot_config → nom EXACT du rôle
# ═══════════════════════════════════════════════════════

# Comme pour les salons : plusieurs noms possibles par clé
# (nom du serveur communautaire, puis nom du serveur informatif).
ROLE_NAMES = {
    # ─── Base ───
    "member":        ("📖 Member", "📖 Lecteur"),
    "veteran":       "🎖️ Veteran",
    "lecteur_fr":    "🇫🇷 Lecteur FR",
    "reader_en":     "🇬🇧 Reader EN",

    # ─── Staff ───
    "founder":       ("🩸 Founder", "🩸 Fondateur"),
    "cofounder":     "🥀 Co-Founder",
    "admin":         "⚔️ Admin",
    "moderator":     ("🛡️ Moderator", "🛡️ Modération"),
    "helper":        "🔰 Helper",

    # ─── Métiers scantrad ───
    "translator":    ("📝 Translator", "💬 Traduction"),
    "cleaner":       ("🧼 Cleaner", "🧽 Clean"),
    "redrawer":      "✏️ Redrawer",
    "typesetter":    ("🖋️ Typesetter", "✍️ Édition"),
    "qc":            ("✅ QC", "🔍 Q-check"),
    "raw_provider":  ("🇯🇵 Raw Provider", "📥 Pages"),
    "trial":         "🎓 En test",

    # ─── Perks ───
    "booster":       "🚀 Booster",
    "patron":        "💎 Patron",
    "vip":           "👑 VIP",

    # ─── Niveaux XP ───
    "lvl_apprenti":  "🐣 Apprenti Lecteur",
    "lvl_regulier":  "📖 Lecteur Régulier",
    "lvl_disciple":  "🩸 Disciple",
    "lvl_confirme":  "⚔️ Lecteur Confirmé",
    "lvl_maitre":    "🥀 Maître",
    "lvl_legende":   "👑 Légende",

    # ─── Pings séries ───
    # Sur le serveur LanorTrad, ces rôles EXISTENT DÉJÀ (KEEP_ROLE_IDS) et
    # portent peut-être d'autres noms : map_kept_manga_roles() les rattache
    # par leur nom réel, quel que soit leur habillage.
    "ping_tougen":   ("🗡️ ⋆ Tougen Anki", "Tougen Anki"),
    "ping_ao":       ("🩸 ⋆ Ao No Exorcist", "🩸 ⋆ Ao no Exorcist", "Ao No Exorcist"),
    "ping_tokyo":    ("🏙️ ⋆ Tokyo Underworld", "Tokyo Underworld"),
    "ping_cat":      ("⚽ ⋆ Catenaccio", "Catenaccio"),
    "ping_sat":      ("🔪 ⋆ Satsudou", "Satsudou"),
    "ping_one":      ("📜 ⋆ Oneshots", "📜 Oneshots"),

    # ─── Suivi de fabrication (créé par /suivi_setup) ───
    "ping_workshop": ("🔔 Suivi de fabrication", "Suivi de fabrication",
                      "🔔 ⋆ Suivi de fabrication"),

    # ─── Pings communauté ───
    "ping_all":           "🔔 ⋆ Toutes sorties",
    "ping_announcements": ("📢 ⋆ Announcements", "📢 ⋆ Annonces"),
    "ping_events":        "🎉 ⋆ Events",
    "ping_giveaways":     "🎁 ⋆ Giveaways",
}


def _find_channel(guild: discord.Guild, slugs):
    if isinstance(slugs, str):
        slugs = (slugs,)
    for slug in slugs:
        needle = slug.lower()
        for ch in guild.channels:
            if isinstance(ch, discord.CategoryChannel):
                continue
            if needle in ch.name.lower():
                return ch
    return None


def _find_role(guild: discord.Guild, names):
    if isinstance(names, str):
        names = (names,)
    for name in names:
        role = discord.utils.get(guild.roles, name=name)
        if role is not None:
            return role
    return None


def _normalize(text: str) -> str:
    """minuscules, sans accents ni décorations — pour comparer des noms de rôles."""
    text = unicodedata.normalize("NFKD", text or "")
    text = "".join(c for c in text if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def map_kept_manga_roles(guild: discord.Guild) -> dict:
    """Rattache les rôles conservés (KEEP_ROLE_IDS) aux séries, par leur NOM.

    Les 5 rôles de ping des séries en cours existent déjà sur le serveur et
    sont portés par les membres : on ne les recrée pas, on les reconnaît.
    Aucun ordre à respecter dans KEEP_ROLE_IDS.
    """
    mapped, unknown, explicites = {}, [], []
    for role_id in KEEP_ROLE_IDS:
        role = guild.get_role(int(role_id))
        if role is None:
            continue
        norm = _normalize(role.name)
        match = None
        for key, info in MANGAS.items():
            candidate = _normalize(info["name"])
            if candidate and candidate in norm:
                match = info["role_key"]
                break
        if match:
            explicite = ROLES.get(match)
            if explicite and guild.get_role(int(explicite)):
                explicites.append(match)   # ID explicite : il fait autorité
                continue
            ROLES[match] = role.id
            mapped[match] = role.name
        else:
            unknown.append(f"{role.name} ({role.id})")

    if mapped:
        log.info("🎭 rôles séries rattachés : %s",
                 ", ".join(f"{k} → « {v} »" for k, v in mapped.items()))
    if explicites:
        log.info("🔒 rôles séries fixés par ID : %s", ", ".join(sorted(explicites)))
    connus = set(mapped) | set(explicites)
    missing = [i["role_key"] for i in MANGAS.values()
               if i["role_key"] not in connus and i["role_key"] != "ping_one"]
    if missing:
        log.warning("   séries sans rôle conservé : %s", ", ".join(missing))
    if unknown:
        log.warning("   rôles conservés non reconnus (nom ≠ catalogue) : %s",
                    ", ".join(unknown))
    return mapped


def resolve(guild: discord.Guild) -> dict:
    """Complète CHANNELS et ROLES en place. Retourne un rapport."""
    found_ch, found_role, missing_ch, missing_role = {}, {}, [], []

    for key, slugs in CHANNEL_SLUGS.items():
        current = CHANNELS.get(key)
        if current and guild.get_channel(current) is not None:
            found_ch[key] = current           # ID existant toujours valide
            continue
        ch = _find_channel(guild, slugs)
        if ch is not None:
            CHANNELS[key] = ch.id
            found_ch[key] = ch.id
        else:
            CHANNELS.setdefault(key, None)
            missing_ch.append(key)

    # Les rôles de séries conservés sont rattachés en priorité : leur ID fait foi
    kept = map_kept_manga_roles(guild) if KEEP_ROLE_IDS else {}

    for key, names in ROLE_NAMES.items():
        # 1. un ID explicite et valide gagne toujours
        current = ROLES.get(key)
        if current and guild.get_role(int(current)) is not None:
            found_role[key] = int(current)
            continue
        # 2. sinon, le rattachement par nom des roles de series
        if key in kept:
            found_role[key] = ROLES[key]
            continue
        role = _find_role(guild, names)
        if role is not None:
            ROLES[key] = role.id
            found_role[key] = role.id
        else:
            ROLES.setdefault(key, None)
            missing_role.append(key)

    _write(found_ch, found_role)

    log.info(
        "🔎 [%s] IDs résolus : %d salons · %d rôles "
        "(manquants : %d salons, %d rôles)",
        PROFILE, len(found_ch), len(found_role), len(missing_ch), len(missing_role),
    )
    if missing_ch:
        log.warning("   salons non trouvés : %s", ", ".join(missing_ch))
    if missing_role:
        log.warning("   rôles non trouvés : %s", ", ".join(missing_role))

    return {
        "channels": found_ch, "roles": found_role,
        "missing_channels": missing_ch, "missing_roles": missing_role,
    }


def _write(channels: dict, roles: dict):
    os.makedirs(_DATA_DIR, exist_ok=True)
    tmp = _RESOLVED_PATH + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump({"channels": channels, "roles": roles}, f,
                      ensure_ascii=False, indent=2)
        os.replace(tmp, _RESOLVED_PATH)
    except OSError as e:
        log.error("Écriture de resolved_ids.json impossible : %s", e)
