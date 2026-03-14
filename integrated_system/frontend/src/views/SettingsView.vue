<script setup lang="ts">
import EditorialLayout from '@/components/layout/EditorialLayout.vue'
import { Settings as SettingsIcon, User, Bell, Shield, Palette, Database } from 'lucide-vue-next'

const settingSections = [
  { title: '个人信息', icon: User, desc: '管理账户资料' },
  { title: '通知设置', icon: Bell, desc: '配置提醒偏好' },
  { title: '隐私安全', icon: Shield, desc: '数据权限管理' },
  { title: '界面主题', icon: Palette, desc: '自定义外观' },
  { title: '数据导出', icon: Database, desc: '下载个人数据' },
]
</script>

<template>
  <EditorialLayout>
    <div class="min-h-screen px-8 py-12">
      <!-- Header -->
      <div 
        v-motion
        :initial="{ opacity: 0, y: 20 }"
        :enter="{ opacity: 1, y: 0 }"
        class="mb-12"
      >
        <div class="flex items-center gap-3 mb-2">
          <div class="w-12 h-12 rounded-2xl bg-gradient-to-br from-slate-500/20 to-slate-700/20 flex items-center justify-center">
            <SettingsIcon class="w-6 h-6 text-slate-700" />
          </div>
          <div>
            <h1 class="text-4xl font-serif font-bold text-foreground">Settings</h1>
            <p class="text-muted-foreground">系统设置与偏好</p>
          </div>
        </div>
      </div>

      <!-- Settings List -->
      <div class="max-w-4xl space-y-4">
        <div 
          v-for="(section, index) in settingSections"
          :key="section.title"
          v-motion
          :initial="{ opacity: 0, x: -20 }"
          :visible="{ opacity: 1, x: 0, transition: { delay: index * 100 } }"
          class="editorial-card rounded-3xl p-6 hover:bg-white/60 transition-all cursor-pointer group"
        >
          <div class="flex items-center gap-4">
            <div class="w-12 h-12 rounded-xl bg-primary/10 flex items-center justify-center group-hover:scale-110 transition-transform">
              <component :is="section.icon" class="w-6 h-6 text-primary" />
            </div>
            <div class="flex-1">
              <h3 class="font-semibold text-foreground mb-1">{{ section.title }}</h3>
              <p class="text-sm text-muted-foreground">{{ section.desc }}</p>
            </div>
            <svg class="w-5 h-5 text-muted-foreground group-hover:translate-x-1 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
            </svg>
          </div>
        </div>
      </div>

      <!-- Version Info -->
      <div 
        v-motion
        :initial="{ opacity: 0 }"
        :visible="{ opacity: 1, transition: { delay: 600 } }"
        class="mt-16 text-center text-sm text-muted-foreground"
      >
        <p>IP Lumina v1.0.0</p>
        <p class="mt-2">Powered by Vue 3 + Flask + ECharts</p>
      </div>
    </div>
  </EditorialLayout>
</template>
