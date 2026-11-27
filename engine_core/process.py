"""EngineProcess: the shared base for config-driven simulator wrappers.

Every engine wrapper repeats the same shape — declare ports from config, build the
engine once, then each step gather the input values and run the engine to produce the
outputs. `EngineProcess` captures exactly that; a wrapper implements two hooks:

    class PhreeqcProcess(EngineProcess):
        config_schema = {**EngineProcess.config_schema, "recipe": {"_type": "tree", "_default": {}}}
        def build_engine(self, config):      # once
            return PhreeqcEngine(config["database"])
        def run(self, values, interval):      # each step: {port: value} -> {port: value}
            return speciate(self._engine, self.config["recipe"], values)

The base provides inputs()/outputs() from config and update() (gather -> run). It is
pure process-bigraph — no dependency on provenance, the framework, or any engine. A
wrapper whose engine needs lazy construction returns None from build_engine and builds
on the first run(). Genuinely specialized processes (fixed ports, domain pre/post
physics) keep their own shape and reuse the engine's primitives instead.

Reproducibility is a separate, opt-in concern: a wrapper that wants it calls
`capture_run_env(...)` (see engine_core.run_env) itself — it is deliberately NOT baked
into this base, so the base stays a clean, framework-level process pattern.
"""
from __future__ import annotations

from process_bigraph import Process


class EngineProcess(Process):
    config_schema = {
        # Port specs: {port_name: <process-bigraph type>}. The base reads these so a
        # wrapper does not reimplement inputs()/outputs().
        "inputs": {"_type": "tree", "_default": {}},
        "outputs": {"_type": "tree", "_default": {}},
    }

    def __init__(self, config=None, core=None):
        super().__init__(config=config, core=core)
        self._engine = self.build_engine(self.config)

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

    # --- hooks a wrapper implements ---------------------------------------
    def build_engine(self, config):
        """Build the engine once. Return the engine object (stored as self._engine), or
        None to build lazily in run()."""
        raise NotImplementedError("EngineProcess subclasses must implement build_engine()")

    def run(self, values, interval):
        """Advance the engine one interval. `values` is {input_port: value}; return
        {output_port: value}."""
        raise NotImplementedError("EngineProcess subclasses must implement run()")
