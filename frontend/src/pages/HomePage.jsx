import React, { useState, useRef, useEffect, useCallback } from 'react'
import * as echarts from 'echarts'
import { getConversations, getConversationMessages, sendChatMessageStream, clearAllConversations } from '../api/client'

// 对话列表组件
function ConversationItem({ conversation, isActive, onClick }) {
  return (
    <div
      className={`conversation-item ${isActive ? 'active' : ''} ${conversation.pending ? 'pending' : ''}`}
      onClick={onClick}
    >
      <span className="conversation-title">
        {conversation.pending ? '⏳ ' : ''}{conversation.title}
      </span>
      <span className="conversation-meta">
        {conversation.created_at ? conversation.created_at.split(' ')[1] : ''} · {conversation.message_count || 0} 条消息
      </span>
    </div>
  )
}

function SidebarLeft({ conversations, activeId, onSelect, onNewChat, onClearAll, width, onResize }) {
  const sidebarRef = useRef(null)
  const isDragging = useRef(false)

  const handleMouseDown = (e) => {
    isDragging.current = true
    document.addEventListener('mousemove', handleMouseMove)
    document.addEventListener('mouseup', handleMouseUp)
  }

  const handleMouseMove = useCallback((e) => {
    if (!isDragging.current) return
    const newWidth = Math.max(200, Math.min(400, e.clientX))
    onResize(newWidth)
  }, [onResize])

  const handleMouseUp = () => {
    isDragging.current = false
    document.removeEventListener('mousemove', handleMouseMove)
    document.removeEventListener('mouseup', handleMouseUp)
  }

  return (
    <>
      <aside className="sidebar-left" style={{ width }} ref={sidebarRef}>
        <div className="sidebar-header">
          <h2>对话列表</h2>
          <div className="sidebar-actions">
            {conversations.length > 0 && (
              <button className="btn-clear" onClick={onClearAll} title="清除所有历史">🗑️</button>
            )}
            <button onClick={onNewChat}>+ 新对话</button>
          </div>
        </div>
        <div className="conversation-list">
          {conversations.length === 0 ? (
            <p className="no-conversations">暂无对话</p>
          ) : (
            conversations.map(conv => (
              <ConversationItem
                key={conv.id}
                conversation={conv}
                isActive={conv.id === activeId}
                onClick={() => onSelect(conv.id)}
              />
            ))
          )}
        </div>
      </aside>
      <div
        className="resize-handle left"
        onMouseDown={handleMouseDown}
      />
    </>
  )
}

// 消息组件
function Message({ message }) {
  const isUser = message.role === 'user'
  return (
    <div className={`message ${isUser ? 'user' : 'assistant'}`}>
      <div className="message-avatar">
        {isUser ? '👤' : '🤖'}
      </div>
      <div className="message-content">
        <div className="message-text">{message.content}</div>
        {message.sql && (
          <div className="message-sql">
            <span className="sql-label">SQL:</span>
            <code>{message.sql}</code>
          </div>
        )}
      </div>
    </div>
  )
}

// 思考动画组件
function ThinkingIndicator({ expanded, onToggle, thinkingContent }) {
  return (
    <div className="message assistant" onClick={onToggle}>
      <div className="message-avatar">🤖</div>
      <div className="message-content">
        <div className="thinking-indicator">
          <span className="thinking-dot"></span>
          <span className="thinking-dot"></span>
          <span className="thinking-dot"></span>
          <span className="thinking-text">思考中...</span>
          <span className={`expand-icon ${expanded ? 'expanded' : ''}`}>▶</span>
        </div>
        {expanded && thinkingContent && (
          <div className="thinking-content">{thinkingContent}</div>
        )}
      </div>
    </div>
  )
}

// 流式内容显示组件
function StreamingMessage({ content }) {
  return (
    <div className="message assistant">
      <div className="message-avatar">🤖</div>
      <div className="message-content">
        <div className="message-text streaming">{content}<span className="cursor">▋</span></div>
      </div>
    </div>
  )
}

// 中间问答区域
function MainContent({ messages, input, onInputChange, onSend, streamingContent, isStreaming, thinkingExpanded, onToggleThinking, thinkingContent }) {
  const messageListRef = useRef(null)
  const inputRef = useRef(null)

  useEffect(() => {
    if (messageListRef.current) {
      messageListRef.current.scrollTop = messageListRef.current.scrollHeight
    }
  }, [messages, streamingContent])

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      onSend()
    }
  }

  const displayContent = streamingContent || input

  return (
    <main className="main-content">
      <div className="chat-header">
        <h1>智能数据库查询</h1>
      </div>
      <div className="message-list" ref={messageListRef}>
        {messages.length === 0 ? (
          <div className="welcome-message">
            <p>欢迎使用智能数据库查询系统</p>
            <p>请输入自然语言问题，我会帮您查询数据库</p>
          </div>
        ) : (
          messages.map((msg, idx) => (
            <Message key={idx} message={msg} />
          ))
        )}
        {streamingContent ? (
          <StreamingMessage content={streamingContent} />
        ) : isStreaming ? (
          <ThinkingIndicator expanded={thinkingExpanded} onToggle={onToggleThinking} thinkingContent={thinkingContent} />
        ) : null}
      </div>
      <div className="input-area">
        <textarea
          ref={inputRef}
          value={displayContent}
          onChange={(e) => onInputChange(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="输入您的问题..."
        />
        <button onClick={onSend} disabled={!input.trim() && !streamingContent}>
          发送
        </button>
      </div>
    </main>
  )
}

// ECharts 图表组件
function ChartPanel({ chartData, width }) {
  const chartRef = useRef(null)
  const chartInstance = useRef(null)
  const [chartType, setChartType] = useState('bar')

  // Initialize ECharts
  useEffect(() => {
    // Clean up any existing instance first
    if (chartInstance.current) {
      try {
        chartInstance.current.dispose()
      } catch (e) {
        // Ignore disposal errors
      }
      chartInstance.current = null
    }

    // Only init if we have a ref and it has a parent (is in DOM)
    if (chartRef.current && chartRef.current.parentNode) {
      chartInstance.current = echarts.init(chartRef.current)
    }

    return () => {
      if (chartInstance.current) {
        try {
          chartInstance.current.dispose()
        } catch (e) {
          // Ignore disposal errors
        }
        chartInstance.current = null
      }
    }
  }, [])

  // Update chart when data changes
  useEffect(() => {
    if (!chartInstance.current || !chartData) return

    const isPieData = chartData.isPie || (chartData.series && chartData.series.length > 0 && typeof chartData.series[0] === 'object' && chartData.series[0].value !== undefined)
    const finalType = chartData.type || (isPieData ? 'pie' : chartType)

    const options = {
      title: {
        text: chartData.title || '查询结果',
        textStyle: { color: '#e0e6ed', fontSize: 14 }
      },
      tooltip: { trigger: 'axis' },
      legend: { textStyle: { color: '#7a8ba3' } },
      backgroundColor: 'transparent'
    }

    if (finalType === 'pie') {
      options.series = [{
        type: 'pie',
        radius: '60%',
        data: chartData.series || [],
        emphasis: { itemStyle: { shadowBlur: 10, shadowOffsetX: 0, shadowColor: 'rgba(0, 0, 0, 0.5)' } }
      }]
    } else {
      options.xAxis = { type: 'category', data: chartData.xAxis || [], axisLabel: { color: '#7a8ba3' } }
      options.yAxis = { type: 'value', axisLabel: { color: '#7a8ba3' } }
      options.series = [{
        type: finalType,
        data: chartData.series || [],
        itemStyle: { color: finalType === 'line' ? '#39ff14' : '#00f0ff' },
        areaStyle: finalType === 'line' ? { color: 'rgba(57, 255, 20, 0.2)' } : undefined,
        smooth: true
      }]
    }

    try {
      chartInstance.current.setOption(options, true)
      setChartType(finalType)
    } catch (e) {
      console.error('ECharts setOption error:', e)
    }
  }, [chartData])

  useEffect(() => {
    const handleResize = () => {
      chartInstance.current?.resize()
    }
    window.addEventListener('resize', handleResize)
    return () => window.removeEventListener('resize', handleResize)
  }, [])

  return (
    <>
      <aside className="sidebar-right" style={{ width }}>
        <div className="chart-header">
          <h2>可视化结果</h2>
          {chartData && (
            <select
              className="chart-type-select"
              value={chartType}
              onChange={(e) => {
                const newType = e.target.value
                setChartType(newType)
                if (chartInstance.current) {
                  chartInstance.current.setOption({
                    series: [{ type: newType }]
                  }, false)
                }
              }}
            >
              <option value="bar">柱状图</option>
              <option value="line">折线图</option>
              <option value="pie">饼图</option>
            </select>
          )}
        </div>
        <div className="chart-container" ref={chartRef} />
      </aside>
      <div className="resize-handle right" />
    </>
  )
}

// Error Boundary component
class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error }
  }

  componentDidCatch(error, errorInfo) {
    console.error('ErrorBoundary caught error:', error, errorInfo)
  }

  render() {
    if (this.state.hasError) {
      return (
        <aside className="sidebar-right" style={{ width: this.props.width || 400 }}>
          <div className="chart-header">
            <h2>可视化结果</h2>
          </div>
          <div className="chart-container">
            <p style={{ color: '#ff6b6b', padding: '20px' }}>
              图表渲染错误: {this.state.error?.message || '未知错误'}
            </p>
          </div>
        </aside>
      )
    }
    return this.props.children
  }
}

// 从响应内容中解析图表数据
function parseChartData(content, sql) {
  if (!content || !sql) return null

  const sqlUpper = sql.toUpperCase()
  if (!sqlUpper.includes('COUNT') && !sqlUpper.includes('SUM') && !sqlUpper.includes('AVG')) {
    return null
  }

  // 尝试提取数字结果
  const numMatch = content.match(/\d+(\.\d+)?/)
  if (!numMatch) return null

  const numValue = parseFloat(numMatch[0])
  if (isNaN(numValue)) return null

  return {
    title: '统计结果',
    type: 'bar',
    xAxis: ['统计值'],
    series: [numValue]
  }
}

// 主页面组件
function HomePage() {
  const [leftWidth, setLeftWidth] = useState(250)
  const [rightWidth, setRightWidth] = useState(400)
  const [conversations, setConversations] = useState([])
  const [activeConvId, setActiveConvId] = useState(null)
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [streamingContent, setStreamingContent] = useState('')
  const [thinkingContent, setThinkingContent] = useState('')
  const [chartData, setChartData] = useState(null)
  const [isStreaming, setIsStreaming] = useState(false)
  const [thinkingExpanded, setThinkingExpanded] = useState(false)

  // 加载对话列表
  useEffect(() => {
    loadConversations()
  }, [])

  const loadConversations = async () => {
    try {
      const res = await getConversations()
      setConversations(res.conversations || [])
    } catch (err) {
      console.error('加载对话列表失败:', err)
    }
  }

  // 加载对话消息
  const loadConversationMessages = async (convId) => {
    try {
      const res = await getConversationMessages(convId)
      const msgs = (res.messages || []).map(m => ({
        role: m.role,
        content: m.content
      }))
      setMessages(msgs)
    } catch (err) {
      console.error('加载消息失败:', err)
    }
  }

  // 创建新对话
  const handleNewChat = () => {
    // 创建待处理的会话，等发送消息时由后端创建真实会话
    const pendingId = `new_${Date.now()}`
    const pendingConv = {
      id: pendingId,
      title: '新对话...',
      message_count: 0,
      pending: true  // 标记为待确认
    }
    setConversations(prev => [pendingConv, ...prev])
    setActiveConvId(pendingId)
    setMessages([])
    setChartData(null)
    setInput('')
    setStreamingContent('')
  }

  // 清除所有历史对话
  const handleClearAll = async () => {
    if (!window.confirm('确定要清除所有历史对话吗？')) return
    try {
      await clearAllConversations()
      setConversations([])
      setActiveConvId(null)
      setMessages([])
      setChartData(null)
    } catch (err) {
      console.error('清除历史失败:', err)
    }
  }

  // 选择对话
  const handleSelectConv = async (id) => {
    const strId = String(id)
    setActiveConvId(strId)
    if (strId && !strId.startsWith('new_')) {
      await loadConversationMessages(parseInt(strId))
    } else {
      setMessages([])
    }
  }

  // 发送消息
  const handleSend = async () => {
    if (!input.trim() || isStreaming) return

    const userMessage = { role: 'user', content: input }
    setMessages(prev => [...prev, userMessage])
    setInput('')
    setStreamingContent('')
    setThinkingContent('')
    setChartData(null)
    setIsStreaming(true)

    let fullContent = ''
    let currentSql = null
    let pendingConvId = null  // 新建对话时，存放后端返回的真实ID
    const convIdStr = String(activeConvId || '')
    const convIdForApi = convIdStr && !convIdStr.startsWith('new_') ? parseInt(convIdStr) : undefined

    sendChatMessageStream(
      input,
      convIdForApi,
      {
        onMessage: (data) => {
          switch (data.type) {
            case 'thinking':
              setThinkingContent(prev => prev + data.content)
              break
            case 'conversation':
              // 后端返回新创建的对话ID
              pendingConvId = data.id
              // 更新当前对话ID
              setActiveConvId(String(data.id))
              // 更新对话列表：用后端返回的信息替换pending的会话
              setConversations(prev => prev.map(c =>
                c.pending && c.id === activeConvId
                  ? { id: data.id, title: data.title, message_count: 0 }
                  : c
              ))
              break
            case 'sql':
              currentSql = data.content
              break
            case 'assistant':
              fullContent += data.content
              setStreamingContent(fullContent)
              break
            case 'error':
              fullContent = `错误: ${data.content}`
              setStreamingContent(fullContent)
              break
          }
        },
        onDone: () => {
          // 流结束，解析图表数据
          const parsed = parseChartData(fullContent, currentSql)
          if (parsed) {
            setChartData(parsed)
          }
        },
        onError: (err) => {
          console.error('发送失败:', err)
          fullContent = '抱歉，发生了错误。'
        }
      }
    ).then(() => {
      // 更新消息
      setMessages(prev => [...prev, { role: 'assistant', content: fullContent, sql: currentSql }])
      setStreamingContent('')
      setIsStreaming(false)
      // 刷新对话列表
      loadConversations()
    }).catch(() => {
      setMessages(prev => [...prev, { role: 'assistant', content: '抱歉，发生了错误。' }])
      setStreamingContent('')
      setIsStreaming(false)
    })
  }

  return (
    <div className="app-container">
      <SidebarLeft
        conversations={conversations.slice(0, 10)}
        activeId={activeConvId}
        onSelect={handleSelectConv}
        onNewChat={handleNewChat}
        onClearAll={handleClearAll}
        width={leftWidth}
        onResize={setLeftWidth}
      />
      <MainContent
        messages={messages}
        input={input}
        onInputChange={setInput}
        onSend={handleSend}
        streamingContent={streamingContent}
        isStreaming={isStreaming}
        thinkingExpanded={thinkingExpanded}
        onToggleThinking={() => setThinkingExpanded(!thinkingExpanded)}
        thinkingContent={thinkingContent}
      />
      <ErrorBoundary width={rightWidth}>
        <ChartPanel chartData={chartData} width={rightWidth} />
      </ErrorBoundary>
    </div>
  )
}

export default HomePage
