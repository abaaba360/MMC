"""Q2因果日前净负荷预测与整日残差情景生成。

所有函数均通过 history_end 明确限制标签可见范围。任何目标日的真实值只在
该日完成后进入残差库。候选包括季节加权朴素法N1与岭回归N3。
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler


ALPHA_GRID = (0.0, 0.25, 0.5, 0.75, 1.0)
RIDGE_LAMBDA_GRID = (0.01, 0.1, 1.0, 10.0, 100.0)
RIDGE_WINDOW_GRID = (56, 112, 10000)


@dataclass(frozen=True)
class ForecastChoice:
    method: str
    params: dict[str, float | int | str]
    validation_wape: float
    validation_mae: float
    validation_days: int


def _safe_lag(net: np.ndarray, day: int, lag: int, fallback: np.ndarray) -> np.ndarray:
    idx = day - lag
    return net[idx] if idx >= 0 else fallback


def seasonal_forecast(
    net: np.ndarray,
    day: int,
    alpha: float,
    fallback: np.ndarray,
    *,
    recursive_lag1: np.ndarray | None = None,
) -> np.ndarray:
    """N1预测；day可以等于历史截止日以后的第一天。"""

    if day <= 0:
        return np.asarray(fallback, dtype=float).copy()
    lag1 = recursive_lag1 if recursive_lag1 is not None else net[day - 1]
    lag7 = _safe_lag(net, day, 7, lag1)
    return alpha * np.asarray(lag1) + (1.0 - alpha) * np.asarray(lag7)


def _day_features(
    net: np.ndarray,
    load: np.ndarray,
    pv: np.ndarray,
    day: int,
    fallback: np.ndarray,
    *,
    lag1_override: np.ndarray | None = None,
) -> np.ndarray:
    """构造某目标日144条记录；只引用目标日前的日数据。"""

    t = np.arange(144, dtype=float)
    doy = float(day + 1)
    weekday = day % 7
    lag1 = lag1_override if lag1_override is not None else _safe_lag(net, day, 1, fallback)
    lag7 = _safe_lag(net, day, 7, lag1)
    start = max(0, day - 7)
    hist = net[start:day]
    if hist.shape[0] == 0:
        hist_mean = fallback
        hist_std = np.zeros(144)
    else:
        hist_mean = hist.mean(axis=0)
        hist_std = hist.std(axis=0)
    prev_load = load[day - 1] if day >= 1 else np.maximum(fallback, 0.0)
    prev_pv = pv[day - 1] if day >= 1 else np.maximum(-fallback, 0.0)
    scalar = np.column_stack(
        [
            np.sin(2 * np.pi * t / 144),
            np.cos(2 * np.pi * t / 144),
            np.full(144, np.sin(2 * np.pi * doy / 365)),
            np.full(144, np.cos(2 * np.pi * doy / 365)),
            np.full(144, float(weekday >= 5)),
            np.full(144, float(weekday)),
            lag1,
            lag7,
            hist_mean,
            hist_std,
            np.full(144, float(np.mean(lag1))),
            np.full(144, float(np.max(lag1))),
            np.full(144, float(np.min(lag1))),
            np.full(144, float(np.sum(prev_load))),
            np.full(144, float(np.sum(prev_pv))),
        ]
    )
    return scalar


def fit_ridge(
    net: np.ndarray,
    load: np.ndarray,
    pv: np.ndarray,
    history_end: int,
    lam: float,
    window: int,
    fallback: np.ndarray,
):
    """在[0, history_end)日拟合N3，窗口和标准化均仅用过去。"""

    train_start = max(1, history_end - int(window))
    train_days = list(range(train_start, history_end))
    if len(train_days) < 7:
        return None
    x = np.vstack([_day_features(net, load, pv, d, fallback) for d in train_days])
    y = np.concatenate([net[d] for d in train_days])
    model = make_pipeline(StandardScaler(), Ridge(alpha=float(lam), fit_intercept=True))
    model.fit(x, y)
    return model


def ridge_forecast(
    model,
    net: np.ndarray,
    load: np.ndarray,
    pv: np.ndarray,
    day: int,
    fallback: np.ndarray,
    *,
    lag1_override: np.ndarray | None = None,
) -> np.ndarray:
    if model is None:
        return seasonal_forecast(net, day, 1.0, fallback, recursive_lag1=lag1_override)
    x = _day_features(net, load, pv, day, fallback, lag1_override=lag1_override)
    return np.asarray(model.predict(x), dtype=float)


def _metrics(actual: np.ndarray, predicted: np.ndarray) -> tuple[float, float]:
    err = np.asarray(predicted) - np.asarray(actual)
    mae = float(np.mean(np.abs(err)))
    den = float(np.sum(np.abs(actual)))
    wape = float(np.sum(np.abs(err)) / den) if den > 1e-12 else float("inf")
    return wape, mae


def select_month_model(
    net: np.ndarray,
    load: np.ndarray,
    pv: np.ndarray,
    month_start: int,
    fallback: np.ndarray,
) -> ForecastChoice:
    """用月首前最近14日作严格时间验证，选择N1或N3。

    岭回归在验证段开始前一次拟合，因此其系数对14个验证原点均为过去信息；
    滞后特征则按各验证日当时已完成的数据逐日构造。
    """

    val_start = max(1, month_start - 14)
    val_days = list(range(val_start, month_start))
    if not val_days:
        return ForecastChoice("N1", {"alpha": 1.0}, float("nan"), float("nan"), 0)

    candidates: list[tuple[float, float, int, str, dict[str, float | int | str]]] = []
    for alpha in ALPHA_GRID:
        preds = np.vstack([seasonal_forecast(net, d, alpha, fallback) for d in val_days])
        wape, mae = _metrics(net[val_days], preds)
        candidates.append((wape, mae, 1, "N1", {"alpha": alpha}))

    train_end = val_start
    for window in RIDGE_WINDOW_GRID:
        for lam in RIDGE_LAMBDA_GRID:
            model = fit_ridge(net, load, pv, train_end, lam, window, fallback)
            if model is None:
                continue
            preds = np.vstack(
                [ridge_forecast(model, net, load, pv, d, fallback) for d in val_days]
            )
            wape, mae = _metrics(net[val_days], preds)
            candidates.append(
                (wape, mae, 3, "N3", {"lambda": lam, "window_days": int(window)})
            )
    candidates.sort(key=lambda row: (row[0], row[2], row[1]))
    best = candidates[0]
    # 差异不足1%时按预先规则选更简单的N1。
    near = [row for row in candidates if row[0] <= best[0] * 1.01]
    chosen = min(near, key=lambda row: (row[2], row[0], row[1]))
    return ForecastChoice(chosen[3], chosen[4], chosen[0], chosen[1], len(val_days))


def forecast_from_choice(
    choice: ForecastChoice,
    net: np.ndarray,
    load: np.ndarray,
    pv: np.ndarray,
    day: int,
    history_end: int,
    fallback: np.ndarray,
    *,
    lag1_override: np.ndarray | None = None,
) -> np.ndarray:
    """按已在月首冻结的模型配置生成预测。"""

    if choice.method == "N1":
        return seasonal_forecast(
            net,
            day,
            float(choice.params["alpha"]),
            fallback,
            recursive_lag1=lag1_override,
        )
    model = fit_ridge(
        net,
        load,
        pv,
        history_end,
        float(choice.params["lambda"]),
        int(choice.params["window_days"]),
        fallback,
    )
    return ridge_forecast(
        model, net, load, pv, day, fallback, lag1_override=lag1_override
    )


def choose_scenario_count(residuals: np.ndarray) -> int:
    """按残差分布统计量的0.5%收敛准则从10/20/30中选较小场景数。"""

    n = len(residuals)
    if n <= 10:
        return max(1, n)
    previous = None
    for size in (10, 20, 30):
        use = min(size, n)
        idx = np.linspace(0, n - 1, use).round().astype(int)
        ordered = residuals[np.argsort(residuals.sum(axis=1))]
        sample = ordered[idx]
        signature = np.array(
            [np.mean(np.maximum(sample, 0.0)), np.quantile(sample, 0.95)]
        )
        if previous is not None:
            denom = np.maximum(np.abs(signature), 1e-9)
            if float(np.max(np.abs(signature - previous) / denom)) < 0.005:
                return max(10, use - 10)
        previous = signature
        if use == n:
            return use
    return min(30, n)


def residual_scenarios(
    point: np.ndarray,
    residuals: np.ndarray,
    *,
    scenario_count: int | None = None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """用整日残差向量作等概率分位抽样，保留144维日内相关性。"""

    point = np.asarray(point, dtype=float)
    if residuals.size == 0:
        return point[None, :], np.ones(1), np.array([], dtype=int)
    residuals = np.asarray(residuals, dtype=float)
    count = scenario_count or choose_scenario_count(residuals)
    count = min(max(1, int(count)), len(residuals))
    order = np.argsort(residuals.sum(axis=1))
    idx_sorted = np.linspace(0, len(residuals) - 1, count).round().astype(int)
    selected = order[idx_sorted]
    scenarios = point[None, :] + residuals[selected]
    probs = np.full(count, 1.0 / count)
    return scenarios, probs, selected

