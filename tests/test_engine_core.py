"""EngineProcess base: ports from config, gather->run lifecycle, env capture."""
from process_bigraph import allocate_core
from viva_engine_core import EngineProcess, capture_run_env

_CORE = allocate_core()


class _DoublerProcess(EngineProcess):
    """Toy engine: each step returns 2x each named input on the matching output port."""
    def build_engine(self, config):
        return {"gain": 2.0}

    def run(self, values, interval):
        return {k: self._engine["gain"] * float(v) for k, v in values.items()}


def _mk(**config):
    return _DoublerProcess(config=config, core=_CORE)


def test_ports_come_from_config():
    p = _mk(inputs={"a": {"_type": "float"}}, outputs={"a": {"_type": "float"}})
    assert p.inputs() == {"a": {"_type": "float"}}
    assert p.outputs() == {"a": {"_type": "float"}}


def test_update_gathers_then_runs():
    p = _mk(inputs={"a": {"_type": "float"}, "b": {"_type": "float"}},
            outputs={"a": {"_type": "float"}, "b": {"_type": "float"}})
    # only declared input ports present in state are passed through
    out = p.update({"a": 3.0, "b": 5.0, "ignored": 9.0}, 1.0)
    assert out == {"a": 6.0, "b": 10.0}


def test_engine_built_once():
    p = _mk(inputs={}, outputs={})
    assert p._engine == {"gain": 2.0}


def test_env_capture_opt_in():
    assert _mk(inputs={}, outputs={}).run_env() is None
    p = _mk(inputs={}, outputs={}, capture_env=True, env_packages=["process-bigraph"])
    env = p.run_env()
    assert env and "python" in env and "process-bigraph" in env["packages"]


def test_capture_run_env_missing_package_is_blank_not_error():
    env = capture_run_env(["definitely-not-installed-xyz"])
    assert env["packages"]["definitely-not-installed-xyz"]["version"] == ""
