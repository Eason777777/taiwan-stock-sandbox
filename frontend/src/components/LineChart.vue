<template>
  <div class="w-full bg-nature-900 border-3 sm:border-6 md:border-1 border-nature-500 rounded-[10px] p-4 sm:p-6 text-nature-100 font-sans relative select-none">
    <div class="flex items-center justify-between mb-4 flex-wrap gap-2">
      <h3 class="text-sm sm:text-lg font-bold text-white flex items-center gap-2">
        資產趨勢與交易紀錄分析
      </h3>
      <span class="text-[10px] sm:text-xs text-nature-300">
        （滑鼠懸停可查看當日交易與帳務細節）
      </span>
    </div>

    <!-- 圖表與 Tooltip 的專屬相對定位容器，以確保 X/Y 坐標精準 1:1 對齊 -->
    <div class="relative w-full h-[320px] sm:h-[400px]">
      <!-- ECharts 圖表容器 -->
      <div ref="chartRef" class="w-full h-full"></div>

      <!-- 自訂 Vue Tooltip (絕對定位，具備智慧型左右邊界判斷以防跑出畫面，點擊卡片內部阻止冒泡以防觸發解鎖) -->
      <div 
        v-if="tooltip.show && activeData"
        @click.stop
        class="absolute z-50 p-3 sm:p-4 bg-nature-900/95 backdrop-blur-md border border-nature-500 rounded-[8px] shadow-2xl w-[280px] sm:w-80 max-w-[calc(100%-16px)] max-h-[250px] sm:max-h-[300px] overflow-y-auto pointer-events-auto text-nature-100 scrollbar-thin scrollbar-thumb-nature-500"
        :style="{ left: tooltip.x + 'px', top: tooltip.y + 'px' }"
      >
        <!-- 日期標題 -->
        <div class="font-bold border-b border-nature-600 pb-2 mb-2 text-white flex justify-between items-center text-xs sm:text-sm">
          <span>{{ activeData.date }}</span>
          <div class="flex items-center gap-1.5">
            <span v-if="tooltip.isLocked" class="text-[9px] text-amber-400 bg-amber-500/20 px-1.5 py-0.5 rounded font-normal animate-pulse">
              已鎖定
            </span>
            <button 
              v-if="tooltip.isLocked" 
              @click.stop="unlockTooltip" 
              class="text-nature-300 hover:text-white cursor-pointer text-xs font-bold px-1.5 py-0.5 hover:bg-nature-700 rounded transition-colors"
              title="點擊解鎖"
            >
              ✕
            </button>
            <span v-else class="text-[9px] text-nature-300 bg-nature-700 px-1.5 py-0.5 rounded">明細</span>
          </div>
        </div>
        
        <!-- 帳戶餘額與市值資訊 -->
        <div class="space-y-1.5 text-xs mb-3">
          <div class="flex justify-between">
            <span class="text-nature-300">存款戶餘額：</span>
            <span class="font-bold text-blue-400">${{ activeData.deposit.toLocaleString() }}</span>
          </div>
          <div class="flex justify-between">
            <span class="text-nature-300">交割戶餘額：</span>
            <span class="font-bold text-emerald-400">${{ activeData.settlement.toLocaleString() }}</span>
          </div>
          <div class="flex justify-between">
            <span class="text-nature-300">持股總市值：</span>
            <span class="font-bold text-purple-400">${{ activeData.holdingsValue.toLocaleString() }}</span>
          </div>
          <div class="flex justify-between border-t border-nature-700 pt-1.5 font-bold text-amber-400 text-sm">
            <span>資產總額：</span>
            <span>${{ activeData.totalAssets.toLocaleString() }}</span>
          </div>
        </div>

        <!-- 當日轉帳與存取款紀錄 -->
        <div class="border-t border-nature-700 pt-2 mb-3">
          <h4 class="text-[11px] font-bold text-nature-400 mb-1.5">
            當日轉帳與存取款紀錄
          </h4>
          <div v-if="!activeData.transfers.length" class="text-[10px] text-nature-400 italic">無轉帳與存取款紀錄</div>
          <div v-else class="space-y-1.5">
            <div 
              v-for="tx in activeData.transfers" 
              :key="tx.seq"
              :class="[
                'p-2 rounded text-[11px] bg-nature-800 border-l-3',
                isDeposit(tx.change_type) ? 'border-emerald-500' : 'border-red-500'
              ]"
            >
              <div class="flex justify-between font-medium">
                <span>{{ formatAccountType(tx.account_type) }} - {{ formatChangeType(tx.change_type) }}</span>
                <span :class="isDeposit(tx.change_type) ? 'text-emerald-400' : 'text-red-400'">
                  {{ isDeposit(tx.change_type) ? '+' : '-' }}${{ parseFloat(tx.amount).toLocaleString() }}
                </span>
              </div>
              <div class="text-[9px] text-nature-400 mt-1">{{ tx.note || '-' }}</div>
            </div>
          </div>
        </div>

        <!-- 當日委託單 -->
        <div class="border-t border-nature-700 pt-2 mb-3">
          <h4 class="text-[11px] font-bold text-nature-400 mb-1.5">
            當日委託單
          </h4>
          <div v-if="!activeData.orders.length" class="text-[10px] text-nature-400 italic">無委託紀錄</div>
          <div v-else class="space-y-1.5">
            <div 
              v-for="order in activeData.orders" 
              :key="order.order_id"
              :class="[
                'p-2 rounded text-[11px] border-l-3 bg-nature-800',
                order.side === 'BUY' ? 'border-red-500' : 'border-emerald-500'
              ]"
            >
              <div class="flex justify-between font-medium">
                <span>{{ order.stock_name_zh || '未知股票' }} ({{ order.stock_id }})</span>
                <span :class="order.side === 'BUY' ? 'text-red-400' : 'text-emerald-400'">
                  {{ order.side === 'BUY' ? '買進' : '賣出' }}
                </span>
              </div>
              <div class="flex justify-between text-nature-300 mt-1">
                <span>{{ order.price !== null ? order.price + '元' : '市價' }} / {{ order.quantity }}張</span>
                <span class="bg-nature-700 text-nature-200 px-1 rounded text-[9px]">{{ formatStatus(order.status) }}</span>
              </div>
            </div>
          </div>
        </div>

        <!-- 當日成交紀錄 -->
        <div class="border-t border-nature-700 pt-2">
          <h4 class="text-[11px] font-bold text-nature-400 mb-1.5">
            當日成交紀錄
          </h4>
          <div v-if="!activeData.deals.length" class="text-[10px] text-nature-400 italic">無成交紀錄</div>
          <div v-else class="space-y-1.5">
            <div 
              v-for="deal in activeData.deals" 
              :key="deal.order_id"
              :class="[
                'p-2 rounded text-[11px] bg-nature-800 border-l-3',
                deal.side === 'BUY' ? 'border-red-500' : 'border-emerald-500'
              ]"
            >
              <div class="flex justify-between font-medium">
                <span>{{ deal.stock_name_zh }} ({{ deal.stock_id }})</span>
                <span :class="deal.side === 'BUY' ? 'text-red-400' : 'text-emerald-400'">
                  {{ deal.side === 'BUY' ? '買進成交' : '賣出成交' }}
                </span>
              </div>
              <div class="flex justify-between text-nature-300 mt-1">
                <span>成交: {{ deal.exec_price }}元 / {{ deal.quantity }}張</span>
                <span class="text-[9px] text-nature-400">時段: {{ formatPhase(deal.phase) }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted, computed, watch, nextTick } from 'vue';
import * as echarts from 'echarts';

const props = defineProps({
  dates: {
    type: Array,
    required: true,
    default: () => []
  },
  depositData: {
    type: Array,
    required: true,
    default: () => []
  },
  settlementData: {
    type: Array,
    required: true,
    default: () => []
  },
  holdingsData: {
    type: Array,
    required: true,
    default: () => []
  },
  totalAssetsData: {
    type: Array,
    required: true,
    default: () => []
  },
  dailyTransactions: {
    type: Object,
    required: true,
    default: () => ({})
  }
});

const chartRef = ref(null);
let myChart = null;

// Tooltip 浮動座標、當前選取日期與鎖定狀態
const tooltip = reactive({
  show: false,
  x: 0,
  y: 0,
  date: '',
  isLocked: false // 是否鎖定 Tooltip 位置與內容
});

// 解鎖 Tooltip 方法
const unlockTooltip = () => {
  tooltip.isLocked = false;
  tooltip.show = false;
};

// 當前懸停點的詳細數據
const activeData = computed(() => {
  if (!tooltip.date) return null;
  const idx = props.dates.indexOf(tooltip.date);
  if (idx === -1) return null;
  
  const tx = props.dailyTransactions[tooltip.date] || { orders: [], deals: [], transfers: [] };
  return {
    date: tooltip.date,
    deposit: props.depositData[idx] || 0,
    settlement: props.settlementData[idx] || 0,
    holdingsValue: props.holdingsData[idx] || 0,
    totalAssets: props.totalAssetsData[idx] || 0,
    orders: tx.orders || [],
    deals: tx.deals || [],
    transfers: tx.transfers || []
  };
});

// 格式化帳戶類型
const formatAccountType = (type) => {
  if (type === 'SAVINGS') return '存款戶';
  if (type === 'TRADING') return '交割戶';
  return type;
};

// 格式化資金變動類型
const formatChangeType = (type) => {
  const typeMap = {
    'INITIAL_DEPOSIT': '開戶存入',
    'TRANSFER_IN': '帳戶轉入',
    'TRANSFER_OUT': '帳戶轉出'
  };
  return typeMap[type] || type;
};

// 判斷是否為存入/轉入
const isDeposit = (type) => ['TRANSFER_IN', 'INITIAL_DEPOSIT'].includes(type);

// 格式化訂單狀態
const formatStatus = (status) => {
  const statusMap = {
    'PENDING': '已委託',
    'FILLED': '全部成交',
    'PARTIAL_FILLED': '部分成交',
    'CANCELLED': '已撤單',
    'EXPIRED': '已過期'
  };
  return statusMap[status] || status;
};

// 格式化交易時段/階段
const formatPhase = (phase) => {
  const phaseMap = {
    'PRE_MARKET': '盤前',
    'INTRADAY': '盤中',
    'POST_MARKET': '盤後',
    'CLOSED': '已收盤'
  };
  return phaseMap[phase] || phase;
};

const initChart = () => {
  if (!chartRef.value) return;

  myChart = echarts.init(chartRef.value);

  const option = {
    tooltip: {
      show: true,
      showContent: false, // 隱藏 ECharts 預設黑框，但保持軸線指示線與事件觸發
      trigger: 'axis',
      axisPointer: {
        type: 'line',
        lineStyle: {
          color: '#f59e0b',
          width: 1.5,
          type: 'dashed'
        }
      }
    },
    toolbox: {
      show: true,
      right: '5%',
      top: '2%',
      iconStyle: {
        borderColor: '#94a3b8'
      },
      emphasis: {
        iconStyle: {
          borderColor: '#f59e0b'
        }
      },
      feature: {
        dataZoom: {
          title: {
            zoom: '區域框選縮放',
            back: '還原縮放'
          }
        },
        restore: {
          title: '重設'
        }
      }
    },
    legend: {
      data: ['存款戶餘額', '交割戶餘額', '持股總市值', '資產總額'],
      textStyle: { color: '#e2e8f0' },
      bottom: 0,
      icon: 'roundRect'
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '12%', // 調整底部間距以容納圖例
      top: '12%',    // 增加頂部間距防工具箱遮擋
      containLabel: true
    },
    dataZoom: [
      {
        type: 'inside', // 支援滾輪縮放 X 軸
        xAxisIndex: [0]
      },
      {
        type: 'inside', // 支援滾輪縮放 Y 軸
        yAxisIndex: [0]
      }
    ],
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: props.dates,
      axisLabel: { 
        color: '#94a3b8',
        fontSize: 10
      },
      axisLine: { lineStyle: { color: '#475569' } }
    },
    yAxis: {
      type: 'value',
      axisLabel: {
        color: '#94a3b8',
        fontSize: 10,
        formatter: (val) => `$${val.toLocaleString()}`
      },
      axisLine: { lineStyle: { color: '#475569' } },
      splitLine: { lineStyle: { color: '#334155' } }
    },
    series: [
      {
        name: '存款戶餘額',
        type: 'line',
        data: props.depositData,
        smooth: true,
        showSymbol: false,
        itemStyle: { color: '#3b82f6' },
        lineStyle: { width: 2 }
      },
      {
        name: '交割戶餘額',
        type: 'line',
        data: props.settlementData,
        smooth: true,
        showSymbol: false,
        itemStyle: { color: '#10b981' },
        lineStyle: { width: 2 }
      },
      {
        name: '持股總市值',
        type: 'line',
        data: props.holdingsData,
        smooth: true,
        showSymbol: false,
        itemStyle: { color: '#a855f7' },
        lineStyle: { width: 2 }
      },
      {
        name: '資產總額',
        type: 'line',
        data: props.totalAssetsData,
        smooth: true,
        showSymbol: true,
        symbolSize: 6,
        itemStyle: { color: '#f59e0b' },
        lineStyle: { width: 3.5 }
      }
    ]
  };

  myChart.setOption(option);

  // 1. 監聽圖表 axisPointer 移動，僅更新當前資料點與顯示狀態 (被鎖定時不動作)
  myChart.on('updateAxisPointer', (event) => {
    if (tooltip.isLocked) return;
    
    if (!event.axesInfo || event.axesInfo.length === 0) {
      tooltip.show = false;
      return;
    }
    
    const targetPoint = event.axesInfo[0];
    const dataIndex = targetPoint.value;
    const date = props.dates[dataIndex];
    if (!date) return;

    tooltip.date = date;
    tooltip.show = true;
  });

  // 2. 監聽 ZRender 的滑鼠移動事件，動態移動 Tooltip (被鎖定時不動作)
  myChart.getZr().on('mousemove', (params) => {
    if (tooltip.isLocked) return;

    const x = params.offsetX;
    const y = params.offsetY;

    const containerWidth = chartRef.value.clientWidth;
    const containerHeight = chartRef.value.clientHeight;

    // 依據容器寬度自適應 Tooltip 的計算寬度與高度 (與 CSS 中 w-[280px] sm:w-80 max-w-[calc(100%-16px)] 一致)
    const isMobile = containerWidth < 640;
    const tooltipWidth = isMobile ? Math.min(280, containerWidth - 16) : Math.min(320, containerWidth - 16);
    const tooltipHeight = isMobile ? 240 : 280;

    // X 軸定位：預設放在游標右側，右側放不下則放左側
    let targetX = x + 15;
    if (targetX + tooltipWidth + 15 > containerWidth) {
      targetX = x - tooltipWidth - 15;
    }

    // Y 軸定位：預設將 tooltip 放在游標上方，上方放不下則放下方
    let targetY = y - tooltipHeight - 15;
    if (targetY < 0) {
      targetY = y + 15;
    }

    // 強制限制於畫布範圍內 (Snap to border)，預留 8px 的邊界間距
    tooltip.x = Math.max(8, Math.min(targetX, containerWidth - tooltipWidth - 8));
    tooltip.y = Math.max(8, Math.min(targetY, containerHeight - tooltipHeight - 8));
  });

  // 3. 點擊圖表空白處或資料點，以切換鎖定狀態
  myChart.getZr().on('click', (params) => {
    // 若目前已經是鎖定狀態，點擊圖表任意處即可解鎖
    if (tooltip.isLocked) {
      tooltip.isLocked = false;
      return;
    }
    
    // 若非鎖定狀態且當前 Tooltip 有顯示，點擊則將其「釘住鎖定」
    if (tooltip.show) {
      tooltip.isLocked = true;
    }
  });

  // 4. 當滑鼠移出畫布時，非鎖定狀態下才關閉 Tooltip
  myChart.getZr().on('globalout', () => {
    if (tooltip.isLocked) return;
    tooltip.show = false;
  });
};

const handleResize = () => {
  if (myChart) myChart.resize();
};

// 監聽資料異動，即時重繪圖表
watch(
  () => [props.dates, props.depositData, props.settlementData, props.holdingsData, props.totalAssetsData],
  () => {
    if (myChart) {
      myChart.setOption({
        xAxis: { data: props.dates },
        series: [
          { data: props.depositData },
          { data: props.settlementData },
          { data: props.holdingsData },
          { data: props.totalAssetsData }
        ]
      });
    }
  },
  { deep: true }
);

onMounted(async () => {
  await nextTick();
  initChart();
  window.addEventListener('resize', handleResize);
});

onUnmounted(() => {
  window.removeEventListener('resize', handleResize);
  if (myChart) {
    myChart.dispose();
  }
});
</script>

<style scoped>
/* 隱藏滾動條但保持滾動功能 (針對 Tooltip) */
.scrollbar-thin::-webkit-scrollbar {
  width: 4px;
}
.scrollbar-thin::-webkit-scrollbar-track {
  background: transparent;
}
.scrollbar-thin::-webkit-scrollbar-thumb {
  background-color: var(--color-nature-500, #a1a1aa);
  border-radius: 10px;
}
</style>
