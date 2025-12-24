import argparse
from pathlib import Path

import numpy as np
import pandas as pd


SUBJECTS = [
    ("历史原始", "历史赋分"),
    ("地理原始", "地理赋分"),
    ("政治原始", "政治赋分"),
    ("物理原始", "物理赋分"),
    ("化学原始", "化学赋分"),
    ("生物原始", "生物赋分"),
    ("技术原始", "技术赋分"),
]

# 20 级人数比例上限（累计比例）
LEVEL_CUM_RATIOS = [
    0.03,
    0.06,
    0.10,
    0.15,
    0.21,
    0.28,
    0.36,
    0.43,
    0.50,
    0.57,
    0.64,
    0.71,
    0.78,
    0.84,
    0.89,
    0.93,
    0.96,
    0.98,
    0.99,
    1.00,
]

# 20 级等级赋分区间（低分, 高分），起点 40
LEVEL_SCORE_RANGES = [
    (97, 100),
    (94, 96),
    (91, 93),
    (88, 90),
    (85, 87),
    (82, 84),
    (79, 81),
    (76, 78),
    (73, 75),
    (70, 72),
    (67, 69),
    (64, 66),
    (61, 63),
    (58, 60),
    (55, 57),
    (52, 54),
    (49, 51),
    (46, 48),
    (43, 45),
    (40, 42),
]


def _round_half_up_positive(x: np.ndarray) -> np.ndarray:
    # 分数均为非负，按“四舍五入”实现：0.5 进 1
    return np.floor(x + 0.5).astype(int)


def _assign_levels_by_rank(values: pd.Series) -> pd.Series:
    """基于名次（从高到低）按累计比例分配 1..20 等级。"""
    s = pd.to_numeric(values, errors="coerce")
    mask = s.notna()

    levels = pd.Series(pd.NA, index=s.index, dtype="Int64")
    if not mask.any():
        return levels

    s_valid = s[mask]
    n = len(s_valid)

    # 打散同分，确保严格按人数比例切分
    ranks = s_valid.rank(method="first", ascending=False).astype(int)
    # p in [0,1)
    p = (ranks - 1) / n

    # level = 1..20
    cutoffs = np.array(LEVEL_CUM_RATIOS, dtype=float)
    p_np = p.to_numpy(dtype=float)
    level_idx = np.searchsorted(cutoffs, p_np, side="right") + 1
    levels.loc[mask] = pd.Series(level_idx, index=s_valid.index, dtype="Int64")
    return levels


def zhejiang_grade_score(raw_scores: pd.Series) -> pd.Series:
    """按浙江“5等20级”规则，把原始分转换为等级赋分（整数，40~100）。"""
    raw = pd.to_numeric(raw_scores, errors="coerce")
    levels = _assign_levels_by_rank(raw)

    out = pd.Series(pd.NA, index=raw.index, dtype="Int64")

    for level in range(1, 21):
        idx = levels == level
        if not idx.any():
            continue

        t_low, t_high = LEVEL_SCORE_RANGES[level - 1]
        group = raw[idx].astype(float)
        s1 = float(group.min())
        s2 = float(group.max())

        if s2 == s1:
            t = np.full(group.shape, (t_low + t_high) / 2.0, dtype=float)
        else:
            t = t_low + (group.to_numpy(dtype=float) - s1) * (t_high - t_low) / (s2 - s1)

        t_int = _round_half_up_positive(t)
        t_int = np.clip(t_int, 40, 100)
        out.loc[idx] = pd.Series(t_int, index=group.index, dtype="Int64")

    return out


def apply_to_df(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for raw_col, fufen_col in SUBJECTS:
        if raw_col not in df.columns:
            # 技术可能在原始数据中不存在：允许缺失，按 NA 处理
            df[raw_col] = pd.NA
        if fufen_col not in df.columns:
            df[fufen_col] = pd.NA
        df[fufen_col] = zhejiang_grade_score(df[raw_col])
    return df


def main() -> None:
    parser = argparse.ArgumentParser(description="按浙江5等20级规则重算选考赋分")
    parser.add_argument("--input", required=True, help="输入 CSV 路径")
    parser.add_argument("--output", required=True, help="输出 CSV 路径")
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)

    df = pd.read_csv(input_path)
    df2 = apply_to_df(df)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    df2.to_csv(output_path, index=False, encoding="utf-8-sig")


if __name__ == "__main__":
    main()
