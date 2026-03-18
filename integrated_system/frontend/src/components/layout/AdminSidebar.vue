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
  Cpu,
  Settings,
  BookOpen,
  LogOut,
  ArrowLeft
} from 'lucide-vue-next'

interface MenuItem {
  title: string
  titleEn: string
  url: string
  icon: any
}

const route = useRoute()
const router = useRouter()
const { user, logout } = useAuth()

const menuItems: MenuItem[] = [
  { title: "总览", titleEn: "Overview", url: "/admin?tab=overview", icon: LayoutDashboard },
  { title: "用户管理", titleEn: "Users", url: "/admin?tab=users", icon: Users },
  { title: "书籍管理", titleEn: "Books", url: "/admin?tab=books", icon: Library },
  { title: "平台监控", titleEn: "Platform", url: "/admin?tab=platform", icon: Globe },
  { title: "数据采集", titleEn: "Pipeline", url: "/admin?tab=monitor", icon: Database },
  { title: "智能审计", titleEn: "Audit", url: "/admin?tab=audit", icon: Shield },
  { title: "模型训练", titleEn: "Model", url: "/admin?tab=model", icon: Cpu },
  { title: "设置", titleEn: "Settings", url: "/admin?tab=settings", icon: Settings },
]

function isActive(url: string) {
  const tab = url.split('tab=')[1]
  return route.query.tab === tab || (!route.query.tab && tab === 'overview')
}

function goHome() {
  router.push('/')
}

function handleLogout() {
  logout()
  router.push('/login')
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

    <!-- Footer -->
    <div class="pt-6 border-t border-slate-200/50 space-y-3">
      <!-- 返回前台 -->
      <button 
        @click="goHome"
        class="w-full flex items-center gap-3 px-4 py-3 rounded-xl text-slate-600 hover:bg-slate-100 hover:text-slate-900 transition-colors"
      >
        <ArrowLeft class="w-5 h-5" />
        <span class="text-sm font-medium">返回前台</span>
      </button>
      
      <!-- 用户信息 -->
      <div class="flex items-center gap-3 px-4 py-3 bg-slate-50 rounded-xl">
        <div class="w-8 h-8 rounded-lg bg-indigo-100 flex items-center justify-center">
          <span class="text-xs font-bold text-indigo-600 uppercase">{{ user?.username?.charAt(0) || 'A' }}</span>
        </div>
        <div class="flex-1 min-w-0">
          <p class="text-sm font-medium text-slate-800 truncate">{{ user?.username || '管理员' }}</p>
          <p class="text-xs text-slate-400">管理员</p>
        </div>
        <button @click="handleLogout" class="p-1.5 rounded-lg hover:bg-slate-200 text-slate-400 hover:text-slate-600 transition-colors">
          <LogOut class="w-4 h-4" />
        </button>
      </div>
    </div>
  </aside>
</template>
