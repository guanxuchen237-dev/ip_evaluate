<template>
  <el-config-provider :locale="locale">
    <div class="app-container">
      <router-view />
    </div>
  </el-config-provider>
</template>

<script setup>
import { ElConfigProvider } from 'element-plus'
import zhCn from 'element-plus/dist/locale/zh-cn.mjs'
const locale = zhCn
</script>

<style>
/* No extra styles needed here, handled by global css */
</style>
