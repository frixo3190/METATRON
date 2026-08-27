#!/usr/bin/env python3
"""
METATRON - metatron.py
Lanceur principal.
  - par défaut : interface Textual (TUI moderne)
  - --legacy   : ancienne interface ligne par ligne (metatron_legacy.py)

Usage : ./venv/bin/python metatron.py [--legacy]
"""

import os
import sys


def _relaunch_in_venv() -> None:
    """Relance le script avec l'interpréteur du venv si nécessaire."""
    venv_python = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "venv", "bin", "python"
    )
    if not os.path.isfile(venv_python):
        return
    if sys.prefix != sys.base_prefix:
        return  # déjà dans un environnement virtuel
    print("\033[96m[*] Environnement virtuel détecté — relance avec :\033[0m")
    print(f"\033[96m    {venv_python} metatron.py\033[0m\n")
    os.execv(venv_python, [venv_python] + sys.argv)


def _run_legacy() -> None:
    from metatron_legacy import main as legacy_main
    legacy_main()


def main() -> None:
    _relaunch_in_venv()

    if "--legacy" in sys.argv:
        _run_legacy()
        return

    # Vérification de l'installation (sortie terminal, avant la prise de
    # contrôle de l'écran par Textual).
    from metatron_legacy import preflight_check
    if not preflight_check():
        sys.exit(1)

    try:
        from tui.app import MetatronApp
    except ImportError as e:
        print("\033[91m  [✗] Textual n'est pas installé.\033[0m")
        print(f"\033[91m      {e}\033[0m")
        print("\033[93m  [!] Basculer sur l'interface legacy...\033[0m\n")
        _run_legacy()
        return

    MetatronApp().run()


if __name__ == "__main__":
    main()
