import json

# Build notebook cells
cells = []

def md(source):
    cells.append({
        "cell_type": "markdown",
        "metadata": {},
        "source": [line + "\n" if not line.startswith("#") else line + "\n" for line in source.strip().split("\n")]
    })

def code(source):
    cells.append({
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": source.strip().split("\n")
    })

# ====== Cell 0: Title ======
md("""# 招商银行 (600036.SH) 近一年交易数据分析
## K线图 & 成交量 & 收盘价曲线

**数据来源**: Tushare Pro  
**时间区间**: 2025-07-03 ~ 2026-07-03  
**交易日数**: 243 天  

本 Notebook 演示完整流程：数据获取 → 本地存储 → 可视化分析""")

# ====== Cell 1: Setup ======
md("""## 1. 环境准备""")

code("""# 导入所需库
import tushare as ts
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.patches import Rectangle
import json
import os

# 设置中文字体（Windows 用 SimHei，Mac 用 Arial Unicode MS）
plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

print("环境准备完成！")""")

# ====== Cell 2: Get data from Tushare ======
md("""## 2. 从 Tushare 获取数据

使用 Tushare Pro API 获取招商银行近一年（2025-07-03 至 2026-07-03）的日线行情数据。""")

code("""# Tushare Pro 配置（需要替换为你自己的 token）
# 免费注册: https://tushare.pro
TOKEN = '你的TushareToken'

# 方法一：通过 Tushare Python SDK
# pro = ts.pro_api(TOKEN)
# df = pro.daily(ts_code='600036.SH', start_date='20250703', end_date='20260703')
# df = df.sort_values('trade_date')

# 方法二：加载本地已保存的数据（本次演示使用）
DATA_FILE = 'cmb_daily.json'
with open(DATA_FILE, 'r', encoding='utf-8') as f:
    data = json.load(f)

df = pd.DataFrame(data)
df['trade_date'] = pd.to_datetime(df['trade_date'])
df = df.sort_values('trade_date').reset_index(drop=True)

print(f"数据获取成功！")
print(f"数据条目: {len(df)} 条")
print(f"时间区间: {df['trade_date'].min().strftime('%Y-%m-%d')} ~ {df['trade_date'].max().strftime('%Y-%m-%d')}")
print(f"\\n数据预览:")
df.head(10)""")

# ====== Cell 3: Data Overview ======
md("""## 3. 数据概览""")

code("""# 基本统计
print("=" * 50)
print("招商银行 (600036.SH) 近一年数据统计")
print("=" * 50)
print(f"起始收盘价: {df.iloc[0]['close']:.2f}")
print(f"最新收盘价: {df.iloc[-1]['close']:.2f}")
pct = (df.iloc[-1]['close'] - df.iloc[0]['close']) / df.iloc[0]['close'] * 100
print(f"区间涨跌幅: {pct:+.2f}%")
print(f"最高价: {df['high'].max():.2f} (日期: {df.loc[df['high'].idxmax(), 'trade_date'].strftime('%Y-%m-%d')})")
print(f"最低价: {df['low'].min():.2f} (日期: {df.loc[df['low'].idxmin(), 'trade_date'].strftime('%Y-%m-%d')})")
print(f"日均成交量: {df['vol'].mean():.0f} 手")
print(f"最大成交量: {df['vol'].max():.0f} 手 (日期: {df.loc[df['vol'].idxmax(), 'trade_date'].strftime('%Y-%m-%d')})")

# 数据描述
print(f"\\n描述统计:")
df[['open', 'high', 'low', 'close', 'vol', 'amount']].describe()""")

# ====== Cell 4: Store Data ======
md("""## 4. 本地存储""")

code("""# 保存为 CSV
df.to_csv('cmb_daily.csv', index=False, encoding='utf-8-sig')
print("已保存: cmb_daily.csv")

# 保存为 JSON
records = df.to_dict('records')
# 将 datetime 转为字符串
for r in records:
    r['trade_date'] = r['trade_date'].strftime('%Y%m%d')
with open('cmb_daily.json', 'w', encoding='utf-8') as f:
    json.dump(records, f, ensure_ascii=False, indent=2)
print("已保存: cmb_daily.json")""")

# ====== Cell 5: Close Price Curve ======
md("""## 5. 每日收盘价曲线图""")

code("""# 绘制收盘价曲线
fig, ax = plt.subplots(figsize=(16, 6))

dates = df['trade_date']
close_prices = df['close']

# 根据涨跌着色
colors = ['#e83939' if close_prices.iloc[i] >= close_prices.iloc[i-1] else '#19a55e' 
          for i in range(1, len(close_prices))]
colors = ['#e83939'] + colors  # 第一天默认红色

ax.plot(dates, close_prices, color='#333', linewidth=1.2, alpha=0.8, zorder=2)

# 填充区域渐变
ax.fill_between(dates, close_prices, close_prices.min() * 0.98, 
                alpha=0.08, color='#e83939')

# 标注最高最低
max_idx = close_prices.idxmax()
min_idx = close_prices.idxmin()
ax.annotate(f'最高 ¥{close_prices[max_idx]:.2f}', 
            xy=(dates[max_idx], close_prices[max_idx]),
            xytext=(dates[max_idx], close_prices[max_idx] + 2),
            fontsize=11, color='#e83939', fontweight='bold',
            arrowprops=dict(arrowstyle='->', color='#e83939'))
ax.annotate(f'最低 ¥{close_prices[min_idx]:.2f}',
            xy=(dates[min_idx], close_prices[min_idx]),
            xytext=(dates[min_idx], close_prices[min_idx] - 3),
            fontsize=11, color='#19a55e', fontweight='bold',
            arrowprops=dict(arrowstyle='->', color='#19a55e'))

# 计算均线
for period, color, label in [(5, '#f5a623', 'MA5'), (10, '#4a90d9', 'MA10'), (20, '#9b59b6', 'MA20')]:
    ma = close_prices.rolling(window=period).mean()
    ax.plot(dates, ma, color=color, linewidth=1, alpha=0.8, label=label)

ax.set_title('招商银行 (600036.SH) 每日收盘价曲线', fontsize=16, fontweight='bold', pad=15)
ax.set_xlabel('日期', fontsize=12)
ax.set_ylabel('收盘价 (元)', fontsize=12)
ax.legend(loc='upper left', fontsize=10)
ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
ax.grid(True, alpha=0.3)
fig.autofmt_xdate()
plt.tight_layout()
plt.savefig('cmb_close_price.png', dpi=150, bbox_inches='tight')
plt.show()
print(f"图表已保存: cmb_close_price.png")""")

# ====== Cell 6: K-line ======
md("""## 6. K线图 (Candlestick Chart)""")

code("""# 使用 matplotlib 绘制 K 线图
fig, ax = plt.subplots(figsize=(16, 7))

# 计算宽度
width = 0.6
for i, row in df.iterrows():
    d = row['trade_date']
    o, c, l, h = row['open'], row['close'], row['low'], row['high']
    color = '#e83939' if c >= o else '#19a55e'
    
    # 绘制影线
    ax.plot([d, d], [l, h], color=color, linewidth=0.8)
    # 绘制实体
    body_bottom = min(o, c)
    body_height = abs(c - o) or 0.01  # 十字星最小高度
    ax.add_patch(Rectangle((mdates.date2num(d) - width/2, body_bottom), 
                           width, body_height,
                           facecolor=color, edgecolor=color, linewidth=0.5))

# 均线
close_prices = df['close']
dates = df['trade_date']
for period, color, lbl in [(5, '#f5a623', 'MA5'), (10, '#4a90d9', 'MA10'), (20, '#9b59b6', 'MA20')]:
    ma = close_prices.rolling(window=period).mean()
    ax.plot(dates, ma, color=color, linewidth=1.2, label=lbl, zorder=3)

ax.set_title('招商银行 (600036.SH) 近一年日K线图', fontsize=16, fontweight='bold', pad=15)
ax.set_ylabel('价格 (元)', fontsize=12)
ax.legend(loc='upper left', fontsize=10)
ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
ax.grid(True, alpha=0.3)
fig.autofmt_xdate()
plt.tight_layout()
plt.savefig('cmb_kline.png', dpi=150, bbox_inches='tight')
plt.show()
print(f"图表已保存: cmb_kline.png")""")

# ====== Cell 7: Volume ======
md("""## 7. 成交量图""")

code("""# 成交量柱状图
fig, ax = plt.subplots(figsize=(16, 5))

dates = df['trade_date']
vols = df['vol'] / 10000  # 转换为万手
colors = ['#e83939' if df.iloc[i]['close'] >= df.iloc[i]['open'] 
          else '#19a55e' for i in range(len(df))]

ax.bar(dates, vols, width=0.8, color=colors, alpha=0.85)

# 均量线
vol_ma5 = vols.rolling(window=5).mean()
vol_ma20 = vols.rolling(window=20).mean()
ax.plot(dates, vol_ma5, color='#f5a623', linewidth=1, alpha=0.9, label='VOL MA5')
ax.plot(dates, vol_ma20, color='#9b59b6', linewidth=1, alpha=0.9, label='VOL MA20')

ax.set_title('招商银行 (600036.SH) 成交量', fontsize=14, fontweight='bold', pad=12)
ax.set_ylabel('成交量 (万手)', fontsize=12)
ax.legend(loc='upper left', fontsize=10)
ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
ax.grid(True, alpha=0.3, axis='y')
fig.autofmt_xdate()
plt.tight_layout()
plt.savefig('cmb_volume.png', dpi=150, bbox_inches='tight')
plt.show()
print(f"图表已保存: cmb_volume.png")""")

# ====== Cell 8: Summary ======
md("""## 8. 分析总结""")

code("""print("=" * 60)
print("招商银行 (600036.SH) 近一年交易数据总结")
print("=" * 60)

start_price = df.iloc[0]['close']
end_price = df.iloc[-1]['close']
change_pct = (end_price - start_price) / start_price * 100

print(f"\\n💰 价格表现:")
print(f"   起始: ¥{start_price:.2f}  →  最新: ¥{end_price:.2f}")
print(f"   区间涨跌: {change_pct:+.2f}%")
print(f"   区间振幅: {(df['high'].max() / df['low'].min() - 1) * 100:.2f}%")

print(f"\\n📊 成交量特征:")
print(f"   日均: {df['vol'].mean():.0f} 手")
print(f"   峰值: {df['vol'].max():.0f} 手 ({df.loc[df['vol'].idxmax(), 'trade_date'].strftime('%Y-%m-%d')})")

# 涨跌天数
up_days = (df['close'] > df['open']).sum()
down_days = (df['close'] < df['open']).sum()
print(f"\\n📈 涨跌天数分布:")
print(f"   收阳: {up_days} 天 ({up_days/len(df)*100:.1f}%)")
print(f"   收阴: {down_days} 天 ({down_days/len(df)*100:.1f}%)")

# 按季度统计
df['quarter'] = df['trade_date'].dt.to_period('Q')
quarterly = df.groupby('quarter').agg({
    'close': ['first', 'last'],
    'vol': 'mean'
}).round(2)
quarterly.columns = ['季初收盘', '季末收盘', '均量']
quarterly['涨跌%'] = ((quarterly['季末收盘'] / quarterly['季初收盘'] - 1) * 100).round(2)
print(f"\\n📅 季度表现:")
print(quarterly.to_string())""")

# Output files summary
md("""## 9. 输出文件汇总

| 文件 | 说明 |
|------|------|
| `cmb_daily.json` | JSON 格式原始数据 |
| `cmb_daily.csv` | CSV 格式（可用 Excel 打开） |
| `cmb_close_price.png` | 收盘价曲线图 |
| `cmb_kline.png` | K线图 |
| `cmb_volume.png` | 成交量图 |
| `cmb_kline_dashboard.html` | 交互式 HTML 看板 |
| `cmb_analysis.ipynb` | 本 Notebook |

---

**数据来源**: Tushare Pro (https://tushare.pro)  
**分析日期**: 2026-07-04""")

# ====== Build notebook JSON ======
notebook = {
    "cells": cells,
    "metadata": {
        "kernelspec": {
            "display_name": "Python 3",
            "language": "python",
            "name": "python3"
        },
        "language_info": {
            "name": "python",
            "version": "3.13.0"
        }
    },
    "nbformat": 4,
    "nbformat_minor": 5
}

output_path = 'C:/Users/Administrator/Desktop/量化交易/cmb_analysis.ipynb'
with open(output_path, 'w', encoding='utf-8') as f:
    json.dump(notebook, f, ensure_ascii=False, indent=1)

print(f"Notebook saved: {output_path}")
print(f"Cells: {len(cells)}")
