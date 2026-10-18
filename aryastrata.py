#!/usr/bin/env python3
"""AryaStrata command line: chat, list installed models, and benchmark.

Uses the inherited implementation; polystrata.py remains an import-compatible entry point.
"""
import sys
from polystrata import main

if __name__ == "__main__":
    sys.exit(main())
