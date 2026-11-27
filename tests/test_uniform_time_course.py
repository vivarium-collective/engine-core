"""UniformTimeCourseStep / SteadyStateStep contracts + packing helpers."""
import pytest
from process_bigraph import allocate_core

from engine_core import (
    SteadyStateStep,
    UniformTimeCourseStep,
    pack_utc,
    validate_n_points,
)

_CORE = allocate_core()


class _LinearUTC(UniformTimeCourseStep):
    """Toy backend: two species, A = t, B = 2t, sampled at n_points over [0, time]."""

    def simulate(self, model_source, time, n_points):
        step = time / (n_points - 1)
        times = [i * step for i in range(n_points)]
        values = [[t, 2 * t] for t in times]
        return times, ["A", "B"], values


class _ConstSteady(SteadyStateStep):
    def steady_state(self, model_source):
        return {"A": 1, "B": 2}  # ints on purpose -> coerced to float


def test_utc_ports_are_fixed():
    p = _LinearUTC(config={}, core=_CORE)
    assert p.inputs() == {"model_source": "string", "time": "float", "n_points": "integer"}
    assert p.outputs() == {"result": "tree"}


def test_utc_update_packs_canonical_result():
    p = _LinearUTC(config={}, core=_CORE)
    out = p.update({"model_source": "x", "time": 10.0, "n_points": 3})
    assert out == {
        "result": {
            "time": [0.0, 5.0, 10.0],
            "columns": ["A", "B"],
            "values": [[0.0, 0.0], [5.0, 10.0], [10.0, 20.0]],
        }
    }


def test_utc_validates_n_points():
    p = _LinearUTC(config={}, core=_CORE)
    with pytest.raises(ValueError):
        p.update({"model_source": "x", "time": 1.0, "n_points": 1})


def test_steady_state_result_shape_and_coercion():
    p = _ConstSteady(config={}, core=_CORE)
    out = p.update({"model_source": "x"})
    assert out == {
        "result": {"kind": "steady_state", "time": None, "observables": {"A": 1.0, "B": 2.0}}
    }
    assert isinstance(out["result"]["observables"]["A"], float)


def test_abstract_hooks_raise():
    with pytest.raises(NotImplementedError):
        UniformTimeCourseStep(config={}, core=_CORE).simulate("m", 1.0, 2)
    with pytest.raises(NotImplementedError):
        SteadyStateStep(config={}, core=_CORE).steady_state("m")


def test_validate_n_points():
    assert validate_n_points("5") == 5
    for bad in (1, 0, -3, "x", None):
        with pytest.raises(ValueError):
            validate_n_points(bad)


def test_pack_utc_coerces_and_checks_shape():
    r = pack_utc((0, 1), ["A"], [[0], [3]])
    assert r == {"time": [0.0, 1.0], "columns": ["A"], "values": [[0.0], [3.0]]}
    with pytest.raises(ValueError):  # row width != n columns
        pack_utc([0.0], ["A", "B"], [[1.0]])
    with pytest.raises(ValueError):  # rows != time points
        pack_utc([0.0, 1.0], ["A"], [[1.0]])
