"""
Registre des serveurs — « sur quel serveur travaille-t-on ? »
==============================================================
Le bot refuse de démarrer sans savoir où il agit. Trois façons de le lui
dire, par ordre de priorité :

  1. `--server prod` en ligne de commande
  2. `LANOR_SERVER=prod` dans l'environnement (VPS, systemd, Docker)
  3. la question posée dans le terminal

Le serveur choisi fixe le GUILD_ID, et le bot **ignore tout événement**
venant d'ailleurs : aucun risque de mélanger prod et bac à sable.
"""
import os
import sys

SERVERS = {
    "prod": {
        "key": "prod",
        "id": 1325767167203082341,
        "name": "LanorTrad",
        "label": "Serveur officiel — informatif (sorties · contact · recrutement)",
        "emoji": "🩸",
        "keep_series_roles": True,   # les rôles de séries existent déjà
    },
    "test": {
        "key": "test",
        "id": 1520497372474380428,
        "name": "LanorTrad — Bac à sable",
        "label": "Serveur de test — mêmes commandes, pour essayer sans risque",
        "emoji": "🧪",
        "keep_series_roles": False,  # serveur vierge : on crée les rôles
    },
}

ALIASES = {
    "1": "prod", "2": "test",
    "lanortrad": "prod", "officiel": "prod", "production": "prod",
    "sandbox": "test", "bac": "test", "essai": "test", "dev": "test",
}

_selected = None


def by_id(guild_id):
    for server in SERVERS.values():
        if server["id"] == int(guild_id or 0):
            return server
    return None


def _normalize(value):
    if not value:
        return None
    value = value.strip().lower()
    if value in SERVERS:
        return SERVERS[value]
    if value in ALIASES:
        return SERVERS[ALIASES[value]]
    if value.isdigit():
        return by_id(int(value))
    return None


def _from_argv():
    for i, arg in enumerate(sys.argv):
        if arg == "--server" and i + 1 < len(sys.argv):
            return _normalize(sys.argv[i + 1]), sys.argv[i + 1]
        if arg.startswith("--server="):
            raw = arg.split("=", 1)[1]
            return _normalize(raw), raw
    return None, None


def _ask():
    print()
    print("=" * 62)
    print("   SUR QUEL SERVEUR DISCORD TRAVAILLE-T-ON ?")
    print("=" * 62)
    for i, key in enumerate(SERVERS, start=1):
        s = SERVERS[key]
        print(f"  [{i}] {s['emoji']}  {s['name']}")
        print(f"      {s['label']}")
        print(f"      id {s['id']}")
    print("  [q] annuler")
    print("-" * 62)
    while True:
        choice = input("Ton choix : ").strip().lower()
        if choice in ("q", "quit", "annuler", ""):
            print("Annulé.")
            sys.exit(0)
        server = _normalize(choice)
        if server:
            return server
        print("  ❌ Tape 1, 2, une clé (prod / test) ou un ID.")


def select():
    """Retourne le serveur choisi (une seule fois par processus)."""
    global _selected
    if _selected is not None:
        return _selected

    server, raw = _from_argv()
    if raw and server is None:
        print(f"❌ Serveur inconnu : « {raw} ». Valeurs : {', '.join(SERVERS)}")
        sys.exit(1)

    if server is None:
        raw_env = os.environ.get("LANOR_SERVER")
        if raw_env:
            server = _normalize(raw_env)
            if server is None:
                print(f"❌ LANOR_SERVER={raw_env} : serveur inconnu.")
                sys.exit(1)

    if server is None:
        if sys.stdin is not None and sys.stdin.isatty():
            server = _ask()
        else:
            print("❌ Aucun serveur indiqué et terminal non interactif.")
            print("   Utilise --server prod  ou  LANOR_SERVER=prod")
            sys.exit(1)

    _selected = server
    return server


def banner(server):
    line = "═" * 62
    return (f"\n{line}\n"
            f"  {server['emoji']}  {server['name']}  ·  id {server['id']}\n"
            f"     {server['label']}\n"
            f"{line}")
