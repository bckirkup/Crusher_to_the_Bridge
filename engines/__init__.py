"""engines – path registry for sibling simulation repositories."""

from engines.engine_paths import (
    ENGINE_REGISTRY,
    get_engine_path,
    register_engine_paths,
)

__all__ = [
    "ENGINE_REGISTRY",
    "register_engine_paths",
    "get_engine_path",
]
