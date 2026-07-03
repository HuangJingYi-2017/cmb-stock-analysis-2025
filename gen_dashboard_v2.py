import json

json_path = 'C:/Users/Administrator/Desktop/量化交易/cmb_daily.json'

with open(json_path, 'r', encoding='utf-8') as f:
    data = json.load(f)

data.sort(key=lambda x: x['trade_date'])

dates = [d['trade_date'] for d in data]
dates_fmt = [f"{d[:4]}-{d[4:6]}-{d[6:8]}" for d in dates]
ohlc = [[d['open'], d['close'], d['low'], d['high']] for d in data]
close_prices = [d['close'] for d in data]
vols = [d['vol'] for d in data]

def calc_ma(values, period):
    result = [None] * len(values)
    for i in range(period - 1, len(values)):
        result[i] = round(sum(values[i - period + 1:i + 1]) / period, 2)
    return result

ma5 = calc_ma(close_prices, 5)
ma10 = calc_ma(close_prices, 10)
ma20 = calc_ma(close_prices, 20)
ma60 = calc_ma(close_prices, 60)

start_price = data[0]['close']
end_price = data[-1]['close']
change_pct = round((end_price - start_price) / start_price * 100, 2)
max_price = max(d['high'] for d in data)
min_price = min(d['low'] for d in data)
avg_vol = round(sum(d['vol'] for d in data) / len(data), 0)
max_vol = max(d['vol'] for d in data)

end_cls = 'up' if change_pct >= 0 else 'down'
chg_sign = '+' if change_pct >= 0 else ''

html = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>招商银行 (600036.SH) 交易数据分析看板</title>
<script src="https://cdn.jsdelivr.net/npm/echarts@5/dist/echarts.min.js"></script>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', sans-serif; background: #f5f6fa; color: #333; }
.header { background: linear-gradient(135deg, #1a1a2e, #16213e); color: #fff; padding: 24px 32px; }
.header h1 { font-size: 24px; font-weight: 600; margin-bottom: 4px; }
.header .sub { font-size: 14px; opacity: 0.75; }
.stats-row { display: flex; gap: 14px; padding: 18px 32px; background: #fff; border-bottom: 1px solid #e8e8e8; flex-wrap: wrap; }
.stat-card { flex: 1; min-width: 130px; padding: 14px 16px; background: #fafbfc; border-radius: 8px; border: 1px solid #eee; }
.stat-card .label { font-size: 11px; color: #888; margin-bottom: 5px; }
.stat-card .value { font-size: 18px; font-weight: 700; }
.stat-card .value.up { color: #e83939; }
.stat-card .value.down { color: #19a55e; }
.tabs { display: flex; margin: 16px 32px 0; gap: 0; }
.tab-btn { padding: 10px 24px; border: 1px solid #ddd; border-bottom: none; background: #eee; cursor: pointer; font-size: 14px; color: #666; border-radius: 8px 8px 0 0; margin-right: 2px; transition: all 0.2s; }
.tab-btn.active { background: #fff; color: #1a1a2e; font-weight: 700; border-color: #ccc; }
.tab-btn:hover { background: #f5f5f5; }
.chart-container { margin: 0 32px 16px; background: #fff; border: 1px solid #e8e8e8; border-top: 3px solid #1a1a2e; border-radius: 0 8px 8px 8px; overflow: hidden; }
.chart-body { padding: 10px; }
.chart { width: 100%; height: 480px; }
.chart-vol { width: 100%; height: 200px; }
.data-source { padding: 12px 32px 20px; font-size: 12px; color: #999; text-align: right; }
</style>
</head>
<body>

<div class="header">
  <h1>招商银行 600036.SH</h1>
  <div class="sub">China Merchants Bank · 上交所 · 银行板块 · 近一年交易数据分析</div>
</div>

<div class="stats-row">
  <div class="stat-card">
    <div class="label">区间</div>
    <div class="value" style="font-size:13px;">__D0__ ~ __DL__</div>
  </div>
  <div class="stat-card">
    <div class="label">交易日</div>
    <div class="value" style="font-size:16px;">__NR__ 天</div>
  </div>
  <div class="stat-card">
    <div class="label">起始收盘</div>
    <div class="value">__SP__</div>
  </div>
  <div class="stat-card">
    <div class="label">最新收盘</div>
    <div class="value __EC__">__EP__</div>
  </div>
  <div class="stat-card">
    <div class="label">区间涨跌</div>
    <div class="value __CC__">__S____CP__%</div>
  </div>
  <div class="stat-card">
    <div class="label">最高 / 最低</div>
    <div class="value" style="font-size:15px;">__MX__ / __MN__</div>
  </div>
  <div class="stat-card">
    <div class="label">日均成交量</div>
    <div class="value" style="font-size:15px;">__AV__ 手</div>
  </div>
</div>

<div class="tabs">
  <button class="tab-btn active" onclick="switchTab('close')">📈 收盘价曲线</button>
  <button class="tab-btn" onclick="switchTab('kline')">🕯️ K线图</button>
  <button class="tab-btn" onclick="switchTab('volume')">📊 成交量</button>
</div>

<div class="chart-container">
  <div class="chart-body">
    <div id="chart-close" class="chart"></div>
    <div id="chart-kline" class="chart" style="display:none;"></div>
    <div id="chart-volume" class="chart" style="display:none;"></div>
  </div>
</div>

<div class="data-source">数据来源: Tushare Pro · 更新于 __DL__ · 共计 __NR__ 个交易日</div>

<script>
var dates = __DATES__;
var closePrices = __CLOSE__;
var ohlc = __OHLC__;
var vols = __VOLS__;
var ma5 = __MA5__;
var ma10 = __MA10__;
var ma20 = __MA20__;
var ma60 = __MA60__;

var volColors = ohlc.map(function(d) { return d[1] >= d[0] ? '#e83939' : '#19a55e'; });
var changeColors = [];
for (var i = 0; i < closePrices.length; i++) {
  if (i === 0) { changeColors.push('#e83939'); }
  else { changeColors.push(closePrices[i] >= closePrices[i-1] ? '#e83939' : '#19a55e'); }
}

var commonGrid = { left: '8%', right: '3%', top: '4%', height: '75%' };
var commonX = {
  type: 'category', data: dates,
  axisLabel: { formatter: function(v) { return v.slice(5); } },
  axisLine: { lineStyle: { color: '#ccc' } }
};
var commonZoom = [
  { type: 'inside', start: 70, end: 100 },
  { type: 'slider', start: 70, end: 100, height: 20, bottom: 24 }
];
var commonY = { scale: true, splitLine: { lineStyle: { color: '#f0f0f0' } } };

var charts = {};

function initCloseChart() {
  var dom = document.getElementById('chart-close');
  if (!charts.close) charts.close = echarts.init(dom);
  var c = charts.close;

  c.setOption({
    tooltip: {
      trigger: 'axis',
      formatter: function(params) {
        var d = params[0].axisValue;
        var html = '<strong>' + d + '</strong><br/>';
        params.forEach(function(p) {
          if (p.seriesName === '收盘价') {
            var color = changeColors[params[0].dataIndex];
            html += '<span style=\"color:' + color + '\">\u25cf</span> ' + p.seriesName + ': \u00a5' + p.value.toFixed(2);
          } else if (p.value != null) {
            html += p.seriesName + ': ' + p.value.toFixed(2) + '<br/>';
          }
        });
        return html;
      }
    },
    grid: commonGrid,
    xAxis: commonX,
    yAxis: commonY,
    dataZoom: commonZoom,
    series: [
      {
        name: '收盘价',
        type: 'line',
        data: closePrices,
        lineStyle: { width: 1.5, color: '#333' },
        areaStyle: { color: new echarts.graphic.LinearGradient(0,0,0,1, [
          {offset:0, color:'rgba(232,57,57,0.15)'}, {offset:1, color:'rgba(232,57,57,0.01)'}
        ])},
        symbol: 'none',
        markPoint: {
          data: [
            { type: 'max', name: '最高', symbol: 'pin', symbolSize: 40, itemStyle: { color: '#e83939' } },
            { type: 'min', name: '最低', symbol: 'pin', symbolSize: 40, itemStyle: { color: '#19a55e' } }
          ]
        }
      },
      { name: 'MA5',  type: 'line', data: ma5,  smooth: true, lineStyle: { width: 1, color: '#f5a623' }, symbol: 'none' },
      { name: 'MA10', type: 'line', data: ma10, smooth: true, lineStyle: { width: 1, color: '#4a90d9' }, symbol: 'none' },
      { name: 'MA20', type: 'line', data: ma20, smooth: true, lineStyle: { width: 1, color: '#9b59b6' }, symbol: 'none' },
      { name: 'MA60', type: 'line', data: ma60, smooth: true, lineStyle: { width: 1, color: '#e67e22' }, symbol: 'none' }
    ]
  });
}

function initKlineChart() {
  var dom = document.getElementById('chart-kline');
  if (!charts.kline) charts.kline = echarts.init(dom);
  var c = charts.kline;

  c.setOption({
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'cross' },
      formatter: function(params) {
        var d = params[0].axisValue, html = '<strong>' + d + '</strong><br/>';
        params.forEach(function(p) {
          if (p.seriesName === '日K') {
            var v = p.data;
            if (v && v.length >= 4) {
              var chg = ((v[1] - v[0]) / v[0] * 100).toFixed(2);
              var clr = chg >= 0 ? '#e83939' : '#19a55e';
              html += '\u5f00: ' + v[0].toFixed(2) + ' \u6536: <span style=\"color:' + clr + '\">' + v[1].toFixed(2) + '</span><br/>';
              html += '\u4f4e: ' + v[2].toFixed(2) + ' \u9ad8: ' + v[3].toFixed(2) + ' (' + (chg>=0?'+':'') + chg + '%)<br/>';
            }
          } else if (p.value != null) {
            html += p.seriesName + ': ' + p.value.toFixed(2) + '<br/>';
          }
        });
        return html;
      }
    },
    legend: { data: ['日K','MA5','MA10','MA20','MA60'], bottom: 0 },
    grid: { left: '8%', right: '3%', top: '3%', height: '68%' },
    xAxis: commonX,
    yAxis: commonY,
    dataZoom: commonZoom,
    series: [
      {
        name: '日K', type: 'candlestick', data: ohlc,
        itemStyle: { color: '#e83939', color0: '#19a55e', borderColor: '#e83939', borderColor0: '#19a55e' }
      },
      { name: 'MA5',  type: 'line', data: ma5,  smooth: true, lineStyle: { width: 1, color: '#f5a623' }, symbol: 'none' },
      { name: 'MA10', type: 'line', data: ma10, smooth: true, lineStyle: { width: 1, color: '#4a90d9' }, symbol: 'none' },
      { name: 'MA20', type: 'line', data: ma20, smooth: true, lineStyle: { width: 1, color: '#9b59b6' }, symbol: 'none' },
      { name: 'MA60', type: 'line', data: ma60, smooth: true, lineStyle: { width: 1, color: '#e67e22' }, symbol: 'none' }
    ]
  });
}

function initVolumeChart() {
  var dom = document.getElementById('chart-volume');
  if (!charts.volume) charts.volume = echarts.init(dom);
  var c = charts.volume;

  c.setOption({
    tooltip: {
      trigger: 'axis',
      formatter: function(params) {
        var v = params[0].value;
        return '<strong>' + params[0].axisValue + '</strong><br/>\u6210\u4ea4\u91cf: ' + (v/10000).toFixed(2) + ' \u4e07\u624b';
      }
    },
    grid: { left: '8%', right: '3%', top: '4%', height: '75%' },
    xAxis: commonX,
    yAxis: {
      scale: true,
      splitLine: { lineStyle: { color: '#f0f0f0' } },
      axisLabel: { formatter: function(v) { return (v/10000).toFixed(0) + '\u4e07'; } }
    },
    dataZoom: commonZoom,
    series: [
      {
        type: 'bar', name: '成交量',
        data: vols.map(function(v, i) { return { value: v, itemStyle: { color: volColors[i] } }; })
      },
      {
        name: 'VOL MA5',  type: 'line',
        data: (function() {
          var r = [];
          for (var i = 0; i < vols.length; i++) {
            if (i >= 4) { var s = 0; for (var j = i-4; j <= i; j++) s += vols[j]; r.push(Math.round(s/5)); }
            else { r.push(null); }
          }
          return r;
        })(),
        smooth: true, lineStyle: { width: 1, color: '#f5a623' }, symbol: 'none'
      },
      {
        name: 'VOL MA20', type: 'line',
        data: (function() {
          var r = [];
          for (var i = 0; i < vols.length; i++) {
            if (i >= 19) { var s = 0; for (var j = i-19; j <= i; j++) s += vols[j]; r.push(Math.round(s/20)); }
            else { r.push(null); }
          }
          return r;
        })(),
        smooth: true, lineStyle: { width: 1, color: '#9b59b6' }, symbol: 'none'
      }
    ]
  });
}

function switchTab(tab) {
  document.getElementById('chart-close').style.display = tab === 'close' ? '' : 'none';
  document.getElementById('chart-kline').style.display = tab === 'kline' ? '' : 'none';
  document.getElementById('chart-volume').style.display = tab === 'volume' ? '' : 'none';
  var btns = document.querySelectorAll('.tab-btn');
  btns.forEach(function(b) { b.classList.remove('active'); });
  var idx = tab === 'close' ? 0 : (tab === 'kline' ? 1 : 2);
  btns[idx].classList.add('active');
  setTimeout(function() {
    if (charts[tab]) charts[tab].resize();
  }, 50);
}

// Init all
initCloseChart();
initKlineChart();
initVolumeChart();
switchTab('close');

// Responsive
window.addEventListener('resize', function() {
  for (var k in charts) { if (charts[k]) charts[k].resize(); }
});
</script>

</body>
</html>"""

replacements = {
    '__D0__': dates_fmt[0], '__DL__': dates_fmt[-1],
    '__NR__': str(len(data)), '__SP__': str(start_price), '__EP__': str(end_price),
    '__EC__': end_cls, '__CC__': end_cls, '__S__': chg_sign, '__CP__': str(change_pct),
    '__MX__': str(max_price), '__MN__': str(min_price),
    '__AV__': f"{avg_vol:,.0f}",
    '__DATES__': json.dumps(dates_fmt),
    '__CLOSE__': json.dumps(close_prices),
    '__OHLC__': json.dumps(ohlc),
    '__VOLS__': json.dumps(vols),
    '__MA5__': json.dumps(ma5),
    '__MA10__': json.dumps(ma10),
    '__MA20__': json.dumps(ma20),
    '__MA60__': json.dumps(ma60),
}
for old, new in replacements.items():
    html = html.replace(old, new)

html_path = 'C:/Users/Administrator/Desktop/量化交易/cmb_kline_dashboard.html'
with open(html_path, 'w', encoding='utf-8') as f:
    f.write(html)
print(f'HTML saved: {html_path}')
print(f'Size: {len(html)} bytes')
