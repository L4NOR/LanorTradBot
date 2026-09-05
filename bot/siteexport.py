"""
Pont atelier → site : régénérer `js/data/atelier.js`
======================================================
Les fiches Discord savent où en est chaque chapitre ; le site le sait aussi,
dans son propre fichier. Deux sources de vérité finissent toujours par
diverger — ce module fabrique la seconde à partir de la première.

Trois précautions, parce qu'on réécrit un fichier de production :

  • **On part du fichier existant.** Une série sans fiche Discord garde son
    entrée telle quelle ; on n'efface jamais ce qu'on ne sait pas produire.
  • **`eta` et `note` du site survivent.** Le bot ne les connaît pas
    toujours ; quand il n'a rien à dire, l'ancienne valeur reste.
  • **Le rendu imite la mise en forme à la main.** Colonnes alignées, notes
    sur une ligne de continuation : le diff git montre ce qui change
    vraiment, pas une reformatation complète.

Les fonctions sont pures et sans Discord : `python -m bot.siteexport` les
teste sur le fichier en ligne.
"""
import datetime
import logging
import re

try:
    from zoneinfo import ZoneInfo
    FUSEAU = ZoneInfo("Europe/Paris")
except Exception:                                  # pragma: no cover
    FUSEAU = None

log = logging.getLogger("lanortrad.siteexport")

VARIABLE = "ATELIER"
CHEMIN = "js/data/atelier.js"

# Une entrée terminée disparaît toute seule du site 3 jours après `updated`.
# On garde une marge pour ne pas la faire réapparaître entre deux exports.
GARDE_JOURS = 5


def _jour(ts: float) -> str:
    """Horodatage → « AAAA-MM-JJ », heure de Paris."""
    moment = datetime.datetime.fromtimestamp(ts, FUSEAU) if FUSEAU \
        else datetime.datetime.fromtimestamp(ts)
    return moment.strftime("%Y-%m-%d")


def _echapper(valeur) -> str:
    return str(valeur).replace("\\", "\\\\").replace('"', '\\"')


# ═══════════════════════════════════════════════════════
# Lecture du fichier existant
# ═══════════════════════════════════════════════════════

def entete(brut: str) -> str:
    """Le bloc de commentaires qui précède `window.ATELIER`.

    C'est la documentation que lit la personne qui édite le fichier à la
    main : elle doit survivre à chaque export.
    """
    trouve = re.search(r"(?:window\s*\.\s*)?%s\s*=" % VARIABLE, brut)
    return brut[:trouve.start()].rstrip("\n") if trouve else ""


# ═══════════════════════════════════════════════════════
# Rendu
# ═══════════════════════════════════════════════════════

def rendre(entrees: dict, tete: str = "") -> str:
    """Reconstruit le fichier complet, aligné comme s'il était écrit à la main."""
    if not entrees:
        corps = f"window.{VARIABLE} = {{}};"
        return (tete + "\n" + corps + "\n") if tete else corps + "\n"

    cles = {nom: f'"{_echapper(nom)}":' for nom in entrees}
    chapitres = {nom: f'chapter: "{_echapper(val.get("chapter", ""))}",'
                 for nom, val in entrees.items()}
    etapes = {nom: f'step: "{_echapper(val.get("step", ""))}",'
              for nom, val in entrees.items()}

    l_cle = max(len(v) for v in cles.values())
    l_chap = max(len(v) for v in chapitres.values())
    l_etape = max(len(v) for v in etapes.values())
    marge = " " * (2 + l_cle + 1 + 2)          # sous le « { » ouvrant

    lignes = []
    noms = list(entrees)
    for index, nom in enumerate(noms):
        val = entrees[nom]
        debut = (f"  {cles[nom].ljust(l_cle)} {{ "
                 f"{chapitres[nom].ljust(l_chap)} "
                 f"{etapes[nom].ljust(l_etape)} "
                 f'updated: "{_echapper(val.get("updated", ""))}"')
        if val.get("eta"):
            debut += f', eta: "{_echapper(val["eta"])}"'

        fin = " }" if index == len(noms) - 1 else " },"
        if val.get("note"):
            lignes.append(debut + ",\n" + marge
                          + f'note: "{_echapper(val["note"])}"' + fin)
        else:
            lignes.append(debut + fin)

    corps = f"window.{VARIABLE} = {{\n" + "\n".join(lignes) + "\n};"
    return (tete + "\n" + corps + "\n") if tete else corps + "\n"


# ═══════════════════════════════════════════════════════
# Fiches Discord → entrées du site
# ═══════════════════════════════════════════════════════

def _derniere_etape(fiche: dict):
    """(id de l'étape, horodatage, note) de la dernière étape validée."""
    faites = fiche.get("etapes") or {}
    if not faites:
        return None, fiche.get("ouvert_le", 0), None
    eid, detail = max(faites.items(), key=lambda kv: kv[1].get("le", 0))
    return eid, detail.get("le", 0), detail.get("note")


def fiche_a_retenir(fiches: list):
    """Le site n'affiche qu'un chapitre par série : le prochain à sortir.

    On prend donc la fiche ouverte la plus ancienne. Si tout est terminé,
    la plus récemment finie — le temps que le site l'affiche puis l'oublie.
    """
    en_cours = [f for f in fiches if not f.get("termine")]
    if en_cours:
        return min(en_cours, key=lambda f: f.get("ouvert_le", 0))
    if fiches:
        return max(fiches, key=lambda f: _derniere_etape(f)[1])
    return None


def entrees_depuis_fiches(fiches: list, noms: dict, *,
                          maintenant: float = None,
                          garde_jours: int = GARDE_JOURS):
    """Transforme les fiches en entrées `atelier.js`.

    `noms` fait la correspondance clé de série → nom exact sur le site.
    Retourne (entrées, remarques) — les remarques disent ce qui a été
    écarté et pourquoi, pour que rien ne disparaisse en silence.
    """
    import time
    maintenant = maintenant if maintenant is not None else time.time()

    par_serie, remarques = {}, []
    for fiche in fiches:
        par_serie.setdefault(fiche.get("manga"), []).append(fiche)

    entrees = {}
    for cle_serie, lot in par_serie.items():
        nom = noms.get(cle_serie)
        if not nom:
            remarques.append(
                f"⚠️ `{cle_serie}` n'a pas de nom connu sur le site — ignoré.")
            continue

        fiche = fiche_a_retenir(lot)
        if fiche is None:
            continue

        etape, quand, note = _derniere_etape(fiche)
        if fiche.get("termine"):
            etape = "sortie"
            age = (maintenant - quand) / 86400
            if age > garde_jours:
                remarques.append(
                    f"⏭️ **{nom}** ch. {fiche.get('chapitre')} est sorti il y a "
                    f"{age:.0f} jours — le site l'a déjà retiré.")
                continue

        restants = [f for f in lot if f is not fiche and not f.get("termine")]
        if restants:
            autres = ", ".join(str(f.get("chapitre")) for f in restants)
            remarques.append(
                f"ℹ️ **{nom}** : le site ne montre qu'un chapitre, "
                f"c'est **{fiche.get('chapitre')}** qui passe (aussi ouverts : {autres}).")

        entree = {
            "chapter": str(fiche.get("chapitre", "")),
            "step": etape or "pages",
            "updated": _jour(quand),
        }
        if fiche.get("eta"):
            entree["eta"] = fiche["eta"]
        if note:
            entree["note"] = note
        entrees[nom] = entree

    return entrees, remarques


# ═══════════════════════════════════════════════════════
# Fusion avec ce que le site affiche déjà
# ═══════════════════════════════════════════════════════

def fusionner(site: dict, bot: dict):
    """Applique les entrées du bot au fichier du site, sans rien perdre.

    Retourne (fusion, changements) — `changements` est lisible tel quel
    dans un embed.
    """
    fusion, changements = {}, []

    for nom, ancienne in site.items():
        neuve = bot.get(nom)
        if neuve is None:
            fusion[nom] = dict(ancienne)
            changements.append(f"· **{nom}** — aucune fiche, entrée conservée")
            continue

        # Le bot ne connaît pas toujours eta/note : on garde ceux du site.
        fondue = dict(neuve)
        for champ in ("eta", "note"):
            if not fondue.get(champ) and ancienne.get(champ):
                fondue[champ] = ancienne[champ]

        avant = (str(ancienne.get("chapter", "")), ancienne.get("step"))
        apres = (fondue["chapter"], fondue["step"])
        if avant == apres:
            # Même chapitre, même étape : seule la date peut avoir bougé.
            # Le dire, plutôt que d'annoncer « inchangé » sur une ligne
            # que le diff git montrera quand même comme modifiée.
            if ancienne.get("updated") != fondue.get("updated"):
                changements.append(
                    f"📅 **{nom}** — {apres[1]}, date corrigée "
                    f"({ancienne.get('updated')} → **{fondue.get('updated')}**)")
            else:
                changements.append(f"· **{nom}** — inchangé ({apres[1]})")
        elif avant[0] != apres[0]:
            changements.append(
                f"🆕 **{nom}** — ch. {avant[0]} → **ch. {apres[0]}** ({apres[1]})")
        else:
            changements.append(
                f"➡️ **{nom}** ch. {apres[0]} — {avant[1]} → **{apres[1]}**")
        fusion[nom] = fondue

    for nom, neuve in bot.items():
        if nom in fusion:
            continue
        fusion[nom] = dict(neuve)
        changements.append(
            f"➕ **{nom}** — ajouté (ch. {neuve['chapter']}, {neuve['step']})")

    return fusion, changements


# ═══════════════════════════════════════════════════════
# Vérification manuelle : python -m bot.siteexport
# ═══════════════════════════════════════════════════════

if __name__ == "__main__":                          # pragma: no cover
    import sys
    import urllib.request

    url = "https://lanortrad.com/js/data/atelier.js"
    brut = urllib.request.urlopen(
        urllib.request.Request(url, headers={"User-Agent": "LanorTradBot"}),
        timeout=20).read().decode("utf-8")

    sys.path.insert(0, ".")
    from bot.site import parse_js_literal

    actuel = parse_js_literal(brut, VARIABLE)
    refait = rendre(actuel, entete(brut))

    if refait == brut:
        print("Aller-retour identique au caractere pres.")
    else:
        print("DIFFERENCES :")
        import difflib
        for ligne in difflib.unified_diff(
                brut.splitlines(), refait.splitlines(),
                "en ligne", "regenere", lineterm="", n=1):
            print(" ", ligne)
