<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { 
  LayoutDashboard,
  FileSearch, 
  Sparkles, 
  Megaphone, 
  Settings,
  BookOpen,
  Network,
  Glasses,
  User,
  Users
} from 'lucide-vue-next'

interface MenuItem {
  title: string
  titleEn: string
  url: string
  icon: any
}

const route = useRoute()

const menuItems: MenuItem[] = [
  { title: "仪表盘", titleEn: "Dashboard", url: "/", icon: LayoutDashboard },
  { title: "虚拟读者", titleEn: "Reader Space", url: "/reader-space", icon: Users },
  { title: "灵感探索", titleEn: "AI Agent", url: "/search", icon: Sparkles },
  { title: "设置", titleEn: "Settings", url: "/settings", icon: Settings },
]

const isActive = (url: string) => {
  return route.path === url
}
</script>

<template>
  <aside class="w-64 min-h-screen bg-white/60 backdrop-blur-xl border-r border-white/40 p-6 flex flex-col">
    <!-- Logo -->
    <div class="flex items-center gap-3 mb-10">
      <div class="w-10 h-10 rounded-xl bg-gradient-to-br from-primary to-accent flex items-center justify-center">
        <BookOpen class="w-5 h-5 text-white" />
      </div>
      <div>
        <h1 class="font-semibold text-foreground text-lg leading-tight">IP Scout</h1>
        <p class="text-xs text-muted-foreground">价值评估平台</p>
      </div>
    </div>

    <!-- Navigation -->
    <nav class="flex-1 space-y-2">
      <router-link
        v-for="(item, index) in menuItems"
        :key="item.url"
        :to="item.url"
        :class="[
          'group flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-200',
          isActive(item.url)
            ? 'bg-primary text-primary-foreground shadow-md'
            : 'hover:bg-secondary text-muted-foreground hover:text-foreground'
        ]"
        :style="{ animationDelay: `${index * 50}ms` }"
      >
        <component 
          :is="item.icon" 
          :class="[
            'w-5 h-5 transition-transform duration-200',
            !isActive(item.url) && 'group-hover:scale-110'
          ]"
        />
        <div class="flex flex-col">
          <span class="text-sm font-medium">{{ item.title }}</span>
          <span :class="[
            'text-xs',
            isActive(item.url) ? 'text-primary-foreground/70' : 'text-muted-foreground/60'
          ]">
            {{ item.titleEn }}
          </span>
        </div>
      </router-link>
    </nav>

    <!-- Footer -->
    <div class="pt-6 border-t border-border/50">
      <div class="glass-card rounded-xl p-4">
        <p class="text-xs text-muted-foreground mb-2">已分析 IP 数量</p>
        <p class="text-2xl font-semibold gradient-text">1,284</p>
      </div>
    </div>
  </aside>
</template>
