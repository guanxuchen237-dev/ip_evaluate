<script setup lang="ts">
import { ref, onUnmounted, computed, watch } from "vue";
import { 
  Users, MessageCircle, ThumbsUp, ThumbsDown, Meh, 
  Sparkles, Play, Pause, RotateCcw, Plus, X, UserPlus,
  Download
} from "lucide-vue-next";
import Input from "@/components/ui/Input.vue";
import Button from "@/components/ui/Button.vue";
import jsPDF from "jspdf";

interface VirtualReader {
  id: string;
  persona: string;
  avatar: string;
  age: string;
  traits: string[];
  preferences: string[];
  isThinking: boolean;
  isCustom?: boolean;
  feedback?: {
    rating: number;
    sentiment: "positive" | "neutral" | "negative";
    comment: string;
    keyPoints: string[];
  };
}

const defaultReaderPersonas: Omit<VirtualReader, "isThinking" | "feedback">[] = [
  {
    id: "gen-z",
    persona: "Z世代学生",
    avatar: "🧑‍🎓",
    age: "18-22",
    traits: ["追求新鲜感", "碎片化阅读", "社交分享"],
    preferences: ["快节奏", "强CP", "脑洞大开"],
  },
  {
    id: "office-worker",
    persona: "职场白领",
    avatar: "👩‍💼",
    age: "25-35",
    traits: ["时间有限", "解压需求", "品质要求"],
    preferences: ["轻松治愈", "成长逆袭", "职场元素"],
  },
  {
    id: "overseas-chinese",
    persona: "海外华人",
    avatar: "🌏",
    age: "25-45",
    traits: ["文化认同", "怀旧情结", "双语能力"],
    preferences: ["东方元素", "文化输出", "精品改编"],
  },
  {
    id: "western-reader",
    persona: "欧美读者",
    avatar: "👨",
    age: "20-30",
    traits: ["开放心态", "注重逻辑", "视觉体验"],
    preferences: ["世界观", "人物深度", "史诗叙事"],
  },
  {
    id: "anime-fan",
    persona: "二次元爱好者",
    avatar: "🎮",
    age: "16-28",
    traits: ["高度投入", "社区活跃", "周边消费"],
    preferences: ["动漫改编", "设定党", "番剧梗"],
  },
  {
    id: "senior-reader",
    persona: "资深书虫",
    avatar: "📚",
    age: "30-50",
    traits: ["阅读量大", "口味挑剔", "评论影响力"],
    preferences: ["文笔功底", "逻辑严谨", "深度主题"],
  },
];

const avatarOptions = ["👤", "👨", "👩", "🧑", "👴", "👵", "🧒", "👦", "👧", "🧔", "👱", "👸", "🤴", "🎭", "🎯", "💼", "🎓", "🌍", "🎮", "📱"];

const feedbackPool = {
  positive: [
    "节奏把控得当，爽点密集",
    "世界观新颖，设定有创意",
    "人物塑造立体，有成长弧光",
    "文笔流畅，画面感强",
    "情感戏处理细腻动人",
    "主角不圣母不白莲，很真实",
  ],
  neutral: [
    "前期节奏稍慢，需要耐心",
    "部分设定需要适应期",
    "配角戏份可以再丰富些",
    "有些地方翻译可能有困难",
    "风格比较独特，见仁见智",
  ],
  negative: [
    "开篇吸引力不足",
    "部分情节逻辑有待商榷",
    "文化背景理解门槛较高",
    "节奏有些拖沓",
    "人设有点脸谱化",
  ],
};

const keyPointsPool = [
  "世界观完整度高",
  "角色成长线清晰",
  "情节紧凑度优秀",
  "文化元素丰富",
  "改编潜力大",
  "粉丝基础稳固",
  "商业价值明确",
  "情感共鸣强烈",
];

const readerPersonas = ref(defaultReaderPersonas);
const readers = ref<VirtualReader[]>(
  defaultReaderPersonas.map(r => ({ ...r, isThinking: false }))
);
const isRunning = ref(false);
const currentStep = ref(0);
const overallScore = ref<number | null>(null);
const showAddForm = ref(false);
const newPersona = ref({
  persona: "",
  avatar: "👤",
  age: "",
  traits: "",
  preferences: ""
});

let timeoutId: any;

const completedCount = computed(() => readers.value.filter(r => r.feedback).length);

const handleAddPersona = () => {
  if (!newPersona.value.persona || !newPersona.value.age) return;
  
  const newReader: Omit<VirtualReader, "isThinking" | "feedback"> = {
    id: `custom-${Date.now()}`,
    persona: newPersona.value.persona,
    avatar: newPersona.value.avatar,
    age: newPersona.value.age,
    traits: newPersona.value.traits.split(",").map(t => t.trim()).filter(t => t),
    preferences: newPersona.value.preferences.split(",").map(p => p.trim()).filter(p => p),
    isCustom: true
  };
  
  readerPersonas.value = [...readerPersonas.value, newReader];
  readers.value = [...readers.value, { ...newReader, isThinking: false }];
  newPersona.value = { persona: "", avatar: "👤", age: "", traits: "", preferences: "" };
  showAddForm.value = false;
};

const handleRemoveCustomPersona = (id: string) => {
  readerPersonas.value = readerPersonas.value.filter(r => r.id !== id);
  readers.value = readers.value.filter(r => r.id !== id);
};

const runSimulation = () => {
  setIsRunning(true);
  currentStep.value = 0;
  overallScore.value = null;
  readers.value = readerPersonas.value.map(r => ({ ...r, isThinking: false, feedback: undefined }));
};

const setIsRunning = (val: boolean) => {
  isRunning.value = val;
};

const resetSimulation = () => {
  setIsRunning(false);
  currentStep.value = 0;
  overallScore.value = null;
  readers.value = readerPersonas.value.map(r => ({ ...r, isThinking: false, feedback: undefined }));
  clearTimeout(timeoutId);
};

watch([isRunning, currentStep], ([running, step]) => {
  if (!running) return;
  
  if (step >= readers.value.length) {
    setIsRunning(false);
    // Calculate overall score
    const scores = readers.value.map(r => r.feedback?.rating || 0).filter(s => s > 0);
    if (scores.length > 0) {
      overallScore.value = Math.round(scores.reduce((a, b) => a + b, 0) / scores.length * 10) / 10;
    }
    return;
  }

  // Set current reader to thinking
  readers.value = readers.value.map((r, i) => ({
    ...r,
    isThinking: i === step
  }));

  // After delay, generate feedback
  timeoutId = setTimeout(() => {
    readers.value = readers.value.map((r, i) => {
      if (i !== step) return r;
      
      const rating = 6 + Math.random() * 4; // 6-10 range
      const sentimentRoll = Math.random();
      const sentiment: "positive" | "neutral" | "negative" = 
        sentimentRoll > 0.3 ? "positive" : sentimentRoll > 0.1 ? "neutral" : "negative";
      
      const pool = feedbackPool[sentiment];
      const comment = pool[Math.floor(Math.random() * pool.length)] || "";
      
      const keyPoints = keyPointsPool
        .sort(() => Math.random() - 0.5)
        .slice(0, 2 + Math.floor(Math.random() * 2));

      return {
        ...r,
        isThinking: false,
        feedback: { rating, sentiment, comment, keyPoints }
      };
    });
    currentStep.value++;
  }, 1500 + Math.random() * 1000);
});

onUnmounted(() => {
  clearTimeout(timeoutId);
});

const exportToPDF = () => {
  const doc = new jsPDF();
  const pageWidth = doc.internal.pageSize.getWidth();
  const pageHeight = doc.internal.pageSize.getHeight();

  // === COVER PAGE ===
  // Background gradient effect
  doc.setFillColor(25, 20, 40);
  doc.rect(0, 0, pageWidth, pageHeight, "F");

  // Simplified decorative elements
  doc.setFillColor(102, 51, 153);
  doc.triangle(0, 0, 80, 0, 0, 80, "F");
  
  // Logo icon (stylized "VF" for Virtual Focus)
  doc.setFontSize(36);
  doc.setTextColor(255, 255, 255);
  doc.setFont("helvetica", "bold");
  doc.text("VF", pageWidth / 2, pageHeight / 2 - 25, { align: "center" });

  // Main Title
  doc.setFontSize(28);
  doc.setTextColor(255, 255, 255);
  doc.text("Market Test Report", pageWidth / 2, pageHeight / 2 + 40, { align: "center" });

  // Metadata
  doc.setFontSize(10);
  doc.setTextColor(200, 200, 210);
  doc.text(`Generation Date: ${new Date().toLocaleString("zh-CN")}`, 40, pageHeight - 52);
  doc.text(`Overall Score: ${overallScore.value !== null ? overallScore.value.toFixed(1) : "N/A"}`, pageWidth - 80, pageHeight - 52);

  // === PAGE 2: SUMMARY ===
  doc.addPage();
  doc.setFillColor(255, 255, 255);
  doc.rect(0, 0, pageWidth, pageHeight, "F");
  
  doc.setFontSize(14);
  doc.setTextColor(50, 50, 50);
  doc.text("EXECUTIVE SUMMARY", pageWidth / 2, 20, { align: "center" });

  let y = 40;
  
  // Stats
  const completedReaders = readers.value.filter(r => r.feedback);
  const positiveCount = completedReaders.filter(r => r.feedback?.sentiment === "positive").length;
  const neutralCount = completedReaders.filter(r => r.feedback?.sentiment === "neutral").length;
  const negativeCount = completedReaders.filter(r => r.feedback?.sentiment === "negative").length;
  
  doc.setFontSize(10);
  doc.setTextColor(80, 80, 80);
  doc.text(`Total Participants: ${completedReaders.length}`, 25, y);
  y += 10;
  doc.text(`Positive Feedback: ${positiveCount}`, 25, y);
  y += 10;
  doc.text(`Neutral Feedback: ${neutralCount}`, 25, y);
  y += 10;
  doc.text(`Negative Feedback: ${negativeCount}`, 25, y);
  y += 20;

  // Feedback list
  doc.setFontSize(12);
  doc.text("Detailed Feedback", 25, y);
  y += 10;

  completedReaders.forEach(reader => {
    if (y > 270) {
      doc.addPage();
      y = 20;
    }
    doc.setFontSize(10);
     doc.setTextColor(50, 50, 50);
    // Handle special characters in names/avatars? jsPDF default font doesn't support emoji/Chinese well without custom font.
    // For now, using simple text fallback or English labels if possible, or just rendering as is (might show garbage for Chinese without font).
    // Note: Standard jsPDF doesn't support UTF-8 out of the box for Chinese. 
    // In a real scenario, we'd add a font. For this port, we'll keep it simple and maybe warn or just render.
    // I will try to use reader.id or English fallback if provided, or proceed.
    // Ideally we should bundle a font, but that's complex for this environment.
    // I'll assume standard ASCII for this demo or accept it might be garbled in PDF.
    
    // Attempting to write text (Chinese traits might fail)
    // doc.text(`${reader.persona}: ${reader.feedback?.comment}`, 25, y); 
    // Just putting ID and score to be safe for now, or raw text.
    doc.text(`Reader (${reader.age}y): ${reader.feedback?.rating.toFixed(1)}/10`, 25, y);
    y += 7;
    doc.setFontSize(9);
    doc.setTextColor(100, 100, 100);
    // Split long comment
    const lines = doc.splitTextToSize(`"${reader.feedback?.comment}"`, pageWidth - 50);
    doc.text(lines, 25, y);
    y += lines.length * 5 + 5;
  });

  doc.save(`focus-group-report-${Date.now()}.pdf`);
};

const getSentimentIcon = (sentiment: "positive" | "neutral" | "negative" | undefined) => {
  switch (sentiment) {
    case "positive": return ThumbsUp;
    case "neutral": return Meh;
    case "negative": return ThumbsDown;
    default: return Meh;
  }
};
</script>

<template>
  <div class="editorial-card rounded-3xl p-8">
    <!-- Header -->
    <div class="flex items-start justify-between mb-6">
      <div class="flex items-center gap-3">
        <div class="w-10 h-10 rounded-xl bg-chart-purple/10 flex items-center justify-center">
          <Users class="w-5 h-5 text-chart-purple" />
        </div>
        <div>
          <h3 class="editorial-headline text-xl text-foreground">Virtual Focus Group</h3>
          <p class="text-sm text-muted-foreground">AI模拟虚拟读者焦点小组</p>
        </div>
      </div>
      
      <div class="flex items-center gap-2">
        <button
          @click="showAddForm = true"
          class="p-2 rounded-lg bg-chart-green/10 hover:bg-chart-green/20 border border-chart-green/30 text-chart-green transition-all"
          title="添加自定义画像"
        >
          <UserPlus class="w-4 h-4" />
        </button>
        <button
          v-if="overallScore !== null"
          @click="exportToPDF"
          class="flex items-center gap-2 px-3 py-2 rounded-lg bg-chart-blue/10 hover:bg-chart-blue/20 border border-chart-blue/30 text-chart-blue transition-all"
          title="导出PDF报告"
        >
          <Download class="w-4 h-4" />
          <span class="text-sm">导出报告</span>
        </button>
        <button
          @click="resetSimulation"
          class="p-2 rounded-lg bg-white/50 hover:bg-white/70 border border-white/40 transition-all"
        >
          <RotateCcw class="w-4 h-4" />
        </button>
        <button
          @click="isRunning ? setIsRunning(false) : runSimulation()"
          class="flex items-center gap-2 px-4 py-2 rounded-lg bg-chart-purple/10 hover:bg-chart-purple/20 border border-chart-purple/30 text-chart-purple transition-all"
        >
          <component :is="isRunning ? Pause : Play" class="w-4 h-4" />
          {{ isRunning ? "暂停" : "开始模拟" }}
        </button>
      </div>
    </div>

    <!-- Add Custom Persona Form -->
    <div v-if="showAddForm" class="mb-6 p-4 rounded-xl bg-gradient-to-br from-chart-green/10 to-chart-green/5 border border-chart-green/30">
      <div class="flex items-center justify-between mb-4">
        <div class="flex items-center gap-2">
          <UserPlus class="w-4 h-4 text-chart-green" />
          <span class="font-medium text-foreground">创建自定义读者画像</span>
        </div>
        <button 
          @click="showAddForm = false"
          class="p-1 rounded hover:bg-white/50 transition-colors"
        >
          <X class="w-4 h-4 text-muted-foreground" />
        </button>
      </div>
      
      <div class="grid grid-cols-2 gap-4 mb-4">
        <div>
          <label class="text-xs text-muted-foreground mb-1 block">画像名称 *</label>
          <Input 
            v-model="newPersona.persona"
            placeholder="如：科幻迷、宝妈群体"
            class="bg-white/50 border-white/40"
          />
        </div>
        <div>
          <label class="text-xs text-muted-foreground mb-1 block">年龄段 *</label>
          <Input 
            v-model="newPersona.age"
            placeholder="如：25-35"
            class="bg-white/50 border-white/40"
          />
        </div>
      </div>
      
      <div class="mb-4">
        <label class="text-xs text-muted-foreground mb-2 block">选择头像</label>
        <div class="flex flex-wrap gap-2">
          <button
            v-for="emoji in avatarOptions"
            :key="emoji"
            @click="newPersona.avatar = emoji"
            class="w-10 h-10 rounded-lg text-xl flex items-center justify-center transition-all"
            :class="newPersona.avatar === emoji 
              ? 'bg-chart-green/30 border-2 border-chart-green' 
              : 'bg-white/50 border border-white/40 hover:bg-white/70'"
          >
            {{ emoji }}
          </button>
        </div>
      </div>
      
      <div class="grid grid-cols-2 gap-4 mb-4">
        <div>
          <label class="text-xs text-muted-foreground mb-1 block">特征标签（逗号分隔）</label>
          <Input 
            v-model="newPersona.traits"
            placeholder="如：高消费, 追求品质"
            class="bg-white/50 border-white/40"
          />
        </div>
        <div>
          <label class="text-xs text-muted-foreground mb-1 block">偏好标签（逗号分隔）</label>
          <Input 
            v-model="newPersona.preferences"
            placeholder="如：硬核科幻, 太空歌剧"
            class="bg-white/50 border-white/40"
          />
        </div>
      </div>
      
      <Button 
        @click="handleAddPersona"
        :disabled="!newPersona.persona || !newPersona.age"
        class="w-full bg-chart-green hover:bg-chart-green/90"
      >
        <Plus class="w-4 h-4 mr-2" />
        添加画像
      </Button>
    </div>

    <!-- Progress -->
    <div v-if="isRunning || completedCount > 0" class="mb-6">
      <div class="flex items-center justify-between mb-2">
        <span class="text-sm text-muted-foreground">测试进度</span>
        <span class="text-sm font-medium">{{ completedCount }}/{{ readers.length }}</span>
      </div>
      <div class="h-2 bg-white/30 rounded-full overflow-hidden">
        <div 
          class="h-full bg-gradient-to-r from-chart-purple to-chart-blue transition-all duration-500"
          :style="{ width: `${(completedCount / readers.length) * 100}%` }"
        />
      </div>
    </div>

    <!-- Overall score -->
    <div v-if="overallScore !== null" class="mb-6 p-6 rounded-2xl bg-gradient-to-br from-chart-purple/10 to-chart-blue/10 border border-chart-purple/20 text-center">
      <div class="flex items-center justify-center gap-2 mb-2">
        <Sparkles class="w-5 h-5 text-chart-purple" />
        <span class="text-sm font-medium text-foreground">综合市场测试评分</span>
      </div>
      <p class="text-5xl font-serif font-bold text-chart-purple">{{ overallScore }}</p>
      <p class="text-sm text-muted-foreground mt-2">
        基于{{ completedCount }}位虚拟读者的反馈
      </p>
    </div>

    <!-- Readers grid -->
    <div class="grid grid-cols-2 lg:grid-cols-3 gap-4">
      <div
        v-for="reader in readers"
        :key="reader.id"
        class="p-4 rounded-xl border transition-all duration-300"
        :class="{
          'bg-chart-purple/10 border-chart-purple/40 scale-105 shadow-lg': reader.isThinking,
          'bg-white/50 border-white/40': reader.feedback,
          'bg-white/30 border-white/30': !reader.isThinking && !reader.feedback
        }"
      >
        <!-- Avatar & persona -->
        <div class="flex items-center justify-between mb-3">
          <div class="flex items-center gap-3">
            <div class="w-10 h-10 rounded-full bg-white/60 flex items-center justify-center text-xl">
              {{ reader.avatar }}
            </div>
            <div>
              <div class="flex items-center gap-2">
                <p class="font-medium text-foreground text-sm">{{ reader.persona }}</p>
                <span v-if="reader.isCustom" class="px-1.5 py-0.5 rounded bg-chart-green/20 text-[10px] text-chart-green">自定义</span>
              </div>
              <p class="text-xs text-muted-foreground">{{ reader.age }}岁</p>
            </div>
          </div>
          <button
            v-if="reader.isCustom && !reader.isThinking && !reader.feedback"
            @click="handleRemoveCustomPersona(reader.id)"
            class="p-1 rounded hover:bg-chart-red/20 text-muted-foreground hover:text-chart-red transition-colors"
          >
            <X class="w-3 h-3" />
          </button>
        </div>

        <!-- Tags -->
        <div class="flex flex-wrap gap-1 mb-3">
          <span 
            v-for="trait in reader.traits.slice(0, 2)" 
            :key="trait"
            class="px-1.5 py-0.5 rounded bg-white/40 text-[10px] text-muted-foreground"
          >
            {{ trait }}
          </span>
        </div>

        <!-- Feedback Area -->
        <div class="min-h-[80px] flex items-center justify-center">
          <div v-if="reader.isThinking" class="flex flex-col items-center gap-2 text-chart-purple animate-pulse">
            <MessageCircle class="w-5 h-5" />
            <span class="text-xs">阅读分析中...</span>
          </div>

          <div v-else-if="reader.feedback" class="w-full space-y-2 animate-in fade-in slide-in-from-bottom-2 duration-500">
            <div class="flex items-center justify-between">
              <div class="flex items-center gap-1.5">
                <component :is="getSentimentIcon(reader.feedback.sentiment)" 
                  class="w-4 h-4"
                  :class="{
                    'text-chart-green': reader.feedback.sentiment === 'positive',
                    'text-chart-yellow': reader.feedback.sentiment === 'neutral',
                    'text-chart-red': reader.feedback.sentiment === 'negative'
                  }"
                />
                <span class="font-bold text-lg" 
                  :class="{
                    'text-chart-green': reader.feedback.sentiment === 'positive',
                    'text-chart-yellow': reader.feedback.sentiment === 'neutral',
                    'text-chart-red': reader.feedback.sentiment === 'negative'
                  }"
                >
                  {{ reader.feedback.rating.toFixed(1) }}
                </span>
              </div>
              <span class="text-[10px] text-muted-foreground px-1.5 py-0.5 rounded bg-white/50">
                {{ reader.feedback.sentiment.toUpperCase() }}
              </span>
            </div>
            
            <p class="text-xs text-foreground/80 line-clamp-3 leading-relaxed">
              "{{ reader.feedback.comment }}"
            </p>
            
            <div class="pt-2 border-t border-white/20">
              <div v-for="(point, i) in reader.feedback.keyPoints" :key="i" class="flex items-center gap-1 text-[10px] text-muted-foreground">
                <div class="w-1 h-1 rounded-full bg-chart-purple/50"></div>
                {{ point }}
              </div>
            </div>
          </div>

          <div v-else class="text-xs text-muted-foreground/50 text-center">
            等待测试...
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
