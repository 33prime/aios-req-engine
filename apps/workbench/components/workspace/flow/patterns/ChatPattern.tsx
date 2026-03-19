'use client'

import type { PatternRendererProps } from './types'

export function ChatPattern({ fields, detail }: PatternRendererProps) {
  const agentName = detail.ai_config?.agent_name || 'AI Assistant'
  const actor = detail.actors?.[0] || 'User'
  const topics = fields.slice(0, 3)

  const messages = [
    { from: actor, text: topics[0]?.mock_value || 'Can you help me analyze this data?', isUser: true },
    { from: agentName, text: topics[1]?.mock_value || 'I found 3 patterns in your data. The most significant is...', isUser: false },
    { from: actor, text: topics[2]?.mock_value || 'Show me more detail on the first one.', isUser: true },
    { from: agentName, text: 'Here\'s a breakdown with confidence scores...', isUser: false },
  ]

  return (
    <div className="flex flex-col gap-2" style={{ maxWidth: 500 }}>
      {messages.map((msg, i) => (
        <div key={i} className={`flex ${msg.isUser ? 'justify-end' : 'justify-start'}`}>
          <div
            className="rounded-[7px] px-3 py-2 max-w-[75%]"
            style={{
              background: msg.isUser ? '#3FAF7A' : '#EDF2F7',
              color: msg.isUser ? '#fff' : '#2D3748',
            }}
          >
            <div className="text-[8px] font-medium mb-0.5" style={{ color: msg.isUser ? 'rgba(255,255,255,0.7)' : '#A0AEC0' }}>
              {msg.from}
            </div>
            <div className="text-[10px] leading-snug">{msg.text}</div>
          </div>
        </div>
      ))}
      {/* Input area */}
      <div className="flex gap-1.5 mt-1">
        <div className="flex-1 rounded-[5px] px-2.5 py-[7px] text-[10px]" style={{ background: '#EDF2F7', border: '1px solid #E2E8F0', color: '#A0AEC0' }}>
          Ask {agentName}...
        </div>
        <button className="px-3 py-[7px] rounded-[5px] text-[10px] font-semibold text-white" style={{ background: '#3FAF7A' }}>Send</button>
      </div>
    </div>
  )
}
