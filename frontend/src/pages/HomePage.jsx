import { useState, useRef, useEffect, useCallback } from 'react'
import * as echarts from 'echarts'

// 对话列表组件
function ConversationItem({ conversation, isActive, onClick }) {
  return (
    <div
      className={`conversation-item ${isActive ? 'active' : ''}`}
      onClick={onClick}
    >
      <span className="conversation-title">{conversation.title}</span>
      <span className="conversation-time">{conversation.time}</span>
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
        <button onClick={onSend} disabled={!input.trim()}>
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

  useEffect(() => {
    if (chartRef.current && chartData) {
      if (!chartInstance.current) {
        chartInstance.current = echarts.init(chartRef.current)
      }
      chartInstance.current.setOption({
        title: { text: chartData.title || '查询结果' },
        tooltip: {},
        xAxis: { type: 'category', data: chartData.xAxis || [] },
        yAxis: { type: 'value' },
        series: [{
          type: chartData.type || 'bar',
          data: chartData.series || [],
          itemStyle: { color: '#1890ff' }
        }]
      })
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
              value={chartData.type || 'bar'}
              onChange={(e) => {
                // chart type change handled by parent
              }}
            >
              <option value="bar">柱状图</option>
              <option value="line">折线图</option>
              <option value="pie">饼图</option>
            </select>
          )}
        </div>
        <div className="chart-container" ref={chartRef}>
          {!chartData ? (
            <p>暂无图表数据</p>
          ) : null}
        </div>
      </aside>
      <div
        className="resize-handle right"
        onMouseDown={(e) => {
          // parent handles resize
        }}
      />
    </>
  )
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
  const eventSourceRef = useRef(null)

  // 创建新对话
  const handleNewChat = () => {
    const newConv = {
      id: Date.now().toString(),
      title: `新对话 ${conversations.length + 1}`,
      time: new Date().toLocaleTimeString()
    }
    setConversations(prev => [newConv, ...prev])
    setActiveConvId(newConv.id)
    setMessages([])
    setChartData(null)
    setInput('')
  }

  // 选择对话
  const handleSelectConv = (id) => {
    setActiveConvId(id)
    // TODO: 加载对话历史
  }

  // 发送消息
  const handleSend = async () => {
    if (!input.trim()) return

    const userMessage = { role: 'user', content: input }
    setMessages(prev => [...prev, userMessage])
    setInput('')
    setStreamingContent('')

    // TODO: SSE 调用后端 API
    // 模拟流式响应
    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: input })
      })

      if (response.ok && response.body) {
        const reader = response.body.getReader()
        const decoder = new TextDecoder()
        let fullContent = ''

        while (true) {
          const { done, value } = await reader.read()
          if (done) break
          const chunk = decoder.decode(value)
          fullContent += chunk
          setStreamingContent(fullContent)
        }

        // 流结束后，更新消息并解析结果
        setMessages(prev => [...prev, { role: 'assistant', content: fullContent }])
        setStreamingContent('')

        // TODO: 解析 chartData 从响应中
        // 模拟图表数据
        if (fullContent.includes('图表')) {
          setChartData({
            title: '查询结果',
            type: 'bar',
            xAxis: ['类别A', '类别B', '类别C', '类别D'],
            series: [120, 200, 150, 80]
          })
        }
      }
    } catch (error) {
      console.error('发送失败:', error)
      setMessages(prev => [...prev, { role: 'assistant', content: '抱歉，发生了错误。' }])
      setStreamingContent('')
    }
  }

  // 右侧 resize
  const handleRightResize = (newWidth) => {
    setRightWidth(newWidth)
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
