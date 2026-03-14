<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from "vue";
import * as echarts from "echarts";
import axios from 'axios';

const chartRef = ref<HTMLElement | null>(null);
let chartInstance: echarts.ECharts | null = null;
const API_BASE = 'http://localhost:5000/api';

const initChart = async () => {
  if (!chartRef.value) return;
  
  chartInstance = echarts.init(chartRef.value);
  
  let indicators = [
    { name: '世界观 (World)', max: 100 },
    { name: '故事性 (Story)', max: 100 },
    { name: '角色 (Char)', max: 100 },
    { name: '商业性 (Biz)', max: 100 },
    { name: '创新 (Inno)', max: 100 },
  ];
  let dataValues = [80, 85, 90, 75, 70];

  try {
    const res = await axios.get(`${API_BASE}/charts/radar`);
    if (res.data && res.data.indicators && res.data.values) {
        indicators = res.data.indicators;
        dataValues = res.data.values;
    }
  } catch (e) {
    console.warn("Radar Fetch Fail, using mock", e);
  }

  const option = {
    radar: {
      indicator: indicators,
      radius: '65%',
      splitNumber: 4,
      axisName: {
        color: '#64748b', // Slate-500
        fontSize: 12
      },
      splitLine: {
        lineStyle: {
          color: '#e2e8f0' // Slate-200
        }
      },
      splitArea: {
        show: true,
        areaStyle: {
           color: ['#f8fafc', '#ffffff'] // Very subtle alternation
        }
      },
      axisLine: {
        lineStyle: {
          color: '#e2e8f0'
        }
      }
    },
    series: [
      {
        type: 'radar',
        data: [
          {
            value: dataValues,
            name: 'IP Dimension Analysis',
            symbol: 'circle',
            symbolSize: 6,
            itemStyle: { color: '#0ea5e9' }, // Sky-500
            lineStyle: {
              width: 2,
              color: '#0ea5e9' 
            },
            areaStyle: {
              color: '#0ea5e9',
              opacity: 0.2
            }
          }
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
