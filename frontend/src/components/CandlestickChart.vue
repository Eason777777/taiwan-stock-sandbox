<!-- K線圖 (尚須調整) -->
<template>
  <div :class="[
    'w-full flex flex-col items-stretch gap-4 border-10 border-solid rounded-xl shadow-2xl p-6 transition-colors duration-300',
    theme === 'light' ? 'bg-white border-nature-300 text-nature-900' : 'bg-nature-800 border-nature-500 text-white'
  ]">
    <!-- Header Section -->
    <div class="flex justify-between items-center border-b pb-3" :class="theme === 'light' ? 'border-nature-200' : 'border-nature-700'">
      <div class="flex flex-col">
        <h2 class="text-03 font-bold bg-linear-to-r from-blue-400 to-blue-600 bg-clip-text text-transparent font-display">
          {{ stockId }} {{ stockName }}
        </h2>
        <p class="text-sm" :class="theme === 'light' ? 'text-nature-600' : 'text-nature-400'">
          K線圖看板 | 資料由後端即時提供
        </p>
      </div>

      <!-- Timeframe Selector -->
      <div class="flex items-center gap-3">
        <div class="flex p-1 rounded-lg border" :class="theme === 'light' ? 'border-nature-300 bg-nature-100' : 'border-nature-700 bg-nature-900/60'">
          <button
            class="px-4 py-1.5 rounded-md text-sm font-semibold cursor-pointer transition-all duration-200"
            :class="[
              timeframe === 'daily'
                ? 'bg-blue-500 text-white shadow-md'
                : theme === 'light' ? 'text-nature-700 hover:text-nature-900 hover:bg-nature-200' : 'text-nature-400 hover:text-white hover:bg-nature-800'
            ]"
            @click="switchTimeframe('daily')"
          >
            日K
          </button>
          <button
            class="px-4 py-1.5 rounded-md text-sm font-semibold cursor-pointer transition-all duration-200"
            :class="[
              timeframe === 'weekly'
                ? 'bg-blue-500 text-white shadow-md'
                : theme === 'light' ? 'text-nature-700 hover:text-nature-900 hover:bg-nature-200' : 'text-nature-400 hover:text-white hover:bg-nature-800'
            ]"
            @click="switchTimeframe('weekly')"
          >
            週K
          </button>
          <button
            class="px-4 py-1.5 rounded-md text-sm font-semibold cursor-pointer transition-all duration-200"
            :class="[
              timeframe === 'monthly'
                ? 'bg-blue-500 text-white shadow-md'
                : theme === 'light' ? 'text-nature-700 hover:text-nature-900 hover:bg-nature-200' : 'text-nature-400 hover:text-white hover:bg-nature-800'
            ]"
            @click="switchTimeframe('monthly')"
          >
            月K
          </button>
        </div>
      </div>
    </div>

    <!-- Stock Info Bar (OHLCV + Change) -->
    <div v-if="activeData" class="flex flex-wrap gap-x-6 gap-y-2 py-2 text-sm font-medium items-center" :class="theme === 'light' ? 'text-nature-800' : 'text-nature-200'">
      <span><strong>{{ activeDataDateStr }}</strong></span>
      
      <!-- Open -->
      <span>
        開
        <strong :class="getPriceClass(activeData.open)">
          {{ activeData.open !== undefined ? activeData.open.toFixed(2) : '--' }}
        </strong>
      </span>
      
      <!-- High -->
      <span>
        高
        <strong :class="getPriceClass(activeData.high)">
          {{ activeData.high !== undefined ? activeData.high.toFixed(2) : '--' }}
        </strong>
      </span>
      
      <!-- Low -->
      <span>
        低
        <strong :class="getPriceClass(activeData.low)">
          {{ activeData.low !== undefined ? activeData.low.toFixed(2) : '--' }}
        </strong>
      </span>
      
      <!-- Close -->
      <span>
        收
        <strong :class="getPriceClass(activeData.close)">
          {{ activeData.close !== undefined ? activeData.close.toFixed(2) : '--' }}
        </strong>
      </span>
      
      <!-- Volume -->
      <span>
        量(張)
        <strong :class="theme === 'light' ? 'text-nature-900' : 'text-white'">
          {{ activeData.volume ? activeData.volume.toLocaleString() : '0' }}
        </strong>
      </span>
      
      <!-- Change -->
      <span>
        漲跌
        <strong :class="getChangeClass(priceChange)">
          {{ priceChange > 0 ? '+' : '' }}{{ priceChange.toFixed(2) }}
        </strong>
      </span>

      <!-- Change Percent -->
      <span>
        幅度
        <strong :class="getChangeClass(priceChange)">
          {{ priceChange > 0 ? '+' : '' }}{{ priceChangePercent.toFixed(2) }}%
        </strong>
      </span>
    </div>
    <div v-else class="py-2 text-sm text-nature-400 animate-pulse">
      暫無 K線數據
    </div>

    <!-- Chart Container Element -->
    <div 
      ref="chartContainerRef" 
      class="w-full h-112.5 rounded-lg border transition-colors duration-300 overflow-hidden"
      :class="theme === 'light' ? 'bg-white border-nature-200' : 'bg-nature-950 border-nature-700'"
    ></div>

    <!-- Footer Description -->
    <div class="flex justify-between items-center text-xs" :class="theme === 'light' ? 'text-nature-500' : 'text-nature-400'">
      <div>使用滑鼠滾輪縮放，按住左鍵左右拖曳平移</div>
      <div class="flex gap-4">
        <span class="flex items-center gap-1"><span class="w-2.5 h-2.5 rounded-full bg-[#45B0E6]"></span>MA5</span>
        <span class="flex items-center gap-1"><span class="w-2.5 h-2.5 rounded-full bg-[#B052CA]"></span>MA10</span>
        <span class="flex items-center gap-1"><span class="w-2.5 h-2.5 rounded-full bg-[#FF9800]"></span>MA20</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch, computed } from 'vue'
import { init, dispose, registerIndicator } from 'klinecharts'

// 自訂註冊/覆蓋 VOL 指標，將預設的 MA 均線標題修改為 MV (Volume Moving Average)
registerIndicator({
  name: 'VOL',
  shortName: 'VOL',
  series: 'volume',
  calcParams: [5, 20],
  precision: 0,
  shouldFormatBigNumber: true,
  minValue: 0,
  figures: [
    { key: 'ma1', title: 'MV5: ', type: 'line' },
    { key: 'ma2', title: 'MV20: ', type: 'line' },
    {
      key: 'volume',
      title: 'VOLUME: ',
      type: 'bar',
      baseValue: 0,
      styles: function (kLineData, indicator, defaultStyles) {
        var n = kLineData.current.kLineData;
        var color = defaultStyles.bars[0].noChangeColor;
        if (n) {
          if (n.close > n.open) {
            color = defaultStyles.bars[0].upColor;
          } else if (n.close < n.open) {
            color = defaultStyles.bars[0].downColor;
          }
        }
        return { color: color };
      }
    }
  ],
  regenerateFigures: function (params) {
    var figures = params.map(function (p, i) {
      return { key: 'ma' + (i + 1), title: 'MV' + p + ': ', type: 'line' };
    });
    figures.push({
      key: 'volume',
      title: 'VOLUME: ',
      type: 'bar',
      baseValue: 0,
      styles: function (kLineData, indicator, defaultStyles) {
        var n = kLineData.current.kLineData;
        var color = defaultStyles.bars[0].noChangeColor;
        if (n) {
          if (n.close > n.open) {
            color = defaultStyles.bars[0].upColor;
          } else if (n.close < n.open) {
            color = defaultStyles.bars[0].downColor;
          }
        }
        return { color: color };
      }
    });
    return figures;
  },
  calc: function (dataList, indicator) {
    var params = indicator.calcParams;
    var volumes = [];
    return dataList.map(function (kLineData, i) {
      var vol = kLineData.volume !== undefined && kLineData.volume !== null ? kLineData.volume : 0;
      var result = { volume: vol };
      volumes.push(vol);
      params.forEach(function (p, j) {
        if (i >= p - 1) {
          var sum = 0;
          for (var x = i - p + 1; x <= i; x++) {
            sum += volumes[x];
          }
          result['ma' + (j + 1)] = sum / p;
        }
      });
      return result;
    });
  }
});

const props = defineProps({
  // 價格歷史資料 (支援 snake_case 或 camelCase 屬性)
  prices: {
    type: Array,
    required: true,
    default: () => []
  },
  // 主題色: 'dark' | 'light'
  theme: {
    type: String,
    default: 'dark',
    validator: (val) => ['dark', 'light'].includes(val)
  },
  // K線週期: 'daily' | 'weekly' | 'monthly'
  timeframe: {
    type: String,
    default: 'daily',
    validator: (val) => ['daily', 'weekly', 'monthly'].includes(val)
  },
  // 股票代號
  stockId: {
    type: String,
    default: ''
  },
  // 股票名稱
  stockName: {
    type: String,
    default: ''
  }
})

const emit = defineEmits(['update:timeframe', 'change-timeframe'])

const chartContainerRef = ref(null)
let chartInstance = null
const currentHoveredData = ref(null)

// 格式化傳入的價格資料以符合 KlineCharts 規格
const formattedPrices = computed(() => {
  if (!props.prices) return []
  return props.prices.map(item => {
    const ts = item.timestamp || (item.trade_date ? new Date(item.trade_date).getTime() : 0)
    return {
      timestamp: ts,
      open: Number(item.open),
      high: Number(item.high),
      low: Number(item.low),
      close: Number(item.close),
      volume: Number(item.volume),
      limitUp: Number(item.limitUp ?? item.limit_up ?? 0),
      limitDown: Number(item.limitDown ?? item.limit_down ?? 0)
    }
  }).sort((a, b) => a.timestamp - b.timestamp)
})

// 當前顯示在指標看板的資料點 (滑鼠懸停優先，否則預設為最新一筆)
const activeData = computed(() => {
  if (currentHoveredData.value) {
    return currentHoveredData.value
  }
  if (formattedPrices.value.length > 0) {
    return formattedPrices.value[formattedPrices.value.length - 1]
  }
  return null
})

// 取得前一日收盤價以估計漲跌幅
const prevClose = computed(() => {
  const data = activeData.value
  if (!data || formattedPrices.value.length === 0) return 0
  
  const idx = formattedPrices.value.findIndex(item => item.timestamp === data.timestamp)
  if (idx > 0) {
    return formattedPrices.value[idx - 1].close
  }
  return data.open
})

// 當前 K 線收盤的漲跌值
const priceChange = computed(() => {
  if (!activeData.value) return 0
  return activeData.value.close - prevClose.value
})

// 當前 K 線收盤的漲跌幅百分比
const priceChangePercent = computed(() => {
  if (!activeData.value || prevClose.value === 0) return 0
  return (priceChange.value / prevClose.value) * 100
})

// 日期格式化：YYYY/MM/DD
const activeDataDateStr = computed(() => {
  const data = activeData.value
  if (!data) return ''
  const ts = data.timestamp || (data.trade_date ? new Date(data.trade_date).getTime() : null)
  if (!ts) return ''
  return formatDateStr(ts)
})

function formatDateStr(timestamp) {
  const date = new Date(timestamp)
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}/${month}/${day}`
}

// 根據價格是否漲停、跌停、或漲跌判斷 class
const getPriceClass = (price) => {
  if (!activeData.value) return ''
  const limitUp = activeData.value.limitUp
  const limitDown = activeData.value.limitDown
  const prev = prevClose.value

  // 漲停
  if (limitUp && Math.abs(price - limitUp) < 0.01) {
    return 'bg-red-600 text-white px-1.5 py-0.5 rounded font-bold'
  }
  // 跌停
  if (limitDown && Math.abs(price - limitDown) < 0.01) {
    return 'bg-green-700 text-white px-1.5 py-0.5 rounded font-bold'
  }

  if (price > prev) {
    return props.theme === 'light' ? 'text-red-600' : 'text-red-400'
  } else if (price < prev) {
    return props.theme === 'light' ? 'text-green-700' : 'text-green-400'
  } else {
    return props.theme === 'light' ? 'text-nature-900 font-semibold' : 'text-nature-300 font-semibold'
  }
}

const getChangeClass = (change) => {
  if (change > 0) {
    return props.theme === 'light' ? 'text-red-600' : 'text-red-400'
  } else if (change < 0) {
    return props.theme === 'light' ? 'text-green-700' : 'text-green-400'
  } else {
    return props.theme === 'light' ? 'text-nature-900 font-semibold' : 'text-nature-300 font-semibold'
  }
}

const switchTimeframe = (tf) => {
  emit('update:timeframe', tf)
  emit('change-timeframe', tf)
}

// 產生圖表主題配色設定
function getThemeStyles(theme) {
  const isLight = theme === 'light'
  return {
    grid: {
      show: true,
      horizontal: {
        show: true,
        size: 1,
        color: isLight ? '#EEEEEE' : '#2B3139',
        style: 'dash',
        dashValue: [2, 2]
      },
      vertical: {
        show: true,
        size: 1,
        color: isLight ? '#EEEEEE' : '#2B3139',
        style: 'dash',
        dashValue: [2, 2]
      }
    },
    candle: {
      type: 'candle_solid',
      bar: {
        upColor: isLight ? '#FF333A' : '#EF5350',          // 漲 (台股紅)
        downColor: isLight ? '#00A600' : '#26A69A',        // 跌 (台股綠)
        noChangeColor: isLight ? '#666666' : '#555555',    // 平盤
        upBorderColor: isLight ? '#FF333A' : '#EF5350',
        downBorderColor: isLight ? '#00A600' : '#26A69A',
        noChangeBorderColor: isLight ? '#666666' : '#555555',
        upWickColor: isLight ? '#FF333A' : '#EF5350',
        downWickColor: isLight ? '#00A600' : '#26A69A',
        noChangeWickColor: isLight ? '#666666' : '#555555'
      },
      tooltip: {
        showRule: 'none', // 關閉 Canvas 內建的 OHLCV 文字，改由 Vue DOM info-bar 展示
        labels: ['時間: ', '開: ', '收: ', '高: ', '低: ', '量: '],
        values: null,
        text: {
          color: isLight ? '#333333' : '#9BA2AE',
          family: "'Noto Sans TC', 'Roboto', sans-serif"
        }
      },
      priceMark: {
        show: true,
        last: {
          show: true,
          upColor: isLight ? '#FF333A' : '#EF5350',          // 漲 (台股紅)
          downColor: isLight ? '#00A600' : '#26A69A',        // 跌 (台股綠)
          noChangeColor: isLight ? '#666666' : '#95A5A6',    // 平盤 (灰)
          line: {
            show: true,
            style: 'dashed',
            dashedValue: [2, 2],
            size: 1
          },
          text: {
            show: true,
            color: '#FFFFFF',
            family: "'Noto Sans TC', 'Roboto', sans-serif",
            size: 12
          }
        }
      }
    },
    xAxis: {
      tickText: {
        color: isLight ? '#555555' : '#76808F',
        family: "'Noto Sans TC', 'Roboto', sans-serif"
      }
    },
    yAxis: {
      tickText: {
        color: isLight ? '#555555' : '#76808F',
        family: "'Noto Sans TC', 'Roboto', sans-serif"
      }
    },
    indicator: {
      ohlc: {
        upColor: isLight ? '#FF333A' : '#EF5350',
        downColor: isLight ? '#00A600' : '#26A69A'
      },
      tooltip: {
        showRule: 'always', // 顯示均線指標參數/值在 Legend
        showName: true,
        showParams: true,
        text: {
          color: isLight ? '#333333' : '#9BA2AE',
          family: "'Noto Sans TC', 'Roboto', sans-serif",
          size: 12
        }
      },
      lines: [
        { color: isLight ? '#5A98D3' : '#45B0E6' }, // MA5
        { color: isLight ? '#8E44AD' : '#B052CA' }, // MA10
        { color: isLight ? '#E67E22' : '#FF9800' }, // MA20
        { color: isLight ? '#F1C40F' : '#FFE066' }, // MA60
        { color: isLight ? '#A04000' : '#FF7043' }, // MA120
        { color: isLight ? '#7F8C8D' : '#95A5A6' }  // MA240
      ]
    },
    crosshair: {
      horizontal: {
        line: {
          color: isLight ? '#555555' : '#76808F',
          style: 'solid'
        },
        text: {
          backgroundColor: isLight ? '#222222' : '#434651',
          color: '#FFFFFF',
          family: "'Noto Sans TC', 'Roboto', sans-serif"
        }
      },
      vertical: {
        line: {
          color: isLight ? '#555555' : '#76808F',
          style: 'solid'
        },
        text: {
          backgroundColor: isLight ? '#222222' : '#434651',
          color: '#FFFFFF',
          family: "'Noto Sans TC', 'Roboto', sans-serif"
        }
      }
    }
  }
}

onMounted(() => {
  if (!chartContainerRef.value) return

  // 初始化 KlineCharts
  chartInstance = init(chartContainerRef.value, {
    customApi: {
      formatDate: (dateTimeFormat, timestamp, format, type) => {
        return formatDateStr(timestamp)
      }
    }
  })

  // 套用對應主題樣式
  chartInstance.setStyles(getThemeStyles(props.theme))

  // 在主圖 (candle_pane) 載入 MA 均線
  chartInstance.createIndicator('MA', true, {
    id: 'candle_pane',
    calcParams: [5, 10, 20, 60, 120, 240]
  })

  // 在副圖 (volume_pane) 載入成交量成交均量 VOL
  chartInstance.createIndicator('VOL', false, {
    id: 'volume_pane',
    calcParams: [5, 20],
    height: 120
  })

  // 載入資料
  if (formattedPrices.value.length > 0) {
    chartInstance.applyNewData(formattedPrices.value)
  }

  // 訂閱十字線移動，動態更新頂部的 OHLCV 看板
  chartInstance.subscribeAction('onCrosshairChange', (params) => {
    if (params && params.kLineData) {
      currentHoveredData.value = params.kLineData
    } else {
      currentHoveredData.value = null
    }
  })
})

onUnmounted(() => {
  if (chartInstance) {
    dispose(chartContainerRef.value)
    chartInstance = null
  }
})

// 監聽傳入的價格資料變動，重新套用到圖表
watch(formattedPrices, (newVal) => {
  if (chartInstance) {
    chartInstance.applyNewData(newVal)
  }
}, { deep: true })

// 監聽主題變更，更新 Canvas 配色
watch(() => props.theme, (newTheme) => {
  if (chartInstance) {
    chartInstance.setStyles(getThemeStyles(newTheme))
  }
})
</script>

<style scoped>
/* Scoped adjustments if any */
</style>
