# -*- coding: utf-8 -*-
"""
只做“拟合 + 拟合图”，其余图都不要。
步骤：读数 -> 训练概率模型(含Isotonic校准) -> 画【观测vs预测(分箱标定)】一张图并保存。
"""

import os, re, warnings
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.isotonic import IsotonicRegression
from sklearn.ensemble import HistGradientBoostingClassifier, GradientBoostingClassifier
from sklearn.calibration import calibration_curve

warnings.filterwarnings("ignore")

EXCEL_PATH = "附件.xlsx"        #
OUT_DIR    = "./"
PLOT_PATH  = os.path.join(OUT_DIR, "fit_obs_vs_pred.png")
os.makedirs(OUT_DIR, exist_ok=True)


matplotlib.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
matplotlib.rcParams['axes.unicode_minus'] = False
PALETTE = {
    "points": "peachpuff",
    "line": "peru",
    "identity": "silver",
    "density": "YlOrBr",
}

def _soft_axes_square(ax=None):
    ax = ax or plt.gca()
    ax.grid(True, alpha=0.25, linestyle="--")
    ax.set_facecolor("#fcfcfc")
    ax.set_aspect("equal", adjustable="box")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    return ax

# === 小工具：列名标准化 / 孕周解析 / 比例修正 ===
def parse_week_to_float(x):
    if pd.isna(x): return np.nan
    s = str(x).strip().lower().replace('周','w').replace('d','')
    m = re.match(r'^(\d+)\s*w\+(\d+)$', s)
    if m: return int(m.group(1)) + int(m.group(2))/7.0
    m = re.match(r'^(\d+)\s*\+\s*(\d+)$', s)
    if m: return int(m.group(1)) + int(m.group(2))/7.0
    try: return float(s)
    except: return np.nan

def standardize_columns(df: pd.DataFrame) -> pd.DataFrame:
    rename_map = {}
    for c in df.columns:
        cc = str(c).strip().replace(' ', '')
        if cc in ['孕妇代码','样本编号','样本ID','孕妇编号']: rename_map[c] = 'id'
        elif cc in ['检测孕周','孕周','孕周数','孕周(周)']:   rename_map[c] = 'gw_raw'
        elif cc in ['孕妇BMI','BMI','bmi']:                 rename_map[c] = 'bmi'
        elif cc in ['Y染色体浓度','Y浓度','y浓度']:         rename_map[c] = 'y_frac'
        elif cc in ['GC含量','gc含量','GC']:                rename_map[c] = 'gc'
        elif cc in ['在参考基因组上比对的比例','比对比例','比对率']: rename_map[c] = 'map_ratio'
        elif cc in ['重复读段的比例','重复率','dup率']:        rename_map[c] = 'dup_ratio'
        elif cc in ['被过滤掉读段数的比例','过滤比例','filter比例']: rename_map[c] = 'flt_ratio'
        elif cc in ['原始读段数','rawreads','原始reads数','原始测序读段数']: rename_map[c] = 'raw_reads'
        elif cc in ['唯一比对的读段数','唯一比对的读段数 ','唯一比对读段数']: rename_map[c] = 'uniq_reads'
    return df.rename(columns=rename_map)

def normalize_rate(s):
    v = pd.to_numeric(s.astype(str).str.replace("%","").str.replace(",",""), errors="coerce")
    return v/100.0 if (np.nanmax(v) > 1.5) else v

# === 只保留拟合所需的数据准备 ===
def load_data_for_fit(excel_path="附件.xlsx", min_week=10.0, max_week=30.0):
    df0 = pd.read_excel(excel_path, sheet_name=0)
    df0 = standardize_columns(df0)

    for need in ['id','gw_raw','bmi','y_frac','gc','map_ratio','dup_ratio','flt_ratio','raw_reads','uniq_reads']:
        if need not in df0.columns: df0[need] = np.nan

    df0['gw'] = df0['gw_raw'].apply(parse_week_to_float)

    # 比例字段裁剪/修正一下
    for p in ['gc','map_ratio','dup_ratio','flt_ratio','y_frac']:
        x = pd.to_numeric(df0[p], errors="coerce")
        if (x > 1).mean() > 0.3: x = x/100.0
        df0[p] = x.clip(0, 1)

    # reads 做log10
    for rd in ['raw_reads','uniq_reads']:
        df0[f'log10_{rd}'] = np.log10(pd.to_numeric(df0[rd], errors="coerce").clip(lower=0) + 1.0)

    # 关键列不能缺
    df = df0.dropna(subset=['gw','bmi','y_frac']).copy()
    df = df[(df['gw']>=min_week) & (df['gw']<=max_week)]

    # 标签：是否达标(>=4%)
    df['achieve'] = (df['y_frac'] >= 0.04).astype(int)

    feat_cols = ['gw','bmi','gc','map_ratio','dup_ratio','flt_ratio','log10_raw_reads','log10_uniq_reads']
    for c in feat_cols:
        if c not in df.columns: df[c] = np.nan
    df[feat_cols] = df[feat_cols].fillna(df[feat_cols].median())

    if 'id' not in df.columns: df['id'] = np.arange(len(df))
    return df, feat_cols

# === 概率模型（gw 单调非减 + Isotonic校准） ===
class AchieveProbModel:
    def __init__(self, feature_cols, monotonic_gw_idx=None):
        self.feature_cols = feature_cols
        self.monotonic_gw_idx = monotonic_gw_idx
        self.scaler = StandardScaler()
        self.clf = None
        self.iso = None
        self.use_histgb = True

    def _build_classifier(self):
        if self.use_histgb:
            n_features = len(self.feature_cols)
            mono = [0]*n_features
            if self.monotonic_gw_idx is not None:
                mono[self.monotonic_gw_idx] = 1  # gw 单调非减
            return HistGradientBoostingClassifier(
                max_depth=3, learning_rate=0.08, max_iter=500,
                monotonic_cst=mono, l2_regularization=1e-3
            )
        else:
            return GradientBoostingClassifier(
                learning_rate=0.06, n_estimators=600, max_depth=3, subsample=0.9
            )

    def fit(self, df, label_col='achieve'):
        X = df[self.feature_cols].astype(float).values
        y = df[label_col].astype(int).values
        Xs = self.scaler.fit_transform(X)
        # 先试HGB(带单调约束)，不行再回退GBDT
        try:
            self.use_histgb = True
            self.clf = self._build_classifier()
            self.clf.fit(Xs, y)
        except Exception:
            self.use_histgb = False
            self.clf = self._build_classifier()
            self.clf.fit(Xs, y)

        # Holdout 里做Isotonic校准（避免概率偏硬）
        Xtr, Xval, ytr, yval = train_test_split(Xs, y, test_size=0.25, stratify=y, random_state=42)
        self.clf.fit(Xtr, ytr)
        raw = self.clf.predict_proba(Xval)[:, 1]
        self.iso = IsotonicRegression(out_of_bounds='clip')
        self.iso.fit(raw, yval)

    def predict_proba(self, df):
        X = df[self.feature_cols].astype(float).values
        Xs = self.scaler.transform(X)
        raw = self.clf.predict_proba(Xs)[:, 1]
        if self.iso is not None:
            cal = self.iso.transform(raw)
            return np.clip(cal, 1e-5, 1-1e-5)
        return np.clip(raw, 1e-5, 1-1e-5)

# === 主流程：拟合 + 单张“拟合图”(观测vs预测，分箱标定) ===
if __name__ == "__main__":
    # 1) 数据
    df, feat_cols = load_data_for_fit(EXCEL_PATH, min_week=10.0, max_week=30.0)

    # 2) 训练模型（gw 单调非减）
    gw_idx = feat_cols.index('gw') if 'gw' in feat_cols else None
    model = AchieveProbModel(feat_cols, monotonic_gw_idx=gw_idx)
    model.fit(df, label_col='achieve')

    # 3) 生成“观测vs预测”的拟合图（用分箱均值，避免点都堆在0/1角落）
    y = df['achieve'].astype(int).values
    p = model.predict_proba(df)

    # 分位数等量分箱更稳（点数少时自动降箱）
    nbin = max(6, min(20, int(np.sqrt(max(50, len(p))))))
    prob_true, prob_pred = calibration_curve(y, p, n_bins=nbin, strategy='quantile')

    plt.figure(figsize=(6, 6))
    ax = _soft_axes_square()

    try:
        hb = ax.hexbin(p, y, gridsize=25, extent=[0,1,0,1], cmap=PALETTE["density"], mincnt=1, alpha=0.25)
    except Exception:
        pass

    ax.plot(prob_pred, prob_true, color=PALETTE["line"], linewidth=2.0, label="分箱均值曲线")
    ax.scatter(prob_pred, prob_true, s=36, color=PALETTE["points"], edgecolor="white", zorder=3, label="分箱均值点")

    # y=x 参考线
    xs = np.linspace(0, 1, 200)
    ax.plot(xs, xs, linestyle="--", color=PALETTE["identity"], linewidth=1.4, label="理想：预测=观测")

    ax.set_title("拟合图：观测(达标率) vs 预测概率（分箱标定）")
    ax.set_xlabel("预测概率（分箱均值）")
    ax.set_ylabel("真实达标率（分箱均值）")
    ax.legend(frameon=False, loc="lower right")

    plt.tight_layout()
    plt.savefig(PLOT_PATH, dpi=160)
    plt.close()

    print("图文件：", PLOT_PATH)
