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
        const res = await axios.get(`${API_BASE}/charts/ip_score_distribution`);
        const { ranges, counts } = res.data;

        const option = {
            tooltip: {
                trigger: 'item',
                formatter: '{b}: {c} ({d}%)',
                confine: false,
                position: function (point: any, params: any, dom: any, rect: any, size: any) {
                    const obj: any = { top: 60 };
                    const side = +(point[0] < size.viewSize[0] / 2);
                    const positions = ['left', 'right'] as const;
                    obj[positions[side] ?? 'left'] = 10;
                    return obj;
                }
            },
            legend: {
                orient: 'vertical',
                right: '5%',
                top: 'center',
                itemWidth: 10,
                itemHeight: 10,
                textStyle: { fontSize: 10, color: '#64748b' }
            },
            series: [{
                type: 'pie',
                radius: ['40%', '70%'],
                center: ['40%', '50%'],
                avoidLabelOverlap: false,
                itemStyle: {
                    borderRadius: 6,
                    borderColor: '#fff',
                    borderWidth: 2
                },
                label: {
                    show: false,
                    position: 'center'
                },
                emphasis: {
                    label: {
                        show: true,
                        fontSize: 14,
                        fontWeight: 'bold'
                    }
                },
                labelLine: { show: false },
                data: ranges.map((range: string, index: number) => ({
                    name: range,
                    value: counts[index]
                })),
                color: [
                    '#f59e0b',  // S�?- 琥珀�?                    '#10b981',  // A�?- 翠绿�?                    '#3b82f6',  // B�?- 蓝色
                    '#6366f1',  // C�?- 靛蓝�?                    '#94a3b8'   // D�?- 灰色
                ]
            }]
        };

        chartInstance.setOption(option);
    } catch (e) {
        console.warn("[ScoreDistribution] Init fail:", e);
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
