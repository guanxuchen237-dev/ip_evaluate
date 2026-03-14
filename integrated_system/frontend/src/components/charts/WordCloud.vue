<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue';
import * as echarts from 'echarts';
import 'echarts-wordcloud';
import axios from 'axios';

const chartRef = ref<HTMLElement | null>(null);
let chartInstance: echarts.ECharts | null = null;
const API_BASE = 'http://localhost:5000/api';

// Neon Color Palette
const colors = ['#06b6d4', '#3b82f6', '#8b5cf6', '#d946ef', '#ec4899', '#f43f5e', '#22d3ee', '#a855f7'];

const initChart = async () => {
  if (!chartRef.value) return;
  chartInstance = echarts.init(chartRef.value);

  let data = [
    { name: '烟斗老哥', value: 100 },
    { name: '知白', value: 95 },
    { name: '言归正传', value: 90 },
    { name: '远瞳', value: 85 },
    { name: '黑山老鬼', value: 80 },
    { name: '奕辰辰', value: 75 },
    { name: '滚开', value: 70 },
    { name: '步履无声', value: 65 },
    { name: '火中物', value: 60 },
    { name: '一叶青天', value: 55 },
    { name: '海棠灯', value: 50 },
    { name: '李闲鱼', value: 45 },
    { name: '如水意', value: 40 },
    { name: '子与2', value: 35 },
    { name: '姬叉', value: 30 },
  ];

  try {
    const res = await axios.get(`${API_BASE}/charts/wordcloud`);
    if (Array.isArray(res.data) && res.data.length > 0) {
      data = res.data.slice(0, 30).map((item: any) => ({
        name: item.name || item.word,
        value: item.value || item.count || 50
      }));
    }
  } catch (e) {
    console.warn("WordCloud Fetch Fail", e);
  }

  const option = {
    backgroundColor: 'transparent',
    series: [{
      type: 'wordCloud',
      shape: 'circle',
      left: 'center',
      top: 'center',
      width: '90%',
      height: '90%',
      sizeRange: [14, 55],
      rotationRange: [-45, 45],
      rotationStep: 15,
      gridSize: 8,
      drawOutOfBound: false,
      layoutAnimation: true,
      textStyle: {
        fontFamily: 'sans-serif',
        fontWeight: 'bold',
        color: () => colors[Math.floor(Math.random() * colors.length)]
      },
      emphasis: {
        focus: 'self',
        textStyle: {
          textShadowBlur: 10,
          textShadowColor: '#fff'
        }
      },
      data: data
    }]
  };

  chartInstance.setOption(option);
};

onMounted(() => {
  initChart();
  window.addEventListener("resize", () => chartInstance?.resize());
});

onUnmounted(() => {
  window.removeEventListener("resize", () => chartInstance?.resize());
  chartInstance?.dispose();
});
</script>

<template>
  <div ref="chartRef" class="w-full h-full" />
</template>
