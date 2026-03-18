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
        const res = await axios.get(`${API_BASE}/charts/correlation`);
        const { dimensions, matrix } = res.data;

        // 转换数据为热力图格式
        const data: [number, number, number][] = [];
        for (let i = 0; i < matrix.length; i++) {
            for (let j = 0; j < matrix[i].length; j++) {
                data.push([j, i, parseFloat(matrix[i][j].toFixed(2))]);
            }
        }

        const option = {
            tooltip: {
                position: 'top',
                formatter: function(params: any) {
                    return `${dimensions[params.value[1]]} × ${dimensions[params.value[0]]}<br/>相关性: ${params.value[2]}`;
                }
            },
            grid: {
                left: '15%',
                right: '15%',
                top: '5%',
                bottom: '12%'
            },
            xAxis: {
                type: 'category',
                data: dimensions,
                splitArea: { show: true },
                axisLabel: {
                    fontSize: 9,
                    color: '#64748b',
                    interval: 0
                }
            },
            yAxis: {
                type: 'category',
                data: dimensions,
                splitArea: { show: true },
                axisLabel: {
                    fontSize: 10,
                    color: '#64748b'
                }
            },
            visualMap: {
                min: -1,
                max: 1,
                orient: 'vertical',
                right: 0,
                top: 'center',
                itemWidth: 6,
                itemHeight: 80,
                show: false,
                inRange: {
                    color: ['#f87171', '#fca5a5', '#fed7aa', '#fef3c7', '#dbeafe', '#93c5fd', '#3b82f6']
                }
            },
            series: [{
                name: '相关性',
                type: 'heatmap',
                data: data,
                label: {
                    show: true,
                    fontSize: 9,
                    color: '#374151'
                },
                emphasis: {
                    itemStyle: {
                        shadowBlur: 10,
                        shadowColor: 'rgba(0, 0, 0, 0.5)'
                    }
                }
            }]
        };

        chartInstance.setOption(option);
    } catch (e) {
        console.warn("[CorrelationHeatmap] Init fail:", e);
        // 显示空状态
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
