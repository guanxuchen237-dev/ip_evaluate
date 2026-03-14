<script setup lang="ts">
import { Globe, MapPin, Users } from 'lucide-vue-next'

interface RegionData {
  region: string
  regionCn: string
  potential: number
  culturalDiscount: number
  notes: string
}

const regionData: RegionData[] = [
  {
    region: 'East Asia',
    regionCn: '东亚',
    potential: 95,
    culturalDiscount: 5,
    notes: '文化接近度高，市场成熟',
  },
  {
    region: 'Southeast Asia',
    regionCn: '东南亚',
    potential: 88,
    culturalDiscount: 12,
    notes: '网文接受度高，增长迅速',
  },
  {
    region: 'North America',
    regionCn: '北美',
    potential: 72,
    culturalDiscount: 25,
    notes: '需要本土化改编',
  },
  {
    region: 'Europe',
    regionCn: '欧洲',
    potential: 65,
    culturalDiscount: 30,
    notes: '奇幻类型有受众基础',
  },
  {
    region: 'Latin America',
    regionCn: '拉美',
    potential: 58,
    culturalDiscount: 35,
    notes: '潜力市场，需要培育',
  },
]

const focusGroups = [
  { persona: 'Z世代读者', age: '18-25', feedback: '节奏感强，世界观吸引人', sentiment: 'positive' },
  { persona: '职场白领', age: '25-35', feedback: '适合碎片化阅读', sentiment: 'positive' },
  { persona: '海外华人', age: '25-45', feedback: '文化认同感强', sentiment: 'positive' },
  { persona: '欧美读者', age: '20-30', feedback: '部分设定需解释', sentiment: 'neutral' },
]

const avgPotential = Math.round(regionData.reduce((acc, r) => acc + r.potential, 0) / regionData.length)
</script>

<template>
  <div class="editorial-card rounded-3xl p-8">
    <!-- Header -->
    <div class="flex items-start justify-between mb-8">
      <div class="flex items-center gap-3">
        <div class="w-10 h-10 rounded-xl bg-chart-blue/10 flex items-center justify-center">
          <Globe class="w-5 h-5 text-chart-blue" />
        </div>
        <div>
          <h3 class="editorial-headline text-xl text-foreground">Global Potential</h3>
          <p class="text-sm text-muted-foreground">全球化改编潜力指数</p>
        </div>
      </div>

      <div class="text-right">
        <p class="text-3xl font-serif font-bold text-chart-blue">{{ avgPotential }}%</p>
        <p class="text-xs text-muted-foreground">全球适应性</p>
      </div>
    </div>

    <!-- Region potential -->
    <div class="space-y-3 mb-8">
      <div 
        v-for="region in regionData"
        :key="region.region"
        class="p-4 rounded-2xl bg-white/40 hover:bg-white/60 transition-all"
      >
        <div class="flex items-center justify-between mb-2">
          <div class="flex items-center gap-2">
            <MapPin class="w-4 h-4 text-muted-foreground" />
            <span class="font-medium text-foreground">{{ region.regionCn }}</span>
            <span class="text-xs text-muted-foreground">{{ region.region }}</span>
          </div>
          <div class="flex items-center gap-4">
            <span class="text-xs text-chart-red">文化折扣 -{{ region.culturalDiscount }}%</span>
            <span class="text-lg font-serif font-bold text-foreground">{{ region.potential }}%</span>
          </div>
        </div>
        <div class="flex items-center gap-3">
          <div class="flex-1 h-2 bg-white/50 rounded-full overflow-hidden">
            <div 
              class="h-full rounded-full bg-gradient-to-r from-chart-blue to-chart-cyan"
              :style="{ width: `${region.potential}%` }"
            />
          </div>
          <span class="text-xs text-muted-foreground min-w-0 truncate">{{ region.notes }}</span>
        </div>
      </div>
    </div>

    <!-- Virtual focus groups -->
    <div>
      <div class="flex items-center gap-2 mb-4">
        <Users class="w-4 h-4 text-muted-foreground" />
        <span class="text-sm font-medium text-foreground">虚拟读者焦点小组</span>
      </div>
      <div class="grid grid-cols-2 gap-3">
        <div 
          v-for="(group, index) in focusGroups"
          :key="index"
          :class="[
            'p-4 rounded-xl border',
            group.sentiment === 'positive' 
              ? 'bg-chart-green/5 border-chart-green/20'
              : 'bg-chart-yellow/5 border-chart-yellow/20'
          ]"
        >
          <div class="flex items-center gap-2 mb-2">
            <span class="text-sm font-medium text-foreground">{{ group.persona }}</span>
            <span class="text-xs text-muted-foreground">{{ group.age }}</span>
          </div>
          <p class="text-xs text-muted-foreground">"{{ group.feedback }}"</p>
        </div>
      </div>
    </div>
  </div>
</template>
