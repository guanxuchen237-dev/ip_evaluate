<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuth } from '@/composables/useAuth'
import { 
  LayoutDashboard,
  Users,
  Library,
  Globe,
  Database,
  Shield,
  Settings,
  BookOpen,
  Ban
} from 'lucide-vue-next'

interface MenuItem {
  title: string
  titleEn: string
  url: string
  icon: any
}

const route = useRoute()

const menuItems: MenuItem[] = [
  { title: "总览", titleEn: "Overview", url: "/admin?tab=overview", icon: LayoutDashboard },
  { title: "用户管理", titleEn: "Users", url: "/admin?tab=users", icon: Users },
  { title: "书籍管理", titleEn: "Books", url: "/admin?tab=books", icon: Library },
  { title: "黑名单", titleEn: "Blacklist", url: "/admin/blacklist", icon: Ban },
  { title: "平台监控", titleEn: "Platform", url: "/admin?tab=platform", icon: Globe },
  { title: "数据采集", titleEn: "Pipeline", url: "/admin?tab=monitor", icon: Database },
  { title: "智能审计", titleEn: "Audit", url: "/admin?tab=audit", icon: Shield },
  { title: "设置", titleEn: "Settings", url: "/admin?tab=settings", icon: Settings },
]

function isActive(url: string) {
  // 处理独立路由（如 /admin/blacklist）
  if (!url.includes('tab=')) {
    return route.path === url
  }
  // 如果当前在黑名单页面，不激活任何tab路由
  if (route.path === '/admin/blacklist') {
    return false
  }
  const tab = url.split('tab=')[1]
  return route.query.tab === tab || (!route.query.tab && tab === 'overview')
}
</script>

<template>
  <aside class="fixed left-0 top-0 w-64 h-screen bg-white/60 backdrop-blur-xl border-r border-white/40 p-6 flex flex-col overflow-hidden z-20">
    <!-- Logo -->
    <div class="flex items-center gap-3 mb-10">
      <div class="w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-500 flex items-center justify-center">
        <BookOpen class="w-5 h-5 text-white" />
      </div>
      <div>
        <h1 class="font-semibold text-foreground text-lg leading-tight">IP Scout</h1>
        <p class="text-xs text-muted-foreground">管理后台</p>
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
            ? 'bg-indigo-500 text-white shadow-md'
            : 'hover:bg-slate-100 text-slate-600 hover:text-slate-900'
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
            isActive(item.url) ? 'text-white/70' : 'text-slate-400'
          ]">
            {{ item.titleEn }}
          </span>
        </div>
      </router-link>
    </nav>
  </aside>
</template>
