import argparse
from pathlib import Path

import numpy as np
import pandas as pd


SUBJECTS = [
    ("历史", "历史原始", "历史赋分"),
    ("地理", "地理原始", "地理赋分"),
    ("政治", "政治原始", "政治赋分"),
    ("物理", "物理原始", "物理赋分"),
    ("化学", "化学原始", "化学赋分"),
    ("生物", "生物原始", "生物赋分"),
    ("技术", "技术原始", "技术赋分"),
]

CORE_150 = ["语文", "数学", "英语"]


def _to_number(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def _clip(series: pd.Series, max_value: float) -> pd.Series:
    s = _to_number(series)
    return s.clip(lower=0, upper=max_value)


def _drop_unnamed_columns(df: pd.DataFrame) -> pd.DataFrame:
    unnamed = [c for c in df.columns if str(c).startswith("Unnamed")]
    return df.drop(columns=unnamed, errors="ignore")


def _reorder_columns(df: pd.DataFrame) -> pd.DataFrame:
    preferred = [
        "准考证号",
        "姓名",
        *CORE_150,
        *[c for _, raw, f in SUBJECTS for c in (raw, f)],
    ]
    existing_preferred = [c for c in preferred if c in df.columns]
    remaining = [c for c in df.columns if c not in existing_preferred]
    return df[existing_preferred + remaining]


def enforce_rules(df: pd.DataFrame) -> pd.DataFrame:
    df = _drop_unnamed_columns(df.copy())

    # 1) 保证列存在
    for c in CORE_150:
        if c not in df.columns:
            raise ValueError(f"缺少必需列: {c}")

    for _, raw_col, fufen_col in SUBJECTS:
        if raw_col not in df.columns:
            df[raw_col] = pd.NA
        if fufen_col not in df.columns:
            df[fufen_col] = pd.NA

    # 2) 满分裁剪
    for c in CORE_150:
        df[c] = _clip(df[c], 150)

    for _, raw_col, fufen_col in SUBJECTS:
        df[raw_col] = _clip(df[raw_col], 100)
        df[fufen_col] = _clip(df[fufen_col], 100)

    # 3) 强制“七选三”：按赋分最高的三门作为选科，其余置空
    fufen_cols = [f for _, _, f in SUBJECTS]

    fufen_values = df[fufen_cols].to_numpy(dtype=float)
    # NaN 视为极小值，不会被选中
    fufen_values_for_rank = np.where(np.isnan(fufen_values), -np.inf, fufen_values)

    # argsort 得到从小到大索引，取最后3个为 top3（顺序无关）
    top3_idx = np.argsort(fufen_values_for_rank, axis=1)[:, -3:]

    keep_mask = np.zeros_like(fufen_values_for_rank, dtype=bool)
    row_idx = np.arange(len(df))[:, None]
    keep_mask[row_idx, top3_idx] = True

    # 如果某行所有赋分都是 NaN（理论上不应发生），就保留前三门（按 SUBJECTS 顺序）
    no_valid = np.isneginf(fufen_values_for_rank).all(axis=1)
    if no_valid.any():
        keep_mask[no_valid, :] = False
        keep_mask[no_valid, :3] = True

    for i, (subj, raw_col, fufen_col) in enumerate(SUBJECTS):
        drop = ~keep_mask[:, i]
        df.loc[drop, raw_col] = pd.NA
        df.loc[drop, fufen_col] = pd.NA

    # 4) 数值类型与排版：赋分/原始列尽量用可空整数，列顺序固定
    for _, raw_col, fufen_col in SUBJECTS:
        df[raw_col] = pd.to_numeric(df[raw_col], errors="coerce").astype("Int64")
        df[fufen_col] = pd.to_numeric(df[fufen_col], errors="coerce").astype("Int64")

    for c in CORE_150:
        df[c] = pd.to_numeric(df[c], errors="coerce").astype("Int64")

    df = _reorder_columns(df)

    return df


def main() -> None:
    parser = argparse.ArgumentParser(description="按满分与6选3规则规范化成绩 CSV")
    parser.add_argument("--input", required=True, help="输入 CSV 路径")
    parser.add_argument("--output", required=True, help="输出 CSV 路径")
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)

    df = pd.read_csv(input_path)
    df2 = enforce_rules(df)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    df2.to_csv(output_path, index=False, encoding="utf-8-sig")


if __name__ == "__main__":
    main()
