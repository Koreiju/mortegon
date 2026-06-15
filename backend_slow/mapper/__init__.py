"""
mapper — SLAM-inspired DOM lifecycle manager.

Orchestrates the scan → register → distill → layout → stream → release pipeline.
"""

from .mapper import DomMapper

__all__ = ['DomMapper']
