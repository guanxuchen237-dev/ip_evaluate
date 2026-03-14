<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import * as THREE from 'three'

interface NodeData {
  id: string
  title: string
  author: string
  genre: string
  position: [number, number, number]
  connections: string[]
  color: string
  size: number
}

const canvasRef = ref<HTMLCanvasElement | null>(null)
const hoveredNode = ref<NodeData | null>(null)
const tooltipPos = ref({ x: 0, y: 0 })

const nodes: NodeData[] = [
  { id: '1', title: '诡秘之主', author: '爱潜水的乌贼', genre: '奇幻悬疑', position: [0, 0, 0], connections: ['2', '3', '5'], color: '#60A5FA', size: 0.8 },
  { id: '2', title: '全职高手', author: '蝴蝶蓝', genre: '电竞热血', position: [3, 1, 2], connections: ['1', '4'], color: '#34D399', size: 0.7 },
  { id: '3', title: '盗墓笔记', author: '南派三叔', genre: '冒险悬疑', position: [-2, 2, 1], connections: ['1', '6'], color: '#F472B6', size: 0.75 },
  { id: '4', title: '斗破苍穹', author: '天蚕土豆', genre: '玄幻热血', position: [2, -2, -1], connections: ['2', '5'], color: '#FBBF24', size: 0.85 },
  { id: '5', title: '庆余年', author: '猫腻', genre: '权谋古风', position: [-1, -1, 3], connections: ['1', '4', '7'], color: '#A78BFA', size: 0.7 },
  { id: '6', title: '鬼吹灯', author: '天下霸唱', genre: '冒险悬疑', position: [-3, 0, -2], connections: ['3'], color: '#F472B6', size: 0.65 },
  { id: '7', title: '琅琊榜', author: '海宴', genre: '权谋古风', position: [1, 2, -2], connections: ['5'], color: '#A78BFA', size: 0.6 },
  { id: '8', title: '三体', author: '刘慈欣', genre: '科幻', position: [-2, -2, -2], connections: ['9'], color: '#06B6D4', size: 0.9 },
  { id: '9', title: '流浪地球', author: '刘慈欣', genre: '科幻', position: [0, -3, 0], connections: ['8'], color: '#06B6D4', size: 0.65 },
]

let scene: THREE.Scene
let camera: THREE.PerspectiveCamera
let renderer: THREE.WebGLRenderer
let nodeMeshes: Map<string, THREE.Mesh> = new Map()
let animationId: number
let mouseX = 0
let mouseY = 0

function createGlassBubble(node: NodeData): THREE.Group {
  const group = new THREE.Group()
  
  // Glow effect
  const glowGeometry = new THREE.SphereGeometry(node.size * 1.2, 32, 32)
  const glowMaterial = new THREE.MeshBasicMaterial({
    color: node.color,
    transparent: true,
    opacity: 0.15
  })
  const glow = new THREE.Mesh(glowGeometry, glowMaterial)
  group.add(glow)
  
  // Main glass bubble
  const bubbleGeometry = new THREE.SphereGeometry(node.size, 32, 32)
  const bubbleMaterial = new THREE.MeshPhysicalMaterial({
    color: node.color,
    transparent: true,
    opacity: 0.6,
    roughness: 0.1,
    metalness: 0.1,
    transmission: 0.5,
    thickness: 0.5,
    clearcoat: 1,
    clearcoatRoughness: 0
  })
  const bubble = new THREE.Mesh(bubbleGeometry, bubbleMaterial)
  bubble.userData = { nodeData: node }
  group.add(bubble)
  nodeMeshes.set(node.id, bubble)
  
  // Inner core
  const coreGeometry = new THREE.SphereGeometry(node.size * 0.3, 16, 16)
  const coreMaterial = new THREE.MeshBasicMaterial({ color: node.color })
  const core = new THREE.Mesh(coreGeometry, coreMaterial)
  group.add(core)
  
  group.position.set(...node.position)
  
  return group
}

function createConnectionLine(start: [number, number, number], end: [number, number, number], color: string) {
  const curve = new THREE.QuadraticBezierCurve3(
    new THREE.Vector3(...start),
    new THREE.Vector3(
      (start[0] + end[0]) / 2 + (Math.random() - 0.5) * 0.5,
      (start[1] + end[1]) / 2 + (Math.random() - 0.5) * 0.5,
      (start[2] + end[2]) / 2 + (Math.random() - 0.5) * 0.5
    ),
    new THREE.Vector3(...end)
  )
  
  const points = curve.getPoints(30)
  const geometry = new THREE.BufferGeometry().setFromPoints(points)
  const material = new THREE.LineBasicMaterial({ 
    color, 
    transparent: true, 
    opacity: 0.3 
  })
  
  return new THREE.Line(geometry, material)
}

function onMouseMove(event: MouseEvent) {
  if (!canvasRef.value) return
  
  const rect = canvasRef.value.getBoundingClientRect()
  mouseX = ((event.clientX - rect.left) / rect.width) * 2 - 1
  mouseY = -((event.clientY - rect.top) / rect.height) * 2 + 1
  
  // Raycasting for hover detection
  const raycaster = new THREE.Raycaster()
  raycaster.setFromCamera(new THREE.Vector2(mouseX, mouseY), camera)
  
  const meshArray = [...nodeMeshes.values()]
  const intersects = raycaster.intersectObjects(meshArray)
  const firstHit = intersects[0]
  
  if (firstHit && firstHit.object.userData?.nodeData) {
    const nodeData = firstHit.object.userData.nodeData as NodeData
    hoveredNode.value = nodeData
    tooltipPos.value = { x: event.clientX, y: event.clientY }
    
    // Scale up hovered node
    nodeMeshes.forEach((mesh, id) => {
      const targetScale = id === nodeData.id ? 1.3 : 1.0
      const target = new THREE.Vector3(targetScale, targetScale, targetScale)
      mesh.scale.lerp(target, 0.1)
    })
  } else {
    hoveredNode.value = null
    
    // Reset all scales
    nodeMeshes.forEach(mesh => {
      const target = new THREE.Vector3(1, 1, 1)
      mesh.scale.lerp(target, 0.1)
    })
  }
}

function animate() {
  animationId = requestAnimationFrame(animate)
  
  // Auto-rotate camera
  camera.position.x = Math.sin(Date.now() * 0.0001) * 12
  camera.position.z = Math.cos(Date.now() * 0.0001) * 12
  camera.lookAt(0, 0, 0)
  
  // Rotate nodes
  nodeMeshes.forEach(mesh => {
    mesh.rotation.y += 0.005
  })
  
  renderer.render(scene, camera)
}

onMounted(() => {
  if (!canvasRef.value) return
  
  // Scene setup
  scene = new THREE.Scene()
  // 使用透明背景，让glass-card的背景色显示
  scene.background = null
  
  // Camera
  camera = new THREE.PerspectiveCamera(
    60,
    canvasRef.value.clientWidth / canvasRef.value.clientHeight,
    0.1,
    1000
  )
  camera.position.set(0, 0, 10)
  
  // Renderer
  renderer = new THREE.WebGLRenderer({ 
    canvas: canvasRef.value,
    antialias: true,
    alpha: true
  })
  renderer.setSize(canvasRef.value.clientWidth, canvasRef.value.clientHeight)
  renderer.setPixelRatio(window.devicePixelRatio)
  
  // Lights
  const ambientLight = new THREE.AmbientLight(0xffffff, 0.6)
  scene.add(ambientLight)
  
  const pointLight1 = new THREE.PointLight(0xffffff, 1)
  pointLight1.position.set(10, 10, 10)
  scene.add(pointLight1)
  
  const pointLight2 = new THREE.PointLight(0xa78bfa, 0.5)
  pointLight2.position.set(-10, -10, -10)
  scene.add(pointLight2)
  
  // Create connections (before nodes so they're behind)
  const processed = new Set<string>()
  nodes.forEach(node => {
    node.connections.forEach(targetId => {
      const key = [node.id, targetId].sort().join('-')
      if (!processed.has(key)) {
        processed.add(key)
        const target = nodes.find(n => n.id === targetId)
        if (target) {
          const line = createConnectionLine(node.position, target.position, node.color)
          scene.add(line)
        }
      }
    })
  })
  
  // Create nodes
  nodes.forEach(node => {
    const bubble = createGlassBubble(node)
    scene.add(bubble)
  })
  
  // Event listeners
  canvasRef.value.addEventListener('mousemove', onMouseMove)
  
  // Handle resize
  const handleResize = () => {
    if (!canvasRef.value) return
    camera.aspect = canvasRef.value.clientWidth / canvasRef.value.clientHeight
    camera.updateProjectionMatrix()
    renderer.setSize(canvasRef.value.clientWidth, canvasRef.value.clientHeight)
  }
  window.addEventListener('resize', handleResize)
  
  // Start animation
  animate()
  
  // Cleanup
  onUnmounted(() => {
    cancelAnimationFrame(animationId)
    window.removeEventListener('resize', handleResize)
    if (canvasRef.value) {
      canvasRef.value.removeEventListener('mousemove', onMouseMove)
    }
    renderer.dispose()
  })
})
</script>

<template>
  <div class="relative w-full h-full">
    <!-- Gradient blobs background -->
    <div class="absolute inset-0 overflow-hidden pointer-events-none">
      <div class="absolute top-1/4 left-1/4 w-96 h-96 bg-blue-200/30 rounded-full blur-3xl animate-float" />
      <div class="absolute bottom-1/4 right-1/4 w-80 h-80 bg-purple-200/30 rounded-full blur-3xl animate-float" style="animation-delay: -2s;" />
      <div class="absolute top-1/2 right-1/3 w-64 h-64 bg-cyan-200/20 rounded-full blur-3xl animate-float" style="animation-delay: -4s;" />
    </div>
    
    <!-- Three.js Canvas -->
    <canvas ref="canvasRef" class="w-full h-full" />
    
    <!-- Hover Tooltip -->
    <div 
      v-if="hoveredNode"
      :style="{ left: `${tooltipPos.x + 20}px`, top: `${tooltipPos.y}px` }"
      class="fixed z-50 pointer-events-none animate-scale-in"
    >
      <div class="bg-slate-900/95 backdrop-blur-lg rounded-2xl p-5 min-w-[200px] shadow-2xl border border-white/20">
        <h4 class="font-bold text-white text-base mb-2">{{ hoveredNode.title }}</h4>
        <p class="text-slate-300 text-sm mb-3">{{ hoveredNode.author }}</p>
        <div class="flex items-center gap-2">
          <span 
            class="px-3 py-1 rounded-full text-xs font-medium text-white shadow-lg"
            :style="{ backgroundColor: hoveredNode.color }"
          >
            {{ hoveredNode.genre }}
          </span>
        </div>
      </div>
    </div>
    
    <!-- Legend -->
    <div class="absolute bottom-6 left-6 bg-white/95 backdrop-blur-lg rounded-2xl p-5 shadow-xl border border-slate-200">
      <p class="text-xs font-semibold text-slate-600 mb-3 uppercase tracking-wider">Genre Legend</p>
      <div class="space-y-2.5">
        <div 
          v-for="item in [
            { color: '#60A5FA', label: '奇幻悬疑' },
            { color: '#34D399', label: '电竞热血' },
            { color: '#F472B6', label: '冒险悬疑' },
            { color: '#A78BFA', label: '权谋古风' },
            { color: '#06B6D4', label: '科幻' },
          ]"
          :key="item.label"
          class="flex items-center gap-3"
        >
          <div class="w-4 h-4 rounded-full shadow-sm" :style="{ backgroundColor: item.color }" />
          <span class="text-sm font-medium text-slate-700">{{ item.label }}</span>
        </div>
      </div>
    </div>
    
    <!-- Instructions -->
    <div class="absolute top-6 right-6 bg-white/95 backdrop-blur-lg rounded-2xl p-4 shadow-xl border border-slate-200">
      <p class="text-sm font-medium text-slate-700">
        🖱️ Hover for details · Auto-rotating · {{ nodes.length }} IPs
      </p>
    </div>
  </div>
</template>

<style scoped>
@keyframes float {
  0%, 100% { transform: translateY(0) translateX(0); }
  33% { transform: translateY(-20px) translateX(10px); }
  66% { transform: translateY(10px) translateX(-10px); }
}

.animate-float {
  animation: float 8s ease-in-out infinite;
}

@keyframes scale-in {
  from { opacity: 0; transform: scale(0.9); }
  to { opacity: 1; transform: scale(1); }
}

.animate-scale-in {
  animation: scale-in 0.2s ease-out;
}
</style>
