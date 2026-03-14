<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  effect: 'rain' | 'fire' | 'storm' | null
}>()

const isVisible = computed(() => !!props.effect)

const getRainStyle = () => ({
  left: `${Math.random() * 100}vw`,
  animationDuration: `${0.5 + Math.random() * 0.5}s`,
  animationDelay: `${Math.random() * 2}s`
})

const getFireStyle = () => ({
  left: `${Math.random() * 100}vw`,
  animationDuration: `${1 + Math.random() * 2}s`,
  animationDelay: `${Math.random()}s`,
  transform: `scale(${0.5 + Math.random()})`
})
</script>

<template>
  <Transition name="fade">
    <div v-if="isVisible" class="fixed inset-0 pointer-events-none z-[100] overflow-hidden">
      <!-- Rain Effect -->
      <div v-if="effect === 'rain'" class="absolute inset-0 bg-slate-900/10">
        <div v-for="n in 60" :key="`rain-${n}`" class="rain-drop" :style="getRainStyle()"></div>
      </div>

      <!-- Fire Effect -->
      <div v-if="effect === 'fire'" class="absolute inset-0">
        <div class="absolute inset-x-0 bottom-0 h-1/3 bg-gradient-to-t from-orange-500/20 to-transparent"></div>
        <div v-for="n in 40" :key="`fire-${n}`" class="fire-particle" :style="getFireStyle()"></div>
      </div>

      <!-- Storm Effect -->
      <div v-if="effect === 'storm'" class="absolute inset-0 bg-slate-900/20">
        <div class="lightning"></div>
        <div class="rain-heavy">
          <div v-for="n in 80" :key="`storm-rain-${n}`" class="rain-drop heavy" :style="getRainStyle()"></div>
        </div>
      </div>
    </div>
  </Transition>
</template>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.5s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

/* Rain Animation */
.rain-drop {
  position: absolute;
  top: -20px;
  width: 1px;
  height: 40px;
  background: linear-gradient(to bottom, transparent, rgba(148, 163, 184, 0.8));
  animation: fall linear infinite;
}

.rain-drop.heavy {
  width: 2px;
  background: linear-gradient(to bottom, transparent, rgba(100, 116, 139, 0.9));
}

@keyframes fall {
  to {
    transform: translateY(110vh);
  }
}

/* Fire Animation */
.fire-particle {
  position: absolute;
  bottom: -20px;
  width: 10px;
  height: 10px;
  background: rgba(251, 146, 60, 0.6);
  border-radius: 50%;
  box-shadow: 0 0 10px 2px rgba(251, 146, 60, 0.4);
  animation: rise ease-out infinite;
  filter: blur(2px);
}

@keyframes rise {
  0% {
    transform: translateY(0) scale(1);
    opacity: 0;
  }
  20% {
    opacity: 1;
  }
  100% {
    transform: translateY(-40vh) scale(0);
    opacity: 0;
  }
}

/* Storm/Lightning Animation */
.lightning {
  position: absolute;
  inset: 0;
  background: rgba(255, 255, 255, 0.8);
  opacity: 0;
  animation: flash 4s infinite;
}

@keyframes flash {
  0%, 90%, 100% { opacity: 0; }
  92% { opacity: 0.6; }
  93% { opacity: 0; }
  94% { opacity: 0.4; }
  96% { opacity: 0; }
}
</style>
