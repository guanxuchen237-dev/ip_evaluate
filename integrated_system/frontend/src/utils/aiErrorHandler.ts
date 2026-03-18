/**
 * AI接口错误处理工具
 * 统一处理Token限额超出和其他错误
 */

export interface AIError {
  error: string
  code?: string
  used?: number
  limit?: number
}

/**
 * 解析AI接口错误并返回用户友好的提示信息
 */
export function parseAIError(error: any): string {
  // 检查是否有响应数据
  if (!error.response?.data) {
    // 网络错误或其他异常
    return '网络连接失败，请检查网络后重试'
  }
  
  const data: AIError = error.response.data
  
  // Token限额超出
  if (data.code === 'TOKEN_LIMIT_EXCEEDED') {
    return `Token额度已用完 (已用: ${data.used?.toLocaleString() || 0} / 限额: ${data.limit?.toLocaleString() || 0})，请联系管理员`
  }
  
  // 未登录或Token过期
  if (data.code === 'NO_TOKEN' || data.code === 'TOKEN_EXPIRED' || data.code === 'INVALID_TOKEN') {
    return '登录已过期，请重新登录'
  }
  
  // 其他后端错误
  if (data.error) {
    return data.error
  }
  
  // 默认错误
  return '操作失败，请稍后重试'
}

/**
 * 显示AI错误Toast提示
 * 自动使用全局Toast组件
 */
export function showAIError(error: any): void {
  const message = parseAIError(error)
  
  // 使用全局Toast
  if (typeof window !== 'undefined' && (window as any).$toast) {
    (window as any).$toast.error(message, 8000) // 错误提示显示8秒
  } else {
    // 降级为原生alert
    alert(message)
  }
}

/**
 * 判断是否为Token限额错误
 */
export function isTokenLimitError(error: any): boolean {
  return error?.response?.data?.code === 'TOKEN_LIMIT_EXCEEDED'
}

/**
 * 判断是否需要重新登录
 */
export function isAuthError(error: any): boolean {
  const code = error?.response?.data?.code
  return code === 'NO_TOKEN' || code === 'TOKEN_EXPIRED' || code === 'INVALID_TOKEN'
}
