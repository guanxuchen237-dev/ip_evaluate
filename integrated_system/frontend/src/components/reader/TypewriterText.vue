<script setup lang="ts">
import { ref, onMounted, watch, computed } from 'vue'

interface Props {
  text: string
  speed?: number  // 每字符毫秒数
  delay?: number  // 开始延迟
  sentiment?: number  // 用于选择表情
}

const props = withDefaults(defineProps<Props>(), {
  speed: 30,
  delay: 0,
  sentiment: 0
})

const emit = defineEmits<{
  complete: []
}>()

const displayText = ref('')
const isTyping = ref(true)
const showEmoji = ref(false)

// 根据情感选择表情
const emoji = computed(() => {
  const s = props.sentiment
  if (s >= 0.7) return ['🔥', '😍', '💯', '👏'][Math.floor(Math.random() * 4)]
  if (s >= 0.3) return ['😊', '👍', '✨', '📖'][Math.floor(Math.random() * 4)]
  if (s >= -0.3) return ['🤔', '😐', '📝', '👀'][Math.floor(Math.random() * 4)]
  if (s >= -0.7) return ['😕', '💭', '❓', '😓'][Math.floor(Math.random() * 4)]
  return ['😤', '💢', '😠', '🙄'][Math.floor(Math.random() * 4)]
})

const startTyping = () => {
  displayText.value = ''
  isTyping.value = true
  showEmoji.value = false
  
  let i = 0
  const text = props.text
  
  setTimeout(() => {
    const interval = setInterval(() => {
      if (i < text.length) {
        displayText.value = text.slice(0, i + 1)
        i++
      } else {
        clearInterval(interval)
        isTyping.value = false
        showEmoji.value = true
        emit('complete')
      }
    }, props.speed)
  }, props.delay)
}

onMounted(() => {
  startTyping()
})

// 如果文本改变，重新开始打字
watch(() => props.text, () => {
  startTyping()
})
</script>

<template>
  <span class="typewriter-container">
    <span class="typewriter-text">{{ displayText }}</span>
    <span v-if="isTyping" class="cursor">|</span>
    <span 
      v-if="showEmoji" 
      class="ml-1 inline-block animate-bounce-in"
    >{{ emoji }}</span>
  </span>
</template>

<style scoped>
.cursor {
  animation: blink 0.7s infinite;
  color: #6366f1;
  font-weight: bold;
}

@keyframes blink {
  0%, 50% { opacity: 1; }
  51%, 100% { opacity: 0; }
}

.animate-bounce-in {
  animation: bounceIn 0.3s ease-out;
}

@keyframes bounceIn {
  0% {
    transform: scale(0);
    opacity: 0;
  }
  50% {
    transform: scale(1.3);
  }
  100% {
    transform: scale(1);
    opacity: 1;
  }
}
</style>
