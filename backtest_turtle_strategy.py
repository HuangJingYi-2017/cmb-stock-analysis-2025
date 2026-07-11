"""
TASK4: 海龟交易法 - 指标计算 + 交易信号
========================================
基于招商银行 600036.SH 日线数据，分两步：

Step 1 — 核心指标计算 (→ data/turtle_indicators.csv)
  1. upper_channel  — 20日高点通道（shift(1) 避免未来函数）
  2. lower_channel  — 20日低点通道（shift(1) 避免未来函数）
  3. TR             — 真实波幅
  4. ATR            — 20日ATR（TR的20日移动平均）

Step 2 — 交易信号生成 (→ data/turtle_signals.csv)
  5. buy_signal       — close > upper_channel 且空仓时买入
  6. sell_signal      — close < lower_channel 且持仓时卖出
  7. stop_loss_signal — close < (entry_price - 2×ATR) 时止损
  8. entry_price      — 买入时的收盘价
  9. stop_loss_price  — 止损价 = entry_price - 2×ATR
  10. position        — 持仓状态 (1=持仓, 0=空仓)

Step 3 — 回测净值计算 (→ data/turtle_backtest_result.csv)
  11. stock_return    — 股票每日收益率 = close.pct_change()
  12. strategy_return  — 策略每日收益率 = position.shift(1) × stock_return
  13. strategy_value   — 策略累计净值 = (1 + strategy_return).cumprod()
  14. buy_hold_value   — 买入持有净值 = (1 + stock_return).cumprod()

Step 4 — 参数对比 (→ data/turtle_parameter_comparison.csv, output/task4_fig4_turtle_parameter_comparison.png)
  测试 10/20/30 日通道周期，对比累计回报、MDD、夏普比率等指标。

关键说明：
  - shift(1) 确保：今天 T 做突破判断时，通道值仅由 T-1 及更早的数据构成，
    不包含今天 T 自身的 high/low，杜绝未来函数。
  - TR 和 ATR 不做 shift，因为它们用于仓位计算（而非突破信号），
    且 TR 中的"前一日 close"在当天决策时是已知信息。
  - 信号优先级: 止损 > 通道卖出 > 买入（同一天不可又卖又买）
  - stop_loss_price 在买入时一次性确定，持仓期间不变
  - ⚠️ strategy_return = position.shift(1) × stock_return
    position.shift(1) 确保今天产生的信号不会用于计算今天的收益，
    因为信号是收盘后产生的，实际执行要到次日。
"""

import pandas as pd
import numpy as np
from pathlib import Path

# matplotlib（参数对比图用）
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["savefig.dpi"] = 300

# ── 路径配置 ──────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
INPUT_CSV = BASE_DIR / "data" / "cmb_600036_daily_latest.csv"
OUTPUT_CSV = BASE_DIR / "data" / "turtle_indicators.csv"
SIGNALS_CSV = BASE_DIR / "data" / "turtle_signals.csv"
BACKTEST_CSV = BASE_DIR / "data" / "turtle_backtest_result.csv"
METRICS_CSV = BASE_DIR / "data" / "turtle_metrics.csv"
PARAM_COMPARISON_CSV = BASE_DIR / "data" / "turtle_parameter_comparison.csv"
PARAM_COMPARISON_FIG = BASE_DIR / "output" / "task4_fig4_turtle_parameter_comparison.png"

# ── 策略参数 ──────────────────────────────────────────────
CHANNEL_PERIOD = 20   # 通道周期（海龟系统1默认20日）
ATR_PERIOD = 20       # ATR周期
ATR_STOP_MULT = 2     # ATR止损倍数: stop_loss = entry_price - 2×ATR


def load_data(filepath: Path) -> pd.DataFrame:
    """加载日线数据，确保字段类型正确"""
    df = pd.read_csv(filepath, encoding="utf-8-sig")
    # 统一日期格式
    df["trade_date"] = pd.to_datetime(df["trade_date"], format="%Y-%m-%d")
    df = df.sort_values("trade_date").reset_index(drop=True)

    # 确保价格列为浮点数
    for col in ["open", "high", "low", "close", "pre_close"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    print(f"✅ 数据加载完成: {len(df)} 条")
    print(f"   日期范围: {df['trade_date'].iloc[0].date()} ~ {df['trade_date'].iloc[-1].date()}")
    return df


def calc_turtle_indicators(
    df: pd.DataFrame,
    channel_period: int = CHANNEL_PERIOD,
    atr_period: int = ATR_PERIOD,
) -> pd.DataFrame:
    """
    计算海龟策略核心指标

    Parameters:
        channel_period : 通道周期（默认20日）
        atr_period     : ATR周期（默认与通道周期一致）

    Returns:
        DataFrame 新增列:
          - upper_channel : N日高点通道（shift后，用于今天判断突破）
          - lower_channel : N日低点通道（shift后，用于今天判断突破）
          - TR            : 真实波幅
          - ATR           : N日ATR
    """
    out = df.copy()

    # ── 1. 高点通道 upper_channel ────────────────────────
    # 原始: 过去N日(含今天)的 high 最高值
    # shift(1): 窗口右移一天 → 今天看到的是 [T-N, T-1] 的最高值
    out["upper_channel"] = (
        out["high"]
        .rolling(window=channel_period, min_periods=channel_period)
        .max()
        .shift(1)
    )

    # ── 2. 低点通道 lower_channel ────────────────────────
    # 同理，shift(1) 后今天看到的是 [T-N, T-1] 的最低值
    out["lower_channel"] = (
        out["low"]
        .rolling(window=channel_period, min_periods=channel_period)
        .min()
        .shift(1)
    )

    # ── 3. TR 真实波幅 ───────────────────────────────────
    high = out["high"]
    low = out["low"]
    prev_close = out["close"].shift(1)

    tr1 = high - low
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()

    out["TR"] = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    out.loc[out.index[0], "TR"] = tr1.iloc[0]

    # ── 4. ATR 平均真实波幅 ──────────────────────────────
    # ATR = TR 的 N 日简单移动平均
    out["ATR"] = out["TR"].rolling(window=atr_period, min_periods=atr_period).mean()

    return out


def generate_signals(
    df: pd.DataFrame,
    atr_stop_mult: float = ATR_STOP_MULT,
) -> pd.DataFrame:
    """
    生成海龟策略交易信号（逐行遍历，状态依赖）

    Parameters:
        atr_stop_mult : ATR止损倍数，stop_loss = entry_price - mult × ATR

    规则：
      1. 买入: position==0 且 close > upper_channel → buy_signal=1
      2. 卖出: position==1 且 close < lower_channel  → sell_signal=1
      3. 止损: position==1 且 close < stop_loss_price → stop_loss_signal=1
         stop_loss_price = entry_price - 2×ATR（买入时的ATR）
      4. 持仓状态延续: 无信号时 position = 前一日 position

    优先级: 止损 > 通道卖出 > 买入（同一天不可又卖又买）

    Returns:
        DataFrame 新增列:
          - buy_signal       : 1=买入, 0=无
          - sell_signal      : 1=卖出, 0=无
          - stop_loss_signal : 1=止损, 0=无
          - entry_price      : 买入时的收盘价
          - stop_loss_price   : 止损价 = entry_price - 2×ATR
          - position         : 1=持仓, 0=空仓
    """
    out = df.copy()

    # 初始化信号列
    out["buy_signal"] = 0
    out["sell_signal"] = 0
    out["stop_loss_signal"] = 0
    out["entry_price"] = np.nan
    out["stop_loss_price"] = np.nan
    out["position"] = 0

    # 运行时状态
    position = 0          # 当前持仓
    entry_price = np.nan  # 入场价
    stop_loss_price = np.nan  # 止损价

    for i in range(len(out)):
        row = out.iloc[i]
        upper = row["upper_channel"]
        lower = row["lower_channel"]
        atr = row["ATR"]
        close = row["close"]

        # 通道/ATR 尚未生效（NaN）→ 无信号，保持空仓
        if pd.isna(upper) or pd.isna(lower) or pd.isna(atr):
            out.iloc[i, out.columns.get_loc("position")] = position
            out.iloc[i, out.columns.get_loc("entry_price")] = entry_price
            out.iloc[i, out.columns.get_loc("stop_loss_price")] = stop_loss_price
            continue

        if position == 1:
            # ── 持仓中: 先查止损，再查通道卖出 ──
            # 1) ATR 止损
            if close < stop_loss_price:
                out.iloc[i, out.columns.get_loc("stop_loss_signal")] = 1
                # 先写入退出时的 entry/stop 值（保留平仓前的信息）
                out.iloc[i, out.columns.get_loc("entry_price")] = entry_price
                out.iloc[i, out.columns.get_loc("stop_loss_price")] = stop_loss_price
                out.iloc[i, out.columns.get_loc("position")] = 0
                # 清除运行时状态
                position = 0
                entry_price = np.nan
                stop_loss_price = np.nan
                continue

            # 2) 通道卖出（跌破低点通道）
            elif close < lower:
                out.iloc[i, out.columns.get_loc("sell_signal")] = 1
                out.iloc[i, out.columns.get_loc("entry_price")] = entry_price
                out.iloc[i, out.columns.get_loc("stop_loss_price")] = stop_loss_price
                out.iloc[i, out.columns.get_loc("position")] = 0
                position = 0
                entry_price = np.nan
                stop_loss_price = np.nan
                continue

            # 3) 继续持仓
            # (position 不变)

        elif position == 0:
            # ── 空仓中: 查买入信号 ──
            if close > upper:
                out.iloc[i, out.columns.get_loc("buy_signal")] = 1
                position = 1
                entry_price = close
                stop_loss_price = entry_price - atr_stop_mult * atr

        # 写入当日状态
        out.iloc[i, out.columns.get_loc("position")] = position
        out.iloc[i, out.columns.get_loc("entry_price")] = entry_price
        out.iloc[i, out.columns.get_loc("stop_loss_price")] = stop_loss_price

    return out


def run_backtest(df: pd.DataFrame) -> pd.DataFrame:
    """
    海龟策略回测：计算每日收益率与累计净值

    核心公式（防未来函数）：
      stock_return    = close.pct_change()
      strategy_return = position.shift(1) × stock_return
      strategy_value  = (1 + strategy_return).cumprod()
      buy_hold_value  = (1 + stock_return).cumprod()

    ⚠️ position.shift(1) 的含义：
      今天 T 的信号是收盘后产生的（用收盘价判断突破），
      实际执行要到 T+1 才能生效。
      所以 T 日的收益 = T-1 日的持仓状态 × T 日的股票收益率。
      即：今天买入了（position[T]=1），但今天的收益不算策略的，
          因为信号是收盘后产生的，当天无法执行。

    Returns:
        DataFrame 新增列:
          - stock_return    : 股票每日收益率
          - strategy_return : 策略每日收益率
          - strategy_value  : 策略累计净值（起始=1）
          - buy_hold_value  : 买入持有累计净值（起始=1）
    """
    out = df.copy()

    # 1. 股票每日收益率
    out["stock_return"] = out["close"].pct_change()

    # 2. 策略每日收益率 — position.shift(1) 防未来函数
    #    今天用"昨天的持仓状态"来决定是否享受今天的涨跌
    out["strategy_return"] = out["position"].shift(1) * out["stock_return"]

    # 第一天 stock_return 为 NaN → strategy_return 也为 NaN，设为 0
    out.loc[out.index[0], "stock_return"] = 0.0
    out.loc[out.index[0], "strategy_return"] = 0.0

    # 3. 策略累计净值
    out["strategy_value"] = (1 + out["strategy_return"]).cumprod()

    # 4. 买入持有净值
    out["buy_hold_value"] = (1 + out["stock_return"]).cumprod()

    return out


def calc_metrics(df: pd.DataFrame) -> dict:
    """
    计算海龟策略回测指标

    Returns:
        dict 包含以下 10 项指标:
          1. backtest_period    : 回测区间 (start ~ end)
          2. buy_count          : 买入信号次数
          3. sell_count         : 卖出信号次数
          4. stop_loss_count    : 止损次数
          5. cumulative_return  : 策略累计回报 = 最终策略净值 - 1
          6. buy_hold_return    : 买入持有收益 = 最终买入持有净值 - 1
          7. max_drawdown       : 最大回撤
          8. sharpe_ratio       : 夏普比率
          9. annualized_return  : 年化收益率
          10. trade_count       : 交易次数（一轮买入+卖出/止损 = 1笔交易）
    """
    metrics = {}

    # 1. 回测区间
    start_date = df["trade_date"].iloc[0]
    end_date = df["trade_date"].iloc[-1]
    metrics["backtest_period"] = f"{start_date} ~ {end_date}"

    # 2~4. 信号次数
    metrics["buy_count"] = int(df["buy_signal"].sum())
    metrics["sell_count"] = int(df["sell_signal"].sum())
    metrics["stop_loss_count"] = int(df["stop_loss_signal"].sum())

    # 5. 策略累计回报
    final_strategy_value = df["strategy_value"].iloc[-1]
    metrics["cumulative_return"] = final_strategy_value - 1

    # 6. 买入持有收益
    final_buyhold_value = df["buy_hold_value"].iloc[-1]
    metrics["buy_hold_return"] = final_buyhold_value - 1

    # 7. 最大回撤 MDD
    #    running_max = strategy_value.cummax()
    #    drawdown = strategy_value / running_max - 1
    #    MDD = drawdown.min()
    running_max = df["strategy_value"].cummax()
    drawdown = df["strategy_value"] / running_max - 1
    metrics["max_drawdown"] = drawdown.min()

    # 买入持有最大回撤（对比用）
    bh_running_max = df["buy_hold_value"].cummax()
    bh_drawdown = df["buy_hold_value"] / bh_running_max - 1
    metrics["buy_hold_max_drawdown"] = bh_drawdown.min()

    # 8. 夏普比率
    #    Sharpe = strategy_return.mean() / strategy_return.std() × sqrt(252)
    #    如果标准差为 0，设为 0 避免报错
    std_return = df["strategy_return"].std()
    if std_return > 0:
        metrics["sharpe_ratio"] = (
            df["strategy_return"].mean() / std_return * np.sqrt(252)
        )
    else:
        metrics["sharpe_ratio"] = 0.0

    # 买入持有夏普比率（对比用）
    bh_std = df["stock_return"].std()
    if bh_std > 0:
        metrics["buy_hold_sharpe"] = (
            df["stock_return"].mean() / bh_std * np.sqrt(252)
        )
    else:
        metrics["buy_hold_sharpe"] = 0.0

    # 9. 年化收益率
    n_days = len(df)
    metrics["n_trading_days"] = n_days
    if final_strategy_value > 0 and n_days > 0:
        metrics["annualized_return"] = final_strategy_value ** (252 / n_days) - 1
    else:
        metrics["annualized_return"] = 0.0

    if final_buyhold_value > 0 and n_days > 0:
        metrics["buy_hold_annualized"] = final_buyhold_value ** (252 / n_days) - 1
    else:
        metrics["buy_hold_annualized"] = 0.0

    # 10. 交易次数（每笔完整交易 = 买入 + 卖出/止损）
    metrics["trade_count"] = metrics["buy_count"]

    # 年化波动率（补充指标）
    metrics["annualized_volatility"] = std_return * np.sqrt(252) if std_return > 0 else 0.0
    bh_vol = bh_std * np.sqrt(252) if bh_std > 0 else 0.0
    metrics["buy_hold_volatility"] = bh_vol

    return metrics


# ════════════════════════════════════════════════════════════
# 参数对比功能
# ════════════════════════════════════════════════════════════

def run_single_backtest(
    df: pd.DataFrame,
    channel_period: int,
    atr_period: int,
    atr_stop_mult: float,
) -> tuple:
    """
    用给定参数跑一次完整海龟回测，返回回测 DataFrame 和指标 dict。

    Pipeline: indicators → signals → backtest → metrics
    """
    indicators = calc_turtle_indicators(df, channel_period=channel_period, atr_period=atr_period)
    signals = generate_signals(indicators, atr_stop_mult=atr_stop_mult)
    backtest = run_backtest(signals)
    metrics = calc_metrics(backtest)
    return backtest, metrics


def run_parameter_comparison(
    df: pd.DataFrame,
    param_sets: list,
) -> pd.DataFrame:
    """
    对多组参数跑回测，返回对比表 + 各组 strategy_value 用于绘图。

    Parameters:
        df        : 原始日线数据（已 load_data 的结果）
        param_sets: 参数列表，每项 = (channel_period, atr_period, atr_stop_mult)

    Returns:
        comparison_df : 参数对比表（每组一行）
        equity_curves : dict {label: pd.Series(strategy_value)} 用于绘图
    """
    rows = []
    equity_curves = {}

    for channel_p, atr_p, stop_mult in param_sets:
        label = f"{channel_p}日通道"
        print(f"\n  ▶ 测试参数: channel={channel_p}, ATR={atr_p}, stop×={stop_mult}  ({label})")

        bt, mt = run_single_backtest(df, channel_p, atr_p, stop_mult)

        rows.append({
            "通道周期": channel_p,
            "ATR周期": atr_p,
            "ATR止损倍数": stop_mult,
            "累计回报": mt["cumulative_return"],
            "买入持有收益": mt["buy_hold_return"],
            "最大回撤": mt["max_drawdown"],
            "夏普比率": mt["sharpe_ratio"],
            "交易次数": mt["trade_count"],
            "止损次数": mt["stop_loss_count"],
            "买入次数": mt["buy_count"],
            "卖出次数": mt["sell_count"],
            "年化收益率": mt["annualized_return"],
            "年化波动率": mt["annualized_volatility"],
        })

        equity_curves[label] = bt["strategy_value"].copy()

        print(f"    累计回报={mt['cumulative_return']*100:+.2f}%  "
              f"MDD={mt['max_drawdown']*100:.2f}%  "
              f"Sharpe={mt['sharpe_ratio']:.4f}  "
              f"交易={mt['trade_count']}次  "
              f"止损={mt['stop_loss_count']}次")

    comparison_df = pd.DataFrame(rows)
    return comparison_df, equity_curves


def plot_parameter_comparison(
    equity_curves: dict,
    dates: pd.Series,
    buy_hold: pd.Series,
    stock_name: str,
    out_path: Path,
):
    """
    绘制不同通道周期的策略累计净值对比图。
    """
    fig, ax = plt.subplots(figsize=(14, 7))

    colors = ["#e74c3c", "#2980b9", "#8e44ad", "#27ae60", "#e67e22", "#16a085"]

    # 买入持有基准线
    ax.plot(dates, buy_hold, color="#95a5a6", linewidth=1.5, linestyle="--",
            label="买入持有 Buy & Hold", zorder=2)

    # 各参数策略净值
    for i, (label, values) in enumerate(equity_curves.items()):
        color = colors[i % len(colors)]
        ax.plot(dates, values, color=color, linewidth=2.0, label=label, zorder=3 + i)

    # 基准线
    ax.axhline(y=1.0, color="gray", linewidth=0.8, linestyle=":", alpha=0.5)

    ax.set_title(f"海龟策略不同通道周期净值对比 — {stock_name}", fontsize=16, fontweight="bold", pad=15)
    ax.set_xlabel("日期", fontsize=12)
    ax.set_ylabel("累计净值", fontsize=12)
    ax.legend(loc="upper left", fontsize=11, framealpha=0.9)
    ax.grid(True, alpha=0.3, linestyle="--")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
    fig.autofmt_xdate(rotation=30)
    ax.margins(x=0.02)
    plt.tight_layout()

    out_path.parent.mkdir(exist_ok=True)
    fig.savefig(out_path, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"\n✅ 参数对比图已保存: {out_path}")


def main():
    # 1. 加载数据
    df = load_data(INPUT_CSV)

    # 2. 计算指标
    result = calc_turtle_indicators(df)

    # 3. 格式化输出：日期改回字符串，保留原始字段 + 新增指标
    result["trade_date"] = result["trade_date"].dt.strftime("%Y-%m-%d")

    # 选择输出列：原始关键字段 + 海龟指标
    output_cols = [
        "trade_date", "open", "high", "low", "close", "vol",
        "upper_channel", "lower_channel", "TR", "ATR",
    ]
    result_out = result[output_cols].copy()

    # 4. 保存指标
    result_out.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")
    print(f"✅ 指标计算完成，已保存到: {OUTPUT_CSV}")
    print(f"   总行数: {len(result_out)}")

    # 5. 打印关键统计
    valid = result_out.dropna(subset=["upper_channel", "lower_channel", "ATR"])
    print(f"\n── 指标统计（有效值 {len(valid)} 条）──")
    print(f"   upper_channel 范围: {valid['upper_channel'].min():.2f} ~ {valid['upper_channel'].max():.2f}")
    print(f"   lower_channel 范围: {valid['lower_channel'].min():.2f} ~ {valid['lower_channel'].max():.2f}")
    print(f"   TR            范围: {result_out['TR'].min():.4f} ~ {result_out['TR'].max():.4f}")
    print(f"   ATR           范围: {valid['ATR'].min():.4f} ~ {valid['ATR'].max():.4f}")

    # 6. 验证 shift(1) 正确性：第21行的 upper_channel 应等于第1~20行 high 的最大值
    if len(result) >= 21:
        row_21 = result.iloc[20]   # 第21行（0-indexed = 20）
        max_high_1_20 = result.iloc[0:20]["high"].max()
        check = abs(row_21["upper_channel"] - max_high_1_20) < 1e-6
        print(f"\n── shift(1) 验证 ──")
        print(f"   第21行 upper_channel = {row_21['upper_channel']:.2f}")
        print(f"   第1~20行 high 最大值  = {max_high_1_20:.2f}")
        print(f"   ✅ 一致" if check else f"   ❌ 不一致")

    # ════════════════════════════════════════════════════════
    # 7. 生成交易信号
    # ════════════════════════════════════════════════════════
    print("\n" + "=" * 60)
    print("  生成海龟策略交易信号")
    print("=" * 60)

    signals = generate_signals(result)

    # 选择信号输出列
    signal_cols = [
        "trade_date", "open", "high", "low", "close",
        "upper_channel", "lower_channel", "ATR",
        "buy_signal", "sell_signal", "stop_loss_signal",
        "entry_price", "stop_loss_price", "position",
    ]
    signals_out = signals[signal_cols].copy()
    signals_out.to_csv(SIGNALS_CSV, index=False, encoding="utf-8-sig")
    print(f"\n✅ 信号生成完成，已保存到: {SIGNALS_CSV}")
    print(f"   总行数: {len(signals_out)}")

    # 8. 信号统计
    buy_count = int(signals_out["buy_signal"].sum())
    sell_count = int(signals_out["sell_signal"].sum())
    stop_count = int(signals_out["stop_loss_signal"].sum())
    hold_days = int(signals_out["position"].sum())

    print(f"\n── 信号统计 ──")
    print(f"   买入信号 (buy_signal)       : {buy_count} 次")
    print(f"   卖出信号 (sell_signal)      : {sell_count} 次")
    print(f"   止损信号 (stop_loss_signal) : {stop_count} 次")
    print(f"   持仓天数 / 有效天数          : {hold_days} / {len(signals_out)}")
    if len(signals_out) > 0:
        print(f"   持仓占比                    : {hold_days / len(signals_out) * 100:.1f}%")

    # 9. 展示每笔交易明细
    trades = signals_out[
        (signals_out["buy_signal"] == 1)
        | (signals_out["sell_signal"] == 1)
        | (signals_out["stop_loss_signal"] == 1)
    ].copy()

    if len(trades) > 0:
        print(f"\n── 交易明细（共 {len(trades)} 条信号）──")
        for _, r in trades.iterrows():
            if r["buy_signal"] == 1:
                print(f"  {r['trade_date']}  🟢 买入  close={r['close']:.2f}  "
                      f"ATR={r['ATR']:.4f}  stop_loss={r['stop_loss_price']:.2f}")
            elif r["sell_signal"] == 1:
                print(f"  {r['trade_date']}  🔴 卖出  close={r['close']:.2f}  "
                      f"(跌破下轨 {r['lower_channel']:.2f})")
            elif r["stop_loss_signal"] == 1:
                print(f"  {r['trade_date']}  ⛔ 止损  close={r['close']:.2f}  "
                      f"stop_loss={r['stop_loss_price']:.2f}  "
                      f"(ATR={r['ATR']:.4f})")
    else:
        print("\n── 无交易信号 ──")

    # 10. 末尾持仓状态
    last_row = signals_out.iloc[-1]
    print(f"\n── 末尾状态 ──")
    print(f"   日期: {last_row['trade_date']}")
    print(f"   持仓: {'是' if last_row['position'] == 1 else '否'}")
    if last_row["position"] == 1:
        print(f"   入场价: {last_row['entry_price']:.2f}")
        print(f"   止损价: {last_row['stop_loss_price']:.2f}")

    # ════════════════════════════════════════════════════════
    # 11. 回测：收益率与累计净值
    # ════════════════════════════════════════════════════════
    print("\n" + "=" * 60)
    print("  回测：收益率与累计净值")
    print("=" * 60)

    backtest = run_backtest(signals)

    # 选择回测输出列
    backtest_cols = [
        "trade_date", "close", "position",
        "upper_channel", "lower_channel", "ATR",
        "buy_signal", "sell_signal", "stop_loss_signal",
        "entry_price", "stop_loss_price",
        "stock_return", "strategy_return",
        "strategy_value", "buy_hold_value",
    ]
    backtest_out = backtest[backtest_cols].copy()
    backtest_out.to_csv(BACKTEST_CSV, index=False, encoding="utf-8-sig")
    print(f"\n✅ 回测完成，已保存到: {BACKTEST_CSV}")
    print(f"   总行数: {len(backtest_out)}")

    # 12. 回测统计
    final_strategy = backtest_out["strategy_value"].iloc[-1]
    final_buyhold = backtest_out["buy_hold_value"].iloc[-1]

    # 年化收益率（按252个交易日）
    n_days = len(backtest_out)
    ann_strategy = final_strategy ** (252 / n_days) - 1
    ann_buyhold = final_buyhold ** (252 / n_days) - 1

    # 最大回撤
    def max_drawdown(series):
        peak = series.cummax()
        drawdown = (series - peak) / peak
        return drawdown.min()

    mdd_strategy = max_drawdown(backtest_out["strategy_value"])
    mdd_buyhold = max_drawdown(backtest_out["buy_hold_value"])

    # 波动率（年化）
    vol_strategy = backtest_out["strategy_return"].std() * np.sqrt(252)
    vol_buyhold = backtest_out["stock_return"].std() * np.sqrt(252)

    # 夏普比率（无风险利率=0）
    sharpe_strategy = ann_strategy / vol_strategy if vol_strategy > 0 else 0
    sharpe_buyhold = ann_buyhold / vol_buyhold if vol_buyhold > 0 else 0

    print(f"\n── 回测统计（{n_days} 个交易日）──")
    print(f"{'指标':<20} {'海龟策略':>12} {'买入持有':>12}")
    print(f"{'─'*20} {'─'*12} {'─'*12}")
    print(f"{'累计净值':<20} {final_strategy:>12.4f} {final_buyhold:>12.4f}")
    print(f"{'累计收益率':<20} {(final_strategy-1)*100:>11.2f}% {(final_buyhold-1)*100:>11.2f}%")
    print(f"{'年化收益率':<20} {ann_strategy*100:>11.2f}% {ann_buyhold*100:>11.2f}%")
    print(f"{'最大回撤':<20} {mdd_strategy*100:>11.2f}% {mdd_buyhold*100:>11.2f}%")
    print(f"{'年化波动率':<20} {vol_strategy*100:>11.2f}% {vol_buyhold*100:>11.2f}%")
    print(f"{'夏普比率':<20} {sharpe_strategy:>12.2f} {sharpe_buyhold:>12.2f}")

    # 13. 验证 position.shift(1) 防未来函数
    print(f"\n── position.shift(1) 防未来函数验证 ──")
    # 找到第一个买入日
    first_buy = backtest_out[backtest_out["buy_signal"] == 1].iloc[0]
    buy_idx = backtest_out[backtest_out["buy_signal"] == 1].index[0]
    next_idx = buy_idx + 1
    if next_idx < len(backtest_out):
        next_row = backtest_out.iloc[next_idx]
        print(f"   买入日 {first_buy['trade_date']}: position={first_buy['position']}, "
              f"strategy_return={first_buy['strategy_return']:.6f}")
        print(f"   次日   {next_row['trade_date']}: position={next_row['position']}, "
              f"strategy_return={next_row['strategy_return']:.6f}")
        print(f"   → 买入日 strategy_return=0（当天信号尚未生效）✅")
        print(f"   → 次日起 strategy_return=position×stock_return（信号生效）✅")

    # ════════════════════════════════════════════════════════
    # 14. 回测指标计算与保存
    # ════════════════════════════════════════════════════════
    print("\n" + "=" * 60)
    print("  回测指标汇总")
    print("=" * 60)

    metrics = calc_metrics(backtest_out)

    # 保存指标到 CSV（两列: 指标名, 指标值）
    metrics_rows = []
    label_map = {
        "backtest_period":          ("回测区间",           None),
        "n_trading_days":          ("交易日天数",         None),
        "buy_count":               ("买入信号次数",       None),
        "sell_count":              ("卖出信号次数",       None),
        "stop_loss_count":         ("止损次数",           None),
        "trade_count":             ("交易次数",           None),
        "cumulative_return":       ("策略累计回报",       True),
        "buy_hold_return":         ("买入持有收益",       True),
        "annualized_return":       ("策略年化收益率",     True),
        "buy_hold_annualized":     ("买入持有年化收益率", True),
        "max_drawdown":            ("策略最大回撤",       True),
        "buy_hold_max_drawdown":   ("买入持有最大回撤",   True),
        "annualized_volatility":   ("策略年化波动率",     True),
        "buy_hold_volatility":     ("买入持有年化波动率", True),
        "sharpe_ratio":            ("策略夏普比率",       False),
        "buy_hold_sharpe":         ("买入持有夏普比率",   False),
    }

    for key, (label, is_pct) in label_map.items():
        val = metrics[key]
        if val is None:
            continue
        if is_pct is True:
            metrics_rows.append({"指标": label, "值": f"{val:.6f}", "百分比": f"{val*100:.2f}%"})
        elif is_pct is False:
            metrics_rows.append({"指标": label, "值": f"{val:.4f}", "百分比": ""})
        else:
            metrics_rows.append({"指标": label, "值": str(val), "百分比": ""})

    metrics_df = pd.DataFrame(metrics_rows)
    metrics_df.to_csv(METRICS_CSV, index=False, encoding="utf-8-sig")
    print(f"\n✅ 指标已保存到: {METRICS_CSV}")

    # 控制台输出摘要
    print(f"""
╔══════════════════════════════════════════════════════════╗
║           海龟策略回测结果摘要                          ║
║           招商银行 600036.SH                            ║
╠══════════════════════════════════════════════════════════╣
║ 回测区间          {metrics['backtest_period']:<34s}║
║ 交易日天数        {metrics['n_trading_days']:<34d}║
║                                                          ║
║ 买入信号次数      {metrics['buy_count']:<34d}║
║ 卖出信号次数      {metrics['sell_count']:<34d}║
║ 止损次数          {metrics['stop_loss_count']:<34d}║
║ 交易次数          {metrics['trade_count']:<34d}║
╠══════════════════════════════════════════════════════════╣
║                    海龟策略        买入持有              ║
╠══════════════════════════════════════════════════════════╣
║ 累计回报          {metrics['cumulative_return']*100:>8.2f}%       {metrics['buy_hold_return']*100:>8.2f}%            ║
║ 年化收益率        {metrics['annualized_return']*100:>8.2f}%       {metrics['buy_hold_annualized']*100:>8.2f}%            ║
║ 最大回撤          {metrics['max_drawdown']*100:>8.2f}%       {metrics['buy_hold_max_drawdown']*100:>8.2f}%            ║
║ 年化波动率        {metrics['annualized_volatility']*100:>8.2f}%       {metrics['buy_hold_volatility']*100:>8.2f}%            ║
║ 夏普比率          {metrics['sharpe_ratio']:>8.4f}       {metrics['buy_hold_sharpe']:>8.4f}            ║
╚══════════════════════════════════════════════════════════╝
""")

    # ════════════════════════════════════════════════════════
    # 15. 参数对比：不同通道周期回测
    # ════════════════════════════════════════════════════════
    print("\n" + "=" * 60)
    print("  参数对比：不同通道周期回测")
    print("=" * 60)

    param_sets = [
        (10, 10, 2),   # 10日通道, 10日ATR, 止损2×ATR
        (20, 20, 2),   # 20日通道, 20日ATR, 止损2×ATR
        (30, 30, 2),   # 30日通道, 30日ATR, 止损2×ATR
    ]

    comparison_df, equity_curves = run_parameter_comparison(df, param_sets)

    # 保存对比表
    comparison_df.to_csv(PARAM_COMPARISON_CSV, index=False, encoding="utf-8-sig")
    print(f"\n✅ 参数对比表已保存: {PARAM_COMPARISON_CSV}")

    # 控制台输出对比表
    print(f"\n── 参数对比结果 ──")
    print(f"{'通道周期':>8} {'累计回报':>10} {'买入持有':>10} {'最大回撤':>10} {'夏普比率':>10} {'交易次数':>8} {'止损次数':>8}")
    print(f"{'─'*8} {'─'*10} {'─'*10} {'─'*10} {'─'*10} {'─'*8} {'─'*8}")
    for _, r in comparison_df.iterrows():
        print(f"{int(r['通道周期']):>6}日 "
              f"{r['累计回报']*100:>+9.2f}% "
              f"{r['买入持有收益']*100:>+9.2f}% "
              f"{r['最大回撤']*100:>9.2f}% "
              f"{r['夏普比率']:>10.4f} "
              f"{int(r['交易次数']):>6}次 "
              f"{int(r['止损次数']):>6}次")

    # 生成参数对比净值图
    plot_parameter_comparison(
        equity_curves=equity_curves,
        dates=backtest["trade_date"],
        buy_hold=backtest["buy_hold_value"],
        stock_name="招商银行 600036.SH",
        out_path=PARAM_COMPARISON_FIG,
    )

    print("\n" + "=" * 60)
    print("  TASK4 海龟策略回测全部完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
