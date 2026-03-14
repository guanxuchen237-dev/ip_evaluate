<script setup lang="ts">
interface ComparisonItem {
  label: string;
  current: number;
  previous: number;
  unit?: string;
}

defineProps<{
  data: ComparisonItem[];
}>();

const getMaxValue = (data: ComparisonItem[]) => Math.max(...data.flatMap(d => [d.current, d.previous]));
</script>

<template>
  <div class="space-y-6">
    <div 
      v-for="(item, index) in data" 
      :key="item.label"
      v-motion
      :initial="{ opacity: 0, x: -20 }"
      :enter="{ opacity: 1, x: 0, transition: { duration: 400, delay: index * 100 } }"
      class="space-y-3"
    >
      <div class="flex justify-between items-center">
        <span class="text-sm font-medium text-foreground">{{ item.label }}</span>
        <span 
          class="text-xs font-medium px-2 py-1 rounded-full"
          :class="((item.current - item.previous) / item.previous) * 100 >= 0 
            ? 'bg-chart-green/10 text-chart-green' 
            : 'bg-chart-red/10 text-chart-red'"
        >
          {{ ((item.current - item.previous) / item.previous * 100) >= 0 ? '+' : '' }}
          {{ (((item.current - item.previous) / item.previous) * 100).toFixed(1) }}%
        </span>
      </div>
      
      <div class="relative h-8">
        <!-- Previous value (background) -->
        <div 
          class="absolute top-1 h-3 bg-muted/40 rounded-full transition-all duration-500"
          :style="{ width: `${(item.previous / getMaxValue(data)) * 100}%` }"
        />
        
        <!-- Current value (foreground) -->
        <div 
          class="absolute top-0 h-5 rounded-full transition-all duration-700"
          :style="{
            width: `${(item.current / getMaxValue(data)) * 100}%`,
            background: ((item.current - item.previous) / item.previous) * 100 >= 0 
              ? 'linear-gradient(90deg, hsl(var(--chart-green)), hsl(var(--primary)))'
              : 'linear-gradient(90deg, hsl(var(--chart-red)), hsl(var(--chart-yellow)))',
          }"
        />
        
        <!-- Values -->
        <div class="absolute right-0 top-0 h-full flex items-center gap-3 text-xs">
          <span class="text-muted-foreground">
            {{ item.previous }}{{ item.unit }}
          </span>
          <span class="text-foreground font-medium">
            {{ item.current }}{{ item.unit }}
          </span>
        </div>
      </div>
    </div>
    
    <!-- Legend -->
    <div 
      v-motion
      :initial="{ opacity: 0 }"
      :enter="{ opacity: 1, transition: { delay: 500 } }"
      class="flex items-center gap-6 pt-2 text-xs text-muted-foreground"
    >
      <div class="flex items-center gap-2">
        <div class="w-3 h-2 bg-muted/40 rounded-full" />
        <span>上期</span>
      </div>
      <div class="flex items-center gap-2">
        <div class="w-3 h-3 rounded-full bg-gradient-to-r from-chart-green to-primary" />
        <span>本期</span>
      </div>
    </div>
  </div>
</template>
