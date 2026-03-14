<script setup lang="ts">
import { ref, onMounted, computed, type CSSProperties } from "vue";

interface BubbleData {
  label: string;
  value: number;
  color: string;
}

const props = defineProps<{
  data: BubbleData[];
}>();

const mousePos = ref({ x: 0.5, y: 0.5 });
const mounted = ref(false);

onMounted(() => {
  mounted.value = true;
});

const handleMouseMove = (e: MouseEvent) => {
  const target = e.currentTarget as HTMLDivElement;
  const rect = target.getBoundingClientRect();
  mousePos.value = {
    x: (e.clientX - rect.left) / rect.width,
    y: (e.clientY - rect.top) / rect.height
  };
};

const total = computed(() => props.data.reduce((sum, d) => sum + d.value, 0));

const bubbles = computed(() => props.data.map((item, index) => {
  const percentage = (item.value / total.value) * 100;
  const size = Math.max(60, Math.min(140, percentage * 2.5));
  
  // Base position with mouse interaction offset
  const angle = (index / props.data.length) * Math.PI * 2;
  const radius = 80;
  const baseX = 50 + Math.cos(angle) * radius * 0.8;
  const baseY = 50 + Math.sin(angle) * radius * 0.7;
  
  // Add mouse interaction
  const offsetX = (mousePos.value.x - 0.5) * 15 * (index % 2 === 0 ? 1 : -1);
  const offsetY = (mousePos.value.y - 0.5) * 15 * (index % 2 === 0 ? -1 : 1);
  
  return {
    ...item,
    percentage,
    size,
    x: baseX + offsetX,
    y: baseY + offsetY,
    delay: index * 100
  };
}));
</script>

<template>
  <div 
    class="relative w-full h-80"
    @mousemove="handleMouseMove"
  >
    <div
      v-for="(bubble, index) in bubbles"
      :key="bubble.label"
      class="absolute transform -translate-x-1/2 -translate-y-1/2 transition-all duration-700 ease-out"
      :class="[mounted ? 'opacity-100 scale-100' : 'opacity-0 scale-0']"
      :style="{
        left: `${bubble.x}%`,
        top: `${bubble.y}%`,
        width: `${bubble.size}px`,
        height: `${bubble.size}px`,
        transitionDelay: `${bubble.delay}ms`,
      }"
    >
      <!-- Outer glow -->
      <div 
        class="absolute inset-0 rounded-full blur-xl opacity-30 animate-pulse"
        :style="{ 
          backgroundColor: bubble.color,
          animationDelay: `${index * 300}ms`
        }"
      />
      
      <!-- Main bubble -->
      <div 
        class="absolute inset-2 rounded-full backdrop-blur-md border border-white/40 flex flex-col items-center justify-center cursor-pointer hover:scale-110 transition-transform duration-300 group"
        :style="{ 
          background: `linear-gradient(135deg, ${bubble.color}40, ${bubble.color}20)`,
        }"
      >
        <span class="text-lg font-serif font-semibold text-foreground">
          {{ bubble.percentage.toFixed(0) }}%
        </span>
        <span class="text-xs text-muted-foreground text-center px-2 opacity-0 group-hover:opacity-100 transition-opacity">
          {{ bubble.label }}
        </span>
      </div>
    </div>
    
    <!-- Center label -->
    <div class="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 text-center z-10 pointer-events-none">
      <p class="text-sm text-muted-foreground">Total IPs</p>
      <p class="text-3xl font-serif font-bold text-foreground">{{ total.toLocaleString() }}</p>
    </div>
  </div>
</template>
