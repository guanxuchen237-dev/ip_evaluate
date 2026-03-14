<script setup lang="ts">
import EditorialLayout from "@/components/layout/EditorialLayout.vue";
import VirtualFocusGroup from "@/components/analysis/VirtualFocusGroup.vue";
</script>

<template>
  <EditorialLayout>
    <section class="px-8 py-12 max-w-7xl mx-auto min-h-screen">
      <div 
        v-motion
        :initial="{ opacity: 0, y: 20 }"
        :enter="{ opacity: 1, y: 0, transition: { duration: 600 } }"
        class="text-center mb-8"
      >
        <p class="text-sm uppercase tracking-[0.2em] text-chart-purple mb-4">Market Testing</p>
        <h2 class="editorial-headline text-4xl text-foreground">
          虚拟读者焦点小组
        </h2>
        <p class="text-muted-foreground mt-3">
          AI模拟不同用户画像进行市场测试，验证IP潜力
        </p>
      </div>
      <div
        v-motion
        :initial="{ opacity: 0, y: 30 }"
        :enter="{ opacity: 1, y: 0, transition: { delay: 100 } }"
      >
        <VirtualFocusGroup />
      </div>
    </section>
  </EditorialLayout>
</template>
