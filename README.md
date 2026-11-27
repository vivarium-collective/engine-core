# viva-engine-core

The shared base every config-driven simulator wrapper in the ecosystem reuses, so a
simulator's "wrap a real engine as a process-bigraph Process" shape is implemented
**once** instead of re-rolled per repo.

## `EngineProcess`

Every engine wrapper repeats the same shape: declare ports from config, build the
engine once, then each step gather the input values and run the engine to produce the
outputs. `EngineProcess` captures that; a wrapper implements two hooks:

```python
from viva_engine_core import EngineProcess

class PhreeqcProcess(EngineProcess):
    config_schema = {**EngineProcess.config_schema,
                     "recipe": {"_type": "tree", "_default": {}},
                     "database": {"_type": "string", "_default": "phreeqc.dat"}}

    def build_engine(self, config):          # built once
        return PhreeqcEngine(config["database"])

    def run(self, values, interval):          # each step: {port: value} -> {port: value}
        return speciate(self._engine, self.config["recipe"], values)
```

The base supplies `inputs()` / `outputs()` (from `config["inputs"]` / `config["outputs"]`),
`update()` (gather input values from state → `run`), and optional reproducibility capture.
A wrapper whose engine builds lazily returns `None` from `build_engine` and builds on the
first `run`. Genuinely specialized processes (fixed ports, domain pre/post physics) keep
their own shape and reuse the engine's primitives instead — don't force them onto the base.

## Run-environment capture

`capture_run_env(packages)` records python + platform + each named package's version and
git sha, framework-free, so a run can say exactly which simulator build produced it. Set
`config["capture_env"] = True` and `config["env_packages"] = ["viva-phreeqc", ...]`;
read it back via `process.run_env()`.

## Why

An ecosystem audit found simulator wrappers each hand-roll this shape; a shared base makes
new wraps uniform, gives every run reproducibility capture for free, and lets consumers
rely on one contract. See the ecosystem reuse program.
