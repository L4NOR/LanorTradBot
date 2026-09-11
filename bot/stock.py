"""
Le stock — ce qui est déjà fait d'avance, par plages de chapitres
==================================================================
Une fiche, c'est un chapitre qu'on fabrique en ce moment : un message, un
fil, un métier qui attend. Un stock, c'est autre chose — « les chapitres
248 à 293 sont nettoyés, ils attendent la traduction ». Quarante-six
fiches pour dire ça noieraient l'atelier et repingeraient tout le monde
tous les trois jours ; une plage le dit en une ligne.

Le stock retient donc, par série, des **plages qui ne se chevauchent
jamais** :

    Tokyo Underworld   44 → 46   prêt à sortir
                       47 → 97   attend la traduction

C'est la seule règle du module, et elle se tient toute seule : quand on
pose une plage sur un terrain déjà occupé, **la plus avancée garde son
terrain** et l'autre est rognée. Peu importe l'ordre dans lequel on
déclare : annoncer « 44 à 97 nettoyés » puis « 44 à 46 Q-checkés » donne
le même résultat que l'inverse.

Les numéros de chapitre ne sont pas des entiers (45.5 existe), d'où deux
précautions :

  • on compare sur la **droite réelle** (`num`), pas sur des chaînes —
    « 100 » ne doit pas se ranger avant « 99 » ;
  • une plage rognée ne peut pas commencer « juste après 46 » sur les
    réels, alors on borne au quart (`PAS`) et on affiche une étiquette
    lisible : le reste de 44→97 amputé de 44→46 s'écrit « 47 → 97 ».

Aucun import Discord ici : `python -m bot.stock` vérifie tout hors-ligne.
"""
import math

from bot.site import STEP_IDS, STEP_INFO

# Aucun chapitre ne tombe entre deux quarts : 0.25 sépare proprement une
# plage de sa voisine sans jamais avaler un demi-chapitre.
PAS = 0.25


# ═══════════════════════════════════════════════════════
# Numéros de chapitre
# ═══════════════════════════════════════════════════════

def num(chapitre) -> float:
    """« 45.5 » → 45.5. Lève ValueError si ce n'est pas un numéro."""
    texte = str(chapitre).strip().replace(",", ".")
    if not texte:
        raise ValueError("numéro de chapitre vide")
    return float(texte)


def label(n: float) -> str:
    """45.0 → « 45 » · 45.5 → « 45.5 »."""
    return str(int(n)) if float(n).is_integer() else f"{float(n):g}"


def label_apres(n: float) -> str:
    """L'étiquette du chapitre qui suit n — 46 → « 47 », 45.5 → « 46 »."""
    suivant = n + 0.5
    return label(suivant if suivant.is_integer() else float(math.floor(n) + 1))


def label_avant(n: float) -> str:
    """L'étiquette du chapitre qui précède n — 57 → « 56 », 45.5 → « 45 »."""
    precedent = n - 0.5
    return label(precedent if precedent.is_integer() else float(math.ceil(n) - 1))


# ═══════════════════════════════════════════════════════
# Les étapes
# ═══════════════════════════════════════════════════════

def rang(etape) -> int:
    """Position d'une étape dans la chaîne. -1 pour « rien encore »."""
    try:
        return STEP_IDS.index(etape)
    except ValueError:
        return -1


def attendue(fait) -> str:
    """L'étape qui attend, quand `fait` est la dernière étape terminée.

    `fait=None` (rien de fait) → les pages sont encore à trouver.
    `fait="qcheck"` → il ne reste qu'à sortir le chapitre.
    """
    if not fait:
        return STEP_IDS[0]
    return STEP_IDS[min(rang(fait) + 1, len(STEP_IDS) - 1)]


def faite(etape) -> str:
    """L'inverse : l'étape terminée quand `etape` est celle qui attend."""
    index = rang(etape) - 1
    return STEP_IDS[index] if index >= 0 else None


# ═══════════════════════════════════════════════════════
# Les plages
# ═══════════════════════════════════════════════════════
# Une plage : {"de", "a" (étiquettes), "de_n", "a_n" (réels), "etape",
#              "fait", "note", "le", "par"}

def plage(de, a, fait, *, note=None, le=None, par=None) -> dict:
    """Fabrique une plage. `de` et `a` sont remis dans l'ordre au besoin."""
    de_n, a_n = num(de), num(a)
    if de_n > a_n:
        de_n, a_n = a_n, de_n
    return {
        "de": label(de_n), "a": label(a_n),
        "de_n": de_n, "a_n": a_n,
        "fait": fait or None, "etape": attendue(fait),
        "note": note, "le": le, "par": par,
    }


def compte(p: dict) -> int:
    """Nombre de chapitres ENTIERS dans la plage — les .5 ne comptent pas."""
    premier, dernier = math.ceil(p["de_n"]), math.floor(p["a_n"])
    return max(0, dernier - premier + 1)


def _vide(p: dict) -> bool:
    return p["de_n"] > p["a_n"]


def soustraire(p: dict, de_n: float, a_n: float) -> list:
    """`p` amputée de [de_n, a_n]. Retourne 0, 1 ou 2 morceaux."""
    if a_n < p["de_n"] or de_n > p["a_n"]:
        return [dict(p)]                       # aucun chevauchement

    morceaux = []
    if de_n > p["de_n"]:                       # il reste un bout avant
        gauche = dict(p, a_n=de_n - PAS, a=label_avant(de_n))
        if not _vide(gauche):
            morceaux.append(gauche)
    if a_n < p["a_n"]:                         # il reste un bout après
        droite = dict(p, de_n=a_n + PAS, de=label_apres(a_n))
        if not _vide(droite):
            morceaux.append(droite)
    return morceaux


def _souder(plages: list) -> list:
    """Fond les plages voisines de même étape — 44→46 et 47→97 en clean
    n'ont aucune raison de rester deux lignes."""
    ordre = sorted(plages, key=lambda p: p["de_n"])
    fondues = []
    for p in ordre:
        precedente = fondues[-1] if fondues else None
        colle = (precedente is not None
                 and precedente["etape"] == p["etape"]
                 and precedente["note"] == p["note"]
                 and p["de_n"] <= precedente["a_n"] + 1.0)
        if colle:
            if p["a_n"] > precedente["a_n"]:
                precedente["a_n"], precedente["a"] = p["a_n"], p["a"]
            precedente["le"] = max(precedente.get("le") or 0, p.get("le") or 0)
        else:
            fondues.append(dict(p))
    return fondues


def poser(plages: list, neuve: dict) -> list:
    """Pose `neuve` sur le stock d'une série. La plus avancée l'emporte.

    Une plage déjà là et plus avancée garde son terrain : c'est `neuve`
    qui est rognée. Une plage moins avancée, au contraire, cède le sien.
    À niveau égal les deux fusionnent, ce qui revient au même.
    """
    reste = [dict(neuve)]
    gardees = []

    for ancienne in plages:
        if rang(ancienne["etape"]) >= rang(neuve["etape"]):
            # L'ancienne fait autorité sur son terrain : on y renonce.
            suite = []
            for bout in reste:
                suite.extend(soustraire(bout, ancienne["de_n"], ancienne["a_n"]))
            reste = suite
            gardees.append(dict(ancienne))
        else:
            # L'ancienne est moins avancée : elle recule.
            gardees.extend(soustraire(ancienne, neuve["de_n"], neuve["a_n"]))

    return _souder(gardees + reste)


def retirer(plages: list, de_n: float, a_n: float) -> list:
    """Efface [de_n, a_n] du stock, quelle que soit l'étape."""
    reste = []
    for p in plages:
        reste.extend(soustraire(p, de_n, a_n))
    return _souder(reste)


def contient(plages: list, chapitre) -> dict:
    """La plage qui couvre ce chapitre, ou None."""
    try:
        n = num(chapitre)
    except ValueError:
        return None
    for p in plages:
        if p["de_n"] <= n <= p["a_n"]:
            return p
    return None


def tete(plages: list) -> dict:
    """La plage du plus petit numéro — le prochain chapitre à sortir.

    Le stock avance du plus ancien vers le plus récent : la plage la plus
    basse est donc aussi la plus avancée, et c'est elle que le site doit
    montrer.
    """
    return min(plages, key=lambda p: p["de_n"]) if plages else None


def ligne(p: dict) -> str:
    """« 44 → 46 · 🔍 Q-check fait, prêt à sortir » — lisible dans un embed."""
    etendue = p["de"] if p["de"] == p["a"] else f"{p['de']} → {p['a']}"
    info = STEP_INFO.get(p["etape"])
    if p["etape"] == STEP_IDS[-1]:
        etat = "🎉 prêt à sortir"
    elif info:
        etat = f"attend {info[2]} **{info[1]}**"
    else:
        etat = p["etape"]
    nb = compte(p)
    volume = f" · ~{nb} ch." if nb > 1 else ""
    note = f"\n> {p['note']}" if p.get("note") else ""
    return f"**{etendue}**{volume} — {etat}{note}"


# ═══════════════════════════════════════════════════════
# Vérification hors-ligne : python -m bot.stock
# ═══════════════════════════════════════════════════════

if __name__ == "__main__":                          # pragma: no cover
    def montre(titre, plages):
        print(f"\n{titre}")
        for p in sorted(plages, key=lambda x: x["de_n"]):
            print("   ", ligne(p).replace("\n", " "))

    # Le cas réel : Tokyo Underworld, annoncé dans les deux sens.
    a = poser([], plage(44, 97, "clean"))
    a = poser(a, plage(44, 46, "qcheck"))
    montre("Tokyo — large puis fin :", a)

    b = poser([], plage(44, 46, "qcheck"))
    b = poser(b, plage(44, 97, "clean"))
    montre("Tokyo — fin puis large :", b)
    assert [(p["de"], p["a"], p["etape"]) for p in sorted(a, key=lambda x: x["de_n"])] \
        == [(p["de"], p["a"], p["etape"]) for p in sorted(b, key=lambda x: x["de_n"])], \
        "l'ordre de déclaration ne doit rien changer"

    c = poser([], plage(57, 93, "clean"))
    c = poser(c, plage(57, 75, "edit"))
    montre("Catenaccio :", c)

    d = poser([], plage(248, 293, "clean"))
    montre("Tougen :", d)
    d = retirer(d, num(248), num(248))
    montre("Tougen, le 248 sorti du stock :", d)

    e = poser([], plage(10, 20, "clean"))
    e = poser(e, plage(14, 15, "edit"))
    montre("Trou au milieu (10→20 clean, 14→15 edit) :", e)
    assert len(e) == 3, e

    f = poser([], plage(1, 5, "clean"))
    f = poser(f, plage(6, 9, "clean"))
    montre("Deux plages de même étape se ressoudent :", f)
    assert len(f) == 1 and f[0]["a"] == "9", f

    print("\nÉtiquettes :", label_apres(46), label_apres(45.5),
          label_avant(57), label_avant(45.5))
    assert (label_apres(46), label_apres(45.5)) == ("47", "46")
    assert (label_avant(57), label_avant(45.5)) == ("56", "45")
    print("\nTout est cohérent.")
