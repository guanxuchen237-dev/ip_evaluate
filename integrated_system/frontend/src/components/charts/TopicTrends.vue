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

    try {
        const res = await axios.get(`${API_BASE}/charts/topic_trends`);
        const { categories, qidian, zongheng } = res.data;

        const option = {
            tooltip: {
                trigger: 'axis',
                axisPointer: { type: 'shadow' }
            },
            legend: {
                data: ['起点中文网', '纵横中文网'],
                bottom: 0,
                itemWidth: 12,
                itemHeight: 12,
                textStyle: { fontSize: 10, color: '#64748b' }
            },
            grid: {
                left: '3%',
                right: '4%',
                bottom: '18%',
                top: '8%',
                containLabel: true
            },
            xAxis: {
                type: 'category',
                data: categories,
                axisLabel: {
                    fontSize: 10,
                    color: '#64748b',
                    rotate: 30
                },
                axisTick: { show: false }
            },
            yAxis: {
                type: 'value',
                axisLabel: { fontSize: 10, color: '#64748b' },
                splitLine: { lineStyle: { color: '#f1f5f9', type: 'dashed' } }
            },
            series: [
                {
                    name: '起点中文网',
                    type: 'bar',
                    data: qidian,
                    itemStyle: {
                        borderRadius: [3, 3, 0, 0],
                        color: '#6366f1'
                    },
                    barWidth: '35%'
                },
                {
                    name: '纵横中文网',
                    type: 'bar',
                    data: zongheng,
                    itemStyle: {
                        borderRadius: [3, 3, 0, 0],
                        color: '#3b82f6'
                    },
                    barWidth: '35%'
                }
            ]
        };

        chartInstance.setOption(option);
    } catch (e) {
        console.warn("[TopicTrends] Init fail:", e);
        chartInstance.setOption({
            title: {
                text: '暂无数据',
                left: 'center',
                top: 'center',
                textStyle: { color: '#94a3b8', fontSize: 14 }
            }
        });
    }
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
