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
        const res = await axios.get(`${API_BASE}/charts/keyword_frequency`);
        const { keywords, values } = res.data;

        const option = {
            tooltip: {
                trigger: 'axis',
                axisPointer: { type: 'shadow' },
                formatter: '{b}: {c} �?
            },
            grid: {
                left: '3%',
                right: '4%',
                bottom: '3%',
                top: '3%',
                containLabel: true
            },
            xAxis: {
                type: 'value',
                axisLabel: { fontSize: 10, color: '#64748b' },
                splitLine: { lineStyle: { color: '#f1f5f9', type: 'dashed' } }
            },
            yAxis: {
                type: 'category',
                data: keywords.slice().reverse(),
                axisLabel: { fontSize: 11, color: '#475569' },
                axisTick: { show: false },
                axisLine: { show: false }
            },
            series: [{
                type: 'bar',
                data: values.slice().reverse(),
                itemStyle: {
                    borderRadius: [0, 4, 4, 0],
                    color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
                        { offset: 0, color: '#6366f1' },
                        { offset: 1, color: '#8b5cf6' }
                    ])
                },
                barWidth: '60%',
                label: {
                    show: true,
                    position: 'right',
                    fontSize: 10,
                    color: '#64748b'
                }
            }]
        };

        chartInstance.setOption(option);
    } catch (e) {
        console.warn("[KeywordFrequency] Init fail:", e);
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
