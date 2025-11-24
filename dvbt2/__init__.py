"""
DVBT2 — DVB-T2 Field Strength Calculator

This package implements the complete field-strength and minimum-median equivalent
field-strength calculation chain defined in:

- ITU-R BT.2033-2
- ITU-R BT.2036-5
- GE06 Final Acts (RRC-06)

It provides the `DVBT2` class as the public interface, along with
a CLI defined in `dvbt2_cli.py`.
"""

from .dvbt2 import DVBT2

__all__ = ["DVBT2"]

__version__ = "0.1.0"
