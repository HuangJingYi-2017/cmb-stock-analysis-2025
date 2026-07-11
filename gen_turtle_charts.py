#!/usr/bin/env python3
"""
TASK4: 海龟策略回测图表生成
================================
基于 data/turtle_backtest_result.csv 生成 3 张图表：
  图1: 通道与交易信号图   → output/task4_fig1_turtle_signals.png
  图2: 策略累计净值图     → output/task4_fig2_turtle_equity.png
  图3: 回撤曲线图         → output/task4_fig3_turtle_drawdown.png

中文字体: SimHei / Microsoft YaHei
图片规格: 300 DPI, 适合插入 Word 报告
"""

import os
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from pathlib import Path

# ── 中文字体设置 ──────────────────────────────────────────
plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False  # 负号正常显示
plt.rcParams["figure.dpi"] = 150
plt.rcParams["savefig.dpi"] = 300

# ── 路径配置 ──────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
INPUT_CSV = BASE_DIR / "data" / "turtle_backtest_result.csv"
OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_DIR.mkdir(exist_ok=True)


def load_data():
    """加载回测结果数据"""
    df = pd.read_csv(INPUT_CSV, encoding="utf-8-sig")
    df["trade_date"] = pd.to_datetime(df["trade_date"])
    print(f"✅ 加载数据: {len(df)} 行, {df['trade_date'].iloc[0].date()} ~ {df['trade_date'].iloc[-1].date()}")
    return df


# ════════════════════════════════════════════════════════════
# 图1: 海龟策略通道与交易信号图
# ════════════════════════════════════════════════════════════
def plot_fig1_signals(df):
    fig, ax = plt.subplots(figsize=(14, 7))

    dates = df["trade_date"]
    close = df["close"]
    upper = df["upper_channel"]
    lower = df["lower_channel"]

    # 收盘价曲线
    ax.plot(dates, close, color="#2c3e50", linewidth=1.2, label="收盘价 Close", zorder=3)

    # 上下通道（填充区域）
    ax.fill_between(dates, lower, upper, alpha=0.08, color="#3498db", label="通道区间")
    ax.plot(dates, upper, color="#e74c3c", linewidth=1.0, linestyle="--", label="上轨 Upper Channel (20D)", zorder=2)
    ax.plot(dates, lower, color="#27ae60", linewidth=1.0, linestyle="--", label="下轨 Lower Channel (20D)", zorder=2)

    # 买入信号: 向上红色三角形
    buy_mask = df["buy_signal"] == 1
    if buy_mask.any():
        ax.scatter(
            dates[buy_mask], close[buy_mask],
            marker="^", s=180, color="#e74c3c", edgecolors="white", linewidths=1.2,
            zorder=5, label=f"买入信号 Buy ({buy_mask.sum()})"
        )
        # 在三角形上方标注价格
        for d, p in zip(dates[buy_mask], close[buy_mask]):
            ax.annotate(f"{p:.2f}", (d, p), textcoords="offset points", xytext=(0, 12),
                        fontsize=8, color="#e74c3c", ha="center", fontweight="bold")

    # 卖出信号: 向下绿色三角形
    sell_mask = df["sell_signal"] == 1
    if sell_mask.any():
        ax.scatter(
            dates[sell_mask], close[sell_mask],
            marker="v", s=180, color="#27ae60", edgecolors="white", linewidths=1.2,
            zorder=5, label=f"卖出信号 Sell ({sell_mask.sum()})"
        )
        for d, p in zip(dates[sell_mask], close[sell_mask]):
            ax.annotate(f"{p:.2f}", (d, p), textcoords="offset points", xytext=(0, -18),
                        fontsize=8, color="#27ae60", ha="center", fontweight="bold")

    # 止损信号: 橙色X标记
    stop_mask = df["stop_loss_signal"] == 1
    if stop_mask.any():
        ax.scatter(
            dates[stop_mask], close[stop_mask],
            marker="X", s=200, color="#e67e22", edgecolors="white", linewidths=1.2,
            zorder=6, label=f"止损信号 Stop Loss ({stop_mask.sum()})"
        )
        for d, p in zip(dates[stop_mask], close[stop_mask]):
            ax.annotate(f"{p:.2f}", (d, p), textcoords="offset points", xytext=(0, -20),
                        fontsize=8, color="#e67e22", ha="center", fontweight="bold")

    # 标题和轴标签
    ax.set_title("海龟策略通道与交易信号 — 招商银行 600036.SH", fontsize=16, fontweight="bold", pad=15)
    ax.set_xlabel("日期", fontsize=12)
    ax.set_ylabel("价格 (元)", fontsize=12)

    # 图例
    ax.legend(loc="upper left", fontsize=10, framealpha=0.9)

    # 网格
    ax.grid(True, alpha=0.3, linestyle="--")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
    fig.autofmt_xdate(rotation=30)

    # 边距
    ax.margins(x=0.02)
    plt.tight_layout()

    out_path = OUTPUT_DIR / "task4_fig1_turtle_signals.png"
    fig.savefig(out_path, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"✅ 图1 已保存: {out_path}")
    return out_path


# ════════════════════════════════════════════════════════════
# 图2: 策略累计净值图
# ════════════════════════════════════════════════════════════
def plot_fig2_equity(df):
    fig, ax = plt.subplots(figsize=(14, 7))

    dates = df["trade_date"]
    strategy_value = df["strategy_value"]
    buy_hold_value = df["buy_hold_value"]

    # 策略净值曲线
    ax.plot(dates, strategy_value, color="#e74c3c", linewidth=2.0, label="海龟策略净值 Strategy Value", zorder=3)

    # 买入持有净值曲线
    ax.plot(dates, buy_hold_value, color="#3498db", linewidth=2.0, linestyle="-", label="买入持有净值 Buy & Hold", zorder=2)

    # 基准线 (净值=1.0)
    ax.axhline(y=1.0, color="gray", linewidth=0.8, linestyle=":", alpha=0.6, label="基准线 (净值=1.0)")

    # 填充策略 vs 买入持有的差异区域
    ax.fill_between(dates, strategy_value, buy_hold_value,
                    where=strategy_value >= buy_hold_value,
                    alpha=0.15, color="#e74c3c", label="策略优于持有")
    ax.fill_between(dates, strategy_value, buy_hold_value,
                    where=strategy_value < buy_hold_value,
                    alpha=0.15, color="#3498db", label="策略劣于持有")

    # 标注最终净值
    final_sv = strategy_value.iloc[-1]
    final_bh = buy_hold_value.iloc[-1]
    last_date = dates.iloc[-1]

    ax.annotate(
        f"策略: {final_sv:.4f}\n({(final_sv-1)*100:+.2f}%)",
        xy=(last_date, final_sv),
        xytext=(20, 10), textcoords="offset points",
        fontsize=10, color="#e74c3c", fontweight="bold",
        arrowprops=dict(arrowstyle="->", color="#e74c3c", lw=1.5),
        bbox=dict(boxstyle="round,pad=0.3", facecolor="white", edgecolor="#e74c3c", alpha=0.9)
    )
    ax.annotate(
        f"持有: {final_bh:.4f}\n({(final_bh-1)*100:+.2f}%)",
        xy=(last_date, final_bh),
        xytext=(20, -30), textcoords="offset points",
        fontsize=10, color="#3498db", fontweight="bold",
        arrowprops=dict(arrowstyle="->", color="#3498db", lw=1.5),
        bbox=dict(boxstyle="round,pad=0.3", facecolor="white", edgecolor="#3498db", alpha=0.9)
    )

    # 标题和轴标签
    ax.set_title("海龟策略累计净值 vs 买入持有 — 招商银行 600036.SH", fontsize=16, fontweight="bold", pad=15)
    ax.set_xlabel("日期", fontsize=12)
    ax.set_ylabel("累计净值", fontsize=12)

    # 图例
    ax.legend(loc="upper left", fontsize=10, framealpha=0.9)

    # 网格
    ax.grid(True, alpha=0.3, linestyle="--")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
    fig.autofmt_xdate(rotation=30)

    ax.margins(x=0.02)
    plt.tight_layout()

    out_path = OUTPUT_DIR / "task4_fig2_turtle_equity.png"
    fig.savefig(out_path, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"✅ 图2 已保存: {out_path}")
    return out_path


# ════════════════════════════════════════════════════════════
# 图3: 回撤曲线图
# ════════════════════════════════════════════════════════════
def plot_fig3_drawdown(df):
    fig, ax = plt.subplots(figsize=(14, 6))

    dates = df["trade_date"]
    strategy_value = df["strategy_value"]

    # 计算回撤
    running_max = strategy_value.cummax()
    drawdown = strategy_value / running_max - 1

    # 回撤曲线（填充区域）
    ax.fill_between(dates, drawdown, 0, alpha=0.35, color="#e74c3c", label="策略回撤 Drawdown")
    ax.plot(dates, drawdown, color="#c0392b", linewidth=1.5, zorder=3)

    # 找最大回撤点
    mdd = drawdown.min()
    mdd_idx = drawdown.idxmin()
    mdd_date = dates.iloc[mdd_idx]
    mdd_peak_idx = strategy_value.iloc[:mdd_idx + 1].idxmax() if mdd_idx > 0 else 0
    mdd_peak_date = dates.iloc[mdd_peak_idx]

    # 标注最大回撤
    ax.scatter([mdd_date], [mdd], s=120, color="#e74c3c", edgecolors="white", linewidths=1.5, zorder=5)
    ax.annotate(
        f"最大回撤 MDD\n{mdd_date.strftime('%Y-%m-%d')}\n{mdd*100:.2f}%",
        xy=(mdd_date, mdd),
        xytext=(30, -30), textcoords="offset points",
        fontsize=11, color="#c0392b", fontweight="bold",
        arrowprops=dict(arrowstyle="->", color="#c0392b", lw=1.5),
        bbox=dict(boxstyle="round,pad=0.4", facecolor="#fff5f5", edgecolor="#c0392b", alpha=0.95)
    )

    # 标注回撤起点（峰值点）
    peak_val = strategy_value.iloc[mdd_peak_idx]
    ax.scatter([mdd_peak_date], [0], s=80, color="#f39c12", edgecolors="white", linewidths=1.2, marker="o", zorder=5)
    ax.annotate(
        f"峰值\n{mdd_peak_date.strftime('%Y-%m-%d')}\n净值={peak_val:.4f}",
        xy=(mdd_peak_date, 0),
        xytext=(20, 25), textcoords="offset points",
        fontsize=9, color="#f39c12", fontweight="bold",
        arrowprops=dict(arrowstyle="->", color="#f39c12", lw=1.2),
        bbox=dict(boxstyle="round,pad=0.3", facecolor="white", edgecolor="#f39c12", alpha=0.9)
    )

    # 基准线 (0%)
    ax.axhline(y=0, color="gray", linewidth=0.8, linestyle="-", alpha=0.5)

    # 标题和轴标签
    ax.set_title("海龟策略回撤曲线 — 招商银行 600036.SH", fontsize=16, fontweight="bold", pad=15)
    ax.set_xlabel("日期", fontsize=12)
    ax.set_ylabel("回撤幅度", fontsize=12)

    # Y轴格式化为百分比
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f"{y*100:.1f}%"))

    # 图例
    ax.legend(loc="lower left", fontsize=11, framealpha=0.9)

    # 网格
    ax.grid(True, alpha=0.3, linestyle="--")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
    fig.autofmt_xdate(rotation=30)

    ax.margins(x=0.02)
    plt.tight_layout()

    out_path = OUTPUT_DIR / "task4_fig3_turtle_drawdown.png"
    fig.savefig(out_path, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"✅ 图3 已保存: {out_path}")
    return out_path


# ════════════════════════════════════════════════════════════
# 主函数
# ════════════════════════════════════════════════════════════
def main():
    print("=" * 60)
    print("  TASK4 海龟策略回测图表生成")
    print("  招商银行 600036.SH")
    print("=" * 60)

    # 加载数据
    df = load_data()

    print()
    p1 = plot_fig1_signals(df)
    p2 = plot_fig2_equity(df)
    p3 = plot_fig3_drawdown(df)

    print()
    print("─" * 50)
    print("  📊 图表生成完成，共 3 张：")
    print(f"  图1: {p1}")
    print(f"  图2: {p2}")
    print(f"  图3: {p3}")
    print("─" * 50)


if __name__ == "__main__":
    main()
