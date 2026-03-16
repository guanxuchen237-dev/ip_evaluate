import { createApp } from 'vue'
import './style.css'
import App from './App.vue'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'
import Dashboard from './views/Dashboard.vue'
import Prediction from './views/Prediction.vue'
import { createRouter, createWebHistory } from 'vue-router'

const routes = [
    { path: '/', component: Dashboard },
    { path: '/predict', component: Prediction },
]

const router = createRouter({
    history: createWebHistory(),
    routes,
})

const app = createApp(App)

for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
    app.component(key, component)
}

app.use(ElementPlus)
app.use(router)
app.mount('#app')
