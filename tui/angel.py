"""Bannière METATRON en ASCII art (animée) pour l'écran d'accueil.

Reprend le logo « METATRON » en blocs (issu du bannière legacy),
avec une flamme animée dessous (Metatron = l'archange à l'épée de feu).
"""

# Logo METATRON en blocs (sans l'indentation d'origine)
METATRON_ART = [
    "███╗   ███╗███████╗████████╗ █████╗ ████████╗██████╗  ██████╗ ███╗   ██╗",
    "████╗ ████║██╔════╝╚══██╔══╝██╔══██╗╚══██╔══╝██╔══██╗██╔═══██╗████╗  ██║",
    "██╔████╔██║█████╗     ██║   ███████║   ██║   ██████╔╝██║   ██║██╔██╗ ██║",
    "██║╚██╔╝██║██╔══╝     ██║   ██╔══██║   ██║   ██╔══██╗██║   ██║██║╚██╗██║",
    "██║ ╚═╝ ██║███████╗   ██║   ██║  ██║   ██║   ██║  ██║╚██████╔╝██║ ╚████║",
    "╚═╝     ╚═╝╚══════╝   ╚═╝   ╚═╝  ╚═╝   ╚═╝   ╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═══╝",
]

# Flamme animée (épée de feu) sous le logo
FLAMES = [
    "        ~   ~   ~   ~   ~   ~   ~   ~   ~        ",
    "        ~*~ ~ ~*~ ~ ~ ~ ~*~ ~ ~ ~ ~*~ ~        ",
    "        *~*~ ~*~*~ ~*~ ~*~*~ ~ ~*~*~ ~        ",
    "        ~*~*~*~*~*~*~*~*~*~*~*~*~*~*~*        ",
]


def _frame(index: int) -> str:
    flame = FLAMES[index % len(FLAMES)]
    return "\n".join(METATRON_ART) + "\n" + flame


def angel_frame(index: int) -> str:
    """Retourne la bannière METATRON (frame animée)."""
    return _frame(index)
