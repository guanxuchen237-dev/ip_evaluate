<script setup lang="ts">
import { computed } from "vue";

const props = withDefaults(defineProps<{
  data: number[];
  primaryColor?: string;
  secondaryColor?: string;
}>(), {
  primaryColor: "hsl(var(--primary))",
  secondaryColor: "hsl(var(--accent))"
});

const chartData = computed(() => {
  if (props.data.length < 2) return { pathD: "", fillPathD: "", gradientId: "" };
  
  const min = Math.min(...props.data);
  const max = Math.max(...props.data);
  const range = max - min || 1;
  const height = 60; // Keep original height for now, as props.height is not defined in the original code
  const width = 100; // viewbox width (original was 100, instruction says 1000, but viewbox is 100)

  const points = props.data.map((value, index) => {
    const x = (index / (props.data.length - 1)) * width;
    const y = height - ((value - min) / range) * height * 0.8 - height * 0.1;
    return { x, y };
  });

  if (!points[0]) return { pathD: "", fillPathD: "", gradientId: "" };
  
  let pathD = `M ${points[0].x} ${points[0].y}`;
  
  for (let i = 0; i < points.length - 1; i++) {
    const current = points[i];
    const next = points[i + 1];
    
    if (!current || !next) continue;

    const nextNext = points[i + 2] || next;
    const prev = points[i - 1] || current;

    const cp1x = current.x + (next.x - prev.x) / 6;
    const cp1y = current.y + (next.y - prev.y) / 6;
    const cp2x = next.x - (nextNext.x - current.x) / 6;
    const cp2y = next.y - (nextNext.y - current.y) / 6;
    
    pathD += ` C ${cp1x} ${cp1y}, ${cp2x} ${cp2y}, ${next.x} ${next.y}`;
  }
  
  // Close the path for fill
  // Close the path for fill
  const lastPoint = points[points.length - 1];
  const firstPoint = points[0];
  
  if (lastPoint && firstPoint) {
      const fillPathD = pathD + ` L ${lastPoint.x} ${height} L ${firstPoint.x} ${height} Z`;
      
      return { 
        pathD,
        fillPathD,
        gradientId: `wave-gradient-${Math.random().toString(36).substr(2, 9)}`
      };
  }
  return { pathD, fillPathD: "", gradientId: "" };
});
</script>

<template>
  <div class="relative">
    <svg viewBox="0 0 100 60" class="w-full h-full" preserveAspectRatio="none">
      <defs>
        <linearGradient :id="chartData.gradientId" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" :stop-color="primaryColor" stop-opacity="0.6" />
          <stop offset="50%" :stop-color="secondaryColor" stop-opacity="0.4" />
          <stop offset="100%" :stop-color="primaryColor" stop-opacity="0.1" />
        </linearGradient>
        <filter id="glow">
          <feGaussianBlur stdDeviation="1.5" result="coloredBlur"/>
          <feMerge>
            <feMergeNode in="coloredBlur"/>
            <feMergeNode in="SourceGraphic"/>
          </feMerge>
        </filter>
      </defs>
      
      <!-- Animated wave background -->
      <path 
        :d="chartData.fillPathD"
        :fill="`url(#${chartData.gradientId})`"
        class="animate-pulse-slow"
      />
      
      <!-- Stroke line on top -->
      <path 
        :d="chartData.pathD"
        fill="none"
        :stroke="primaryColor"
        stroke-width="0.5"
        stroke-linecap="round"
        filter="url(#glow)"
        class="opacity-80"
      />
    </svg>
    
    <!-- Floating data points -->
    <div class="absolute inset-0 flex items-end justify-around pb-2 px-4">
      <div 
        v-for="(val, i) in data.slice(0, 6)"
        :key="i"
        class="flex flex-col items-center animate-float"
        :style="{ animationDelay: `${i * 200}ms` }"
      >
        <span class="text-xs font-medium text-slate-600">{{ val }}%</span>
      </div>
    </div>
  </div>
</template>
