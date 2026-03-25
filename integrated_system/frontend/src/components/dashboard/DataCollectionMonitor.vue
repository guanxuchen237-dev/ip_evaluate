<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch, computed } from "vue";
import { 
  Database, RefreshCw, Wifi, WifiOff, Server, 
  Activity, CheckCircle, AlertTriangle, Clock,
  ArrowDownToLine, Zap, TrendingUp
} from "lucide-vue-next";
import * as echarts from 'echarts';
import { useResizeObserver } from '@vueuse/core';

interface DataSource {
  id: string;
  name: string;
  nameCn: string;
  status: "active" | "syncing" | "error" | "idle";
  lastSync: string;
  recordsToday: number;
  progress?: number;
}

interface TrendDataPoint {
  time: string;
  total: number;
  qidian: number;
  weibo: number;
  jjwxc: number;
}

const initialDataSources: DataSource[] = [
  { id: "qidian", name: "Qidian", nameCn: "起点中文网", status: "active", lastSync: "2分钟前", recordsToday: 12847 },
  { id: "zongheng", name: "Zongheng", nameCn: "纵横小说", status: "syncing", lastSync: "同步中...", recordsToday: 8234, progress: 67 },
  { id: "jjwxc", name: "JJWXC", nameCn: "晋江文学城", status: "active", lastSync: "5分钟前", recordsToday: 9562 },
  { id: "weibo", name: "Weibo", nameCn: "微博舆情", status: "active", lastSync: "1分钟前", recordsToday: 45231 },
  { id: "douban", name: "Douban", nameCn: "豆瓣评分", status: "idle", lastSync: "30分钟前", recordsToday: 3421 },
  { id: "bilibili", name: "Bilibili", nameCn: "B站热度", status: "error", lastSync: "失败", recordsToday: 0 },
];

const generateInitialTrendData = (): TrendDataPoint[] => {
  const data: TrendDataPoint[] = [];
  for (let i = 23; i >= 0; i--) {
    const hour = new Date();
    hour.setHours(hour.getHours() - i);
    data.push({
      time: `${hour.getHours().toString().padStart(2, '0')}:00`,
      total: Math.floor(2000 + Math.random() * 3000),
      qidian: Math.floor(500 + Math.random() * 800),
      weibo: Math.floor(800 + Math.random() * 1500),
      jjwxc: Math.floor(400 + Math.random() * 600),
    });
  }
  return data;
};

import axios from 'axios';

const dataSources = ref<DataSource[]>(initialDataSources);
const totalRecords = ref(0);
const isRefreshing = ref(false);
const showTrendChart = ref(true);
const chartRef = ref<HTMLElement | null>(null);
let chartInstance: echarts.ECharts | null = null;

// API Fetch
const fetchStats = async () => {
  try {
    const res = await axios.get('http://localhost:5000/api/stats/overview');
    if (res.data) {
       // Assuming res.data has total_novels or similar
       totalRecords.value = res.data.total_novels || 79295;
    }
  } catch (e) {
    console.error("Failed to fetch stats", e);
    // Fallback if API fails
    if (totalRecords.value === 0) totalRecords.value = 79295; 
  }
};

// Simulation Logic
let intervalId: any;
let trendIntervalId: any;

onMounted(() => {
  fetchStats();
  initChart();
  
  intervalId = setInterval(() => {
    dataSources.value = dataSources.value.map(source => {
      if (source.status === "syncing" && source.progress !== undefined) {
        const newProgress = source.progress + Math.random() * 5;
        if (newProgress >= 100) {
          return { ...source, status: "active", lastSync: "刚刚", progress: undefined, recordsToday: source.recordsToday + Math.floor(Math.random() * 100) };
        }
        return { ...source, progress: Math.min(99, newProgress) };
      }
      if (source.status === "active" && Math.random() > 0.7) {
        const newRecords = Math.floor(Math.random() * 50);
        totalRecords.value += newRecords;
        return { ...source, recordsToday: source.recordsToday + newRecords };
      }
      return source;
    });
  }, 1500);

  trendIntervalId = setInterval(() => {
    updateChartData();
  }, 10000);
});

onUnmounted(() => {
  clearInterval(intervalId);
  clearInterval(trendIntervalId);
  chartInstance?.dispose();
});

const chartData = ref(generateInitialTrendData());

function initChart() {
  if (!chartRef.value) return;
  
  chartInstance = echarts.init(chartRef.value);
  setChartOption();
}

function updateChartData() {
  const now = new Date();
  const newPoint = {
    time: `${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}`,
    total: Math.floor(2000 + Math.random() * 3000),
    qidian: Math.floor(500 + Math.random() * 800),
    weibo: Math.floor(800 + Math.random() * 1500),
    jjwxc: Math.floor(400 + Math.random() * 600),
  };
  
  chartData.value = [...chartData.value.slice(1), newPoint];
  setChartOption();
}

function setChartOption() {
  if (!chartInstance) return;
  
  const option = {
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'hsl(var(--background))',
      borderColor: 'hsl(var(--border))',
      textStyle: { color: 'hsl(var(--foreground))' }
    },
    grid: { top: 10, right: 10, left: 0, bottom: 0, containLabel: true },
    xAxis: {
      type: 'category',
      data: chartData.value.map(d => d.time),
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: { color: 'hsl(var(--muted-foreground))', fontSize: 10 }
    },
    yAxis: {
      type: 'value',
      axisLine: { show: false },
      splitLine: { show: false },
      axisLabel: { color: 'hsl(var(--muted-foreground))', fontSize: 10 }
    },
    series: [
      {
        name: '总量',
        type: 'line',
        smooth: true,
        showSymbol: false,
        stack: 'Total',
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0.05, color: 'rgba(var(--chart-cyan-rgb), 0.4)' }, // approximation
            { offset: 0.95, color: 'rgba(var(--chart-cyan-rgb), 0)' }
          ])
        },
        lineStyle: { width: 2, color: 'hsl(190, 70%, 50%)' }, // chart-cyan
        data: chartData.value.map(d => d.total)
      },
      {
        name: '微博',
        type: 'line',
        smooth: true,
        showSymbol: false,
        stack: 'Total',
        areaStyle: { opacity: 0.3, color: 'hsl(0, 70%, 55%)' },
        lineStyle: { width: 1.5, color: 'hsl(0, 70%, 55%)' }, // chart-red
        data: chartData.value.map(d => d.weibo)
      },
      {
        name: '起点',
        type: 'line',
        smooth: true,
        showSymbol: false,
        stack: 'Total',
        areaStyle: { opacity: 0.3, color: 'hsl(210, 70%, 55%)' },
        lineStyle: { width: 1.5, color: 'hsl(210, 70%, 55%)' }, // chart-blue
        data: chartData.value.map(d => d.qidian)
      }
    ]
  };
  
  chartInstance.setOption(option);
}

useResizeObserver(chartRef, () => {
  chartInstance?.resize();
});

watch(showTrendChart, (val) => {
  if (val) {
    // Wait for DOM
    setTimeout(initChart, 100);
  } else {
    chartInstance?.dispose();
    chartInstance = null;
  }
});

const handleRefresh = () => {
  isRefreshing.value = true;
  setTimeout(() => {
    dataSources.value = dataSources.value.map(source => ({
      ...source,
      status: source.status === "error" ? "syncing" : source.status,
      progress: source.status === "error" ? 0 : source.progress,
    }));
    isRefreshing.value = false;
  }, 1000);
};

const getStatusIcon = (status: DataSource["status"]) => {
  switch (status) {
    case "active": return CheckCircle;
    case "syncing": return RefreshCw;
    case "error": return AlertTriangle;
    case "idle": return Clock;
  }
};

const getStatusColor = (status: DataSource["status"]) => {
  switch (status) {
    case "active": return "bg-chart-green/10 border-chart-green/30";
    case "syncing": return "bg-chart-blue/10 border-chart-blue/30";
    case "error": return "bg-chart-red/10 border-chart-red/30";
    case "idle": return "bg-chart-yellow/10 border-chart-yellow/30";
  }
};

const activeCount = computed(() => dataSources.value.filter(s => s.status === "active").length);
const errorCount = computed(() => dataSources.value.filter(s => s.status === "error").length);
</script>

<template>
  <div class="editorial-card rounded-3xl p-8 fangzheng-font">
    <!-- Header -->
    <div class="flex items-start justify-between mb-6">
      <div class="flex items-center gap-3">
        <div class="w-10 h-10 rounded-xl bg-chart-cyan/10 flex items-center justify-center">
          <Database class="w-5 h-5 text-chart-cyan" />
        </div>
        <div>
          <h3 class="editorial-headline text-xl text-foreground fangzheng-title">Data Pipeline</h3>
          <p class="text-sm text-muted-foreground fangzheng-text">实时数据采集监控</p>
        </div>
      </div>
      
      <button
        @click="handleRefresh"
        :disabled="isRefreshing"
        class="flex items-center gap-2 px-3 py-2 rounded-lg bg-white/50 hover:bg-white/70 border border-white/40 transition-all text-sm disabled:opacity-50"
      >
        <RefreshCw class="w-4 h-4" :class="{ 'animate-spin': isRefreshing }" />
        刷新
      </button>
    </div>

    <!-- Trend Chart Toggle -->
    <div class="flex items-center justify-between mb-4">
      <div class="flex items-center gap-2">
        <TrendingUp class="w-4 h-4 text-chart-cyan" />
        <span class="text-sm font-medium text-foreground">采集趋势</span>
      </div>
      <button
        @click="showTrendChart = !showTrendChart"
        class="text-xs text-muted-foreground hover:text-foreground transition-colors"
      >
        {{ showTrendChart ? "收起" : "展开" }}
      </button>
    </div>

    <!-- Trend Chart -->
    <div v-if="showTrendChart" class="mb-6 p-4 rounded-xl bg-white/30 border border-white/40">
      <div class="h-48" ref="chartRef"></div>
      <div class="flex items-center justify-center gap-6 mt-3">
        <div class="flex items-center gap-2">
          <div class="w-3 h-3 rounded-full bg-chart-cyan" />
          <span class="text-xs text-muted-foreground">总量</span>
        </div>
        <div class="flex items-center gap-2">
          <div class="w-3 h-3 rounded-full bg-chart-red" />
          <span class="text-xs text-muted-foreground">微博</span>
        </div>
        <div class="flex items-center gap-2">
          <div class="w-3 h-3 rounded-full bg-chart-blue" />
          <span class="text-xs text-muted-foreground">起点</span>
        </div>
      </div>
    </div>

    <!-- Stats row -->
    <div class="grid grid-cols-4 gap-4 mb-6">
      <div class="p-4 rounded-xl bg-gradient-to-br from-chart-green/10 to-chart-green/5 border border-chart-green/20">
        <div class="flex items-center gap-2 mb-2">
          <Wifi class="w-4 h-4 text-chart-green" />
          <span class="text-xs text-muted-foreground">在线数据源</span>
        </div>
        <p class="text-2xl font-bold text-foreground fangzheng-number">{{ activeCount }}/{{ dataSources.length }}</p>
      </div>
      
      <div class="p-4 rounded-xl bg-gradient-to-br from-chart-blue/10 to-chart-blue/5 border border-chart-blue/20">
        <div class="flex items-center gap-2 mb-2">
          <ArrowDownToLine class="w-4 h-4 text-chart-blue" />
          <span class="text-xs text-muted-foreground">今日采集</span>
        </div>
        <p class="text-2xl font-bold text-foreground fangzheng-number">{{ totalRecords.toLocaleString() }}</p>
      </div>
      
      <div class="p-4 rounded-xl bg-gradient-to-br from-chart-purple/10 to-chart-purple/5 border border-chart-purple/20">
        <div class="flex items-center gap-2 mb-2">
          <Zap class="w-4 h-4 text-chart-purple" />
          <span class="text-xs text-muted-foreground">处理速率</span>
        </div>
        <p class="text-2xl font-bold text-foreground fangzheng-number">847/s</p>
      </div>
      
      <div 
        class="p-4 rounded-xl border"
        :class="errorCount > 0 ? 'bg-gradient-to-br from-chart-red/10 to-chart-red/5 border-chart-red/20' : 'bg-gradient-to-br from-chart-green/10 to-chart-green/5 border-chart-green/20'"
      >
        <div class="flex items-center gap-2 mb-2">
          <component :is="errorCount > 0 ? WifiOff : Server" class="w-4 h-4" :class="errorCount > 0 ? 'text-chart-red' : 'text-chart-green'" />
          <span class="text-xs text-muted-foreground">异常源</span>
        </div>
        <p class="text-2xl font-bold fangzheng-number" :class="errorCount > 0 ? 'text-chart-red' : 'text-chart-green'">{{ errorCount }}</p>
      </div>
    </div>

    <!-- Data sources list -->
    <div class="space-y-3">
      <div 
        v-for="source in dataSources"
        :key="source.id"
        class="p-4 rounded-xl border transition-all"
        :class="getStatusColor(source.status)"
      >
        <div class="flex items-center justify-between mb-2">
          <div class="flex items-center gap-3">
            <component 
              :is="getStatusIcon(source.status)" 
              class="w-4 h-4" 
              :class="{
                'text-chart-green': source.status === 'active',
                'text-chart-blue animate-spin': source.status === 'syncing',
                'text-chart-red': source.status === 'error',
                'text-chart-yellow': source.status === 'idle'
              }"
            />
            <div>
              <span class="font-medium text-foreground">{{ source.nameCn }}</span>
              <span class="text-xs text-muted-foreground ml-2">{{ source.name }}</span>
            </div>
          </div>
          <div class="text-right">
            <p class="text-sm font-medium text-foreground">
              {{ source.recordsToday.toLocaleString() }} 条
            </p>
            <p class="text-xs text-muted-foreground">{{ source.lastSync }}</p>
          </div>
        </div>
        
        <div v-if="source.status === 'syncing' && source.progress !== undefined" class="mt-2">
          <div class="h-1.5 bg-white/30 rounded-full overflow-hidden">
            <div 
              class="h-full bg-gradient-to-r from-chart-blue to-chart-cyan transition-all duration-500"
              :style="{ width: `${source.progress}%` }"
            />
          </div>
          <p class="text-xs text-chart-blue mt-1">{{ Math.round(source.progress) }}% 完成</p>
        </div>
      </div>
    </div>

    <!-- Live activity indicator -->
    <div class="mt-6 pt-4 border-t border-white/20 flex items-center gap-3">
      <div class="flex items-center gap-2">
        <Activity class="w-4 h-4 text-chart-green animate-pulse" />
        <span class="text-sm text-muted-foreground">系统运行正常</span>
      </div>
      <div class="flex-1" />
      <span class="text-xs text-muted-foreground font-mono">上次更新: {{ new Date().toLocaleTimeString() }}</span>
    </div>
  </div>
</template>

<style scoped>
/* 方正字体 */
.fangzheng-font {
  font-family: '方正兰亭黑', 'FZLanTingHei', '方正黑体', 'FZHei', 'Microsoft YaHei', sans-serif;
}

.fangzheng-title {
  font-family: '方正兰亭黑', 'FZLanTingHei', '方正黑体', 'FZHei', 'Microsoft YaHei', sans-serif;
  font-weight: 600;
}

.fangzheng-text {
  font-family: '方正兰亭黑', 'FZLanTingHei', '方正黑体', 'FZHei', 'Microsoft YaHei', sans-serif;
}

.fangzheng-number {
  font-family: '方正兰亭黑', 'FZLanTingHei', '方正黑体', 'FZHei', 'Microsoft YaHei', sans-serif;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}
</style>
