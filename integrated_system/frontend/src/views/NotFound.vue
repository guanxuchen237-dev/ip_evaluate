<script setup lang="ts">
import { useRouter } from 'vue-router'
import { Home } from 'lucide-vue-next'

const router = useRouter()
</script>

<template>
  <div class="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-50 to-slate-100">
    <div class="text-center">
      <div 
        v-motion
        :initial="{ scale: 0, rotate: -180 }"
        :enter="{ scale: 1, rotate: 0, transition: { type: 'spring', stiffness: 200 } }"
        class="w-24 h-24 rounded-3xl bg-gradient-to-br from-red-500/20 to-orange-500/20 flex items-center justify-center mx-auto mb-8"
      >
        <span class="text-6xl">🔍</span>
      </div>

      <h1 
        v-motion
        :initial="{ opacity: 0, y: 20 }"
        :enter="{ opacity: 1, y: 0, transition: { delay: 200 } }"
        class="text-7xl font-serif font-bold text-slate-800 mb-4"
      >
        404
      </h1>

      <p 
        v-motion
        :initial="{ opacity: 0, y: 20 }"
        :enter="{ opacity: 1, y: 0, transition: { delay: 300 } }"
        class="text-xl text-slate-600 mb-8"
      >
        页面未找到
      </p>

      <p 
        v-motion
        :initial="{ opacity: 0 }"
        :enter="{ opacity: 1, transition: { delay: 400 } }"
        class="text-sm text-slate-500 mb-8"
      >
        抱歉，您访问的页面不存在
      </p>

      <button 
        v-motion
        :initial="{ opacity: 0, y: 20 }"
        :enter="{ opacity: 1, y: 0, transition: { delay: 500 } }"
        @click="router.push('/')"
        class="inline-flex items-center gap-2 px-6 py-3 rounded-xl bg-slate-800 text-white hover:bg-slate-700 transition-all hover:scale-105"
      >
        <Home class="w-5 h-5" />
        <span>返回首页</span>
      </button>
    </div>
  </div>
</template>
