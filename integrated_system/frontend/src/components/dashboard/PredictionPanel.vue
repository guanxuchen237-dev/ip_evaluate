<script setup lang="ts">
import { ref, computed, reactive } from 'vue';
import { Sparkles, Loader2, AlertTriangle, Trophy, Heart, BarChart3, BookOpen, TrendingUp, Award, Zap, ChevronRight, RefreshCw, Star, Target, FileText, Users, Crown, Upload, X, Database, LineChart, Lightbulb, Download } from "lucide-vue-next";
import axios from 'axios';

type PredictionMode = 'basic' | 'ranking' | 'engagement' | 'content';

const currentMode = ref<PredictionMode>('basic');

const modes = [
  { id: 'basic' as PredictionMode, label: '基本信息', icon: FileText, color: 'indigo' },
  { id: 'ranking' as PredictionMode, label: '月票排名', icon: Crown, color: 'amber' },
  { id: 'engagement' as PredictionMode, label: '收藏推荐', icon: Heart, color: 'rose' },
  { id: 'content' as PredictionMode, label: '内容质量', icon: BarChart3, color: 'emerald' },
];

const formData = reactive({
  title: '',
  platform: '起点',
  category: '玄幻',
  author: '',
  wordCount: 0,
  status: '连载',
  monthlyTickets: 0,
  ranking: 0,
  weekOverWeekGrowth: 0,
  collections: 0,
  recommendations: 0,
  comments: 0,
  followers: 0,
  chapterContent: '',
  synopsis: '',
});

const result = ref<any>(null);
const loading = ref(false);
const error = ref('');
const animatingScore = ref(0);
const uploadedFile = ref<File | null>(null);
const isDragging = ref(false);
const showTextarea = ref(false);

const categories = ['玄幻', '都市', '仙侠', '科幻', '历史', '游戏', '奇幻', '军事', '悬疑', '言情', '体育', '轻小说'];
const platforms = ['起点', '纵横'];
const statusOptions = ['连载', '完本', '断更'];

const API_BASE = 'http://localhost:5000/api';

const switchMode = (mode: PredictionMode) => {
  currentMode.value = mode;
};

const submitPrediction = async () => {
  if (!formData.title) {
    error.value = '请输入作品名称';
    return;
  }
  
  loading.value = true;
  error.value = '';
  result.value = null;
  animatingScore.value = 0;

  try {
    const payload = { mode: currentMode.value, ...formData };
    const res = await axios.post(`${API_BASE}/predict/simple`, payload);
    result.value = res.data;
    
    const targetScore = result.value.score || 0;
    const duration = 1200;
    const steps = 40;
    const increment = targetScore / steps;
    let current = 0;
    
    const timer = setInterval(() => {
      current += increment;
      if (current >= targetScore) {
        animatingScore.value = targetScore;
        clearInterval(timer);
      } else {
        animatingScore.value = Math.round(current * 10) / 10;
      }
    }, duration / steps);
    
  } catch (e: any) {
    error.value = e.response?.data?.error || '预测服务连接失败';
  } finally {
    loading.value = false;
  }
};

const reset = () => {
  result.value = null;
  currentMode.value = 'basic';
  animatingScore.value = 0;
  uploadedFile.value = null;
  isDragging.value = false;
  Object.assign(formData, {
    title: '', platform: '起点', category: '玄幻', author: '', wordCount: 0, status: '连载',
    monthlyTickets: 0, ranking: 0, weekOverWeekGrowth: 0,
    collections: 0, recommendations: 0, comments: 0, followers: 0,
    chapterContent: '', synopsis: ''
  });
};

const exportReport = () => {
  if (!result.value) return;
  
  // 格式化未来预测
  const futurePredText = result.value.future_predictions?.length 
    ? `未来3个月预测：\n${result.value.future_predictions.map((p: any) => `- ${p.year}/${p.month}月：预计${p.predicted_tickets?.toLocaleString()}票（${p.trend}）`).join('\n')}`
    : '';
  
  // 格式化历史数据
  const historyText = result.value.history?.length
    ? `历史月票数据：\n${result.value.history.map((h: any) => `- ${h.year}/${h.month}月：${h.monthly_tickets?.toLocaleString()}票`).join('\n')}`
    : '';
  
  const reportContent = `IP价值评估报告
================

作品信息：
- 书名：《${formData.title}》
- 平台：${formData.platform}
- 题材：${formData.category}
- 状态：${formData.status}
- 综合评分：${result.value.score?.toFixed(1)}分（${result.value.grade}级）

六维度评分：
${Object.entries(result.value.dimensions || {}).map(([k, v]) => `- ${k}：${v}分 - ${result.value.dimension_details?.[k] || ''}`).join('\n')}

${historyText}

${futurePredText}

评估报告：
${result.value.report || '暂无'}

${result.value.prediction ? `发展预测：\n${result.value.prediction}` : ''}

${result.value.suggestions?.length ? `优化建议：\n${result.value.suggestions.map((s: string, i: number) => `${i + 1}. ${s}`).join('\n')}` : ''}

生成时间：${new Date().toLocaleString()}
`;

  const blob = new Blob([reportContent], { type: 'text/markdown;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `IP评估报告_${formData.title}_${new Date().toISOString().slice(0, 10)}.md`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
};

const predictedLevel = computed(() => {
  const s = result.value?.score || 0;
  if (s >= 90) return { label: 'S级', sub: '神作', text: 'text-amber-600', bg: 'bg-amber-50', border: 'border-amber-200', ring: 'text-amber-500' };
  if (s >= 80) return { label: 'A+级', sub: '爆款', text: 'text-indigo-600', bg: 'bg-indigo-50', border: 'border-indigo-200', ring: 'text-indigo-500' };
  if (s >= 70) return { label: 'A级', sub: '精品', text: 'text-sky-600', bg: 'bg-sky-50', border: 'border-sky-200', ring: 'text-sky-500' };
  if (s >= 60) return { label: 'B级', sub: '潜力', text: 'text-emerald-600', bg: 'bg-emerald-50', border: 'border-emerald-200', ring: 'text-emerald-500' };
  if (s >= 50) return { label: 'C级', sub: '普通', text: 'text-slate-600', bg: 'bg-slate-50', border: 'border-slate-200', ring: 'text-slate-500' };
  return { label: 'D级', sub: '待观察', text: 'text-rose-600', bg: 'bg-rose-50', border: 'border-rose-200', ring: 'text-rose-500' };
});

const getPlatformHint = () => {
  return formData.platform === '起点' 
    ? '起点头部作品月票可达50万+，榜单竞争激烈' 
    : '纵横头部作品月票约3-5万，平台生态温和';
};

// 简单的Markdown渲染
const renderMarkdown = (text: string) => {
  if (!text) return '';
  return text
    .replace(/##\s+(.*)/g, '<h3 class="text-sm font-bold text-slate-800 mt-3 mb-2">$1</h3>')
    .replace(/###\s+(.*)/g, '<h4 class="text-xs font-semibold text-slate-700 mt-2 mb-1">$1</h4>')
    .replace(/\*\*(.*?)\*\*/g, '<strong class="text-slate-800">$1</strong>')
    .replace(/\n\n/g, '</p><p class="text-sm text-slate-600 leading-relaxed mt-2">')
    .replace(/\n/g, '<br>');
};

// 折线图辅助函数
const getMaxTickets = (history: any[]) => {
  return Math.max(...history.map(h => h.monthly_tickets || 0), 1);
};

const getPointX = (index: number, total: number) => {
  if (total <= 1) return 150;
  return (index / (total - 1)) * 280 + 10;
};

const getPointY = (tickets: number, history: any[]) => {
  const max = getMaxTickets(history);
  const padding = 10;
  const availableHeight = 80;
  return availableHeight - ((tickets || 0) / max) * availableHeight + padding;
};

const getLineChartPath = (history: any[], isArea: boolean) => {
  if (!history || history.length === 0) return '';
  
  const points = history.map((h, i) => ({
    x: getPointX(i, history.length),
    y: getPointY(h.monthly_tickets, history)
  }));
  
  if (points.length === 0) return '';
  
  const first = points[0];
  if (!first) return '';
  
  // Create smooth line using simple averaging
  let path = `M ${first.x} ${first.y}`;
  
  for (let i = 1; i < points.length; i++) {
    const prev = points[i - 1];
    const curr = points[i];
    if (!prev || !curr) continue;
    const midX = (prev.x + curr.x) / 2;
    path += ` C ${midX} ${prev.y}, ${midX} ${curr.y}, ${curr.x} ${curr.y}`;
  }
  
  if (isArea) {
    const last = points[points.length - 1];
    if (last && first) {
      path += ` L ${last.x} 100 L ${first.x} 100 Z`;
    }
  }
  
  return path;
};

// File upload handlers
const handleFileUpload = (event: Event) => {
  const input = event.target as HTMLInputElement;
  const file = input.files?.[0];
  if (file) {
    readFile(file);
  }
};

const handleDrop = (event: DragEvent) => {
  event.preventDefault();
  isDragging.value = false;
  const file = event.dataTransfer?.files[0];
  if (file && (file.type === 'text/plain' || file.name.endsWith('.txt') || file.name.endsWith('.md'))) {
    readFile(file);
  } else if (file) {
    error.value = '请上传文本文件 (.txt 或 .md)';
    setTimeout(() => error.value = '', 3000);
  }
};

const handleDragOver = (event: DragEvent) => {
  event.preventDefault();
  isDragging.value = true;
};

const handleDragLeave = () => {
  isDragging.value = false;
};

const readFile = (file: File) => {
  const reader = new FileReader();
  reader.onload = (e) => {
    formData.chapterContent = e.target?.result as string;
    uploadedFile.value = file;
  };
  reader.onerror = () => {
    error.value = '文件读取失败';
  };
  reader.readAsText(file, 'UTF-8');
};

const removeFile = () => {
  uploadedFile.value = null;
  formData.chapterContent = '';
};
</script>

<template>
  <div class="prediction-panel h-full flex flex-col p-5">
    
    <!-- Header -->
    <div class="flex items-center justify-between mb-6">
      <div class="flex items-center gap-3">
        <div class="w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center shadow-md">
          <Sparkles class="w-5 h-5 text-white" />
        </div>
        <div>
          <h2 class="text-lg font-bold text-slate-900">IP价值预测</h2>
          <p class="text-xs text-slate-500">基于多维度数据的智能评估</p>
        </div>
      </div>
      <div v-if="!result" class="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-emerald-50 border border-emerald-200">
        <span class="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
        <span class="text-xs font-medium text-emerald-600">AI就绪</span>
      </div>
    </div>

    <!-- Result View -->
    <div v-if="result" class="flex-1 flex flex-col overflow-hidden gap-4">
      
      <!-- Score Card -->
      <div class="bg-white/60 backdrop-blur-xl border border-white/40 rounded-2xl shadow-sm p-6">
        <div class="flex items-center gap-6">
          <!-- Score Circle -->
          <div class="relative w-28 h-28 flex-shrink-0">
            <svg class="w-full h-full -rotate-90" viewBox="0 0 100 100">
              <circle cx="50" cy="50" r="44" fill="none" stroke="rgb(241 245 249)" stroke-width="5" stroke-linecap="round" />
              <circle 
                cx="50" cy="50" r="44" 
                fill="none" 
                :stroke="'currentColor'"
                :class="predictedLevel.ring"
                stroke-width="5" 
                stroke-linecap="round"
                :stroke-dasharray="`${276 * (animatingScore / 100)}, 276`"
                class="transition-all duration-500"
              />
            </svg>
            <div class="absolute inset-0 flex flex-col items-center justify-center">
              <span class="text-3xl font-bold text-slate-900">{{ animatingScore.toFixed(1) }}</span>
              <span class="text-[10px] text-slate-400">综合评分</span>
            </div>
          </div>

          <!-- Info -->
          <div class="flex-1 min-w-0">
            <div class="flex items-center gap-2 mb-2">
              <span class="px-3 py-1 rounded-full text-sm font-bold border" :class="[predictedLevel.bg, predictedLevel.text, predictedLevel.border]">
                {{ predictedLevel.label }} · {{ predictedLevel.sub }}
              </span>
            </div>
            <h3 class="text-xl font-bold text-slate-900 truncate mb-2">{{ formData.title }}</h3>
            <div class="flex items-center gap-2 flex-wrap">
              <span class="px-2 py-1 rounded-md text-xs font-medium" 
                    :class="formData.platform === '起点' ? 'bg-blue-50 text-blue-600 border border-blue-200' : 'bg-rose-50 text-rose-600 border border-rose-200'">
                {{ formData.platform }}
              </span>
              <span class="px-2 py-1 rounded-md text-xs font-medium bg-slate-100 text-slate-600 border border-slate-200">
                {{ formData.category }}
              </span>
              <span class="px-2 py-1 rounded-md text-xs font-medium"
                    :class="formData.status === '连载' ? 'bg-emerald-50 text-emerald-600 border border-emerald-200' : 'bg-indigo-50 text-indigo-600 border border-indigo-200'">
                {{ formData.status }}
              </span>
            </div>
          </div>
        </div>
      </div>

      <!-- Scrollable Content -->
      <div class="flex-1 overflow-y-auto pr-1 space-y-4 custom-scrollbar">
        
        <!-- Dimensions -->
        <div v-if="result.dimensions" class="bg-white/60 backdrop-blur-xl border border-white/40 rounded-xl shadow-sm p-5">
          <h4 class="text-sm font-semibold text-slate-700 mb-4 flex items-center gap-2">
            <Target class="w-4 h-4 text-indigo-500" />
            六维度评判
          </h4>
          <div class="space-y-3">
            <div v-for="(val, key) in result.dimensions" :key="key" class="flex flex-col gap-1">
              <div class="flex items-center justify-between">
                <span class="text-sm font-medium text-slate-700">{{ key }}</span>
                <span class="text-sm font-bold text-indigo-600">{{ typeof val === 'number' ? val.toFixed(1) : val }}</span>
              </div>
              <div class="h-2 bg-slate-100 rounded-full overflow-hidden">
                <div class="h-full rounded-full transition-all duration-700"
                     :class="{
                       'bg-gradient-to-r from-emerald-400 to-emerald-600': val >= 20,
                       'bg-gradient-to-r from-indigo-400 to-purple-500': val >= 15 && val < 20,
                       'bg-gradient-to-r from-amber-400 to-amber-600': val < 15
                     }"
                     :style="{ width: `${Math.min(100, (val / 30) * 100)}%` }"></div>
              </div>
              <span v-if="result.dimension_details && result.dimension_details[key]" class="text-xs text-slate-400">{{ result.dimension_details[key] }}</span>
            </div>
          </div>
        </div>

        <!-- DB Match & History -->
        <div v-if="result.db_matched" class="bg-emerald-50/60 backdrop-blur-xl border border-emerald-200 rounded-xl shadow-sm p-5">
          <h4 class="text-sm font-semibold text-emerald-700 mb-3 flex items-center gap-2">
            <Database class="w-4 h-4" />
            数据库已收录
          </h4>
          <p class="text-sm text-slate-600 mb-3">检测到《{{ result.db_title }}》已有 {{ result.history?.length || 0 }} 条历史记录</p>
          
          <!-- History Chart - Line Chart -->
          <div v-if="result.history?.length" class="mt-3">
            <h5 class="text-xs font-medium text-slate-500 mb-2 flex items-center gap-1">
              <LineChart class="w-3 h-3" />
              月票趋势
            </h5>
            <div class="h-28 bg-white/40 rounded-lg p-3 relative">
              <svg class="w-full h-full" viewBox="0 0 300 100" preserveAspectRatio="none">
                <!-- Grid lines -->
                <line x1="0" y1="25" x2="300" y2="25" stroke="#e2e8f0" stroke-width="0.5" stroke-dasharray="2,2" />
                <line x1="0" y1="50" x2="300" y2="50" stroke="#e2e8f0" stroke-width="0.5" stroke-dasharray="2,2" />
                <line x1="0" y1="75" x2="300" y2="75" stroke="#e2e8f0" stroke-width="0.5" stroke-dasharray="2,2" />
                
                <!-- Area under line -->
                <defs>
                  <linearGradient id="lineGradient" x1="0%" y1="0%" x2="0%" y2="100%">
                    <stop offset="0%" style="stop-color:#6366f1;stop-opacity:0.3" />
                    <stop offset="100%" style="stop-color:#6366f1;stop-opacity:0.05" />
                  </linearGradient>
                </defs>
                
                <!-- Area fill -->
                <path :d="getLineChartPath(result.history, true)" fill="url(#lineGradient)" />
                
                <!-- Line -->
                <path :d="getLineChartPath(result.history, false)" fill="none" stroke="#6366f1" :stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
                
                <!-- Data points -->
                <g v-for="(h, i) in result.history" :key="i">
                  <circle 
                    :cx="getPointX(i, result.history.length)" 
                    :cy="getPointY(h.monthly_tickets, result.history)" 
                    r="3" 
                    fill="#6366f1" 
                    stroke="white" 
                    stroke-width="1"
                    class="hover:r-4 transition-all cursor-pointer"
                  >
                    <title>{{ h.year }}/{{ h.month }}: {{ h.monthly_tickets }}票</title>
                  </circle>
                </g>
              </svg>
            </div>
            <div class="flex justify-between text-xs text-slate-400 mt-1">
              <span>{{ result.history[0]?.year }}/{{ result.history[0]?.month }}</span>
              <span>{{ result.history[result.history.length-1]?.year }}/{{ result.history[result.history.length-1]?.month }}</span>
            </div>
          </div>
        </div>

        <!-- Report Section -->
        <div class="bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden">
          <div class="px-5 py-4 bg-slate-50 border-b border-slate-200 flex items-center justify-between">
            <h4 class="text-sm font-semibold text-slate-700 flex items-center gap-2">
              <FileText class="w-4 h-4 text-indigo-500" />
              评估报告
            </h4>
            <button 
              @click="exportReport"
              class="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-indigo-600 bg-indigo-50 hover:bg-indigo-100 rounded-lg transition-colors"
            >
              <Download class="w-3.5 h-3.5" />
              导出报告
            </button>
          </div>
          <div class="p-5">
            <div class="text-sm text-slate-600 leading-relaxed whitespace-pre-line">{{ result.report }}</div>
          </div>
        </div>

        <!-- Prediction Section -->
        <div v-if="result.prediction || result.future_predictions?.length" class="bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden">
          <div class="px-5 py-3 bg-purple-50 border-b border-purple-100">
            <h4 class="text-sm font-semibold text-purple-700 flex items-center gap-2">
              <TrendingUp class="w-4 h-4" />
              发展预测
            </h4>
          </div>
          <div class="p-5">
            <!-- 未来预测数值 -->
            <div v-if="result.future_predictions?.length" class="mb-4 p-4 bg-gradient-to-r from-purple-50 to-indigo-50 rounded-lg border border-purple-100">
              <h5 class="text-xs font-semibold text-purple-600 mb-3 flex items-center gap-1">
                <TrendingUp class="w-3 h-3" />
                未来3个月月票预测
              </h5>
              <div class="grid grid-cols-3 gap-3">
                <div v-for="(pred, i) in result.future_predictions" :key="i" 
                     class="text-center p-3 bg-white rounded-lg shadow-sm border border-purple-100">
                  <div class="text-xs text-slate-500 mb-1">{{ pred.year }}/{{ pred.month }}月</div>
                  <div class="text-lg font-bold text-purple-600">{{ pred.predicted_tickets?.toLocaleString() }}</div>
                  <div class="text-xs text-slate-400">预计月票</div>
                  <div class="mt-1">
                    <span class="text-xs px-1.5 py-0.5 rounded" 
                          :class="pred.trend?.includes('增长') || pred.trend?.includes('上升') ? 'bg-emerald-100 text-emerald-600' : pred.trend?.includes('下滑') ? 'bg-rose-100 text-rose-600' : 'bg-slate-100 text-slate-600'">
                      {{ pred.trend }}
                    </span>
                  </div>
                </div>
              </div>
            </div>
            <!-- 预测文字 -->
            <div v-if="result.prediction" class="text-sm text-slate-600 leading-relaxed whitespace-pre-line">{{ result.prediction }}</div>
          </div>
        </div>

        <!-- Suggestions Section -->
        <div v-if="result.suggestions?.length" class="bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden">
          <div class="px-5 py-3 bg-amber-50 border-b border-amber-100">
            <h4 class="text-sm font-semibold text-amber-700 flex items-center gap-2">
              <Target class="w-4 h-4" />
              优化建议
            </h4>
          </div>
          <div class="p-5 space-y-3">
            <div v-for="(s, i) in result.suggestions" :key="i" class="flex items-start gap-3">
              <span class="w-6 h-6 rounded-full bg-amber-500 text-white text-xs font-bold flex items-center justify-center flex-shrink-0 mt-0.5">
                {{ Number(i) + 1 }}
              </span>
              <span class="text-sm text-slate-600 leading-relaxed">{{ s }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Reset Button -->
      <button @click="reset" class="mt-2 w-full py-3 rounded-xl bg-slate-100 text-sm font-semibold text-slate-600 hover:bg-slate-200 transition-colors border border-slate-200 flex items-center justify-center gap-2">
        <RefreshCw class="w-4 h-4" />
        重新预测
      </button>
    </div>

    <!-- Input Form -->
    <div v-else class="flex-1 flex flex-col overflow-hidden">
      
      <!-- Mode Tabs -->
      <div class="flex gap-2 mb-5 overflow-x-auto pb-1 scrollbar-hide">
        <button 
          v-for="mode in modes" 
          :key="mode.id" 
          @click="switchMode(mode.id)"
          class="flex items-center gap-2 px-4 py-3 rounded-xl border transition-all whitespace-nowrap"
          :class="currentMode === mode.id 
            ? mode.color === 'indigo' ? 'bg-indigo-50 border-indigo-300 text-indigo-700' 
              : mode.color === 'amber' ? 'bg-amber-50 border-amber-300 text-amber-700'
              : mode.color === 'rose' ? 'bg-rose-50 border-rose-300 text-rose-700'
              : 'bg-emerald-50 border-emerald-300 text-emerald-700'
            : 'bg-white/60 border-slate-200 text-slate-600 hover:bg-white/80'"
        >
          <div class="w-7 h-7 rounded-lg flex items-center justify-center text-white"
               :class="mode.color === 'indigo' ? 'bg-indigo-500'
                 : mode.color === 'amber' ? 'bg-amber-500'
                 : mode.color === 'rose' ? 'bg-rose-500'
                 : 'bg-emerald-500'">
            <component :is="mode.icon" class="w-4 h-4" />
          </div>
          <span class="text-sm font-medium">{{ mode.label }}</span>
        </button>
      </div>

      <!-- Platform Notice -->
      <div class="flex items-center gap-2.5 px-4 py-3 rounded-xl bg-amber-50 border border-amber-200 mb-5">
        <Award class="w-5 h-5 text-amber-500 flex-shrink-0" />
        <span class="text-sm text-amber-700">{{ getPlatformHint() }}</span>
      </div>

      <!-- Form Fields -->
      <div class="flex-1 overflow-y-auto pr-1 space-y-4 custom-scrollbar">
        
        <!-- Basic Mode -->
        <template v-if="currentMode === 'basic'">
          <div class="space-y-4">
            <div>
              <label class="block text-sm font-medium text-slate-700 mb-2">
                <span class="inline-flex items-center gap-1.5">
                  <Star class="w-4 h-4 text-amber-500" />
                  作品名称
                </span>
                <span class="text-rose-500">*</span>
              </label>
              <input 
                v-model="formData.title" 
                type="text" 
                placeholder="请输入小说标题"
                class="w-full px-4 py-3 bg-white/70 border border-slate-200 rounded-xl text-slate-900 placeholder-slate-400 focus:outline-none focus:border-indigo-400 focus:ring-2 focus:ring-indigo-100 transition-all"
              />
            </div>
            
            <div class="grid grid-cols-2 gap-4">
              <div>
                <label class="block text-sm font-medium text-slate-700 mb-2">平台</label>
                <select v-model="formData.platform" class="w-full px-4 py-3 bg-white/70 border border-slate-200 rounded-xl text-slate-900 focus:outline-none focus:border-indigo-400 focus:ring-2 focus:ring-indigo-100 transition-all appearance-none cursor-pointer">
                  <option v-for="p in platforms" :key="p" :value="p">{{ p }}</option>
                </select>
              </div>
              <div>
                <label class="block text-sm font-medium text-slate-700 mb-2">题材</label>
                <select v-model="formData.category" class="w-full px-4 py-3 bg-white/70 border border-slate-200 rounded-xl text-slate-900 focus:outline-none focus:border-indigo-400 focus:ring-2 focus:ring-indigo-100 transition-all appearance-none cursor-pointer">
                  <option v-for="c in categories" :key="c" :value="c">{{ c }}</option>
                </select>
              </div>
            </div>

            <div>
              <label class="block text-sm font-medium text-slate-700 mb-2">作者笔名</label>
              <input v-model="formData.author" type="text" placeholder="输入作者名称" 
                class="w-full px-4 py-3 bg-white/70 border border-slate-200 rounded-xl text-slate-900 placeholder-slate-400 focus:outline-none focus:border-indigo-400 focus:ring-2 focus:ring-indigo-100 transition-all" />
            </div>

            <div class="grid grid-cols-2 gap-4">
              <div>
                <label class="block text-sm font-medium text-slate-700 mb-2">当前字数</label>
                <input v-model.number="formData.wordCount" type="number" placeholder="0" 
                  class="w-full px-4 py-3 bg-white/70 border border-slate-200 rounded-xl text-slate-900 placeholder-slate-400 focus:outline-none focus:border-indigo-400 focus:ring-2 focus:ring-indigo-100 transition-all" />
              </div>
              <div>
                <label class="block text-sm font-medium text-slate-700 mb-2">状态</label>
                <select v-model="formData.status" class="w-full px-4 py-3 bg-white/70 border border-slate-200 rounded-xl text-slate-900 focus:outline-none focus:border-indigo-400 focus:ring-2 focus:ring-indigo-100 transition-all appearance-none cursor-pointer">
                  <option v-for="s in statusOptions" :key="s" :value="s">{{ s }}</option>
                </select>
              </div>
            </div>
          </div>
        </template>

        <!-- Ranking Mode -->
        <template v-if="currentMode === 'ranking'">
          <div class="space-y-4">
            <div>
              <label class="block text-sm font-medium text-slate-700 mb-2">
                <span class="inline-flex items-center gap-1.5">
                  <TrendingUp class="w-4 h-4 text-amber-500" />
                  月票数
                </span>
              </label>
              <input v-model.number="formData.monthlyTickets" type="number" placeholder="0" 
                class="w-full px-4 py-3 bg-white/70 border border-slate-200 rounded-xl text-slate-900 placeholder-slate-400 focus:outline-none focus:border-amber-400 focus:ring-2 focus:ring-amber-100 transition-all" />
              <p class="mt-1.5 text-xs text-slate-400">
                {{ formData.platform === '起点' ? '起点头部：50万+ ｜ 优秀：5万+' : '纵横头部：5万+ ｜ 优秀：1万+' }}
              </p>
            </div>

            <div>
              <label class="block text-sm font-medium text-slate-700 mb-2">当前排名</label>
              <input v-model.number="formData.ranking" type="number" placeholder="输入榜单排名" 
                class="w-full px-4 py-3 bg-white/70 border border-slate-200 rounded-xl text-slate-900 placeholder-slate-400 focus:outline-none focus:border-amber-400 focus:ring-2 focus:ring-amber-100 transition-all" />
              <p class="mt-1.5 text-xs text-slate-400">
                {{ formData.platform === '起点' ? '前10头部 ｜ 前100优秀 ｜ 前500良好' : '前3头部 ｜ 前20优秀 ｜ 前50良好' }}
              </p>
            </div>

            <div>
              <label class="block text-sm font-medium text-slate-700 mb-2">周增长率 (%)</label>
              <input v-model.number="formData.weekOverWeekGrowth" type="number" placeholder="例如：15" 
                class="w-full px-4 py-3 bg-white/70 border border-slate-200 rounded-xl text-slate-900 placeholder-slate-400 focus:outline-none focus:border-amber-400 focus:ring-2 focus:ring-amber-100 transition-all" />
            </div>
          </div>
        </template>

        <!-- Engagement Mode -->
        <template v-if="currentMode === 'engagement'">
          <div class="grid grid-cols-2 gap-4">
            <div>
              <label class="block text-sm font-medium text-slate-700 mb-2">总收藏数</label>
              <input v-model.number="formData.collections" type="number" placeholder="0" 
                class="w-full px-4 py-3 bg-white/70 border border-slate-200 rounded-xl text-slate-900 placeholder-slate-400 focus:outline-none focus:border-rose-400 focus:ring-2 focus:ring-rose-100 transition-all" />
            </div>
            <div>
              <label class="block text-sm font-medium text-slate-700 mb-2">推荐票数</label>
              <input v-model.number="formData.recommendations" type="number" placeholder="0" 
                class="w-full px-4 py-3 bg-white/70 border border-slate-200 rounded-xl text-slate-900 placeholder-slate-400 focus:outline-none focus:border-rose-400 focus:ring-2 focus:ring-rose-100 transition-all" />
            </div>
            <div>
              <label class="block text-sm font-medium text-slate-700 mb-2">评论数</label>
              <input v-model.number="formData.comments" type="number" placeholder="0" 
                class="w-full px-4 py-3 bg-white/70 border border-slate-200 rounded-xl text-slate-900 placeholder-slate-400 focus:outline-none focus:border-rose-400 focus:ring-2 focus:ring-rose-100 transition-all" />
            </div>
            <div>
              <label class="block text-sm font-medium text-slate-700 mb-2">粉丝数</label>
              <input v-model.number="formData.followers" type="number" placeholder="0" 
                class="w-full px-4 py-3 bg-white/70 border border-slate-200 rounded-xl text-slate-900 placeholder-slate-400 focus:outline-none focus:border-rose-400 focus:ring-2 focus:ring-rose-100 transition-all" />
            </div>
          </div>
        </template>

        <!-- Content Mode -->
        <template v-if="currentMode === 'content'">
          <div class="space-y-4">
            <div>
              <label class="block text-sm font-medium text-slate-700 mb-2">作品简介</label>
              <textarea 
                v-model="formData.synopsis" 
                rows="3" 
                placeholder="输入作品简介，帮助AI理解故事核心..."
                class="w-full px-4 py-3 bg-white/70 border border-slate-200 rounded-xl text-slate-900 placeholder-slate-400 focus:outline-none focus:border-emerald-400 focus:ring-2 focus:ring-emerald-100 transition-all resize-none"
              ></textarea>
            </div>

            <!-- File Upload Zone -->
            <div>
              <label class="block text-sm font-medium text-slate-700 mb-2">章节内容</label>
              
              <!-- Upload Zone -->
              <div 
                v-if="!uploadedFile"
                class="upload-zone relative"
                :class="{ 'dragging': isDragging }"
                @drop="handleDrop"
                @dragover="handleDragOver"
                @dragleave="handleDragLeave"
              >
                <input 
                  type="file" 
                  accept=".txt,.md,.doc,.docx"
                  class="absolute inset-0 w-full h-full opacity-0 cursor-pointer z-10"
                  @change="handleFileUpload"
                />
                <div class="upload-content">
                  <div class="upload-icon-wrapper">
                    <Upload class="w-8 h-8 upload-icon" />
                  </div>
                  <div class="upload-text">
                    <p class="upload-title">拖拽文件到此处，或点击上传</p>
                    <p class="upload-desc">支持 .txt, .md, .doc, .docx 格式</p>
                  </div>
                  <div class="upload-hint">
                    <span>建议上传3000-5000字的代表性章节</span>
                  </div>
                </div>
              </div>

              <!-- Uploaded File Display -->
              <div v-else class="uploaded-file">
                <div class="file-info">
                  <div class="file-icon">
                    <FileText class="w-5 h-5" />
                  </div>
                  <div class="file-details">
                    <p class="file-name">{{ uploadedFile.name }}</p>
                    <p class="file-size">{{ (uploadedFile.size / 1024).toFixed(1) }} KB · 已读取 {{ formData.chapterContent.length.toLocaleString() }} 字</p>
                  </div>
                </div>
                <button 
                  @click="removeFile"
                  class="remove-btn"
                >
                  <X class="w-4 h-4" />
                </button>
              </div>

              <!-- Manual Input Toggle -->
              <div class="mt-3">
                <button 
                  @click="$event => { uploadedFile ? removeFile() : null; showTextarea = !showTextarea }"
                  class="text-xs text-slate-500 hover:text-emerald-600 transition-colors flex items-center gap-1"
                >
                  <span>{{ showTextarea ? '隐藏文本框' : '或手动粘贴文本' }}</span>
                  <ChevronRight class="w-3 h-3" :class="{ 'rotate-90': showTextarea }" />
                </button>
              </div>

              <!-- Textarea for manual input -->
              <textarea 
                v-if="showTextarea || formData.chapterContent"
                v-model="formData.chapterContent" 
                rows="6" 
                placeholder="在此粘贴章节内容，或拖拽上传文件..."
                class="w-full mt-3 px-4 py-3 bg-white/70 border border-slate-200 rounded-xl text-slate-900 placeholder-slate-400 focus:outline-none focus:border-emerald-400 focus:ring-2 focus:ring-emerald-100 transition-all resize-none"
              ></textarea>
            </div>
          </div>
        </template>
      </div>

      <!-- Error Message -->
      <div v-if="error" class="mt-4 flex items-center gap-2 px-4 py-3 rounded-xl bg-rose-50 border border-rose-200">
        <AlertTriangle class="w-5 h-5 text-rose-500" />
        <span class="text-sm text-rose-600">{{ error }}</span>
      </div>

      <!-- Submit Button -->
      <button 
        @click="submitPrediction" 
        :disabled="loading || !formData.title"
        class="mt-4 w-full py-3.5 rounded-xl font-semibold text-white text-base transition-all flex items-center justify-center gap-2"
        :class="loading ? 'bg-slate-400 cursor-not-allowed' : 'bg-gradient-to-r from-indigo-500 to-purple-600 hover:shadow-lg hover:shadow-indigo-500/20'"
      >
        <Loader2 v-if="loading" class="w-5 h-5 animate-spin" />
        <Sparkles v-else class="w-5 h-5" />
        <span>{{ loading ? 'AI 分析中...' : '开始预测' }}</span>
      </button>
    </div>
  </div>
</template>

<style scoped>
/* Custom scrollbar */
.custom-scrollbar::-webkit-scrollbar {
  width: 6px;
}

.custom-scrollbar::-webkit-scrollbar-track {
  background: transparent;
}

.custom-scrollbar::-webkit-scrollbar-thumb {
  background: rgb(203 213 225);
  border-radius: 6px;
}

.custom-scrollbar::-webkit-scrollbar-thumb:hover {
  background: rgb(148 163 184);
}

/* Hide scrollbar for horizontal scroll */
.scrollbar-hide::-webkit-scrollbar {
  display: none;
}

.scrollbar-hide {
  -ms-overflow-style: none;
  scrollbar-width: none;
}

/* Upload Zone Styles */
.upload-zone {
  border: 2px dashed rgb(203 213 225);
  border-radius: 16px;
  padding: 32px 24px;
  background: rgb(255 255 255 / 0.5);
  transition: all 0.2s ease;
  text-align: center;
}

.upload-zone:hover {
  border-color: rgb(16 185 129);
  background: rgb(16 185 129 / 0.05);
}

.upload-zone.dragging {
  border-color: rgb(16 185 129);
  background: rgb(16 185 129 / 0.1);
  transform: scale(1.02);
}

.upload-content {
  pointer-events: none;
}

.upload-icon-wrapper {
  width: 64px;
  height: 64px;
  background: rgb(16 185 129 / 0.1);
  border-radius: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 16px;
}

.upload-icon {
  color: rgb(16 185 129);
}

.upload-title {
  font-size: 15px;
  font-weight: 600;
  color: rgb(51 65 85);
  margin-bottom: 4px;
}

.upload-desc {
  font-size: 13px;
  color: rgb(148 163 184);
  margin-bottom: 12px;
}

.upload-hint {
  display: inline-block;
  padding: 6px 12px;
  background: rgb(241 245 249);
  border-radius: 20px;
  font-size: 12px;
  color: rgb(100 116 139);
}

/* Uploaded File Display */
.uploaded-file {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px;
  background: rgb(16 185 129 / 0.1);
  border: 1px solid rgb(16 185 129 / 0.3);
  border-radius: 12px;
}

.file-info {
  display: flex;
  align-items: center;
  gap: 12px;
}

.file-icon {
  width: 40px;
  height: 40px;
  background: rgb(16 185 129);
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
}

.file-name {
  font-size: 14px;
  font-weight: 600;
  color: rgb(51 65 85);
  margin-bottom: 2px;
}

.file-size {
  font-size: 12px;
  color: rgb(100 116 139);
}

.remove-btn {
  width: 32px;
  height: 32px;
  background: rgb(255 255 255 / 0.8);
  border: 1px solid rgb(203 213 225);
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: rgb(100 116 139);
  cursor: pointer;
  transition: all 0.2s ease;
}

.remove-btn:hover {
  background: rgb(244 63 94 / 0.1);
  border-color: rgb(244 63 94);
  color: rgb(244 63 94);
}
select {
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='16' height='16' viewBox='0 0 24 24' fill='none' stroke='%2394a3b8' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='m6 9 6 6 6-6'/%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-position: right 12px center;
  padding-right: 40px;
}
</style>
