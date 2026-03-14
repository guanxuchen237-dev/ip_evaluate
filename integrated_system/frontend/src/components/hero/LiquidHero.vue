<script setup lang="ts">
import { onMounted, onBeforeUnmount } from 'vue'
// @ts-ignore
import * as THREE from 'three'

interface Props {
  disableParallax?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  disableParallax: false
})

let scene: THREE.Scene
let camera: THREE.PerspectiveCamera
let renderer: THREE.WebGLRenderer
let sphere: THREE.Group
let torus: THREE.Group
let animationId: number
let container: HTMLDivElement | null = null

// Mouse interaction
let mouseX = 0
let mouseY = 0
let targetRotationX = 0
let targetRotationY = 0

onMounted(() => {
  container = document.getElementById('liquid-hero') as HTMLDivElement
  if (!container) return

  // Scene
  scene = new THREE.Scene()
  // Fog for depth
  scene.fog = new THREE.FogExp2(0xffffff, 0.02)

  // Camera
  camera = new THREE.PerspectiveCamera(
    45,
    container.clientWidth / container.clientHeight,
    0.1,
    1000
  )
  camera.position.z = 6

  // Renderer
  renderer = new THREE.WebGLRenderer({ 
    antialias: true, 
    alpha: true 
  })
  renderer.setSize(container.clientWidth, container.clientHeight)
  renderer.setPixelRatio(window.devicePixelRatio)
  container.appendChild(renderer.domElement)

  // --------------------------------------------------------
  // 1. Math Sphere Group (Structure + Nodes)
  // --------------------------------------------------------
  sphere = new THREE.Group()
  scene.add(sphere)

  // A. The Wireframe Lattice
  const geoLattice = new THREE.IcosahedronGeometry(1.6, 2)
  const matLattice = new THREE.MeshBasicMaterial({
    color: 0x334155, // Slate-700
    wireframe: true,
    transparent: true,
    opacity: 0.3
  })
  const meshLattice = new THREE.Mesh(geoLattice, matLattice)
  sphere.add(meshLattice)

  // B. The Mathematical Nodes (Vertices)
  const matNodes = new THREE.PointsMaterial({
    color: 0x3b82f6, // Blue-500 points
    size: 0.04,
    transparent: true,
    opacity: 0.8
  })
  const meshNodes = new THREE.Points(geoLattice, matNodes)
  sphere.add(meshNodes)

  // C. Inner Core (The "Kernel")
  const geoCore = new THREE.DodecahedronGeometry(0.8)
  const matCore = new THREE.MeshBasicMaterial({
    color: 0x64748b, // Slate-500
    wireframe: true,
    transparent: true,
    opacity: 0.5
  })
  const meshCore = new THREE.Mesh(geoCore, matCore)
  sphere.add(meshCore)


  // --------------------------------------------------------
  // 2. The Torus Function (Orbiting Ring)
  // --------------------------------------------------------
  torus = new THREE.Group()
  torus.position.set(1.2, 0, 0)
  torus.rotation.x = Math.PI / 2.5
  scene.add(torus)

  const geoTorus = new THREE.TorusGeometry(1.5, 0.05, 16, 100)
  const matTorus = new THREE.MeshBasicMaterial({
    color: 0x0ea5e9, // Sky-500
    transparent: true,
    opacity: 0.6
  })
  const meshTorus = new THREE.Mesh(geoTorus, matTorus)
  torus.add(meshTorus)

  // Add particles to Torus path for "Data Stream" look
  const geoTorusPoints = new THREE.TorusGeometry(1.5, 0.05, 16, 50)
  const matTorusPoints = new THREE.PointsMaterial({
    color: 0x0ea5e9,
    size: 0.03
  })
  const pointsTorus = new THREE.Points(geoTorusPoints, matTorusPoints)
  torus.add(pointsTorus)

  // Animation
  function animate() {
    animationId = requestAnimationFrame(animate)
    
    // Constant mathematical rotation
    sphere.rotation.y += 0.001
    meshCore.rotation.x -= 0.002 // Counter-rotation
    meshCore.rotation.z -= 0.002

    torus.rotation.z -= 0.002
    
    // Mouse Interaction (Parallax)
    if (!props.disableParallax) {
       // Smooth ease-out
       targetRotationX = (mouseY - window.innerHeight / 2) * 0.0005
       targetRotationY = (mouseX - window.innerWidth / 2) * 0.0005
       
       sphere.rotation.x += 0.05 * (targetRotationX - sphere.rotation.x)
       sphere.rotation.y += 0.05 * (targetRotationY - sphere.rotation.y)
    }
    
    renderer.render(scene, camera)
  }
  animate()

  // Event Listeners
  const handleResize = () => {
    if (!container) return
    camera.aspect = container.clientWidth / container.clientHeight
    camera.updateProjectionMatrix()
    renderer.setSize(container.clientWidth, container.clientHeight)
  }
  
  const handleMouseMove = (event: MouseEvent) => {
    if (props.disableParallax) return
    mouseX = event.clientX
    mouseY = event.clientY
  }

  window.addEventListener('resize', handleResize)
  document.addEventListener('mousemove', handleMouseMove)
})

onBeforeUnmount(() => {
  if (animationId) {
    cancelAnimationFrame(animationId)
  }
  if (renderer && container) {
    container.removeChild(renderer.domElement)
    renderer.dispose()
  }
  document.removeEventListener('mousemove', () => {})
})
</script>

<template>
  <div id="liquid-hero" class="w-full h-full" />
</template>
