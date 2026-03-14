<script setup lang="ts">
import { ref, onMounted, watch, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import EditorialLayout from '@/components/layout/EditorialLayout.vue'
import { Search, Filter, ChevronLeft, ChevronRight, ChevronsLeft, ChevronsRight, BookOpen, BarChart2, Hash, Layers } from 'lucide-vue-next'

const router = useRouter()
const route = useRoute()

// Filters
const searchQuery = ref('')
const selectedCategory = ref('全部题材')
const selectedPlatform = ref('全部平台')
const selectedStatus = ref('全部状态')
const selectedYear = ref('全部年份')
const selectedMonth = ref('全部月份')
const currentPage = ref(1)

// Data state
const books = ref<any[]>([])
const totalBooks = ref(0)
const totalPages = ref(1)
const isLoading = ref(false)

// Options (Can be fetched from API later)
const categories = ['全部题材', '玄幻', '都市', '仙侠', '科幻', '历史', '游戏', '奇幻']
const platforms = ['全部平台', '起点', '纵横']
const statuses = ['全部状态', '连载', '完结']
// 2020 - 2025
const years = ['全部年份', ...Array.from({length: 6}, (_, i) => (2025 - i).toString())]
const months = ['全部月份', ...Array.from({length: 12}, (_, i) => (i + 1).toString())]

// Gradient Generator for Covers
const getGradient = (str: string) => {
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    hash = str.charCodeAt(i) + ((hash << 5) - hash);
  }
  const c1 = `hsl(${hash % 360}, 70%, 85%)`;
  const c2 = `hsl(${(hash + 120) % 360}, 60%, 75%)`;
  return `linear-gradient(135deg, ${c1}, ${c2})`;
}

// Fetch Data
const fetchLibrary = async () => {
  isLoading.value = true
  try {
    const params = new URLSearchParams({
      page: currentPage.value.toString(),
      pageSize: '12',
      search: searchQuery.value,
      category: selectedCategory.value === '全部题材' ? '' : selectedCategory.value,
      platform: selectedPlatform.value === '全部平台' ? '' : selectedPlatform.value,
      status: selectedStatus.value === '全部状态' ? '' : selectedStatus.value,
      year: selectedYear.value === '全部年份' ? '' : selectedYear.value,
      month: selectedMonth.value === '全部月份' ? '' : selectedMonth.value
    })

    const res = await fetch(`http://localhost:5000/api/library/list?${params}`)
    const data = await res.json()
    
    if (data.error) throw new Error(data.error)
    
    books.value = data.items
    totalBooks.value = data.total
    totalPages.value = data.total_pages
  } catch (err) {
    console.error("Library Fetch Error:", err)
    // Fallback Mock if API fails (Dev Mode)
    // books.value = [] 
  } finally {
    isLoading.value = false
  }
}

// Watchers for refetch
watch([selectedCategory, selectedPlatform, selectedStatus, selectedYear, selectedMonth], () => {
  currentPage.value = 1
  fetchLibrary()
})

watch(currentPage, () => {
  fetchLibrary()
})

// Debounced Search
let debounceTimer: number
watch(searchQuery, () => {
  clearTimeout(debounceTimer)
  debounceTimer = setTimeout(() => {
    currentPage.value = 1
    fetchLibrary()
  }, 500)
})

onMounted(() => {
  // 从 URL query 恢复筛选状态（支持从详情页返回时保留筛选）
  const q = route.query
  if (q.search) searchQuery.value = q.search as string
  if (q.category) selectedCategory.value = q.category as string
  if (q.platform) selectedPlatform.value = q.platform as string
  if (q.status) selectedStatus.value = q.status as string
  if (q.year) selectedYear.value = q.year as string
  if (q.month) selectedMonth.value = q.month as string
  if (q.page) currentPage.value = parseInt(q.page as string) || 1
  fetchLibrary()
})

import { Sparkles } from 'lucide-vue-next'
import AIReportModal from '@/components/ai/AIReportModal.vue'

// ... existing code ...

const showAIReport = ref(false)
const selectedBook = ref<any>(null)

const openAIReport = (book: any) => {
  selectedBook.value = book
  showAIReport.value = true
}

// 构建当前筛选状态的 query 对象，在跳转到详情页时一并携带
const buildFilterQuery = () => {
  const q: Record<string, string> = {}
  if (searchQuery.value) q.f_search = searchQuery.value
  if (selectedCategory.value !== '全部题材') q.f_category = selectedCategory.value
  if (selectedPlatform.value !== '全部平台') q.f_platform = selectedPlatform.value
  if (selectedStatus.value !== '全部状态') q.f_status = selectedStatus.value
  if (selectedYear.value !== '全部年份') q.f_year = selectedYear.value
  if (selectedMonth.value !== '全部月份') q.f_month = selectedMonth.value
  if (currentPage.value > 1) q.f_page = currentPage.value.toString()
  return q
}

const navigateToDetail = (book: any) => {
  const token = localStorage.getItem('auth_token')
  let isAdmin = false
  if(token) {
    try {
      const parts = (token as string).split('.')
      if (parts.length >= 2 && parts[1]) {
        const payload = JSON.parse(atob(parts[1]))
        isAdmin = payload.role === 'admin'
      }
    } catch {}
  }
  
  const filterQ = buildFilterQuery()
  
  if (isAdmin) {
    router.push({ path: '/admin/book/detail', query: { title: book.title, author: book.author, platform: book.platform, ...filterQ } })
  } else {
    router.push({ path: '/library/detail', query: { title: book.title, author: book.author, platform: book.platform, ...filterQ } })
  }
}

const navigateToReader = (book: any) => {
  // Pass book data to Reader Space via Query or Store
  router.push({ 
    path: '/reader-space', 
    query: { 
      bookTitle: book.title, 
      bookId: book.id || 'mock' 
    } 
  })
}
</script>

<template>
  <EditorialLayout>
    <div class="min-h-screen pt-8 px-8 pb-24 max-w-[1920px] mx-auto flex flex-col gap-8">
      
      <!-- Header -->
      <div class="flex flex-col gap-2">
        <h1 class="text-4xl font-serif font-bold text-slate-900 tracking-tight">作品库</h1>
        <p class="text-slate-500 text-lg">收录全平台 {{ totalBooks }} 部网络文学作品，一键开启虚拟读者模拟</p>
      </div>

      <!-- Filter Bar -->
      <div class="bg-white rounded-2xl p-4 shadow-sm border border-slate-200 flex flex-wrap gap-4 items-center justify-between sticky top-4 z-30 backdrop-blur-xl bg-white/90">
        <!-- Search -->
        <div class="relative flex-1 min-w-[300px] max-w-xl group">
          <Search class="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400 group-focus-within:text-indigo-500 transition-colors" />
          <input 
            v-model="searchQuery"
            type="text" 
            placeholder="搜索作品名称或作者..." 
            class="w-full pl-12 pr-4 py-3 bg-slate-50 border border-slate-200 rounded-xl text-slate-700 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all font-medium"
          >
        </div>
        
        <!-- Dropdowns -->
        <div class="flex items-center gap-3 flex-wrap">
          <!-- Calendar/Date Selectors -->
           <div class="relative">
             <select v-model="selectedYear" class="appearance-none pl-4 pr-8 py-3 bg-slate-50 border border-slate-200 rounded-xl text-sm font-bold text-slate-700 hover:border-indigo-300 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 transition-all cursor-pointer min-w-[100px]">
                <option v-for="y in years" :key="y" :value="y">{{ y }}</option>
             </select>
             <div class="absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none text-xs text-slate-400">年</div>
          </div>
          
           <div class="relative">
             <select v-model="selectedMonth" class="appearance-none pl-4 pr-8 py-3 bg-slate-50 border border-slate-200 rounded-xl text-sm font-bold text-slate-700 hover:border-indigo-300 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 transition-all cursor-pointer min-w-[80px]">
                <option v-for="m in months" :key="m" :value="m">{{ m }}</option>
             </select>
             <div class="absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none text-xs text-slate-400">月</div>
          </div>

          <div class="h-8 w-px bg-slate-200 mx-1"></div>

          <div class="relative">
             <select v-model="selectedCategory" class="appearance-none pl-4 pr-10 py-3 bg-white border border-slate-200 rounded-xl text-sm font-medium text-slate-700 hover:border-indigo-300 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 transition-all cursor-pointer">
                <option v-for="c in categories" :key="c" :value="c">{{ c }}</option>
             </select>
             <Filter class="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 pointer-events-none" />
          </div>

          <div class="relative">
             <select v-model="selectedPlatform" class="appearance-none pl-4 pr-10 py-3 bg-white border border-slate-200 rounded-xl text-sm font-medium text-slate-700 hover:border-indigo-300 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 transition-all cursor-pointer">
                <option v-for="p in platforms" :key="p" :value="p">{{ p }}</option>
             </select>
             <Layers class="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 pointer-events-none" />
          </div>

          <div class="relative">
             <select v-model="selectedStatus" class="appearance-none pl-4 pr-10 py-3 bg-white border border-slate-200 rounded-xl text-sm font-medium text-slate-700 hover:border-indigo-300 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 transition-all cursor-pointer">
                <option v-for="s in statuses" :key="s" :value="s">{{ s }}</option>
             </select>
             <Hash class="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 pointer-events-none" />
          </div>
          
          <button 
             @click="searchQuery='';selectedCategory='全部题材';selectedPlatform='全部平台';selectedStatus='全部状态';selectedYear='全部年份';selectedMonth='全部月份';currentPage=1"
             class="px-4 py-3 text-sm font-medium text-slate-500 hover:text-red-500 hover:bg-red-50 rounded-xl transition-colors ml-2"
          >
            清除筛选
          </button>
        </div>
      </div>

      <!-- Book Grid -->
      <div v-if="isLoading" class="flex items-center justify-center py-20">
         <div class="flex flex-col items-center gap-3">
           <div class="w-10 h-10 border-4 border-indigo-200 border-t-indigo-600 rounded-full animate-spin"></div>
           <span class="text-slate-400 text-sm font-medium">正在加载书库...</span>
         </div>
      </div>
      
      <div v-else-if="books.length === 0" class="flex flex-col items-center justify-center py-20 text-slate-400">
         <BookOpen class="w-16 h-16 mb-4 opacity-20" />
         <p class="text-lg font-medium">未找到相关作品</p>
         <p class="text-sm opacity-60">尝试更换关键词或筛选条件</p>
      </div>

      <div v-else class="flex flex-col gap-4">
        <div 
          v-for="(book, index) in books" 
          :key="index"
          class="group bg-white rounded-xl border border-slate-200 p-4 hover:border-indigo-300 hover:shadow-md transition-all duration-300 flex gap-6 relative"
        >
           <!-- Rank Badge (Top 3 colored) -->
           <div 
             class="absolute -top-1 -left-1 w-8 h-8 flex items-center justify-center text-white font-bold font-serif italic text-sm z-20 shadow-md"
             :class="[
                (currentPage - 1) * 12 + index + 1 === 1 ? 'bg-red-500 rounded-br-lg rounded-tl-lg' :
                (currentPage - 1) * 12 + index + 1 === 2 ? 'bg-orange-500 rounded-br-lg rounded-tl-lg' :
                (currentPage - 1) * 12 + index + 1 === 3 ? 'bg-amber-500 rounded-br-lg rounded-tl-lg' :
                'bg-slate-400/80 rounded-br-lg rounded-tl-lg text-xs w-6 h-6'
             ]"
           >
             {{ (currentPage - 1) * 12 + index + 1 }}
           </div>

           <!-- Cover (Real or Procedural) -->
           <div 
             class="w-28 h-36 flex-shrink-0 rounded shadow-sm relative overflow-hidden flex items-center justify-center p-0 text-center cursor-pointer group-hover:scale-105 transition-transform duration-500"
             :style="!book.cover_url ? { background: getGradient(book.title) } : {}"
             @click="navigateToDetail(book)"
           >
              <template v-if="book.cover_url">
                <img :src="book.cover_url" :alt="book.title" class="w-full h-full object-cover" @error="book.cover_url = ''" />
                <div class="absolute bottom-1 right-1 px-1.5 py-0.5 bg-black/60 backdrop-blur rounded-[2px] text-[8px] font-bold text-white uppercase tracking-widest z-20">
                   {{ book.platform === 'Qidian' ? 'QD' : 'ZH' }}
                </div>
              </template>
              <template v-else>
                <!-- Noise Texture -->
                <div class="absolute inset-0 opacity-20 bg-repeat bg-[url('data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSI0IiBoZWlnaHQ9IjQiPgo8cmVjdCB3aWR0aD0iNCIgaGVpZ2h0PSI0IiBmaWxsPSIjZmZmIi8+CjxyZWN0IHdpZHRoPSIxIiBoZWlnaHQ9IjEiIGZpbGw9IiMwMDAiIG9wYWNpdHk9IjAuMSIvPgo8L3N2Zz4=')]"></div>
                
                <h3 class="font-serif font-bold text-slate-800 text-sm leading-tight drop-shadow-sm z-10 line-clamp-3 p-3">
                  {{ book.title }}
                </h3>
                
                <div class="absolute bottom-1 right-1 px-1.5 py-0.5 bg-white/40 backdrop-blur rounded-[2px] text-[8px] font-bold text-slate-700 uppercase tracking-widest z-20">
                   {{ book.platform === 'Qidian' ? 'QD' : 'ZH' }}
                </div>
              </template>
           </div>

           <!-- Content Middle -->
           <div class="flex-1 flex flex-col min-w-0 py-1">
              <div class="flex items-baseline justify-between mb-2">
                 <h2 
                   @click="navigateToDetail(book)"
                   class="text-xl font-bold text-slate-900 group-hover:text-indigo-600 cursor-pointer transition-colors truncate pr-4"
                 >
                   {{ book.title }}
                 </h2>
                 
                 <!-- Right Top: IP 价值评分 -->
                 <div class="text-right flex-shrink-0">
                    <span 
                      class="text-2xl font-bold" 
                      :class="book.ip_score >= 80 ? 'text-emerald-600' : book.ip_score >= 60 ? 'text-amber-600' : 'text-slate-600'"
                      style="font-family: 'Times New Roman', 'FangZhengShuSong', 'STSong', serif;"
                    >
                      {{ book.ip_score || '--' }}
                    </span>
                    <span class="text-xs text-slate-400 ml-1">IP Score</span>
                    <div class="text-xs mt-0.5">
                      <span 
                        class="font-bold px-1.5 py-0.5 rounded"
                        :class="(book.ai_grade || '').startsWith('A') ? 'bg-emerald-50 text-emerald-700' : (book.ai_grade || '').startsWith('B') ? 'bg-amber-50 text-amber-700' : 'bg-slate-50 text-slate-600'"
                      >{{ book.ai_grade || '--' }}</span>
                    </div>
                 </div>
              </div>

              <!-- Metadata Row -->
              <div class="flex items-center gap-3 text-sm text-slate-500 mb-3">
                 <span class="flex items-center gap-1.5">
                    <div class="w-5 h-5 rounded-full bg-slate-100 flex items-center justify-center text-[10px]">
                      👤
                    </div>
                    {{ book.author }}
                 </span>
                 <span class="w-px h-3 bg-slate-300"></span>
                 <span 
                    class="px-2 py-0.5 text-xs font-bold rounded"
                    :class="book.platform === 'Qidian' ? 'bg-red-50 text-red-600 border border-red-200/50' : 'bg-slate-800 text-white border border-slate-700'"
                 >
                    {{ book.platform === 'Qidian' ? '起点' : book.platform === 'Zongheng' ? '纵横' : book.platform || '全平台' }}
                 </span>
                 <span class="w-px h-3 bg-slate-300"></span>
                 <span>{{ book.category }}</span> 
                 <span class="w-px h-3 bg-slate-300"></span>
                 <span :class="book.status === '连载' ? 'text-red-500' : 'text-emerald-600'">{{ book.status }}</span>
                 <span class="w-px h-3 bg-slate-300"></span>
                 <span>{{ (book.word_count / 10000).toFixed(1) }}万字</span>
              </div>
              
              <p class="text-sm text-slate-500 leading-relaxed line-clamp-2 mb-auto pr-8">
                {{ book.abstract }}
              </p>

              <!-- Footer Update Info -->
              <div class="mt-2 flex items-center gap-2 text-xs text-slate-400">
                 <span class="text-red-600/80 bg-red-50 px-2 py-0.5 rounded">最新更新</span>
                 <span v-if="book.updated_at" class="text-slate-500 font-medium whitespace-nowrap">{{ book.updated_at }}</span>
                 <span v-if="book.latest_chapter" class="truncate max-w-[200px]">{{ book.latest_chapter }}</span>
              </div>
           </div>
           
            <!-- Right Actions -->
            <div class="w-48 flex-shrink-0 flex flex-col justify-end items-end gap-3 py-1">
               <button 
                 @click="navigateToDetail(book)"
                 class="bg-white border border-slate-200 hover:border-slate-300 hover:bg-slate-50 text-slate-600 hover:text-slate-900 px-6 py-2 rounded-lg text-sm font-medium transition-all w-36"
               >
                 书籍详情
               </button>
               
               <button 
                 @click="openAIReport(book)"
                 class="bg-indigo-600 hover:bg-indigo-700 text-white px-6 py-2 rounded-lg text-sm font-bold transition-all shadow-lg shadow-indigo-500/20 hover:shadow-indigo-500/40 w-36 flex items-center justify-center gap-2 group-hover:scale-105"
               >
                 <Sparkles class="w-4 h-4" /> 智能书探
               </button>
            </div>
        </div>
      </div>

      <!-- Pagination -->
      <div v-if="totalPages > 1" class="flex justify-center items-center gap-3 py-8">
         <button 
           @click="currentPage = 1" 
           :disabled="currentPage === 1"
           class="p-2 rounded-lg border border-slate-200 hover:bg-slate-50 disabled:opacity-50 disabled:hover:bg-white transition-colors group"
           title="第一页"
         >
           <ChevronsLeft class="w-5 h-5 text-slate-400 group-hover:text-indigo-600 transition-colors" />
         </button>

         <button 
           @click="currentPage--" 
           :disabled="currentPage === 1"
           class="p-2 rounded-lg border border-slate-200 hover:bg-slate-50 disabled:opacity-50 disabled:hover:bg-white transition-colors group"
           title="上一页"
         >
           <ChevronLeft class="w-5 h-5 text-slate-600 group-hover:text-indigo-600 transition-colors" />
         </button>
         
         <div class="px-4 py-2 bg-slate-50 border border-slate-200 rounded-xl">
           <span class="text-sm font-bold text-slate-700">
             第 {{ currentPage }} 页 <span class="text-slate-300 mx-2">/</span> 共 {{ totalPages }} 页
           </span>
         </div>
         
         <button 
           @click="currentPage++" 
           :disabled="currentPage === totalPages"
           class="p-2 rounded-lg border border-slate-200 hover:bg-slate-50 disabled:opacity-50 disabled:hover:bg-white transition-colors group"
           title="下一页"
         >
           <ChevronRight class="w-5 h-5 text-slate-600 group-hover:text-indigo-600 transition-colors" />
         </button>

         <button 
           @click="currentPage = totalPages" 
           :disabled="currentPage === totalPages"
           class="p-2 rounded-lg border border-slate-200 hover:bg-slate-50 disabled:opacity-50 disabled:hover:bg-white transition-colors group"
           title="最后一页"
         >
           <ChevronsRight class="w-5 h-5 text-slate-400 group-hover:text-indigo-600 transition-colors" />
         </button>
      </div>

    </div>
  </EditorialLayout>
  
  <AIReportModal 
    :show="showAIReport" 
    :book="selectedBook" 
    @close="showAIReport = false" 
  />
</template>
