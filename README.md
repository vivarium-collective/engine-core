# engine-core

A tiny shared base so the ecosystem's simulator wrappers implement the "wrap a real
engine as a process-bigraph Process" shape **once** instead of re-rolling it per repo.
Framework-general: it depends only on process-bigraph, not on viva or any engine.

## `EngineProcess`

Every engine wrapper repeats the same shape: declare ports from config, build the engine
once, then each step gather the input values and run the engine. `EngineProcess` captures
that; a wrapper implements just **two hooks**:

```python
from engine_core import EngineProcess

class PhreeqcProcess(EngineProcess):
    config_schema = {**EngineProcess.config_schema,
                     "recipe": {"_type": "tree", "_default": {}},
                     "database": {"_type": "string", "_default": "phreeqc.dat"}}

    def build_engine(self, config):          # built once
        return PhreeqcEngine(config["database"])

    def run(self, values, interval):          # each step: {port: value} -> {port: value}
        return speciate(self._engine, self.config["recipe"], values)
```

The base supplies `inputs()`/`outputs()` (from `config["inputs"]`/`config["outputs"]`) and
`update()` (gather declared input values from state → `run`). A wrapper whose engine builds
lazily returns `None` from `build_engine` and builds on first `run`. Genuinely specialized
processes (fixed ports, domain pre/post physics) keep their own shape and reuse the engine's
primitives — the base is for the common config-driven case, not a straitjacket.

## Reproducibility (opt-in, decoupled)

`capture_run_env(packages)` records python + platform + each named package's version and git
sha, framework-free, so a run can say which simulator build produced it. It is a **separate
helper**, deliberately NOT baked into `EngineProcess` — a wrapper that wants it calls it
itself, keeping the base a clean process pattern:

```python
from engine_core import capture_run_env
env = capture_run_env(["viva-phreeqc"])   # {"python":..., "platform":..., "packages": {...}}
```

## Scope

`EngineProcess` is framework-general and is a candidate to graduate into process-bigraph itself
(as a `process_bigraph.engine` submodule) once its hook API has settled across several adopters.
`capture_run_env` is a provenance concern and stays out of the core framework.
