"""
Element detection strategies
"""

from .dom import DOMStrategy
from .heuristic import HeuristicStrategy

# Import optional strategies if available
try:
    from .ocr import OCRStrategy

    HAS_OCR = True
except ImportError:
    HAS_OCR = False
    OCRStrategy = None

try:
    from .ml import MLStrategy

    HAS_ML = True
except ImportError:
    HAS_ML = False
    MLStrategy = None


def get_default_strategies():
    """Get available detection strategies"""
    strategies = {
        'dom': DOMStrategy,
        'heuristic': HeuristicStrategy,
    }

    if HAS_OCR and OCRStrategy:
        strategies['ocr'] = OCRStrategy

    if HAS_ML and MLStrategy:
        strategies['ml'] = MLStrategy

    return strategies


__all__ = [
    'DOMStrategy',
    'HeuristicStrategy',
    'get_default_strategies',
]

if HAS_OCR:
    __all__.append('OCRStrategy')

if HAS_ML:
    __all__.append('MLStrategy')