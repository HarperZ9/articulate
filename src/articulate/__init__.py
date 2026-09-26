"""Articulate: local prose checks. Named writing patterns, where they occur, and
what each costs a reader, with an optional editor.

The checks run standard-library-only with no network call. The optional editor
layer (judge / fix / polish) sends the text to a hosted model through the claude
CLI. Profiles decide which findings block. No output shows who or what wrote a
text.
"""
from . import genres, profiles
from .detector import (GATE_TIERS, analyze_blocks, binary_reason, check_text,
                       scan_lines, segment_blocks)

__version__ = "0.4.2"
__all__ = ["check_text", "scan_lines", "analyze_blocks", "segment_blocks",
           "binary_reason", "profiles", "genres", "GATE_TIERS", "__version__"]
