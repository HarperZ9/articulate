"""Articulate: a local writing-quality and AI-tell detector, with an optional editor.

The detector runs standard-library-only with no network call. The optional
editor layer (judge / fix / polish) sends the text to a hosted model through the
claude CLI. The register-adaptive
profile system decides which findings gate.
"""
from . import genres, profiles
from .detector import (GATE_TIERS, analyze_blocks, binary_reason, check_text,
                       scan_lines, segment_blocks)

__version__ = "0.4.2"
__all__ = ["check_text", "scan_lines", "analyze_blocks", "segment_blocks",
           "binary_reason", "profiles", "genres", "GATE_TIERS", "__version__"]
