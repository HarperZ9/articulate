import os
import sys

# src-layout: make the package importable without an editable install.
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))
