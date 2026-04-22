import { useState } from 'react'

function HomePage() {
  const [leftWidth, setLeftWidth] = useState(250)
  const [rightWidth, setRightWidth] = useState(400)

  return (
    <div className="app-container">
      {/* 左侧聊天管理栏 */}
      <aside className="sidebar-left" style={{ width: leftWidth }}>
        <div className="sidebar-header">
          <h2>对话列表</h2>
          <button>+ 新对话</button>
        </div>
        <div className="conversation-list">
          {/* 待实现：对话列表 */}
          <p>暂无对话</p>
        </div>
      </aside>

      {/* 中间问答区域 */}
      <main className="main-content">
        <div className="chat-header">
          <h1>智能数据库查询</h1>
        </div>
        <div className="message-list">
          {/* 待实现：消息列表 */}
          <div className="welcome-message">
            <p>欢迎使用智能数据库查询系统</p>
            <p>请输入自然语言问题，我会帮您查询数据库</p>
          </div>
        </div>
        <div className="input-area">
          <textarea placeholder="输入您的问题..." />
          <button>发送</button>
        </div>
      </main>

      {/* 右侧可视化图表栏 */}
      <aside className="sidebar-right" style={{ width: rightWidth }}>
        <div className="chart-header">
          <h2>可视化结果</h2>
        </div>
        <div className="chart-container">
          {/* 待实现：ECharts 图表 */}
          <p>暂无图表数据</p>
        </div>
      </aside>

      {/* 调整手柄 */}
      <div className="resize-handle left" />
      <div className="resize-handle right" />
    </div>
  )
}

export default HomePage
