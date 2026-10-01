import os
import sys

# src-layout: make the package importable without an editable install.
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

import pytest


@pytest.fixture(autouse=True)
def _isolated_house_settings(monkeypatch, tmp_path_factory):
    """No test reads or writes the real user's house-voice settings or voice
    store; each starts from the shipped defaults."""
    monkeypatch.setenv("ARTICULATE_CONFIG_DIR", str(tmp_path_factory.mktemp("house-config")))
    for name in ("ARTICULATE_HOUSE_VOICE", "ARTICULATE_HOUSE_LENGTH", "ARTICULATE_HOUSE_HEADINGS",
                 "ARTICULATE_HOUSE_LISTS", "ARTICULATE_HOUSE_FIRST_PERSON",
                 "ARTICULATE_HOUSE_LIMITS", "ARTICULATE_HOUSE_END_LINE"):
        monkeypatch.delenv(name, raising=False)
