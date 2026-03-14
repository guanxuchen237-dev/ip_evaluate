<script setup lang="ts">
import EditorialLayout from "@/components/layout/EditorialLayout.vue";
import DataCollectionMonitor from "@/components/dashboard/DataCollectionMonitor.vue";
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
        <p class="text-sm uppercase tracking-[0.2em] text-chart-cyan mb-4">Real-time Pipeline</p>
        <h2 class="editorial-headline text-4xl text-foreground">
          数据采集监控
        </h2>
        <p class="text-muted-foreground mt-3">
          混合爬虫策略实时采集多平台数据，突破反爬机制
        </p>
      </div>
      <div
        v-motion
        :initial="{ opacity: 0, y: 30 }"
        :enter="{ opacity: 1, y: 0, transition: { delay: 100 } }"
      >
        <DataCollectionMonitor />
      </div>
    </section>
  </EditorialLayout>
</template>
