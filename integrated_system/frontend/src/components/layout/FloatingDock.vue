<script setup lang="ts">
import { RouterLink, useRoute, useRouter } from 'vue-router'
import {
  LayoutDashboard,
  FileSearch,
  Sparkles,
  Megaphone,
  Network,
  Glasses,
  Activity,
  Users,
  Database,
  Brain,
  Library,
  Crown,
  Settings,
  User,
  LogOut,
  ChevronUp
} from "lucide-vue-next";
import { ref, computed } from "vue";
import { useAuth } from '@/composables/useAuth'

const props = defineProps<{
  items?: Array<{ title: string; titleEn: string; url: string; icon: any; isVip?: boolean }>
}>();

const route = useRoute();
const router = useRouter();
const hoveredItem = ref<string | null>(null);
const showUserMenu = ref(false);

const { user, isAdmin, logout, isLoggedIn } = useAuth();

interface MenuItem {
  title: string;
  titleEn: string;
  url: string;
  icon: any;
  isVip?: boolean;
}

// 用户端功能 — 所有用户可见
const userMenuItems: MenuItem[] = [
  { title: "仪表盘", titleEn: "Dashboard", url: "/", icon: LayoutDashboard },
  { title: "AI预测", titleEn: "Prediction", url: "/prediction", icon: Brain },
  { title: "作品库", titleEn: "Library", url: "/library", icon: Library },
  { title: "虚拟读者", titleEn: "Reader Space", url: "/reader-space", icon: Users },
];

// 根据角色合并菜单，或者使用传入的自定义菜单
const menuItems = computed<MenuItem[]>(() => {
  if (props.items && props.items.length > 0) {
    return props.items as MenuItem[];
  }
  return userMenuItems
})

function goToAdmin() {
  showUserMenu.value = false
  router.push('/admin')
}

function goToHome() {
  showUserMenu.value = false
  router.push('/')
}

function handleLogout() {
  showUserMenu.value = false
  logout()
  router.push('/login')
}

function goToProfile() {
  showUserMenu.value = false
  router.push('/profile')
}
</script>

<template>
  <nav class="fixed bottom-6 left-1/2 -translate-x-1/2 z-50">
    <div class="flex items-center gap-1.5 px-3 py-2.5 bg-white/80 backdrop-blur-2xl rounded-2xl border border-white/40 shadow-2xl shadow-black/5">
      <!-- 导航图标 -->
      <template v-for="item in menuItems" :key="item.url">
        <RouterLink
          :to="item.url"
          custom
          v-slot="{ isActive, isExactActive, href, navigate }"
        >
          <a
            :href="href"
            @click.prevent="() => {
               // 如果是未登录访问受限路由，拦截并跳转
               if (!isLoggedIn && item.url !== '/' && item.url !== '/library') {
                 router.push('/login')
               } else {
                 navigate()
               }
            }"
            @mouseenter="hoveredItem = item.url"
            @mouseleave="hoveredItem = null"
            class="relative flex flex-col items-center justify-center px-3 py-1.5 rounded-xl transition-all duration-300"
            :class="[
              (item.url === '/' ? isExactActive : isActive) 
                ? (item.isVip 
                  ? 'bg-gradient-to-br from-amber-400 via-yellow-500 to-orange-500 text-white scale-110' 
                  : 'bg-slate-700 text-white scale-110') 
                : (item.isVip
                  ? 'text-amber-600 hover:text-amber-700 hover:bg-amber-50'
                  : 'text-slate-500 hover:text-slate-800 hover:bg-slate-100')
            ]"
          >
            <component 
              :is="item.icon" 
              class="w-[18px] h-[18px] transition-transform duration-300" 
              :class="[hoveredItem === item.url && !isActive ? 'scale-125' : '']"
            />
            
            <!-- VIP Badge -->
            <span v-if="item.isVip && !isActive" class="absolute -top-1 -right-1 w-3.5 h-3.5 bg-gradient-to-br from-amber-400 to-orange-500 rounded-full flex items-center justify-center">
              <span class="text-[7px] text-white font-bold">V</span>
            </span>
            
            <!-- Tooltip -->
            <div 
              class="absolute -top-12 left-1/2 -translate-x-1/2 px-2.5 py-1 rounded-lg text-white text-[11px] whitespace-nowrap transition-all duration-200 shadow-xl"
              :class="[
                item.isVip ? 'bg-gradient-to-r from-amber-500 to-orange-500' : 'bg-slate-800',
                hoveredItem === item.url ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-2 pointer-events-none'
              ]"
            >
              <span class="font-medium">{{ item.title }}</span>
              <div 
                class="absolute -bottom-1 left-1/2 -translate-x-1/2 w-2 h-2 rotate-45"
                :class="[item.isVip ? 'bg-orange-500' : 'bg-slate-800']"
              />
            </div>
          </a>
        </RouterLink>
      </template>

      <!-- 分割线 -->
      <div class="w-px h-6 bg-slate-200 mx-1" />

      <!-- 用户/登录 区域 -->
      <div class="relative">
        <!-- 已登录状态按钮 -->
        <button
          v-if="isLoggedIn"
          @click="showUserMenu = !showUserMenu"
          @mouseenter="hoveredItem = 'user'"
          @mouseleave="hoveredItem = null"
          class="flex items-center justify-center w-9 h-9 rounded-xl transition-all duration-300"
          :class="showUserMenu ? 'bg-slate-700 text-white' : 'bg-emerald-50 text-emerald-700 hover:bg-emerald-100'"
        >
          <span v-if="user?.username" class="text-xs font-bold uppercase">{{ user.username.charAt(0) }}</span>
          <User v-else class="w-4 h-4" />
        </button>

        <!-- 游客模式登录按钮 -->
        <button
          v-else
          @click="router.push('/login')"
          class="flex items-center gap-2 px-4 py-1.5 bg-indigo-600 text-white rounded-xl text-sm font-bold shadow-lg shadow-indigo-500/20 hover:bg-indigo-700 transition-all hover:scale-105"
        >
          <User class="w-4 h-4" />
          登录
        </button>

        <!-- 用户弹出菜单 -->
        <Transition name="pop">
          <div
            v-if="showUserMenu && isLoggedIn"
            class="absolute bottom-full right-0 mb-3 w-52 bg-white/90 backdrop-blur-2xl rounded-2xl border border-white/50 shadow-2xl shadow-black/10 overflow-hidden"
          >
            <!-- 用户信息 -->
            <div class="px-4 py-3 border-b border-slate-100">
              <p class="text-sm font-semibold text-slate-800">{{ user?.username || '用户' }}</p>
              <p class="text-[11px] text-slate-400 mt-0.5">{{ user?.email || '' }}</p>
              <span
                class="inline-block mt-1.5 px-2 py-0.5 rounded-full text-[10px] font-medium"
                :class="isAdmin ? 'bg-amber-50 text-amber-600 border border-amber-200' : 'bg-emerald-50 text-emerald-600 border border-emerald-200'"
              >
                {{ isAdmin ? '管理员' : '普通用户' }}
              </span>
            </div>

            <div class="py-1.5">
              <button
                v-if="isAdmin && !route.path.startsWith('/admin')"
                @click="goToAdmin"
                class="w-full flex items-center gap-2.5 px-4 py-2 text-sm text-indigo-600 hover:bg-indigo-50 hover:text-indigo-800 transition-colors"
              >
                <LayoutDashboard class="w-4 h-4" />
                进入管理后台
              </button>
              <button
                v-if="isAdmin && route.path.startsWith('/admin')"
                @click="goToHome"
                class="w-full flex items-center gap-2.5 px-4 py-2 text-sm text-emerald-600 hover:bg-emerald-50 hover:text-emerald-800 transition-colors"
              >
                <LayoutDashboard class="w-4 h-4" />
                返回前台大厅
              </button>
              <button
                @click="goToProfile"
                class="w-full flex items-center gap-2.5 px-4 py-2 text-sm text-slate-600 hover:bg-slate-50 hover:text-slate-800 transition-colors"
              >
                <User class="w-4 h-4 text-slate-400" />
                个人设置
              </button>
              <button
                @click="handleLogout"
                class="w-full flex items-center gap-2.5 px-4 py-2 text-sm text-red-500 hover:bg-red-50 hover:text-red-600 transition-colors"
              >
                <LogOut class="w-4 h-4" />
                退出登录
              </button>
            </div>
          </div>
        </Transition>
      </div>
    </div>

    <!-- 点击外部关闭菜单 -->
    <div v-if="showUserMenu" class="fixed inset-0 z-[-1]" @click="showUserMenu = false" />
  </nav>
</template>

<style scoped>
.pop-enter-active {
  transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
}
.pop-leave-active {
  transition: all 0.15s ease-in;
}
.pop-enter-from {
  opacity: 0;
  transform: translateY(8px) scale(0.95);
}
.pop-leave-to {
  opacity: 0;
  transform: translateY(4px) scale(0.98);
}
</style>
