#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
双均线交易策略回测
===================
股票: 招商银行 600036.SH
短期均线: MA5  (5日简单移动平均)
长期均线: MA15 (15日简单移动平均)
信号规则: MA5 上穿 MA15 → 金叉买入; MA5 下穿 MA15 → 死叉卖出
"""

import os
import sys
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')  # 非交互式后端，适合脚本运行
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import matplotlib.dates as mdates

# 中文字体设置 — Windows 优先 SimHei
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False  # 负号正常显示

# ============================================================
# 0. 配置参数
# ============================================================

DATA_FILE = os.path.join(os.path.dirname(__file__), "data", "cmb_2025_daily.csv")
SHORT_WINDOW = 5    # 短期均线窗口
LONG_WINDOW = 15    # 长期均线窗口
INITIAL_CAPITAL = 100_000.0  # 初始资金 (元)

# ============================================================
# 1. 读取数据
# ============================================================

def load_data(filepath: str) -> pd.DataFrame:
    """读取日线 CSV 数据并预处理"""
    if not os.path.exists(filepath):
        sys.exit(f"错误: 数据文件不存在 -> {filepath}")

    df = pd.read_csv(filepath)

    # 统一列名：有的 CSV 可能带 BOM 头
    df.columns = df.columns.str.replace('\ufeff', '', regex=False)

    # 检查必要列
    required = {'trade_date', 'close'}
    missing = required - set(df.columns)
    if missing:
        sys.exit(f"错误: 缺少必要列 -> {missing}")

    # 转换日期
    df['trade_date'] = pd.to_datetime(df['trade_date'], format='%Y-%m-%d')

    # 按日期从早到晚排序
    df = df.sort_values('trade_date', ignore_index=True)

    return df

# ============================================================
# 2. 指标计算
# ============================================================

def calc_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """计算 MA 均线、信号、持仓、收益率"""
    n = len(df)

    # --- 均线 ---
    df['ma_short'] = df['close'].rolling(window=SHORT_WINDOW).mean()
    df['ma_long']  = df['close'].rolling(window=LONG_WINDOW).mean()

    # --- 信号 ---
    # buy_signal:  MA5 从下方上穿 MA15 → True
    # sell_signal: MA5 从上方下穿 MA15 → True
    df['buy_signal']  = False
    df['sell_signal'] = False

    # 有效的均线行 (非 NaN)
    valid = df['ma_short'].notna() & df['ma_long'].notna()
    valid_idx = df.index[valid]

    for i in range(1, len(valid_idx)):
        idx_prev = valid_idx[i - 1]
        idx_curr = valid_idx[i]

        ma_s_prev = df.at[idx_prev, 'ma_short']
        ma_l_prev = df.at[idx_prev, 'ma_long']
        ma_s_curr = df.at[idx_curr, 'ma_short']
        ma_l_curr = df.at[idx_curr, 'ma_long']

        # 金叉: 短期均线从下方上穿长期均线
        if ma_s_prev <= ma_l_prev and ma_s_curr > ma_l_curr:
            df.at[idx_curr, 'buy_signal'] = True

        # 死叉: 短期均线从上方下穿长期均线
        if ma_s_prev >= ma_l_prev and ma_s_curr < ma_l_curr:
            df.at[idx_curr, 'sell_signal'] = True

    # --- 持仓 ---
    # 持仓列: 1=持有, 0=空仓
    # 买入信号 → 持有; 卖出信号 → 空仓; 无信号 → 延续上一日持仓
    df['position'] = 0
    holding = False

    for i in range(n):
        if df.at[i, 'buy_signal'] and not holding:
            holding = True
        elif df.at[i, 'sell_signal'] and holding:
            holding = False
        df.at[i, 'position'] = 1 if holding else 0

    # --- 每日收益率 ---
    # 1. 每日股票收益率
    df['daily_return'] = df['close'].pct_change()
    # 2. 每日策略收益率 (前一日持仓 × 当日股票收益，避免未来函数)
    df['strategy_return'] = df['daily_return'] * df['position'].shift(1).fillna(0)

    # --- 累计净值 ---
    # 3. 策略净值 (从 1 开始)
    df['strategy_value'] = (1 + df['strategy_return'].fillna(0)).cumprod()
    # 买入持有净值
    df['benchmark_value'] = (1 + df['daily_return'].fillna(0)).cumprod()

    # 4. 累计收益率 (净值 - 1)
    df['cum_strategy_return'] = df['strategy_value'] - 1
    df['cum_market_return']   = df['benchmark_value'] - 1

    # 5. 回撤 (基于策略净值)
    df['running_max'] = df['strategy_value'].cummax()
    df['drawdown']    = df['strategy_value'] / df['running_max'] - 1

    return df

# ============================================================
# 3. 回测统计
# ============================================================

def calc_statistics(df: pd.DataFrame) -> dict:
    """计算回测关键指标，返回数值型 dict（含格式化标签）"""
    # 有效交易区间 (均线计算完成之后)
    mask = df['ma_long'].notna()
    df_valid = df[mask].copy()

    # --- 4. 累计回报 ---
    total_return  = df_valid['strategy_value'].iloc[-1] - 1
    market_return = df_valid['benchmark_value'].iloc[-1] - 1
    excess_return = total_return - market_return

    # 交易次数
    buy_count  = int(df_valid['buy_signal'].sum())
    sell_count = int(df_valid['sell_signal'].sum())

    # 首次持有日之后的数据
    first_hold = df_valid[df_valid['position'] == 1]
    if len(first_hold) > 0:
        first_date = first_hold['trade_date'].iloc[0]
        df_held = df_valid[df_valid['trade_date'] >= first_date]
    else:
        df_held = df_valid

    # 胜率 (盈利交易日占比)
    win_days = (df_held['strategy_return'] > 0).sum()
    total_hold_days = (df_held['position'] == 1).sum()
    win_rate = win_days / total_hold_days if total_hold_days > 0 else 0

    # --- 5. 最大回撤 MDD ---
    max_drawdown = df_held['drawdown'].min()

    # 日收益率波动
    daily_return_mean = df_held['strategy_return'].mean()
    daily_vol = df_held['strategy_return'].std()
    annual_vol = daily_vol * np.sqrt(252)

    # 年化收益率
    trading_days = len(df_held)
    annual_return = (1 + total_return) ** (252 / max(trading_days, 1)) - 1

    # --- 6. 夏普比率 ---
    sharpe = annual_return / annual_vol if annual_vol > 0 else 0

    return {
        'strategy_total_return':   total_return,
        'market_total_return':     market_return,
        'excess_return':           excess_return,
        'annual_return':           annual_return,
        'annual_volatility':       annual_vol,
        'sharpe_ratio':            sharpe,
        'max_drawdown':            max_drawdown,
        'buy_signal_count':        buy_count,
        'sell_signal_count':       sell_count,
        'win_rate_daily':          win_rate,
        'start_date':              str(df_valid['trade_date'].iloc[0].date()),
        'end_date':                str(df_valid['trade_date'].iloc[-1].date()),
        'trading_days':            len(df_valid),
        'daily_return_mean':       daily_return_mean,
    }

# ============================================================
# 4. 输出结果
# ============================================================

def show_results(df: pd.DataFrame, stats: dict):
    """打印回测结果"""

    print("=" * 72)
    print("  招商银行 600036.SH — 双均线策略回测 (MA5 × MA15)")
    print("=" * 72)

    # 统计摘要
    print("\n【策略统计】")
    print(f"  初始资金　　　　　　　　: ¥{INITIAL_CAPITAL:,.0f}")
    print(f"  策略累计收益率　　　　　: {stats['strategy_total_return']:+.2%}")
    print(f"  买入持有收益率　　　　　: {stats['market_total_return']:+.2%}")
    print(f"  超额收益　　　　　　　　: {stats['excess_return']:+.2%}")
    print(f"  年化收益率　　　　　　　: {stats['annual_return']:+.2%}")
    print(f"  年化波动率　　　　　　　: {stats['annual_volatility']:+.2%}")
    print(f"  夏普比率　　　　　　　　: {stats['sharpe_ratio']:.2f}")
    print(f"  最大回撤　　　　　　　　: {stats['max_drawdown']:+.2%}")
    print(f"  买入信号数　　　　　　　: {stats['buy_signal_count']}")
    print(f"  卖出信号数　　　　　　　: {stats['sell_signal_count']}")
    print(f"  胜率(日)　　　　　　　 : {stats['win_rate_daily']:.2%}")
    print(f"  回测起始日　　　　　　　: {stats['start_date']}")
    print(f"  回测截止日　　　　　　　: {stats['end_date']}")
    print(f"  有效交易天数　　　　　　: {stats['trading_days']}")

    # 信号明细
    buy_df = df[df['buy_signal']][
        ['trade_date', 'close', 'ma_short', 'ma_long']
    ].copy()
    buy_df['trade_date'] = buy_df['trade_date'].dt.date
    buy_df['信号类型'] = '金叉买入'
    sell_df = df[df['sell_signal']][
        ['trade_date', 'close', 'ma_short', 'ma_long']
    ].copy()
    sell_df['trade_date'] = sell_df['trade_date'].dt.date
    sell_df['信号类型'] = '死叉卖出'
    signals_df = pd.concat([buy_df, sell_df], ignore_index=True)
    signals_df = signals_df.sort_values('trade_date', ignore_index=True)
    for c in ['close', 'ma_short', 'ma_long']:
        signals_df[c] = signals_df[c].round(2)
    signals_df = signals_df[['trade_date', 'close', 'ma_short', 'ma_long', '信号类型']]

    print(f"\n【交易信号明细】 共 {len(signals_df)} 条")
    print(signals_df.to_string(index=False))

    # 最近 15 行完整数据
    cols_show = ['trade_date', 'close', 'ma_short', 'ma_long', 'buy_signal',
                 'sell_signal', 'position', 'daily_return', 'strategy_return']
    tail_df = df[cols_show].tail(15).copy()
    tail_df['trade_date'] = tail_df['trade_date'].dt.date
    for c in ['close', 'ma_short', 'ma_long']:
        tail_df[c] = tail_df[c].round(2)
    for c in ['daily_return', 'strategy_return']:
        tail_df[c] = tail_df[c].apply(lambda x: f"{x:+.4%}" if pd.notna(x) else "—")

    print(f"\n【数据表末尾 15 行】")
    print(tail_df.to_string(index=False))

    return signals_df, tail_df

# ============================================================
# 4.5 保存指标到 CSV
# ============================================================

def save_metrics(stats: dict, out_dir: str):
    """将回测指标保存为 CSV 文件"""
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "ma5_ma15_metrics.csv")

    rows = [
        ('指标名称', '指标值'),
        ('初始资金',     f"¥{INITIAL_CAPITAL:,.0f}"),
        ('策略累计收益率', f"{stats['strategy_total_return']:+.6f}"),
        ('买入持有收益率', f"{stats['market_total_return']:+.6f}"),
        ('超额收益',      f"{stats['excess_return']:+.6f}"),
        ('年化收益率',    f"{stats['annual_return']:+.6f}"),
        ('年化波动率',    f"{stats['annual_volatility']:+.6f}"),
        ('夏普比率',      f"{stats['sharpe_ratio']:.4f}"),
        ('最大回撤',      f"{stats['max_drawdown']:+.6f}"),
        ('买入信号数',     str(stats['buy_signal_count'])),
        ('卖出信号数',     str(stats['sell_signal_count'])),
        ('胜率(日)',      f"{stats['win_rate_daily']:+.6f}"),
        ('回测起始日',     stats['start_date']),
        ('回测截止日',     stats['end_date']),
        ('有效交易天数',   str(stats['trading_days'])),
    ]

    metrics_df = pd.DataFrame(rows[1:], columns=rows[0])
    metrics_df.to_csv(out_path, index=False, encoding='utf-8-sig')
    print(f"\n回测指标已保存至: {out_path}")

# ============================================================
# 4.6 图表绘制
# ============================================================

def plot_ma_signals(df: pd.DataFrame, out_dir: str):
    """图1：收盘价 + MA 均线 + 买卖信号"""
    os.makedirs(out_dir, exist_ok=True)

    # 只画均线有效的区间
    df_plot = df[df['ma_long'].notna()].copy()

    # 确保日期为 datetime 类型，避免 main 中格式化后变成字符串
    df_plot['trade_date'] = pd.to_datetime(df_plot['trade_date'])

    buy_dates  = df_plot[df_plot['buy_signal']]['trade_date']
    buy_prices = df_plot[df_plot['buy_signal']]['close']
    sell_dates  = df_plot[df_plot['sell_signal']]['trade_date']
    sell_prices = df_plot[df_plot['sell_signal']]['close']

    fig, ax = plt.subplots(figsize=(14, 6))

    # 收盘价
    ax.plot(df_plot['trade_date'], df_plot['close'],
            color='#333333', linewidth=1.0, label='收盘价', zorder=2)

    # 均线
    ax.plot(df_plot['trade_date'], df_plot['ma_short'],
            color='#E67E22', linewidth=1.0, alpha=0.9, label=f'MA{SHORT_WINDOW}')
    ax.plot(df_plot['trade_date'], df_plot['ma_long'],
            color='#3498DB', linewidth=1.2, alpha=0.9, label=f'MA{LONG_WINDOW}')

    # 信号标记 — A股惯例：红涨(买) / 绿跌(卖)
    ax.scatter(buy_dates, buy_prices, marker='^', s=100, color='#C0392B',
               edgecolors='white', linewidths=0.6, zorder=5, label='买入信号')
    ax.scatter(sell_dates, sell_prices, marker='v', s=100, color='#27AE60',
               edgecolors='white', linewidths=0.6, zorder=5, label='卖出信号')

    # 标注
    ax.set_title('招商银行 600036.SH — MA5 / MA15 双均线交易信号', fontsize=15, fontweight='bold', pad=12)
    ax.set_xlabel('交易日期', fontsize=11)
    ax.set_ylabel('收盘价 (元)', fontsize=11)
    ax.legend(loc='upper left', fontsize=9, framealpha=0.9)
    ax.yaxis.set_major_formatter(mticker.FormatStrFormatter('%.0f'))

    # 网格
    ax.grid(True, linestyle='--', alpha=0.3)

    # 日期格式：每月 1 日，格式 2025-01
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=1))
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    fig.autofmt_xdate(rotation=30, ha='right')

    plt.tight_layout()
    out_path = os.path.join(out_dir, "fig1_ma_signals.png")
    fig.savefig(out_path, dpi=200, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    print(f"图1 已保存至: {out_path}")


def plot_strategy_value(df: pd.DataFrame, stats: dict, out_dir: str):
    """图2：策略累计净值 vs 买入持有净值"""
    os.makedirs(out_dir, exist_ok=True)

    df_plot = df[df['ma_long'].notna()].copy()

    # 确保日期为 datetime 类型，避免 main 中格式化后变成字符串
    df_plot['trade_date'] = pd.to_datetime(df_plot['trade_date'])
    dates = df_plot['trade_date']

    fig, ax = plt.subplots(figsize=(14, 6))

    # 策略净值
    ax.plot(dates, df_plot['strategy_value'], color='#C0392B', linewidth=1.5,
            label=f'策略净值 (累计收益 {stats["strategy_total_return"]:+.2%})')
    # 买入持有净值
    ax.plot(dates, df_plot['benchmark_value'], color='#7F8C8D', linewidth=1.2,
            linestyle='--', label=f'买入持有净值 (累计收益 {stats["market_total_return"]:+.2%})')
    # 基准线 1.0
    ax.axhline(y=1.0, color='black', linewidth=0.6, linestyle=':', alpha=0.4)

    # 标注
    ax.set_title('招商银行 600036.SH — 策略累计净值曲线 (MA5 / MA15)', fontsize=15, fontweight='bold', pad=12)
    ax.set_xlabel('交易日期', fontsize=11)
    ax.set_ylabel('累计净值', fontsize=11)
    ax.legend(loc='upper left', fontsize=9, framealpha=0.9)

    # 网格
    ax.grid(True, linestyle='--', alpha=0.3)

    # 日期格式：每月 1 日，格式 2025-01
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=1))
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    fig.autofmt_xdate(rotation=30, ha='right')

    plt.tight_layout()
    out_path = os.path.join(out_dir, "fig2_strategy_value.png")
    fig.savefig(out_path, dpi=200, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    print(f"图2 已保存至: {out_path}")

# ============================================================
# 5. 主入口
# ============================================================

def main():
    print("正在加载数据...")
    df = load_data(DATA_FILE)
    print(f"数据加载完成: {len(df)} 条记录, "
          f"{df['trade_date'].iloc[0].date()} ~ {df['trade_date'].iloc[-1].date()}")

    print(f"正在计算 MA{SHORT_WINDOW} / MA{LONG_WINDOW} 均线及交易信号...")
    df = calc_indicators(df)

    stats = calc_statistics(df)
    show_results(df, stats)

    # 保存完整回测结果到 CSV
    out_dir = os.path.join(os.path.dirname(__file__), "output")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "ma5_ma15_backtest_data.csv")
    df['trade_date'] = df['trade_date'].dt.strftime('%Y-%m-%d')
    df.to_csv(out_path, index=False, encoding='utf-8-sig')
    print(f"\n完整回测结果已保存至: {out_path}")

    # 保存回测指标到 CSV
    save_metrics(stats, out_dir)

    # 绘制图表
    print("\n正在生成图表...")
    plot_ma_signals(df, out_dir)
    plot_strategy_value(df, stats, out_dir)

if __name__ == '__main__':
    main()
