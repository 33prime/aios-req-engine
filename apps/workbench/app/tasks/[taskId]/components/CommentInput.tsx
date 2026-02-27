'use client'

import { useState } from 'react'
import Image from 'next/image'
import { Send, User } from 'lucide-react'

interface CommentInputProps {
  avatarUrl?: string
  onSubmit: (body: string) => Promise<void>
}

export function CommentInput({ avatarUrl, onSubmit }: CommentInputProps) {
  const [body, setBody] = useState('')
  const [sending, setSending] = useState(false)

  const handleSubmit = async () => {
    if (!body.trim() || sending) return
    setSending(true)
    try {
      await onSubmit(body.trim())
      setBody('')
    } finally {
      setSending(false)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit()
    }
  }

  return (
    <div className="flex items-start gap-3 py-3">
      <div className="w-7 h-7 rounded-full bg-[#E8F5E9] flex items-center justify-center overflow-hidden flex-shrink-0 mt-0.5">
        {avatarUrl ? (
          <Image src={avatarUrl} alt="" width={28} height={28} className="w-full h-full object-cover" />
        ) : (
          <User className="w-3.5 h-3.5 text-brand-primary" />
        )}
      </div>
      <div className="flex-1 flex items-center gap-2 border border-border rounded-lg px-3 py-2 focus-within:border-brand-primary transition-colors">
        <input
          value={body}
          onChange={(e) => setBody(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Add a comment..."
          className="flex-1 text-[13px] text-[#333] placeholder-[#CCC] outline-none bg-transparent"
        />
        <button
          onClick={handleSubmit}
          disabled={!body.trim() || sending}
          className="text-brand-primary hover:text-[#25785A] disabled:text-[#CCC] transition-colors"
        >
          <Send className="w-4 h-4" />
        </button>
      </div>
    </div>
  )
}
