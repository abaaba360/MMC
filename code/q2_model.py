"""问题二：严格0时两阶段随机MILP全年滚动求解。

第一阶段：计划购电G、充电C、放电D、SOC E与互斥状态z跨情景共享。
第二阶段：每个净负荷情景只允许紧急购电R和弃电W。
输入：附件1固定电价与附件2全年实际负荷/光伏。
输出：state/agent_outputs/q2_results.json、results/q2_detail.npz。
运行：python code/q2_model.py [--days N] [--horizon-days 1|2]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter

import numpy as np
import scipy
from scipy.optimize import Bounds, LinearConstraint, milp
from scipy.sparse import lil_matrix

from causal_forecasts import (
    ForecastChoice,
    choose_scenario_count,
    forecast_from_choice,
    residual_scenarios,
    select_month_model,
)
from formal_data_loader import DATA_DIR, N_STEPS, load_q2_data, load_typical_day


ROOT = Path(__file__).resolve().parents[1]
RESULTS_DIR = ROOT / "results"
STATE_DIR = ROOT / "state" / "agent_outputs"
ETA_C = 0.9
ETA_D = 0.9
SOC_MIN = 1200.0
SOC_MAX = 10800.0
POWER_LIMIT_KWH = 5000.0 / 6.0
INITIAL_SOC = 6000.0
EMERGENCY_MULTIPLIER = 5.0


@dataclass
class StochasticDispatch:
    grid: np.ndarray
    charge: np.ndarray
    discharge: np.ndarray
    soc: np.ndarray
    mode: np.ndarray
    scenario_emergency: np.ndarray
    scenario_curtailment: np.ndarray
    objective: float
    solve_seconds: float
    success: bool
    message: str
    mip_gap: float | None
    max_balance_residual: float
    max_soc_residual: float


def solve_two_stage_day(
    scenario_net_kwh: np.ndarray,
    probabilities: np.ndarray,
    price: np.ndarray,
    initial_soc: float,
    *,
    terminal_soc: float | None = None,
    time_limit: float = 60.0,
) -> StochasticDispatch:
    """求解共享计划、仅R/W追索的两阶段随机MILP。"""

    scenarios = np.asarray(scenario_net_kwh, dtype=float)
    probs = np.asarray(probabilities, dtype=float)
    tariff = np.asarray(price, dtype=float)
    if scenarios.ndim != 2:
        raise ValueError("scenario_net_kwh必须为S×H矩阵")
    s_count, horizon = scenarios.shape
    if tariff.shape != (horizon,) or probs.shape != (s_count,):
        raise ValueError("电价、概率与情景维度不匹配")
    if np.any(probs < 0) or not np.isclose(probs.sum(), 1.0):
        raise ValueError("情景概率必须非负且和为1")
    if np.any(tariff < 0) or not np.isfinite(scenarios).all():
        raise ValueError("电价不得为负，净负荷情景必须有限")

    # g,c,d,E,z,R,W
    g0 = 0
    c0 = g0 + horizon
    d0 = c0 + horizon
    e0 = d0 + horizon
    z0 = e0 + horizon + 1
    r0 = z0 + horizon
    w0 = r0 + s_count * horizon
    nvar = w0 + s_count * horizon

    objective = np.zeros(nvar)
    objective[g0 : g0 + horizon] = tariff
    for s in range(s_count):
        lo = r0 + s * horizon
        objective[lo : lo + horizon] = probs[s] * EMERGENCY_MULTIPLIER * tariff

    lower = np.zeros(nvar)
    upper = np.full(nvar, np.inf)
    upper[c0 : c0 + horizon] = POWER_LIMIT_KWH
    upper[d0 : d0 + horizon] = POWER_LIMIT_KWH
    lower[e0 : e0 + horizon + 1] = SOC_MIN
    upper[e0 : e0 + horizon + 1] = SOC_MAX
    lower[e0] = upper[e0] = float(initial_soc)
    if terminal_soc is not None:
        lower[e0 + horizon] = upper[e0 + horizon] = float(terminal_soc)
    upper[z0 : z0 + horizon] = 1.0

    # 每个情景每时段平衡 + 共享SOC状态转移。
    aeq = lil_matrix((s_count * horizon + horizon, nvar), dtype=float)
    beq = np.zeros(s_count * horizon + horizon)
    for s in range(s_count):
        for t in range(horizon):
            row = s * horizon + t
            aeq[row, g0 + t] = 1.0
            aeq[row, c0 + t] = -1.0
            aeq[row, d0 + t] = 1.0
            aeq[row, r0 + s * horizon + t] = 1.0
            aeq[row, w0 + s * horizon + t] = -1.0
            beq[row] = scenarios[s, t]
    for t in range(horizon):
        row = s_count * horizon + t
        aeq[row, e0 + t] = -1.0
        aeq[row, e0 + t + 1] = 1.0
        aeq[row, c0 + t] = -ETA_C
        aeq[row, d0 + t] = 1.0 / ETA_D

    # 充放电互斥：C<=Mz, D<=M(1-z)。
    aub = lil_matrix((2 * horizon, nvar), dtype=float)
    bub = np.zeros(2 * horizon)
    for t in range(horizon):
        aub[t, c0 + t] = 1.0
        aub[t, z0 + t] = -POWER_LIMIT_KWH
        aub[horizon + t, d0 + t] = 1.0
        aub[horizon + t, z0 + t] = POWER_LIMIT_KWH
        bub[horizon + t] = POWER_LIMIT_KWH

    integrality = np.zeros(nvar, dtype=int)
    integrality[z0 : z0 + horizon] = 1
    started = perf_counter()
    raw = milp(
        objective,
        integrality=integrality,
        bounds=Bounds(lower, upper),
        constraints=[
            LinearConstraint(aeq.tocsr(), beq, beq),
            LinearConstraint(aub.tocsr(), -np.inf, bub),
        ],
        options={"time_limit": time_limit, "mip_rel_gap": 1e-7},
    )
    elapsed = perf_counter() - started
    if raw.x is None:
        raise RuntimeError(f"Q2两阶段MILP无可用解：{raw.message}")
    x = raw.x
    grid = x[g0 : g0 + horizon]
    charge = x[c0 : c0 + horizon]
    discharge = x[d0 : d0 + horizon]
    soc = x[e0 : e0 + horizon + 1]
    mode = x[z0 : z0 + horizon]
    emergency = x[r0 : r0 + s_count * horizon].reshape(s_count, horizon)
    curtailment = x[w0 : w0 + s_count * horizon].reshape(s_count, horizon)
    balance = (
        grid[None, :]
        - charge[None, :]
        + discharge[None, :]
        + emergency
        - curtailment
        - scenarios
    )
    soc_residual = soc[1:] - soc[:-1] - ETA_C * charge + discharge / ETA_D
    return StochasticDispatch(
        grid=grid,
        charge=charge,
        discharge=discharge,
        soc=soc,
        mode=mode,
        scenario_emergency=emergency,
        scenario_curtailment=curtailment,
        objective=float(raw.fun),
        solve_seconds=elapsed,
        success=bool(raw.success),
        message=str(raw.message),
        mip_gap=float(raw.mip_gap) if getattr(raw, "mip_gap", None) is not None else None,
        max_balance_residual=float(np.max(np.abs(balance))),
        max_soc_residual=float(np.max(np.abs(soc_residual))),
    )


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return "sha256:" + h.hexdigest()


def _jsonable_choice(choice: ForecastChoice) -> dict:
    result = asdict(choice)
    result["validation_wape"] = (
        None if not np.isfinite(choice.validation_wape) else choice.validation_wape
    )
    result["validation_mae"] = (
        None if not np.isfinite(choice.validation_mae) else choice.validation_mae
    )
    return result


def run_q2(*, days: int = 365, horizon_days: int = 2) -> dict:
    """从1月1日顺序递推，正式汇总2月1日至12月31日。"""

    if not 1 <= days <= 365 or horizon_days not in (1, 2):
        raise ValueError("days须为1..365，horizon_days须为1或2")
    typical = load_typical_day()
    data = load_q2_data()
    net = data["net_kwh"]
    load = data["load_kwh"]
    pv = data["pv_kwh"]
    dates = data["dates"]
    price_day = typical["price"]

    shape = (days, N_STEPS)
    grid = np.zeros(shape)
    charge = np.zeros(shape)
    discharge = np.zeros(shape)
    emergency = np.zeros(shape)
    curtailment = np.zeros(shape)
    point_forecast = np.zeros(shape)
    soc_start = np.zeros(days)
    soc_end = np.zeros(days)
    planned_cost = np.zeros(days)
    emergency_cost = np.zeros(days)
    solve_seconds = np.zeros(days)
    scenario_counts = np.zeros(days, dtype=int)
    max_balance_residual = 0.0
    max_soc_residual = 0.0
    simultaneous_count = 0
    current_soc = INITIAL_SOC
    current_choice = ForecastChoice("N1", {"alpha": 1.0}, float("nan"), float("nan"), 0)
    selection_log: list[dict] = []
    residual_library: list[np.ndarray] = []
    day_messages: list[str] = []
    started_all = perf_counter()

    for day in range(days):
        date = dates[day]
        month = int(str(date)[5:7])
        day_of_month = int(str(date)[8:10])
        if day >= 31 and day_of_month == 1:
            current_choice = select_month_model(net, load, pv, day, typical["net_kwh"])
            selection_log.append(
                {
                    "effective_month": f"2025-{month:02d}",
                    "training_cutoff": str(dates[day - 1]),
                    **_jsonable_choice(current_choice),
                }
            )

        # 正式规格：1月1日只使用附件1典型日作为赛前初始化先验。
        if day == 0:
            point1 = typical["net_kwh"].copy()
        else:
            point1 = forecast_from_choice(
                current_choice,
                net,
                load,
                pv,
                day,
                day,
                typical["net_kwh"],
            )
        point_forecast[day] = point1
        residuals = (
            np.vstack(residual_library)
            if residual_library
            else np.empty((0, N_STEPS), dtype=float)
        )
        count = choose_scenario_count(residuals) if len(residuals) else 1
        scenarios1, probs, selected = residual_scenarios(
            point1, residuals, scenario_count=count
        )

        use_two_days = horizon_days == 2 and day + 1 < days
        if use_two_days:
            point2 = forecast_from_choice(
                current_choice,
                net,
                load,
                pv,
                day + 1,
                day,
                typical["net_kwh"],
                lag1_override=point1,
            )
            if len(residuals):
                scenarios2 = point2[None, :] + residuals[selected]
            else:
                scenarios2 = point2[None, :]
            scenarios = np.hstack([scenarios1, scenarios2])
            tariff = np.tile(price_day, 2)
        else:
            scenarios = scenarios1
            tariff = price_day
        # 两日滚动窗末端回到当前SOC，消除截断处无代价放空；只执行首日，
        # 因而不是强迫每日首尾相等。年末单日窗采用同一条件。
        dispatch = solve_two_stage_day(
            scenarios, probs, tariff, current_soc, terminal_soc=current_soc
        )

        plan_g = dispatch.grid[:N_STEPS]
        plan_c = dispatch.charge[:N_STEPS]
        plan_d = dispatch.discharge[:N_STEPS]
        plan_soc = dispatch.soc[: N_STEPS + 1]
        actual_gap = net[day] + plan_c - plan_g - plan_d
        actual_r = np.maximum(actual_gap, 0.0)
        actual_w = np.maximum(-actual_gap, 0.0)

        soc_start[day] = current_soc
        current_soc = float(plan_soc[-1])
        soc_end[day] = current_soc
        grid[day], charge[day], discharge[day] = plan_g, plan_c, plan_d
        emergency[day], curtailment[day] = actual_r, actual_w
        planned_cost[day] = float(np.dot(price_day, plan_g))
        emergency_cost[day] = float(np.dot(EMERGENCY_MULTIPLIER * price_day, actual_r))
        solve_seconds[day] = dispatch.solve_seconds
        scenario_counts[day] = scenarios1.shape[0]
        max_balance_residual = max(max_balance_residual, dispatch.max_balance_residual)
        max_soc_residual = max(max_soc_residual, dispatch.max_soc_residual)
        simultaneous_count += int(np.sum((plan_c > 1e-7) & (plan_d > 1e-7)))
        day_messages.append(dispatch.message)

        # 当天结束后才允许实际误差进入次日残差库。
        residual_library.append(net[day] - point1)

    elapsed_all = perf_counter() - started_all
    official_start = 31 if days > 31 else days
    sl = slice(official_start, days)
    actual_total = planned_cost + emergency_cost
    forecast_error = point_forecast - net[:days]
    wape = float(
        np.sum(np.abs(forecast_error[sl])) / np.sum(np.abs(net[:days][sl]))
    ) if official_start < days else None
    mae = float(np.mean(np.abs(forecast_error[sl]))) if official_start < days else None
    rmse = float(np.sqrt(np.mean(forecast_error[sl] ** 2))) if official_start < days else None
    bias = float(np.mean(forecast_error[sl])) if official_start < days else None

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        RESULTS_DIR / "q2_detail.npz",
        dates=dates[:days],
        price=price_day,
        actual_net_kwh=net[:days],
        point_forecast_net_kwh=point_forecast,
        planned_grid_kwh=grid,
        planned_charge_kwh=charge,
        planned_discharge_kwh=discharge,
        actual_emergency_kwh=emergency,
        actual_curtailment_kwh=curtailment,
        soc_start_kwh=soc_start,
        soc_end_kwh=soc_end,
        planned_cost_yuan=planned_cost,
        emergency_cost_yuan=emergency_cost,
        actual_total_cost_yuan=actual_total,
        scenario_count=scenario_counts,
        official_start_index=np.array([official_start]),
    )

    official_days = max(0, days - official_start)
    output = {
        "sub_question": "Q2",
        "status": "success" if (
            max_balance_residual <= 1e-5
            and max_soc_residual <= 1e-5
            and simultaneous_count == 0
        ) else "failed",
        "model": "严格0时两阶段随机MILP（计划G/C/D/E/z共享，情景仅R/W）",
        "run_timestamp": datetime.now(timezone.utc).astimezone().isoformat(),
        "input_data_hash": _sha256(DATA_DIR / "附件2.xlsx"),
        "information_boundary": {
            "forecast_origin": "每天00:00",
            "history_rule": "日期d的预测、参数和残差样本仅使用j<d的已完成数据",
            "january_warm_start": "2025-01-01使用附件1典型日先验；其后逐日因果更新SOC与残差库",
            "first_stage_shared": ["G", "C", "D", "E", "z"],
            "scenario_recourse_only": ["R", "W"],
        },
        "key_results": {
            "evaluation_period": (
                "2025-02-01至" + str(dates[days - 1]) if official_days else "尚未进入正式评价期"
            ),
            "evaluation_days": official_days,
            "planned_purchase_kwh": float(grid[sl].sum()),
            "planned_charge_kwh": float(charge[sl].sum()),
            "planned_discharge_kwh": float(discharge[sl].sum()),
            "emergency_purchase_kwh": float(emergency[sl].sum()),
            "curtailment_kwh": float(curtailment[sl].sum()),
            "planned_cost_yuan": float(planned_cost[sl].sum()),
            "emergency_cost_yuan": float(emergency_cost[sl].sum()),
            "actual_total_cost_yuan": float(actual_total[sl].sum()),
            "emergency_intervals": int(np.sum(emergency[sl] > 1e-7)),
            "minimum_soc_kwh": float(min(soc_start[sl].min(initial=INITIAL_SOC), soc_end[sl].min(initial=INITIAL_SOC))),
            "maximum_soc_kwh": float(max(soc_start[sl].max(initial=INITIAL_SOC), soc_end[sl].max(initial=INITIAL_SOC))),
        },
        "forecast_metrics": {"WAPE": wape, "MAE_kwh": mae, "RMSE_kwh": rmse, "Bias_kwh": bias},
        "parameter_selection": {
            "monthly_log": selection_log,
            "scenario_count_rule": "整日残差按总误差排序作等概率分位抽样；10/20/30按统计签名0.5%收敛取较小者",
            "scenario_count_min": int(scenario_counts.min()),
            "scenario_count_max": int(scenario_counts.max()),
            "randomness": "无；分位抽样完全确定性复现",
        },
        "intermediate_results": {
            "constraint_check": "all_passed" if (
                max_balance_residual <= 1e-5
                and max_soc_residual <= 1e-5
                and simultaneous_count == 0
                and np.all(soc_start >= SOC_MIN - 1e-6)
                and np.all(soc_end <= SOC_MAX + 1e-6)
            ) else "failed",
            "max_scenario_balance_residual_kwh": max_balance_residual,
            "max_soc_residual_kwh": max_soc_residual,
            "simultaneous_charge_discharge_intervals": simultaneous_count,
            "soc_link_max_residual_kwh": float(np.max(np.abs(soc_start[1:] - soc_end[:-1]))) if days > 1 else 0.0,
            "all_solver_runs_have_solution": len(day_messages) == days,
            "total_runtime_seconds": elapsed_all,
            "mean_daily_solve_seconds": float(solve_seconds.mean()),
            "max_daily_solve_seconds": float(solve_seconds.max()),
        },
        "environment": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "scipy": scipy.__version__,
            "solver": "scipy.optimize.milp (HiGHS)",
        },
        "artifacts": {"detail": "results/q2_detail.npz", "code": "code/q2_model.py"},
        "warnings": [
            "两日滚动视野的第二日只作为终端延续近似，执行时仅冻结首日计划；视野末端SOC回到视野初值以抑制截断放空。"
        ] if horizon_days == 2 else [
            "单日视野可能低估日末储能的跨日价值。"
        ],
    }
    with (STATE_DIR / "q2_results.json").open("w", encoding="utf-8") as handle:
        json.dump(output, handle, ensure_ascii=False, indent=2)
    return output


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=365)
    parser.add_argument("--horizon-days", type=int, choices=(1, 2), default=2)
    args = parser.parse_args()
    result = run_q2(days=args.days, horizon_days=args.horizon_days)
    print(json.dumps({
        "key_results": result["key_results"],
        "forecast_metrics": result["forecast_metrics"],
        "checks": result["intermediate_results"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
