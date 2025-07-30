from .base import DetectionStrategy
from .dom import DOMStrategy
from .heuristic import HeuristicStrategy
from .ocr import OCRStrategy
from .ml import MLStrategy


def get_default_strategies():
    """Get available detection strategies"""
    return {
        "dom": DOMStrategy,
        "heuristic": HeuristicStrategy,
        "ocr": OCRStrategy,
        "ml": MLStrategy,
    }


__all__ = [
    "DetectionStrategy",
    "DOMStrategy",
    "HeuristicStrategy",
    "OCRStrategy",
    "MLStrategy",
    "get_default_strategies",
]