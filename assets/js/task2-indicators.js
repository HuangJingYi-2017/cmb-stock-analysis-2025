/**
 * TASK2: 指标实验室 - 交互式技术指标图表
 * 加载 data/cmb_2025_indicators.json，渲染价格+布林带+MA、RSI、MACD
 */

let chartData = [];
let priceChart = null;
let rsiChart = null;
let macdChart = null;

// 配置项状态
const state = {
  showBoll: true,
  showMa5: true,
  showMa10: false,
  showMa20: false,
  showVolume: true,
  rsiPeriod: 14,
};

async function initIndicators() {
  const container = document.getElementById('priceChart');
  if (!container) return;

  container.innerHTML = '<div class="loading"><div class="spinner"></div>正在加载数据...</div>';

  try {
    const response = await fetch('../data/cmb_2025_indicators.json');
    if (!response.ok) throw new Error('数据加载失败');
    chartData = await response.json();

    // 过滤掉前 20 个无效数据，确保指标有效
    chartData = chartData.filter(d => d.ma5 !== null && d.bb_upper !== null);

    renderAllCharts();
    bindControls();
  } catch (err) {
    container.innerHTML = `<div class="loading">数据加载失败: ${err.message}</div>`;
    console.error(err);
  }
}

function renderAllCharts() {
  renderPriceChart();
  renderRsiChart();
  renderMacdChart();
  syncChartZoom();
}

function renderPriceChart() {
  const dom = document.getElementById('priceChart');
  if (!dom) return;
  priceChart = echarts.init(dom);

  const dates = chartData.map(d => d.trade_date);
  const closeData = chartData.map(d => d.close);
  const volumeData = chartData.map(d => [d.trade_date, d.vol]);

  const series = [
    {
      name: '收盘价',
      type: 'line',
      data: closeData,
      smooth: false,
      symbol: 'none',
      lineStyle: { width: 2, color: '#1f2937' },
      itemStyle: { color: '#1f2937' },
    }
  ];

  if (state.showBoll) {
    series.push(
      {
        name: '上轨',
        type: 'line',
        data: chartData.map(d => d.bb_upper),
        smooth: false,
        symbol: 'none',
        lineStyle: { width: 1, color: '#9ca3af', type: 'dashed' },
        itemStyle: { color: '#9ca3af' },
      },
      {
        name: '下轨',
        type: 'line',
        data: chartData.map(d => d.bb_lower),
        smooth: false,
        symbol: 'none',
        lineStyle: { width: 1, color: '#9ca3af', type: 'dashed' },
        itemStyle: { color: '#9ca3af' },
      },
      {
        name: '布林带',
        type: 'line',
        data: chartData.map(d => d.bb_middle),
        smooth: false,
        symbol: 'none',
        lineStyle: { width: 1, color: '#d1d5db' },
        itemStyle: { color: '#d1d5db' },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(156, 163, 175, 0.15)' },
            { offset: 1, color: 'rgba(156, 163, 175, 0.02)' }
          ])
        },
      }
    );
  }

  if (state.showMa5) {
    series.push({
      name: 'MA5',
      type: 'line',
      data: chartData.map(d => d.ma5),
      smooth: false,
      symbol: 'none',
      lineStyle: { width: 1.5, color: '#10b981' },
      itemStyle: { color: '#10b981' },
    });
  }

  if (state.showMa10) {
    series.push({
      name: 'MA10',
      type: 'line',
      data: chartData.map(d => d.ma10),
      smooth: false,
      symbol: 'none',
      lineStyle: { width: 1.5, color: '#3b82f6' },
      itemStyle: { color: '#3b82f6' },
    });
  }

  if (state.showMa20) {
    series.push({
      name: 'MA20',
      type: 'line',
      data: chartData.map(d => d.ma20),
      smooth: false,
      symbol: 'none',
      lineStyle: { width: 1.5, color: '#f59e0b' },
      itemStyle: { color: '#f59e0b' },
    });
  }

  const options = {
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'cross' },
      backgroundColor: 'rgba(255,255,255,0.95)',
      borderColor: '#e5e7eb',
      textStyle: { color: '#1f2937', fontSize: 12 },
    },
    grid: {
      left: 60, right: 20, top: 30, bottom: state.showVolume ? 80 : 30,
    },
    legend: {
      data: series.map(s => s.name),
      top: 0,
      textStyle: { fontSize: 12 },
    },
    xAxis: {
      type: 'category',
      data: dates,
      axisLine: { lineStyle: { color: '#e5e7eb' } },
      axisLabel: { color: '#6b7280', fontSize: 11 },
      axisPointer: { show: true },
    },
    yAxis: {
      type: 'value',
      scale: true,
      axisLine: { show: false },
      splitLine: { lineStyle: { color: '#f3f4f6' } },
      axisLabel: { color: '#6b7280', fontSize: 11 },
    },
    dataZoom: [
      { type: 'inside', xAxisIndex: 0, start: 50, end: 100 },
      { type: 'slider', xAxisIndex: 0, start: 50, end: 100, bottom: 40, height: 20 },
    ],
    series: series,
  };

  if (state.showVolume) {
    options.series.push({
      name: '成交量',
      type: 'bar',
      xAxisIndex: 0,
      yAxisIndex: 0,
      data: chartData.map((d, i) => {
        const prev = i > 0 ? chartData[i - 1].close : d.pre_close;
        return {
          value: d.vol,
          itemStyle: { color: d.close >= prev ? '#ef4444' : '#22c55e' }
        };
      }),
      barWidth: '50%',
      z: 2,
    });
    // 将成交量放在下方坐标轴，简化处理：用第二个 yAxis
    options.yAxis = [
      {
        type: 'value',
        scale: true,
        position: 'left',
        axisLine: { show: false },
        splitLine: { lineStyle: { color: '#f3f4f6' } },
        axisLabel: { color: '#6b7280', fontSize: 11 },
      },
      {
        type: 'value',
        position: 'right',
        axisLine: { show: false },
        splitLine: { show: false },
        axisLabel: { show: false },
      }
    ];
    // 成交量使用第二个 yAxis
    options.series[options.series.length - 1].yAxisIndex = 1;
  }

  priceChart.setOption(options, true);
}

function renderRsiChart() {
  const dom = document.getElementById('rsiChart');
  if (!dom) return;
  rsiChart = echarts.init(dom);

  const dates = chartData.map(d => d.trade_date);
  const rsiData = chartData.map(d => d.rsi14);

  rsiChart.setOption({
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(255,255,255,0.95)',
      borderColor: '#e5e7eb',
      textStyle: { color: '#1f2937', fontSize: 12 },
    },
    grid: { left: 60, right: 20, top: 20, bottom: 30 },
    xAxis: {
      type: 'category',
      data: dates,
      axisLine: { lineStyle: { color: '#e5e7eb' } },
      axisLabel: { color: '#6b7280', fontSize: 11 },
      axisPointer: { show: true },
    },
    yAxis: {
      type: 'value',
      min: 0,
      max: 100,
      splitLine: { lineStyle: { color: '#f3f4f6' } },
      axisLabel: { color: '#6b7280', fontSize: 11 },
    },
    dataZoom: [
      { type: 'inside', xAxisIndex: 0, start: 50, end: 100 },
    ],
    series: [
      {
        name: `RSI${state.rsiPeriod}`,
        type: 'line',
        data: rsiData,
        smooth: false,
        symbol: 'none',
        lineStyle: { width: 1.5, color: '#8b5cf6' },
        itemStyle: { color: '#8b5cf6' },
        markLine: {
          silent: true,
          data: [
            { yAxis: 70, lineStyle: { color: '#ef4444', type: 'dashed' }, label: { formatter: '超买 70', fontSize: 10 } },
            { yAxis: 30, lineStyle: { color: '#22c55e', type: 'dashed' }, label: { formatter: '超卖 30', fontSize: 10 } },
          ]
        },
      }
    ],
  }, true);
}

function renderMacdChart() {
  const dom = document.getElementById('macdChart');
  if (!dom) return;
  macdChart = echarts.init(dom);

  const dates = chartData.map(d => d.trade_date);

  macdChart.setOption({
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(255,255,255,0.95)',
      borderColor: '#e5e7eb',
      textStyle: { color: '#1f2937', fontSize: 12 },
    },
    grid: { left: 60, right: 20, top: 20, bottom: 30 },
    legend: { data: ['DIF', 'DEA'], top: 0, textStyle: { fontSize: 12 } },
    xAxis: {
      type: 'category',
      data: dates,
      axisLine: { lineStyle: { color: '#e5e7eb' } },
      axisLabel: { color: '#6b7280', fontSize: 11 },
      axisPointer: { show: true },
    },
    yAxis: {
      type: 'value',
      splitLine: { lineStyle: { color: '#f3f4f6' } },
      axisLabel: { color: '#6b7280', fontSize: 11 },
    },
    dataZoom: [
      { type: 'inside', xAxisIndex: 0, start: 50, end: 100 },
    ],
    series: [
      {
        name: 'DIF',
        type: 'line',
        data: chartData.map(d => d.macd_dif),
        smooth: false,
        symbol: 'none',
        lineStyle: { width: 1.5, color: '#3b82f6' },
        itemStyle: { color: '#3b82f6' },
      },
      {
        name: 'DEA',
        type: 'line',
        data: chartData.map(d => d.macd_dea),
        smooth: false,
        symbol: 'none',
        lineStyle: { width: 1.5, color: '#f97316' },
        itemStyle: { color: '#f97316' },
      },
      {
        name: 'MACD柱',
        type: 'bar',
        data: chartData.map(d => ({
          value: d.macd_hist,
          itemStyle: { color: d.macd_hist >= 0 ? '#ef4444' : '#22c55e' }
        })),
        barWidth: '50%',
      }
    ],
  }, true);
}

function syncChartZoom() {
  if (priceChart && rsiChart && macdChart) {
    priceChart.group = 'indicators';
    rsiChart.group = 'indicators';
    macdChart.group = 'indicators';
    echarts.connect('indicators');
  }
}

function bindControls() {
  const ids = {
    'toggleBoll': 'showBoll',
    'toggleMa5': 'showMa5',
    'toggleMa10': 'showMa10',
    'toggleMa20': 'showMa20',
    'toggleVolume': 'showVolume',
  };

  Object.entries(ids).forEach(([id, key]) => {
    const el = document.getElementById(id);
    if (el) {
      el.addEventListener('change', (e) => {
        state[key] = e.target.checked;
        renderPriceChart();
      });
    }
  });

  window.addEventListener('resize', () => {
    priceChart && priceChart.resize();
    rsiChart && rsiChart.resize();
    macdChart && macdChart.resize();
  });
}

// 初始化
document.addEventListener('DOMContentLoaded', initIndicators);
