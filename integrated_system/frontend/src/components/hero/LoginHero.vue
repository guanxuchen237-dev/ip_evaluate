<script setup lang="ts">
/**
 * 登录页 3D 场景 —— 极简数学之美
 * 只保留：斐波那契球体 + 一条优雅的轨道环
 * 追求 "少即是多" 的克制美学
 */
import { onMounted, onBeforeUnmount } from 'vue'
// @ts-ignore
import * as THREE from 'three'

let scene: THREE.Scene
let camera: THREE.PerspectiveCamera
let renderer: THREE.WebGLRenderer
let animationId: number
let container: HTMLDivElement | null = null
let mainGroup: THREE.Group

let mouseX = 0
let mouseY = 0

onMounted(() => {
  container = document.getElementById('login-hero') as HTMLDivElement
  if (!container) return

  scene = new THREE.Scene()

  camera = new THREE.PerspectiveCamera(
    45,
    container.clientWidth / container.clientHeight,
    0.1,
    1000
  )
  camera.position.z = 7

  renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true })
  renderer.setSize(container.clientWidth, container.clientHeight)
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
  container.appendChild(renderer.domElement)

  mainGroup = new THREE.Group()
  // 整体稍微偏左，为文字留空间
  mainGroup.position.set(0.3, 0, 0)
  scene.add(mainGroup)

  // ========================================================
  // 1. 斐波那契球体 —— 黄金角分布粒子
  //    每个粒子按 137.5° 黄金角均匀铺满球面
  // ========================================================
  const particleCount = 500
  const goldenAngle = Math.PI * (3 - Math.sqrt(5))
  const sphereRadius = 2.2
  const positions: number[] = []
  const colors: number[] = []
  const sizes: number[] = []

  for (let i = 0; i < particleCount; i++) {
    const y = 1 - (i / (particleCount - 1)) * 2
    const r = Math.sqrt(1 - y * y)
    const theta = goldenAngle * i

    positions.push(
      Math.cos(theta) * r * sphereRadius,
      y * sphereRadius,
      Math.sin(theta) * r * sphereRadius
    )

    // 从顶部 slate-300 到底部 sky-400 的自然渐变
    const t = i / particleCount
    const cr = 0.70 - t * 0.35   // 0.70 → 0.35
    const cg = 0.74 - t * 0.08   // 0.74 → 0.66
    const cb = 0.80 + t * 0.12   // 0.80 → 0.92
    colors.push(cr, cg, cb)

    // 大小微变化，更自然
    sizes.push(0.03 + Math.random() * 0.02)
  }

  const fibGeo = new THREE.BufferGeometry()
  fibGeo.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3))
  fibGeo.setAttribute('color', new THREE.Float32BufferAttribute(colors, 3))

  const fibMat = new THREE.PointsMaterial({
    size: 0.035,
    transparent: true,
    opacity: 0.7,
    vertexColors: true,
    sizeAttenuation: true,
  })

  const fibSphere = new THREE.Points(fibGeo, fibMat)
  mainGroup.add(fibSphere)

  // ========================================================
  // 2. 经纬线（极简线框感，只画 3 条大圆弧）
  // ========================================================
  function createGreatCircle(radius: number, segments: number, rotX: number, rotY: number, opacity: number) {
    const pts: THREE.Vector3[] = []
    for (let i = 0; i <= segments; i++) {
      const angle = (i / segments) * Math.PI * 2
      pts.push(new THREE.Vector3(Math.cos(angle) * radius, 0, Math.sin(angle) * radius))
    }
    const geo = new THREE.BufferGeometry().setFromPoints(pts)
    const mat = new THREE.LineBasicMaterial({
      color: 0x94a3b8,
      transparent: true,
      opacity: opacity,
    })
    const line = new THREE.Line(geo, mat)
    line.rotation.x = rotX
    line.rotation.y = rotY
    return line
  }

  // 赤道
  mainGroup.add(createGreatCircle(2.35, 120, 0, 0, 0.15))
  // 倾斜 60°
  mainGroup.add(createGreatCircle(2.35, 120, Math.PI / 3, 0.5, 0.1))
  // 倾斜 -45°
  mainGroup.add(createGreatCircle(2.35, 120, -Math.PI / 4, -0.3, 0.08))

  // ========================================================
  // 3. 轨道环 —— 单条优雅的倾斜环
  // ========================================================
  const orbitGeo = new THREE.TorusGeometry(3.0, 0.008, 16, 200)
  const orbitMat = new THREE.MeshBasicMaterial({
    color: 0x94a3b8,
    transparent: true,
    opacity: 0.18,
  })
  const orbit = new THREE.Mesh(orbitGeo, orbitMat)
  orbit.rotation.x = Math.PI / 2.8
  orbit.rotation.z = 0.15
  mainGroup.add(orbit)

  // 轨道上的几个亮点（像卫星）
  const dotCount = 5
  const dotGeo = new THREE.SphereGeometry(0.035, 8, 8)
  const dots: THREE.Mesh[] = []
  for (let i = 0; i < dotCount; i++) {
    const dotMat = new THREE.MeshBasicMaterial({
      color: i === 0 ? 0x38bdf8 : 0x94a3b8,
      transparent: true,
      opacity: i === 0 ? 0.8 : 0.4,
    })
    const dot = new THREE.Mesh(dotGeo, dotMat)
    dots.push(dot)
    mainGroup.add(dot)
  }

  // ========================================================
  // 动画
  // ========================================================
  const clock = new THREE.Clock()

  function animate() {
    animationId = requestAnimationFrame(animate)
    const t = clock.getElapsedTime()

    // 球体缓慢自转
    fibSphere.rotation.y = t * 0.04

    // 轨道微旋
    orbit.rotation.z = 0.15 + t * 0.01

    // 卫星沿轨道运动
    for (let i = 0; i < dotCount; i++) {
      const angle = t * 0.3 + (i * Math.PI * 2) / dotCount
      const r = 3.0
      const x = Math.cos(angle) * r
      const z = Math.sin(angle) * r
      // 应用轨道倾斜
      const cosRx = Math.cos(Math.PI / 2.8)
      const sinRx = Math.sin(Math.PI / 2.8)
      dots[i]!.position.set(x, z * sinRx, z * cosRx)
    }

    // 鼠标视差（非常轻微）
    const targetRX = (mouseY - window.innerHeight / 2) * 0.00015
    const targetRY = (mouseX - window.innerWidth / 2) * 0.00015
    mainGroup.rotation.x += 0.03 * (targetRX - mainGroup.rotation.x)
    mainGroup.rotation.y += 0.03 * (targetRY + t * 0.008 - mainGroup.rotation.y)

    renderer.render(scene, camera)
  }
  animate()

  const handleResize = () => {
    if (!container) return
    camera.aspect = container.clientWidth / container.clientHeight
    camera.updateProjectionMatrix()
    renderer.setSize(container.clientWidth, container.clientHeight)
  }

  const handleMouseMove = (e: MouseEvent) => {
    mouseX = e.clientX
    mouseY = e.clientY
  }

  window.addEventListener('resize', handleResize)
  document.addEventListener('mousemove', handleMouseMove)
})

onBeforeUnmount(() => {
  if (animationId) cancelAnimationFrame(animationId)
  if (renderer && container) {
    container.removeChild(renderer.domElement)
    renderer.dispose()
  }
})
</script>

<template>
  <div id="login-hero" class="w-full h-full" />
</template>
