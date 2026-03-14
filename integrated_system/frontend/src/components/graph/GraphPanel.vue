<template>
  <div class="graph-panel w-full h-full relative bg-white/50 rounded-3xl overflow-hidden backdrop-blur-sm border border-slate-200 shadow-sm">
    <!-- Header Controls -->
    <div class="absolute top-4 right-4 z-10 flex gap-2">
      <button 
        @click="centerGraph"
        class="p-2 bg-white rounded-xl shadow-sm border border-slate-200 text-slate-600 hover:text-indigo-600 hover:border-indigo-200 transition-all active:scale-95"
        title="Center View"
      >
        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-focus"><circle cx="12" cy="12" r="3"/><path d="M3 7V5a2 2 0 0 1 2-2h2"/><path d="M17 3h2a2 2 0 0 1 2 2v2"/><path d="M21 17v2a2 2 0 0 1-2 2h-2"/><path d="M7 21H5a2 2 0 0 1-2-2v-2"/></svg>
      </button>
      <button 
        @click="zoomIn"
        class="p-2 bg-white rounded-xl shadow-sm border border-slate-200 text-slate-600 hover:text-indigo-600 hover:border-indigo-200 transition-all active:scale-95"
        title="Zoom In"
      >
        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="5" x2="12" y2="19"></line><line x1="5" y1="12" x2="19" y2="12"></line></svg>
      </button>
      <button 
        @click="zoomOut"
        class="p-2 bg-white rounded-xl shadow-sm border border-slate-200 text-slate-600 hover:text-indigo-600 hover:border-indigo-200 transition-all active:scale-95"
        title="Zoom Out"
      >
        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="5" y1="12" x2="19" y2="12"></line></svg>
      </button>
    </div>

    <!-- Graph Container -->
    <div ref="graphContainer" class="w-full h-full cursor-grab active:cursor-grabbing"></div>

    <!-- Legend -->
    <div class="absolute bottom-4 left-4 bg-white/90 backdrop-blur rounded-2xl p-4 shadow-sm border border-slate-200">
      <h4 class="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">实体类型</h4>
      <div class="space-y-1.5">
        <div v-for="type in entityTypes" :key="type.name" class="flex items-center gap-2">
          <span class="w-2.5 h-2.5 rounded-full" :style="{ backgroundColor: type.color }"></span>
          <span class="text-xs text-slate-600 font-medium">{{ type.name }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch } from 'vue'
import * as d3 from 'd3'

const props = defineProps({
  data: {
    type: Object,
    default: () => ({ nodes: [], edges: [] })
  }
})

const graphContainer = ref(null)
const width = ref(0)
const height = ref(0)
let simulation = null
let svg = null
let g = null // Main group for zoom
let zoom = null

// Light Theme Colors (Apple-style pastel/vibrant mix)
const colors = [
  '#6366f1', // Indigo
  '#ec4899', // Pink
  '#10b981', // Emerald
  '#f59e0b', // Amber
  '#8b5cf6', // Violet
  '#3b82f6', // Blue
  '#ef4444', // Red
]

const entityTypes = ref([])

onMounted(() => {
  if (graphContainer.value) {
    width.value = graphContainer.value.clientWidth
    height.value = graphContainer.value.clientHeight
    initGraph()
    if (props.data.nodes.length > 0) {
      updateGraph(props.data)
    }
    
    window.addEventListener('resize', handleResize)
  }
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  if (simulation) simulation.stop()
})

const handleResize = () => {
  if (graphContainer.value) {
    width.value = graphContainer.value.clientWidth
    height.value = graphContainer.value.clientHeight
    if (svg) {
      svg.attr('width', width.value).attr('height', height.value)
      if (simulation) {
        simulation.force('center', d3.forceCenter(width.value / 2, height.value / 2))
        simulation.alpha(0.3).restart()
      }
    }
  }
}

const initGraph = () => {
  svg = d3.select(graphContainer.value)
    .append('svg')
    .attr('width', width.value)
    .attr('height', height.value)
    .attr('viewBox', [0, 0, width.value, height.value])

  // Define arrow marker
  svg.append('defs').selectAll('marker')
    .data(['end'])
    .enter().append('marker')
    .attr('id', 'arrow')
    .attr('viewBox', '0 -5 10 10')
    .attr('refX', 25) // Offset to not overlap node
    .attr('refY', 0)
    .attr('markerWidth', 6)
    .attr('markerHeight', 6)
    .attr('orient', 'auto')
    .append('path')
    .attr('d', 'M0,-5L10,0L0,5')
    .attr('fill', '#cbd5e1') // Slate 300

  g = svg.append('g')

  zoom = d3.zoom()
    .scaleExtent([0.1, 4])
    .on('zoom', (event) => {
      g.attr('transform', event.transform)
    })

  svg.call(zoom)
}

const centerGraph = () => {
  svg.transition().duration(750).call(
    zoom.transform,
    d3.zoomIdentity.translate(width.value / 2, height.value / 2).scale(1).translate(-width.value / 2, -height.value / 2)
  )
}

const zoomIn = () => {
  svg.transition().duration(300).call(zoom.scaleBy, 1.2)
}

const zoomOut = () => {
  svg.transition().duration(300).call(zoom.scaleBy, 0.8)
}

const updateGraph = (graphData) => {
  if (!svg) return
  
  // Compute entity types for legend
  const types = new Set()
  graphData.nodes.forEach(n => {
    if (n.labels && n.labels.length > 0) types.add(n.labels[0])
    else types.add('Unknown')
  })
  
  const typeArray = Array.from(types)
  const colorScale = d3.scaleOrdinal(colors).domain(typeArray)
  
  entityTypes.value = typeArray.map(t => ({
    name: t,
    color: colorScale(t)
  }))

  // Clear previous
  g.selectAll('*').remove()

  const links = graphData.edges.map(d => ({ ...d, source: d.source_node_uuid, target: d.target_node_uuid }))
  const nodes = graphData.nodes.map(d => ({ ...d, id: d.uuid }))

  simulation = d3.forceSimulation(nodes)
    .force('link', d3.forceLink(links).id(d => d.id).distance(120))
    .force('charge', d3.forceManyBody().strength(-800))
    .force('center', d3.forceCenter(width.value / 2, height.value / 2))
    .force('collide', d3.forceCollide(50).strength(0.7))
    .force('x', d3.forceX(width.value / 2).strength(0.05))
    .force('y', d3.forceY(height.value / 2).strength(0.05))

  const link = g.append('g')
    .attr('stroke', '#cbd5e1') // Light gray edges
    .attr('stroke-opacity', 0.6)
    .selectAll('line')
    .data(links)
    .join('line')
    .attr('stroke-width', 2)
    .attr('marker-end', 'url(#arrow)')

  const linkLabel = g.append('g')
    .selectAll('text')
    .data(links)
    .join('text')
    .text(d => d.name)
    .attr('font-size', '11px')
    .attr('fill', '#94a3b8') // Slate 400
    .attr('text-anchor', 'middle')
    .attr('dy', -5)

  const node = g.append('g')
    .attr('stroke', '#fff')
    .attr('stroke-width', 2)
    .selectAll('circle')
    .data(nodes)
    .join('circle')
    .attr('r', 24)
    .attr('fill', d => colorScale(d.labels?.[0] || 'Unknown'))
    .attr('filter', 'drop-shadow(0px 2px 4px rgba(0,0,0,0.1))')
    .call(drag(simulation))

  // Node Labels
  const label = g.append('g')
    .selectAll('text')
    .data(nodes)
    .join('text')
    .text(d => d.name)
    .attr('font-size', '12px')
    .attr('font-weight', '500')
    .attr('fill', '#1e293b') // Slate 800
    .attr('text-anchor', 'middle')
    .attr('dy', 40) // Below node
    .style('pointer-events', 'none')
    .style('text-shadow', '0 1px 2px rgba(255,255,255,0.8)')

  simulation.on('tick', () => {
    link
      .attr('x1', d => d.source.x)
      .attr('y1', d => d.source.y)
      .attr('x2', d => d.target.x)
      .attr('y2', d => d.target.y)

    linkLabel
      .attr('x', d => (d.source.x + d.target.x) / 2)
      .attr('y', d => (d.source.y + d.target.y) / 2)

    node
      .attr('cx', d => d.x)
      .attr('cy', d => d.y)

    label
      .attr('x', d => d.x)
      .attr('y', d => d.y)
  })
}

const drag = (simulation) => {
  function dragstarted(event) {
    if (!event.active) simulation.alphaTarget(0.3).restart()
    event.subject.fx = event.subject.x
    event.subject.fy = event.subject.y
  }

  function dragged(event) {
    event.subject.fx = event.x
    event.subject.fy = event.y
  }

  function dragended(event) {
    if (!event.active) simulation.alphaTarget(0)
    event.subject.fx = null
    event.subject.fy = null
  }

  return d3.drag()
    .on('start', dragstarted)
    .on('drag', dragged)
    .on('end', dragended)
}

// Watch for data changes
watch(() => props.data, (newData) => {
  if (newData) updateGraph(newData)
}, { deep: true })

</script>

<style scoped>
/* Optional: Add custom transitions if needed */
</style>
