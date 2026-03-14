<script setup lang="ts">
import EditorialLayout from '@/components/layout/EditorialLayout.vue'
import { Glasses, Sparkles, Layers, Zap } from 'lucide-vue-next'
</script>

<template>
  <EditorialLayout>
    <div class="min-h-screen px-8 py-12">
      <!-- Header -->
      <div 
        v-motion
        :initial="{ opacity: 0, y: 20 }"
        :enter="{ opacity: 1, y: 0 }"
        class="mb-12 text-center"
      >
        <div class="w-16 h-16 rounded-2xl bg-gradient-to-br from-purple-500 to-cyan-500 flex items-center justify-center mx-auto mb-6">
          <Glasses class="w-8 h-8 text-white" />
        </div>
        <h1 class="text-5xl font-serif font-bold text-foreground mb-4">XR Universe</h1>
        <p class="text-xl text-muted-foreground">沉浸式3D IP体验空间</p>
      </div>

      <!-- Mode Selection -->
      <div class="grid grid-cols-1 md:grid-cols-3 gap-8 max-w-6xl mx-auto">
        <div 
          v-for="(mode, index) in [
            { title: 'AR模式', desc: '增强现实IP展示', icon: Layers, color: 'from-blue-500 to-cyan-500' },
            { title: 'VR模式', desc: '虚拟现实沉浸体验', icon: Glasses, color: 'from-purple-500 to-pink-500' },
            { title: '3D模式', desc: '立体可视化浏览', icon: Zap, color: 'from-yellow-500 to-red-500' },
          ]"
          :key="mode.title"
          v-motion
          :initial="{ opacity: 0, scale: 0.9 }"
          :visible="{ opacity: 1, scale: 1, transition: { delay: index * 150 } }"
          class="editorial-card rounded-3xl p-8 hover:scale-105 transition-all cursor-pointer group"
        >
          <div :class="`w-16 h-16 rounded-2xl bg-gradient-to-br ${mode.color} flex items-center justify-center mb-6 group-hover:scale-110 transition-transform shadow-lg`">
            <component :is="mode.icon" class="w-8 h-8 text-white" />
          </div>
          <h3 class="text-2xl font-bold text-foreground mb-3">{{ mode.title }}</h3>
          <p class="text-muted-foreground">{{ mode.desc }}</p>
        </div>
      </div>

      <!-- Features -->
      <div class="mt-16 max-w-4xl mx-auto text-center">
        <div class="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-primary/10 border border-primary/20 mb-6">
          <Sparkles class="w-4 h-4 text-primary" />
          <span class="text-sm font-medium text-primary">Coming Soon</span>
        </div>
        <p class="text-muted-foreground text-lg">
          XR体验模式正在开发中。将提供：<br>
          AR卡片扫描、VR空间漫游、3D IP可视化等功能。
        </p>
      </div>
    </div>
  </EditorialLayout>
</template>

