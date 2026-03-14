<script setup lang="ts">
interface BarData {
  label: string;
  value: number;
  maxValue?: number;
  color?: string;
}

defineProps<{
  data: BarData[];
}>();

const getMaxValue = (data: BarData[]) => Math.max(...data.map(d => d.maxValue || d.value));
</script>

<template>
  <div class="space-y-4">
    <div 
      v-for="(item, index) in data" 
      :key="item.label"
      v-motion
      :initial="{ opacity: 0, x: -20 }"
      :enter="{ opacity: 1, x: 0, transition: { duration: 400, delay: index * 100 } }"
      class="space-y-2"
    >
      <div class="flex justify-between items-center text-sm">
        <span class="text-foreground font-medium">{{ item.label }}</span>
        <span class="text-muted-foreground">{{ item.value }}%</span>
      </div>
      <div class="h-3 bg-muted/30 rounded-full overflow-hidden">
        <div
          class="h-full rounded-full transition-all duration-1000 ease-out"
          :style="{
            width: `${(item.value / getMaxValue(data)) * 100}%`,
            background: item.color || 'linear-gradient(90deg, hsl(var(--primary)), hsl(var(--accent)))',
          }"
        />
      </div>
    </div>
  </div>
</template>
