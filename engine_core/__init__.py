"""engine-core: the shared base for config-driven simulator wrappers.

`EngineProcess` is the framework-general base; `capture_run_env` is a separate,
opt-in reproducibility helper (not coupled to the base).
"""
from engine_core.process import EngineProcess
from engine_core.run_env import capture_run_env

__all__ = ["EngineProcess", "capture_run_env"]
