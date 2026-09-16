"""Phase 4最小原型：验证问题一的物理约束与MILP/LP角色。"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from common_milp import solve_deterministic_dispatch
from data_loader import ROOT, load_q1


def summarize(result) -> dict:
    simultaneous = np.sum((result.charge > 1e-7) & (result.discharge > 1e-7))
    return {
        "objective_yuan": result.objective,
        "grid_kwh": float(result.grid.sum()),
        "charge_kwh": float(result.charge.sum()),
        "discharge_kwh": float(result.discharge.sum()),
        "curtailment_kwh": float(result.curtailment.sum()),
        "soc_start_kwh": float(result.soc[0]),
        "soc_end_kwh": float(result.soc[-1]),
        "soc_min_kwh": float(result.soc.min()),
        "soc_max_kwh": float(result.soc.max()),
        "simultaneous_intervals": int(simultaneous),
        "max_balance_residual_kwh": result.max_balance_residual,
        "max_soc_residual_kwh": result.max_soc_residual,
        "solve_seconds": result.solve_seconds,
        "success": result.success,
        "solver_message": result.message,
    }


def main() -> None:
    data = load_q1()
    kwargs = dict(
        load_kwh=data["load_kwh"],
        pv_kwh=data["pv_kwh"],
        price=data["price"],
        initial_soc=6000.0,
        terminal_soc=6000.0,
        allow_emergency=False,
    )
    milp_result = solve_deterministic_dispatch(**kwargs, binary_mode=True)
    lp_result = solve_deterministic_dispatch(**kwargs, binary_mode=False)
    report = {
        "prototype": "Q1_144_interval_energy_balance",
        "time_step_hours": 1.0 / 6.0,
        "milp": summarize(milp_result),
        "lp_relaxation": summarize(lp_result),
        "lp_lower_bound_gap_yuan": milp_result.objective - lp_result.objective,
        "acceptance": {
            "milp_feasible": bool(milp_result.success),
            "balance_residual_le_1e-6": bool(
                milp_result.max_balance_residual <= 1e-6
            ),
            "soc_residual_le_1e-6": bool(milp_result.max_soc_residual <= 1e-6),
            "soc_within_bounds": bool(
                milp_result.soc.min() >= 1200 - 1e-6
                and milp_result.soc.max() <= 10800 + 1e-6
            ),
            "terminal_soc_equal": bool(
                abs(milp_result.soc[-1] - 6000.0) <= 1e-6
            ),
            "no_simultaneous_charge_discharge": bool(
                summarize(milp_result)["simultaneous_intervals"] == 0
            ),
            "lp_is_lower_bound": bool(
                lp_result.objective <= milp_result.objective + 1e-6
            ),
        },
    }
    report["passed"] = all(report["acceptance"].values())
    output = ROOT / "state" / "agent_outputs" / "prototype_review.json"
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
