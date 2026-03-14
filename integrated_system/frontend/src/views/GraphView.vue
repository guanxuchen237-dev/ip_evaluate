<script setup lang="ts">
import EditorialLayout from '@/components/layout/EditorialLayout.vue'
import KnowledgeGraph3D from '@/components/graph/KnowledgeGraph3D.vue'
import { Network } from 'lucide-vue-next'
</script>

<template>
  <EditorialLayout>
    <div class="min-h-screen flex flex-col px-8 py-12">
      <!-- Header -->
      <div 
        v-motion
        :initial="{ opacity: 0, y: 20 }"
        :enter="{ opacity: 1, y: 0, transition: { duration: 400 } }"
        class="mb-8"
      >
        <div class="flex items-center gap-3 mb-2">
          <div class="w-12 h-12 rounded-2xl bg-gradient-to-br from-primary to-accent flex items-center justify-center">
            <Network class="w-6 h-6 text-white" />
          </div>
          <div>
            <h1 class="text-4xl font-serif font-bold text-foreground">IP Universe</h1>
            <p class="text-muted-foreground">3D Knowledge Graph · 探索IP关联网络</p>
          </div>
        </div>
      </div>

      <!-- 3D Canvas -->
      <div 
        v-motion
        :initial="{ opacity: 0, y: 20 }"
        :enter="{ opacity: 1, y: 0, transition: { duration: 500, delay: 100 } }"
        class="flex-1 min-h-[600px] glass-card rounded-3xl overflow-hidden"
      >
        <KnowledgeGraph3D />
      </div>
    </div>
  </EditorialLayout>
</template>
