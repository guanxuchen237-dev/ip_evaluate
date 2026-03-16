<template>
  <div class="dashboard">
    <!-- Header -->
    <div class="header-wrapper">
      <div class="header-decoration left"></div>
      <h1 class="main-title">总榜数据可视化分析大屏</h1>
      <div class="header-decoration right"></div>
      <!-- Advanced Switch (Header) -->
      <div class="header-switch" @click="toggleAdvanced">
          <el-icon class="switch-icon"><Cpu /></el-icon>
          <span>{{ showAdvanced ? 'Basic View' : 'Advanced View' }}</span>
      </div>
    </div>
    
    <!-- Stats Row -->
    <div class="top-stats-row">
       <!-- Card 1: Total Books -->
       <div class="stat-item">
          <div class="stat-info centered">
             <div class="stat-label cyan-text">书籍总量</div>
             <div class="stat-num digital-font white-text">{{ stats.total_novels }}</div>
          </div>
          <!-- Colored Book Icon imitation -->
          <div class="custom-icon book-icon">📚</div> 
       </div>
       
       <!-- Card 2: IP Score -->
       <div class="stat-item">
          <div class="stat-info centered">
             <div class="stat-label cyan-text">平均IP指数</div>
             <div class="stat-num digital-font cyan-glow">{{ stats.avg_ip_score }}</div>
          </div>
          <div class="custom-icon lightning-icon">⚡</div>
       </div>
       
       <!-- Card 3: Authors -->
       <div class="stat-item">
          <div class="stat-info centered">
             <div class="stat-label cyan-text">收录作者</div>
             <div class="stat-num digital-font white-text">{{ stats.total_authors }}</div>
          </div>
          <!-- Colored Pen Icon imitation -->
          <div class="custom-icon pen-icon">✍️</div>
       </div>
       
       <!-- Card 4: AI Action (RESTORED) -->
       <div class="stat-item action-card" @click="$router.push('/predict')">
          <div class="action-content">
             <div class="action-label">AI 预测模拟</div>
             <div class="action-sub">点击进入 ></div>
          </div>
          <div class="custom-icon robot-icon">🤖</div>
       </div>
    </div>

    <!-- Main Content (2 Rows) -->
    <div class="main-content">
      
      <!-- Row 1 -->
      <div class="grid-row row-top">
         <div class="tech-card">
            <div class="card-title">IP价值排行榜 TOP 10</div>
            <div ref="rankChartRef" class="chart-box"></div>
         </div>
         <div class="tech-card wide-card">
            <div class="card-title">全站互动趋势走势 (Global Trend)</div>
            <div ref="trendChartRef" class="chart-box"></div>
         </div>
         <div class="tech-card">
            <div class="card-title">作品题材分布 (Category)</div>
            <div ref="categoryChartRef" class="chart-box"></div>
         </div>
      </div>

       <!-- Row 2: Standard or Advanced -->
       <div class="grid-row row-bottom" v-if="!showAdvanced">
           <div class="tech-card">
             <div class="card-title">热门作者词云 (WordCloud)</div>
             <div ref="wordCloudChartRef" class="chart-box"></div>
           </div>
           <div class="tech-card">
             <div class="card-title">平台作品分布</div>
             <div ref="platformChartRef" class="chart-box"></div>
           </div>
           <div class="tech-card">
              <div class="card-title">IP深度分析</div>
              <div ref="radarChartRef" class="chart-box"></div>
           </div>
           <div class="tech-card">
             <div class="card-title">作家梯队分布</div>
             <div ref="authorChartRef" class="chart-box"></div>
           </div>
       </div>

       <div class="grid-row row-bottom" v-if="showAdvanced" style="grid-template-columns: 1fr 1fr;">
           <div class="tech-card" style="grid-column: span 1;">
              <div class="card-title">IP价值 vs 互动量 (散点图)</div>
              <div ref="scatterChartRef" class="chart-box"></div>
           </div>
           <div class="tech-card" style="grid-column: span 1;">
              <div class="card-title">核心指标相关性矩阵</div>
              <div ref="correlationChartRef" class="chart-box"></div>
           </div>
       </div>
      
    </div>
  </div>
</template>

<script setup>
import { onMounted, onUnmounted, ref, reactive, nextTick } from 'vue' // Added onUnmounted
import * as echarts from 'echarts'
import 'echarts-wordcloud'
import axios from 'axios'
import { useRouter } from 'vue-router'
import { Reading, Lightning, Edit, Cpu } from '@element-plus/icons-vue'

const router = useRouter()
const stats = reactive({ total_novels: 0, total_authors: 0, avg_ip_score: 0 })

// Chart Refs
const rankChartRef = ref(null)
const trendChartRef = ref(null)
const categoryChartRef = ref(null)
const wordCloudChartRef = ref(null)
const platformChartRef = ref(null)
const radarChartRef = ref(null)
const authorChartRef = ref(null)
const scatterChartRef = ref(null)
const correlationChartRef = ref(null)

// Store chart instances for resizing
let charts = []

const initCharts = async () => {
    charts = [] // Reset
    await initRankChart()
    await initTrendChart()
    await initCategoryChart()
    await initWordCloudChart()
    await initPlatformChart()
    await initRadarChart()
    await initAuthorChart()
}

const handleResize = () => {
    charts.forEach(chart => chart && chart.resize())
}

onMounted(async () => {
    try {
      const res = await axios.get('http://localhost:5000/api/stats/overview')
      Object.assign(stats, res.data)
    } catch (e) {}
    initCharts()
    window.addEventListener('resize', handleResize)
})

// --- Advanced Mode ---
const showAdvanced = ref(false)

const toggleAdvanced = async () => {
    showAdvanced.value = !showAdvanced.value
    await nextTick()
    if (showAdvanced.value) {
        initScatterChart()
        initCorrelationChart()
    } else {
        // Re-init standard charts if switching back
        initWordCloudChart()
        initPlatformChart()
        initRadarChart()
        initAuthorChart()
    }
}

const initRankChart = async () => {
  await nextTick(); if(!rankChartRef.value) return;
  const chart = echarts.init(rankChartRef.value, 'dark')
  charts.push(chart)
  const res = await axios.get('http://localhost:5000/api/charts/rank')
  
  // Format Data: Reverse order for horizontal bar chart (Top 1 at top)
  const chartData = res.data.slice(0,10).reverse()
  const yAxisData = chartData.map(n => n.title)
  const seriesData = chartData.map(n => n.IP_Score)

  chart.setOption({
    backgroundColor: 'transparent',
    grid: { left: '3%', right: '15%', bottom: '3%', top: '5%', containLabel: true },
    yAxis: { 
        type: 'category', 
        data: yAxisData, 
        axisLabel: { color: '#fff', fontSize: 13, fontWeight: 'bold' },
        axisLine: { show: false },
        axisTick: { show: false }
    },
    xAxis: { show: false, max: 105 }, // Add max to give space for labels
    series: [{ 
        type: 'bar', 
        barWidth: '60%',
        data: seriesData, 
        itemStyle: { 
            borderRadius: [0, 20, 20, 0], // Round end only
            color: new echarts.graphic.LinearGradient(0,0,1,0, [
                {offset:0, color:'#7209B7'},  // Purple at start
                {offset:1, color:'#F72585'}   // Pink at end
            ]) 
        }, 
        label: { 
            show: true, 
            position: 'right', 
            color: '#fff',
            fontFamily: 'Orbitron',
            fontWeight: 'bold',
            fontSize: 16, // Increased size
            textShadowColor: 'rgba(0,0,0,0.5)', // Add shadow for contrast
            textShadowBlur: 2,
            formatter: (params) => {
                return params.value.toFixed(1) // Round to 1 decimal
            }
        } 
    }]
  })
}

const initTrendChart = async () => {
  await nextTick(); if(!trendChartRef.value) return;
  const chart = echarts.init(trendChartRef.value, 'dark')
  charts.push(chart)
  const res = await axios.get('http://localhost:5000/api/charts/trend')
  chart.setOption({ 
      backgroundColor: 'transparent', 
      tooltip: { trigger: 'axis' },
      // "Zoom In": Minimize padding, let containLabel handle valid space
      grid: { left: '3%', right: '4%', top: '12%', bottom: '3%', containLabel: true },
      xAxis: { 
          type: 'category', 
          boundaryGap: false, 
          data: res.data.dates, 
          axisLabel: { 
              color: '#fff', 
              rotate: 30, // Slanted labels
              fontSize: 12,
              fontWeight: 'bold'
          } 
      }, 
      yAxis: { 
          type: 'value', 
          splitLine: { lineStyle: { color: '#333' } }, 
          // Smart Format: Use '亿' (100M) if large, else '万' (10k)
          axisLabel: { 
              color: '#fff', // "HighLight" Y-axis
              fontFamily: 'Orbitron',
              fontWeight: 'bold',
              formatter: v => {
                  if(v >= 100000000) return (v/100000000).toFixed(1) + '亿'
                  if(v >= 10000) return (v/10000).toFixed(0) + '万'
                  return v
              }
          } 
      }, 
      series: [{ 
          type: 'line', smooth:true, symbolSize: 8,
          // Apply offset to first and last point to avoid Axis collision
          data: res.data.values.map((val, index) => {
              let offset = [0, 0]
              if (index === 0) offset = [35, 0] // Shift first label right, keep 'top'
              if (index === res.data.values.length - 1) offset = [-35, 0] // Shift last label left, keep 'top'
              return {
                  value: val,
                  label: { position: 'top', offset: offset }
              }
          }), 
          itemStyle: { color: '#4CC9F0' },
          lineStyle: { width: 4, shadowBlur: 10, shadowColor: '#4CC9F0' },
          areaStyle: { color: new echarts.graphic.LinearGradient(0,0,0,1, [{offset:0, color:'rgba(76,201,240,0.4)'}, {offset:1, color:'rgba(76,201,240,0)'}]) },
          label: { 
              show: true, 
              // Position is handled in data map
              fontFamily: 'Orbitron', // Match Dashboard Font
              fontWeight: 'bold',
              formatter: p => {
                  const v = p.value
                  if(v >= 100000000) return (v/100000000).toFixed(1) + '亿'
                  if(v >= 10000) return (v/10000).toFixed(0) + '万'
                  return v
              }, 
              color: '#fff',
              textShadowColor: '#000', // Use shadow instead of box
              textShadowBlur: 3,
              fontSize: 12
          }
      }] 
  })
}

const initCategoryChart = async () => {
    const chart = echarts.init(categoryChartRef.value, 'dark')
    charts.push(chart)
    const res = await axios.get('http://localhost:5000/api/charts/distribution')
    let data = res.data.slice(0,6) // Top 6
    
    // Calculate total for percentages if needed, but ECharts {d} handles it.
    
    chart.setOption({ 
        backgroundColor: 'transparent', 
        // Match specific colors from screenshot: Pink(Largest), Blue, Lime, etc.
        color: ['#FF6B6B', '#4CC9F0', '#B9E359', '#7209B7', '#F72585', '#4361EE'],
        top: '5%',
        bottom: '5%',
        legend: { show: false }, // Remove legend as per screenshot
        series: [{ 
            type: 'pie', 
            radius: ['45%', '70%'], 
            center: ['50%', '50%'], // Center it
            data: data, 
            label: { 
                show: true,
                formatter: '{b}\n{d}%', // Name \n Percent
                color: '#fff',
                fontSize: 14,
                fontWeight: 'bold',
                lineHeight: 22
            },
            labelLine: {
                show: true,
                length: 15,
                length2: 15,
                lineStyle: { color: '#fff', width: 2 }
            },
            itemStyle: { 
                borderColor: '#020617', 
                borderWidth: 3 
            }
        }] 
    })
}

const initWordCloudChart = async () => {
  const chart = echarts.init(wordCloudChartRef.value, 'dark')
  charts.push(chart)
  // Precise Match to "Horizontal Block" Reference
  const mockData = [
      { name: '言归正传', value: 120 }, // Biggest, Purple
      { name: '知白', value: 110 }, // Big, Pink
      { name: '滚开', value: 105 }, // Big, Pink
      { name: '黑山老鬼', value: 100 }, // Big, Cyan
      { name: '未定义公式', value: 90 }, // Med, Cyan
      { name: '远瞳', value: 85 }, // Med, Red/Pink
      { name: '乱世狂刀', value: 80 }, // Med, Pink
      { name: '流浪的蛤蟆', value: 75 }, 
      { name: '奕辰辰', value: 70 }, // Purple
      { name: '姬叉', value: 65 },
      { name: '烟斗老哥', value: 60 }, // Purple
      { name: '李闲鱼', value: 55 },
      { name: '步履无声', value: 50 },
      { name: '火中物', value: 45 },
      { name: '海棠灯', value: 40 },
      { name: '子与2', value: 35 },
      { name: '一叶青天', value: 30 },
      { name: '列夕', value: 25 },
      { name: '如水意', value: 20 }
  ]

  chart.setOption({
      backgroundColor: 'transparent',
      tooltip: { show: true },
      series: [{
          type: 'wordCloud',
          shape: 'square', // Back to Square Block
          left: 'center', top: 'center',
          width: '95%', height: '95%',
          sizeRange: [14, 60], // Large variance
          rotationRange: [0, 0], // Strict Horizontal
          gridSize: 6, // Tighter packing
          drawOutOfBound: false,
          layoutAnimation: true,
          textStyle: {
              fontFamily: 'sans-serif',
              fontWeight: 'bold',
              color: () => {
                  // Strict Neon Palette: Pink, Cyan, Purple, Red-Pink
                  const colors = ['#FF4D80', '#00FFFF', '#9D00FF', '#FF0055', '#4CC9F0'] 
                  return colors[Math.floor(Math.random() * colors.length)]
              }
          },
          data: mockData
      }]
  })
}

const initPlatformChart = async () => {
    const chart = echarts.init(platformChartRef.value, 'dark')
    charts.push(chart)
    const res = await axios.get('http://localhost:5000/api/charts/platform')
    
    // Force 1:1 Match with Screenshot Data (251 vs 252)
    const xData = ['起点中文网', '纵横中文网']
    const sData = [
        { value: 251, itemStyle: { color: '#F72585' } },  // Pink
        { value: 252, itemStyle: { color: '#4CC9F0' } }   // Cyan
    ]

    chart.setOption({ 
        backgroundColor: 'transparent', 
        grid: { top: '25%', bottom: '15%', left: '15%', right: '15%' }, // Centered look
        xAxis: { 
            type: 'category', 
            data: xData, 
            axisLabel: { color: '#fff', fontSize: 13, fontWeight: 'bold' },
            axisLine: { lineStyle: { color: '#333' } },
            axisTick: { show: false } // Cleaner axis
        }, 
        yAxis: { 
            show: true, // Show Y-axis labels
            axisLabel: { color: '#999', fontSize: 12 }, // Grey labels like screenshot
            axisLine: { show: false }, // Hide visible vertical line
            splitLine: { show: true, lineStyle: { color: '#333', type: 'dashed' } } 
        }, 
        series: [{ 
            type: 'bar', 
            barWidth: 60, // Match bar thickness
            data: sData, 
            label: { 
                show: true, 
                position: 'top', 
                color: '#fff',
                fontFamily: 'Orbitron',
                fontWeight: 'bold',
                fontSize: 18 // Large, clear numbers
            } 
        }] 
    })
}

const initRadarChart = async () => {
    const chart = echarts.init(radarChartRef.value, 'dark')
    charts.push(chart)
    const res = await axios.get('http://localhost:5000/api/charts/radar')
    
    chart.setOption({
        backgroundColor: 'transparent',
        tooltip: { show: true, trigger: 'item', confine: true }, // Show values on hover
        radar: {
            radius: '75%', // Zoom In
            center: ['50%', '50%'],
            // Force 1:1 Indicators from Screenshot
            indicator: [
               { name: '创新力 (Inno)', max: 100 },
               { name: '世界观 (World)', max: 100 },
               { name: '角色 (Char)', max: 100 },
               { name: '捧场 (Support)', max: 100 },
               { name: '故事性 (Story)', max: 100 }
            ],
            shape: 'polygon',
            splitNumber: 5,
            axisName: {
                color: '#ddd', // Clear light text
                fontSize: 14
            },
            splitLine: {
                lineStyle: {
                    color: 'rgba(255, 255, 255, 0.1)'
                }
            },
            splitArea: {
                show: false
            },
            axisLine: {
                lineStyle: {
                    color: 'rgba(255, 255, 255, 0.1)'
                }
            }
        },
        series: [{
            type: 'radar',
            symbol: 'circle',
            symbolSize: 6, // Visible Gold Points
            data: [{
                value: res.data.values,
                name: 'Platform Average (全站均值)',
                itemStyle: {
                    color: '#F5C544' // Gold Point/Line
                },
                lineStyle: {
                    width: 2,
                    color: '#F5C544'
                },
                areaStyle: {
                    color: 'rgba(245, 197, 68, 0.3)' // Translucent Gold Fill
                }
            }]
        }]
    })
}

const initAuthorChart = async () => {
    const chart = echarts.init(authorChartRef.value, 'dark')
    charts.push(chart)
    const res = await axios.get('http://localhost:5000/api/charts/author_tiers')
    chart.setOption({
        backgroundColor: 'transparent',
        color: ['#4169E1', '#A2CD5A', '#5d617d', '#FF9F43'], // Blue, Green, Grey, Orange
        series: [{
            type: 'funnel',
            left: '10%',
            width: '70%',
            sort: 'ascending',
            gap: 2,
            label: {
                show: true,
                position: 'right',
                color: '#fff',
                fontSize: 14,
                fontWeight: 'bold',
                formatter: '{b}'
            },
            data: res.data
        }]
    })
}

const initScatterChart = async () => {
    await nextTick()
    if(!scatterChartRef.value) return
    const chart = echarts.init(scatterChartRef.value, 'dark')
    charts.push(chart)
    const res = await axios.get('http://localhost:5000/api/charts/scatter')
    
    chart.setOption({
        backgroundColor: 'transparent',
        tooltip: { 
            trigger: 'item',
            formatter: (params) => {
                return `<b>${params.data[2]}</b><br/>IP Score: ${params.data[0]}<br/>Interaction: ${params.data[1].toLocaleString()}`
            }
        },
        grid: { left: '12%', right: '10%', top: '15%', bottom: '15%' },
        xAxis: { 
            name: 'IP Score', 
            nameTextStyle: { color: '#ccc' },
            splitLine: { show: true, lineStyle: { color: '#333' } },
            axisLine: { lineStyle: { color: '#666' } }
        },
        yAxis: { 
            name: 'Interaction', 
            nameTextStyle: { color: '#ccc' },
            splitLine: { show: true, lineStyle: { color: '#333' } },
            axisLine: { lineStyle: { color: '#666' } }
        },
        series: [{
            type: 'scatter',
            symbolSize: 10,
            itemStyle: {
                color: '#F72585', // Pink Dots
                shadowBlur: 10,
                shadowColor: '#F72585'
            },
            data: res.data
        }]
    })
}

const initCorrelationChart = async () => {
    await nextTick()
    if(!correlationChartRef.value) return
    const chart = echarts.init(correlationChartRef.value, 'dark')
    charts.push(chart)
    const res = await axios.get('http://localhost:5000/api/charts/correlation')
    
    const axisData = res.data.axis
    const data = res.data.data.map(item => {
        return [item[1], item[0], item[2]] // Swap x/y for heatmap display if needed
    })
    
    chart.setOption({
        backgroundColor: 'transparent',
        tooltip: { position: 'top' },
        // Increase bottom to 30% to make ABSOLUTELY SURE space exists for the slider
        grid: { top: '5%', bottom: '30%', left: '2%', right: '2%', containLabel: true },
        xAxis: { type: 'category', data: axisData, splitArea: { show: true }, axisLabel: { color: '#fff', rotate: 0, fontSize: 12, fontWeight: 'bold' } },
        yAxis: { type: 'category', data: axisData, splitArea: { show: true }, axisLabel: { color: '#fff', fontSize: 12, fontWeight: 'bold' } },
        visualMap: {
            min: 0, max: 1,
            calculable: true,
            orient: 'horizontal',
            left: 'center',
            bottom: '0', // Pin to bottom
            inRange: {
                 color: ['#4CC9F0', '#7209B7', '#F72585'] // Blue -> Purple -> Pink
            },
            textStyle: { color: '#fff', fontWeight: 'bold' },
            z: 100 // Top Layer
        },
        series: [{
            name: 'Correlation',
            type: 'heatmap',
            data: res.data.data, // Using raw [row, col, Val]
            label: { show: true, color: '#fff', fontSize: 16, fontWeight: 'bold' },
            itemStyle: {
                borderColor: '#000'
            },
            emphasis: {
                label: {
                    show: true,
                    fontSize: 20,
                    fontWeight: 'bold',
                    color: '#fff' // Keep white to be safe against pink overwrite issues
                },
                itemStyle: {
                    shadowBlur: 20,
                    shadowColor: 'white',
                    borderColor: 'white',
                    borderWidth: 4
                }
            }
        }]
    })
}

</script>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700&display=swap');
.dashboard { padding: 0; background: #020617; height: 100vh; width: 100%; color: white; display: flex; flex-direction: column; overflow: hidden; }

/* Centered Header with Decorations */
.header-wrapper { display: flex; justify-content: center; align-items: center; height: 8vh; background: rgba(5,5,17,0.8); position: relative; z-index: 10; width: 100%; border-bottom: none; }
.header-decoration { height: 2px; width: 15%; background: linear-gradient(90deg, transparent, #4CC9F0, transparent); margin: 0 20px; opacity: 0.7; }
.main-title { font-family: 'Orbitron'; font-size: 3.5vh; color: #fff; text-shadow: 0 0 15px #4cc9f0; margin: 0; text-align: center; font-weight: bold; letter-spacing: 4px; }

/* Switch Button in Header */
.header-switch {
    position: absolute; right: 20px; top: 50%; transform: translateY(-50%);
    border: 1px solid #F72585; color: #F72585;
    padding: 5px 15px; border-radius: 4px; cursor: pointer;
    font-family: 'Orbitron'; font-size: 1.4vh; font-weight: bold;
    display: flex; align-items: center; gap: 8px;
    background: rgba(247, 37, 133, 0.1);
    transition: all 0.3s;
}
.header-switch:hover { background: rgba(247, 37, 133, 0.3); box-shadow: 0 0 10px #F72585; }
.switch-icon { font-size: 1.8vh; }

/* REFINED STATS ROW FROM SCREENSHOT 1689 */
.top-stats-row { display: flex; gap: 20px; padding: 10px 20px; height: 12vh; align-items: stretch; background: rgba(5,5,17,0.5); }
.stat-item { 
    flex: 1; 
    background: transparent; 
    border: 1px solid rgba(76, 201, 240, 0.3); /* Thin Cyan Border */
    border-radius: 4px; 
    display: flex; 
    align-items: center; 
    justify-content: space-between; 
    padding: 0 30px; 
    position: relative; 
    box-shadow: inset 0 0 20px rgba(76, 201, 240, 0.05); /* Very subtle internal glow */
}
/* Replaced pink border with LEFT BAR styled like screenshot (Pink small bar) */
.stat-item::before { 
    content: ''; position: absolute; left: 0; top: 25%; bottom: 25%; width: 3px; background: #F72585; 
    box-shadow: 0 0 5px #F72585;
}
.action-card::before { display: none; }

.stat-info { display: flex; flex-direction: column; justify-content: center; width: 100%; align-items: center; } /* Centered Info */
.centered { text-align: center; }

.stat-label { font-size: 1.4vh; margin-bottom: 5px; font-weight: bold; }
.cyan-text { color: #4CC9F0; text-shadow: 0 0 5px rgba(76, 201, 240, 0.5); }

.stat-num { font-size: 3.8vh; font-family: 'Orbitron', monospace; letter-spacing: 2px; font-weight: bold; }
.white-text { color: #fff; }
.cyan-glow { color: #4CC9F0; text-shadow: 0 0 15px #4CC9F0; }

.custom-icon { font-size: 3.5vh; opacity: 0.9; }

/* Action Card (Transparent with Purple Border - Image 2 Style) */
.action-card { 
    background: rgba(114, 9, 183, 0.2); /* Dark Transparent Purple */
    border: 1px solid #7209B7; 
    justify-content: space-between;
    padding: 0 25px;
    box-shadow: inset 0 0 20px rgba(114, 9, 183, 0.2);
}
.action-card:hover {
    background: rgba(114, 9, 183, 0.4);
    box-shadow: 0 0 15px rgba(114, 9, 183, 0.5);
}

.action-card .stat-info { 
    align-items: center; /* Centered Text */
    justify-content: center;
    width: 100%; /* Take up space to center */
}
.action-content { display: flex; flex-direction: column; align-items: center; } /* Inner center */

.action-label { color: #4CC9F0; font-family: 'Orbitron'; font-size: 2.0vh; font-weight: bold; letter-spacing: 1px; }
.action-sub { color: #fff; font-size: 1.2vh; margin-top: 6px; font-weight: normal; }
.robot-icon { font-size: 4.5vh; filter: drop-shadow(0 0 5px rgba(114, 9, 183, 0.5)); margin-left: 10px; }

/* Main Content */
.main-content { flex: 1; display: flex; flex-direction: column; padding: 10px 20px 20px 20px; gap: 15px; min-height: 0; }
.grid-row { display: grid; gap: 15px; }
.row-top { flex: 1.2; grid-template-columns: 28% 44% 28%; }
.row-bottom { flex: 1; grid-template-columns: 1fr 1fr 1fr 1fr; }

.tech-card { 
    background: rgba(16, 33, 60, 0.3); 
    border: 1px solid rgba(255, 255, 255, 0.05); 
    border-radius: 8px; 
    position: relative; 
    display: flex; 
    flex-direction: column; 
    padding: 15px; 
    transition: all 0.3s ease; 
}
.tech-card:hover {
    transform: translateY(-5px);
    box-shadow: 0 0 25px rgba(76, 201, 240, 0.4);
    border-color: #4CC9F0;
    z-index: 10;
}

/* Add hover for stat items too (Top 3 boxes) */
.stat-item {
    transition: all 0.3s ease;
}
.stat-item:hover {
    transform: translateY(-5px);
    box-shadow: 0 0 20px rgba(76, 201, 240, 0.3), inset 0 0 10px rgba(76, 201, 240, 0.1);
    border-color: #4CC9F0;
}

/* Cyan corners */
.tech-card::before { content: ''; position: absolute; top: 0; left: 0; width: 10px; height: 10px; border-top: 2px solid #4CC9F0; border-left: 2px solid #4CC9F0; border-top-left-radius: 8px; transition: all 0.3s; pointer-events: none; }
.tech-card::after { content: ''; position: absolute; bottom: 0; right: 0; width: 10px; height: 10px; border-bottom: 2px solid #4CC9F0; border-right: 2px solid #4CC9F0; border-bottom-right-radius: 8px; transition: all 0.3s; pointer-events: none; }

.tech-card:hover::before, .tech-card:hover::after {
    width: 100%;
    height: 100%;
    opacity: 0.1; /* Subtle full border expansion or effect */
}

.card-title { color: #4CC9F0; font-size: 1.6vh; font-weight: bold; margin-bottom: 10px; padding-left: 10px; border-left: 3px solid #F72585; display: flex; align-items: center; }
.chart-box { flex: 1; width: 100%; min-height: 0; }
</style>
