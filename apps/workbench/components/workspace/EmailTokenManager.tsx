'use client'

import { useCallback, useEffect, useState } from 'react'
import { Copy, Plus, Trash2, Mail, Loader } from 'lucide-react'
import { createEmailToken, listEmailTokens, deactivateEmailToken } from '@/lib/api'
import type { EmailTokenResponse } from '@/types/api'

interface EmailTokenManagerProps {
  projectId: string
}

export function EmailTokenManager({ projectId }: EmailTokenManagerProps) {
  const [tokens, setTokens] = useState<EmailTokenResponse[]>([])
  const [loading, setLoading] = useState(true)
  const [creating, setCreating] = useState(false)
  const [copied, setCopied] = useState<string | null>(null)

  const fetchTokens = useCallback(async () => {
    try {
      const data = await listEmailTokens(projectId)
      setTokens(data.tokens)
    } catch (err) {
      console.error('Failed to fetch email tokens:', err)
    } finally {
      setLoading(false)
    }
  }, [projectId])

  useEffect(() => {
    fetchTokens()
  }, [fetchTokens])

  const handleCreate = async () => {
    setCreating(true)
    try {
      const token = await createEmailToken({ project_id: projectId })
      setTokens(prev => [token, ...prev])
    } catch (err) {
      console.error('Failed to create email token:', err)
    } finally {
      setCreating(false)
    }
  }

  const handleDeactivate = async (tokenId: string) => {
    try {
      await deactivateEmailToken(tokenId)
      setTokens(prev => prev.filter(t => t.id !== tokenId))
    } catch (err) {
      console.error('Failed to deactivate token:', err)
    }
  }

  const handleCopy = async (address: string, tokenId: string) => {
    try {
      await navigator.clipboard.writeText(address)
      setCopied(tokenId)
      setTimeout(() => setCopied(null), 2000)
    } catch (err) {
      console.error('Failed to copy:', err)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center gap-2 text-zinc-400 py-4">
        <Loader className="w-4 h-4 animate-spin" />
        <span className="text-sm">Loading email tokens...</span>
      </div>
    )
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Mail className="w-4 h-4 text-zinc-500" />
          <h3 className="text-sm font-medium text-zinc-700">Email Capture</h3>
        </div>
        <button
          onClick={handleCreate}
          disabled={creating}
          className="flex items-center gap-1 text-xs text-emerald-600 hover:text-emerald-700 font-medium disabled:opacity-50"
        >
          {creating ? (
            <Loader className="w-3 h-3 animate-spin" />
          ) : (
            <Plus className="w-3 h-3" />
          )}
          Generate Address
        </button>
      </div>

      <p className="text-xs text-zinc-500">
        Forward client emails to these addresses to capture them as signals.
      </p>

      {tokens.length === 0 ? (
        <div className="text-xs text-zinc-400 py-2">
          No active email tokens. Generate one to start capturing emails.
        </div>
      ) : (
        <div className="space-y-2">
          {tokens.map(token => (
            <div
              key={token.id}
              className="bg-zinc-50 border border-zinc-200 rounded-lg p-3 space-y-2"
            >
              <div className="flex items-center gap-2">
                <code className="text-xs text-zinc-700 font-mono flex-1 truncate">
                  {token.reply_to_address}
                </code>
                <button
                  onClick={() => handleCopy(token.reply_to_address, token.id)}
                  className="text-zinc-400 hover:text-zinc-600 shrink-0"
                  title="Copy address"
                >
                  <Copy className="w-3.5 h-3.5" />
                </button>
                <button
                  onClick={() => handleDeactivate(token.id)}
                  className="text-zinc-400 hover:text-red-500 shrink-0"
                  title="Deactivate"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              </div>

              {copied === token.id && (
                <span className="text-xs text-emerald-600">Copied!</span>
              )}

              <div className="flex items-center gap-3 text-xs text-zinc-400">
                <span>{token.emails_received} / {token.max_emails} emails</span>
                <span>Expires {new Date(token.expires_at).toLocaleDateString()}</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
