<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { X, Save, Server, Key, Globe, Box, Plus, Trash2, CheckCircle2 } from 'lucide-vue-next'
import axios from 'axios'

const emit = defineEmits(['close'])

const form = ref({
  primary_chat_id: '',
  primary_logic_id: '',
  models: [] as any[]
})

const loading = ref(false)
const saving = ref(false)
const message = ref('')
const error = ref('')
const testingId = ref('')

// Defaults
const DEFAULTS = {
  github: {
    base_url: 'https://models.inference.ai.azure.com',
    model_name: 'gpt-4o'
  },
  gemini: {
    base_url: 'http://127.0.0.1:7861/v1',
    model_name: 'gemini-1.5-pro'
  },
  deepseek: {
    base_url: 'https://api.deepseek.com/v1',
    model_name: 'deepseek-chat'
  },
  custom: {
    base_url: '',
    model_name: ''
  }
}

const fetchConfig = async () => {
  loading.value = true
  try {
    const res = await axios.get('http://localhost:5000/api/config/ai')
    if (res.data.models) {
        form.value = res.data
    } else {
        // Fallback for old configs
        form.value = {
            primary_chat_id: 'legacy-1',
            primary_logic_id: 'legacy-1',
            models: [{
                id: 'legacy-1',
                provider: res.data.provider || 'github',
                base_url: res.data.base_url || '',
                api_key: res.data.api_key || '',
                model_name: res.data.model_name || ''
            }]
        }
    }
  } catch (e) {
    error.value = '加载配置失败'
  } finally {
    loading.value = false
  }
}

const saveConfig = async () => {
  saving.value = true
  error.value = ''
  message.value = ''
  
  try {
    await axios.post('http://localhost:5000/api/config/ai', form.value)
    message.value = '多模型池配置已保存，后端服务已重连...'
    setTimeout(() => {
        emit('close')
    }, 1500)
  } catch (e: any) {
    error.value = e.response?.data?.error || '保存失败'
  } finally {
    saving.value = false
  }
}

const addNewModel = () => {
    const newId = 'm_' + Math.random().toString(36).substring(2, 9)
    form.value.models.push({
        id: newId,
        provider: 'github',
        base_url: DEFAULTS.github.base_url,
        model_name: DEFAULTS.github.model_name,
        api_key: ''
    })
    // 如果是第一个模型，自动绑定为全局主模型
    if (form.value.models.length === 1) {
        form.value.primary_chat_id = newId
        form.value.primary_logic_id = newId
    }
}

const removeModel = (index: number) => {
    form.value.models.splice(index, 1)
}

const applyDefaults = (model: any) => {
    const provider = model.provider as keyof typeof DEFAULTS
    if (DEFAULTS[provider]) {
        model.base_url = DEFAULTS[provider].base_url
        model.model_name = DEFAULTS[provider].model_name
    }
}

const testModel = async (model: any) => {
    testingId.value = model.id
    error.value = ''
    message.value = ''
    try {
        const res = await axios.post('http://localhost:5000/api/config/ai/test', {
            provider: model.provider,
            base_url: model.base_url,
            api_key: model.api_key,
            model_name: model.model_name
        })
        message.value = `[${model.model_name}] ` + res.data.message
    } catch (e: any) {
        error.value = `[${model.model_name}] 连通测试失败: ` + (e.response?.data?.error || e.message)
    } finally {
        testingId.value = ''
    }
}

onMounted(() => {
  fetchConfig()
})
</script>

<template>
  <div class="fixed inset-0 z-[100] flex items-center justify-center p-4">
    <!-- Backdrop -->
    <div class="absolute inset-0 bg-slate-900/40 backdrop-blur-sm transition-opacity" @click="$emit('close')"></div>

    <!-- Modal Card -->
    <div class="relative w-full max-w-2xl bg-white rounded-2xl shadow-2xl border border-slate-100 overflow-hidden flex flex-col max-h-[90vh]">
      
      <!-- Header -->
      <div class="px-6 py-4 bg-slate-50 border-b border-slate-100 flex items-center justify-between shrink-0">
        <h3 class="text-lg font-bold text-slate-800 flex items-center gap-2">
            <Server class="w-5 h-5 text-indigo-600" />
            AI 多模型池配置
        </h3>
        <button @click="$emit('close')" class="p-1 rounded-full text-slate-400 hover:bg-slate-200 hover:text-slate-600 transition-colors">
            <X class="w-5 h-5" />
        </button>
      </div>

      <!-- Body -->
      <div class="p-6 space-y-6 overflow-y-auto font-sans">
        
        <!-- Global Usages -->
        <div class="space-y-4">
            <h4 class="text-sm font-bold text-slate-800 border-b border-slate-100 pb-2">全局用途绑定</h4>
            <div class="grid grid-cols-2 gap-4">
                <div>
                    <label class="block text-xs font-semibold text-slate-500 mb-1">主聊天大模型 (Chat)</label>
                    <select v-model="form.primary_chat_id" class="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-sm focus:bg-white focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20 outline-none transition-all">
                        <option value="">-- 请选择 --</option>
                        <option v-for="m in form.models" :key="m.id" :value="m.id">
                            {{ m.model_name || '未命名' }} ({{ m.provider }})
                        </option>
                    </select>
                </div>
                <div>
                    <label class="block text-xs font-semibold text-slate-500 mb-1">轻量逻辑模型 (Logic)</label>
                    <select v-model="form.primary_logic_id" class="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-sm focus:bg-white focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20 outline-none transition-all">
                        <option value="">-- 请选择 --</option>
                        <option v-for="m in form.models" :key="m.id" :value="m.id">
                            {{ m.model_name || '未命名' }} ({{ m.provider }})
                        </option>
                    </select>
                </div>
            </div>
            <p class="text-[11px] text-slate-400">将不同的系统功能绑定到特定模型上，以便通过高低搭配节省成本并提升稳定性。</p>
        </div>

        <!-- Model List -->
        <div class="space-y-4">
            <div class="flex items-center justify-between border-b border-slate-100 pb-2">
                <h4 class="text-sm font-bold text-slate-800">模型实例池 ({{ form.models.length }})</h4>
                <button @click="addNewModel" class="flex items-center gap-1 text-xs font-bold text-indigo-600 hover:text-indigo-700 bg-indigo-50 hover:bg-indigo-100 px-3 py-1.5 rounded-lg transition-colors">
                    <Plus class="w-3.5 h-3.5" />
                    添加新模型
                </button>
            </div>
            
            <div v-if="form.models.length === 0" class="flex flex-col items-center justify-center py-8 text-slate-400 bg-slate-50 rounded-xl border border-dashed border-slate-200">
                <Box class="w-8 h-8 mb-2 opacity-50" />
                <span class="text-sm">尚未添加任何模型</span>
            </div>

            <!-- Model Cards -->
            <div class="space-y-4">
                <div v-for="(m, i) in form.models" :key="m.id" class="p-4 bg-white border border-slate-200 rounded-xl shadow-sm relative group">
                    <button @click="removeModel(i)" title="移除此模型" class="absolute top-4 right-4 text-slate-300 hover:text-red-500 hover:bg-red-50 p-1.5 rounded-lg transition-all opacity-0 group-hover:opacity-100">
                        <Trash2 class="w-4 h-4" />
                    </button>
                    
                    <div class="grid grid-cols-2 gap-4">
                        <!-- Provider -->
                        <div class="col-span-2 sm:col-span-1">
                            <label class="block text-xs font-semibold text-slate-500 mb-1">服务商 (Provider)</label>
                            <select v-model="m.provider" @change="applyDefaults(m)" class="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-sm focus:bg-white outline-none">
                                <option value="github">GitHub Models</option>
                                <option value="gemini">Google Gemini</option>
                                <option value="deepseek">DeepSeek</option>
                                <option value="custom">Custom (OpenAI Compatible)</option>
                            </select>
                        </div>

                        <!-- Model Name -->
                        <div class="col-span-2 sm:col-span-1">
                            <label class="block text-xs font-semibold text-slate-500 mb-1">模型名称 (Model ID)</label>
                            <input v-model="m.model_name" type="text" placeholder="例如: gpt-4o" class="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-sm font-mono focus:bg-white outline-none focus:border-indigo-500">
                        </div>

                        <!-- Base URL -->
                        <div class="col-span-2">
                            <label class="block text-xs font-semibold text-slate-500 mb-1">API Base URL</label>
                            <input v-model="m.base_url" type="text" placeholder="https://api.openai.com/v1" class="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-sm font-mono focus:bg-white outline-none focus:border-indigo-500">
                        </div>

                        <!-- API Key -->
                        <div class="col-span-2 flex items-end gap-3">
                            <div class="flex-1">
                                <label class="block text-xs font-semibold text-slate-500 mb-1">API Key</label>
                                <input v-model="m.api_key" type="password" placeholder="sk-..." class="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-sm font-mono focus:bg-white outline-none focus:border-indigo-500">
                            </div>
                            <!-- Test Button -->
                            <button 
                                @click="testModel(m)" 
                                :disabled="testingId === m.id"
                                class="shrink-0 flex items-center justify-center gap-1.5 h-[38px] px-4 bg-slate-800 hover:bg-slate-700 text-white text-xs font-bold rounded-lg transition-colors disabled:opacity-50"
                            >
                                <span v-if="testingId === m.id" class="animate-spin w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full"></span>
                                <CheckCircle2 v-else class="w-3.5 h-3.5" />
                                {{ testingId === m.id ? '测试中...' : '测试连通性' }}
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Status Messages -->
        <div v-if="error" class="p-3 bg-red-50 text-red-600 text-sm rounded-lg border border-red-100 flex items-center gap-2">
            <span class="w-1.5 h-1.5 rounded-full bg-red-500"></span>
            {{ error }}
        </div>
        <div v-if="message" class="p-3 bg-emerald-50 text-emerald-600 text-sm rounded-lg border border-emerald-100 flex items-center gap-2">
            <span class="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
            {{ message }}
        </div>

      </div>

      <!-- Footer -->
      <div class="px-6 py-4 bg-slate-50 border-t border-slate-100 flex justify-end gap-3 shrink-0">
        <button 
            @click="$emit('close')"
            class="px-4 py-2 text-sm font-medium text-slate-600 hover:text-slate-800 hover:bg-slate-200 rounded-lg transition-colors"
        >
            取消
        </button>
        <button 
            @click="saveConfig"
            :disabled="saving || loading"
            class="flex items-center gap-2 px-6 py-2 bg-indigo-600 hover:bg-indigo-700 active:bg-indigo-800 text-white text-sm font-bold rounded-lg shadow-sm transition-all disabled:opacity-50 disabled:cursor-not-allowed"
        >
            <Save v-if="!saving" class="w-4 h-4" />
            <span v-if="saving" class="animate-spin w-4 h-4 border-2 border-white/30 border-t-white rounded-full"></span>
            {{ saving ? '保存中...' : '保存配置' }}
        </button>
      </div>

      <!-- Loading Overlay -->
      <div v-if="loading" class="absolute inset-0 bg-white/80 backdrop-blur-[1px] flex items-center justify-center z-10">
        <div class="flex flex-col items-center gap-2">
            <div class="w-8 h-8 border-3 border-indigo-100 border-t-indigo-600 rounded-full animate-spin"></div>
            <span class="text-xs text-indigo-600 font-medium">加载配置...</span>
        </div>
      </div>
    </div>
  </div>
</template>
