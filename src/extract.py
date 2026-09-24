"""
EXTRACT：把旧系统导出的 Excel 报表原样转成 pipeline 使用的 RAW CSV 格式。

  - 不解释任何业务含义，所有单元格都当文本
  - 列名 raw_col_1 … raw_col_7，外加 source_row_id / ingest_row_id（从 1 开始）
  - 和 data/legacy_dirty/sales_dirty.csv 的格式完全一致

单独运行：python src/extract.py data/grouth_truth/2026-2.xlsx /tmp/2026-2.csv
通常由 pipeline.py 自动调用。
"""
import sys
from pathlib import Path

import pandas as pd

N_COLS = 7


def xlsx_to_raw_csv(xlsx_path, csv_path):
    df = pd.read_excel(xlsx_path, header=None, dtype=str)
    if df.shape[1] != N_COLS:
        raise ValueError(f"{Path(xlsx_path).name}: 期望 {N_COLS} 列，实际 {df.shape[1]} 列")
    df.columns = [f"raw_col_{i}" for i in range(1, N_COLS + 1)]
    df["source_row_id"] = range(1, len(df) + 1)
    df["ingest_row_id"] = df["source_row_id"]
    Path(csv_path).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(csv_path, index=False)
    return len(df)


if __name__ == "__main__":
    n = xlsx_to_raw_csv(sys.argv[1], sys.argv[2])
    print(f"已转换 {n} 行 → {sys.argv[2]}")
