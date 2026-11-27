"""EngineProcess: the shared base for config-driven simulator wrappers.

Every engine wrapper in the ecosystem repeats the same shape — declare ports from
config, build the engine once, then each step gather the input values and run the
engine to produce the outputs. This base captures that shape (and optional run-env
capture) so a wrapper only implements two hooks:

    class PhreeqcProcess(EngineProcess):
        config_schema = {**EngineProcess.config_schema, "recipe": {"_type": "tree", "_default": {}}}
        def build_engine(self, config):      # once
            return PhreeqcEngine(config["database"])
        def run(self, values, interval):      # each step: {port: value} -> {port: value}
            return speciate(self._engine, self.config["recipe"], values)

The base provides inputs()/outputs() from config, update() (gather -> run), and
capture_env. A wrapper whose engine needs lazy construction can override build_engine
to return None and build on first run(). Genuinely specialized processes (fixed ports,
domain pre/post) keep their own shape and reuse the engine primitives instead.
"""
from __future__ import annotations

from process_bigraph import Process

from .run_env import capture_run_env


class EngineProcess(Process):
    config_schema = {
        # Port specs: {port_name: <process-bigraph type>}. The base reads these so a
        # wrapper does not reimplement inputs()/outputs().
        "inputs": {"_type": "tree", "_default": {}},
        "outputs": {"_type": "tree", "_default": {}},
        # Reproducibility: names of the engine packages to stamp into run_env().
        "env_packages": {"_type": "tree", "_default": []},
        "capture_env": {"_type": "boolean", "_default": False},
    }

    def __init__(self, config=None, core=None):
        super().__init__(config=config, core=core)
        self._engine = self.build_engine(self.config)
        self._run_env = (
            capture_run_env(self.config.get("env_packages") or ())
            if self.config.get("capture_env")
            else None
        )

    # --- ports from config -------------------------------------------------
    def inputs(self):
        return dict(self.config.get("inputs") or {})

    def outputs(self):
        return dict(self.config.get("outputs") or {})

    # --- lifecycle ---------------------------------------------------------
    def update(self, state, interval):
        ports = self.config.get("inputs") or {}
        values = {name: state[name] for name in ports if name in state}
        return self.run(values, interval)

    def run_env(self) -> dict | None:
        """The captured run environment (None unless config['capture_env'])."""
        return self._run_env

    # --- hooks a wrapper implements ---------------------------------------
    def build_engine(self, config):
        """Build the engine once. Return the engine object (stored as self._engine), or
        None to build lazily in run()."""
        raise NotImplementedError("EngineProcess subclasses must implement build_engine()")

    def run(self, values, interval):
        """Advance the engine one interval. `values` is {input_port: value}; return
        {output_port: value}."""
        raise NotImplementedError("EngineProcess subclasses must implement run()")
