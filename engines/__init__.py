"""engines – path registry for sibling simulation repositories."""

from engines.engine_paths import (
    ENGINE_REGISTRY,
    register_engine_paths,
    get_engine_path,
)

__all__ = [
    "ENGINE_REGISTRY",
    "register_engine_paths",
    "get_engine_path",
]
