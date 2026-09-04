"""
Client du site LanorTrad — le site est la source de vérité
============================================================
Le site publie ses données dans quatre fichiers JS statiques, qui sont
*déjà* ce que l'équipe met à jour à la main :

  /js/data/series.js    → window.SERIES   (catalogue : genres, auteur, note…)
  /js/data/chapters.js  → window.CHAPTERS (index des chapitres parus)
  /js/data/atelier.js   → window.ATELIER  (où en est chaque prochain chapitre)
  /js/data/covers.js    → window.COVERS   (variantes de couvertures)

On les lit tels quels : rien à ressaisir dans Discord, aucun risque de
divergence entre le site et le serveur.

Ce ne sont pas du JSON (clés sans guillemets, virgules traînantes,
commentaires) : `parse_js_literal` s'en occupe sans dépendance externe.
"""
import json
import logging
import re
import unicodedata

log = logging.getLogger("lanortrad.site")

# (clé, chemin, variable JS, marqueur éventuel)
# chapters.js est généré en format COMPACT et déplié par le site au runtime :
# on lit directement l'argument de `expand(`.
DATA_FILES = {
    "series":   ("/js/data/series.js",   "SERIES",   None),
    "chapters": ("/js/data/chapters.js", "CHAPTERS", "return expand("),
    "atelier":  ("/js/data/atelier.js",  "ATELIER",  None),
    "covers":   ("/js/data/covers.js",   "COVERS",   None),
}

# Étapes de fabrication — identiques à window.LTatelier.STEPS sur le site.
STEPS = [
    ("pages",  "Pages trouvées", "📥", "Les pages japonaises sont récupérées et remises au propre."),
    ("clean",  "Clean",          "🧽", "On efface les textes d'origine et on redessine ce qui passe dessous."),
    ("trad",   "Traduction",     "💬", "Le chapitre passe du japonais au français, réplique par réplique."),
    ("edit",   "Edit",           "✍️", "Le texte français est placé dans les bulles, avec les bonnes polices."),
    ("qcheck", "Q-check",        "🔍", "Dernière relecture : fautes, sens, cohérence, oublis."),
    ("sortie", "Sortie",         "🎉", "C'est en ligne. Bonne lecture !"),
]
STEP_IDS = [s[0] for s in STEPS]
STEP_INFO = {s[0]: s for s in STEPS}

DAYS_FR = ["Dimanche", "Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi"]
WEEK_ORDER = [1, 2, 3, 4, 5, 6, 0]        # lundi → dimanche, comme sur le site


# ═══════════════════════════════════════════════════════
# Parsing d'un littéral JavaScript
# ═══════════════════════════════════════════════════════

def _strip_and_fix(src: str) -> str:
    """Enlève les commentaires, quote les clés nues, supprime les virgules
    traînantes — en respectant le contenu des chaînes."""
    out = []
    i, n = 0, len(src)
    quote = None                      # guillemet ouvrant courant, ou None

    while i < n:
        c = src[i]

        if quote:
            out.append(c)
            if c == "\\" and i + 1 < n:      # échappement : on recopie tel quel
                out.append(src[i + 1])
                i += 2
                continue
            if c == quote:
                quote = None
            i += 1
            continue

        # hors chaîne
        if c in "\"'":
            quote = c
            out.append('"' if c == "'" else c)
            i += 1
            continue

        if c == "/" and i + 1 < n:
            if src[i + 1] == "/":
                i = src.find("\n", i)
                if i == -1:
                    break
                continue
            if src[i + 1] == "*":
                end = src.find("*/", i + 2)
                i = n if end == -1 else end + 2
                continue

        out.append(c)
        i += 1

    text = "".join(out)
    # clé nue → clé entre guillemets :   chapter: "19"  →  "chapter": "19"
    text = re.sub(r'([{,]\s*)([A-Za-z_$][\w$]*)\s*:', r'\1"\2":', text)
    # virgule traînante avant } ou ]
    text = re.sub(r",(\s*[}\]])", r"\1", text)
    return text


def parse_js_literal(source: str, varname: str, marker: str = None):
    """Extrait `window.VARNAME = <littéral>;` et le convertit en objet Python.

    `marker` permet de viser un littéral ailleurs dans le fichier — par
    exemple l'argument de `expand(` dans chapters.js, qui est généré sous
    forme compacte puis déplié par le site.
    """
    if marker:
        pos = source.find(marker)
        if pos == -1:
            raise ValueError(f"{varname} : marqueur « {marker} » introuvable")
        start = pos + len(marker)
    else:
        match = re.search(
            r"(?:window\s*\.\s*)?%s\s*=\s*" % re.escape(varname), source)
        if not match:
            raise ValueError(f"variable {varname} introuvable")
        start = match.end()

    while start < len(source) and source[start] in " \t\r\n":
        start += 1
    if start >= len(source) or source[start] not in "[{":
        raise ValueError(f"{varname} : littéral attendu")

    opening = source[start]
    closing = "]" if opening == "[" else "}"
    depth, i, quote = 0, start, None
    while i < len(source):
        c = source[i]
        if quote:
            if c == "\\":
                i += 2
                continue
            if c == quote:
                quote = None
        elif c in "\"'":
            quote = c
        elif c == opening:
            depth += 1
        elif c == closing:
            depth -= 1
            if depth == 0:
                return json.loads(_strip_and_fix(source[start:i + 1]))
        i += 1
    raise ValueError(f"{varname} : littéral non terminé")


# ═══════════════════════════════════════════════════════
# Modèle
# ═══════════════════════════════════════════════════════

def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKD", text or "")
    text = "".join(c for c in text if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


class SiteData:
    """Photographie des données du site à un instant T."""

    def __init__(self, series=None, chapters=None, atelier=None, covers=None,
                 base_url=""):
        self.base_url = base_url.rstrip("/")
        self.series = series or []
        self.chapters = chapters or {}
        self.atelier = atelier or {}
        self.covers = covers or {}

    # ─── Accès ───
    def get_series(self, series_id: str):
        target = normalize(series_id)
        for s in self.series:
            if normalize(s.get("id")) == target or normalize(s.get("title")) == target:
                return s
        return None

    def ongoing(self):
        """Séries en cours (mangas), comme le planning du site."""
        return [s for s in self.series
                if s.get("type") == "manga"
                and "cours" in (s.get("status") or "").lower()]

    def finished(self):
        return [s for s in self.series if "termin" in (s.get("status") or "").lower()]

    def last_chapter(self, series_id: str):
        entries = self.chapters.get(series_id) or []
        if not entries or not isinstance(entries, list):
            return None
        first = entries[0]
        return first.get("num") if isinstance(first, dict) else None

    def cover_url(self, series: dict, width: int = 720) -> str:
        """URL absolue de la couverture, en privilégiant la variante responsive."""
        raw = series.get("cover")
        if not raw:
            return ""
        variant = self.covers.get(raw)
        if variant and variant.get("base"):
            widths = variant.get("w") or [width]
            chosen = max([w for w in widths if w <= width] or [min(widths)])
            return f"{self.base_url}/{variant['base']}-{chosen}.webp"
        return f"{self.base_url}/{raw.replace(' ', '%20')}"

    def series_url(self, series: dict) -> str:
        url = series.get("url") or ""
        return f"{self.base_url}/{url}" if url else f"{self.base_url}/catalogue"

    def accent(self, series: dict, default: int = 0xB30000) -> int:
        raw = (series.get("accent") or "").lstrip("#")
        try:
            return int(raw, 16)
        except (ValueError, TypeError):
            return default

    # ─── Atelier ───
    def workshop(self):
        """Chapitres en fabrication, du plus avancé au moins avancé."""
        items = []
        for series_id, entry in (self.atelier or {}).items():
            if not isinstance(entry, dict):
                continue
            step = entry.get("step") or STEP_IDS[0]
            index = STEP_IDS.index(step) if step in STEP_IDS else 0
            items.append({
                "series": series_id,
                "chapter": entry.get("chapter"),
                "step": step,
                "step_index": index,
                "step_label": STEP_INFO.get(step, ("", step, "•", ""))[1],
                "step_emoji": STEP_INFO.get(step, ("", "", "•", ""))[2],
                "step_desc": STEP_INFO.get(step, ("", "", "", ""))[3],
                "progress": f"{index + 1}/{len(STEPS)}",
                "updated": entry.get("updated"),
                "eta": entry.get("eta"),
                "note": entry.get("note"),
            })
        items.sort(key=lambda i: (-i["step_index"], i["series"]))
        return items

    def workshop_signature(self) -> dict:
        """Empreinte {série: 'chapitre|étape'} pour détecter les changements."""
        return {i["series"]: f"{i['chapter']}|{i['step']}" for i in self.workshop()}

    # ─── Planning hebdomadaire (même règle que le site) ───
    def weekly(self):
        """Chaque série en cours tombe le jour de semaine de sa dernière MàJ."""
        by_day = {}
        for s in self.ongoing():
            last = s.get("lastUpdate")
            try:
                import datetime
                dow = datetime.date.fromisoformat(last).weekday()
                dow = (dow + 1) % 7          # ISO (lundi=0) → JS (dimanche=0)
            except (TypeError, ValueError):
                dow = 6
            entry = self.atelier.get(s["id"]) if self.atelier else None
            if entry and entry.get("chapter"):
                nxt = entry["chapter"]
            else:
                last_num = self.last_chapter(s["id"])
                try:
                    nxt = str(int(float(last_num)) + 1)
                except (TypeError, ValueError):
                    nxt = "?"
            by_day.setdefault(dow, []).append({"series": s, "next": nxt,
                                               "atelier": entry})
        return [(DAYS_FR[d], by_day.get(d, [])) for d in WEEK_ORDER]


def expand_chapters(compact: dict) -> dict:
    """Déplie l'index compact de chapters.js : {série: [{num, pages}, …]}."""
    out = {}
    for series_id, data in (compact or {}).items():
        if not isinstance(data, dict):
            continue
        prefix = data.get("p", "")
        entries = []
        for row in data.get("c", []):
            if not isinstance(row, list) or not row:
                continue
            opts = row[2] if len(row) > 2 and isinstance(row[2], dict) else {}
            folder = opts.get("f", (opts.get("p", prefix)) + str(row[0]))
            entries.append({
                "num": str(row[0]),
                "pages": row[1] if len(row) > 1 else None,
                "folder": folder,
            })
        out[series_id] = entries
    return out


async def fetch(session, base_url: str) -> SiteData:
    """Télécharge et parse les quatre fichiers de données du site."""
    base_url = base_url.rstrip("/")
    parsed = {}
    for key, (path, varname, marker) in DATA_FILES.items():
        async with session.get(f"{base_url}{path}") as resp:
            resp.raise_for_status()
            raw = await resp.text()
        value = parse_js_literal(raw, varname, marker)
        if key == "chapters":
            value = expand_chapters(value)
        parsed[key] = value
        log.debug("site: %s → %d entrées", key, len(value))
    return SiteData(base_url=base_url, **parsed)
