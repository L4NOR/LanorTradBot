# minigames.py
# ═══════════════════════════════════════════════════════════════════════════════
# MINI-JEUX COMMUNAUTAIRES - GAINS D'XP PAR LE JEU
# ═══════════════════════════════════════════════════════════════════════════════

import discord
from discord.ext import commands, tasks
import random
import asyncio
import time
import unicodedata
from datetime import datetime, timedelta
from config import COLORS, POINTS_ALLOWED_CHANNELS
from community import add_xp, get_user_stats, sauvegarder_donnees, calculate_level, xp_progress, generate_xp_bar
from database import db
from utils import safe_api_call, load_json, save_json
from effects import (
    apply_minigame_xp,
    is_featured,
    get_featured_game,
    FEATURED_MULTIPLIER,
)
import logging

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════════
# CONSTANTES
# ═══════════════════════════════════════════════════════════════════════════════

MINIGAME_XP = {
    "reaction": 15,
    "unscramble": 25,
    "wordle": 50,
    "hangman": 30,
    "chain": 20,
    "boss_hit": 5,
    "boss_kill": 100,
    "duel_min_bet": 10,
}

# ═══════════════════════════════════════════════════════════════════════════════
# LIMITES QUOTIDIENNES — pool partagé par catégorie
# ═══════════════════════════════════════════════════════════════════════════════
# Les admins (rôles dans ADMIN_ROLES) ne sont pas soumis à ces limites.
# Chaque utilisateur dispose d'un pool partagé :
#   • "minigames" : 15 parties/jour réparties librement entre les 9 mini-jeux
#   • "boss"      : 1 attaque/jour
# Le compteur est stocké en SQLite via la "catégorie" comme clé (pas par jeu).

CATEGORY_LIMITS = {
    "minigames": 15,
    "boss":      1,
}

# Mapping nom du jeu → catégorie partagée
GAME_CATEGORIES = {
    "reaction":   "minigames",
    "unscramble": "minigames",
    "wordle":     "minigames",
    "hangman":    "minigames",
    "chain":      "minigames",
    "coinflip":   "minigames",
    "slots":      "minigames",
    "roulette":   "minigames",
    "duel":       "minigames",
    "boss":       "boss",
}

CATEGORY_LABELS = {
    "minigames": "Mini-jeux",
    "boss":      "Attaques boss",
}

# Mots pour les jeux (thème manga / traduction)
# Utilisés par !hangman, !unscramble et !chain.
# Chaque mot appartient à un thème → le thème est affiché dans l'embed du jeu
# comme indice pour le joueur.
MANGA_WORD_THEMES = {
    "serveur_univers": {
        "emoji": "🌀",
        "label": "Mangas & univers LanorTrad",
        "words": [
            "exorciste", "demon", "satan", "flammes", "paladin",
            "assassin", "combat", "survie", "lame", "malediction",
            "football", "gardien", "attaquant", "defenseur", "match",
            "yakuza", "crime", "souterrain", "gang",
            "oni", "shiki", "transformation", "rituel", "pacte",
        ],
    },
    "edition_manga": {
        "emoji": "📖",
        "label": "Manga & édition",
        "words": [
            "manga", "anime", "shonen", "seinen", "shojo", "josei", "kodomo",
            "chapitre", "tome", "volume", "scan", "raw", "edition", "couverture",
            "traduction", "traducteur", "correction", "relecture", "cleaning",
            "typesetting", "redraw", "sfx", "mangaka", "studio", "serialisation",
            "editeur", "tirage", "preview",
        ],
    },
    "maitres_eleves": {
        "emoji": "🎓",
        "label": "Maîtres, élèves & relations",
        "words": [
            "sensei", "nakama", "kohai", "senpai", "shifu", "disciple",
            "maitre", "apprenti", "mentor", "rival", "equipe", "famille",
        ],
    },
    "armes_equipement": {
        "emoji": "⚔️",
        "label": "Armes & équipement",
        "words": [
            "katana", "wakizashi", "tanto", "nodachi", "tachi", "naginata",
            "shinobi", "shuriken", "kunai", "sabre", "epee",
            "rapiere", "dague", "fleau", "hache", "masse", "lance",
            "bouclier", "armure", "casque", "gantelet", "arc", "fleche",
            "arbalete", "javelot", "fronde", "fouet",
        ],
    },
    "pouvoirs_techniques": {
        "emoji": "💥",
        "label": "Pouvoirs & techniques",
        "words": [
            "jutsu", "ninjutsu", "genjutsu", "taijutsu", "fuinjutsu",
            "chakra", "haki", "bankai", "shikai", "reiatsu", "zanpakuto",
            "sharingan", "byakugan", "rinnegan", "tsukuyomi", "amaterasu",
            "susanoo", "rasengan", "kamehameha", "bijuu",
            "pouvoir", "technique", "incantation", "mudra", "sceau",
        ],
    },
    "magie_arcanes": {
        "emoji": "🔮",
        "label": "Magie & arcanes",
        "words": [
            "magie", "sortilege", "invocation", "portail", "dimension",
            "alchimie", "necromancie", "elementaire", "runique", "arcane",
            "enchantement", "malefice", "exorcisme", "purification",
        ],
    },
    "aventuriers_classes": {
        "emoji": "🏹",
        "label": "Aventuriers & classes",
        "words": [
            "guerrier", "barbare", "moine", "voleur", "rodeur", "barde",
            "druide", "necromant", "sorcier", "magicien", "invocateur",
            "chevalier", "samourai", "ronin", "ninja", "ashigaru", "shogun", "daimyo",
            "heros", "vilain", "tueur", "chasseur", "traqueur", "garde",
        ],
    },
    "creatures_monstres": {
        "emoji": "🐉",
        "label": "Créatures & monstres",
        "words": [
            "dragon", "wyverne", "hydre", "kraken", "leviathan", "behemoth",
            "fantome", "spectre", "revenant", "liche", "vampire", "loup",
            "loupgarou", "phenix", "griffon", "minotaure", "centaure", "harpie",
            "gorgone", "chimere", "basilic", "sphinx", "manticore",
            "yokai", "tengu", "kappa", "kitsune", "tanuki", "akuma",
            "gobelin", "orc", "troll", "ogre", "geant", "titan", "colosse",
        ],
    },
    "lieux_royaumes": {
        "emoji": "🏰",
        "label": "Lieux & royaumes",
        "words": [
            "clan", "royaume", "empire", "forteresse", "donjon", "chateau",
            "tour", "citadelle", "muraille", "temple", "sanctuaire", "monastere",
            "village", "cite", "capitale", "taverne", "marche", "guilde",
            "foret", "montagne", "caverne", "abime", "oasis", "desert",
            "konoha", "soulsociety", "wano", "edo",
        ],
    },
    "objets_artefacts": {
        "emoji": "💎",
        "label": "Objets & artefacts",
        "words": [
            "elixir", "poison", "antidote", "potion", "parchemin", "grimoire",
            "amulette", "talisman", "relique", "artefact", "joyau", "cristal",
            "rune", "totem", "anneau", "couronne", "sceptre", "orbe",
        ],
    },
    "quetes_mysteres": {
        "emoji": "🗺️",
        "label": "Quêtes & mystères",
        "words": [
            "mission", "quete", "aventure", "mystere", "secret", "enigme",
            "prophetie", "oracle", "vision", "prediction", "destin", "fatalite",
        ],
    },
    "emotions_combat": {
        "emoji": "❤️‍🔥",
        "label": "Émotions & combat",
        "words": [
            "courage", "bravoure", "honneur", "fierte", "fureur", "rage",
            "colere", "vengeance", "trahison", "loyaute", "amitie", "amour",
            "haine", "peur", "terreur", "espoir", "douleur", "sacrifice",
        ],
    },
    "culture_japonaise": {
        "emoji": "🎎",
        "label": "Culture japonaise",
        "words": [
            "ramen", "sushi", "miso", "udon", "soba", "tempura", "onigiri",
            "matsuri", "sakura", "momiji", "kimono", "yukata", "hakama",
            "kanji", "hiragana", "katakana", "tatami", "shoji",
        ],
    },
}

# Flat list dérivée — conservée pour la compatibilité des endroits qui
# n'utilisent pas encore le thème (ex: starter word de !chain).
MANGA_WORDS = [w for theme in MANGA_WORD_THEMES.values() for w in theme["words"]]


def pick_themed_manga_word(min_len=None, max_len=None):
    """Tire un mot aléatoire parmi MANGA_WORD_THEMES.

    Retourne (theme_key, theme_dict, word). Le tirage est équitable sur
    l'ensemble des mots (pas par thème), pour ne pas sur-représenter
    les petits thèmes.
    """
    pool = []
    for key, theme in MANGA_WORD_THEMES.items():
        for w in theme["words"]:
            if min_len is not None and len(w) < min_len:
                continue
            if max_len is not None and len(w) > max_len:
                continue
            pool.append((key, theme, w))
    if not pool:
        # Fallback sans contrainte
        for key, theme in MANGA_WORD_THEMES.items():
            for w in theme["words"]:
                pool.append((key, theme, w))
    return random.choice(pool)

# Mots pour Wordle. La longueur du mot tiré définit le nombre de lettres
# que le joueur doit taper. Les mots sont regroupés par thème — le thème est
# affiché dans l'embed comme indice. Tous les mots sont sans accents
# (normalize() enlève les accents lors des comparaisons). NE PAS y mettre
# des mots avec apostrophe ou tiret — la garde `isalpha()` les rejetterait.
WORDLE_WORD_THEMES = {
    "edition_manga": {
        "emoji": "📖",
        "label": "Manga & édition",
        "words": [
            "manga", "anime", "scans", "clean", "check", "ligne", "bulle",
            "trame", "encre", "trait", "plume", "panel", "pages", "texte",
            "verbe", "prose", "ecrit", "haiku", "kanji",
        ],
    },
    "armes_equipement": {
        "emoji": "⚔️",
        "label": "Armes & équipement",
        "words": [
            "lame", "epee", "sabre", "lames", "epees", "lance", "armes",
            "garde", "forge", "armee", "sabres", "lances", "casque",
        ],
    },
    "magie_arcanes": {
        "emoji": "🔮",
        "label": "Magie & arcanes",
        "words": [
            "magie", "magies", "rituel", "divin", "arcane", "mages", "sages",
            "dieux", "saint", "pieux", "prier", "grace", "foudre",
            "tonner", "purger", "enfers", "saints",
        ],
    },
    "creatures_monstres": {
        "emoji": "🐉",
        "label": "Créatures & monstres",
        "words": [
            "demon", "titan", "ange", "loup", "elfe", "nain",
            "ogres", "morts", "anges", "tengu", "kappa", "akuma",
            "trolls", "demons", "diable", "ourse", "loups", "lions",
        ],
    },
    "aventuriers_classes": {
        "emoji": "🏹",
        "label": "Aventuriers & classes",
        "words": [
            "heros", "ninja", "ronin", "brave", "moine", "barde", "noble",
            "tueur", "voleur", "rodeur", "mentor", "berger", "soldat",
            "ennemi", "allies", "rival", "tueurs", "chefs", "loyaux",
        ],
    },
    "combats_duels": {
        "emoji": "🛡️",
        "label": "Combat & duels",
        "words": [
            "force", "piege", "duels", "siege", "combat", "guerre",
            "cible", "vivant", "vision", "destin", "chaos", "droit",
        ],
    },
    "emotions": {
        "emoji": "❤️‍🔥",
        "label": "Émotions",
        "words": [
            "rage", "coeur", "amour", "haine", "peine",
            "songe", "reves", "honte", "fureur", "esprit",
        ],
    },
    "nature_elements": {
        "emoji": "🌪️",
        "label": "Nature & éléments",
        "words": [
            "feux", "vent", "nuage", "neige", "pluie", "brume", "vents",
            "foret", "orage", "glace", "fumee", "vague", "monts", "mares",
        ],
    },
    "temps_cycles": {
        "emoji": "⏳",
        "label": "Temps & cycles",
        "words": [
            "nuit", "jour", "jours", "soirs", "midis", "matin", "aubes",
            "ciels", "lunes", "neufs", "cents", "mille",
        ],
    },
    "lieux_royaumes": {
        "emoji": "🏰",
        "label": "Lieux & royaumes",
        "words": [
            "clan", "arena", "monde", "route", "voies", "piste", "ponts",
            "tours", "cites", "toits", "camps", "forts", "ports", "baies",
            "trone", "donjon", "guilde", "marche",
        ],
    },
    "objets_artefacts": {
        "emoji": "💎",
        "label": "Objets & artefacts",
        "words": [
            "cles", "clefs", "bague", "croix", "perle", "outil", "objet",
            "plans", "choix",
        ],
    },
    "culture_japonaise": {
        "emoji": "🎎",
        "label": "Culture japonaise",
        "words": [
            "yari", "tabi", "sumo", "ramen", "sushi", "shiki",
        ],
    },
    "corps_physique": {
        "emoji": "🦴",
        "label": "Corps & physique",
        "words": [
            "torse", "genou", "barbe", "front", "ailes", "queue", "crocs",
            "poils", "large", "court", "tete", "epaule", "garcon",
        ],
    },
    "couleurs_ombres": {
        "emoji": "🎨",
        "label": "Couleurs & ombres",
        "words": [
            "rouge", "blanc", "noir", "noirs", "verts", "bleus",
            "noires", "rouges", "vertes", "mort", "ombre", "ombres",
        ],
    },
    "ordre_justice": {
        "emoji": "⚖️",
        "label": "Ordre & justice",
        "words": [
            "rangs", "ordre", "juste", "prise", "chute", "sauts", "volee",
            "quete",
        ],
    },
    "relations_liens": {
        "emoji": "🤝",
        "label": "Relations & liens",
        "words": [
            "amis", "lien", "voie",
        ],
    },
}

# Flat list dérivée — conservée pour compatibilité.
WORDLE_WORDS = [w for theme in WORDLE_WORD_THEMES.values() for w in theme["words"]]


def pick_themed_wordle_word(min_len=None, max_len=None):
    """Tire un mot Wordle aléatoire parmi WORDLE_WORD_THEMES.

    Retourne (theme_key, theme_dict, word). Tirage équitable sur
    l'ensemble des mots.
    """
    pool = []
    for key, theme in WORDLE_WORD_THEMES.items():
        for w in theme["words"]:
            if min_len is not None and len(w) < min_len:
                continue
            if max_len is not None and len(w) > max_len:
                continue
            pool.append((key, theme, w))
    if not pool:
        for key, theme in WORDLE_WORD_THEMES.items():
            for w in theme["words"]:
                pool.append((key, theme, w))
    return random.choice(pool)

# Emojis pour le slot machine
SLOT_EMOJIS = ["🍒", "🍋", "🍊", "🍇", "⭐", "💎", "7️⃣"]

# Emojis pour le jeu de réaction
REACTION_EMOJIS = ["🔥", "⚡", "💎", "🎯", "🌟", "👑", "🎲", "🎪", "🎭", "🎨"]

BOSS_FILE = "data/boss.json"

# ═══════════════════════════════════════════════════════════════════════════════
# BOSS COMMUNAUTAIRES — Catalogue de boss
# ═══════════════════════════════════════════════════════════════════════════════
# Chaque boss reste actif pendant BOSS_DURATION_DAYS. Les bosses tournent
# (manuellement avec !boss_rotate, ou automatiquement avec !boss_auto on).
# La liste est ordonnée — c'est l'ordre de rotation. Ajouter / retirer / modifier
# librement, l'index de rotation est sauvegardé en base et ré-ajusté au load.

BOSS_DURATION_DAYS = 30  # 1 mois

BOSS_CATALOG = [
    {
        "id": "dragon_ombres",
        "name": "🐉 Dragon des Ombres",
        "color": 0x4B0082,
        "max_hp": 50000,
        "hit_min": 15,
        "hit_max": 60,
        "lore": (
            "Un dragon ancien tissé d'ombres et de cendres. Ses écailles "
            "absorbent la lumière, et son rugissement glace les âmes."
        ),
    },
    {
        "id": "oni_supreme",
        "name": "👹 Oni Suprême",
        "color": 0xC0392B,
        "max_hp": 60000,
        "hit_min": 12,
        "hit_max": 55,
        "lore": (
            "Roi des oni, descendu des montagnes interdites. Sa massue "
            "brise les sceaux, son rire fait trembler les villages."
        ),
    },
    {
        "id": "spectre_maudit",
        "name": "💀 Spectre Maudit",
        "color": 0x2C3E50,
        "max_hp": 45000,
        "hit_min": 10,
        "hit_max": 50,
        "lore": (
            "Un revenant lié à un pacte brisé. Insaisissable, il ne peut "
            "être blessé que par la volonté collective de ses traqueurs."
        ),
    },
    {
        "id": "demon_flammes",
        "name": "🔥 Démon des Flammes",
        "color": 0xE74C3C,
        "max_hp": 55000,
        "hit_min": 18,
        "hit_max": 65,
        "lore": (
            "Né d'une fournaise infernale, il transforme l'air en braise "
            "et le sol en lave. Quiconque l'approche brûle déjà."
        ),
    },
    {
        "id": "titan_foudre",
        "name": "⚡ Titan de Foudre",
        "color": 0xF1C40F,
        "max_hp": 65000,
        "hit_min": 14,
        "hit_max": 58,
        "lore": (
            "Un colosse sculpté dans l'orage. Chacun de ses pas déclenche "
            "un éclair, chacun de ses coups un tonnerre dévastateur."
        ),
    },
    {
        "id": "leviathan_abyssal",
        "name": "🌊 Léviathan Abyssal",
        "color": 0x1F618D,
        "max_hp": 70000,
        "hit_min": 20,
        "hit_max": 70,
        "lore": (
            "Surgi des fosses sans fond, ce monstre marin engloutit des "
            "flottes entières. Ses tentacules atteignent même le rivage."
        ),
    },
]


def get_boss_by_id(boss_id):
    """Retourne le dict du boss correspondant à l'id, ou None."""
    for b in BOSS_CATALOG:
        if b["id"] == boss_id:
            return b
    return None


def get_boss_index(boss_id):
    """Retourne l'index du boss dans le catalogue, ou -1."""
    for i, b in enumerate(BOSS_CATALOG):
        if b["id"] == boss_id:
            return i
    return -1


# Hangman stages
HANGMAN_STAGES = [
    "```\n  +---+\n      |\n      |\n      |\n      |\n=========```",
    "```\n  +---+\n  O   |\n      |\n      |\n      |\n=========```",
    "```\n  +---+\n  O   |\n  |   |\n      |\n      |\n=========```",
    "```\n  +---+\n  O   |\n /|   |\n      |\n      |\n=========```",
    "```\n  +---+\n  O   |\n /|\\  |\n      |\n      |\n=========```",
    "```\n  +---+\n  O   |\n /|\\  |\n /    |\n      |\n=========```",
    "```\n  +---+\n  O   |\n /|\\  |\n / \\  |\n      |\n=========```",
]


def normalize(text):
    """Supprime les accents pour la comparaison"""
    nfkd = unicodedata.normalize('NFKD', text.lower())
    return ''.join(c for c in nfkd if not unicodedata.combining(c))


def remove_xp(user_id, amount):
    """Retire de l'XP du solde uniquement (sans affecter le niveau/total_xp)"""
    stats = get_user_stats(user_id)
    stats["xp"] = max(0, stats.get("xp", 0) - amount)
    sauvegarder_donnees()


def fmt_deadline(seconds_from_now):
    """Retourne un timestamp Discord relatif (ex: <t:1234567890:R>)"""
    return f"<t:{int(time.time()) + int(seconds_from_now)}:R>"


def format_countdown(remaining_seconds, total_seconds, bar_length=12):
    """Construit une ligne de compte à rebours : '⏱️ 00:27 🟩🟩🟩⬜⬜⬜'"""
    remaining = max(0, int(remaining_seconds))
    total = max(1, int(total_seconds))
    mins = remaining // 60
    secs = remaining % 60
    ratio = min(1.0, max(0.0, remaining / total))
    filled = round(ratio * bar_length)
    # Couleur de la barre selon temps restant
    if ratio > 0.5:
        cell = "🟩"
    elif ratio > 0.25:
        cell = "🟨"
    else:
        cell = "🟥"
    bar = cell * filled + "⬛" * (bar_length - filled)
    return f"⏱️ **{mins:02d}:{secs:02d}** `{bar}`"


def build_timer_embed(remaining_seconds, total_seconds, title="⏱️ Temps restant"):
    """Construit un embed dédié au compte à rebours (séparé du jeu)."""
    remaining = max(0, remaining_seconds)
    total = max(1, total_seconds)
    ratio = remaining / total
    if ratio > 0.5:
        color = 0x2ECC71  # vert
    elif ratio > 0.25:
        color = 0xF1C40F  # jaune
    else:
        color = 0xE74C3C  # rouge
    return discord.Embed(
        title=title,
        description=format_countdown(remaining, total),
        color=color,
    )


async def finalize_timer(timer_msg, status="⌛ Temps écoulé !", color=None):
    """Édite le message timer pour afficher l'état final (fin de jeu)."""
    if timer_msg is None:
        return
    try:
        await timer_msg.edit(embed=discord.Embed(
            title="⏱️ Terminé",
            description=status,
            color=color if color is not None else 0x95A5A6,  # gris
        ))
    except (discord.NotFound, discord.Forbidden, discord.HTTPException):
        pass


async def run_countdown(message, state, rebuild_embed, interval=3):
    """Tâche d'arrière-plan qui édite l'embed pour mettre à jour le compte à rebours.

    - state: dict partagé contenant au minimum `deadline` (timestamp unix) et
      éventuellement `ended` (bool) pour stopper proprement.
    - rebuild_embed(remaining_seconds): callable retournant un discord.Embed à jour.
    - interval: intervalle (secondes) entre deux éditions (>=2s pour éviter le
      rate-limit Discord).
    """
    try:
        # Petit délai initial : laisse le main code entrer dans wait_for avant
        # le premier tick, et évite de ré-éditer immédiatement après ctx.send()
        await asyncio.sleep(1.0)

        while True:
            if state.get("ended"):
                return
            remaining = state.get("deadline", 0) - time.time()
            if remaining <= 0:
                return

            # Construction de l'embed (protégée : si le rebuild crash,
            # on log la trace et on arrête pour ne pas boucler à l'infini)
            try:
                embed = rebuild_embed(remaining)
            except Exception:
                logger.exception("run_countdown: rebuild_embed a crashé")
                return

            try:
                await message.edit(embed=embed)
            except asyncio.CancelledError:
                raise
            except discord.NotFound:
                return
            except discord.Forbidden:
                logger.warning("run_countdown: edit refusé (Forbidden)")
                return
            except discord.HTTPException as e:
                # Rate-limit ou autre erreur HTTP transitoire : on loggue et on continue
                logger.warning(f"run_countdown: edit HTTP échoué ({e}) — on continue")
            except Exception:
                logger.exception("run_countdown: edit inattendu")
                return

            # Sleep jusqu'au prochain tick, sans dépasser le temps restant
            sleep_for = min(interval, max(0.5, remaining))
            try:
                await asyncio.sleep(sleep_for)
            except asyncio.CancelledError:
                raise
    except asyncio.CancelledError:
        return
    except Exception:
        logger.exception("run_countdown: erreur fatale")


async def stop_countdown(task, state):
    """Arrête proprement une tâche de countdown et attend sa fin.

    Garantit que la tâche ne produira plus d'édition APRÈS cet appel, ce qui
    évite qu'un tick résiduel n'écrase l'embed final de fin de jeu.
    """
    if state is not None:
        state["ended"] = True
    if task is None or task.done():
        return
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
    except Exception:
        logger.exception("stop_countdown: erreur en attendant la tâche")


async def announce_level_up_safe(bot, user_id, new_level):
    """Annonce un level-up sans casser le flux du jeu en cas d'erreur."""
    try:
        cog = bot.get_cog("CommunitySystem")
        if cog:
            await cog.announce_level_up(user_id, new_level)
    except Exception as e:
        logger.warning(f"announce_level_up failed: {e}")


def apply_win_xp(user_id, base_xp, source):
    """Helper local : applique l'XP gagnée avec streak + featured via effects.

    Retourne (xp_earned, level_up, new_level, info) — info contient
    {streak, streak_mult, featured, shielded, frozen} pour affichage.
    """
    final, _total_mult, level_up, new_level, info = apply_minigame_xp(
        user_id, base_xp, won=True, source=source
    )
    return final, level_up, new_level, info


def apply_loss_xp(user_id, base_xp, source):
    """Helper local : applique la défaite (reset streak, éventuel freeze)."""
    final, _total_mult, level_up, new_level, info = apply_minigame_xp(
        user_id, base_xp, won=False, source=source
    )
    return final, level_up, new_level, info


def bonus_line(info):
    """Construit une petite ligne résumant streak + featured à afficher après une victoire."""
    parts = []
    streak = info.get("streak", 0)
    mult = info.get("streak_mult", 1.0)
    if streak >= 3:
        parts.append(f"🔥 **Streak x{streak}** (x{mult:g} XP)")
    if info.get("featured"):
        parts.append(f"⭐ **Jeu vedette** (x{FEATURED_MULTIPLIER:g} XP)")
    if info.get("shielded"):
        parts.append("🛡️ Bouclier consommé")
    if info.get("frozen"):
        parts.append("🧊 Perte annulée (Level Freeze)")
    return " • ".join(parts) if parts else ""


# ═══════════════════════════════════════════════════════════════════════════════
# VIEWS — Invitations par bouton
# ═══════════════════════════════════════════════════════════════════════════════

class WesternDuelView(discord.ui.View):
    """Duel Far West tour par tour avec HP et dégâts RNG.

    Chaque joueur a 100 HP. À son tour, le joueur actif clique sur **🔫 Tirer**.
    Les dégâts varient :
      • 10 % → miss (0 dmg)
      •  8 % → esquive de l'adversaire
      • 77 % → touché (10-22 dmg)
      •  5 % → touché grave (28-42 dmg, 🎯)

    Le premier à 0 HP perd. Un timer de 30 s par tour évite le blocage : si le
    joueur actif ne tire pas à temps, son arme s'enraye et il perd son tour.
    """

    MAX_HP = 100
    TURN_TIMEOUT = 30.0

    def __init__(self, bot, p1_id: int, p2_id: int, p1_name: str, p2_name: str):
        super().__init__(timeout=None)  # on gère nous-mêmes via asyncio
        self.bot = bot
        self.p1_id = p1_id
        self.p2_id = p2_id
        self.p1_name = p1_name
        self.p2_name = p2_name
        self.hp = {p1_id: self.MAX_HP, p2_id: self.MAX_HP}
        self.turn = p1_id  # p1 commence
        self.log = []  # liste de lignes narratives (dernières en haut)
        self.round_num = 1
        self.message = None
        self.finished = False
        self._event = asyncio.Event()
        self._turn_task = None

    # ── Helpers ─────────────────────────────────────────────────────────────

    def _other(self, uid):
        return self.p2_id if uid == self.p1_id else self.p1_id

    def _name(self, uid):
        return self.p1_name if uid == self.p1_id else self.p2_name

    def _hp_bar(self, uid, length=10):
        hp = self.hp[uid]
        filled = int(round(length * hp / self.MAX_HP))
        filled = max(0, min(length, filled))
        if hp > 60:
            full, empty = "🟩", "⬛"
        elif hp > 30:
            full, empty = "🟨", "⬛"
        else:
            full, empty = "🟥", "⬛"
        return full * filled + empty * (length - filled)

    def _render_embed(self, header_line=None):
        title = "🤠 Duel du Far West"
        # Sceneries par tour
        western_scene = (
            "```\n"
            "         ☀️          \n"
            "   🌵       🌵    🌵 \n"
            "────────────────────\n"
            "```"
        )
        lines = [western_scene]

        # Bloc joueurs avec HP bars
        for uid in (self.p1_id, self.p2_id):
            tag = "🔫" if uid == self.turn and not self.finished else "  "
            lines.append(
                f"{tag} **{self._name(uid)}**  `{self._hp_bar(uid)}`  "
                f"{self.hp[uid]}/{self.MAX_HP} HP"
            )

        lines.append("")
        if header_line:
            lines.append(header_line)
            lines.append("")

        # Derniers événements (max 6)
        if self.log:
            lines.append("**📜 Journal**")
            for entry in self.log[-6:]:
                lines.append(f"• {entry}")

        desc = "\n".join(lines)

        color = COLORS["warning"] if not self.finished else COLORS["success"]
        embed = discord.Embed(title=title, description=desc, color=color)
        if not self.finished:
            embed.set_footer(
                text=f"Tour {self.round_num} • C'est à {self._name(self.turn)} de tirer • "
                     f"{int(self.TURN_TIMEOUT)}s par tour"
            )
        return embed

    def _resolve_shot(self, shooter_id):
        """Calcule le résultat d'un tir et met à jour le HP + le log."""
        target_id = self._other(shooter_id)
        roll = random.random()

        if roll < 0.05:
            # Critique
            dmg = random.randint(28, 42)
            self.hp[target_id] = max(0, self.hp[target_id] - dmg)
            self.log.append(
                f"💥 **{self._name(shooter_id)}** touche en plein cœur "
                f"**{self._name(target_id)}** — **{dmg} dégâts** !"
            )
        elif roll < 0.82:
            # Touché standard
            dmg = random.randint(10, 22)
            self.hp[target_id] = max(0, self.hp[target_id] - dmg)
            self.log.append(
                f"🎯 **{self._name(shooter_id)}** tire et touche "
                f"**{self._name(target_id)}** — **{dmg} dégâts**."
            )
        elif roll < 0.92:
            # Miss
            self.log.append(
                f"🤠 **{self._name(shooter_id)}** vise mal, la balle ricoche sur un cactus..."
            )
        else:
            # Esquive
            self.log.append(
                f"💨 **{self._name(target_id)}** plonge au sol et esquive le tir !"
            )

    def _switch_turn(self):
        self.turn = self._other(self.turn)
        if self.turn == self.p1_id:
            self.round_num += 1

    def _check_winner(self):
        if self.hp[self.p1_id] <= 0:
            return self.p2_id
        if self.hp[self.p2_id] <= 0:
            return self.p1_id
        return None

    # ── Timer par tour ──────────────────────────────────────────────────────

    async def _turn_timeout_task(self):
        try:
            await asyncio.sleep(self.TURN_TIMEOUT)
        except asyncio.CancelledError:
            return
        if self.finished:
            return
        # Le joueur actif a laissé expirer son tour → arme enrayée
        loser_of_turn = self.turn
        self.log.append(
            f"⏰ **{self._name(loser_of_turn)}** hésite trop longtemps… son arme s'enraye !"
        )
        self._switch_turn()
        try:
            await self.message.edit(embed=self._render_embed(), view=self)
        except Exception:
            pass
        self._start_turn_timer()

    def _start_turn_timer(self):
        if self._turn_task and not self._turn_task.done():
            self._turn_task.cancel()
        self._turn_task = asyncio.create_task(self._turn_timeout_task())

    # ── Bouton TIRER ────────────────────────────────────────────────────────

    @discord.ui.button(label="TIRER", style=discord.ButtonStyle.danger, emoji="🔫")
    async def fire(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.finished:
            await interaction.response.send_message("Duel terminé.", ephemeral=True)
            return
        if interaction.user.id != self.turn:
            if interaction.user.id in (self.p1_id, self.p2_id):
                await interaction.response.send_message(
                    f"❌ Ce n'est pas ton tour — attends que **{self._name(self.turn)}** tire.",
                    ephemeral=True,
                )
            else:
                await interaction.response.send_message(
                    "❌ Tu n'es pas dans ce duel.", ephemeral=True
                )
            return

        # Annuler le timer en cours
        if self._turn_task and not self._turn_task.done():
            self._turn_task.cancel()

        shooter = interaction.user.id
        self._resolve_shot(shooter)

        # Vérifier victoire
        winner_id = self._check_winner()
        if winner_id is not None:
            self.finished = True
            for child in self.children:
                child.disabled = True
            self.log.append(
                f"🏆 **{self._name(winner_id)}** abat son adversaire et remporte le duel !"
            )
            await interaction.response.edit_message(embed=self._render_embed(), view=self)
            self._event.set()
            self.stop()
            return

        # Changer de tour
        self._switch_turn()
        await interaction.response.edit_message(embed=self._render_embed(), view=self)
        self._start_turn_timer()

    async def start(self, message):
        """À appeler après avoir attaché ce View à un message."""
        self.message = message
        self._start_turn_timer()

    async def wait_finished(self, max_total: float = 600.0):
        try:
            await asyncio.wait_for(self._event.wait(), timeout=max_total)
        except asyncio.TimeoutError:
            pass
        return self._check_winner()


class DuelInviteView(discord.ui.View):
    """Boutons Accepter / Refuser pour une invitation de duel."""

    def __init__(self, challenger_id: int, target_id: int, timeout: float = 60):
        super().__init__(timeout=timeout)
        self.challenger_id = challenger_id
        self.target_id = target_id
        self.result = None  # "accept" | "refuse" | None (timeout)
        self._event = asyncio.Event()

    async def _only_target(self, interaction):
        if interaction.user.id != self.target_id:
            await interaction.response.send_message(
                "❌ Seule la personne défiée peut répondre.", ephemeral=True
            )
            return False
        return True

    @discord.ui.button(label="Accepter", style=discord.ButtonStyle.success, emoji="✅")
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self._only_target(interaction):
            return
        self.result = "accept"
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(view=self)
        self._event.set()
        self.stop()

    @discord.ui.button(label="Refuser", style=discord.ButtonStyle.danger, emoji="❌")
    async def refuse(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self._only_target(interaction):
            return
        self.result = "refuse"
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(view=self)
        self._event.set()
        self.stop()

    async def wait_result(self, timeout: float):
        try:
            await asyncio.wait_for(self._event.wait(), timeout=timeout)
        except asyncio.TimeoutError:
            return None
        return self.result


# ═══════════════════════════════════════════════════════════════════════════════
# COG PRINCIPAL
# ═══════════════════════════════════════════════════════════════════════════════

class MiniGames(commands.Cog):
    """Mini-jeux communautaires pour gagner de l'XP"""

    def __init__(self, bot):
        self.bot = bot
        # channel_id -> {"type": str, "owner_id": int|None}
        self.active_games = {}
        self.boss_data = load_json(BOSS_FILE, {})
        # Migration : ajouter les nouveaux champs si absents (anciens fichiers)
        self.boss_data.setdefault("rotation_index", -1)
        self.boss_data.setdefault("auto_rotate", False)
        self.boss_data.setdefault("history", [])
        self.attack_cooldowns = {}  # user_id -> datetime
        # Dernier jeu vedette annoncé — pour n'annoncer qu'une fois par jour
        self._last_featured_announced = None
        # Tâche d'arrière-plan : check toutes les heures si le boss a expiré
        # ou si un nouveau doit spawn (auto rotation).
        self.boss_rotation_task.start()
        self.featured_rotation_task.start()

    def cog_unload(self):
        try:
            self.boss_rotation_task.cancel()
        except Exception:
            pass
        try:
            self.featured_rotation_task.cancel()
        except Exception:
            pass

    # ─────────────────────────────────────────────────────────────────────────
    # Daily featured minigame — rotation & annonce
    # ─────────────────────────────────────────────────────────────────────────

    @tasks.loop(hours=1)
    async def featured_rotation_task(self):
        """Vérifie chaque heure si un nouveau jeu vedette doit être annoncé.

        Appelle simplement `get_featured_game()` — la logique de rotation est
        dans effects.py (un seul tirage par jour). Si le jeu a changé par
        rapport à la dernière annonce, on poste dans le premier channel de
        `POINTS_ALLOWED_CHANNELS`.
        """
        try:
            game = get_featured_game()
            today = datetime.now().date().isoformat()
            key = f"{today}:{game}"
            if key == self._last_featured_announced:
                return
            self._last_featured_announced = key

            channel = None
            for cid in POINTS_ALLOWED_CHANNELS:
                ch = self.bot.get_channel(cid)
                if ch:
                    channel = ch
                    break
            if not channel:
                return

            cmd_hint = {
                "reaction": "!reaction",
                "unscramble": "!unscramble",
                "wordle": "!wordle",
                "hangman": "!hangman",
                "chain": "!chain",
                "devinette": "!devinette",
                "quoteguess": "!quoteguess",
                "emojirebus": "!emojirebus",
                "anagram": "!anagram",
                "guessmanga": "!guessmanga",
                "opening": "!opening",
                "click": "!click",
                "memory": "!memory",
            }.get(game, f"!{game}")

            embed = discord.Embed(
                title="⭐ Jeu vedette du jour !",
                description=(
                    f"Aujourd'hui, **{game}** rapporte **x{FEATURED_MULTIPLIER:g} XP** !\n"
                    f"Lance-le avec `{cmd_hint}`"
                ),
                color=COLORS["info"],
            )
            embed.set_footer(text="Remis à zéro chaque jour à minuit")
            await channel.send(embed=embed)
        except Exception as e:
            logger.warning(f"featured_rotation_task error: {e}")

    @featured_rotation_task.before_loop
    async def before_featured_rotation_task(self):
        await self.bot.wait_until_ready()

    def _is_game_active(self, channel_id):
        return channel_id in self.active_games

    def _get_game(self, channel_id):
        return self.active_games.get(channel_id)

    def _set_game(self, channel_id, game_type, owner_id=None):
        self.active_games[channel_id] = {"type": game_type, "owner_id": owner_id}

    def _clear_game(self, channel_id):
        self.active_games.pop(channel_id, None)

    # ─────────────────────────────────────────────────────────────────────────
    # LIMITES QUOTIDIENNES
    # ─────────────────────────────────────────────────────────────────────────

    def _is_admin(self, member):
        """Un admin contourne les limites quotidiennes."""
        try:
            from config import ADMIN_ROLES
            roles = getattr(member, "roles", None) or []
            return any(r.name in ADMIN_ROLES for r in roles)
        except Exception:
            return False

    async def _check_daily_limit(self, ctx, game):
        """Vérifie la limite quotidienne (pool partagé par catégorie) et incrémente.

        Retourne True si l'utilisateur peut jouer, False sinon (un message
        d'erreur a déjà été envoyé au joueur).

        Comportement :
        - Chaque jeu appartient à une catégorie (`GAME_CATEGORIES`) qui partage
          un pool unique par utilisateur (`CATEGORY_LIMITS`).
        - Les admins bypass la limite (et ne consomment pas de compteur).
        - Une catégorie sans limite (0 ou absente) passe toujours.
        """
        category = GAME_CATEGORIES.get(game)
        if category is None:
            return True

        limit = CATEGORY_LIMITS.get(category, 0)
        if limit <= 0:
            return True

        if self._is_admin(ctx.author):
            return True

        used = db.get_daily_usage(ctx.author.id, category)
        if used >= limit:
            now = datetime.now()
            next_midnight = (now + timedelta(days=1)).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            reset_unix = int(next_midnight.timestamp())

            label = CATEGORY_LABELS.get(category, category)
            embed = discord.Embed(
                title="🚫 Limite quotidienne atteinte",
                description=(
                    f"{ctx.author.mention}, tu as déjà utilisé **{used}/{limit}** "
                    f"de tes **{label}** aujourd'hui.\n\n"
                    f"⏰ Reset <t:{reset_unix}:R>\n"
                    f"📊 Utilise `!mglimits` pour voir tes compteurs."
                ),
                color=COLORS["error"],
            )
            await ctx.send(embed=embed)
            return False

        db.increment_daily_usage(ctx.author.id, category)
        return True

    # ═══════════════════════════════════════════════════════════════════════════
    # 🎯 REACTION - Jeu de rapidité
    # ═══════════════════════════════════════════════════════════════════════════

    @commands.command(name="reaction")
    @commands.cooldown(1, 30, commands.BucketType.channel)
    async def reaction_game(self, ctx, mode: str = None):
        """Sois le premier à réagir avec le bon emoji !

        `!reaction silent` pour lancer sans ping et sans mention bruyante.
        """
        silent = bool(mode and mode.lower() in ("silent", "silencieux", "mute", "quiet"))
        if self._is_game_active(ctx.channel.id):
            return await ctx.send("❌ Un jeu est déjà en cours dans ce channel !")

        if not await self._check_daily_limit(ctx, "reaction"):
            return

        self._set_game(ctx.channel.id, "reaction", owner_id=None)

        countdown_task = None
        timer_msg = None
        state = {"deadline": 0, "ended": False}
        try:
            target_emoji = random.choice(REACTION_EMOJIS)
            delay = random.uniform(2, 6)

            launcher = "🕶️ *Mode silencieux*" if silent else f"Lancé par {ctx.author.mention}"
            featured_tag = " ⭐" if is_featured("reaction") else ""
            embed = discord.Embed(
                title=f"🎯 Jeu de Réaction{featured_tag}",
                description=(
                    f"{launcher}\n"
                    "Préparez-vous... Un emoji va apparaître !\n"
                    "Soyez le **premier** à réagir avec le bon emoji !"
                ),
                color=COLORS["info"]
            )
            allowed_mentions = discord.AllowedMentions.none() if silent else None
            msg = await ctx.send(embed=embed, allowed_mentions=allowed_mentions)

            await asyncio.sleep(delay)

            react_timeout = 10
            state["deadline"] = time.time() + react_timeout

            await msg.edit(embed=discord.Embed(
                title="🎯 Jeu de Réaction",
                description=f"# RÉAGIS AVEC {target_emoji} !",
                color=0xFF0000,
            ))

            timer_msg = await ctx.send(embed=build_timer_embed(react_timeout, react_timeout))
            countdown_task = asyncio.create_task(
                run_countdown(
                    timer_msg, state,
                    lambda r: build_timer_embed(r, react_timeout),
                    interval=2,
                )
            )

            start_time = time.time()

            def check(reaction, user):
                return (
                    reaction.message.id == msg.id
                    and str(reaction.emoji) == target_emoji
                    and not user.bot
                )

            try:
                reaction, winner = await self.bot.wait_for("reaction_add", check=check, timeout=react_timeout)
                await stop_countdown(countdown_task, state)
                countdown_task = None
                elapsed = time.time() - start_time
                xp_earned, level_up, new_level, info = apply_win_xp(winner.id, MINIGAME_XP["reaction"], "reaction")
                db.record_minigame(winner.id, "reaction", True, xp_earned, duration_seconds=elapsed)

                await finalize_timer(timer_msg, status=f"✅ {winner.display_name} a réagi en {elapsed:.2f}s", color=COLORS["success"])

                bline = bonus_line(info)
                embed = discord.Embed(
                    title="🎯 Réaction — Victoire !",
                    description=(
                        f"{winner.mention} a été le plus rapide !\n"
                        f"⚡ **{elapsed:.2f}s** de réaction\n"
                        f"**+{xp_earned} XP** gagnés !"
                        + (f"\n\n{bline}" if bline else "")
                    ),
                    color=COLORS["success"]
                )
                await msg.edit(embed=embed)

                if level_up:
                    await announce_level_up_safe(self.bot, winner.id, new_level)

            except asyncio.TimeoutError:
                await stop_countdown(countdown_task, state)
                countdown_task = None
                await finalize_timer(timer_msg, status="⌛ Temps écoulé !", color=COLORS["error"])
                embed = discord.Embed(
                    title="🎯 Réaction — Temps écoulé !",
                    description="Personne n'a réagi à temps... 😔",
                    color=COLORS["error"]
                )
                await msg.edit(embed=embed)
        finally:
            await stop_countdown(countdown_task, state)
            self._clear_game(ctx.channel.id)

    # ═══════════════════════════════════════════════════════════════════════════
    # 🔤 UNSCRAMBLE - Mot mélangé
    # ═══════════════════════════════════════════════════════════════════════════

    @commands.command(name="unscramble")
    @commands.cooldown(1, 15, commands.BucketType.user)
    async def unscramble_game(self, ctx):
        """[Solo] Remets les lettres dans le bon ordre !"""
        if self._is_game_active(ctx.channel.id):
            return await ctx.send("❌ Un jeu est déjà en cours dans ce channel !")

        if not await self._check_daily_limit(ctx, "unscramble"):
            return

        self._set_game(ctx.channel.id, "unscramble", owner_id=ctx.author.id)
        total_timeout = 30

        countdown_task = None
        timer_msg = None
        state = {"deadline": 0, "ended": False}
        try:
            _theme_key, theme, word = pick_themed_manga_word()
            scrambled = list(word)
            attempts = 0
            while ''.join(scrambled) == word and attempts < 10:
                random.shuffle(scrambled)
                attempts += 1
            scrambled = ''.join(scrambled).upper()

            state["deadline"] = time.time() + total_timeout

            game_embed = discord.Embed(
                title=f"🔤 Unscramble — {theme['emoji']} {theme['label']}",
                description=(
                    f"👤 Joueur : {ctx.author.mention}\n"
                    f"💡 **Thème :** {theme['emoji']} *{theme['label']}*\n\n"
                    f"# `{scrambled}`\n\n"
                    f"*{len(word)} lettres — réponds dans le chat !*"
                ),
                color=COLORS["info"],
            )
            game_embed.set_footer(text="Jeu solo — seul le joueur qui a lancé peut répondre")
            game_msg = await ctx.send(embed=game_embed)

            timer_msg = await ctx.send(embed=build_timer_embed(total_timeout, total_timeout))
            countdown_task = asyncio.create_task(
                run_countdown(
                    timer_msg, state,
                    lambda r: build_timer_embed(r, total_timeout),
                    interval=3,
                )
            )

            def check(m):
                return (
                    m.channel.id == ctx.channel.id
                    and m.author.id == ctx.author.id
                    and normalize(m.content.strip()) == normalize(word)
                )

            start = time.time()
            try:
                msg = await self.bot.wait_for("message", check=check, timeout=total_timeout)
                await stop_countdown(countdown_task, state)
                countdown_task = None

                elapsed = time.time() - start
                xp_earned, level_up, new_level, info = apply_win_xp(ctx.author.id, MINIGAME_XP["unscramble"], "unscramble")
                db.record_minigame(ctx.author.id, "unscramble", True, xp_earned, duration_seconds=elapsed)

                await finalize_timer(timer_msg, status=f"✅ Trouvé en {elapsed:.1f}s", color=COLORS["success"])

                bline = bonus_line(info)
                win_embed = discord.Embed(
                    title="🔤 Unscramble — Bravo !",
                    description=(
                        f"{ctx.author.mention} a trouvé le mot **{word.upper()}** !\n"
                        f"💡 Thème : {theme['emoji']} *{theme['label']}*\n"
                        f"⚡ Résolu en **{elapsed:.1f}s**\n"
                        f"**+{xp_earned} XP** gagnés !"
                        + (f"\n\n{bline}" if bline else "")
                    ),
                    color=COLORS["success"],
                )
                await game_msg.edit(embed=win_embed)

                if level_up:
                    await announce_level_up_safe(self.bot, ctx.author.id, new_level)

            except asyncio.TimeoutError:
                await stop_countdown(countdown_task, state)
                countdown_task = None
                db.record_minigame(ctx.author.id, "unscramble", False, 0)
                apply_loss_xp(ctx.author.id, 0, "unscramble")
                await finalize_timer(timer_msg, status="⌛ Temps écoulé !", color=COLORS["error"])
                lose_embed = discord.Embed(
                    title="🔤 Unscramble — Temps écoulé !",
                    description=(
                        f"{ctx.author.mention}, le mot était **{word.upper()}**\n"
                        f"💡 Thème : {theme['emoji']} *{theme['label']}*"
                    ),
                    color=COLORS["error"],
                )
                await game_msg.edit(embed=lose_embed)
        finally:
            await stop_countdown(countdown_task, state)
            self._clear_game(ctx.channel.id)

    # ═══════════════════════════════════════════════════════════════════════════
    # 🪙 COINFLIP - Pile ou Face
    # ═══════════════════════════════════════════════════════════════════════════

    @commands.command(name="coinflip", aliases=["cf"])
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def coinflip(self, ctx, mise: int = None):
        """Pile ou face ! Mise ton XP (x2 ou perdu)"""
        if mise is None:
            return await ctx.send("❌ Usage : `!coinflip <montant>`")

        if mise < 5:
            return await ctx.send("❌ Mise minimum : **5 XP**")

        stats = get_user_stats(ctx.author.id)
        if stats.get("xp", 0) < mise:
            return await ctx.send(f"❌ Tu n'as que **{stats.get('xp', 0):,} XP** !")

        if not await self._check_daily_limit(ctx, "coinflip"):
            return

        result = random.choice(["pile", "face"])
        win = random.random() < 0.5

        embed = discord.Embed(title="🪙 Coinflip", color=COLORS["info"])
        embed.description = "La pièce tourne..."
        msg = await ctx.send(embed=embed)

        await asyncio.sleep(1.5)

        if win:
            xp_earned, _, level_up, new_level = add_xp(ctx.author.id, mise, "coinflip_win")
            db.record_minigame(ctx.author.id, "coinflip", True, xp_earned)
            new_balance = get_user_stats(ctx.author.id).get("xp", 0)
            embed.title = f"🪙 {result.upper()} — Tu gagnes !"
            embed.description = f"**+{xp_earned} XP** gagnés !\n💰 Solde : {new_balance:,} XP"
            embed.color = COLORS["success"]

            if level_up:
                await announce_level_up_safe(self.bot, ctx.author.id, new_level)
        else:
            remove_xp(ctx.author.id, mise)
            db.record_minigame(ctx.author.id, "coinflip", False, -mise)
            new_balance = get_user_stats(ctx.author.id).get("xp", 0)
            embed.title = f"🪙 {result.upper()} — Tu perds !"
            embed.description = f"**-{mise} XP** perdus...\n💰 Solde : {new_balance:,} XP"
            embed.color = COLORS["error"]

        await msg.edit(embed=embed)

    # ═══════════════════════════════════════════════════════════════════════════
    # 🎰 SLOTS - Machine à sous
    # ═══════════════════════════════════════════════════════════════════════════

    @commands.command(name="slots")
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def slots(self, ctx, mise: int = None):
        """Machine à sous ! 3 identiques = jackpot"""
        if mise is None:
            return await ctx.send("❌ Usage : `!slots <montant>`")

        if mise < 5:
            return await ctx.send("❌ Mise minimum : **5 XP**")

        stats = get_user_stats(ctx.author.id)
        if stats.get("xp", 0) < mise:
            return await ctx.send(f"❌ Tu n'as que **{stats.get('xp', 0):,} XP** !")

        if not await self._check_daily_limit(ctx, "slots"):
            return

        # Tirer 3 emojis
        reels = [random.choice(SLOT_EMOJIS) for _ in range(3)]

        embed = discord.Embed(title="🎰 Machine à Sous", color=COLORS["info"])
        embed.description = "Les rouleaux tournent..."
        msg = await ctx.send(embed=embed)

        await asyncio.sleep(1.5)

        display = f"# {reels[0]} | {reels[1]} | {reels[2]}"

        # Vérifier les gains
        if reels[0] == reels[1] == reels[2]:
            # Jackpot — 3 identiques
            if reels[0] == "7️⃣":
                multiplier = 15
                title = "🎰 MEGA JACKPOT !!! 🎆"
            elif reels[0] == "💎":
                multiplier = 10
                title = "🎰 JACKPOT DIAMANT ! 💎"
            else:
                multiplier = 5
                title = "🎰 JACKPOT !"

            gain = mise * multiplier
            xp_earned, _, level_up, new_level = add_xp(ctx.author.id, gain, "slots_jackpot")
            db.record_minigame(ctx.author.id, "slots", True, xp_earned)
            embed.title = title
            embed.description = f"{display}\n\n🎉 **x{multiplier}** — **+{xp_earned} XP** !"
            embed.color = 0xFFD700

            if level_up:
                await announce_level_up_safe(self.bot, ctx.author.id, new_level)

        elif reels[0] == reels[1] or reels[1] == reels[2] or reels[0] == reels[2]:
            # 2 identiques
            gain = mise
            xp_earned, _, level_up, new_level = add_xp(ctx.author.id, gain, "slots_small")
            db.record_minigame(ctx.author.id, "slots", True, xp_earned)
            embed.title = "🎰 Petite victoire !"
            embed.description = f"{display}\n\n**+{xp_earned} XP** gagnés !"
            embed.color = COLORS["success"]

            if level_up:
                await announce_level_up_safe(self.bot, ctx.author.id, new_level)
        else:
            # Perdu
            remove_xp(ctx.author.id, mise)
            db.record_minigame(ctx.author.id, "slots", False, -mise)
            embed.title = "🎰 Perdu..."
            embed.description = f"{display}\n\n**-{mise} XP** perdus"
            embed.color = COLORS["error"]

        embed.set_footer(text=f"💰 Solde : {get_user_stats(ctx.author.id).get('xp', 0):,} XP")
        await msg.edit(embed=embed)

    # ═══════════════════════════════════════════════════════════════════════════
    # 🎡 ROULETTE
    # ═══════════════════════════════════════════════════════════════════════════

    @commands.command(name="roulette")
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def roulette(self, ctx, mise: int = None, *, choix: str = None):
        """Roulette ! Mise sur rouge, noir ou un numéro (0-36)"""
        if mise is None or choix is None:
            embed = discord.Embed(
                title="🎡 Roulette — Comment jouer",
                description=(
                    "`!roulette <mise> rouge` — x2\n"
                    "`!roulette <mise> noir` — x2\n"
                    "`!roulette <mise> vert` — x14\n"
                    "`!roulette <mise> <0-36>` — x10"
                ),
                color=COLORS["info"]
            )
            return await ctx.send(embed=embed)

        if mise < 5:
            return await ctx.send("❌ Mise minimum : **5 XP**")

        stats = get_user_stats(ctx.author.id)
        if stats.get("xp", 0) < mise:
            return await ctx.send(f"❌ Tu n'as que **{stats.get('xp', 0):,} XP** !")

        choix = choix.lower().strip()

        # Valider le choix
        bet_type = None
        bet_number = None
        if choix in ("rouge", "red"):
            bet_type = "rouge"
        elif choix in ("noir", "black"):
            bet_type = "noir"
        elif choix in ("vert", "green"):
            bet_type = "vert"
        elif choix.isdigit() and 0 <= int(choix) <= 36:
            bet_type = "number"
            bet_number = int(choix)
        else:
            return await ctx.send("❌ Choix invalide ! Utilise `rouge`, `noir`, `vert` ou un numéro `0-36`")

        if not await self._check_daily_limit(ctx, "roulette"):
            return

        # Tirer le résultat
        result = random.randint(0, 36)
        rouges = {1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36}
        if result == 0:
            result_color = "vert"
            result_emoji = "🟢"
        elif result in rouges:
            result_color = "rouge"
            result_emoji = "🔴"
        else:
            result_color = "noir"
            result_emoji = "⚫"

        embed = discord.Embed(title="🎡 Roulette", description="La bille tourne...", color=COLORS["info"])
        msg = await ctx.send(embed=embed)
        await asyncio.sleep(2)

        # Calculer le gain
        win = False
        multiplier = 0
        if bet_type == "rouge" and result_color == "rouge":
            win, multiplier = True, 2
        elif bet_type == "noir" and result_color == "noir":
            win, multiplier = True, 2
        elif bet_type == "vert" and result_color == "vert":
            win, multiplier = True, 14
        elif bet_type == "number" and result == bet_number:
            win, multiplier = True, 10

        result_text = f"{result_emoji} **{result}** ({result_color})"

        if win:
            gain = mise * (multiplier - 1)
            xp_earned, _, level_up, new_level = add_xp(ctx.author.id, gain, "roulette_win")
            db.record_minigame(ctx.author.id, "roulette", True, xp_earned)
            embed.title = "🎡 Roulette — Tu gagnes !"
            embed.description = f"{result_text}\n\n**x{multiplier}** — **+{xp_earned} XP** !"
            embed.color = COLORS["success"]

            if level_up:
                await announce_level_up_safe(self.bot, ctx.author.id, new_level)
        else:
            remove_xp(ctx.author.id, mise)
            db.record_minigame(ctx.author.id, "roulette", False, -mise)
            embed.title = "🎡 Roulette — Perdu..."
            embed.description = f"{result_text}\n\n**-{mise} XP** perdus"
            embed.color = COLORS["error"]

        embed.set_footer(text=f"💰 Solde : {get_user_stats(ctx.author.id).get('xp', 0):,} XP")
        await msg.edit(embed=embed)

    # ═══════════════════════════════════════════════════════════════════════════
    # ⚔️ DUEL - PvP avec mise d'XP
    # ═══════════════════════════════════════════════════════════════════════════

    @commands.command(name="duel")
    @commands.cooldown(1, 30, commands.BucketType.user)
    async def duel(self, ctx, adversaire: discord.Member = None, mise: int = None):
        """Défie un autre membre en duel ! Le gagnant prend la mise"""
        if adversaire is None or mise is None:
            return await ctx.send("❌ Usage : `!duel @adversaire <mise>`")

        if adversaire.bot or adversaire.id == ctx.author.id:
            return await ctx.send("❌ Tu ne peux pas te défier toi-même ou un bot !")

        if mise < MINIGAME_XP["duel_min_bet"]:
            return await ctx.send(f"❌ Mise minimum : **{MINIGAME_XP['duel_min_bet']} XP**")

        # Vérifier les soldes
        stats_challenger = get_user_stats(ctx.author.id)
        stats_opponent = get_user_stats(adversaire.id)

        if stats_challenger.get("xp", 0) < mise:
            return await ctx.send(f"❌ Tu n'as que **{stats_challenger.get('xp', 0):,} XP** !")
        if stats_opponent.get("xp", 0) < mise:
            return await ctx.send(f"❌ {adversaire.display_name} n'a que **{stats_opponent.get('xp', 0):,} XP** !")

        if not await self._check_daily_limit(ctx, "duel"):
            return

        # Demander l'acceptation — via boutons (plus besoin de réactions)
        accept_timeout = 60
        duel_state = {"deadline": time.time() + accept_timeout, "ended": False}

        view = DuelInviteView(ctx.author.id, adversaire.id, timeout=accept_timeout)

        invite_embed = discord.Embed(
            title="⚔️ Défi en Duel !",
            description=(
                f"{ctx.author.mention} défie {adversaire.mention} !\n"
                f"💰 Mise : **{mise} XP**\n\n"
                f"{adversaire.mention}, clique sur un bouton ci-dessous."
            ),
            color=COLORS["warning"],
        )
        msg = await ctx.send(embed=invite_embed, view=view)

        timer_msg = await ctx.send(embed=build_timer_embed(accept_timeout, accept_timeout, title="⏱️ Temps pour accepter"))
        duel_countdown = asyncio.create_task(
            run_countdown(
                timer_msg, duel_state,
                lambda r: build_timer_embed(r, accept_timeout, title="⏱️ Temps pour accepter"),
                interval=3,
            )
        )

        result = await view.wait_result(accept_timeout)
        await stop_countdown(duel_countdown, duel_state)

        if result is None:
            await finalize_timer(timer_msg, status="⌛ Pas de réponse", color=COLORS["error"])
            for child in view.children:
                child.disabled = True
            expired = discord.Embed(
                title="⚔️ Duel expiré",
                description="Pas de réponse... Le duel est annulé.",
                color=COLORS["error"],
            )
            return await msg.edit(embed=expired, view=view)

        if result == "refuse":
            await finalize_timer(timer_msg, status="❌ Duel refusé", color=COLORS["error"])
            refused = discord.Embed(
                title="⚔️ Duel refusé",
                description=f"{adversaire.display_name} a refusé le duel.",
                color=COLORS["error"],
            )
            return await msg.edit(embed=refused, view=view)

        await finalize_timer(timer_msg, status="✅ Défi accepté !", color=COLORS["success"])

        # ── Combat Far West ─────────────────────────────────────────────────
        # Intro cinématique "High Noon"
        intro_embed = discord.Embed(
            title="🤠 Duel du Far West",
            description=(
                "```\n"
                "       ☀️  HIGH NOON  ☀️       \n"
                "   🌵              🌵         \n"
                "────────────────────────────\n"
                "```\n"
                f"**{ctx.author.display_name}** fait face à **{adversaire.display_name}**...\n"
                f"💰 Mise : **{mise} XP** • HP : **100/100** chacun\n\n"
                "*Le soleil tape. Le vent soulève la poussière.*\n"
                "*Chacun son tour, cliquez sur 🔫 **TIRER** pour dégainer !*"
            ),
            color=COLORS["warning"],
        )
        await msg.edit(embed=intro_embed, view=None)
        await asyncio.sleep(3)

        western = WesternDuelView(
            self.bot,
            p1_id=ctx.author.id,
            p2_id=adversaire.id,
            p1_name=ctx.author.display_name,
            p2_name=adversaire.display_name,
        )
        await msg.edit(embed=western._render_embed(), view=western)
        await western.start(msg)

        winner_id = await western.wait_finished(max_total=600.0)

        if winner_id is None:
            # Aucun vainqueur (timeout global) — match nul
            draw_embed = discord.Embed(
                title="🤠 Duel avorté",
                description=(
                    "Le duel s'éternise… les deux pistoleros rengainent.\n"
                    "Aucune mise n'est transférée."
                ),
                color=COLORS["info"],
            )
            try:
                await msg.edit(embed=draw_embed, view=None)
            except Exception:
                pass
            return

        if winner_id == ctx.author.id:
            winner, loser = ctx.author, adversaire
        else:
            winner, loser = adversaire, ctx.author

        # Transférer l'XP
        xp_earned, _, level_up, new_level = add_xp(winner.id, mise, "duel_win")
        remove_xp(loser.id, mise)
        db.record_minigame(winner.id, "duel", True, xp_earned)
        db.record_minigame(loser.id, "duel", False, -mise)

        winner_hp = western.hp[winner.id]
        win_embed = discord.Embed(
            title=f"🏆 {winner.display_name} remporte le duel !",
            description=(
                f"```\n"
                f"     🤠 🔫      💀    \n"
                f"   VAINQUEUR   ABATTU \n"
                f"```\n"
                f"❤️ HP restant : **{winner_hp}/100**\n"
                f"🎯 {winner.mention} gagne **+{xp_earned} XP** !\n"
                f"💀 {loser.display_name} perd **-{mise} XP**"
            ),
            color=COLORS["success"],
        )
        try:
            await msg.edit(embed=win_embed, view=None)
        except Exception:
            pass

        if level_up:
            await announce_level_up_safe(self.bot, winner.id, new_level)

    # ═══════════════════════════════════════════════════════════════════════════
    # 🟩 WORDLE - Deviner un mot en 6 essais
    # ═══════════════════════════════════════════════════════════════════════════

    @commands.command(name="wordle")
    @commands.cooldown(1, 30, commands.BucketType.user)
    async def wordle(self, ctx):
        """[Solo] Devine le mot en 6 essais ! 🟩 = bonne place, 🟨 = mauvaise place, ⬛ = absent"""
        if self._is_game_active(ctx.channel.id):
            return await ctx.send("❌ Un jeu est déjà en cours dans ce channel !")

        if not await self._check_daily_limit(ctx, "wordle"):
            return

        self._set_game(ctx.channel.id, "wordle", owner_id=ctx.author.id)
        per_turn_timeout = 60

        countdown_task = None
        timer_msg = None
        state = {
            "deadline": 0,
            "ended": False,
            "remaining_attempts": 6,
        }
        try:
            _theme_key, theme, word = pick_themed_wordle_word()
            word_normalized = normalize(word)
            word_len = len(word_normalized)
            max_attempts = 6
            attempts = []
            start_time = time.time()

            state["deadline"] = time.time() + per_turn_timeout
            state["remaining_attempts"] = max_attempts

            def render_embed(title=None, color=None, status_line=None):
                desc_lines = [
                    f"👤 Joueur : {ctx.author.mention}",
                    f"💡 **Thème :** {theme['emoji']} *{theme['label']}*",
                    f"📏 **{word_len} lettres** — **{state['remaining_attempts']}/{max_attempts}** essais restants",
                    "",
                ]
                if attempts:
                    desc_lines.append("\n".join(attempts))
                    desc_lines.append("")
                desc_lines.append("🟩 bonne place · 🟨 mauvaise place · ⬛ absente")
                if status_line:
                    desc_lines.append("")
                    desc_lines.append(status_line)
                e = discord.Embed(
                    title=title or f"🟩 Wordle — {theme['emoji']} {theme['label']}",
                    description="\n".join(desc_lines),
                    color=color if color is not None else COLORS["info"],
                )
                e.set_footer(text="Jeu solo — tape ton essai dans le chat")
                return e

            game_msg = await ctx.send(embed=render_embed())
            timer_msg = await ctx.send(embed=build_timer_embed(per_turn_timeout, per_turn_timeout))
            countdown_task = asyncio.create_task(
                run_countdown(
                    timer_msg, state,
                    lambda r: build_timer_embed(r, per_turn_timeout),
                    interval=3,
                )
            )

            for attempt_num in range(1, max_attempts + 1):
                state["deadline"] = time.time() + per_turn_timeout
                state["remaining_attempts"] = max_attempts - attempt_num + 1

                def check(m):
                    return (
                        m.channel.id == ctx.channel.id
                        and m.author.id == ctx.author.id
                        and len(normalize(m.content.strip())) == word_len
                        and m.content.strip().isalpha()
                    )

                try:
                    msg = await self.bot.wait_for("message", check=check, timeout=per_turn_timeout)
                except asyncio.TimeoutError:
                    await stop_countdown(countdown_task, state)
                    countdown_task = None
                    db.record_minigame(ctx.author.id, "wordle", False, 0)
                    await finalize_timer(timer_msg, status="⌛ Temps écoulé !", color=COLORS["error"])
                    return await game_msg.edit(embed=render_embed(
                        title="🟩 Wordle — Temps écoulé !",
                        color=COLORS["error"],
                        status_line=f"⌛ Plus de temps... Le mot était **{word.upper()}**",
                    ))

                guess = normalize(msg.content.strip())

                word_chars = list(word_normalized)
                guess_chars = list(guess)
                result = ["⬛"] * word_len

                for i in range(word_len):
                    if guess_chars[i] == word_chars[i]:
                        result[i] = "🟩"
                        word_chars[i] = None
                        guess_chars[i] = None

                for i in range(word_len):
                    if guess_chars[i] is not None and guess_chars[i] in word_chars:
                        result[i] = "🟨"
                        word_chars[word_chars.index(guess_chars[i])] = None

                feedback_str = "".join(result)
                attempts.append(f"{feedback_str} `{guess.upper()}`")

                if guess == word_normalized:
                    elapsed = time.time() - start_time
                    bonus = max(10, MINIGAME_XP["wordle"] + (max_attempts - attempt_num) * 10)
                    xp_earned, level_up, new_level, info = apply_win_xp(ctx.author.id, bonus, "wordle")
                    db.record_minigame(ctx.author.id, "wordle", True, xp_earned, duration_seconds=elapsed)

                    await stop_countdown(countdown_task, state)
                    countdown_task = None
                    state["remaining_attempts"] = max_attempts - attempt_num
                    await finalize_timer(timer_msg, status=f"✅ Trouvé en {elapsed:.1f}s", color=COLORS["success"])

                    bline = bonus_line(info)
                    await game_msg.edit(embed=render_embed(
                        title="🟩 Wordle — Bravo !",
                        color=COLORS["success"],
                        status_line=(
                            f"🎉 Trouvé en **{attempt_num}/{max_attempts}** essais "
                            f"(⚡ {elapsed:.1f}s) — **+{xp_earned} XP** !"
                            + (f"\n{bline}" if bline else "")
                        ),
                    ))

                    if level_up:
                        await announce_level_up_safe(self.bot, ctx.author.id, new_level)
                    return

                remaining = max_attempts - attempt_num
                if remaining > 0:
                    state["deadline"] = time.time() + per_turn_timeout
                    state["remaining_attempts"] = remaining
                    await game_msg.edit(embed=render_embed())

            # Défaite : tous les essais épuisés
            await stop_countdown(countdown_task, state)
            countdown_task = None
            state["remaining_attempts"] = 0
            db.record_minigame(ctx.author.id, "wordle", False, 0)
            apply_loss_xp(ctx.author.id, 0, "wordle")
            await finalize_timer(timer_msg, status="❌ Tous les essais épuisés", color=COLORS["error"])
            await game_msg.edit(embed=render_embed(
                title="🟩 Wordle — Perdu !",
                color=COLORS["error"],
                status_line=f"💀 Le mot était **{word.upper()}**",
            ))

        finally:
            await stop_countdown(countdown_task, state)
            self._clear_game(ctx.channel.id)

    # ═══════════════════════════════════════════════════════════════════════════
    # 💀 HANGMAN - Pendu
    # ═══════════════════════════════════════════════════════════════════════════

    @commands.command(name="hangman", aliases=["pendu"])
    @commands.cooldown(1, 15, commands.BucketType.user)
    async def hangman(self, ctx):
        """[Solo] Jeu du pendu ! Devine le mot lettre par lettre"""
        if self._is_game_active(ctx.channel.id):
            return await ctx.send("❌ Un jeu est déjà en cours dans ce channel !")

        if not await self._check_daily_limit(ctx, "hangman"):
            return

        self._set_game(ctx.channel.id, "hangman", owner_id=ctx.author.id)
        per_turn_timeout = 60

        countdown_task = None
        timer_msg = None
        state = {
            "deadline": 0,
            "ended": False,
            "wrong": 0,
            "max_wrong": len(HANGMAN_STAGES) - 1,
        }
        try:
            _theme_key, theme, word = pick_themed_manga_word()
            word_normalized = normalize(word)
            guessed_letters = set()
            start_time = time.time()

            state["deadline"] = time.time() + per_turn_timeout

            def get_display():
                return " ".join(
                    c.upper() if normalize(c) in guessed_letters else "\\_"
                    for c in word
                )

            def build_embed(title=None, color=None, status_line=None):
                wrong = state["wrong"]
                max_wrong = state["max_wrong"]
                desc_lines = [
                    f"👤 Joueur : {ctx.author.mention}",
                    f"💡 **Thème :** {theme['emoji']} *{theme['label']}*",
                    f"❤️ Vies : **{max_wrong - wrong}/{max_wrong}**",
                ]
                desc_lines.append(HANGMAN_STAGES[wrong])
                desc_lines.append(f"**{get_display()}**  *({len(word)} lettres)*")
                if status_line:
                    desc_lines.append("")
                    desc_lines.append(status_line)
                e = discord.Embed(
                    title=title or f"💀 Pendu — {theme['emoji']} {theme['label']}",
                    description="\n".join(desc_lines),
                    color=color if color is not None else COLORS["info"],
                )
                if guessed_letters:
                    e.add_field(
                        name="Lettres essayées",
                        value=" ".join(sorted(l.upper() for l in guessed_letters)),
                        inline=False,
                    )
                e.set_footer(text="Jeu solo — tape une lettre dans le chat")
                return e

            game_msg = await ctx.send(embed=build_embed())
            timer_msg = await ctx.send(embed=build_timer_embed(per_turn_timeout, per_turn_timeout))
            countdown_task = asyncio.create_task(
                run_countdown(
                    timer_msg, state,
                    lambda r: build_timer_embed(r, per_turn_timeout),
                    interval=3,
                )
            )

            while state["wrong"] < state["max_wrong"]:
                state["deadline"] = time.time() + per_turn_timeout

                def check(m):
                    return (
                        m.channel.id == ctx.channel.id
                        and m.author.id == ctx.author.id
                        and len(m.content.strip()) == 1
                        and m.content.strip().isalpha()
                    )

                try:
                    msg = await self.bot.wait_for("message", check=check, timeout=per_turn_timeout)
                except asyncio.TimeoutError:
                    await stop_countdown(countdown_task, state)
                    countdown_task = None
                    db.record_minigame(ctx.author.id, "hangman", False, 0)
                    await finalize_timer(timer_msg, status="⌛ Temps écoulé !", color=COLORS["error"])
                    return await game_msg.edit(embed=build_embed(
                        title="💀 Pendu — Temps écoulé !",
                        color=COLORS["error"],
                        status_line=f"⌛ Le mot était **{word.upper()}**",
                    ))

                letter = normalize(msg.content.strip().lower())

                if letter in guessed_letters:
                    try:
                        await msg.reply(f"❌ `{letter.upper()}` déjà essayée !", delete_after=3)
                    except Exception:
                        pass
                    continue

                guessed_letters.add(letter)

                if letter in word_normalized:
                    if all(normalize(c) in guessed_letters for c in word):
                        elapsed = time.time() - start_time
                        xp_earned, level_up, new_level, info = apply_win_xp(ctx.author.id, MINIGAME_XP["hangman"], "hangman")
                        db.record_minigame(ctx.author.id, "hangman", True, xp_earned, duration_seconds=elapsed)

                        await stop_countdown(countdown_task, state)
                        countdown_task = None
                        await finalize_timer(timer_msg, status=f"✅ Trouvé en {elapsed:.1f}s", color=COLORS["success"])

                        bline = bonus_line(info)
                        await game_msg.edit(embed=build_embed(
                            title="💀 Pendu — Victoire !",
                            color=COLORS["success"],
                            status_line=(
                                f"🎉 Mot trouvé : **{word.upper()}** "
                                f"(⚡ {elapsed:.1f}s) — **+{xp_earned} XP** !"
                                + (f"\n{bline}" if bline else "")
                            ),
                        ))

                        if level_up:
                            await announce_level_up_safe(self.bot, ctx.author.id, new_level)
                        return
                else:
                    state["wrong"] += 1

                # Reset deadline pour le tour suivant
                state["deadline"] = time.time() + per_turn_timeout
                await game_msg.edit(embed=build_embed())

            # Défaite
            await stop_countdown(countdown_task, state)
            countdown_task = None
            db.record_minigame(ctx.author.id, "hangman", False, 0)
            apply_loss_xp(ctx.author.id, 0, "hangman")
            await finalize_timer(timer_msg, status="💀 Pendu", color=COLORS["error"])
            await game_msg.edit(embed=build_embed(
                title="💀 Pendu — Défaite !",
                color=COLORS["error"],
                status_line=f"💀 Le mot était **{word.upper()}**",
            ))

        finally:
            await stop_countdown(countdown_task, state)
            self._clear_game(ctx.channel.id)

    # ═══════════════════════════════════════════════════════════════════════════
    # 🔗 CHAIN - Chaîne de mots
    # ═══════════════════════════════════════════════════════════════════════════

    @commands.command(name="chain", aliases=["chaine"])
    @commands.cooldown(1, 30, commands.BucketType.channel)
    async def chain_game(self, ctx):
        """Chaîne de mots ! Chaque mot doit commencer par la dernière lettre du précédent"""
        if self._is_game_active(ctx.channel.id):
            return await ctx.send("❌ Un jeu est déjà en cours dans ce channel !")

        if not await self._check_daily_limit(ctx, "chain"):
            return

        self._set_game(ctx.channel.id, "chain", owner_id=None)
        turn_timeout = 15

        countdown_task = None
        timer_msg = None
        state = {"deadline": 0, "ended": False}
        try:
            _theme_key, theme, start_word = pick_themed_manga_word(min_len=4)
            used_words = {start_word}
            current_letter = normalize(start_word[-1])
            last_player = None
            participants = {}  # user_id -> count

            embed = discord.Embed(
                title=f"🔗 Chaîne de Mots — {theme['emoji']} {theme['label']}",
                description=(
                    f"Lancée par {ctx.author.mention}\n"
                    f"💡 **Thème du mot de départ :** {theme['emoji']} *{theme['label']}*\n"
                    f"Le premier mot est : **{start_word.upper()}**\n\n"
                    f"Tapez un mot qui commence par la lettre **`{current_letter.upper()}`** !\n"
                    f"⏱️ **{turn_timeout}s** par tour — dernier debout gagne !\n\n"
                    f"*Règles : min. 3 lettres, pas de répétition, pas 2x d'affilée le même joueur*"
                ),
                color=COLORS["info"]
            )
            await ctx.send(embed=embed)

            state["deadline"] = time.time() + turn_timeout
            timer_msg = await ctx.send(embed=build_timer_embed(turn_timeout, turn_timeout, title="⏱️ Tour en cours"))
            countdown_task = asyncio.create_task(
                run_countdown(
                    timer_msg, state,
                    lambda r: build_timer_embed(r, turn_timeout, title="⏱️ Tour en cours"),
                    interval=2,
                )
            )

            while True:
                def check(m):
                    if m.channel.id != ctx.channel.id or m.author.bot:
                        return False
                    word = normalize(m.content.strip().lower())
                    return (
                        len(word) >= 3
                        and word.isalpha()
                        and word[0] == current_letter
                        and word not in used_words
                        and m.author.id != last_player
                    )

                try:
                    msg = await self.bot.wait_for("message", check=check, timeout=turn_timeout)
                except asyncio.TimeoutError:
                    await stop_countdown(countdown_task, state)
                    countdown_task = None
                    await finalize_timer(timer_msg, status="⌛ Temps écoulé !", color=COLORS["error"])
                    # Fin du jeu
                    if not participants:
                        embed = discord.Embed(
                            title="🔗 Chaîne — Terminée !",
                            description="Personne n'a joué... 😔",
                            color=COLORS["error"]
                        )
                        return await ctx.send(embed=embed)

                    # Le gagnant est celui avec le plus de mots
                    winner_id = max(participants, key=participants.get)
                    winner = ctx.guild.get_member(winner_id)

                    xp_earned, level_up, new_level, info = apply_win_xp(winner_id, MINIGAME_XP["chain"], "chain")
                    db.record_minigame(winner_id, "chain", True, xp_earned)
                    for pid in participants:
                        if pid != winner_id:
                            db.record_minigame(pid, "chain", False, 0)
                            apply_loss_xp(pid, 0, "chain")

                    bline = bonus_line(info)
                    embed = discord.Embed(
                        title="🔗 Chaîne — Temps écoulé !",
                        description=(
                            f"La chaîne s'arrête à **{len(used_words)}** mots !\n\n"
                            f"🏆 {winner.mention if winner else f'User {winner_id}'} gagne avec "
                            f"**{participants[winner_id]} mots** !\n"
                            f"**+{xp_earned} XP** gagnés !"
                            + (f"\n\n{bline}" if bline else "")
                        ),
                        color=COLORS["success"]
                    )
                    await ctx.send(embed=embed)

                    if level_up:
                        await announce_level_up_safe(self.bot, winner_id, new_level)
                    return

                word = normalize(msg.content.strip().lower())
                used_words.add(word)
                current_letter = word[-1]
                last_player = msg.author.id
                participants[msg.author.id] = participants.get(msg.author.id, 0) + 1

                # Reset du deadline pour le tour suivant
                state["deadline"] = time.time() + turn_timeout

                try:
                    await msg.add_reaction("✅")
                except Exception:
                    pass

        finally:
            await stop_countdown(countdown_task, state)
            self._clear_game(ctx.channel.id)

    # ═══════════════════════════════════════════════════════════════════════════
    # 👹 BOSS - Boss communautaire (durée 1 mois, rotation 6 boss)
    # ═══════════════════════════════════════════════════════════════════════════

    # ─── Helpers internes ────────────────────────────────────────────────────

    def _spawn_boss(self, boss_def, channel_id, *, auto_rotate=None):
        """Initialise self.boss_data pour un nouveau boss et sauvegarde.

        boss_def : dict du catalogue (id, name, max_hp, hit_min, hit_max, color, lore)
        channel_id : channel utilisé pour les annonces auto.
        auto_rotate : si fourni, écrase la valeur dans boss_data.
        """
        now = datetime.now()
        ends_at = now + timedelta(days=BOSS_DURATION_DAYS)
        previous_auto = self.boss_data.get("auto_rotate", False)
        history = self.boss_data.get("history", [])

        self.boss_data = {
            "active": True,
            "boss_id": boss_def["id"],
            "name": boss_def["name"],
            "max_hp": boss_def["max_hp"],
            "hp": boss_def["max_hp"],
            "hit_min": boss_def["hit_min"],
            "hit_max": boss_def["hit_max"],
            "color": boss_def["color"],
            "lore": boss_def["lore"],
            "participants": {},
            "spawned_at": now.isoformat(),
            "ends_at": ends_at.isoformat(),
            "channel_id": channel_id,
            "rotation_index": get_boss_index(boss_def["id"]),
            "auto_rotate": auto_rotate if auto_rotate is not None else previous_auto,
            "history": history,
        }
        save_json(BOSS_FILE, self.boss_data)

    def _archive_boss(self, status):
        """Archive l'instance courante du boss dans l'historique."""
        history = self.boss_data.get("history", [])
        history.append({
            "boss_id": self.boss_data.get("boss_id"),
            "name": self.boss_data.get("name"),
            "spawned_at": self.boss_data.get("spawned_at"),
            "ended_at": datetime.now().isoformat(),
            "status": status,  # "killed", "expired", "force_ended"
            "participants": self.boss_data.get("participants", {}),
            "hp_remaining": self.boss_data.get("hp"),
        })
        # Limiter la taille
        self.boss_data["history"] = history[-50:]

    def _build_boss_embed(self, attacker=None, damage=0, crit=False, xp_hit=0):
        """Construit l'embed d'état du boss (utilisé par !boss et après une attaque)."""
        hp = self.boss_data["hp"]
        max_hp = self.boss_data["max_hp"]
        name = self.boss_data["name"]
        percentage = int((hp / max_hp) * 100) if max_hp else 0
        bar_len = 20
        filled = int((hp / max_hp) * bar_len) if max_hp else 0

        # Temps restant
        ends_str = self.boss_data.get("ends_at")
        time_line = ""
        if ends_str:
            try:
                ends_at = datetime.fromisoformat(ends_str)
                ends_unix = int(ends_at.timestamp())
                time_line = f"\n⏳ Disparaît <t:{ends_unix}:R>"
            except Exception:
                pass

        desc = (
            f"❤️ **HP : {hp:,} / {max_hp:,}**\n"
            f"```{'█' * filled}{'░' * (bar_len - filled)} {percentage}%```"
            f"{time_line}"
        )

        embed = discord.Embed(
            title=f"👹 {name}",
            description=desc,
            color=self.boss_data.get("color", 0xFF0000),
        )

        if attacker is not None:
            crit_text = " **CRITIQUE !** 💥" if crit else ""
            embed.add_field(
                name=f"⚔️ {attacker.display_name} attaque !",
                value=f"**-{damage:,}** dégâts !{crit_text} (+{xp_hit} XP)",
                inline=False,
            )

        return embed

    async def _apply_damage(self, channel, attacker, damage, *, source_label="attack",
                            crit=False, give_hit_xp=True):
        """Applique des dégâts au boss et gère le coup fatal.

        - channel : channel discord pour envoyer les embeds.
        - attacker : discord.Member portant le coup.
        - damage : dégâts bruts à appliquer.
        - source_label : "attack" / "hero_apprenti" / etc. (pour les logs XP)
        - give_hit_xp : si False, on ne donne pas l'XP de hit standard
          (utile pour les héros, qui ont leur propre récompense).

        Retourne True si le boss est tué, False sinon.
        """
        if not self.boss_data.get("active"):
            await channel.send("❌ Aucun boss actif !")
            return False

        self.boss_data["hp"] = max(0, self.boss_data["hp"] - damage)

        # Enregistrer la participation
        uid_str = str(attacker.id)
        self.boss_data.setdefault("participants", {})
        self.boss_data["participants"][uid_str] = (
            self.boss_data["participants"].get(uid_str, 0) + damage
        )

        xp_hit = 0
        if give_hit_xp:
            xp_hit, _, _, _ = add_xp(attacker.id, MINIGAME_XP["boss_hit"], source_label)

        save_json(BOSS_FILE, self.boss_data)

        # Boss mort ?
        if self.boss_data["hp"] <= 0:
            await self._on_boss_killed(channel, attacker, crit=crit, kill_xp_extra=xp_hit)
            return True

        # Sinon : embed d'attaque
        embed = self._build_boss_embed(
            attacker=attacker, damage=damage, crit=crit, xp_hit=xp_hit
        )
        await channel.send(embed=embed)
        return False

    async def _on_boss_killed(self, channel, killer, *, crit=False, kill_xp_extra=0):
        """Distribue les récompenses, archive le boss et envoie l'embed final."""
        xp_kill, _, level_up, new_level = add_xp(
            killer.id, MINIGAME_XP["boss_kill"], "boss_kill"
        )
        participants = self.boss_data.get("participants", {})

        # XP bonus pour tous les autres participants
        for pid_str, total_dmg in participants.items():
            if int(pid_str) != killer.id:
                bonus = min(50, total_dmg // 10)
                if bonus > 0:
                    add_xp(int(pid_str), bonus, "boss_participation")

        # Podium
        sorted_attackers = sorted(participants.items(), key=lambda x: x[1], reverse=True)[:3]
        podium = ""
        medals = ["🥇", "🥈", "🥉"]
        for i, (uid, dmg) in enumerate(sorted_attackers):
            member = channel.guild.get_member(int(uid)) if channel.guild else None
            name_str = member.display_name if member else f"User {uid}"
            podium += f"{medals[i]} {name_str} — **{dmg:,}** dégâts\n"

        crit_text = " **CRITIQUE !** 💥" if crit else ""
        embed = discord.Embed(
            title=f"☠️ {self.boss_data['name']} est VAINCU !",
            description=(
                f"💥 {killer.mention} a porté le **coup fatal** !{crit_text}\n"
                f"**+{xp_kill + kill_xp_extra} XP** pour le coup fatal !\n\n"
                f"**Podium :**\n{podium}\n"
                f"🎉 **{len(participants)} participants** — XP bonus distribué à tous !"
            ),
            color=0xFFD700,
        )
        await channel.send(embed=embed)

        # Archive + reset
        self._archive_boss("killed")
        self.boss_data["active"] = False
        save_json(BOSS_FILE, self.boss_data)

        if level_up:
            await announce_level_up_safe(self.bot, killer.id, new_level)

    # ─── Tâche de rotation auto / expiration ─────────────────────────────────

    @tasks.loop(hours=1)
    async def boss_rotation_task(self):
        """Vérifie chaque heure si le boss courant a expiré.

        - Si oui : on l'archive comme "expired"
        - Si auto_rotate est activé : on spawn le boss suivant dans le catalogue
        """
        try:
            if not self.boss_data.get("active"):
                return
            ends_str = self.boss_data.get("ends_at")
            if not ends_str:
                return
            try:
                ends_at = datetime.fromisoformat(ends_str)
            except Exception:
                return
            if datetime.now() < ends_at:
                return

            # Boss expiré
            channel_id = self.boss_data.get("channel_id")
            channel = self.bot.get_channel(channel_id) if channel_id else None

            previous_name = self.boss_data.get("name", "Boss")
            self._archive_boss("expired")
            self.boss_data["active"] = False
            save_json(BOSS_FILE, self.boss_data)

            if channel:
                await channel.send(embed=discord.Embed(
                    title=f"🌫️ {previous_name} se retire...",
                    description=(
                        "Le boss a survécu pendant 1 mois et disparaît dans les ombres.\n"
                        "Les guerriers peuvent souffler... pour l'instant."
                    ),
                    color=0x95A5A6,
                ))

            # Auto rotation ?
            if self.boss_data.get("auto_rotate") and channel:
                next_index = (self.boss_data.get("rotation_index", -1) + 1) % len(BOSS_CATALOG)
                next_boss = BOSS_CATALOG[next_index]
                self._spawn_boss(next_boss, channel.id)
                await channel.send(embed=discord.Embed(
                    title=f"⚠️ {next_boss['name']} APPARAÎT !",
                    description=(
                        f"*{next_boss['lore']}*\n\n"
                        f"❤️ **HP : {next_boss['max_hp']:,} / {next_boss['max_hp']:,}**\n"
                        f"```{'█' * 20} 100%```\n\n"
                        f"⏳ Disponible **{BOSS_DURATION_DAYS} jours**\n"
                        f"Utilisez `!attack` pour l'attaquer !"
                    ),
                    color=next_boss["color"],
                ))
        except Exception as e:
            logger.exception(f"boss_rotation_task error: {e}")

    @boss_rotation_task.before_loop
    async def before_boss_rotation_task(self):
        await self.bot.wait_until_ready()

    # ─── Commandes joueur ────────────────────────────────────────────────────

    @commands.command(name="boss")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def boss_status(self, ctx):
        """Affiche l'état du boss actuel"""
        if not self.boss_data.get("active"):
            return await ctx.send("❌ Aucun boss actif. Un admin peut en invoquer un avec `!boss_spawn`.")

        embed = self._build_boss_embed()

        # Lore en field
        lore = self.boss_data.get("lore")
        if lore:
            embed.add_field(name="📖 Légende", value=f"*{lore}*", inline=False)

        # Top attaquants
        participants = self.boss_data.get("participants", {})
        sorted_attackers = sorted(participants.items(), key=lambda x: x[1], reverse=True)[:5]
        if sorted_attackers:
            attackers_text = ""
            for i, (uid, dmg) in enumerate(sorted_attackers):
                member = ctx.guild.get_member(int(uid))
                name_str = member.display_name if member else f"User {uid}"
                medal = ["🥇", "🥈", "🥉"][i] if i < 3 else f"#{i+1}"
                attackers_text += f"{medal} {name_str} — **{dmg:,}** dégâts\n"
            embed.add_field(name="⚔️ Top Attaquants", value=attackers_text, inline=False)

        embed.set_footer(
            text=f"!attack pour attaquer • {len(participants)} participant(s) "
                 f"• Auto rotation: {'ON' if self.boss_data.get('auto_rotate') else 'OFF'}"
        )
        await ctx.send(embed=embed)

    @commands.command(name="boss_list", aliases=["bosses", "boss_catalog"])
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def boss_list(self, ctx):
        """Affiche le catalogue des 6 boss disponibles."""
        embed = discord.Embed(
            title="📜 Catalogue des Boss",
            description=(
                f"**{len(BOSS_CATALOG)}** boss au total. Chaque boss reste actif "
                f"**{BOSS_DURATION_DAYS} jours**.\n\n"
                f"_Un seul boss est actif à la fois — voir `!boss`._"
            ),
            color=COLORS["info"],
        )
        current_id = self.boss_data.get("boss_id") if self.boss_data.get("active") else None
        for i, b in enumerate(BOSS_CATALOG):
            marker = " ◀ **EN COURS**" if b["id"] == current_id else ""
            embed.add_field(
                name=f"{i+1}. {b['name']}{marker}",
                value=(
                    f"❤️ **{b['max_hp']:,}** HP — `id: {b['id']}`\n"
                    f"*{b['lore']}*"
                ),
                inline=False,
            )
        await ctx.send(embed=embed)

    @commands.command(name="attack", aliases=["attaque", "atk"])
    async def attack_boss(self, ctx):
        """Attaque le boss actuel !"""
        if not self.boss_data.get("active"):
            return await ctx.send("❌ Aucun boss actif !")

        # Cooldown manuel (30 secondes)
        user_id = ctx.author.id
        now = datetime.now()
        last_attack = self.attack_cooldowns.get(user_id)
        if last_attack and (now - last_attack).total_seconds() < 30:
            remaining = 30 - int((now - last_attack).total_seconds())
            return await ctx.send(f"⏱️ Cooldown ! Attaque disponible dans **{remaining}s**", delete_after=5)

        if not await self._check_daily_limit(ctx, "boss"):
            return

        self.attack_cooldowns[user_id] = now

        # Dégâts aléatoires basés sur les stats du boss
        hit_min = self.boss_data.get("hit_min", 10)
        hit_max = self.boss_data.get("hit_max", 50)
        damage = random.randint(hit_min, hit_max)
        crit = random.random() < 0.1  # 10% de chance de critique
        if crit:
            damage *= 3

        await self._apply_damage(
            ctx.channel, ctx.author, damage, source_label="boss_hit", crit=crit
        )

    # ─── API publique pour les héros (appelée depuis shop.py) ────────────────

    async def hero_attack(self, channel, attacker, hero_name, hero_damage):
        """Inflige une attaque héroïque au boss courant.

        Appelé par shop.py quand un joueur utilise un item de catégorie 'heroes'.
        Retourne (success, message_si_echec).
        """
        if not self.boss_data.get("active"):
            return False, "❌ Aucun boss actif — ton héros attend l'occasion."

        # Annonce d'arrivée du héros
        try:
            await channel.send(embed=discord.Embed(
                title=f"✨ {hero_name} entre dans la bataille !",
                description=(
                    f"{attacker.mention} a invoqué **{hero_name}** "
                    f"pour frapper **{self.boss_data['name']}** !"
                ),
                color=0x9B59B6,
            ))
        except Exception:
            pass

        # Le héros tape un gros coup (pas de crit, pas d'XP de hit standard)
        await self._apply_damage(
            channel, attacker, hero_damage,
            source_label="hero_attack", crit=False, give_hit_xp=False,
        )
        return True, None

    # ─── Commandes admin ─────────────────────────────────────────────────────

    @commands.command(name="boss_spawn", aliases=["spawn_boss"])
    @commands.has_any_role(*__import__('config').ADMIN_ROLES)
    async def boss_spawn(self, ctx, boss_id: str = None):
        """(ADMIN) Fait apparaître un boss du catalogue.

        Usage : `!boss_spawn` (boss suivant dans la rotation)
                `!boss_spawn dragon_ombres` (par id)
                `!boss_spawn 3` (par numéro 1-6)
        """
        if self.boss_data.get("active"):
            return await ctx.send(
                "❌ Un boss est déjà actif ! Utilise `!boss` pour voir son état "
                "ou `!boss_end` pour le terminer."
            )

        # Sélection du boss
        boss_def = None
        if boss_id is None:
            # Suivant dans la rotation
            next_index = (self.boss_data.get("rotation_index", -1) + 1) % len(BOSS_CATALOG)
            boss_def = BOSS_CATALOG[next_index]
        else:
            # Par numéro ?
            if boss_id.isdigit():
                idx = int(boss_id) - 1
                if 0 <= idx < len(BOSS_CATALOG):
                    boss_def = BOSS_CATALOG[idx]
            # Par id ?
            if boss_def is None:
                boss_def = get_boss_by_id(boss_id)

        if boss_def is None:
            return await ctx.send(
                f"❌ Boss inconnu. Utilise `!boss_list` pour voir les ids disponibles."
            )

        self._spawn_boss(boss_def, ctx.channel.id)

        embed = discord.Embed(
            title=f"⚠️ {boss_def['name']} APPARAÎT !",
            description=(
                f"*{boss_def['lore']}*\n\n"
                f"❤️ **HP : {boss_def['max_hp']:,} / {boss_def['max_hp']:,}**\n"
                f"```{'█' * 20} 100%```\n\n"
                f"⏳ Disponible **{BOSS_DURATION_DAYS} jours**\n"
                f"Utilisez `!attack` pour l'attaquer !\n"
                f"⏱️ Cooldown : 30 secondes par attaque\n"
                f"🏆 **{MINIGAME_XP['boss_kill']} XP** pour le coup fatal !"
            ),
            color=boss_def["color"],
        )
        await ctx.send(embed=embed)

    @commands.command(name="boss_rotate")
    @commands.has_any_role(*__import__('config').ADMIN_ROLES)
    async def boss_rotate(self, ctx):
        """(ADMIN) Termine le boss courant (s'il y en a un) et spawn le suivant."""
        if self.boss_data.get("active"):
            self._archive_boss("force_ended")
            self.boss_data["active"] = False
            save_json(BOSS_FILE, self.boss_data)

        next_index = (self.boss_data.get("rotation_index", -1) + 1) % len(BOSS_CATALOG)
        boss_def = BOSS_CATALOG[next_index]
        self._spawn_boss(boss_def, ctx.channel.id)

        await ctx.send(embed=discord.Embed(
            title=f"⚠️ {boss_def['name']} APPARAÎT !",
            description=(
                f"*{boss_def['lore']}*\n\n"
                f"❤️ **HP : {boss_def['max_hp']:,} / {boss_def['max_hp']:,}**\n"
                f"```{'█' * 20} 100%```\n\n"
                f"⏳ Disponible **{BOSS_DURATION_DAYS} jours** — `!attack` pour frapper !"
            ),
            color=boss_def["color"],
        ))

    @commands.command(name="boss_auto")
    @commands.has_any_role(*__import__('config').ADMIN_ROLES)
    async def boss_auto(self, ctx, mode: str = None):
        """(ADMIN) Active/désactive la rotation auto mensuelle.

        Usage : `!boss_auto on` / `!boss_auto off` / `!boss_auto` (status)
        """
        if mode is None:
            current = self.boss_data.get("auto_rotate", False)
            return await ctx.send(
                f"🔁 Auto rotation : **{'ON' if current else 'OFF'}**\n"
                f"Utilise `!boss_auto on|off` pour changer."
            )

        mode_lower = mode.lower()
        if mode_lower in ("on", "true", "1", "yes", "oui"):
            self.boss_data["auto_rotate"] = True
            save_json(BOSS_FILE, self.boss_data)
            await ctx.send("✅ Rotation automatique **activée**. Le bot fera spawn le boss suivant à la fin du mois.")
        elif mode_lower in ("off", "false", "0", "no", "non"):
            self.boss_data["auto_rotate"] = False
            save_json(BOSS_FILE, self.boss_data)
            await ctx.send("✅ Rotation automatique **désactivée**.")
        else:
            await ctx.send("❌ Usage : `!boss_auto on|off`")

    @commands.command(name="boss_end")
    @commands.has_any_role(*__import__('config').ADMIN_ROLES)
    async def boss_end(self, ctx):
        """(ADMIN) Termine le boss de force"""
        if not self.boss_data.get("active"):
            return await ctx.send("❌ Aucun boss actif.")

        self._archive_boss("force_ended")
        self.boss_data["active"] = False
        save_json(BOSS_FILE, self.boss_data)
        await ctx.send("✅ Boss terminé de force.")

    # ═══════════════════════════════════════════════════════════════════════════
    # 📊 MGSTATS / MGTOP / MGCANCEL - Stats & gestion
    # ═══════════════════════════════════════════════════════════════════════════

    @commands.command(name="mgstats", aliases=["minigame_stats", "gamestats"])
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def mgstats(self, ctx, member: discord.Member = None):
        """Affiche tes statistiques de mini-jeux (ou celles d'un autre membre)"""
        target = member or ctx.author
        rows = db.get_minigame_stats(target.id)
        totals = db.get_minigame_totals(target.id)

        embed = discord.Embed(
            title=f"📊 Stats Mini-Jeux — {target.display_name}",
            color=COLORS["info"],
        )
        embed.set_thumbnail(url=target.display_avatar.url)

        if not rows or not totals or totals.get("played", 0) == 0:
            embed.description = "Aucune partie jouée pour le moment.\nLance `!unscramble`, `!wordle`, `!hangman`... pour commencer !"
            return await ctx.send(embed=embed)

        played = totals.get("played", 0) or 0
        wins = totals.get("wins", 0) or 0
        losses = totals.get("losses", 0) or 0
        winrate = (wins / played * 100) if played else 0
        net = (totals.get("xp_earned", 0) or 0) - (totals.get("xp_lost", 0) or 0)

        embed.description = (
            f"🎮 **{played:,}** parties · 🏆 **{wins:,}** victoires · 💀 **{losses:,}** défaites\n"
            f"📈 Winrate : **{winrate:.1f}%**\n"
            f"💰 XP net : **{net:+,}** (gagnés {totals.get('xp_earned', 0):,} / perdus {totals.get('xp_lost', 0):,})\n"
            f"🔥 Meilleure série : **{totals.get('best_streak', 0)}**"
        )

        # Détail par jeu
        emoji_map = {
            "reaction": "🎯", "unscramble": "🔤", "wordle": "🟩",
            "hangman": "💀", "chain": "🔗", "coinflip": "🪙",
            "slots": "🎰", "roulette": "🎡", "duel": "⚔️",
        }
        lines = []
        for r in rows:
            game = r["game"]
            emo = emoji_map.get(game, "🎲")
            wr = (r["wins"] / r["played"] * 100) if r["played"] else 0
            line = f"{emo} **{game.capitalize()}** — {r['played']} parties · {r['wins']}V/{r['losses']}D ({wr:.0f}%)"
            if r.get("fastest_win_seconds"):
                line += f" · ⚡ {r['fastest_win_seconds']:.1f}s"
            lines.append(line)

        if lines:
            embed.add_field(name="Détail par jeu", value="\n".join(lines), inline=False)

        await ctx.send(embed=embed)

    @commands.command(name="mgtop", aliases=["minigame_top"])
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def mgtop(self, ctx, game: str = None):
        """Classement des meilleurs joueurs de mini-jeux. Usage: !mgtop [jeu]"""
        valid_games = {"reaction", "unscramble", "wordle", "hangman", "chain",
                       "coinflip", "slots", "roulette", "duel"}
        game_filter = None
        if game:
            game = game.lower().strip()
            if game not in valid_games:
                return await ctx.send(
                    f"❌ Jeu inconnu. Disponibles : {', '.join(sorted(valid_games))}"
                )
            game_filter = game

        rows = db.get_minigame_leaderboard(game=game_filter, limit=10, sort_by="wins")

        title = f"🏆 Top Mini-Jeux" + (f" — {game_filter.capitalize()}" if game_filter else " (global)")
        embed = discord.Embed(title=title, color=COLORS["info"])

        if not rows:
            embed.description = "Aucun joueur classé pour le moment."
            return await ctx.send(embed=embed)

        medals = ["🥇", "🥈", "🥉"]
        lines = []
        for i, r in enumerate(rows):
            uid = r["user_id"]
            member = ctx.guild.get_member(uid) if ctx.guild else None
            name = member.display_name if member else f"User {uid}"
            medal = medals[i] if i < 3 else f"`#{i+1}`"
            wins = r.get("wins") or 0
            played = r.get("played") or 0
            xp = r.get("xp_earned") or 0
            lines.append(
                f"{medal} **{name}** — {wins}V / {played} parties · {xp:,} XP"
            )

        embed.description = "\n".join(lines)
        embed.set_footer(text="Trié par victoires • !mgstats pour tes stats perso")
        await ctx.send(embed=embed)

    @commands.command(name="mgcancel", aliases=["cancel_game"])
    async def mgcancel(self, ctx):
        """Annule le mini-jeu actif dans ce channel (uniquement le lanceur ou un admin)"""
        game = self._get_game(ctx.channel.id)
        if not game:
            return await ctx.send("❌ Aucun mini-jeu actif dans ce channel.")

        from config import ADMIN_ROLES
        is_admin = any(r.name in ADMIN_ROLES for r in getattr(ctx.author, "roles", []))
        owner_id = game.get("owner_id")
        is_owner = owner_id == ctx.author.id

        if not (is_owner or is_admin):
            return await ctx.send(
                "❌ Seul le joueur qui a lancé la partie (ou un admin) peut l'annuler."
            )

        self._clear_game(ctx.channel.id)
        await ctx.send(f"✅ Mini-jeu **{game.get('type', '?')}** annulé. Tu peux en relancer un.")

    @commands.command(name="mglimits", aliases=["mglimit", "minigame_limits"])
    async def mglimits(self, ctx, member: discord.Member = None):
        """Affiche les pools quotidiens (mini-jeux + boss) et ton usage du jour."""
        target = member or ctx.author
        usage = db.get_all_daily_usage(target.id)
        is_admin_target = self._is_admin(target)

        now = datetime.now()
        next_midnight = (now + timedelta(days=1)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        reset_unix = int(next_midnight.timestamp())

        embed = discord.Embed(
            title=f"📊 Limites quotidiennes — {target.display_name}",
            description=f"⏰ Reset <t:{reset_unix}:R>",
            color=COLORS["info"],
        )

        if is_admin_target:
            embed.add_field(
                name="👑 Admin",
                value="Bypass actif — aucune limite quotidienne.",
                inline=False,
            )

        lines = []
        for category, limit in CATEGORY_LIMITS.items():
            label = CATEGORY_LABELS.get(category, category)
            used = usage.get(category, 0)
            if is_admin_target:
                bar = "♾️"
                status = f"`{used}` utilisées"
            else:
                ratio = min(1.0, used / limit) if limit > 0 else 0
                filled = int(ratio * 10)
                if used >= limit:
                    bar = "🟥" * 10
                else:
                    bar = "🟩" * filled + "⬜" * (10 - filled)
                status = f"`{used}/{limit}`"
            lines.append(f"**{label}** — {status}\n{bar}")

        embed.add_field(name="Pools", value="\n\n".join(lines), inline=False)
        embed.add_field(
            name="ℹ️ Détail",
            value=(
                "• **Mini-jeux** : pool partagé entre `reaction`, `unscramble`, "
                "`wordle`, `hangman`, `chain`, `coinflip`, `slots`, `roulette`, `duel`.\n"
                "• **Attaques boss** : 1 `!attack` par jour."
            ),
            inline=False,
        )
        embed.set_footer(text="Les admins ont un bypass • !mgstats pour tes stats")
        await ctx.send(embed=embed)


async def setup(bot):
    """Setup pour discord.py 2.0+"""
    await bot.add_cog(MiniGames(bot))
    logging.info("✅ Cog MiniGames chargé avec succès")
