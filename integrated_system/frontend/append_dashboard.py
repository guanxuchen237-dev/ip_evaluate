import os

filepath = 'd:/ip-lumina-main/integrated_system/frontend/src/views/Dashboard.vue'
with open(filepath, 'r', encoding='utf-8') as f:
    text = f.read()

# insert import
if 'LongTermTrendChart' not in text:
    text = text.replace('import GeoMap from "@/components/charts/GeoMap.vue";', 'import GeoMap from "@/components/charts/GeoMap.vue";\nimport LongTermTrendChart from "@/components/charts/LongTermTrendChart.vue";')

# update bottom
old_bottom = """      </div>
    </div>
  </EditorialLayout>"""

new_bottom = """      </div>

      <!-- 底部趋势层：长周期表现 -->
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-4 mt-6">
        <div class="h-[280px]"> 
          <LongTermTrendChart platform="qidian" title="起点顶级大作长线推荐票趋势" />
        </div>
        <div class="h-[280px]">
          <LongTermTrendChart platform="zongheng" title="纵横现象级作品长线月票趋势" />
        </div>
      </div>

    </div>
  </EditorialLayout>"""

if '底部趋势层' not in text:
    text = text.replace(old_bottom, new_bottom)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(text)
print('Dashboard.vue replaced!')
