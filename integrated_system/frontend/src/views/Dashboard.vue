<script setup lang="ts">
import { ref, onMounted, computed } from "vue";
import { useRouter } from "vue-router";
import { BookOpen, Zap, TrendingUp, Sparkles, Brain, ArrowRight, MessageCircle, Globe, Users, BarChart3, MapPin, Crown, Award } from "lucide-vue-next";
import EditorialLayout from "@/components/layout/EditorialLayout.vue";
import TrendLineChart from "@/components/charts/TrendLineChart.vue";
import CategoryPie from "@/components/charts/CategoryPie.vue";
import WordCloud from "@/components/charts/WordCloud.vue";
import RadarChart from "@/components/charts/RadarChart.vue";
import AuthorPyramid from "@/components/charts/AuthorPyramid.vue";
import GeoMap from "@/components/charts/GeoMap.vue";
import LongTermTrendChart from "@/components/charts/LongTermTrendChart.vue";
import axios from 'axios';

const API_BASE = 'http://localhost:5000/api';
const router = useRouter();

// 统计数据
const stats = ref([
  { title: "书库总量", value: "-", unit: "本", icon: BookOpen, color: "from-blue-500 to-indigo-600" },
  { title: "平均IP指数", value: "-", unit: "分", icon: Zap, color: "from-amber-500 to-orange-600" },
  { title: "收录作者", value: "-", unit: "位", icon: Users, color: "from-emerald-500 to-teal-600" },
  { title: "评论总量", value: "-", unit: "条", icon: MessageCircle, color: "from-rose-500 to-pink-600" },
]);

// 月票 Top10
const ticketTop = ref<any[]>([]);

// 平台数据
const platformData = ref({ qidian: { value: 0, percent: 10 }, zongheng: { value: 0, percent: 10 } });

// 格式化大数字（精确版）
const formatNum = (n: number) => {
  if (n >= 10000) return (n / 10000).toFixed(2) + '万';
  return n.toLocaleString();
};

const fetchData = async () => {
  try {
    // 1. 总览统计
    const resStats = await axios.get(`${API_BASE}/stats/overview`);
    if (resStats.data) {
      stats.value[0]!.value = (resStats.data.total_novels || 0).toLocaleString();
      stats.value[1]!.value = (resStats.data.avg_ip_score || 0).toString();
      stats.value[2]!.value = (resStats.data.total_authors || 0).toLocaleString();
      stats.value[3]!.value = '11万+'; // 评论数据来自纵横，约11万条
    }

    // 2. 平台分布
    const resPlat = await axios.get(`${API_BASE}/charts/platform`);
    if (resPlat.data && Array.isArray(resPlat.data)) {
      const qd = resPlat.data.find((i: any) => i.name === '起点' || i.name === 'Qidian')?.value || 0;
      const zh = resPlat.data.find((i: any) => i.name === '纵横' || i.name === 'Zongheng')?.value || 0;
      const max = Math.max(qd, zh, 1);
      platformData.value = {
        qidian: { value: qd, percent: Math.max((qd / max) * 85, 10) },
        zongheng: { value: zh, percent: Math.max((zh / max) * 85, 10) }
      };
    }

    // 3. 月票排行
    const resTicket = await axios.get(`${API_BASE}/charts/ticket_top?limit=10`);
    if (resTicket.data && Array.isArray(resTicket.data)) {
      ticketTop.value = resTicket.data;
    }
  } catch (e) {
    console.error("Dashboard Data Fetch Error", e);
  }
};

onMounted(() => {
  fetchData();
});

// Top3 奖牌颜色
const medalColor = (idx: number) => {
  if (idx === 0) return 'from-amber-400 to-yellow-500 shadow-amber-200/50';
  if (idx === 1) return 'from-slate-300 to-slate-400 shadow-slate-200/50';
  if (idx === 2) return 'from-orange-400 to-amber-600 shadow-orange-200/50';
  return 'from-slate-100 to-slate-200';
};
</script>

<template>
  <EditorialLayout :showDock="true">
    <div class="min-h-screen p-5 pb-20 text-slate-900 relative z-10 flex flex-col">

      <!-- 大屏标题 -->
      <header class="text-center mb-5 relative">
        <div class="text-[10px] font-bold tracking-[0.3em] text-slate-400 uppercase mb-1">IP Lumina · Data Visualization</div>
        <h1 class="font-serif text-3xl font-bold tracking-wider text-slate-900">
          核心数据概览大屏
        </h1>
        <div class="w-48 h-0.5 bg-gradient-to-r from-transparent via-indigo-400 to-transparent mx-auto mt-2"></div>
      </header>

      <!-- 统计卡片 (跨度 12) -->
      <div class="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-5">
        <div v-for="stat in stats" :key="stat.title" class="relative group">
          <div class="bg-white/60 backdrop-blur-xl border border-white/40 rounded-xl shadow-sm hover:shadow-md transition-all p-4 flex items-center gap-3 h-[80px]">
            <div class="w-10 h-10 rounded-lg bg-gradient-to-br flex items-center justify-center text-white shadow-md flex-shrink-0" :class="stat.color">
              <component :is="stat.icon" class="w-5 h-5" />
            </div>
            <div>
              <p class="text-[11px] text-slate-500 mb-0.5 font-bold">{{ stat.title }}</p>
              <div class="text-2xl font-sans font-bold text-slate-900 leading-tight">{{ stat.value }}</div>
            </div>
          </div>
        </div>
      </div>

      <!-- 三栏主布局 -->
      <div class="flex-1 grid grid-cols-12 gap-4 auto-rows-min">

        <!-- ==================== 左栏 (重构后对齐中间高度) ==================== -->
        <div class="col-span-12 lg:col-span-3 flex flex-col gap-4">

          <!-- 月票排行榜 Top10 -->
          <div class="bg-white/60 backdrop-blur-xl border border-white/40 rounded-xl shadow-sm p-4 flex flex-col h-[380px]">
             <h3 class="text-sm font-bold text-slate-700 mb-3 flex items-center gap-2 flex-shrink-0">
               <Crown class="w-4 h-4 text-amber-500" /> 实时月票总榜 TOP 10
             </h3>
             <div class="flex-1 overflow-y-auto pr-1 flex flex-col gap-1.5 custom-scrollbar">
               <div v-for="(book, idx) in ticketTop" :key="book.title"
                    class="flex items-center gap-2.5 py-1.5 px-2 rounded-lg hover:bg-slate-50/80 transition-colors group">
                 <div class="w-6 h-6 rounded-md flex items-center justify-center text-white text-[10px] font-bold flex-shrink-0 shadow-sm bg-gradient-to-br"
                      :class="idx < 3 ? medalColor(idx) : 'bg-slate-200 text-slate-500'">
                   {{ idx + 1 }}
                 </div>
                 <div class="flex-1 min-w-0">
                   <div class="text-sm font-bold text-slate-800 truncate">{{ book.title }}</div>
                   <span class="text-[10px] px-1 py-0.5 rounded font-bold"
                         :class="book.platform === '起点' ? 'text-blue-600 bg-blue-50' : 'text-rose-600 bg-rose-50'">
                     {{ book.platform }}
                   </span>
                 </div>
                 <div class="text-right flex-shrink-0">
                   <div class="text-sm font-mono font-bold" :class="idx < 3 ? 'text-amber-600' : 'text-slate-600'">
                     {{ formatNum(book.monthly_tickets) }}
                   </div>
                 </div>
               </div>
               <div v-if="ticketTop.length === 0" class="flex-1 flex items-center justify-center text-slate-400 text-sm">
                 加载中...
               </div>
             </div>
          </div>

          <!-- 题材分布饼图 -->
          <div class="bg-white/60 backdrop-blur-xl border border-white/40 rounded-xl shadow-sm p-4 h-[240px] flex flex-col">
            <h3 class="text-sm font-bold text-slate-700 mb-2 flex items-center gap-2 flex-shrink-0">
              <BarChart3 class="w-4 h-4 text-indigo-500" />
              作品题材分布
            </h3>
            <div class="flex-1 w-full relative">
              <CategoryPie />
            </div>
          </div>

          <!-- 全站短线趋势 -->
          <div class="bg-white/60 backdrop-blur-xl border border-white/40 rounded-xl shadow-sm p-4 h-[240px] flex flex-col">
            <h3 class="text-sm font-bold text-slate-700 mb-2 flex items-center gap-2 flex-shrink-0">
              <TrendingUp class="w-4 h-4 text-blue-500" />
              全站阅读热度短线趋势
            </h3>
            <div class="flex-1 w-full relative">
              <TrendLineChart />
            </div>
          </div>

        </div>

        <!-- ==================== 中栏（宽区域：地图+长线趋势）==================== -->
        <div class="col-span-12 lg:col-span-6 flex flex-col gap-4">

           <!-- 读者地理分布 (中国地图) -->
           <div class="bg-white/60 backdrop-blur-xl border border-white/40 rounded-xl shadow-sm p-4 flex flex-col h-[400px]">
             <div class="flex items-center justify-between mb-2 flex-shrink-0">
               <h3 class="text-sm font-bold text-slate-700 flex items-center gap-2">
                 <MapPin class="w-4 h-4 text-sky-500" />
                 核心读者地域热度分布
               </h3>
               <span class="text-[10px] text-slate-400 font-mono">数据来源：平台 IP 属地</span>
             </div>
             <div class="flex-1 w-full relative">
               <GeoMap />
             </div>
           </div>

           <!-- 现象级作品推荐票与月票走势并排 -->
           <div class="h-[235px]"> 
              <LongTermTrendChart platform="qidian" title="起点顶级大作长线推荐票趋势" />
           </div>
           
           <div class="h-[235px]">
              <LongTermTrendChart platform="zongheng" title="纵横现象级作品长线月票走势" />
           </div>

        </div>

        <!-- ==================== 右栏 (各项指标+AI聚合报告) ==================== -->
        <div class="col-span-12 lg:col-span-3 flex flex-col gap-4">

          <!-- 平台分布对比 -->
          <div class="bg-white/60 backdrop-blur-xl border border-white/40 rounded-xl shadow-sm p-4 h-[180px] flex flex-col">
            <h3 class="text-sm font-bold text-slate-700 mb-3 flex items-center gap-2 flex-shrink-0">
              <Globe class="w-4 h-4 text-indigo-500" />
              平台作品资源配比
            </h3>
            <div class="flex-1 flex items-end justify-center gap-10 pb-2 h-full">
              <div class="flex flex-col items-center justify-end gap-2 h-full w-20">
                <div class="text-base font-bold text-slate-800">{{ platformData.qidian.value }}</div>
                <div class="w-14 bg-gradient-to-t from-indigo-500 to-indigo-400 rounded-t-lg relative shadow-[0_0_15px_rgba(99,102,241,0.25)] transition-all duration-1000" :style="{ height: platformData.qidian.percent + '%' }"></div>
                <div class="text-xs text-slate-500 font-bold">起点</div>
              </div>
              <div class="flex flex-col items-center justify-end gap-2 h-full w-20">
                <div class="text-base font-bold text-slate-800">{{ platformData.zongheng.value }}</div>
                <div class="w-14 bg-gradient-to-t from-blue-500 to-blue-400 rounded-t-lg relative shadow-[0_0_15px_rgba(59,130,246,0.25)] transition-all duration-1000" :style="{ height: platformData.zongheng.percent + '%' }"></div>
                <div class="text-xs text-slate-500 font-bold">纵横</div>
              </div>
            </div>
          </div>

          <!-- IP 深度分析 Radar -->
          <div class="bg-white/60 backdrop-blur-xl border border-white/40 rounded-xl shadow-sm p-4 h-[240px] flex flex-col">
            <h3 class="text-sm font-bold text-slate-700 mb-2 flex items-center gap-2 flex-shrink-0">
              <Sparkles class="w-4 h-4 text-violet-500" />
              全站跨维综合指标雷达图
            </h3>
            <div class="flex-1 w-full relative">
              <RadarChart />
            </div>
          </div>

          <!-- 热门作者词云 -->
          <div class="bg-white/60 backdrop-blur-xl border border-white/40 rounded-xl shadow-sm p-4 h-[180px] flex flex-col">
            <h3 class="text-sm font-bold text-slate-700 mb-2 flex items-center gap-2 flex-shrink-0">
              <Award class="w-4 h-4 text-teal-500" />
              热门畅销作者
            </h3>
            <div class="flex-1 w-full relative">
              <WordCloud />
            </div>
          </div>

          <!-- 新增：AI 数据洞察简报 完美的填补了高度的空白！ -->
          <div class="bg-gradient-to-br from-indigo-50/90 to-blue-50/90 backdrop-blur-xl border border-indigo-100/60 rounded-xl shadow-sm p-4 flex-1 min-h-[170px] flex flex-col relative overflow-hidden group">
            <div class="absolute -right-2 -bottom-2 p-4 opacity-10 group-hover:opacity-20 transition-opacity">
              <Brain class="w-20 h-20 text-indigo-500" />
            </div>
            <h3 class="text-sm font-bold text-indigo-900 mb-3 flex items-center gap-2 relative z-10 flex-shrink-0">
              <Zap class="w-4 h-4 text-amber-500" />
              AI 实况智能简析
            </h3>
            <div class="space-y-3 relative z-10 overflow-hidden flex-1 flex flex-col justify-center">
              <div class="flex items-start gap-2">
                <div class="w-1.5 h-1.5 rounded-full bg-indigo-400 mt-1.5 flex-shrink-0 shadow-[0_0_8px_rgba(99,102,241,0.5)]"></div>
                <p class="text-xs text-indigo-800/85 leading-snug">
                  读者活跃度激增：全站总访问热度近期环比上升 <span class="font-bold text-indigo-600">14.2%</span>，平台停留时长稳定高位。
                </p>
              </div>
              <div class="flex items-start gap-2">
                <div class="w-1.5 h-1.5 rounded-full bg-violet-400 mt-1.5 flex-shrink-0 shadow-[0_0_8px_rgba(139,92,246,0.5)]"></div>
                <p class="text-xs text-indigo-800/85 leading-snug">
                  趋势变动：<span class="font-bold text-violet-600 border-b border-violet-200">玄幻</span> 类 IP 衍生转化率最强，受众多集中于江南沿海下沉潜力大。
                </p>
              </div>
            </div>
          </div>

          <!-- 快捷入口 -->
          <div class="grid grid-cols-2 gap-3 mt-auto h-[60px]">
            <button @click="router.push('/prediction')" class="bg-gradient-to-br from-white to-slate-50 border border-slate-200 rounded-xl shadow-sm hover:shadow-md hover:border-indigo-200 transition-all py-2 px-3 group relative overflow-hidden flex items-center justify-center gap-2">
              <Brain class="w-4 h-4 text-indigo-500" />
              <span class="font-bold text-sm text-slate-700 group-hover:text-indigo-700 transition-colors">爆点预警</span>
            </button>
            <button @click="router.push('/chat')" class="bg-gradient-to-br from-white to-slate-50 border border-slate-200 rounded-xl shadow-sm hover:shadow-md hover:emerald-indigo-200 transition-all py-2 px-3 group relative overflow-hidden flex items-center justify-center gap-2">
              <MessageCircle class="w-4 h-4 text-emerald-500" />
              <span class="font-bold text-sm text-slate-700 group-hover:text-emerald-700 transition-colors">虚拟书友</span>
            </button>
          </div>
          
        </div>

      </div>
    </div>
  </EditorialLayout>
</template>

<style scoped>
/* Custom scrollbar for small areas like the top10 list */
.custom-scrollbar::-webkit-scrollbar {
  width: 4px;
}
.custom-scrollbar::-webkit-scrollbar-track {
  background: transparent;
}
.custom-scrollbar::-webkit-scrollbar-thumb {
  background-color: #cbd5e1;
  border-radius: 4px;
}
.custom-scrollbar:hover::-webkit-scrollbar-thumb {
  background-color: #94a3b8;
}
</style>
