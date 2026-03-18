<script setup lang="ts">
import { onMounted } from 'vue'
import { useAuth } from '@/composables/useAuth'
import Toast from '@/components/common/Toast.vue'

const { fetchUser } = useAuth()

// 应用启动时恢复登录状态
onMounted(() => {
  fetchUser()
})
</script>

<template>
  <div class="min-h-screen bg-background font-sans antialiased">
    <router-view />
    <Toast />
  </div>
</template>
