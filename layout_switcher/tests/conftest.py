import os
import sys

# Headless CI: pynput must not try to open a display / device.
os.environ.setdefault('PYNPUT_BACKEND_KEYBOARD', 'dummy')
os.environ.setdefault('PYNPUT_BACKEND_MOUSE', 'dummy')

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from dictionaries import Lexicon


@pytest.fixture(scope='session')
def lexicon():
    """One real Lexicon for the whole session (pymorphy2 init is slow)."""
    return Lexicon()
