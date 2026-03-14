<script setup lang="ts">
import EditorialLayout from '@/components/layout/EditorialLayout.vue'
import { Megaphone, Sparkles, Image as ImageIcon, Video, FileText } from 'lucide-vue-next'
</script>

<template>
  <EditorialLayout>
    <section class="px-8 py-20 max-w-5xl mx-auto text-center">
      <div 
        v-motion
        :initial="{ opacity: 0, y: 20 }"
        :enter="{ opacity: 1, y: 0 }"
        class="w-16 h-16 rounded-2xl bg-gradient-to-br from-pink-500/20 to-orange-500/20 flex items-center justify-center mx-auto mb-6"
      >
        <Megaphone class="w-8 h-8 text-pink-600" />
      </div>

      <h1 
        v-motion
        :initial="{ opacity: 0, y: 30 }"
        :enter="{ opacity: 1, y: 0, transition: { duration: 600, delay: 100 } }"
        class="editorial-headline text-6xl mb-6"
      >
        AI宣发生成器
      </h1>

      <p 
        v-motion
        :initial="{ opacity: 0, y: 20 }"
        :enter="{ opacity: 1, y: 0, transition: { delay: 200 } }"
        class="text-xl text-muted-foreground mb-16"
      >
        一键生成社交媒体营销内容
      </p>

      <!-- Content Types -->
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <div 
          v-for="(type, index) in [
            { title: '海报生成', icon: ImageIcon, color: 'chart-blue' },
            { title: '短视频', icon: Video, color: 'chart-red' },
            { title: '文案撰写', icon: FileText, color: 'chart-green' },
            { title: 'AI配音', icon: Sparkles, color: 'chart-purple' },
          ]"
          :key="type.title"
          v-motion
          :initial="{ opacity: 0, scale: 0.9 }"
          :visible="{ opacity: 1, scale: 1, transition: { delay: 300 + index * 100 } }"
          class="editorial-card rounded-3xl p-8 hover:scale-105 transition-all cursor-pointer"
        >
          <div :class="`w-16 h-16 rounded-2xl bg-${type.color}/10 flex items-center justify-center mx-auto mb-4`">
            <component :is="type.icon" :class="`w-8 h-8 text-${type.color}`" />
          </div>
          <h3 class="font-semibold text-foreground">{{ type.title }}</h3>
        </div>
      </div>

      <div class="mt-16 p-12 rounded-3xl bg-gradient-to-br from-primary/5 to-accent/5 border border-primary/10">
        <Sparkles class="w-12 h-12 text-primary mx-auto mb-6" />
        <p class="text-lg text-muted-foreground">
          AI宣发生成功能正在开发中<br>
          将支持：社交媒体文案、宣传海报、短视频脚本、配音生成等
        </p>
      </div>
    </section>
  </EditorialLayout>
</template>
