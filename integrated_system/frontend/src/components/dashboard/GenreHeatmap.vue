<script setup lang="ts">
import { computed } from "vue";

interface HeatmapCell {
  genre: string;
  period: string;
  value: number;
}

const genres = ["奇幻", "都市", "仙侠", "科幻", "历史", "悬疑", "言情", "军事"];
const periods = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

const heatmapData = computed(() => {
  const data: HeatmapCell[] = [];
  genres.forEach(genre => {
    periods.forEach(period => {
      data.push({
        genre,
        period,
        value: Math.random() * 100,
      });
    });
  });
  return data;
});

const getColor = (value: number) => {
  if (value < 20) return "bg-primary/5";
  if (value < 40) return "bg-primary/20";
  if (value < 60) return "bg-primary/40";
  if (value < 80) return "bg-primary/60";
  return "bg-primary/90";
};
</script>

<template>
  <div
    v-motion
    :initial="{ opacity: 0, y: 20 }"
    :enter="{ opacity: 1, y: 0, transition: { duration: 500 } }"
    class="editorial-card rounded-3xl p-6"
  >
    <div class="flex items-center justify-between mb-6">
      <div>
        <h3 class="text-xl font-serif font-semibold text-foreground">类型热力图</h3>
        <p class="text-sm text-muted-foreground">Genre Heatmap · 周活跃分布</p>
      </div>
      <div class="flex items-center gap-2 text-xs text-muted-foreground">
        <span>低</span>
        <div class="flex gap-0.5">
          <div v-for="opacity in [5, 20, 40, 60, 90]" :key="opacity" class="w-3 h-3 rounded-sm" :class="`bg-primary/${opacity}`" />
        </div>
        <span>高</span>
      </div>
    </div>

    <div class="overflow-x-auto">
      <div class="min-w-[500px]">
        <!-- Header -->
        <div class="flex gap-1 mb-2">
          <div class="w-16" />
          <div 
            v-for="(period, i) in periods" 
            :key="period"
            v-motion
            :initial="{ opacity: 0, y: -10 }"
            :enter="{ opacity: 1, y: 0, transition: { delay: i * 50 } }"
            class="flex-1 text-center text-xs text-muted-foreground"
          >
            {{ period }}
          </div>
        </div>

        <!-- Rows -->
        <div v-for="(genre, genreIndex) in genres" :key="genre" class="flex gap-1 mb-1">
          <div
            v-motion
            :initial="{ opacity: 0, x: -10 }"
            :enter="{ opacity: 1, x: 0, transition: { delay: genreIndex * 50 } }"
            class="w-16 text-xs text-muted-foreground flex items-center"
          >
            {{ genre }}
          </div>
          <template v-for="(period, periodIndex) in periods" :key="`${genre}-${period}`">
            <div
              v-motion
              :initial="{ opacity: 0, scale: 0.5 }"
              :enter="{ opacity: 1, scale: 1, transition: { delay: genreIndex * 30 + periodIndex * 30, duration: 300 } }"
              class="flex-1 aspect-square rounded-md cursor-pointer transition-transform hover:scale-110 hover:z-10 relative group"
              :class="getColor(heatmapData.find(c => c.genre === genre && c.period === period)?.value || 0)"
            >
              <!-- Tooltip -->
              <div class="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-2 py-1 bg-foreground text-background text-xs rounded-md opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap z-20 pointer-events-none">
                {{ genre }} · {{ period }}: {{ heatmapData.find(c => c.genre === genre && c.period === period)?.value.toFixed(0) }}%
              </div>
            </div>
          </template>
        </div>
      </div>
    </div>
  </div>
</template>
