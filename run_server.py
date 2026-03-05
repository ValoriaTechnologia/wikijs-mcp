#!/usr/bin/env python3
"""Script d'entrée pour lancer le serveur MCP Oversecur."""

import sys
from pathlib import Path

# Ajouter le répertoire parent au path pour les imports
sys.path.insert(0, str(Path(__file__).parent))

from src.server import main

if __name__ == "__main__":
    # main() est maintenant synchrone car FastMCP.run() gère sa propre boucle d'événements
    main()

