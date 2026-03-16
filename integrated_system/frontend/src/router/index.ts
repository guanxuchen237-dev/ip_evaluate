import { createRouter, createWebHistory } from 'vue-router'
import Dashboard from '../views/Dashboard.vue'
import RealtimeView from '../views/RealtimeView.vue'
import SearchView from '../views/SearchView.vue'
import PrivateView from '../views/PrivateView.vue'
import SettingsView from '../views/SettingsView.vue'
import DataMonitorView from '../views/DataMonitorView.vue'
import FocusGroupView from '../views/FocusGroupView.vue'
import PredictionView from '../views/PredictionView.vue'
import ReaderSpaceView from '../views/ReaderSpaceView.vue'
import LibraryView from '../views/LibraryView.vue'
import NotFound from '../views/NotFound.vue'
import LoginView from '../views/LoginView.vue'


const router = createRouter({
    history: createWebHistory(import.meta.env.BASE_URL || '/'),
    routes: [
        // ============================================
        //  公开路由（无需登录）
        // ============================================
        {
            path: '/login',
            name: 'login',
            component: LoginView,
            meta: { guest: true }
        },

        // ============================================
        //  用户路由（需登录）
        // ============================================
        {
            path: '/admin',
            name: 'admin-dashboard',
            component: () => import('../views/AdminDashboard.vue'),
            meta: { requiresAuth: true, requiresAdmin: true }
        },
        {
            path: '/',
            name: 'home',
            component: Dashboard,
            meta: { requiresAuth: false }
        },
        {
            path: '/library',
            name: 'library',
            component: LibraryView,
            meta: { requiresAuth: false }
        },
        {
            path: '/search',
            name: 'search',
            component: SearchView,
            meta: { requiresAuth: true }
        },
        {
            path: '/prediction',
            name: 'prediction',
            component: PredictionView,
            meta: { requiresAuth: true }
        },
        {
            path: '/chat',
            name: 'chat',
            component: () => import('../views/CharacterHub.vue'),
            meta: { requiresAuth: true }
        },
        {
            path: '/library/detail',
            name: 'book-detail',
            component: () => import('../views/BookDetailView.vue'),
            meta: { requiresAuth: false }
        },
        {
            path: '/reader-space',
            name: 'reader-space',
            component: ReaderSpaceView,
            meta: { requiresAuth: true }
        },
        {
            path: '/profile',
            name: 'profile',
            component: () => import('../views/ProfileView.vue'),
            meta: { requiresAuth: true }
        },

        // ============================================
        //  管理员路由（需管理员权限）
        // ============================================
        {
            path: '/settings',
            name: 'settings',
            component: SettingsView,
            meta: { requiresAuth: true, requiresAdmin: true }
        },
        {
            path: '/monitor',
            name: 'monitor',
            component: DataMonitorView,
            meta: { requiresAuth: true, requiresAdmin: true }
        },
        {
            path: '/focus-group',
            name: 'focus-group',
            component: FocusGroupView,
            meta: { requiresAuth: true, requiresAdmin: true }
        },
        {
            path: '/realtime',
            name: 'realtime',
            component: RealtimeView,
            meta: { requiresAuth: true, requiresAdmin: true }
        },
        {
            path: '/admin/book/detail',
            name: 'admin-book-detail',
            component: () => import('../views/AdminBookDetailView.vue'),
            meta: { requiresAuth: true, requiresAdmin: true }
        },
        {
            path: '/private',
            name: 'private',
            component: PrivateView,
            meta: { requiresAuth: true, requiresAdmin: true }
        },

        // ============================================
        //  404
        // ============================================
        {
            path: '/:pathMatch(.*)*',
            name: 'not-found',
            component: NotFound
        }
    ]
})

// ============================================
//  全局路由守卫
// ============================================
router.beforeEach((to, _from, next) => {
    const token = localStorage.getItem('auth_token')
    const requiresAuth = to.meta.requiresAuth as boolean
    const requiresAdmin = to.meta.requiresAdmin as boolean
    const isGuest = to.meta.guest as boolean

    // 已登录用户访问登录页，重定向到首页
    if (isGuest && token) {
        next({ name: 'home' })
        return
    }

    // 需要认证但未登录，重定向到登录页
    if (requiresAuth && !token) {
        next({ name: 'login' })
        return
    }

    // 需要管理员权限，检查 token 中的角色
    if (requiresAdmin && token) {
        try {
            // 解析 JWT payload（不做签名验证，签名由后端验证）
            const parts = (token as string).split('.')
            if (parts.length < 2 || !parts[1]) throw new Error('Invalid token')
            const payload = JSON.parse(atob(parts[1]))
            if (payload.role !== 'admin') {
                next({ name: 'home' })
                return
            }
        } catch {
            next({ name: 'login' })
            return
        }
    }

    next()
})

export default router
