"""Public pipeline classes, imported only when requested."""
from importlib import import_module

_EXPORTS = {"ContentGenerator": "generate_content", "VoiceGenerator": "generate_voice",
            "QualityCheckPipeline": "quality_check", "ContentPublisher": "publish_content"}
__all__ = list(_EXPORTS)


def __getattr__(name):
    if name not in _EXPORTS:
        raise AttributeError(name)
    value = getattr(import_module(f".{_EXPORTS[name]}", __name__), name)
    globals()[name] = value
    return value
