<script setup lang="ts">
import FloatingDock from './FloatingDock.vue';

withDefaults(defineProps<{
  showDock?: boolean;
  dockItems?: any[];
}>(), {
  showDock: true,
  dockItems: undefined
});
</script>

<template>
  <div class="min-h-screen w-full bg-background relative overflow-x-hidden">
    <!-- Paper texture background -->
    <div 
      class="fixed inset-0 pointer-events-none opacity-60 z-0"
      style="
        background-image: url('/images/paper-texture-bg.png');
        background-size: cover;
        background-position: center;
        background-repeat: no-repeat;
      "
    />
    
    <!-- Subtle paper grain overlay -->
    <div 
      class="fixed inset-0 pointer-events-none opacity-20 z-0"
      style="
        background-image: url('data:image/svg+xml,%3Csvg viewBox=\'0 0 200 200\' xmlns=\'http://www.w3.org/2000/svg\'%3E%3Cfilter id=\'noiseFilter\'%3E%3CfeTurbulence type=\'fractalNoise\' baseFrequency=\'0.85\' numOctaves=\'4\' stitchTiles=\'stitch\'/%3E%3C/filter%3E%3Crect width=\'100%25\' height=\'100%25\' filter=\'url(%23noiseFilter)\'/%3E%3C/svg%3E');
      "
    />
    
    <!-- Animated gradient blobs -->
    <div class="fixed inset-0 pointer-events-none z-0 overflow-hidden">
      <div class="absolute top-1/4 -left-32 w-96 h-96 bg-gradient-to-br from-primary/8 to-accent/4 rounded-full blur-3xl animate-blob" />
      <div class="absolute top-1/3 right-0 w-[500px] h-[500px] bg-gradient-to-bl from-accent/6 to-chart-purple/4 rounded-full blur-3xl animate-blob animation-delay-2000" />
      <div class="absolute bottom-1/4 left-1/3 w-80 h-80 bg-gradient-to-tr from-chart-cyan/6 to-primary/4 rounded-full blur-3xl animate-blob animation-delay-4000" />
    </div>
    
    <!-- Main content -->
    <main class="relative z-10 pb-28">
      <slot />
    </main>
    
    <!-- Floating navigation dock -->
    <FloatingDock v-if="showDock" :items="dockItems" />
  </div>
</template>
