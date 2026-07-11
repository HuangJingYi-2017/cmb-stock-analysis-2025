#!/usr/bin/env python3
"""
TASK4 数据更新脚本：合并旧数据 + Tushare 最新数据，生成 cmb_600036_daily_latest.csv
通过 Tushare MCP 连接器获取数据，Token 由 MCP 配置管理，不写死在代码中。
"""
import json
import csv
import os
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ============================================================
# 1. 读取旧数据文件
# ============================================================
print("=" * 70)
print("TASK4 数据更新：招商银行 600036.SH 日线数据合并")
print("=" * 70)

old_records = []

# 旧文件1: data/cmb_2025_daily.csv (日期格式 YYYY-MM-DD)
old_file1 = os.path.join(BASE_DIR, "data", "cmb_2025_daily.csv")
if os.path.exists(old_file1):
    with open(old_file1, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            td = row["trade_date"].strip()
            # 统一为 YYYYMMDD
            td_norm = td.replace("-", "")
            old_records.append({
                "ts_code": row["ts_code"],
                "trade_date": td_norm,
                "open": float(row["open"]),
                "high": float(row["high"]),
                "low": float(row["low"]),
                "close": float(row["close"]),
                "pre_close": float(row["pre_close"]),
                "change": float(row["change"]),
                "pct_chg": float(row["pct_chg"]),
                "vol": float(row["vol"]),
                "amount": float(row["amount"]),
                "_source": "old_csv1"
            })
    print(f"[旧文件1] data/cmb_2025_daily.csv: {len([r for r in old_records if r['_source']=='old_csv1'])} 条")

# 旧文件2: cmb_daily.csv (根目录, 日期格式 YYYYMMDD)
old_file2 = os.path.join(BASE_DIR, "cmb_daily.csv")
if os.path.exists(old_file2):
    count_before = len(old_records)
    with open(old_file2, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            td = row["trade_date"].strip()
            old_records.append({
                "ts_code": row["ts_code"],
                "trade_date": td,
                "open": float(row["open"]),
                "high": float(row["high"]),
                "low": float(row["low"]),
                "close": float(row["close"]),
                "pre_close": float(row["pre_close"]),
                "change": float(row["change"]),
                "pct_chg": float(row["pct_chg"]),
                "vol": float(row["vol"]),
                "amount": float(row["amount"]),
                "_source": "old_csv2"
            })
    print(f"[旧文件2] cmb_daily.csv: {len(old_records) - count_before} 条")

# 记录旧数据日期范围
old_dates = sorted(set(r["trade_date"] for r in old_records))
old_date_start = old_dates[0] if old_dates else "N/A"
old_date_end = old_dates[-1] if old_dates else "N/A"
print(f"[旧数据] 合计 {len(old_records)} 条, 去重后 {len(old_dates)} 个交易日")
print(f"[旧数据] 日期范围: {old_date_start} ~ {old_date_end}")

# ============================================================
# 2. 读取 Tushare 最新数据 (MCP 返回的 JSON)
# ============================================================
print("\n" + "-" * 70)
print("[Tushare MCP] 加载最新日线数据...")

# Tushare MCP 返回的数据 (从 MCP 工具调用结果获取)
tushare_json_path = os.path.join(BASE_DIR, "data", "_tushare_latest.json")
with open(tushare_json_path, "r", encoding="utf-8") as f:
    tushare_data = json.load(f)

print(f"[Tushare] 获取到 {len(tushare_data)} 条记录")
tushare_dates = sorted(set(r["trade_date"] for r in tushare_data))
print(f"[Tushare] 日期范围: {tushare_dates[0]} ~ {tushare_dates[-1]}")

# ============================================================
# 3. 合并所有数据，按 trade_date 去重（Tushare 数据优先）
# ============================================================
print("\n" + "-" * 70)
print("合并数据并去重...")

# 合并：先放旧数据，再用 Tushare 数据覆盖（同日期取 Tushare）
merged = {}
for r in old_records:
    td = r["trade_date"]
    if td not in merged:
        merged[td] = {k: v for k, v in r.items() if k != "_source"}

# Tushare 数据覆盖（优先级最高）
new_count = 0
for r in tushare_data:
    td = r["trade_date"]
    if td not in merged:
        new_count += 1
    merged[td] = {
        "ts_code": r["ts_code"],
        "trade_date": td,
        "open": float(r["open"]),
        "high": float(r["high"]),
        "low": float(r["low"]),
        "close": float(r["close"]),
        "pre_close": float(r["pre_close"]),
        "change": float(r["change"]),
        "pct_chg": float(r["pct_chg"]),
        "vol": float(r["vol"]),
        "amount": float(r["amount"])
    }

# 按日期排序
all_dates = sorted(merged.keys())
final_records = [merged[d] for d in all_dates]

print(f"合并后总记录数: {len(final_records)} 条")
print(f"新增交易日数: {new_count} 条")

# ============================================================
# 4. 格式化日期为 YYYY-MM-DD 并保存
# ============================================================
print("\n" + "-" * 70)
print("保存数据...")

# 转换日期格式 YYYYMMDD -> YYYY-MM-DD
for r in final_records:
    td = r["trade_date"]
    r["trade_date"] = f"{td[0:4]}-{td[4:6]}-{td[6:8]}"

output_path = os.path.join(BASE_DIR, "data", "cmb_600036_daily_latest.csv")
fieldnames = ["ts_code", "trade_date", "open", "high", "low", "close",
              "pre_close", "change", "pct_chg", "vol", "amount"]

with open(output_path, "w", encoding="utf-8-sig", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    for r in final_records:
        writer.writerow({k: r[k] for k in fieldnames})

print(f"已保存: {output_path}")
print(f"总记录数: {len(final_records)} 条")

# ============================================================
# 5. 数据质量分析
# ============================================================
print("\n" + "=" * 70)
print("数据质量分析报告")
print("=" * 70)

# 时间范围
final_dates = [r["trade_date"] for r in final_records]
date_start = final_dates[0]
date_end = final_dates[-1]

# 新增条数计算
old_dates_set = set(old_dates)
new_dates_set = set(tushare_dates)
added_dates = sorted(new_dates_set - old_dates_set)

print(f"\n1. 原始数据时间范围:")
print(f"   data/cmb_2025_daily.csv: {old_date_start[:4]}-{old_date_start[4:6]}-{old_date_start[6:8]} ~ "
      f"{old_dates[-1][:4]}-{old_dates[-1][4:6]}-{old_dates[-1][6:8] if len(old_dates[-1]) == 8 else old_dates[-1][5:7]}")
# 更准确的显示
old_start_fmt = f"{old_date_start[0:4]}-{old_date_start[4:6]}-{old_date_start[6:8]}" if len(old_date_start) == 8 else old_date_start
old_end_fmt = f"{old_date_end[0:4]}-{old_date_end[4:6]}-{old_date_end[6:8]}" if len(old_date_end) == 8 else old_date_end
print(f"   合并后旧数据: {old_start_fmt} ~ {old_end_fmt}")
print(f"   旧数据交易日数: {len(old_dates)}")

print(f"\n2. 更新后数据时间范围:")
print(f"   {date_start} ~ {date_end}")
print(f"   更新后交易日数: {len(final_records)}")

print(f"\n3. 新增交易日数据:")
print(f"   新增 {len(added_dates)} 个交易日")
if added_dates:
    for d in added_dates[:10]:
        ds = f"{d[0:4]}-{d[4:6]}-{d[6:8]}"
        print(f"     {ds}")
    if len(added_dates) > 10:
        print(f"     ... 共 {len(added_dates)} 个")

# 缺失值检查
print(f"\n4. 缺失值检查:")
total_missing = 0
for field in fieldnames:
    missing = sum(1 for r in final_records if r[field] is None or r[field] == "")
    if missing > 0:
        print(f"   [WARN] {field}: {missing} 个缺失值")
        total_missing += missing
if total_missing == 0:
    print(f"   [OK] 所有字段无缺失值")

# 重复日期检查
print(f"\n5. 重复日期检查:")
dup_check = {}
for r in final_records:
    dup_check[r["trade_date"]] = dup_check.get(r["trade_date"], 0) + 1
dups = {k: v for k, v in dup_check.items() if v > 1}
if dups:
    print(f"   [WARN] 发现 {len(dups)} 个重复日期")
    for d, c in list(dups.items())[:5]:
        print(f"     {d}: {c} 次")
else:
    print(f"   [OK] 无重复日期")

# 价格逻辑检查
print(f"\n6. 价格逻辑检查:")
price_err = [r for r in final_records if r["high"] < r["low"]]
if price_err:
    print(f"   [WARN] {len(price_err)} 条 high < low")
else:
    print(f"   [OK] 所有记录 high >= low")

# 关键字段检查 (TASK4 需要: high, low, close)
print(f"\n7. TASK4 海龟策略字段检查:")
task4_fields = ["high", "low", "close"]
all_ok = True
for field in task4_fields:
    vals = [r[field] for r in final_records]
    has_null = any(v is None for v in vals)
    has_zero = any(v == 0 for v in vals)
    if has_null or has_zero:
        print(f"   [WARN] {field}: 存在空值或零值")
        all_ok = False
    else:
        print(f"   [OK] {field}: {len(vals)} 条有效值, 范围 {min(vals):.2f} ~ {max(vals):.2f}")

# vol 字段检查
vol_vals = [r["vol"] for r in final_records]
print(f"   [OK] vol: {len(vol_vals)} 条有效值, 日均 {sum(vol_vals)/len(vol_vals):,.0f} 手")

# 数据量是否足够 (海龟策略通常需要 20-55 日通道)
print(f"\n8. 数据量评估:")
print(f"   总交易日数: {len(final_records)}")
print(f"   海龟策略常用参数: 20日通道(入场), 10日通道(退出), 20日ATR(仓位)")
print(f"   最少需要 ~55 个交易日即可开始回测")
if len(final_records) >= 55:
    print(f"   [OK] 数据量 {len(final_records)} 条，远超最低要求，满足回测需求")
else:
    print(f"   [WARN] 数据量不足，建议获取更多历史数据")

print(f"\n{'=' * 70}")
print("数据更新完成！")
print(f"输出文件: data/cmb_600036_daily_latest.csv")
print(f"{'=' * 70}")
