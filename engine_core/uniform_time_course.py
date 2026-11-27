"""Category contract for SBML/ODE simulators: the one-shot *uniform time course*.

Across the ecosystem, every ODE/SBML backend wrapper (tellurium, copasi, amici,
pysces, simbio, opencor, julia-diffeqs, ...) grew a ``<Engine>UTCStep`` that does the
same job — load a model, integrate ``t`` from 0 to a horizon at ``n_points`` evenly
spaced samples, and emit the species trajectory — yet each re-declared the ports and
re-packed the result by hand, and the shapes silently drifted (three different result
payloads, two result type names). :class:`UniformTimeCourseStep` fixes the contract in
one place so a backend implements only the engine call.

A backend subclass implements a single hook::

    class PyscesUTCStep(UniformTimeCourseStep):
        config_schema = {**UniformTimeCourseStep.config_schema, "quiet": {"_type": "boolean", "_default": True}}
        def simulate(self, model_source, time, n_points):
            model = load(model_source)
            model.doSim(end=time, points=n_points)
            times, columns, values = ...        # columns = species ids
            return times, columns, values

The base supplies ``inputs()``/``outputs()`` and ``update()`` (validate -> ``simulate``
-> :func:`pack_utc`), emitting the canonical trajectory

    {"result": {"time": [float, ...],
                "columns": [str, ...],              # one per species
                "values": [[float, ...], ...]}}     # one row per time point

:class:`SteadyStateStep` is the matching one-shot steady-state contract, emitting

    {"result": {"kind": "steady_state", "time": None, "observables": {id: float}}}

Both are pure process-bigraph ``Step`` s — no dependency on any engine. The ``result``
port is typed ``tree`` (the built-in bigraph type the conforming backends already use);
unifying the alternative ``numeric_result`` type name is a separate, later step.
"""
from __future__ import annotations

from typing import Any, Sequence

from process_bigraph import Step


def validate_n_points(n: Any) -> int:
    """Coerce ``n_points`` to an int and require at least the two endpoints."""
    try:
        n = int(n)
    except (TypeError, ValueError):
        raise ValueError(f"n_points must be an integer >= 2, got {n!r}")
    if n < 2:
        raise ValueError(f"n_points must be >= 2, got {n}")
    return n


def pack_utc(
    times: Sequence[Any],
    columns: Sequence[Any],
    values: Sequence[Sequence[Any]],
) -> dict[str, Any]:
    """Pack a trajectory into the canonical UTC ``result`` payload.

    ``times`` is one value per time point, ``columns`` one id per species, and
    ``values`` a row per time point with one float per column. Everything is coerced
    (``float``/``str``) and the row shape is checked so every backend emits byte-
    identical structure regardless of the array type its engine returned.
    """
    cols = [str(c) for c in columns]
    width = len(cols)
    out_times = [float(t) for t in times]
    out_values: list[list[float]] = []
    for row in values:
        row = list(row)
        if len(row) != width:
            raise ValueError(
                f"pack_utc: row has {len(row)} values but there are {width} columns"
            )
        out_values.append([float(v) for v in row])
    if len(out_values) != len(out_times):
        raise ValueError(
            f"pack_utc: {len(out_values)} value rows but {len(out_times)} time points"
        )
    return {"time": out_times, "columns": cols, "values": out_values}


class UniformTimeCourseStep(Step):
    """One-shot uniform-time-course contract for SBML/ODE backends.

    Fixed ports: runtime inputs ``model_source`` (path/string the backend loads),
    ``time`` (horizon, t runs 0 -> time) and ``n_points`` (evenly spaced samples, >= 2);
    output ``result`` carrying the canonical ``{time, columns, values}`` trajectory.
    Subclasses implement :meth:`simulate` only.
    """

    config_schema: dict[str, Any] = {}

    def inputs(self) -> dict[str, str]:
        return {"model_source": "string", "time": "float", "n_points": "integer"}

    def outputs(self) -> dict[str, str]:
        return {"result": "tree"}

    def update(self, state: dict[str, Any]) -> dict[str, Any]:
        n_points = validate_n_points(state["n_points"])
        horizon = float(state["time"])
        times, columns, values = self.simulate(state["model_source"], horizon, n_points)
        return {"result": pack_utc(times, columns, values)}

    # --- hook a backend implements ----------------------------------------
    def simulate(
        self, model_source: str, time: float, n_points: int
    ) -> tuple[Sequence[Any], Sequence[Any], Sequence[Sequence[Any]]]:
        """Integrate the model and return ``(times, columns, values)``.

        ``columns`` are the species ids; ``values`` is one row per time point with a
        value per column. The base validates ``n_points`` and packs the result.
        """
        raise NotImplementedError(
            "UniformTimeCourseStep subclasses must implement simulate()"
        )


class SteadyStateStep(Step):
    """One-shot steady-state contract for SBML/ODE backends.

    Runtime input ``model_source``; output ``result`` carrying
    ``{"kind": "steady_state", "time": None, "observables": {id: value}}``. Subclasses
    implement :meth:`steady_state` only.
    """

    config_schema: dict[str, Any] = {}

    def inputs(self) -> dict[str, str]:
        return {"model_source": "string"}

    def outputs(self) -> dict[str, str]:
        return {"result": "tree"}

    def update(self, state: dict[str, Any]) -> dict[str, Any]:
        observables = self.steady_state(state["model_source"])
        return {
            "result": {
                "kind": "steady_state",
                "time": None,
                "observables": {str(k): float(v) for k, v in observables.items()},
            }
        }

    # --- hook a backend implements ----------------------------------------
    def steady_state(self, model_source: str) -> dict[str, Any]:
        """Solve for the steady state and return ``{species_id: value}``."""
        raise NotImplementedError(
            "SteadyStateStep subclasses must implement steady_state()"
        )
