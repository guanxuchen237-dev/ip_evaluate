/**
 * 认证状态管理 Composable
 * 提供用户登录、注册、登出和状态管理功能
 */

import { ref, computed, readonly } from 'vue'
import axios from 'axios'

const API_BASE = 'http://localhost:5000/api/auth'

// ============================================================
//  全局状态（跨组件共享）
// ============================================================

interface User {
    id: number
    username: string
    email: string
    role: 'user' | 'admin'
    avatar: string | null
    created_at?: string
}

const user = ref<User | null>(null)
const token = ref<string | null>(localStorage.getItem('auth_token'))
const loading = ref(false)

// ============================================================
//  Axios 拦截器（自动附加 JWT）
// ============================================================

// 请求拦截器：自动附加 token
axios.interceptors.request.use((config) => {
    const t = token.value
    if (t) {
        config.headers.Authorization = `Bearer ${t}`
    }
    return config
})

// 响应拦截器：token 过期自动登出
axios.interceptors.response.use(
    (response) => response,
    (error) => {
        if (error.response?.status === 401) {
            const code = error.response?.data?.code
            if (code === 'TOKEN_EXPIRED' || code === 'INVALID_TOKEN') {
                // token 失效，清除状态
                user.value = null
                token.value = null
                localStorage.removeItem('auth_token')
                // 跳转登录页（避免循环）
                if (window.location.pathname !== '/login' && window.location.pathname !== '/admin/login') {
                    window.location.href = '/login'
                }
            }
        }
        return Promise.reject(error)
    }
)

// ============================================================
//  Composable 导出
// ============================================================

export function useAuth() {
    const isLoggedIn = computed(() => !!token.value && !!user.value)
    const isAdmin = computed(() => user.value?.role === 'admin')

    /**
     * 用户登录
     */
    async function login(username: string, password: string) {
        loading.value = true
        try {
            const res = await axios.post(`${API_BASE}/login`, { username, password })
            token.value = res.data.token
            user.value = res.data.user
            localStorage.setItem('auth_token', res.data.token)
            return { success: true, user: res.data.user }
        } catch (error: any) {
            const msg = error.response?.data?.error || '登录失败，请稍后重试'
            return { success: false, error: msg }
        } finally {
            loading.value = false
        }
    }

    /**
     * 用户注册
     */
    async function register(username: string, email: string, password: string) {
        loading.value = true
        try {
            const res = await axios.post(`${API_BASE}/register`, { username, email, password })
            token.value = res.data.token
            user.value = res.data.user
            localStorage.setItem('auth_token', res.data.token)
            return { success: true, user: res.data.user }
        } catch (error: any) {
            const msg = error.response?.data?.error || '注册失败，请稍后重试'
            return { success: false, error: msg }
        } finally {
            loading.value = false
        }
    }

    /**
     * 获取当前用户信息（用于页面刷新后恢复状态）
     */
    async function fetchUser() {
        if (!token.value) return
        try {
            const res = await axios.get(`${API_BASE}/me`)
            user.value = res.data.user
        } catch {
            // token 失效，清除
            token.value = null
            user.value = null
            localStorage.removeItem('auth_token')
        }
    }

    /**
     * 登出
     */
    function logout() {
        token.value = null
        user.value = null
        localStorage.removeItem('auth_token')
    }

    return {
        user: readonly(user),
        token: readonly(token),
        loading: readonly(loading),
        isLoggedIn,
        isAdmin,
        login,
        register,
        logout,
        fetchUser
    }
}
