<script setup lang="ts">
import EditorialLayout from "@/components/layout/EditorialLayout.vue";
import PredictionPanel from "@/components/dashboard/PredictionPanel.vue";
import { ArrowLeft } from "lucide-vue-next";
import { useRouter } from "vue-router";

const router = useRouter();
</script>

<template>
  <EditorialLayout :showDock="true">
    <div class="min-h-screen p-8 text-slate-900 relative z-10 flex flex-col items-center justify-center">
      <div class="w-full max-w-5xl">
        <button 
          @click="router.push('/')"
          class="flex items-center gap-2 text-slate-500 hover:text-slate-900 mb-6 transition-colors"
        >
          <ArrowLeft class="w-4 h-4" /> 返回大屏
        </button>
        
        <div class="bg-white/80 backdrop-blur-xl border border-slate-200 rounded-3xl shadow-2xl overflow-hidden min-h-[600px] p-8">
          <h1 class="font-serif text-3xl font-bold text-center mb-8 text-slate-900">
             小说IP价值预测系统
          </h1>
          <PredictionPanel />
        </div>
      </div>
    </div>
  </EditorialLayout>
</template>
