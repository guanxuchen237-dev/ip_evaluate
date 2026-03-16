<template>
  <div class="predict-container">
    <div class="page-header">
      <el-button icon="ArrowLeft" plain class="neon-btn" @click="$router.push('/')">返回大屏</el-button>
      <h2 class="neon-title">小说IP价值预测系统</h2>
    </div>

    <el-row :gutter="40" style="margin-top: 20px;" class="full-height-row">
      <!-- Input Panel -->
      <el-col :span="10" class="full-height-col">
        <div class="neon-card input-card">
          <div class="card-header">
            <span>📡 录入作品信息</span>
          </div>
          <el-form label-position="top" size="large" class="neon-form">
            <el-form-item label="小说名称">
              <el-input v-model="form.title" placeholder="请输入小说名称" class="custom-input"></el-input>
            </el-form-item>
            <el-form-item label="题材分类">
              <el-select v-model="form.category" placeholder="请选择题材" style="width: 100%;" class="custom-select" popper-class="dark-popper">
                <el-option label="玄幻奇幻" value="玄幻"></el-option>
                <el-option label="都市现实" value="都市"></el-option>
                <el-option label="武侠仙侠" value="仙侠"></el-option>
                <el-option label="科幻未来" value="科幻"></el-option>
                <el-option label="历史军事" value="历史"></el-option>
              </el-select>
            </el-form-item>
            <el-form-item label="开篇/简介内容" style="flex: 1; display: flex; flex-direction: column;">
              <el-input 
                type="textarea" 
                v-model="form.abstract" 
                :rows="10" 
                placeholder="请输入小说简介或开篇三章内容，AI神经网络将自动分析..."
                class="custom-textarea">
              </el-input>
            </el-form-item>
            <el-button class="neon-submit-btn" :loading="loading" @click="handlePredict">
              {{ loading ? '深度运算中...' : '启动预测引擎' }}
            </el-button>
          </el-form>
        </div>
      </el-col>

      <!-- Result Panel -->
      <el-col :span="14" class="full-height-col">
        <div class="neon-card result-card" v-loading="loading" element-loading-background="rgba(0, 0, 0, 0.7)">
           <div class="card-header">
             <span>📊 分析报告结果</span>
           </div>

           <div v-if="!result" class="empty-state">
             <div class="empty-icon">🤖</div>
             <p>等待录入数据...</p>
           </div>

           <div v-else class="report-content">
              <!-- Score Header -->
              <div class="score-header">
                 <div class="score-circle">
                    <svg viewBox="0 0 100 100" class="circle-svg">
                       <circle cx="50" cy="50" r="45" class="bg-ring" />
                       <circle cx="50" cy="50" r="45" class="prog-ring" :style="{strokeDashoffset: (283 - 283 * (result.score/100))}" />
                    </svg>
                    <div class="score-inner">
                        <div class="score-val">{{ result.score }}</div>
                        <div class="score-label">综合IP指数</div>
                    </div>
                 </div>
                 
                 <!-- Dual Dimension Analysis -->
                 <div class="dual-score-box" v-if="result.details && result.details.content_potential_score">
                    <div class="ds-row">
                        <span class="ds-label" style="color: #F72585;">内容潜力</span>
                        <div class="ds-bar-bg"><div class="ds-bar-fill" :style="{width: result.details.content_potential_score + '%', background: '#F72585'}"></div></div>
                        <span class="ds-val">{{ result.details.content_potential_score }}</span>
                    </div>
                    <div class="ds-row">
                        <span class="ds-label" style="color: #4CC9F0;">市场数据</span>
                        <div class="ds-bar-bg"><div class="ds-bar-fill" :style="{width: result.score + '%', background: '#4CC9F0'}"></div></div>
                        <span class="ds-val">{{ result.score }}</span>
                    </div>
                    <div class="ds-insight">
                        <span v-if="result.score > result.details.content_potential_score">
                            📈 运营加成: <span class="highlight">+{{ (result.score - result.details.content_potential_score).toFixed(1) }}</span>
                        </span>
                        <span v-else>
                            💎 价值低估: <span class="highlight">-{{ (result.details.content_potential_score - result.score).toFixed(1) }}</span>
                        </span>
                    </div>
                 </div>

                 <div class="grade-box">
                    <div class="grade-label">潜力评级</div>
                    <div class="grade-val" :class="getGradeColor(result.details.predicted_level)">{{ result.details.predicted_level }}</div>
                 </div>
              </div>
              
              <div class="divider"></div>

              <!-- Analysis -->
              <div class="analysis-section">
                 <h3 class="section-title">✨ AI 深度点评</h3>
                 <div class="ai-text typewriter">{{ (result.ai_report || {}).comment }}</div>
                 
                 <el-row :gutter="20" style="margin-top: 25px;">
                    <el-col :span="12">
                       <div class="tag-label pro">✅ 核心优势</div>
                       <ul class="list-pros">
                          <li v-for="(p, i) in (result.ai_report || {}).pros" :key="i">{{ p }}</li>
                       </ul>
                    </el-col>
                    <el-col :span="12">
                       <div class="tag-label con">⚠️ 潜在风险</div>
                       <ul class="list-cons">
                          <li v-for="(c, i) in (result.ai_report || {}).cons" :key="i">{{ c }}</li>
                       </ul>
                    </el-col>
                 </el-row>
              </div>
              
              <div class="divider"></div>
              <h3 class="section-title">📈 未来热度趋势预测</h3>
              <div ref="trendChart" class="trend-chart-box"></div>
           </div>
        </div>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, reactive, nextTick, onMounted, onBeforeUnmount } from 'vue'
import axios from 'axios'
import * as echarts from 'echarts'

const form = reactive({ title: '', category: '', abstract: '' })
const loading = ref(false)
const result = ref(null)
const trendChart = ref(null)
const radarChart = ref(null)

// Dynamic Background
const bgCanvas = ref(null)
let animId = null

const handlePredict = async () => {
   if(!form.title) return alert('请输入标题')
   loading.value = true
   try {
     const res = await axios.post('http://localhost:5000/api/predict', form)
     result.value = res.data
     await nextTick()
     initCharts()
   } catch(e) {
     console.error(e)
     alert('分析失败')
   } finally {
     loading.value = false
   }
}

const initCharts = () => {
    // 1. Trend Chart
    if(trendChart.value) {
        const tChart = echarts.init(trendChart.value, 'dark')
        const tData = (result.value.ai_report || {}).trend || [50, 60, 70, 80, 85, 90]
        tChart.setOption({
            backgroundColor: 'transparent',
            tooltip: { trigger: 'axis' },
            grid: { top: 30, bottom: 20, left: 40, right: 20, containLabel: true },
            xAxis: { 
                type: 'category', 
                data: ['+1月', '+2月', '+3月', '+4月', '+5月', '+6月'], 
                axisLine: {lineStyle:{color:'rgba(255,255,255,0.3)'}},
                axisLabel: { color: 'rgba(255,255,255,0.7)' }
            },
            yAxis: { 
                type: 'value', 
                splitLine: {lineStyle:{color:'rgba(255,255,255,0.1)'}},
                axisLabel: { color: 'rgba(255,255,255,0.7)' }
            },
            series: [{ 
                type: 'line', smooth: true, data: tData, 
                symbolSize: 8,
                itemStyle: { color: '#4CC9F0', shadowBlur: 10, shadowColor: '#4CC9F0' }, 
                areaStyle: { color: new echarts.graphic.LinearGradient(0,0,0,1, [{offset:0, color:'rgba(76,201,240,0.4)'}, {offset:1, color:'rgba(76,201,240,0)'}]) },
                lineStyle: { width: 4, shadowBlur: 15, shadowColor: 'rgba(76,201,240,0.6)' }
            }]
        })
    }
    
    // 2. Radar Chart
    if(radarChart.value && result.value.ai_report.scores) {
        const rChart = echarts.init(radarChart.value, 'dark')
        const scores = result.value.ai_report.scores
        const indicators = [
            { name: '创新力', max: 100 },
            { name: '故事性', max: 100 },
            { name: '商业度', max: 100 },
            { name: '世界观', max: 100 },
            { name: '人设', max: 100 }
        ]
        const dataValues = [
            scores.Innovation || 80,
            scores.Story || 80,
            scores.Commercial || 80,
            scores.World || 80,
            scores.Character || 80
        ]
        
        rChart.setOption({
            backgroundColor: 'transparent',
            radar: {
                indicator: indicators,
                splitArea: { areaStyle: { color: ['rgba(255,255,255,0.02)', 'rgba(255,255,255,0.05)'] } },
                axisLine: { lineStyle: { color: 'rgba(255,255,255,0.2)' } },
                splitLine: { lineStyle: { color: 'rgba(255,255,255,0.2)' } },
                axisName: { color: '#4CC9F0', fontSize: 14, fontFamily: 'Orbitron' }
            },
            series: [{
                type: 'radar',
                data: [{
                    value: dataValues,
                    name: 'IP能力五维图',
                    symbol: 'circle',
                    symbolSize: 6,
                    itemStyle: { color: '#F72585' },
                    areaStyle: { color: 'rgba(247, 37, 133, 0.4)' },
                    lineStyle: { width: 2, color: '#F72585' }
                }]
            }]
        })
    }
}

const getGradeColor = (g) => {
    if(g === 'S') return 'glow-gold'
    if(g === 'A') return 'glow-purple'
    return 'glow-blue'
}

// Particle Animation
onMounted(() => {
    const canvas = bgCanvas.value
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    let width, height, particles = []
    
    const resize = () => {
        width = canvas.width = window.innerWidth
        height = canvas.height = window.innerHeight
    }
    
    class Particle {
        constructor() {
            this.x = Math.random() * width
            this.y = Math.random() * height
            this.vx = (Math.random() - 0.5) * 0.5
            this.vy = (Math.random() - 0.5) * 0.5
            this.size = Math.random() * 2
            this.color = `rgba(${Math.random()>0.5? '76, 201, 240' : '247, 37, 133'}, ${Math.random() * 0.5})`
        }
        update() {
            this.x += this.vx; this.y += this.vy
            if(this.x<0) this.x=width; if(this.x>width) this.x=0
            if(this.y<0) this.y=height; if(this.y>height) this.y=0
        }
        draw() {
            ctx.fillStyle = this.color
            ctx.beginPath()
            ctx.arc(this.x, this.y, this.size, 0, Math.PI*2)
            ctx.fill()
        }
    }
    
    const initParticles = () => {
        particles = []
        for(let i=0; i<100; i++) particles.push(new Particle())
    }
    
    const animate = () => {
        ctx.clearRect(0,0,width,height)
        particles.forEach(p => { p.update(); p.draw() })
        animId = requestAnimationFrame(animate)
    }
    
    window.addEventListener('resize', resize)
    resize()
    initParticles()
    animate()
})

onBeforeUnmount(() => cancelAnimationFrame(animId))
</script>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700&display=swap');

.predict-container {
  position: relative;
  padding: 30px;
  background: radial-gradient(circle at top right, #1a1a2e, #050511);
  height: 100vh;
  box-sizing: border-box;
  overflow: hidden;
  color: #fff;
  font-family: 'Microsoft YaHei', sans-serif;
  display: flex;
  flex-direction: column;
}

.bg-canvas {
    position: absolute; top:0; left:0; width:100%; height:100%; z-index:0; pointer-events:none;
}

.page-header {
  position: relative; z-index: 10;
  display: flex;
  align-items: center;
  gap: 20px;
  margin-bottom: 20px;
  border-bottom: 1px solid rgba(76,201,240,0.2);
  padding-bottom: 15px;
  flex-shrink: 0;
}

.neon-title { 
    margin: 0; 
    font-family: 'Orbitron'; 
    background: linear-gradient(90deg, #4CC9F0, #F72585);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    text-shadow: 0 0 20px rgba(76,201,240,0.3);
    font-size: 36px;
}

.neon-btn { 
    background: rgba(76,201,240,0.1); border: 1px solid #4CC9F0; color: #4CC9F0; 
    transition: all 0.3s;
    font-size: 18px;
    padding: 12px 24px;
    backdrop-filter: blur(5px);
}
.neon-btn:hover { background: rgba(76,201,240,0.3); box-shadow: 0 0 15px rgba(76,201,240,0.5); transform: translateY(-2px); }

.full-height-row { flex: 1; overflow: hidden; position: relative; z-index: 10; }
.full-height-col { height: 100%; }

.neon-card {
  background: rgba(20, 30, 50, 0.4); /* More transparent */
  backdrop-filter: blur(16px); /* Glassmorphism */
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 16px;
  padding: 30px;
  box-shadow: 0 20px 50px rgba(0,0,0,0.3);
  height: 100%;
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
  transition: transform 0.3s;
}
.neon-card:hover { border-color: rgba(255,255,255,0.2); }

.card-header { 
    font-size: 24px; color: #e0e0ff; margin-bottom: 25px; 
    border-left: 6px solid #F72585; padding-left: 15px; font-weight: bold; 
    text-shadow: 0 2px 4px rgba(0,0,0,0.5);
}

.neon-form { flex: 1; display: flex; flex-direction: column; }

/* Enhanced Form Inputs */
.custom-input :deep(.el-input__wrapper), 
.custom-select :deep(.el-input__wrapper),
.custom-textarea :deep(.el-textarea__inner) {
    background-color: rgba(0,0,0,0.3) !important;
    border: 1px solid rgba(255,255,255,0.1) !important;
    box-shadow: none !important;
    color: #fff !important;
    font-size: 18px !important;
    border-radius: 8px;
    transition: all 0.3s;
}
.custom-input :deep(.el-input__wrapper):hover,
.custom-textarea :deep(.el-textarea__inner):hover {
    border-color: #4CC9F0 !important;
    background-color: rgba(76,201,240,0.1) !important;
}
.custom-input :deep(.el-input__wrapper).is-focus,
.custom-textarea :deep(.el-textarea__inner):focus {
    border-color: #F72585 !important;
    box-shadow: 0 0 10px rgba(247, 37, 133, 0.3) !important;
}

.custom-input :deep(.el-input__inner) { height: 50px; }
.custom-textarea { height: 100%; }
.custom-textarea :deep(.el-textarea__inner) { height: 100% !important; font-family: inherit; line-height: 1.6; }

:deep(.el-form-item__label) { font-size: 20px !important; margin-bottom: 12px !important; color: #a5b4fc; text-shadow: 0 0 5px rgba(0,0,0,0.5); }
:deep(.el-form-item) { margin-bottom: 30px; }

.neon-submit-btn {
    width: 100%; margin-top: auto; height: 60px;
    background: linear-gradient(135deg, #4CC9F0 0%, #4361EE 100%);
    border: none; color: #fff; font-weight: bold; font-family: 'Orbitron'; letter-spacing: 2px;
    font-size: 22px; border-radius: 8px;
    box-shadow: 0 5px 15px rgba(67, 97, 238, 0.4);
    transition: all 0.3s;
}
.neon-submit-btn:hover { transform: translateY(-2px); box-shadow: 0 8px 25px rgba(67, 97, 238, 0.6); }

/* Result States */
.empty-state { flex: 1; display: flex; flex-direction: column; justify-content: center; align-items: center; color: #8ecae6; opacity: 0.7; }
.empty-icon { font-size: 80px; margin-bottom: 25px; animation: float 3s ease-in-out infinite; filter: drop-shadow(0 0 10px rgba(76,201,240,0.5)); }
.empty-state p { font-size: 24px; font-weight: 300; }

.report-content { flex: 1; overflow-y: auto; padding-right: 10px; }

.score-header { display: flex; justify-content: space-between; align-items: center; padding: 20px 10px; }
.score-circle { position: relative; width: 180px; height: 180px; display: flex; justify-content: center; align-items: center; }
.circle-svg { position: absolute; width: 100%; height: 100%; transform: rotate(-90deg); }
.bg-ring { fill: none; stroke: rgba(255,255,255,0.05); stroke-width: 8; }
.prog-ring { 
    fill: none; stroke: #F72585; stroke-width: 8; stroke-dasharray: 283; stroke-dashoffset: 0; 
    filter: drop-shadow(0 0 8px #F72585); 
    animation: dash 1.5s ease-out forwards;
}
.score-inner { text-align: center; z-index: 2; }
.score-val { font-size: 46px; font-weight: bold; color: #fff; font-family: 'Orbitron'; text-shadow: 0 0 20px rgba(255,255,255,0.5); }
.score-label { font-size: 16px; color: #ccc; }

.radar-chart-box { width: 250px; height: 250px; }

.grade-val { font-size: 80px; font-weight: 900; font-family: 'Orbitron'; transform: rotate(5deg); }
.glow-gold { color: #FFD166; text-shadow: 0 0 30px #FFD166; }
.glow-purple { color: #F72585; text-shadow: 0 0 30px #F72585; }
.glow-blue { color: #4CC9F0; text-shadow: 0 0 30px #4CC9F0; }

.divider { height: 1px; background: linear-gradient(90deg, transparent, rgba(255,255,255,0.2), transparent); margin: 30px 0; }
.section-title { color: #bde0fe; margin-bottom: 20px; display: flex; align-items: center; gap: 12px; font-size: 24px; text-shadow: 0 0 10px rgba(189, 224, 254, 0.3); }

.ai-text { 
    background: rgba(0,0,0,0.2); 
    padding: 25px; border-radius: 12px; border-left: 4px solid #7209B7; 
    line-height: 1.8; color: #e2e8f0; font-family: 'Consolas', monospace; font-size: 18px;
    box-shadow: inset 0 0 20px rgba(0,0,0,0.2);
}

.tag-label { 
    font-size: 16px; font-weight: bold; margin-bottom: 15px; padding: 6px 14px; border-radius: 6px; display: inline-block; 
}
.tag-label.pro { background: rgba(6, 214, 160, 0.1); color: #06D6A0; border: 1px solid rgba(6, 214, 160, 0.3); }
.tag-label.con { background: rgba(239, 71, 111, 0.1); color: #EF476F; border: 1px solid rgba(239, 71, 111, 0.3); }

.list-pros li { color: #06D6A0; margin-bottom: 8px; list-style: none; font-size: 18px; position: relative; padding-left: 20px; }
.list-pros li::before { content: '✓'; position: absolute; left: 0; font-weight: bold; }
.list-cons li { color: #EF476F; margin-bottom: 8px; list-style: none; font-size: 18px; position: relative; padding-left: 20px; }
.list-cons li::before { content: '!'; position: absolute; left: 0; font-weight: bold; }

.trend-chart-box { height: 300px; width: 100%; }

/* Animations */
@keyframes float { 0% { transform: translateY(0px); } 50% { transform: translateY(-10px); } 100% { transform: translateY(0px); } }
@keyframes dash { from { stroke-dashoffset: 283; } to { stroke-dashoffset: 0; } }

.slide-up { animation: slideUp 0.6s ease-out forwards; opacity: 0; transform: translateY(20px); }
@keyframes slideUp { to { opacity: 1; transform: translateY(0); } }

/* Scrollbar */
::-webkit-scrollbar { width: 8px; }
::-webkit-scrollbar-track { background: rgba(0,0,0,0.1); }
::-webkit-scrollbar-thumb { background: rgba(76,201,240,0.3); border-radius: 4px; }
::-webkit-scrollbar-thumb:hover { background: rgba(76,201,240,0.5); }

/* Dual Score Box */
.dual-score-box {
    flex: 1; margin: 0 30px; display: flex; flex-direction: column; justify-content: center;
    background: rgba(0,0,0,0.2); padding: 15px; border-radius: 10px;
    border: 1px solid rgba(255,255,255,0.05);
}
.ds-row { display: flex; align-items: center; margin-bottom: 8px; }
.ds-label { width: 70px; font-size: 14px; font-weight: bold; }
.ds-bar-bg { flex: 1; height: 8px; background: rgba(255,255,255,0.1); border-radius: 4px; margin: 0 10px; overflow: hidden; }
.ds-bar-fill { height: 100%; border-radius: 4px; transition: width 1s ease-out; }
.ds-val { width: 40px; text-align: right; font-family: 'Orbitron'; font-weight: bold; }

.ds-insight { margin-top: 10px; font-size: 14px; color: #ccc; text-align: center; }
.ds-insight .highlight { color: #ffffff; font-weight: bold; font-size: 16px; margin-left: 5px; text-shadow: 0 0 5px rgba(255,255,255,0.5); }
</style>
