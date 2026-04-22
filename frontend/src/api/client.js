import axios from 'axios'

const apiClient = axios.create({
  baseURL: '/api',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// 请求拦截器
apiClient.interceptors.request.use(
  config => config,
  error => Promise.reject(error)
)

// 响应拦截器
apiClient.interceptors.response.use(
  response => response.data,
  error => {
    console.error('API Error:', error)
    return Promise.reject(error)
  }
)

// 获取对话列表
export async function getConversations() {
  return apiClient.get('/history/conversations')
}

// 获取对话消息
export async function getConversationMessages(conversationId) {
  return apiClient.get(`/history/conversations/${conversationId}/messages`)
}

// 创建新对话
export async function createConversation(title = '新对话') {
  return apiClient.post('/history/conversations', null, { params: { title } })
}

// 删除对话
export async function deleteConversation(conversationId) {
  return apiClient.delete(`/history/conversations/${conversationId}`)
}

// 获取模型配置
export async function getModelConfig() {
  return apiClient.get('/config/model')
}

// 更新模型配置
export async function updateModelConfig(config) {
  return apiClient.post('/config/model', config)
}

// 获取数据库配置
export async function getDatabaseConfig() {
  return apiClient.get('/config/database')
}

// 获取数据库表
export async function getDatabaseTables() {
  return apiClient.get('/config/database/tables')
}

// 获取表结构
export async function getTableSchema(tableName) {
  return apiClient.get(`/config/database/schema/${tableName}`)
}

// SSE 流式响应
export async function sendChatMessageStream(message, conversationId, callbacks = {}) {
  const { onMessage = () => {}, onDone = () => {}, onError = () => {} } = callbacks

  try {
    const response = await fetch('/api/chat/stream', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message,
        conversation_id: conversationId
      })
    })

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }

    if (!response.body) {
      throw new Error('No response body')
    }

    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() || ''

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const dataStr = line.slice(6)
          if (dataStr === '[DONE]') {
            onDone()
            return
          }
          try {
            const data = JSON.parse(dataStr)
            onMessage(data)
          } catch {
            onMessage({ content: dataStr })
          }
        }
      }
    }

    onDone()
  } catch (error) {
    onError(error)
  }
}

export default apiClient
