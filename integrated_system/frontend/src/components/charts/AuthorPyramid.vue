<script setup lang="ts">
import { ref, onMounted, onUnmounted } from "vue";
import * as echarts from "echarts";
import axios from 'axios';

const chartRef = ref<HTMLElement | null>(null);
let chartInstance: echarts.ECharts | null = null;
const API_BASE = 'http://localhost:5000/api';

const initChart = async () => {
  if (!chartRef.value) return;
  
  chartInstance = echarts.init(chartRef.value);
  
  let data = [
    { value: 20, name: '白金大神' },
    { value: 40, name: '签约作家' },
    { value: 60, name: '潜力新锐' },
    { value: 100, name: '驻站作者' }
  ];

  try {
    const res = await axios.get(`${API_BASE}/charts/author_tiers`);
    if (res.data && Array.isArray(res.data)) {
        data = res.data;
    }
  } catch (e) {
    console.warn("Author Tiers Fetch Fail", e);
  }

  const option = {
    color: ['#0f172a', '#334155', '#475569', '#94a3b8'], // Slate Scale using user's preferred vibe or blue?
    // User wants "Trend and Color optimization". Professional usually means Blue scale.
    // Let's use a nice Indigo/Blue scale.
    // Top (Smallest) -> Bottom (Largest)
    // Tiers: Platinum (Top) -> Signed -> Potential -> Station (Bottom)
    
    tooltip: {
      trigger: 'item',
      formatter: "{b} : {c}%"
    },
    series: [
      {
        name: 'Author Pyramid',
        type: 'funnel',
        left: '10%',
        top: '10%',
        bottom: '10%',
        width: '60%', // Reduce width to make room for labels
        sort: 'ascending',
        gap: 2,
        label: {
          show: true,
          position: 'right',
          color: '#475569', // Slate-600
          formatter: ' {b}\n {c}%',
          align: 'left'
        },
        labelLine: {
          show: true,
          length: 10,
          lineStyle: {
            color: '#cbd5e1'
          }
        },
        itemStyle: {
            borderColor: '#fff',
            borderWidth: 1
        },
        data: [
            // Re-map colors to data items if needed, or rely on color list. 
            // Funnel usually uses color list cyclically. 
            // We want Top to be most intense?
            { value: 20, name: '白金大神', itemStyle: { color: '#4f46e5' } }, // Indigo-600
            { value: 40, name: '签约作家', itemStyle: { color: '#6366f1' } }, // Indigo-500
            { value: 60, name: '潜力新锐', itemStyle: { color: '#818cf8' } }, // Indigo-400
            { value: 100, name: '驻站作者', itemStyle: { color: '#a5b4fc' } }  // Indigo-300
        ]
      }
    ]
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
