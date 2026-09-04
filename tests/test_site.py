"""
Tests hors-ligne du client du site.
    python -m tests.test_site
Vérifie que le parseur avale bien les fichiers JS du site (clés sans
guillemets, virgules traînantes, commentaires, format compact).
"""
import sys

from bot.site import parse_js_literal, expand_chapters, SiteData

SERIES_JS = '''// commentaire
window.SERIES = [
  { id: "Tougen Anki", title: "Tougen Anki", type: "manga", status: "En cours",
    chapters: 249, lastUpdate: "2026-07-12", rating: 4.8, accent: "#e0245e",
    cover: "images/Cover/TougenAnki.jpg", url: "manga.html?id=Tougen%20Anki" },
  { id: "Countdown", type: "oneshot", status: "Terminé", chapters: 1,
    lastUpdate: "2025-12-25", rating: 4.2, accent: "#64748b" },
];
'''

ATELIER_JS = '''/* bloc */
window.ATELIER = {
  "Tougen Anki": { chapter: "248-249-250", step: "qcheck", updated: "2026-08-03",
                   eta: "2026-09-13" },
};
'''

CHAPTERS_JS = '''window.CHAPTERS = (function () {
  function expand(D) { return D; }
  return expand({"Tougen Anki":{"p":"Chapitres/Chapitre ","c":[["247",40],["246",38]]}});
})();
'''


def main():
    series = parse_js_literal(SERIES_JS, "SERIES")
    atelier = parse_js_literal(ATELIER_JS, "ATELIER")
    chapters = expand_chapters(parse_js_literal(CHAPTERS_JS, "CHAPTERS", "return expand("))

    data = SiteData(series=series, atelier=atelier, chapters=chapters,
                    base_url="https://exemple.test")

    checks = [
        ("2 séries lues", len(series) == 2),
        ("1 série en cours", len(data.ongoing()) == 1),
        ("1 oneshot terminé", len(data.finished()) == 1),
        ("dernier chapitre = 247", data.last_chapter("Tougen Anki") == "247"),
        ("atelier : 1 chapitre", len(data.workshop()) == 1),
        ("étape = Q-check", data.workshop()[0]["step_label"] == "Q-check"),
        ("jauge 5/6", data.workshop()[0]["progress"] == "5/6"),
        ("accent lu", data.accent(data.get_series("Tougen Anki")) == 0xE0245E),
        ("recherche insensible aux accents", data.get_series("tougen anki") is not None),
        ("planning : dimanche", any(
            d == "Dimanche" and items for d, items in data.weekly())),
    ]

    failed = [name for name, ok in checks if not ok]
    for name, ok in checks:
        print(("  [OK]  " if ok else "  [KO]  ") + name)
    print(f"\n{len(checks) - len(failed)}/{len(checks)} tests passés")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
