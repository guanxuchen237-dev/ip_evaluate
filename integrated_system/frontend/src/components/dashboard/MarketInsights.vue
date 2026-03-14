<script setup lang="ts">
import { ref } from "vue";
import { ArrowUpRight, Eye } from "lucide-vue-next";
import TrendSparkline from "@/components/charts/TrendSparkline.vue";
import ComparisonChart from "@/components/charts/ComparisonChart.vue";
import AnimatedBarChart from "@/components/charts/AnimatedBarChart.vue";

import axios from 'axios';
import { onMounted } from 'vue';

const trendingIPs = ref([
  { 
    name: "夜的命名术", 
    trend: [45, 52, 48, 65, 72, 68, 85], 
    change: "+24%",
    views: "2.3M",
    isHot: true,
  },
  { 
    name: "全球高武", 
    trend: [60, 58, 62, 55, 68, 75, 82], 
    change: "+18%",
    views: "1.8M",
    isHot: true,
  },
]);

onMounted(async () => {
  try {
    const res = await axios.get('http://localhost:5000/api/charts/rank');
    if (res.data && Array.isArray(res.data)) {
        // Map backend data to frontend format
        // Backend returns: [{title, rank, change, heat...}, ...] (assumed)
        // Adjust mapping based on actual API response structure. 
        // For now, mapping simulated structure if fields match, or falling back.
        trendingIPs.value = res.data.slice(0, 5).map((item: any) => ({
             name: item.title,
             trend: [50, 60, 55, 70, 65, 80, 75], // Mock trend if not provided
             change: item.change || "+10%",
             views: item.views || "1M",
             isHot: true
        }));
    }
  } catch (e) {
    console.error("Failed to fetch rank", e);
  }
});

const engagementData = [
  { label: "收藏率", value: 78, color: "linear-gradient(90deg, hsl(var(--primary)), hsl(var(--accent)))" },
  { label: "互动率", value: 65, color: "linear-gradient(90deg, hsl(var(--chart-purple)), hsl(var(--chart-blue)))" },
  { label: "完读率", value: 45, color: "linear-gradient(90deg, hsl(var(--chart-green)), hsl(var(--chart-cyan)))" },
  { label: "推荐率", value: 82, color: "linear-gradient(90deg, hsl(var(--chart-yellow)), hsl(var(--chart-red)))" },
];

const comparisonData = [
  { label: "日活用户", current: 2847000, previous: 2156000, unit: "" },
  { label: "新增订阅", current: 45600, previous: 38200, unit: "" },
  { label: "平均阅读时长", current: 48, previous: 42, unit: "min" },
];
</script>

<template>
  <div class="grid grid-cols-12 gap-6">
    <!-- Trending IPs -->
    <div
      v-motion
      :initial="{ opacity: 0, y: 20 }"
      :enter="{ opacity: 1, y: 0, transition: { duration: 500 } }"
      class="col-span-12 lg:col-span-7 editorial-card rounded-3xl p-6"
    >
      <div class="flex items-center justify-between mb-6">
        <div>
          <h3 class="text-xl font-serif font-semibold text-foreground">热度趋势</h3>
          <p class="text-sm text-muted-foreground">Trending IPs · 7日热度变化</p>
        </div>
        <button
          class="text-sm text-primary hover:underline flex items-center gap-1 transition-transform hover:scale-105 active:scale-95"
        >
          查看全部 <ArrowUpRight class="w-4 h-4" />
        </button>
      </div>

      <div class="space-y-4">
        <div
          v-for="(ip, index) in trendingIPs"
          :key="ip.name"
          v-motion
          :initial="{ opacity: 0, x: -20 }"
          :enter="{ opacity: 1, x: 0, transition: { duration: 400, delay: index * 100 } }"
          class="flex items-center justify-between p-4 rounded-2xl bg-muted/20 hover:bg-muted/30 transition-colors cursor-pointer group hover:translate-x-1"
        >
          <div class="flex items-center gap-4">
            <span class="text-lg font-serif font-medium text-muted-foreground w-6">
              {{ (index + 1).toString().padStart(2, '0') }}
            </span>
            <div>
              <div class="flex items-center gap-2">
                <span class="font-medium text-foreground group-hover:text-primary transition-colors">
                  {{ ip.name }}
                </span>
                <span
                  v-if="ip.isHot"
                  v-motion
                  :initial="{ scale: 0 }"
                  :enter="{ scale: 1, transition: { delay: index * 100 + 300 } }"
                  class="px-2 py-0.5 rounded-full bg-chart-red/10 text-chart-red text-xs font-medium"
                >
                  HOT
                </span>
              </div>
              <div class="flex items-center gap-3 text-xs text-muted-foreground mt-1">
                <span class="flex items-center gap-1">
                  <Eye class="w-3 h-3" /> {{ ip.views }}
                </span>
              </div>
            </div>
          </div>
          
          <div class="flex items-center gap-4">
            <TrendSparkline 
              :data="ip.trend" 
              :width="80"
              :height="30"
              :color="ip.change.startsWith('+') ? 'hsl(var(--chart-green))' : 'hsl(var(--chart-red))'"
            />
            <span 
              class="text-sm font-medium"
              :class="ip.change.startsWith('+') ? 'text-chart-green' : 'text-chart-red'"
            >
              {{ ip.change }}
            </span>
          </div>
        </div>
      </div>
    </div>

    <!-- Right column -->
    <div class="col-span-12 lg:col-span-5 space-y-6">
      <!-- Engagement metrics -->
      <div
        v-motion
        :initial="{ opacity: 0, y: 20 }"
        :enter="{ opacity: 1, y: 0, transition: { duration: 500, delay: 100 } }"
        class="editorial-card rounded-3xl p-6"
      >
        <h3 class="text-lg font-serif font-semibold text-foreground mb-1">用户参与度</h3>
        <p class="text-sm text-muted-foreground mb-6">Engagement Metrics</p>
        <AnimatedBarChart :data="engagementData" />
      </div>

      <!-- Comparison -->
      <div
        v-motion
        :initial="{ opacity: 0, y: 20 }"
        :enter="{ opacity: 1, y: 0, transition: { duration: 500, delay: 200 } }"
        class="editorial-card rounded-3xl p-6"
      >
        <h3 class="text-lg font-serif font-semibold text-foreground mb-1">周期对比</h3>
        <p class="text-sm text-muted-foreground mb-6">Period Comparison</p>
        <ComparisonChart :data="comparisonData" />
      </div>
    </div>
  </div>
</template>
