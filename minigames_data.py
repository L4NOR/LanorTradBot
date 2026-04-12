# ═══════════════════════════════════════════════════════════════════════════════
# MINIGAMES_DATA.PY — Données centralisées de tous les mini-jeux
# ═══════════════════════════════════════════════════════════════════════════════
# Ce fichier regroupe TOUTES les constantes de données utilisées par les
# mini-jeux (minigames.py et minigames_extra.py). Pour ajouter/modifier
# des mots, devinettes, citations, etc. → c'est ici.
# ═══════════════════════════════════════════════════════════════════════════════

# ─── Mots thématiques pour Unscramble / Hangman / Chain ──────────────────────
# Chaque thème contient un emoji, un label affiché et une liste de mots.
# Les mots sont SANS accents (normalize() gère les comparaisons).

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
            "chapitre", "episode", "saison", "arc", "prologue",
            "epilogue", "final", "climax", "revelation", "flashback",
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
            "editeur", "tirage", "preview", "planche", "vignette", "phylactere",
            "onomatopee", "scenario", "storyboard", "ebauche", "croquis",
            "publication", "magazine", "hebdomadaire", "mensuel", "collector",
            "numerique", "papier", "impression", "reliure", "jaquette",
        ],
    },
    "maitres_eleves": {
        "emoji": "🎓",
        "label": "Maîtres, élèves & relations",
        "words": [
            "sensei", "nakama", "kohai", "senpai", "shifu", "disciple",
            "maitre", "apprenti", "mentor", "rival", "equipe", "famille",
            "alliance", "camarade", "compagnon", "protege", "eleve",
            "professeur", "instructeur", "guide", "frere", "soeur",
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
            "arbalete", "javelot", "fronde", "fouet", "hallebarde",
            "trident", "marteau", "faux", "mousquet", "pistolet",
            "fusil", "canon", "belier", "catapulte", "trebuchet",
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
            "invulnerabilite", "teleportation", "invisibilite", "regeneration",
            "telepathie", "telekinesie", "clairvoyance", "metamorphose",
        ],
    },
    "magie_arcanes": {
        "emoji": "🔮",
        "label": "Magie & arcanes",
        "words": [
            "magie", "sortilege", "invocation", "portail", "dimension",
            "alchimie", "necromancie", "elementaire", "runique", "arcane",
            "enchantement", "malefice", "exorcisme", "purification",
            "conjuration", "divination", "transmutation", "illusion",
            "evocation", "abjuration", "rituel", "pentacle", "cercle",
            "sorcellerie", "chamanisme", "vaudou", "druidisme",
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
            "paladin", "templier", "archer", "eclaireur", "mercenaire",
            "gladiateur", "centurion", "legionnaire", "corsaire", "pirate",
            "boucanier", "flibustier", "explorateur", "vagabond", "nomade",
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
            "cyclope", "sirene", "meduse", "cerbere", "pegase", "licorne",
            "golem", "djinn", "demon", "succube", "incube", "banshee",
            "wendigo", "chupacabra", "yeti", "sasquatch", "gargouillle",
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
            "volcan", "glacier", "archipel", "peninsule", "continent",
            "cathedrale", "palais", "arene", "colisee", "pyramide",
            "labyrinthe", "catacombes", "ruines", "phare", "port",
        ],
    },
    "objets_artefacts": {
        "emoji": "💎",
        "label": "Objets & artefacts",
        "words": [
            "elixir", "poison", "antidote", "potion", "parchemin", "grimoire",
            "amulette", "talisman", "relique", "artefact", "joyau", "cristal",
            "rune", "totem", "anneau", "couronne", "sceptre", "orbe",
            "calice", "graal", "pendentif", "medaillon", "coffre", "tresor",
            "boussole", "lunette", "miroir", "cloche", "chandelier",
            "sablier", "horloge", "diademe", "tiare", "baton",
        ],
    },
    "quetes_mysteres": {
        "emoji": "🗺️",
        "label": "Quêtes & mystères",
        "words": [
            "mission", "quete", "aventure", "mystere", "secret", "enigme",
            "prophetie", "oracle", "vision", "prediction", "destin", "fatalite",
            "complot", "conspiration", "intrigue", "enquete", "indice",
            "suspect", "temoin", "alibi", "mobile", "preuve", "verdict",
            "expedition", "odyssee", "periple", "pelerinage", "croisade",
        ],
    },
    "emotions_combat": {
        "emoji": "❤️‍🔥",
        "label": "Émotions & combat",
        "words": [
            "courage", "bravoure", "honneur", "fierte", "fureur", "rage",
            "colere", "vengeance", "trahison", "loyaute", "amitie", "amour",
            "haine", "peur", "terreur", "espoir", "douleur", "sacrifice",
            "passion", "melancolie", "nostalgie", "solitude", "tristesse",
            "joie", "allegresse", "serenite", "extase", "angoisse",
            "remords", "compassion", "mepris", "jalousie", "admiration",
        ],
    },
    "culture_japonaise": {
        "emoji": "🎎",
        "label": "Culture japonaise",
        "words": [
            "ramen", "sushi", "miso", "udon", "soba", "tempura", "onigiri",
            "matsuri", "sakura", "momiji", "kimono", "yukata", "hakama",
            "kanji", "hiragana", "katakana", "tatami", "shoji",
            "torii", "geisha", "kabuki", "sumo", "judo", "karate",
            "kendo", "aikido", "origami", "ikebana", "bonsai",
            "wasabi", "sake", "matcha", "mochi", "dango", "takoyaki",
            "futon", "kotatsu", "hanami", "tanabata", "obon",
        ],
    },
    # ── NOUVEAUX THÈMES — Mots français / culture générale ──
    "animaux": {
        "emoji": "🦁",
        "label": "Animaux",
        "words": [
            "lion", "tigre", "panthere", "leopard", "guepard", "jaguar",
            "elephant", "rhinoceros", "hippopotame", "girafe", "zebre",
            "gorille", "chimpanze", "orang", "babouin", "lemur",
            "crocodile", "alligator", "python", "cobra", "vipere",
            "aigle", "faucon", "hibou", "chouette", "vautour", "condor",
            "requin", "baleine", "dauphin", "orque", "pieuvre", "meduse",
            "loup", "renard", "ours", "cerf", "biche", "sanglier",
            "castor", "loutre", "herisson", "ecureuil", "lapin",
            "tortue", "cameleon", "iguane", "salamandre", "grenouille",
            "papillon", "libellule", "scarabee", "fourmi", "abeille",
        ],
    },
    "sciences": {
        "emoji": "🔬",
        "label": "Sciences & technologie",
        "words": [
            "atome", "molecule", "electron", "proton", "neutron", "photon",
            "gravite", "magnetisme", "electricite", "radiation", "friction",
            "chimie", "physique", "biologie", "geologie", "astronomie",
            "cellule", "bacterie", "virus", "proteine", "enzyme",
            "telescope", "microscope", "satellite", "fusee", "orbite",
            "galaxie", "nebuleuse", "pulsar", "quasar", "supernova",
            "algorithme", "programme", "logiciel", "serveur", "reseau",
            "internet", "cryptage", "robotique", "intelligence", "quantique",
            "formule", "equation", "theoreme", "hypothese", "experience",
        ],
    },
    "geographie": {
        "emoji": "🌍",
        "label": "Géographie & monde",
        "words": [
            "ocean", "atlantique", "pacifique", "arctique", "mediterranee",
            "montagne", "volcan", "canyon", "falaise", "plateau",
            "fleuve", "riviere", "cascade", "delta", "estuaire",
            "continent", "archipel", "peninsule", "tropique", "equateur",
            "toundra", "savane", "steppe", "prairie", "mangrove",
            "capitale", "metropole", "village", "frontiere", "territoire",
            "amazonie", "sahara", "himalaya", "alpes", "andes",
            "japon", "france", "egypte", "grece", "italie",
        ],
    },
    "histoire": {
        "emoji": "📜",
        "label": "Histoire & civilisations",
        "words": [
            "pharaon", "pyramide", "momie", "hieroglyphe", "papyrus",
            "gladiateur", "colisee", "senat", "legion", "empereur",
            "viking", "drakkar", "rune", "valhalla", "ragnarok",
            "croisade", "templier", "trebuchet", "catapulte", "siege",
            "revolution", "monarchie", "republique", "democratie", "tyrannie",
            "renaissance", "baroque", "medieval", "antiquite", "prehistoire",
            "samurai", "shogun", "bushido", "seppuku", "harakiri",
            "spartiate", "centurion", "consul", "tribun", "cesar",
            "napoleon", "charlemagne", "cleopatre", "alexandre", "genghis",
        ],
    },
    "nourriture": {
        "emoji": "🍕",
        "label": "Nourriture & cuisine",
        "words": [
            "baguette", "croissant", "brioche", "eclair", "macaron",
            "fromage", "camembert", "roquefort", "brie", "gruyere",
            "chocolat", "vanille", "caramel", "cannelle", "muscade",
            "tomate", "oignon", "poivron", "aubergine", "courgette",
            "framboise", "myrtille", "cassis", "mangue", "ananas",
            "poulet", "boeuf", "agneau", "poisson", "crevette",
            "pizza", "lasagne", "risotto", "paella", "couscous",
            "crepe", "gaufre", "tarte", "gateau", "mousse",
            "soupe", "ragout", "gratin", "fondue", "raclette",
        ],
    },
    "sport": {
        "emoji": "⚽",
        "label": "Sport & compétition",
        "words": [
            "football", "basketball", "volleyball", "handball", "rugby",
            "tennis", "badminton", "natation", "athletisme", "cyclisme",
            "boxe", "escrime", "lutte", "judo", "karate",
            "marathon", "sprint", "relais", "saut", "lancer",
            "gardien", "attaquant", "defenseur", "milieu", "arbitre",
            "champion", "medaille", "podium", "record", "victoire",
            "equipe", "entraineur", "stade", "terrain", "vestiaire",
            "dribble", "penalty", "corner", "touche", "prolongation",
        ],
    },
    "musique": {
        "emoji": "🎵",
        "label": "Musique & instruments",
        "words": [
            "guitare", "piano", "violon", "batterie", "trompette",
            "saxophone", "flute", "harpe", "contrebasse", "accordeon",
            "melodie", "harmonie", "rythme", "tempo", "refrain",
            "couplet", "partition", "gamme", "octave", "accord",
            "concert", "orchestre", "chorale", "soliste", "maestro",
            "rock", "jazz", "blues", "reggae", "classique",
            "symphonie", "sonate", "opera", "ballade", "requiem",
        ],
    },
    "nature_elements": {
        "emoji": "🌿",
        "label": "Nature & éléments",
        "words": [
            "tonnerre", "eclair", "tempete", "ouragan", "cyclone",
            "tsunami", "seisme", "eruption", "avalanche", "tornade",
            "aurore", "crepuscule", "eclipse", "arc", "brouillard",
            "rosee", "givre", "grele", "bruine", "averse",
            "chene", "sapin", "bouleau", "erable", "sequoia",
            "orchidee", "tulipe", "tournesol", "lavande", "jasmin",
            "corail", "recif", "marais", "etang", "source",
            "cristal", "ambre", "obsidienne", "saphir", "emeraude",
        ],
    },
    "metiers": {
        "emoji": "👷",
        "label": "Métiers & professions",
        "words": [
            "medecin", "chirurgien", "infirmier", "pharmacien", "dentiste",
            "avocat", "juge", "notaire", "detective", "policier",
            "pompier", "pilote", "capitaine", "matelot", "astronaute",
            "architecte", "ingenieur", "plombier", "electricien", "menuisier",
            "boulanger", "patissier", "cuisinier", "serveur", "sommelier",
            "professeur", "chercheur", "scientifique", "journaliste", "ecrivain",
            "artiste", "sculpteur", "peintre", "photographe", "musicien",
            "forgeron", "tisserand", "potier", "verrier", "orfèvre",
        ],
    },
    "espace": {
        "emoji": "🚀",
        "label": "Espace & cosmos",
        "words": [
            "planete", "etoile", "comete", "asteroide", "meteorite",
            "mercure", "venus", "mars", "jupiter", "saturne",
            "uranus", "neptune", "pluton", "lune", "soleil",
            "constellation", "zodiaque", "equinoxe", "solstice", "eclipse",
            "astronaute", "cosmonaute", "station", "navette", "fusee",
            "telescope", "observatoire", "apesanteur", "atmosphere", "stratosphere",
            "cratere", "anneau", "satellite", "sonde", "rover",
        ],
    },
    "mythologie": {
        "emoji": "⚡",
        "label": "Mythologie",
        "words": [
            "zeus", "poseidon", "hades", "athena", "apollon",
            "artemis", "hermes", "aphrodite", "ares", "hephaïstos",
            "odin", "thor", "loki", "freya", "fenrir",
            "anubis", "osiris", "isis", "horus", "bastet",
            "olympe", "tartare", "elysee", "styx", "acheron",
            "minotaure", "meduse", "centaure", "cyclope", "hydre",
            "excalibur", "mjolnir", "gungnir", "trident", "egide",
            "pandore", "promethee", "hercule", "achille", "ulysse",
        ],
    },
}

# ─── Mots pour Wordle (4-6 lettres principalement) ──────────────────────────
# Les mots sont regroupés par thème — le thème est affiché comme indice.
# Tous sans accents, sans apostrophe ni tiret (isalpha() les rejetterait).

WORDLE_WORD_THEMES = {
    "edition_manga": {
        "emoji": "📖",
        "label": "Manga & édition",
        "words": [
            "manga", "anime", "scans", "clean", "check", "ligne", "bulle",
            "trame", "encre", "trait", "plume", "panel", "pages", "texte",
            "verbe", "prose", "ecrit", "haiku", "kanji", "conte",
            "roman", "fable", "poeme", "tirage", "serie", "album",
        ],
    },
    "armes_equipement": {
        "emoji": "⚔️",
        "label": "Armes & équipement",
        "words": [
            "lame", "epee", "sabre", "lames", "epees", "lance", "armes",
            "garde", "forge", "armee", "sabres", "lances", "casque",
            "hache", "dague", "masse", "pique", "glaive", "fouet",
            "arcs", "trait", "fleche", "gilet", "cotte", "heaume",
        ],
    },
    "magie_arcanes": {
        "emoji": "🔮",
        "label": "Magie & arcanes",
        "words": [
            "magie", "rituel", "divin", "arcane", "mages", "sages",
            "dieux", "saint", "pieux", "prier", "grace", "foudre",
            "sorts", "voeux", "runes", "auras", "elixir", "fiole",
            "signe", "astre", "augure", "oracle",
        ],
    },
    "creatures_monstres": {
        "emoji": "🐉",
        "label": "Créatures & monstres",
        "words": [
            "demon", "titan", "ange", "loup", "elfe", "nain",
            "ogres", "morts", "anges", "tengu", "kappa", "akuma",
            "trolls", "diable", "loups", "lions", "hydre",
            "golem", "djinn", "orque", "harpie", "sirene",
        ],
    },
    "aventuriers_classes": {
        "emoji": "🏹",
        "label": "Aventuriers & classes",
        "words": [
            "heros", "ninja", "ronin", "brave", "moine", "barde", "noble",
            "tueur", "voleur", "rodeur", "mentor", "soldat",
            "rival", "chefs", "garde", "scout", "reine", "prince",
            "baron", "comte", "druide", "clerc", "sage",
        ],
    },
    "combats_duels": {
        "emoji": "🛡️",
        "label": "Combat & duels",
        "words": [
            "force", "piege", "duels", "siege", "guerre",
            "cible", "destin", "chaos", "droit", "lutte",
            "round", "champ", "assaut", "riposte", "feinte",
            "garde", "esquive", "charge", "rush", "frappe",
        ],
    },
    "emotions": {
        "emoji": "❤️‍🔥",
        "label": "Émotions",
        "words": [
            "rage", "coeur", "amour", "haine", "peine",
            "songe", "reves", "honte", "fureur", "joie",
            "peur", "envie", "doute", "calme", "emoi",
            "fierté", "zele", "extase", "gloire", "larme",
        ],
    },
    "nature_elements": {
        "emoji": "🌪️",
        "label": "Nature & éléments",
        "words": [
            "feux", "vent", "nuage", "neige", "pluie", "brume", "vents",
            "foret", "orage", "glace", "fumee", "vague", "monts", "mares",
            "givre", "rosee", "terre", "sable", "roche", "fleur",
            "chene", "sapin", "lierre", "mousse", "algue", "corail",
        ],
    },
    "temps_cycles": {
        "emoji": "⏳",
        "label": "Temps & cycles",
        "words": [
            "nuit", "jour", "jours", "soirs", "matin", "aubes",
            "ciels", "lunes", "heure", "saison", "annee",
            "passe", "futur", "epoque", "cycle", "phase",
        ],
    },
    "lieux_royaumes": {
        "emoji": "🏰",
        "label": "Lieux & royaumes",
        "words": [
            "clan", "arena", "monde", "route", "voies", "piste", "ponts",
            "tours", "cites", "toits", "camps", "forts", "ports", "baies",
            "trone", "donjon", "guilde", "place", "palais", "arene",
            "grotte", "plaine", "colline", "vallee", "ile",
        ],
    },
    "objets_artefacts": {
        "emoji": "💎",
        "label": "Objets & artefacts",
        "words": [
            "cles", "clefs", "bague", "croix", "perle", "outil", "objet",
            "plans", "choix", "coupe", "vase", "coffre", "lampe",
            "miroir", "carte", "sceau", "fiole", "totem", "globe",
        ],
    },
    "culture_japonaise": {
        "emoji": "🎎",
        "label": "Culture japonaise",
        "words": [
            "yari", "tabi", "sumo", "ramen", "sushi", "shiki",
            "torii", "geisha", "bento", "futon", "wasabi",
            "matcha", "mochi", "dango", "sake", "obon",
        ],
    },
    "corps_physique": {
        "emoji": "🦴",
        "label": "Corps & physique",
        "words": [
            "torse", "genou", "barbe", "front", "ailes", "queue", "crocs",
            "poils", "tete", "bras", "mains", "doigt", "coude",
            "gorge", "nuque", "joues", "crane", "pouce", "ongle",
        ],
    },
    "couleurs_ombres": {
        "emoji": "🎨",
        "label": "Couleurs & ombres",
        "words": [
            "rouge", "blanc", "noir", "verts", "bleus",
            "jaune", "mauve", "beige", "gris", "brun",
            "ombre", "lueur", "eclat", "teinte", "nuance",
            "aube", "neon", "prisme", "reflet", "opale",
        ],
    },
    "ordre_justice": {
        "emoji": "⚖️",
        "label": "Ordre & justice",
        "words": [
            "rangs", "ordre", "juste", "prise", "chute", "volee",
            "quete", "regle", "devoir", "droit", "juge", "loi",
            "jury", "peine", "blame", "grace", "vertu", "crime",
        ],
    },
    "relations_liens": {
        "emoji": "🤝",
        "label": "Relations & liens",
        "words": [
            "amis", "lien", "voie", "frere", "soeur", "union",
            "pacte", "serment", "aveu", "promesse",
        ],
    },
    # ── NOUVEAUX THÈMES WORDLE ──
    "animaux_wordle": {
        "emoji": "🦁",
        "label": "Animaux",
        "words": [
            "tigre", "lions", "aigle", "cobra", "loup", "cerf",
            "ours", "vache", "poule", "chien", "chat", "lapin",
            "biche", "canard", "singe", "panda", "raton", "otarie",
            "crabe", "huître", "moule", "raie", "thon", "truite",
            "faon", "cygne", "merle", "grue", "hibou", "porc",
        ],
    },
    "science_wordle": {
        "emoji": "🔬",
        "label": "Sciences",
        "words": [
            "atome", "laser", "virus", "radio", "radar",
            "fibre", "orbite", "prisme", "noyau", "force",
            "masse", "poids", "tesla", "hertz", "diode",
            "acide", "base", "sel", "ion", "gaz",
            "onde", "flux", "dose", "gene", "phase",
        ],
    },
    "geo_wordle": {
        "emoji": "🌍",
        "label": "Géographie",
        "words": [
            "paris", "tokyo", "rome", "lima", "oslo",
            "lagos", "delhi", "pekin", "seoul", "berne",
            "alpes", "andes", "volcan", "ocean", "fleuve",
            "plage", "ile", "baie", "cap", "golfe",
            "dune", "oasis", "fjord", "lac", "pic",
        ],
    },
    "nourriture_wordle": {
        "emoji": "🍕",
        "label": "Cuisine",
        "words": [
            "pain", "tarte", "soupe", "sauce", "creme",
            "fruit", "olive", "melon", "peche", "poire",
            "figue", "noix", "miel", "beurre", "sucre",
            "epice", "thym", "menthe", "curry", "poivre",
            "gratin", "crepe", "frite", "pizza", "pates",
        ],
    },
    "musique_wordle": {
        "emoji": "🎵",
        "label": "Musique",
        "words": [
            "piano", "flute", "harpe", "note", "tempo",
            "blues", "rock", "jazz", "opera", "choeur",
            "basse", "gamme", "chord", "album", "scene",
            "micro", "ampli", "sono", "bande", "voix",
        ],
    },
}

# ─── Emojis (Slot Machine, Réaction, Memory) ────────────────────────────────

SLOT_EMOJIS = ["🍒", "🍋", "🍊", "🍇", "⭐", "💎", "7️⃣"]

REACTION_EMOJIS = ["🔥", "⚡", "💎", "🎯", "🌟", "👑", "🎲", "🎪", "🎭", "🎨"]

MEMORY_EMOJIS = ["🍒", "🍋", "🍇", "⭐", "💎", "7️⃣", "🎯", "🔥"]

# ─── Boss communautaires ────────────────────────────────────────────────────

BOSS_DURATION_DAYS = 30

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

# ─── Hangman (étapes du pendu) ──────────────────────────────────────────────

HANGMAN_STAGES = [
    "```\n  +---+\n      |\n      |\n      |\n      |\n=========```",
    "```\n  +---+\n  O   |\n      |\n      |\n      |\n=========```",
    "```\n  +---+\n  O   |\n  |   |\n      |\n      |\n=========```",
    "```\n  +---+\n  O   |\n /|   |\n      |\n      |\n=========```",
    "```\n  +---+\n  O   |\n /|\\  |\n      |\n      |\n=========```",
    "```\n  +---+\n  O   |\n /|\\  |\n /    |\n      |\n=========```",
    "```\n  +---+\n  O   |\n /|\\  |\n / \\  |\n      |\n=========```",
]

# ─── Devinettes ─────────────────────────────────────────────────────────────

RIDDLES = [
    # — Manga / LanorTrad —
    {"q": "Je suis né démon mais je veux devenir exorciste, mon frère est mon plus grand rival. Qui suis-je ?",
     "answer": "rin", "alts": ["rin okumura", "okumura"]},
    {"q": "Mon père m'a transformé en oni pour sauver ma soeur. Je porte un masque blanc à cornes. Qui suis-je ?",
     "answer": "shiki", "alts": ["shiki ichinose"]},
    {"q": "Je suis un assassin né dans une famille de tueurs, et la survie est mon seul code. Quel manga ?",
     "answer": "satsudou", "alts": ["satsu dou"]},
    {"q": "Mon univers parle de football italien, de tactique et de défense de fer. Quel manga ?",
     "answer": "catenaccio", "alts": []},
    {"q": "Je suis un lecteur d'élite qui repère le talent avant qu'il n'éclose. Mon métier dans une team scan ?",
     "answer": "beta reader", "alts": ["beta-reader", "betareader"]},
    {"q": "Je suis un yakuza qui contrôle Tokyo depuis l'ombre. Quel manga ?",
     "answer": "tokyo underworld", "alts": ["tokyo", "underworld"]},
    {"q": "Sans moi, les bulles de manga restent vides. Quel rôle dans la team ?",
     "answer": "traducteur", "alts": ["trad", "translator", "traduction"]},
    {"q": "Je nettoie les pages, j'efface les textes japonais. Quel rôle ?",
     "answer": "cleaner", "alts": ["cleaning", "clean"]},
    {"q": "Je place le texte traduit dans les bulles avec la bonne typo. Quel rôle ?",
     "answer": "typesetter", "alts": ["type", "typesetting"]},
    {"q": "Je relis tout pour traquer la moindre faute. Quel rôle ?",
     "answer": "correcteur", "alts": ["check", "checker", "correction", "relecture"]},
    {"q": "Une lame courbe japonaise, symbole du samouraï. Quel objet ?",
     "answer": "katana", "alts": ["sabre"]},
    {"q": "Petit couteau de ninja qu'on lance en silence. Quel objet ?",
     "answer": "shuriken", "alts": []},
    {"q": "Je suis un samouraï sans maître, errant le long des routes. Quel mot ?",
     "answer": "ronin", "alts": []},
    {"q": "Je suis un esprit-renard à plusieurs queues, célèbre dans le folklore japonais. Quel yokai ?",
     "answer": "kitsune", "alts": []},
    {"q": "Manga centré sur un démon-flamme et un institut d'exorcistes. Quel manga ?",
     "answer": "blue exorcist", "alts": ["ao no exorcist", "blueexorcist", "ao"]},
    {"q": "Petite soeur de Rin, calme, observatrice. Qui ?",
     "answer": "yukio", "alts": ["yukio okumura"]},
    {"q": "Je suis un soldat sans visage qui marche pour le shogun. Quel guerrier ?",
     "answer": "ashigaru", "alts": []},
    {"q": "Pour planter du texte dans une case, je dois maîtriser cet art typographique. Quoi ?",
     "answer": "typesetting", "alts": ["type", "typeset"]},
    {"q": "Trois lettres qui désignent un effet sonore en BD/manga.",
     "answer": "sfx", "alts": ["onomatopee"]},
    # — Culture générale —
    {"q": "Je suis le plus grand océan du monde. Lequel ?",
     "answer": "pacifique", "alts": ["ocean pacifique"]},
    {"q": "Je suis la planète rouge du système solaire. Laquelle ?",
     "answer": "mars", "alts": []},
    {"q": "Tour emblématique de Paris construite en 1889 pour l'Exposition universelle. Quoi ?",
     "answer": "tour eiffel", "alts": ["eiffel"]},
    {"q": "Je suis le plus long fleuve d'Afrique. Lequel ?",
     "answer": "nil", "alts": ["le nil"]},
    {"q": "Animal le plus rapide sur terre, félin tacheté d'Afrique. Lequel ?",
     "answer": "guepard", "alts": ["gepard", "cheetah"]},
    {"q": "Je suis le sommet le plus haut du monde, 8849 mètres. Lequel ?",
     "answer": "everest", "alts": ["mont everest"]},
    {"q": "Peintre italien de la Joconde et de la Cène. Qui ?",
     "answer": "leonard de vinci", "alts": ["vinci", "da vinci", "leonard", "leonardo"]},
    {"q": "Je suis le plus petit pays du monde, enclavé dans Rome. Lequel ?",
     "answer": "vatican", "alts": ["cite du vatican"]},
    {"q": "Instrument de musique à 88 touches, noir et blanc. Lequel ?",
     "answer": "piano", "alts": []},
    {"q": "Capitale du Japon, mégalopole de plus de 13 millions d'habitants. Laquelle ?",
     "answer": "tokyo", "alts": []},
    {"q": "Je suis le gaz que nous respirons, 21% de l'atmosphère. Lequel ?",
     "answer": "oxygene", "alts": ["o2"]},
    {"q": "Ce reptile géant a dominé la Terre pendant 165 millions d'années. Quel groupe ?",
     "answer": "dinosaure", "alts": ["dinosaures", "dino"]},
    {"q": "Fruit jaune courbé, riche en potassium, adoré des singes. Lequel ?",
     "answer": "banane", "alts": []},
    {"q": "Scientifique qui a découvert la relativité. Qui ?",
     "answer": "einstein", "alts": ["albert einstein"]},
    {"q": "Ce sport se joue avec une balle orange et un panier en hauteur. Lequel ?",
     "answer": "basketball", "alts": ["basket", "basket-ball"]},
    {"q": "Dieu grec de la foudre et roi de l'Olympe. Qui ?",
     "answer": "zeus", "alts": []},
    {"q": "Continent de glace situé au pôle Sud. Lequel ?",
     "answer": "antarctique", "alts": ["antartique"]},
    {"q": "La Grande Muraille est le plus grand monument de quel pays ?",
     "answer": "chine", "alts": []},
    {"q": "Compositeur allemand devenu sourd, auteur de la 9e symphonie. Qui ?",
     "answer": "beethoven", "alts": ["ludwig van beethoven"]},
    {"q": "Oiseau noir et blanc qui ne vole pas et vit en Antarctique. Lequel ?",
     "answer": "manchot", "alts": ["pingouin"]},
]

# ─── Citations (deviner le manga) ───────────────────────────────────────────

QUOTES = [
    {"text": "« Je deviendrai exorciste, et je tuerai Satan ! »",
     "answer": "blue exorcist", "alts": ["ao no exorcist", "blueexorcist", "blue", "ao"]},
    {"text": "« La défense, c'est l'art de transformer un mur en piège. »",
     "answer": "catenaccio", "alts": []},
    {"text": "« Tuer, c'est la seule chose que je sais bien faire. »",
     "answer": "satsudou", "alts": []},
    {"text": "« Si tu veux survivre dans ce milieu, oublie ton passé. »",
     "answer": "tokyo underworld", "alts": ["tokyo", "underworld"]},
    {"text": "« Je porte ce masque pour ne pas oublier qui je dois sauver. »",
     "answer": "tougen anki", "alts": ["tougen", "anki"]},
    {"text": "« Mon frère ne sait pas encore qui je suis vraiment. »",
     "answer": "blue exorcist", "alts": ["ao no exorcist", "blue", "ao"]},
    {"text": "« Le ballon ne ment jamais. »",
     "answer": "catenaccio", "alts": []},
    {"text": "« Un assassin n'a ni amis, ni serment. »",
     "answer": "satsudou", "alts": []},
    {"text": "« Le sang qui coule dans mes veines est celui d'un démon. »",
     "answer": "blue exorcist", "alts": ["ao no exorcist", "blue", "ao"]},
    {"text": "« On ne marchande pas avec un oni. »",
     "answer": "tougen anki", "alts": ["tougen", "anki"]},
    {"text": "« Tout Tokyo nous appartient, du sous-sol au sommet. »",
     "answer": "tokyo underworld", "alts": ["tokyo", "underworld"]},
    {"text": "« Une équipe sans défense n'est qu'une cible. »",
     "answer": "catenaccio", "alts": []},
    {"text": "« Je suis le couteau dans l'ombre, le mot dans le silence. »",
     "answer": "satsudou", "alts": []},
    # — Nouvelles citations —
    {"text": "« Mes flammes bleues brûlent plus fort que l'enfer lui-même. »",
     "answer": "blue exorcist", "alts": ["ao no exorcist", "blue", "ao"]},
    {"text": "« Le masque cache mes larmes, pas ma détermination. »",
     "answer": "tougen anki", "alts": ["tougen", "anki"]},
    {"text": "« Dans les rues de Tokyo, seul le plus rusé survit. »",
     "answer": "tokyo underworld", "alts": ["tokyo", "underworld"]},
    {"text": "« Le terrain est mon champ de bataille, le ballon mon arme. »",
     "answer": "catenaccio", "alts": []},
    {"text": "« Chaque contrat signé est une âme de moins. »",
     "answer": "satsudou", "alts": []},
    {"text": "« Satan est mon père, mais l'humanité est ma famille. »",
     "answer": "blue exorcist", "alts": ["ao no exorcist", "blue", "ao"]},
    {"text": "« La nuit de Tokyo appartient à ceux qui n'ont plus rien à perdre. »",
     "answer": "tokyo underworld", "alts": ["tokyo", "underworld"]},
    {"text": "« Ma soeur est la raison pour laquelle je porte ce fardeau. »",
     "answer": "tougen anki", "alts": ["tougen", "anki"]},
    {"text": "« Le catenaccio n'est pas de la lâcheté, c'est de l'intelligence. »",
     "answer": "catenaccio", "alts": []},
]

# ─── Rebus emojis ───────────────────────────────────────────────────────────

EMOJI_REBUS = [
    {"emoji": "🔵😈⛪", "answer": "blue exorcist", "alts": ["ao no exorcist", "blueexorcist", "blue", "ao"]},
    {"emoji": "⚽🥅🇮🇹", "answer": "catenaccio", "alts": []},
    {"emoji": "🗡️🥷💀", "answer": "satsudou", "alts": []},
    {"emoji": "🏙️🌃🔫", "answer": "tokyo underworld", "alts": ["tokyo", "underworld"]},
    {"emoji": "👹🍑🌀", "answer": "tougen anki", "alts": ["tougen", "anki"]},
    {"emoji": "🔵🔥👦👦", "answer": "blue exorcist", "alts": ["ao no exorcist", "blue", "ao"]},
    {"emoji": "🥷⚔️🌸", "answer": "ronin", "alts": []},
    {"emoji": "📖✏️🇫🇷", "answer": "traduction", "alts": ["traducteur", "trad"]},
    {"emoji": "🧹📄✨", "answer": "cleaning", "alts": ["clean", "cleaner"]},
    {"emoji": "✍️💬📐", "answer": "typesetting", "alts": ["typeset", "type"]},
    {"emoji": "🦊👺🍙", "answer": "kitsune", "alts": []},
    {"emoji": "🐉🌫️🌑", "answer": "dragon", "alts": []},
    {"emoji": "🏰⚔️👑", "answer": "royaume", "alts": ["chateau", "empire"]},
    {"emoji": "🌸🇯🇵🎎", "answer": "matsuri", "alts": ["festival"]},
    # — Nouveaux rebus —
    {"emoji": "🗼🇫🇷❤️", "answer": "paris", "alts": ["france"]},
    {"emoji": "🌋🔥💀", "answer": "volcan", "alts": ["eruption"]},
    {"emoji": "🐺🌕🌲", "answer": "loup garou", "alts": ["loupgarou", "loup", "lycanthrope"]},
    {"emoji": "⚡👑🏔️", "answer": "zeus", "alts": ["olympe"]},
    {"emoji": "🎹🎵🎶", "answer": "piano", "alts": ["musique"]},
    {"emoji": "🧪⚗️💊", "answer": "chimie", "alts": ["alchimie", "potion"]},
    {"emoji": "🚀🌕👨‍🚀", "answer": "astronaute", "alts": ["cosmonaute", "espace"]},
    {"emoji": "🦁👑🌍", "answer": "lion", "alts": ["roi lion"]},
    {"emoji": "🍕🇮🇹🧀", "answer": "pizza", "alts": ["italie"]},
    {"emoji": "📐📏🔺", "answer": "pyramide", "alts": ["triangle", "egypte"]},
    {"emoji": "🎭🗡️💔", "answer": "tragedie", "alts": ["theatre", "drame"]},
    {"emoji": "⛵🏴‍☠️💰", "answer": "pirate", "alts": ["corsaire", "tresor"]},
    {"emoji": "🧠💡🔬", "answer": "einstein", "alts": ["science", "genie"]},
    {"emoji": "🐍🍎👫", "answer": "eden", "alts": ["paradis", "genese"]},
    {"emoji": "🎯🏹🦌", "answer": "chasseur", "alts": ["archer", "chasse"]},
]

# ─── Anagrammes ─────────────────────────────────────────────────────────────

ANAGRAMS = [
    # — Manga —
    {"clue": "Manga d'exorcistes au démon bleu", "answer": "blue exorcist"},
    {"clue": "Manga de football italien", "answer": "catenaccio"},
    {"clue": "Manga de yakuzas tokyoïtes", "answer": "tokyo underworld"},
    {"clue": "Manga d'oni et de masques", "answer": "tougen anki"},
    {"clue": "Manga d'assassinat", "answer": "satsudou"},
    {"clue": "Lame courbe japonaise", "answer": "katana"},
    {"clue": "Samouraï errant", "answer": "ronin"},
    {"clue": "Esprit-renard japonais", "answer": "kitsune"},
    {"clue": "Petit couteau de jet", "answer": "shuriken"},
    {"clue": "Scan brut non traduit", "answer": "raw"},
    {"clue": "Pose des textes dans les bulles", "answer": "typesetting"},
    {"clue": "Nettoie les pages", "answer": "cleaning"},
    {"clue": "Notre team de traduction", "answer": "lanortrad"},
    {"clue": "Festival traditionnel japonais", "answer": "matsuri"},
    # — Culture générale —
    {"clue": "Instrument à 88 touches", "answer": "piano"},
    {"clue": "Plus haute montagne du monde", "answer": "everest"},
    {"clue": "Planète rouge", "answer": "mars"},
    {"clue": "Fruit tropical épineux à chair jaune", "answer": "ananas"},
    {"clue": "Art du papier plié japonais", "answer": "origami"},
    {"clue": "Roi des dieux grecs", "answer": "zeus"},
    {"clue": "Tour de fer parisienne", "answer": "eiffel"},
    {"clue": "Grand félin rayé d'Asie", "answer": "tigre"},
    {"clue": "Boisson chaude japonaise en poudre verte", "answer": "matcha"},
    {"clue": "Scientifique de la relativité", "answer": "einstein"},
    {"clue": "Sport avec raquette et filet", "answer": "tennis"},
    {"clue": "Capitale de l'Italie", "answer": "rome"},
    {"clue": "Dessert français feuilleté en croissant", "answer": "croissant"},
    {"clue": "Reptile géant disparu il y a 66 millions d'années", "answer": "dinosaure"},
    {"clue": "Héros de la mythologie grecque aux 12 travaux", "answer": "hercule"},
]

# ─── Panels manga (deviner le manga d'après une description) ────────────────

PANELS = [
    {"url": None, "caption": "Un démon adolescent à mèches bleues, queue agitée, sourire en coin",
     "answer": "blue exorcist", "alts": ["ao no exorcist", "blue", "ao"]},
    {"url": None, "caption": "Un oni masqué tient sa petite soeur dans ses bras dans la neige",
     "answer": "tougen anki", "alts": ["tougen", "anki"]},
    {"url": None, "caption": "Un footballeur italien retient un attaquant adverse au poteau de corner",
     "answer": "catenaccio", "alts": []},
    {"url": None, "caption": "Un assassin en costume noir tire avec deux pistolets dans une ruelle pluvieuse",
     "answer": "satsudou", "alts": []},
    {"url": None, "caption": "Un yakuza tatoué allume une cigarette devant un néon Shinjuku",
     "answer": "tokyo underworld", "alts": ["tokyo", "underworld"]},
    # — Nouveaux panels —
    {"url": None, "caption": "Deux frères jumeaux se font face, l'un avec des flammes bleues, l'autre avec un pistolet",
     "answer": "blue exorcist", "alts": ["ao no exorcist", "blue", "ao"]},
    {"url": None, "caption": "Un jeune homme masqué court sur les toits d'un village japonais en flammes",
     "answer": "tougen anki", "alts": ["tougen", "anki"]},
    {"url": None, "caption": "Un gardien de but plonge dans la boue pour arrêter un tir puissant",
     "answer": "catenaccio", "alts": []},
    {"url": None, "caption": "Une silhouette sombre nettoie son arme dans un appartement vide de Shinjuku",
     "answer": "satsudou", "alts": []},
    {"url": None, "caption": "Des hommes en costume sombre échangent une mallette dans un parking souterrain de Tokyo",
     "answer": "tokyo underworld", "alts": ["tokyo", "underworld"]},
]

# ─── Openings / OST ─────────────────────────────────────────────────────────

OPENINGS = [
    {"clip": "Core Pride — UVERworld",
     "answer": "blue exorcist", "alts": ["ao no exorcist", "blue", "ao"]},
    {"clip": "In My World — ROOKiEZ is PUNK'D",
     "answer": "blue exorcist", "alts": ["ao no exorcist", "blue", "ao"]},
    {"clip": "(devinette spoiler) Tougen Anki Opening 1",
     "answer": "tougen anki", "alts": ["tougen", "anki"]},
    {"clip": "(devinette spoiler) Catenaccio Opening 1",
     "answer": "catenaccio", "alts": []},
    {"clip": "(devinette spoiler) Tokyo Underworld Opening 1",
     "answer": "tokyo underworld", "alts": ["tokyo", "underworld"]},
    {"clip": "(devinette spoiler) Satsudou Opening 1",
     "answer": "satsudou", "alts": []},
]

# ─── Personnages (20 Questions) ─────────────────────────────────────────────

CHARACTERS = [
    {
        "name": "Rin Okumura", "manga": "Blue Exorcist",
        "tags": {"male": True, "demon": True, "exorcist": True, "swordsman": True,
                 "human_appearance": True, "antagonist": False, "leader": False,
                 "uses_magic": True, "japanese_name": True, "young": True},
    },
    {
        "name": "Yukio Okumura", "manga": "Blue Exorcist",
        "tags": {"male": True, "demon": False, "exorcist": True, "swordsman": False,
                 "human_appearance": True, "antagonist": False, "leader": True,
                 "uses_magic": True, "japanese_name": True, "young": True},
    },
    {
        "name": "Shiki Ichinose", "manga": "Tougen Anki",
        "tags": {"male": True, "demon": True, "exorcist": False, "swordsman": False,
                 "human_appearance": True, "antagonist": False, "leader": False,
                 "uses_magic": True, "japanese_name": True, "young": True},
    },
    {
        "name": "Yamato", "manga": "Tougen Anki",
        "tags": {"male": True, "demon": True, "exorcist": False, "swordsman": True,
                 "human_appearance": True, "antagonist": True, "leader": True,
                 "uses_magic": True, "japanese_name": True, "young": False},
    },
    {
        "name": "Le Boss de Tokyo Underworld", "manga": "Tokyo Underworld",
        "tags": {"male": True, "demon": False, "exorcist": False, "swordsman": False,
                 "human_appearance": True, "antagonist": True, "leader": True,
                 "uses_magic": False, "japanese_name": True, "young": False},
    },
    {
        "name": "L'Assassin de Satsudou", "manga": "Satsudou",
        "tags": {"male": True, "demon": False, "exorcist": False, "swordsman": False,
                 "human_appearance": True, "antagonist": False, "leader": False,
                 "uses_magic": False, "japanese_name": True, "young": True},
    },
    {
        "name": "Le Capitaine de Catenaccio", "manga": "Catenaccio",
        "tags": {"male": True, "demon": False, "exorcist": False, "swordsman": False,
                 "human_appearance": True, "antagonist": False, "leader": True,
                 "uses_magic": False, "japanese_name": False, "young": True},
    },
]

# Questions du 20Q : (label affiché, clé du tag)
CHARACTER_QUESTIONS = [
    ("Est-ce un personnage masculin ?", "male"),
    ("Est-ce un démon ?", "demon"),
    ("Est-ce un exorciste ?", "exorcist"),
    ("Manie-t-il une épée principalement ?", "swordsman"),
    ("A-t-il une apparence humaine ?", "human_appearance"),
    ("Est-ce un antagoniste ?", "antagonist"),
    ("Est-ce un leader ?", "leader"),
    ("Utilise-t-il une forme de magie ou pouvoir surnaturel ?", "uses_magic"),
    ("A-t-il un nom japonais ?", "japanese_name"),
    ("Est-il décrit comme jeune ?", "young"),
]
