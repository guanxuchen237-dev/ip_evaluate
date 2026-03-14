<script setup lang="ts">
import { ref, computed } from 'vue';
import { Sparkles, Loader2, AlertTriangle, CheckCircle2, Database, BookOpen, TrendingUp, TrendingDown } from "lucide-vue-next";
import axios from 'axios';

// Props to potentially pre-fill data or styling
const props = defineProps<{
  // 
}>();

const inputData = ref({
  title: '',
  category: '都市',
  abstract: ''
});

const result = ref<any>(null);
const loading = ref(false);
const error = ref('');

const categories = [
  '玄幻', '都市', '仙侠', '科幻', '历史', '游戏', '奇幻', '军事', '悬疑'
];

const API_BASE = 'http://localhost:5000/api';

const submitPrediction = async () => {
  if (!inputData.value.title || !inputData.value.abstract) {
    error.value = "请填写完整信息";
    return;
  }
  
  loading.value = true;
  error.value = '';
  result.value = null;
  
  try {
    const res = await axios.post(`${API_BASE}/predict`, inputData.value);
    result.value = res.data;
  } catch (e: any) {
    error.value = e.response?.data?.error || "预测服务连接失败";
  } finally {
    loading.value = false;
  }
};

const reset = () => {
  result.value = null;
  inputData.value = { title: '', category: '都市', abstract: '' };
};

// 动态等级标签（根据实际分数计算，不再硬编码）
const predictedLevel = computed(() => {
  const s = result.value?.score || 0;
  if (s >= 92) return { label: '市场S级', color: 'bg-amber-100 text-amber-700 border-amber-200' };
  if (s >= 80) return { label: '市场A级', color: 'bg-indigo-100 text-indigo-600 border-indigo-200' };
  if (s >= 65) return { label: '市场B级', color: 'bg-sky-100 text-sky-600 border-sky-200' };
  return { label: '市场C级', color: 'bg-slate-100 text-slate-600 border-slate-200' };
});

const riskLevel = computed(() => {
  const s = result.value?.score || 0;
  if (s >= 75) return { label: '低风险', color: 'bg-green-100 text-green-600 border-green-200' };
  if (s >= 55) return { label: '中风险', color: 'bg-amber-100 text-amber-600 border-amber-200' };
  return { label: '高风险', color: 'bg-red-100 text-red-600 border-red-200' };
});

// AI 报告文本格式化
const formattedReport = computed(() => {
  const report = result.value?.ai_report;
  if (!report) return ''; 
  if (typeof report === 'string') return report;
  // 如果是对象（含 comment、strengths 等），提取关键内容
  return report.comment || report.summary || JSON.stringify(report);
});

// 多维市场分析数据（映射为进度条组件）
const marketDimensions = computed(() => {
  const ma = result.value?.market_analysis;
  if (!ma) return [];
  const colorMap: Record<string, string> = {
    market_heat: 'bg-rose-400',
    content_quality: 'bg-indigo-400',
    ip_potential: 'bg-violet-400',
    fan_loyalty: 'bg-sky-400',
    commercial_value: 'bg-amber-400',
    timeliness: 'bg-emerald-400'
  };
  const labelMap: Record<string, string> = {
    market_heat: '市场热度',
    content_quality: '内容质量',
    ip_potential: 'IP潜力',
    fan_loyalty: '粉丝粘性',
    commercial_value: '商业价值',
    timeliness: '时效活跃'
  };
  return Object.entries(ma).map(([k, v]) => ({
    label: labelMap[k] || k,
    value: Math.round(v as number),
    colorClass: colorMap[k] || 'bg-slate-400'
  }));
});

// 趋势图 SVG 路径（用真实历史数据绘制）
const trendSvgPath = computed(() => {
  const data = result.value?.trend_history?.tickets;
  if (!data || data.length < 2) return '';
  const w = 280, h = 40;
  const max = Math.max(...data, 1);
  const min = Math.min(...data, 0);
  const range = max - min || 1;
  const step = w / (data.length - 1);
  return 'M' + data.map((v: number, i: number) => `${i * step},${h - ((v - min) / range) * h}`).join(' L');
});
</script>

<template>
  <div class="h-full flex flex-col">
    <!-- Header -->
    <div class="flex items-center gap-2 mb-4 text-indigo-600">
      <Sparkles class="w-5 h-5" />
      <h3 class="font-serif text-lg text-slate-900">AI 价值预测</h3>
    </div>

    <!-- Input Form (Show if no result) -->
    <div v-if="!result" class="flex-1 flex flex-col gap-4">
      <div>
        <label class="text-xs text-slate-500 mb-1 block">作品名称</label>
        <input 
          v-model="inputData.title"
          type="text" 
          placeholder="输入小说标题..."
          class="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-sm text-slate-900 focus:outline-none focus:border-indigo-400 transition-colors"
        />
      </div>
      
      <div>
        <label class="text-xs text-slate-500 mb-1 block">题材分类</label>
        <select 
          v-model="inputData.category"
          class="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-sm text-slate-900 focus:outline-none focus:border-indigo-400"
        >
          <option v-for="cat in categories" :key="cat" :value="cat">{{ cat }}</option>
        </select>
      </div>
      
      <div class="flex-1 min-h-0 flex flex-col">
        <label class="text-xs text-slate-500 mb-1 block">简介 / 开篇 (Abstract)</label>
        <textarea 
          v-model="inputData.abstract"
          placeholder="输入大约200字的内容简介..."
          class="flex-1 w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-sm text-slate-900 focus:outline-none focus:border-indigo-400 resize-none h-24"
        ></textarea>
      </div>

      <div v-if="error" class="text-red-500 text-xs flex items-center gap-1">
        <AlertTriangle class="w-3 h-3" /> {{ error }}
      </div>

      <button 
        @click="submitPrediction"
        :disabled="loading"
        class="w-full py-3 rounded-xl bg-gradient-to-r from-indigo-500 to-purple-500 text-white font-medium hover:opacity-90 transition-opacity disabled:opacity-50 flex items-center justify-center gap-2"
      >
        <Loader2 v-if="loading" class="w-4 h-4 animate-spin" />
        <span v-else>启动预测引擎</span>
      </button>
    </div>

    <!-- Result Display (Show if result) -->
    <div v-else class="flex-1 flex flex-col h-full overflow-hidden">
      <!-- Score Circle -->
      <div class="flex items-center gap-6 mb-4">
        <div class="relative w-20 h-20 flex-shrink-0">
           <svg class="w-full h-full -rotate-90" viewBox="0 0 36 36">
              <path class="text-slate-200" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" fill="none" stroke="currentColor" stroke-width="3" />
              <path class="text-indigo-500 drop-shadow-[0_0_10px_rgba(99,102,241,0.5)]" :stroke-dasharray="`${result.score}, 100`" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" fill="none" stroke="currentColor" stroke-width="3" />
           </svg>
           <div class="absolute inset-0 flex items-center justify-center text-xl font-bold font-serif text-slate-900">
             {{ result.score?.toFixed(1) }}
           </div>
        </div>
        <div class="flex-1">
          <h4 class="text-slate-900 font-medium text-lg leading-tight mb-1">{{ result.matched_book?.title || inputData.title }}</h4>
          <p class="text-xs text-slate-500 mb-2">{{ inputData.category }} · 预测完成</p>
          <div class="flex gap-2 text-[10px] flex-wrap">
             <span class="px-2 py-0.5 rounded-full border" :class="predictedLevel.color">{{ predictedLevel.label }}</span>
             <span class="px-2 py-0.5 rounded-full border" :class="riskLevel.color">{{ riskLevel.label }}</span>
             <span v-if="result.matched_book?.status" class="px-2 py-0.5 rounded-full border"
               :class="result.matched_book.status.includes('连载') ? 'bg-blue-100 text-blue-600 border-blue-200' : 'bg-gray-100 text-gray-500 border-gray-200'">
               {{ result.matched_book.status }}
             </span>
          </div>
        </div>
      </div>

      <!-- 数据库匹配提示 -->
      <div v-if="result.matched_book" class="flex items-center gap-2 px-3 py-2 bg-emerald-50 border border-emerald-200 rounded-lg mb-3 text-xs text-emerald-700">
        <Database class="w-3.5 h-3.5 flex-shrink-0" />
        <span>已匹配数据库: <strong>{{ result.matched_book.author }}</strong> · {{ result.matched_book.platform }} · 月票 {{ (result.matched_book.finance_raw || result.matched_book.finance || 0).toLocaleString() }}
          <template v-if="result.matched_book.platform_norm"> (归一化{{ result.matched_book.platform_norm }})</template>
        </span>
      </div>
      <div v-else class="flex items-center gap-2 px-3 py-2 bg-amber-50 border border-amber-200 rounded-lg mb-3 text-xs text-amber-700">
        <BookOpen class="w-3.5 h-3.5 flex-shrink-0" />
        <span>新作品预估 · 基于内容质量分析</span>
      </div>

      <!-- 多维市场价值分析 (如果有) -->
      <div v-if="result.market_analysis" class="mb-3 bg-slate-50 rounded-lg border border-slate-100 p-3">
        <div class="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-2">市场价值分析</div>
        <div class="space-y-1.5">
          <div v-for="(item, idx) in marketDimensions" :key="idx" class="flex items-center gap-2">
            <span class="text-[10px] text-slate-500 w-14 shrink-0 text-right">{{ item.label }}</span>
            <div class="flex-1 h-2 bg-slate-200 rounded-full overflow-hidden">
              <div class="h-full rounded-full transition-all duration-500" :class="item.colorClass" :style="{ width: item.value + '%' }"></div>
            </div>
            <span class="text-[10px] font-bold w-7 text-right" :class="item.value >= 80 ? 'text-emerald-600' : item.value >= 60 ? 'text-amber-600' : 'text-slate-500'">{{ item.value }}</span>
          </div>
        </div>
      </div>

      <!-- 六维 AI 评估 (如果有且没有 market_analysis) -->
      <div v-else-if="result.dimensions" class="grid grid-cols-3 gap-2 mb-3">
        <div v-for="(val, key) in result.dimensions" :key="key" class="text-center py-1.5 bg-slate-50 rounded-lg border border-slate-100">
          <div class="text-sm font-bold text-slate-800">{{ typeof val === 'number' ? val.toFixed(0) : val }}</div>
          <div class="text-[10px] text-slate-400">{{ { story: '故事', character: '角色', world: '世界观', commercial: '商业', adaptation: '改编', safety: '安全' }[key] || key }}</div>
        </div>
      </div>

      <!-- 真实趋势图 (如果有历史数据) -->
      <div v-if="result.trend_history?.tickets?.length > 1" class="mb-3 bg-slate-50 rounded-lg border border-slate-100 p-3">
        <div class="flex items-center justify-between mb-2">
          <span class="text-[10px] font-bold text-slate-400 uppercase tracking-wider">月票走势</span>
          <div v-if="result.trend" class="flex items-center gap-1 text-[10px] font-bold" :class="result.trend.direction === '上升' ? 'text-emerald-500' : result.trend.direction === '下降' ? 'text-rose-500' : 'text-slate-400'">
            <TrendingUp v-if="result.trend.direction === '上升'" class="w-3 h-3" />
            <TrendingDown v-else-if="result.trend.direction === '下降'" class="w-3 h-3" />
            <span>{{ result.trend.direction }} {{ result.trend.growth_rate > 0 ? '+' : '' }}{{ result.trend.growth_rate }}%</span>
          </div>
        </div>
        <svg viewBox="0 0 280 40" class="w-full h-10">
          <path :d="trendSvgPath" fill="none" stroke="#6366f1" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" />
        </svg>
        <div class="flex justify-between text-[9px] text-slate-300 mt-1">
          <span>{{ result.trend_history.dates[0] }}</span>
          <span>{{ result.trend_history.dates[result.trend_history.dates.length - 1] }}</span>
        </div>
      </div>
      
      <!-- AI Report Scrollable -->
      <div class="flex-1 overflow-y-auto pr-1 custom-scrollbar">
        <div class="bg-slate-50 rounded-lg p-3 text-sm text-slate-700 leading-relaxed border border-slate-200">
           <div class="flex items-center gap-2 mb-2 text-indigo-600">
             <Sparkles class="w-3 h-3" />
             <span class="text-xs font-bold uppercase tracking-wider">AI Analysis</span>
           </div>
           {{ formattedReport || '暂无报告' }}
        </div>
      </div>

      <button 
        @click="reset"
        class="mt-4 w-full py-2 rounded-lg bg-slate-100 text-sm text-slate-700 hover:bg-slate-200 transition-colors border border-slate-200"
      >
        预测下一本
      </button>
    </div>
  </div>
</template>

<style scoped>
.custom-scrollbar::-webkit-scrollbar {
  width: 4px;
}
.custom-scrollbar::-webkit-scrollbar-track {
  background: rgba(0, 0, 0, 0.05);
}
.custom-scrollbar::-webkit-scrollbar-thumb {
  background: rgba(0, 0, 0, 0.1);
  border-radius: 4px;
}
</style>
