# -*- coding: utf-8 -*-
"""生成招商银行(600036.SH)近一年收盘价曲线图"""

import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.ticker import FuncFormatter
import numpy as np
import os

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'PingFang SC', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

# 读取数据
csv_path = os.path.join(os.path.dirname(__file__), 'cmb_daily.csv')
df = pd.read_csv(csv_path)
df['trade_date'] = pd.to_datetime(df['trade_date'], format='%Y%m%d')
df = df.sort_values('trade_date').reset_index(drop=True)

# 计算均线
df['MA5'] = df['close'].rolling(5).mean()
df['MA10'] = df['close'].rolling(10).mean()
df['MA20'] = df['close'].rolling(20).mean()
df['MA60'] = df['close'].rolling(60).mean()

# 计算涨跌颜色
df['color'] = np.where(df['close'] >= df['open'], '#e83939', '#19a55e')

# 统计
start_date = df['trade_date'].iloc[0].strftime('%Y-%m-%d')
end_date = df['trade_date'].iloc[-1].strftime('%Y-%m-%d')
start_close = df['close'].iloc[0]
end_close = df['close'].iloc[-1]
change_pct = (end_close - start_close) / start_close * 100
high_price = df['high'].max()
low_price = df['low'].min()
high_date = df.loc[df['high'].idxmax(), 'trade_date'].strftime('%Y-%m-%d')
low_date = df.loc[df['low'].idxmin(), 'trade_date'].strftime('%Y-%m-%d')
avg_vol = df['vol'].mean()

# 创建图表
fig, ax1 = plt.subplots(figsize=(20, 9), dpi=100)

# 背景色
fig.patch.set_facecolor('#fafbfc')
ax1.set_facecolor('#ffffff')

# 收盘价曲线和填充
ax1.fill_between(df['trade_date'], df['close'], df['close'].min() - 1,
                 alpha=0.08, color='#e83939')
ax1.plot(df['trade_date'], df['close'], color='#1a1a2e', linewidth=2.0,
         label='收盘价', zorder=5)

# 均线
ax1.plot(df['trade_date'], df['MA5'], color='#f5a623', linewidth=1.0,
         linestyle='-', label='MA5', alpha=0.8)
ax1.plot(df['trade_date'], df['MA10'], color='#4a90d9', linewidth=1.0,
         linestyle='-', label='MA10', alpha=0.8)
ax1.plot(df['trade_date'], df['MA20'], color='#9b59b6', linewidth=1.0,
         linestyle='-', label='MA20', alpha=0.8)
ax1.plot(df['trade_date'], df['MA60'], color='#e67e22', linewidth=1.0,
         linestyle='-', label='MA60', alpha=0.8)

# 标记最高点和最低点
ax1.annotate(f'最高: ¥{high_price:.2f}\n{high_date}',
             xy=(mdates.date2num(pd.Timestamp(high_date)), high_price),
             xytext=(0, 20), textcoords='offset points',
             fontsize=10, color='#e83939', fontweight='bold',
             ha='center',
             arrowprops=dict(arrowstyle='->', color='#e83939', lw=1.2))
ax1.annotate(f'最低: ¥{low_price:.2f}\n{low_date}',
             xy=(mdates.date2num(pd.Timestamp(low_date)), low_price),
             xytext=(0, -30), textcoords='offset points',
             fontsize=10, color='#19a55e', fontweight='bold',
             ha='center',
             arrowprops=dict(arrowstyle='->', color='#19a55e', lw=1.2))

# Y轴格式化
ax1.yaxis.set_major_formatter(FuncFormatter(lambda x, _: f'¥{x:.0f}'))
ax1.tick_params(axis='y', colors='#333')

# X轴格式化
ax1.xaxis.set_major_locator(mdates.MonthLocator())
ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
ax1.tick_params(axis='x', colors='#666', rotation=30)

# 网格
ax1.grid(True, alpha=0.3, linestyle='--', linewidth=0.5)

# 边框
for spine in ax1.spines.values():
    spine.set_edgecolor('#e0e0e0')
    spine.set_linewidth(0.8)

# 标题
title_text = f'招商银行 (600036.SH) 近一年每日收盘价走势\n{start_date} ~ {end_date}  |  区间涨跌: {change_pct:+.2f}%  |  交易日: {len(df)} 天'
ax1.set_title(title_text, fontsize=16, fontweight='bold', color='#1a1a2e', pad=18)

# 图例
legend = ax1.legend(loc='upper left', fontsize=10, framealpha=0.9,
                    edgecolor='#e0e0e0', ncol=5)
legend.get_frame().set_facecolor('#ffffff')

# 底部统计信息
stats_text = (f'起始收盘: ¥{start_close:.2f}  →  最新收盘: ¥{end_close:.2f}  |  '
              f'区间最高: ¥{high_price:.2f} ({high_date})  |  '
              f'区间最低: ¥{low_price:.2f} ({low_date})  |  '
              f'日均成交量: {avg_vol/10000:.0f} 万手')
fig.text(0.5, 0.01, stats_text, ha='center', fontsize=9, color='#888',
         transform=fig.transFigure)

plt.tight_layout(rect=[0, 0.04, 1, 1])

# 保存
output_path = os.path.join(os.path.dirname(__file__), 'cmb_close_price.png')
fig.savefig(output_path, dpi=150, bbox_inches='tight', facecolor=fig.get_facecolor())
plt.close(fig)

print(f'图表已保存至: {output_path}')
print(f'数据区间: {start_date} ~ {end_date}')
print(f'交易日数: {len(df)}')
print(f'起始收盘: ¥{start_close:.2f}')
print(f'最新收盘: ¥{end_close:.2f}')
print(f'区间涨跌: {change_pct:+.2f}%')
print(f'最高: ¥{high_price:.2f} ({high_date})')
print(f'最低: ¥{low_price:.2f} ({low_date})')
