<script setup lang="ts">
import { ref, onMounted, onUnmounted } from "vue";
import * as echarts from "echarts";
import axios from 'axios';
// @ts-ignore
import chinaJson from "@/assets/china.json";

const chartRef = ref<HTMLElement | null>(null);
let chartInstance: echarts.ECharts | null = null;
const API_BASE = 'http://localhost:5000/api';

const initChart = async () => {
  if (!chartRef.value) return;
  chartInstance = echarts.init(chartRef.value);

  // 注册中国地图
  echarts.registerMap('china', chinaJson as any);

  // 获取真实地理数据
  let geoData: { name: string; value: number }[] = [];
  const validNames = (chinaJson.features || []).map((f: any) => f.properties.name).filter((n: any) => n);

  try {
    const res = await axios.get(`${API_BASE}/charts/geo_region`);
    if (res.data && Array.isArray(res.data)) {
      geoData = res.data
        .filter((d: any) => d.name && d.name !== '属地未知' && d.name !== '中国' && d.name !== '未知')
        .map((d: any) => {
          let cleanName = d.name.replace(/省$|市$|特别行政区$|自治区$|维吾尔|壮族|回族/g, '');
          let fullName = validNames.find((vn: string) => vn.startsWith(cleanName)) || d.name;
          return { name: fullName, value: d.value };
        });
    }
  } catch (e) {
    console.warn("Geo Fetch Fail", e);
  }

  const maxVal = geoData.length > 0 ? Math.max(...geoData.map(d => d.value)) : 1000;

  const option: echarts.EChartsOption = {
    tooltip: {
      trigger: 'item',
      backgroundColor: 'rgba(255,255,255,0.95)',
      borderColor: '#e2e8f0',
      textStyle: { color: '#334155', fontSize: 13 },
      formatter: (params: any) => {
        return `<b>${params.name}</b><br/>读者评论: ${(params.value || 0).toLocaleString()} 条`;
      }
    },
    visualMap: {
      min: 0,
      max: maxVal,
      left: '3%',
      bottom: '5%',
      text: ['高', '低'],
      textStyle: { color: '#94a3b8', fontSize: 11 },
      inRange: {
        color: ['#e0f2fe', '#7dd3fc', '#38bdf8', '#0284c7', '#0369a1']
      },
      itemWidth: 12,
      itemHeight: 80
    },
    series: [{
      name: '读者分布',
      type: 'map',
      map: 'china',
      roam: false,
      zoom: 1.6,
      center: [104, 35],
      label: {
        show: false
      },
      emphasis: {
        label: {
          show: true,
          color: '#1e293b',
          fontSize: 12,
          fontWeight: 'bold',
          formatter: (params: any) => {
             if (params.value) {
                return `${params.name}: ${params.value} 条`;
             }
             return params.name;
          }
        },
        itemStyle: {
          areaColor: '#6366f1',
          shadowBlur: 10,
          shadowColor: 'rgba(99, 102, 241, 0.3)'
        }
      },
      itemStyle: {
        areaColor: '#f1f5f9',
        borderColor: '#cbd5e1',
        borderWidth: 0.5
      },
      data: geoData
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
