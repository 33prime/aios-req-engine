'use client'

import { useCallback, useEffect, useState } from 'react'
import { Calendar, Link2, Loader, Mic, Unlink } from 'lucide-react'
import {
  getIntegrationSettings,
  updateIntegrationSettings,
  disconnectGoogle,
} from '@/lib/api'
import type { IntegrationSettings as IntegrationSettingsType, RecordingDefault } from '@/types/api'

export function IntegrationSettings() {
  const [settings, setSettings] = useState<IntegrationSettingsType | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [disconnecting, setDisconnecting] = useState(false)

  const fetchSettings = useCallback(async () => {
    try {
      const data = await getIntegrationSettings()
      setSettings(data)
    } catch (err) {
      console.error('Failed to fetch integration settings:', err)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchSettings()
  }, [fetchSettings])

  const handleToggleCalendar = async () => {
    if (!settings) return
    setSaving(true)
    try {
      const newValue = !settings.calendar_sync_enabled
      await updateIntegrationSettings({ calendar_sync_enabled: newValue })
      setSettings(prev => prev ? { ...prev, calendar_sync_enabled: newValue } : prev)
    } catch (err) {
      console.error('Failed to update calendar sync:', err)
    } finally {
      setSaving(false)
    }
  }

  const handleRecordingDefault = async (value: RecordingDefault) => {
    setSaving(true)
    try {
      await updateIntegrationSettings({ recording_default: value })
      setSettings(prev => prev ? { ...prev, recording_default: value } : prev)
    } catch (err) {
      console.error('Failed to update recording default:', err)
    } finally {
      setSaving(false)
    }
  }

  const handleDisconnect = async () => {
    setDisconnecting(true)
    try {
      await disconnectGoogle()
      setSettings(prev => prev ? {
        ...prev,
        google_connected: false,
        calendar_sync_enabled: false,
        scopes_granted: [],
      } : prev)
    } catch (err) {
      console.error('Failed to disconnect Google:', err)
    } finally {
      setDisconnecting(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center gap-2 text-zinc-400 py-8">
        <Loader className="w-4 h-4 animate-spin" />
        <span className="text-sm">Loading settings...</span>
      </div>
    )
  }

  if (!settings) {
    return <div className="text-sm text-zinc-400">Failed to load settings</div>
  }

  return (
    <div className="space-y-6">
      <h2 className="text-lg font-semibold text-zinc-900">Integrations</h2>

      {/* Google Connection */}
      <div className="bg-white border border-zinc-200 rounded-lg p-4 space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-zinc-100 rounded-lg flex items-center justify-center">
              <svg className="w-5 h-5" viewBox="0 0 24 24">
                <path
                  d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 01-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z"
                  fill="#4285F4"
                />
                <path
                  d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                  fill="#34A853"
                />
                <path
                  d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
                  fill="#FBBC05"
                />
                <path
                  d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
                  fill="#EA4335"
                />
              </svg>
            </div>
            <div>
              <h3 className="text-sm font-medium text-zinc-900">Google</h3>
              <p className="text-xs text-zinc-500">
                {settings.google_connected ? 'Connected' : 'Not connected'}
              </p>
            </div>
          </div>

          {settings.google_connected && (
            <button
              onClick={handleDisconnect}
              disabled={disconnecting}
              className="flex items-center gap-1 text-xs text-red-600 hover:text-red-700 font-medium disabled:opacity-50"
            >
              {disconnecting ? (
                <Loader className="w-3 h-3 animate-spin" />
              ) : (
                <Unlink className="w-3 h-3" />
              )}
              Disconnect
            </button>
          )}
        </div>

        {settings.google_connected && settings.scopes_granted.length > 0 && (
          <div className="text-xs text-zinc-400">
            Scopes: {settings.scopes_granted.join(', ')}
          </div>
        )}
      </div>

      {/* Calendar Sync */}
      <div className="bg-white border border-zinc-200 rounded-lg p-4 space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Calendar className="w-5 h-5 text-zinc-400" />
            <div>
              <h3 className="text-sm font-medium text-zinc-900">Calendar Sync</h3>
              <p className="text-xs text-zinc-500">
                Sync upcoming meetings from Google Calendar
              </p>
            </div>
          </div>

          <button
            onClick={handleToggleCalendar}
            disabled={saving || !settings.google_connected}
            className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
              settings.calendar_sync_enabled
                ? 'bg-emerald-500'
                : 'bg-zinc-200'
            } disabled:opacity-50`}
          >
            <span
              className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                settings.calendar_sync_enabled
                  ? 'translate-x-6'
                  : 'translate-x-1'
              }`}
            />
          </button>
        </div>

        {!settings.google_connected && (
          <p className="text-xs text-zinc-400">
            Connect Google to enable calendar sync.
          </p>
        )}
      </div>

      {/* Recording Default */}
      <div className="bg-white border border-zinc-200 rounded-lg p-4 space-y-3">
        <div className="flex items-center gap-3">
          <Mic className="w-5 h-5 text-zinc-400" />
          <div>
            <h3 className="text-sm font-medium text-zinc-900">Recording Default</h3>
            <p className="text-xs text-zinc-500">
              Default recording behavior for new meetings
            </p>
          </div>
        </div>

        <div className="flex gap-2">
          {(['off', 'ask', 'on'] as const).map(option => (
            <button
              key={option}
              onClick={() => handleRecordingDefault(option)}
              disabled={saving}
              className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
                settings.recording_default === option
                  ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                  : 'bg-zinc-50 text-zinc-500 border border-zinc-200 hover:bg-zinc-100'
              } disabled:opacity-50`}
            >
              {option === 'off' && 'Off'}
              {option === 'ask' && 'Ask Each Time'}
              {option === 'on' && 'Always On'}
            </button>
          ))}
        </div>

        <p className="text-xs text-zinc-400">
          {settings.recording_default === 'on' && 'Meetings will be recorded by default. Consent emails are always sent.'}
          {settings.recording_default === 'ask' && 'You\'ll be prompted before each meeting.'}
          {settings.recording_default === 'off' && 'Meetings won\'t be recorded unless you enable it per-meeting.'}
        </p>
      </div>
    </div>
  )
}
