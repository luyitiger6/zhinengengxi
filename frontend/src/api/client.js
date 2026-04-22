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

// SSE 流式响应
export function createSSEClient(url, options = {}) {
  let eventSource = null
  let isConnected = false

  const {
    onMessage = () => {},
    onError = () => {},
    onOpen = () => {},
  } = options

  function connect() {
    if (isConnected) return

    eventSource = new EventSource(url)

    eventSource.onopen = () => {
      isConnected = true
      onOpen()
    }

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        onMessage(data)
      } catch {
        onMessage({ content: event.data })
      }
    }

    eventSource.onerror = (error) => {
      isConnected = false
      onError(error)
      close()
    }
  }

  function close() {
    if (eventSource) {
      eventSource.close()
      eventSource = null
      isConnected = false
    }
  }

  return {
    connect,
    close,
    get connected() {
      return isConnected
    }
  }
}

// 发送消息并获取 SSE 流式响应
export async function sendChatMessage(message, callbacks = {}) {
  const { onMessage = () => {}, onDone = () => {}, onError = () => {} } = callbacks

  try {
    const response = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message })
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
          const data = line.slice(6)
          if (data === '[DONE]') {
            onDone()
            return
          }
          try {
            const parsed = JSON.parse(data)
            onMessage(parsed)
          } catch {
            onMessage({ content: data })
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
