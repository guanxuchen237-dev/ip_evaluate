<script setup lang="ts">
import { computed } from "vue";

const props = withDefaults(defineProps<{
  data: number[];
  width?: number;
  height?: number;
  color?: string;
  showDot?: boolean;
}>(), {
  width: 100,
  height: 40,
  color: "hsl(var(--primary))",
  showDot: true
});

const pathData = computed(() => {
  if (props.data.length < 2) return "";
  
  const min = Math.min(...props.data);
  const max = Math.max(...props.data);
  const range = max - min || 1;
  
  const points = props.data.map((value, index) => {
    const x = (index / (props.data.length - 1)) * props.width;
    const y = props.height - ((value - min) / range) * props.height * 0.8 - props.height * 0.1;
    return { x, y };
  });

  // Create smooth curve path
  const firstP = points[0];
  if (!firstP) return "";
  
  let path = `M ${firstP.x} ${firstP.y}`;
  for (let i = 1; i < points.length; i++) {
    const prev = points[i - 1];
    const curr = points[i];
    if (prev && curr) {
        const cpx = (prev.x + curr.x) / 2;
        path += ` Q ${cpx} ${prev.y}, ${curr.x} ${curr.y}`;
    }
  }
  
  return path;
});

const lastPoint = computed(() => {
  if (props.data.length < 2) return null;
  const min = Math.min(...props.data);
  const max = Math.max(...props.data);
  const range = max - min || 1;
  const lastValue = props.data[props.data.length - 1];
  
  if (lastValue === undefined) return null;

  return {
    x: props.width,
    y: props.height - ((lastValue - min) / range) * props.height * 0.8 - props.height * 0.1,
  };
});
</script>

<template>
  <svg
    :width="width"
    :height="height"
    class="overflow-visible"
    v-motion
    :initial="{ opacity: 0 }"
    :enter="{ opacity: 1, transition: { duration: 500 } }"
  >
    <path
      :d="pathData"
      fill="none"
      :stroke="color"
      stroke-width="2"
      stroke-linecap="round"
      v-motion
      :initial="{ pathLength: 0 }"
      :enter="{ pathLength: 1, transition: { duration: 1000, ease: 'easeOut' } }"
    />
    
    <circle
      v-if="showDot && lastPoint"
      :cx="lastPoint.x"
      :cy="lastPoint.y"
      r="4"
      :fill="color"
      v-motion
      :initial="{ scale: 0 }"
      :enter="{ scale: 1, transition: { duration: 300, delay: 800 } }"
    />
    
    <!-- Glow effect for last point -->
    <circle
      v-if="showDot && lastPoint"
      :cx="lastPoint.x"
      :cy="lastPoint.y"
      r="8"
      :fill="color"
      opacity="0.2"
      class="animate-pulse"
    />
  </svg>
</template>
