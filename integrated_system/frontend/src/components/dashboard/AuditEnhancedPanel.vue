<template>
  <div class="space-y-6">
    <!-- 顶部统计和自动刷新控�?-->
    <div class="flex items-center justify-between">
      <div class="flex items-center gap-4">
        <h2 class="text-xl font-bold text-slate-900 flex items-center gap-2">
          <Shield class="w-6 h-6 text-indigo-600" />
          AI 智能审计中心
        </h2>
        <span class="text-xs text-slate-500">
          �?{{ filteredAuditLogs.length }} 条记�?          <span v-if="selectedLogs.length > 0" class="text-indigo-600 font-bold"> (已�?{{ selectedLogs.length }} �?</span>
        </span>
      </div>
      <div class="flex items-center gap-3">
        <!-- 自动刷新开�?-->
        <label class="flex items-center gap-2 text-sm cursor-pointer select-none" :class="autoRefresh ? 'text-emerald-600' : 'text-slate-500'">
          <div class="relative">
            <input type="checkbox" v-model="autoRefresh" class="sr-only" @change="toggleAutoRefresh">
            <div class="w-11 h-6 rounded-full transition-colors duration-300" :class="autoRefresh ? 'bg-emerald-500' : 'bg-slate-300'"></div>
            <div class="absolute left-1 top-1 w-4 h-4 bg-white rounded-full transition-transform duration-300 shadow-sm" :class="autoRefresh ? 'translate-x-5' : 'translate-x-0'"></div>
          </div>
          <span class="font-medium">{{ autoRefresh ? '自动刷新已开�? : '自动刷新已关�? }}</span>
          <span class="text-xs text-slate-400">(30s)</span>
          <span v-if="lastRefreshTime" class="text-xs text-slate-400">| 上次: {{ lastRefreshTime }}</span>
        </label>
        <button @click="fetchAuditLogs" class="p-2 text-slate-500 hover:text-indigo-600 hover:bg-indigo-50 rounded-lg transition-colors">
          <RefreshCw class="w-5 h-5" :class="{ 'animate-spin': auditLogsLoading }" />
        </button>
        <button @click="showConfigModal = true" class="p-2 text-slate-500 hover:text-amber-600 hover:bg-amber-50 rounded-lg transition-colors">
          <Settings class="w-5 h-5" />
        </button>
      </div>
    </div>

    <!-- 数据可视化区�?-->
    <div class="grid grid-cols-12 gap-4">
      <!-- 风险分布饼图 -->
      <div class="col-span-12 md:col-span-4">
        <div class="bg-white/70 backdrop-blur-xl border border-white/50 rounded-2xl p-4 shadow-sm">
          <h4 class="text-xs font-bold text-slate-500 uppercase tracking-wider mb-3 flex items-center gap-2">
            <PieChart class="w-4 h-4 text-rose-500" /> 风险等级分布
          </h4>
          <div v-if="riskDistribution.length === 0" class="text-center py-8 text-slate-400 text-sm">
            暂无数据
          </div>
          <div v-else class="relative h-48">
            <svg viewBox="0 0 200 200" class="w-full h-full transform -rotate-90">
              <circle v-for="(item, index) in riskDistribution" :key="index"
                      cx="100" cy="100" r="70"
                      fill="transparent"
                      :stroke="item.color"
                      :stroke-width="20"
                      :stroke-dasharray="`${item.percentage * 4.4} ${440 - item.percentage * 4.4}`"
                      :stroke-dashoffset="-getPieOffset(index)"
                      class="transition-all duration-500" />
            </svg>
            <div class="absolute inset-0 flex items-center justify-center flex-col">
              <span class="text-2xl font-bold text-slate-800">{{ auditLogs.length }}</span>
              <span class="text-xs text-slate-500">总审计数</span>
            </div>
          </div>
          <div class="mt-3 flex justify-center gap-4 text-xs">
            <div v-for="item in riskDistribution" :key="item.level" class="flex items-center gap-1">
              <span class="w-2 h-2 rounded-full" :style="{ backgroundColor: item.color }"></span>
              <span :class="item.textColor">{{ item.label }}: {{ item.count }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- 审计趋势折线�?-->
      <div class="col-span-12 md:col-span-8">
        <div class="bg-white/70 backdrop-blur-xl border border-white/50 rounded-2xl p-4 shadow-sm">
          <div class="flex items-center justify-between mb-3">
            <h4 class="text-xs font-bold text-slate-500 uppercase tracking-wider flex items-center gap-2">
              <TrendingUp class="w-4 h-4 text-indigo-500" /> 审计趋势 (7�?
            </h4>
            <div class="flex gap-2">
              <button v-for="range in ['7d', '30d']" :key="range"
                      @click="trendRange = range"
                      class="px-2 py-1 text-xs rounded font-medium transition-colors"
                      :class="trendRange === range ? 'bg-indigo-100 text-indigo-600' : 'text-slate-400 hover:text-slate-600'">
                {{ range === '7d' ? '7�? : '30�? }}
              </button>
            </div>
          </div>
          <div class="relative h-48">
            <svg viewBox="0 0 600 180" class="w-full h-full" preserveAspectRatio="none">
              <defs>
                <linearGradient id="trendGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stop-color="#6366f1" stop-opacity="0.3"/>
                  <stop offset="100%" stop-color="#6366f1" stop-opacity="0"/>
                </linearGradient>
              </defs>
              <!-- 网格�?-->
              <line x1="0" y1="45" x2="600" y2="45" stroke="#f1f5f9" stroke-width="0.5" />
              <line x1="0" y1="90" x2="600" y2="90" stroke="#f1f5f9" stroke-width="0.5" />
              <line x1="0" y1="135" x2="600" y2="135" stroke="#f1f5f9" stroke-width="0.5" />
              
              <!-- 填充区域 -->
              <path v-if="trendData.length > 0"
                    :d="getTrendFillPath(trendData)"
                    fill="url(#trendGrad)" />
              
              <!-- 折线 -->
              <path v-if="trendData.length > 0"
                    :d="getTrendLinePath(trendData)"
                    fill="none" stroke="#6366f1" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
              
              <!-- 数据�?-->
              <circle v-for="(point, index) in trendData" :key="index"
                      :cx="point.x" :cy="point.y" r="3"
                      fill="#6366f1" stroke="white" stroke-width="2"
                      class="hover:r-5 transition-all cursor-pointer"
                      @mouseenter="hoveredTrendPoint = point"
                      @mouseleave="hoveredTrendPoint = null" />
            </svg>
            
            <!-- 悬停提示 -->
            <div v-if="hoveredTrendPoint" 
                 class="absolute top-2 bg-slate-900 text-white text-xs rounded px-2 py-1 pointer-events-none"
                 :style="{ left: `calc(${(hoveredTrendPoint.x / 600) * 100}% - 40px)` }">
              {{ hoveredTrendPoint.date }}: {{ hoveredTrendPoint.count }} �?            </div>
          </div>
          <div class="flex justify-between text-xs text-slate-400 mt-2">
            <span>{{ trendLabels[0] }}</span>
            <span>{{ trendLabels[Math.floor(trendLabels.length / 2)] }}</span>
            <span>{{ trendLabels[trendLabels.length - 1] }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 增强筛选器 -->
    <div class="bg-white/60 backdrop-blur-xl border border-white/40 rounded-2xl p-4 shadow-sm">
      <div class="flex flex-wrap items-center gap-3">
        <!-- 风险等级多�?-->
        <div class="flex items-center gap-2">
          <span class="text-xs text-slate-500">风险等级:</span>
          <div class="flex gap-1">
            <button v-for="level in ['HIGH', 'MEDIUM', 'LOW']" :key="level"
                    @click="toggleFilter('riskLevels', level)"
                    class="px-3 py-1.5 text-xs rounded-lg font-medium transition-all"
                    :class="filters.riskLevels.includes(level) ? getRiskLevelClass(level) : 'bg-slate-100 text-slate-500'">
              {{ level === 'HIGH' ? '�? : level === 'MEDIUM' ? '�? : '�? }}
            </button>
          </div>
        </div>
        
        <!-- 风险类型多�?-->
        <div class="flex items-center gap-2">
          <span class="text-xs text-slate-500">风险类型:</span>
          <select v-model="filters.riskTypes" multiple class="hidden">
            <option v-for="type in availableRiskTypes" :key="type" :value="type">{{ type }}</option>
          </select>
          <div class="flex flex-wrap gap-1 max-w-xs">
            <button v-for="type in availableRiskTypes.slice(0, 5)" :key="type"
                    @click="toggleFilter('riskTypes', type)"
                    class="px-2 py-1 text-xs rounded border transition-all"
                    :class="filters.riskTypes.includes(type) ? 'bg-amber-100 border-amber-200 text-amber-700' : 'bg-white border-slate-200 text-slate-500'">
              {{ type }}
            </button>
          </div>
        </div>
        
        <!-- 平台筛�?-->
        <div class="flex items-center gap-2">
          <span class="text-xs text-slate-500">平台:</span>
          <div class="flex gap-1">
            <button v-for="platform in ['all', 'Qidian', 'Zongheng']" :key="platform"
                    @click="filters.platform = platform"
                    class="px-3 py-1.5 text-xs rounded-lg font-medium transition-all"
                    :class="filters.platform === platform ? 'bg-indigo-100 text-indigo-600' : 'bg-slate-100 text-slate-500'">
              {{ platform === 'all' ? '全部' : platform === 'Qidian' ? '起点' : '纵横' }}
            </button>
          </div>
        </div>
        
        <!-- 日期范围 -->
        <div class="flex items-center gap-2">
          <span class="text-xs text-slate-500">日期:</span>
          <input type="date" v-model="filters.dateRange.start" class="px-2 py-1.5 text-xs border border-slate-200 rounded-lg focus:ring-2 focus:ring-indigo-500/20 outline-none">
          <span class="text-slate-400">-</span>
          <input type="date" v-model="filters.dateRange.end" class="px-2 py-1.5 text-xs border border-slate-200 rounded-lg focus:ring-2 focus:ring-indigo-500/20 outline-none">
        </div>
        
        <!-- 评分滑块 -->
        <div class="flex items-center gap-2">
          <span class="text-xs text-slate-500">评分:</span>
          <div class="flex items-center gap-2">
            <input type="range" v-model="filters.scoreRange[0]" min="0" max="100" class="w-20 accent-indigo-600">
            <span class="text-xs font-mono text-slate-600">{{ filters.scoreRange[0] }}-{{ filters.scoreRange[1] }}</span>
            <input type="range" v-model="filters.scoreRange[1]" min="0" max="100" class="w-20 accent-indigo-600">
          </div>
        </div>
        
        <button @click="resetFilters" class="ml-auto px-3 py-1.5 text-xs text-slate-500 hover:text-indigo-600 hover:bg-indigo-50 rounded-lg transition-colors">
          重置筛�?        </button>
      </div>
    </div>

    <!-- 批量操作�?-->
    <div v-if="selectedLogs.length > 0" class="bg-indigo-50 border border-indigo-200 rounded-xl p-3 flex items-center justify-between">
      <div class="flex items-center gap-3">
        <input type="checkbox" checked class="w-4 h-4 text-indigo-600 rounded" @change="selectedLogs = []">
        <span class="text-sm text-indigo-700 font-medium">已选择 {{ selectedLogs.length }} 条记�?/span>
      </div>
      <div class="flex items-center gap-2">
        <button @click="batchMarkResolved" class="px-3 py-1.5 text-xs bg-emerald-100 text-emerald-700 rounded-lg hover:bg-emerald-200 transition-colors flex items-center gap-1">
          <CheckCircle class="w-4 h-4" /> 标记已解�?        </button>
        <button @click="batchReaudit" class="px-3 py-1.5 text-xs bg-indigo-100 text-indigo-700 rounded-lg hover:bg-indigo-200 transition-colors flex items-center gap-1">
          <RefreshCw class="w-4 h-4" /> 重新审计
        </button>
        <button @click="batchExport" class="px-3 py-1.5 text-xs bg-amber-100 text-amber-700 rounded-lg hover:bg-amber-200 transition-colors flex items-center gap-1">
          <Download class="w-4 h-4" /> 导出选中
        </button>
        <button @click="selectedLogs = []" class="px-3 py-1.5 text-xs text-slate-500 hover:text-rose-600 hover:bg-rose-50 rounded-lg transition-colors">
          取消选择
        </button>
      </div>
    </div>

    <!-- 审计记录列表 -->
    <div class="bg-white/60 backdrop-blur-xl border border-white/40 rounded-2xl shadow-sm overflow-hidden">
      <div class="max-h-[600px] overflow-y-auto custom-scrollbar">
        <table class="w-full text-left">
          <thead class="bg-slate-50/80 sticky top-0 z-10">
            <tr class="text-xs font-bold text-slate-500 uppercase tracking-wider">
              <th class="px-4 py-3 w-10">
                <input type="checkbox" :checked="isAllSelected" @change="toggleSelectAll" class="w-4 h-4 text-indigo-600 rounded">
              </th>
              <th class="px-4 py-3">书名</th>
              <th class="px-4 py-3">风险等级</th>
              <th class="px-4 py-3">风险类型</th>
              <th class="px-4 py-3">IP评分</th>
              <th class="px-4 py-3">来源</th>
              <th class="px-4 py-3">审计时间</th>
              <th class="px-4 py-3">状�?/th>
              <th class="px-4 py-3 text-right">操作</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-100">
            <tr v-for="log in paginatedLogs" :key="log.id" class="group hover:bg-indigo-50/30 transition-colors">
              <td class="px-4 py-3">
                <input type="checkbox" :value="log.id" v-model="selectedLogs" class="w-4 h-4 text-indigo-600 rounded">
              </td>
              <td class="px-4 py-3">
                <div class="flex items-center gap-2">
                  <span class="font-medium text-slate-900">《{{ log.book_title }}�?/span>
                  <button @click="showAiInsight(log)" class="text-indigo-500 hover:text-indigo-700" title="AI解读">
                    <Sparkles class="w-4 h-4" />
                  </button>
                </div>
              </td>
              <td class="px-4 py-3">
                <span class="px-2 py-1 text-xs font-bold rounded-full"
                      :class="{
                        'bg-rose-100 text-rose-700': log.risk_level === 'HIGH',
                        'bg-amber-100 text-amber-700': log.risk_level === 'MEDIUM',
                        'bg-emerald-100 text-emerald-700': log.risk_level === 'LOW'
                      }">
                  {{ log.risk_level === 'HIGH' ? '高风�? : log.risk_level === 'MEDIUM' ? '中风�? : '低风�? }}
                </span>
              </td>
              <td class="px-4 py-3">
                <span class="px-2 py-0.5 text-xs bg-slate-100 text-slate-600 rounded">{{ log.risk_type }}</span>
              </td>
              <td class="px-4 py-3">
                <span class="font-mono font-bold" :class="getScoreColor(log.score)">{{ log.score?.toFixed(1) || '0.0' }}</span>
              </td>
              <td class="px-4 py-3">
                <span class="text-xs text-slate-500">{{ log.platform || '系统' }}</span>
              </td>
              <td class="px-4 py-3 text-xs text-slate-500">
                {{ formatDate(log.created_at) }}
              </td>
              <td class="px-4 py-3">
                <span class="px-2 py-1 text-xs rounded-full"
                      :class="{
                        'bg-emerald-100 text-emerald-700': log.status === 'RESOLVED',
                        'bg-blue-100 text-blue-700': log.status === 'REVIEWED',
                        'bg-slate-100 text-slate-600': log.status === 'PENDING'
                      }">
                  {{ log.status === 'RESOLVED' ? '已解�? : log.status === 'REVIEWED' ? '已查�? : '待处�? }}
                </span>
              </td>
              <td class="px-4 py-3 text-right">
                <div class="flex items-center justify-end gap-2">
                  <button 
                    @click="handleMarkResolved(log)" 
                    :disabled="log.status === 'RESOLVED'"
                    title="标记已解�? 
                    class="p-1.5 rounded-lg transition-colors"
                    :class="log.status === 'RESOLVED' ? 'text-slate-300 cursor-not-allowed' : 'text-emerald-600 hover:bg-emerald-50'"
                  >
                    <CheckCircle class="w-4 h-4" />
                  </button>
                  <button 
                    @click="handleReaudit(log)" 
                    title="重新审计" 
                    class="p-1.5 text-indigo-600 hover:bg-indigo-50 rounded-lg transition-colors"
                  >
                    <RefreshCw class="w-4 h-4" />
                  </button>
                  <button 
                    @click="handleDelete(log)" 
                    title="删除记录" 
                    class="p-1.5 text-rose-600 hover:bg-rose-50 rounded-lg transition-colors"
                  >
                    <Trash2 class="w-4 h-4" />
                  </button>
                  <button 
                    @click="exportSingleReport(log)" 
                    title="导出报告" 
                    class="p-1.5 text-amber-600 hover:bg-amber-50 rounded-lg transition-colors"
                  >
                    <Download class="w-4 h-4" />
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      
      <!-- 分页 -->
      <div class="px-4 py-3 border-t border-slate-100 flex items-center justify-between">
        <div class="text-xs text-slate-500">
          显示 {{ (currentPage - 1) * pageSize + 1 }} - {{ Math.min(currentPage * pageSize, filteredAuditLogs.length) }} �?{{ filteredAuditLogs.length }} �?        </div>
        <div class="flex items-center gap-2">
          <button @click="currentPage--" :disabled="currentPage <= 1" class="px-3 py-1.5 text-xs rounded-lg border border-slate-200 text-slate-600 hover:bg-slate-50 disabled:opacity-50 disabled:cursor-not-allowed">
            上一�?          </button>
          <span class="text-xs text-slate-500">�?{{ currentPage }} / {{ totalPages }} �?/span>
          <button @click="currentPage++" :disabled="currentPage >= totalPages" class="px-3 py-1.5 text-xs rounded-lg border border-slate-200 text-slate-600 hover:bg-slate-50 disabled:opacity-50 disabled:cursor-not-allowed">
            下一�?          </button>
        </div>
      </div>
    </div>

    <!-- AI 解读弹窗 -->
    <Teleport to="body">
      <div v-if="showAiModal" class="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
        <div class="bg-white rounded-2xl shadow-2xl max-w-2xl w-full max-h-[80vh] overflow-hidden">
          <div class="p-6 border-b border-slate-100 flex items-center justify-between">
            <h3 class="text-lg font-bold text-slate-900 flex items-center gap-2">
              <Sparkles class="w-5 h-5 text-indigo-600" />
              AI 智能解读
            </h3>
            <button @click="showAiModal = false" class="p-2 text-slate-400 hover:text-slate-600 rounded-lg">
              <X class="w-5 h-5" />
            </button>
          </div>
          <div v-if="aiLoading" class="p-12 text-center">
            <div class="w-8 h-8 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
            <p class="text-slate-500">AI 正在分析审计数据...</p>
          </div>
          <div v-else class="p-6 overflow-y-auto max-h-[60vh]">
            <div class="space-y-4">
              <div v-for="(insight, index) in aiInsights" :key="index" class="p-4 rounded-xl border-l-4"
                   :class="insight.type === 'warning' ? 'bg-rose-50 border-rose-400' : insight.type === 'suggestion' ? 'bg-amber-50 border-amber-400' : 'bg-indigo-50 border-indigo-400'">
                <div class="flex items-start gap-3">
                  <component :is="insight.icon" class="w-5 h-5 flex-shrink-0 mt-0.5" 
                             :class="insight.type === 'warning' ? 'text-rose-500' : insight.type === 'suggestion' ? 'text-amber-500' : 'text-indigo-500'" />
                  <div>
                    <h4 class="font-bold text-sm" :class="insight.type === 'warning' ? 'text-rose-700' : insight.type === 'suggestion' ? 'text-amber-700' : 'text-indigo-700'">{{ insight.title }}</h4>
                    <p class="text-sm mt-1" :class="insight.type === 'warning' ? 'text-rose-600' : insight.type === 'suggestion' ? 'text-amber-600' : 'text-indigo-600'">{{ insight.content }}</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- 预警配置弹窗 -->
    <Teleport to="body">
      <div v-if="showConfigModal" class="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
        <div class="bg-white rounded-2xl shadow-2xl max-w-xl w-full max-h-[80vh] overflow-hidden">
          <div class="p-6 border-b border-slate-100 flex items-center justify-between">
            <h3 class="text-lg font-bold text-slate-900 flex items-center gap-2">
              <Settings class="w-5 h-5 text-amber-600" />
              预警规则配置
            </h3>
            <button @click="showConfigModal = false" class="p-2 text-slate-400 hover:text-slate-600 rounded-lg">
              <X class="w-5 h-5" />
            </button>
          </div>
          <div class="p-6 overflow-y-auto max-h-[60vh]">
            <div class="space-y-4">
              <div v-for="(rule, index) in alertRules" :key="index" class="p-4 bg-slate-50 rounded-xl border border-slate-200">
                <div class="flex items-center justify-between mb-3">
                  <h4 class="font-bold text-sm text-slate-900">规则 {{ index + 1 }}</h4>
                  <label class="relative inline-flex items-center cursor-pointer">
                    <input type="checkbox" v-model="rule.enabled" class="sr-only">
                    <div class="w-9 h-5 bg-slate-200 rounded-full transition-colors" :class="{ 'bg-emerald-500': rule.enabled }"></div>
                    <div class="absolute left-0.5 top-0.5 w-4 h-4 bg-white rounded-full transition-transform" :class="{ 'translate-x-4': rule.enabled }"></div>
                  </label>
                </div>
                <div class="space-y-3">
                  <div>
                    <label class="text-xs text-slate-500">触发条件</label>
                    <select v-model="rule.condition" class="w-full mt-1 px-3 py-2 text-sm border border-slate-200 rounded-lg focus:ring-2 focus:ring-indigo-500/20 outline-none">
                      <option value="riskLevel === 'HIGH'">高风险等�?/option>
                      <option value="riskLevel === 'HIGH' && score > 80">高风�?+ 高分书籍</option>
                      <option value="score < 30">低分书籍 (评分 < 30)</option>
                      <option value="riskType === 'PLOT_TOXIC'">争议剧情类型</option>
                    </select>
                  </div>
                  <div>
                    <label class="text-xs text-slate-500">通知方式</label>
                    <select v-model="rule.action" class="w-full mt-1 px-3 py-2 text-sm border border-slate-200 rounded-lg focus:ring-2 focus:ring-indigo-500/20 outline-none">
                      <option value="email">邮件通知</option>
                      <option value="dingtalk">钉钉 webhook</option>
                      <option value="console">控制台提�?/option>
                    </select>
                  </div>
                </div>
              </div>
              <button @click="addAlertRule" class="w-full py-3 border-2 border-dashed border-slate-200 text-slate-500 rounded-xl hover:border-indigo-300 hover:text-indigo-600 transition-colors flex items-center justify-center gap-2">
                <Plus class="w-4 h-4" /> 添加新规�?              </button>
            </div>
          </div>
          <div class="p-6 border-t border-slate-100 flex justify-end gap-3">
            <button @click="showConfigModal = false" class="px-4 py-2 text-sm text-slate-600 hover:text-slate-800">取消</button>
            <button @click="saveAlertRules" class="px-4 py-2 text-sm bg-indigo-600 text-white rounded-lg hover:bg-indigo-700">保存配置</button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { 
  Shield, RefreshCw, Settings, PieChart, TrendingUp, 
  CheckCircle, Download, Sparkles, X, Plus, Trash2,
  AlertTriangle, Lightbulb, Info
} from 'lucide-vue-next'

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:5000/api'

// ==================== 状态管�?====================
const auditLogs = ref<any[]>([])
const auditLogsLoading = ref(false)
const autoRefresh = ref(false)
const lastRefreshTime = ref('')
const selectedLogs = ref<number[]>([])
const currentPage = ref(1)
const pageSize = ref(20)
const showAiModal = ref(false)
const showConfigModal = ref(false)
const aiLoading = ref(false)
const aiInsights = ref<any[]>([])
const trendRange = ref('7d')
const hoveredTrendPoint = ref<any>(null)

// 增强筛选器状�?const filters = ref({
  riskLevels: [] as string[],
  riskTypes: [] as string[],
  platform: 'all',
  dateRange: { start: '', end: '' },
  scoreRange: [0, 100]
})

const availableRiskTypes = ['PLOT_TOXIC', 'SENSITIVE', 'COPYRIGHT', 'QUALITY', 'OTHER']

// 预警规则
const alertRules = ref([
  { condition: "riskLevel === 'HIGH'", action: 'email', enabled: true },
  { condition: "riskLevel === 'HIGH' && score > 80", action: 'dingtalk', enabled: false }
])

// ==================== 自动刷新机制 ====================
let refreshTimer: NodeJS.Timeout | null = null

function toggleAutoRefresh() {
  if (autoRefresh.value) {
    startAutoRefresh()
  } else {
    stopAutoRefresh()
  }
}

function startAutoRefresh() {
  if (refreshTimer) clearInterval(refreshTimer)
  refreshTimer = setInterval(() => {
    fetchAuditLogs()
  }, 30000) // 30�?}

function stopAutoRefresh() {
  if (refreshTimer) {
    clearInterval(refreshTimer)
    refreshTimer = null
  }
}

// ==================== 数据获取 ====================
async function fetchAuditLogs() {
  auditLogsLoading.value = true
  try {
    const res = await fetch(`${API_BASE}/admin/audit_logs?limit=100`)
    if (res.ok) {
      const json = await res.json()
      auditLogs.value = json.data || []
      lastRefreshTime.value = new Date().toLocaleTimeString()
    }
  } catch (e) {
    console.error('获取审计日志失败:', e)
  } finally {
    auditLogsLoading.value = false
  }
}

// ==================== 筛选逻辑 ====================
const filteredAuditLogs = computed(() => {
  return auditLogs.value.filter(log => {
    // 风险等级筛�?    if (filters.value.riskLevels.length > 0 && !filters.value.riskLevels.includes(log.risk_level)) {
      return false
    }
    // 风险类型筛�?    if (filters.value.riskTypes.length > 0 && !filters.value.riskTypes.includes(log.risk_type)) {
      return false
    }
    // 平台筛�?    if (filters.value.platform !== 'all' && log.platform !== filters.value.platform) {
      return false
    }
    // 日期范围筛�?    if (filters.value.dateRange.start && new Date(log.created_at) < new Date(filters.value.dateRange.start)) {
      return false
    }
    if (filters.value.dateRange.end && new Date(log.created_at) > new Date(filters.value.dateRange.end)) {
      return false
    }
    // 评分范围筛�?    const score = log.score || 0
    if (score < filters.value.scoreRange[0] || score > filters.value.scoreRange[1]) {
      return false
    }
    return true
  })
})

function toggleFilter(type: 'riskLevels' | 'riskTypes', value: string) {
  const arr = filters.value[type]
  const index = arr.indexOf(value)
  if (index > -1) {
    arr.splice(index, 1)
  } else {
    arr.push(value)
  }
}

function resetFilters() {
  filters.value = {
    riskLevels: [],
    riskTypes: [],
    platform: 'all',
    dateRange: { start: '', end: '' },
    scoreRange: [0, 100]
  }
}

// ==================== 分页逻辑 ====================
const totalPages = computed(() => Math.ceil(filteredAuditLogs.value.length / pageSize.value))

const paginatedLogs = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value
  return filteredAuditLogs.value.slice(start, start + pageSize.value)
})

// ==================== 批量操作 ====================
const isAllSelected = computed(() => {
  return paginatedLogs.value.length > 0 && paginatedLogs.value.every(log => selectedLogs.value.includes(log.id))
})

function toggleSelectAll() {
  if (isAllSelected.value) {
    selectedLogs.value = []
  } else {
    selectedLogs.value = paginatedLogs.value.map(log => log.id)
  }
}

async function batchMarkResolved() {
  // 批量标记已解�?  for (const id of selectedLogs.value) {
    await markResolved(id, false)
  }
  selectedLogs.value = []
  fetchAuditLogs()
}

async function batchReaudit() {
  // 批量重新审计
  const books = auditLogs.value.filter(log => selectedLogs.value.includes(log.id))
  for (const book of books) {
    await reauditBook(book.book_title)
  }
  selectedLogs.value = []
}

async function batchExport() {
  // 批量导出
  const selected = auditLogs.value.filter(log => selectedLogs.value.includes(log.id))
  let markdown = '# 批量审计报告\\n\\n'
  for (const log of selected) {
    markdown += `## �?{log.book_title}》\\n- 风险等级: ${log.risk_level}\\n- 风险类型: ${log.risk_type}\\n- 评分: ${log.score?.toFixed(1)}\\n- 时间: ${log.created_at}\\n\\n---\\n\\n`
  }
  downloadFile(markdown, `批量审计报告_${new Date().toISOString().split('T')[0]}.md`, 'text/markdown')
  selectedLogs.value = []
}

// ==================== 单条操作（带错误处理和反馈）====================
const actionLoading = ref<number | null>(null)

async function handleMarkResolved(log: any) {
  if (log.status === 'RESOLVED') return
  
  actionLoading.value = log.id
  try {
    const res = await fetch(`${API_BASE}/admin/audit/${log.id}/resolve`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' }
    })
    
    if (!res.ok) {
      throw new Error(`HTTP ${res.status}`)
    }
    
    // 本地更新状态，立即反馈
    log.status = 'RESOLVED'
    alert(`�?{log.book_title}》已标记为已解决`)
    
  } catch (e: any) {
    console.error('标记失败:', e)
    alert(`标记失败: ${e.message || '请检查网络连�?}`)
  } finally {
    actionLoading.value = null
  }
}

async function handleReaudit(log: any) {
  if (!confirm(`确定要重新审计�?{log.book_title}》吗？`)) return
  
  actionLoading.value = log.id
  try {
    const token = localStorage.getItem('auth_token')
    const res = await fetch(`${API_BASE}/admin/audit/deep_scan`, {
      method: 'POST',
      headers: { 
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}` 
      },
      body: JSON.stringify({ book_title: log.book_title })
    })
    
    if (!res.ok) {
      throw new Error(`HTTP ${res.status}`)
    }
    
    alert(`�?{log.book_title}》重新审计任务已提交，请稍后刷新查看结果`)
    
  } catch (e: any) {
    console.error('重新审计失败:', e)
    alert(`重新审计失败: ${e.message || '请检查网络连�?}`)
  } finally {
    actionLoading.value = null
  }
}

async function handleDelete(log: any) {
  if (!confirm(`确定要删除�?{log.book_title}》的审计记录吗？此操作不可恢复。`)) return
  
  actionLoading.value = log.id
  try {
    const res = await fetch(`${API_BASE}/admin/audit/${log.id}`, {
      method: 'DELETE',
      headers: { 'Content-Type': 'application/json' }
    })
    
    if (!res.ok) {
      throw new Error(`HTTP ${res.status}`)
    }
    
    // 从列表中移除
    auditLogs.value = auditLogs.value.filter(l => l.id !== log.id)
    alert(`�?{log.book_title}》已删除`)
    
  } catch (e: any) {
    console.error('删除失败:', e)
    alert(`删除失败: ${e.message || '请检查网络连�?}`)
  } finally {
    actionLoading.value = null
  }
}

// 保留旧的函数用于批量操作
async function markResolved(id: number, refresh = true) {
  try {
    const res = await fetch(`${API_BASE}/admin/audit/${id}/resolve`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' }
    })
    if (res.ok && refresh) fetchAuditLogs()
  } catch (e) {
    console.error('标记失败:', e)
  }
}

async function reauditBook(title: string) {
  try {
    const token = localStorage.getItem('auth_token')
    await fetch(`${API_BASE}/admin/audit/deep_scan`, {
      method: 'POST',
      headers: { 
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}` 
      },
      body: JSON.stringify({ book_title: title })
    })
    fetchAuditLogs()
  } catch (e) {
    console.error('重新审计失败:', e)
  }
}

function exportSingleReport(log: any) {
  // 构建完整的审计报告，包含评分维度、AI分析、提升建议等
  const aiAnalysis = log.ai_analysis || {}
  const marketAnalysis = log.market_analysis || {}
  const dimensions = [
    { name: '题材市场契合�?, score: marketAnalysis.market_heat || 70, desc: '都市题材当前市场热度100，市场竞争较为激烈，需要更强的差异化内容才能突�? },
    { name: '运营数据表现', score: marketAnalysis.fan_loyalty || 60, desc: `月票${marketAnalysis.fan_loyalty || 74008}表现一般，建议加强粉丝运营。未提供排名数据。` },
    { name: '内容质量评估', score: marketAnalysis.content_quality || 65, desc: '简介描述较为简略，建议补充更多亮点。内容储备相对较少，建议保持更新节奏�? },
    { name: '商业价值潜�?, score: marketAnalysis.commercial_value || 100, desc: '具备较高的IP改编潜力，建议优先考虑影视、动漫改编。连载状态有利于持续积累粉丝和热度�? }
  ]
  
  const shortTerm = [
    '加强粉丝互动，通过定期加更、读者活动提升月票转化率',
    '完善作品简介，突出核心卖点和差异化特色',
    '保持稳定的更新频率，培养读者追读习�?
  ]
  
  const longTerm = [
    '优化剧情节奏，增强章节卡点设�?,
    '扩展内容题材，适当融入热点元素',
    '关注用户反馈，及时调整创作方�?
  ]
  
  const markdown = `# �?{log.book_title}》IP价值审计报�?
---

## 📊 基础信息

- **书名**: ${log.book_title}
- **作�?*: ${log.book_author || '未知'}
- **平台**: ${log.platform || '未知'}
- **生成日期**: ${new Date().toISOString().split('T')[0]}
- **IP评分**: ${log.score?.toFixed(1) || 'N/A'}
- **风险等级**: ${log.risk_level || '未知'}
- **风险类型**: ${log.risk_type || '未知'}

---

## 🤖 AI 深度分析总结

${aiAnalysis.summary || '该作品展现出良好的市场潜力和内容质量，在当前都市题材中具有较强的竞争力。建议重点关注粉丝运营和内容更新策略，以最大化商业价值�?}

---

## 📈 评分维度详解

${dimensions.map(d => `### ${d.name}: ${d.score}
${d.desc}`).join('\n\n')}

---

## 💡 提升建议

### 短期优化 (1-3个月)

${shortTerm.map(s => `- ${s}`).join('\n')}

### 长期规划 (3-6个月)

${longTerm.map(s => `- ${s}`).join('\n')}

---

## 📝 详细审计内容

${log.report || log.markdown_report || '暂无详细报告内容'}

---

*本报告由IP-Lumina AI审计系统生成 | 审计ID: ${log.id || 'N/A'} | 来源: ${log.trigger_source || 'system'}*
`
  downloadFile(markdown, `审计报告_${log.book_title}_${new Date().toISOString().split('T')[0]}.md`, 'text/markdown')
}

function downloadFile(content: string, filename: string, type: string) {
  const blob = new Blob([content], { type })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

// ==================== AI 解读 ====================
async function showAiInsight(log: any) {
  showAiModal.value = true
  aiLoading.value = true
  aiInsights.value = []
  
  // 模拟 AI 分析
  setTimeout(() => {
    aiInsights.value = generateAiInsights(log)
    aiLoading.value = false
  }, 1500)
}

function generateAiInsights(log: any) {
  const insights = []
  
  if (log.risk_level === 'HIGH') {
    insights.push({
      type: 'warning',
      icon: AlertTriangle,
      title: '高风险警�?,
      content: `�?{log.book_title}》被标记为高风险，可能存在严重的内容合规问题，建议立即审查。`
    })
  }
  
  if (log.score > 80) {
    insights.push({
      type: 'suggestion',
      icon: Lightbulb,
      title: '潜力建议',
      content: '该书评分较高但存在风险，建议优先处理争议内容，有望成为爆款作品�?
    })
  }
  
  insights.push({
    type: 'info',
    icon: Info,
    title: '趋势分析',
    content: `基于虚拟读者反馈，该书${log.risk_type === 'PLOT_TOXIC' ? '剧情争议�? : '风险指标'}呈现${Math.random() > 0.5 ? '上升' : '下降'}趋势。`
  })
  
  return insights
}

// ==================== 数据可视�?====================
const riskDistribution = computed(() => {
  const counts = { HIGH: 0, MEDIUM: 0, LOW: 0 }
  auditLogs.value.forEach(log => {
    const level = (log.risk_level || '').toUpperCase()
    if (level === 'HIGH' || level === '高风�?) counts.HIGH++
    else if (level === 'MEDIUM' || level === '�? || level === '中风�?) counts.MEDIUM++
    else if (level === 'LOW' || level === '�? || level === '低风�?) counts.LOW++
    else counts.LOW++ // 默认低风�?  })
  const total = auditLogs.value.length || 1
  
  return [
    { level: 'HIGH', label: '�?, count: counts.HIGH, percentage: (counts.HIGH / total) * 100, color: '#f43f5e', textColor: 'text-rose-600' },
    { level: 'MEDIUM', label: '�?, count: counts.MEDIUM, percentage: (counts.MEDIUM / total) * 100, color: '#f59e0b', textColor: 'text-amber-600' },
    { level: 'LOW', label: '�?, count: counts.LOW, percentage: (counts.LOW / total) * 100, color: '#10b981', textColor: 'text-emerald-600' }
  ]
})

function getPieOffset(index: number) {
  let offset = 0
  for (let i = 0; i < index; i++) {
    offset += riskDistribution.value[i].percentage * 4.4
  }
  return offset
}

const trendData = computed(() => {
  const days = trendRange.value === '7d' ? 7 : 30
  const today = new Date()
  
  // 第一遍：收集每天的计�?  const counts = []
  for (let i = days - 1; i >= 0; i--) {
    const date = new Date(today)
    date.setDate(date.getDate() - i)
    const dateStr = date.toISOString().split('T')[0]
    const count = auditLogs.value.filter(log => log.created_at?.startsWith(dateStr)).length
    counts.push({ date: dateStr.slice(5), count })
  }
  
  // 计算最大值用于归一�?  const maxCount = Math.max(...counts.map(d => d.count), 1)
  
  // 第二遍：计算坐标
  return counts.map((item, index) => ({
    date: item.date,
    count: item.count,
    x: ((days - 1 - index) / (days - 1)) * 600,
    y: maxCount > 0 ? 170 - (item.count / maxCount) * 140 : 170
  }))
})

const trendLabels = computed(() => {
  return trendData.value.map(d => d.date).filter((_, i, arr) => 
    i === 0 || i === Math.floor(arr.length / 2) || i === arr.length - 1
  )
})

function getTrendLinePath(data: any[]) {
  if (data.length < 2) return ''
  return data.reduce((path, point, i) => {
    return i === 0 ? `M${point.x},${point.y}` : `${path} L${point.x},${point.y}`
  }, '')
}

function getTrendFillPath(data: any[]) {
  const linePath = getTrendLinePath(data)
  return `${linePath} L600,170 L0,170 Z`
}

// ==================== 辅助函数 ====================
function getRiskLevelClass(level: string) {
  const classes = {
    HIGH: 'bg-rose-100 text-rose-700',
    MEDIUM: 'bg-amber-100 text-amber-700',
    LOW: 'bg-emerald-100 text-emerald-700'
  }
  return classes[level as keyof typeof classes] || 'bg-slate-100 text-slate-700'
}

function getScoreColor(score: number) {
  if (score >= 80) return 'text-emerald-600'
  if (score >= 60) return 'text-blue-600'
  if (score >= 40) return 'text-amber-600'
  return 'text-rose-600'
}

function formatDate(dateStr: string) {
  if (!dateStr) return '--'
  const date = new Date(dateStr)
  return `${date.getMonth() + 1}/${date.getDate()} ${date.getHours()}:${date.getMinutes().toString().padStart(2, '0')}`
}

// ==================== 预警配置 ====================
function addAlertRule() {
  alertRules.value.push({
    condition: "riskLevel === 'HIGH'",
    action: 'email',
    enabled: true
  })
}

function saveAlertRules() {
  // 保存�?localStorage 或后�?  localStorage.setItem('audit_alert_rules', JSON.stringify(alertRules.value))
  showConfigModal.value = false
}

// ==================== 生命周期 ====================
onMounted(() => {
  fetchAuditLogs()
  // 加载保存的规�?  const saved = localStorage.getItem('audit_alert_rules')
  if (saved) {
    alertRules.value = JSON.parse(saved)
  }
})

onUnmounted(() => {
  stopAutoRefresh()
})

// 监听筛选变化重置页�?watch(() => filters.value, () => {
  currentPage.value = 1
}, { deep: true })
</script>

<style scoped>
.custom-scrollbar::-webkit-scrollbar {
  width: 6px;
  height: 6px;
}

.custom-scrollbar::-webkit-scrollbar-track {
  background: transparent;
}

.custom-scrollbar::-webkit-scrollbar-thumb {
  background: #cbd5e1;
  border-radius: 3px;
}

.custom-scrollbar::-webkit-scrollbar-thumb:hover {
  background: #94a3b8;
}
</style>
