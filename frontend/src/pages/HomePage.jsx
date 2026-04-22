import { useState, useRef, useEffect, useCallback } from 'react'
import * as echarts from 'echarts'
import { getConversations, getConversationMessages, sendChatMessageStream } from '../api/client'

// 对话列表组件
function ConversationItem({ conversation, isActive, onClick }) {
  return (
    <div
      className={`conversation-item ${isActive ? 'active' : ''}`}
      onClick={onClick}
    >
      <span className="conversation-title">{conversation.title}</span>
      <span className="conversation-time">{conversation.message_count} 条消息</span>
    </div>
  )
}

function SidebarLeft({ conversations, activeId, onSelect, onNewChat, width, onResize }) {
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
          <button onClick={onNewChat}>+ 新对话</button>
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

// 中间问答区域
function MainContent({ messages, input, onInputChange, onSend, streamingContent }) {
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
        {streamingContent && (
          <Message message={{ role: 'assistant', content: streamingContent }} />
        )}
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

  useEffect(() => {
    if (chartRef.current) {
      if (!chartInstance.current) {
        chartInstance.current = echarts.init(chartRef.current)
      }

      if (chartData) {
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

        chartInstance.current.setOption(options, true)
        setChartType(finalType)
      }
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
        <div className="chart-container" ref={chartRef}>
          {!chartData && <p>暂无图表数据</p>}
        </div>
      </aside>
      <div className="resize-handle right" />
    </>
  )
}

// 从响应内容中解析图表数据
function parseChartData(content, sql) {
  if (sql && (sql.toUpperCase().includes('COUNT') || sql.toUpperCase().includes('SUM') || sql.toUpperCase().includes('AVG'))) {
    const lines = content.split('\n')
    const data = []

    for (const line of lines) {
      const match = line.match(/\d+(\.\d+)?/)
      if (match) {
        data.push(parseFloat(match[0]))
      }
    }

    if (data.length > 0) {
      const xAxis = data.map((_, i) => `项${i + 1}`)
      return {
        title: '统计结果',
        type: data.length > 5 ? 'line' : 'bar',
        xAxis,
        series: data
      }
    }
  }

  return null
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
  const [chartData, setChartData] = useState(null)
  const [isStreaming, setIsStreaming] = useState(false)

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
    const newConv = {
      id: `new_${Date.now()}`,
      title: `新对话 ${conversations.length + 1}`,
      message_count: 0
    }
    setConversations(prev => [newConv, ...prev])
    setActiveConvId(newConv.id)
    setMessages([])
    setChartData(null)
    setInput('')
    setStreamingContent('')
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
    setChartData(null)
    setIsStreaming(true)

    let fullContent = ''
    let currentSql = null
    const convIdStr = String(activeConvId || '')
    const convIdForApi = convIdStr && !convIdStr.startsWith('new_') ? parseInt(convIdStr) : undefined

    sendChatMessageStream(
      input,
      convIdForApi,
      {
        onMessage: (data) => {
          switch (data.type) {
            case 'sql':
              currentSql = data.content
              break
            case 'assistant':
              fullContent = data.content
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
        conversations={conversations}
        activeId={activeConvId}
        onSelect={handleSelectConv}
        onNewChat={handleNewChat}
        width={leftWidth}
        onResize={setLeftWidth}
      />
      <MainContent
        messages={messages}
        input={input}
        onInputChange={setInput}
        onSend={handleSend}
        streamingContent={streamingContent}
      />
      <ChartPanel chartData={chartData} width={rightWidth} />
    </div>
  )
}

export default HomePage
