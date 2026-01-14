'use client';

import { useState, useRef, useEffect, useCallback } from 'react';
import { MessageSquare, X, Send, Loader2 } from 'lucide-react';
import api from '@/lib/api';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  toolCalls?: Array<{
    tool_name: string;
    result: Record<string, unknown>;
  }>;
}

interface ChatWidgetProps {
  projectId: string;
  projectName: string;
  clientName?: string;
}

export default function ChatWidget({
  projectId,
  projectName,
  clientName,
}: ChatWidgetProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Focus input when chat opens
  useEffect(() => {
    if (isOpen && inputRef.current) {
      inputRef.current.focus();
    }
  }, [isOpen]);

  // Add welcome message when chat first opens
  useEffect(() => {
    if (isOpen && messages.length === 0) {
      const welcomeName = clientName ? `, ${clientName}` : '';
      setMessages([
        {
          id: 'welcome',
          role: 'assistant',
          content: `Hi${welcomeName}! I'm here to help you share information about your project. Feel free to tell me about the problem you're trying to solve, or ask me what information I still need. What would you like to discuss?`,
        },
      ]);
    }
  }, [isOpen, messages.length, clientName]);

  const sendMessage = useCallback(async () => {
    if (!input.trim() || isLoading) return;

    const userMessage: Message = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: input.trim(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    try {
      // Build conversation history for context
      const history = messages.map((m) => ({
        role: m.role,
        content: m.content,
      }));

      // Call the client chat endpoint
      const response = await api.clientChat(projectId, {
        message: userMessage.content,
        conversation_id: conversationId || undefined,
        conversation_history: history,
      });

      // Handle streaming response
      const reader = response.body?.getReader();
      if (!reader) throw new Error('No response body');

      const decoder = new TextDecoder();
      let assistantContent = '';
      const toolCalls: Message['toolCalls'] = [];

      // Create placeholder assistant message
      const assistantId = `assistant-${Date.now()}`;
      setMessages((prev) => [
        ...prev,
        { id: assistantId, role: 'assistant', content: '' },
      ]);

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        const lines = chunk.split('\n').filter((line) => line.startsWith('data: '));

        for (const line of lines) {
          try {
            const data = JSON.parse(line.slice(6));

            if (data.type === 'conversation_id') {
              setConversationId(data.conversation_id);
            } else if (data.type === 'text') {
              assistantContent += data.content;
              // Update the assistant message in place
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === assistantId ? { ...m, content: assistantContent } : m
                )
              );
            } else if (data.type === 'tool_result') {
              toolCalls.push({
                tool_name: data.tool_name,
                result: data.result,
              });
              // Update with tool calls
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === assistantId
                    ? { ...m, content: assistantContent, toolCalls }
                    : m
                )
              );
            } else if (data.type === 'error') {
              console.error('Chat error:', data.message);
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === assistantId
                    ? {
                        ...m,
                        content:
                          'Sorry, I encountered an error. Please try again.',
                      }
                    : m
                )
              );
            }
          } catch {
            // Skip malformed JSON lines
          }
        }
      }
    } catch (error) {
      console.error('Chat error:', error);
      setMessages((prev) => [
        ...prev,
        {
          id: `error-${Date.now()}`,
          role: 'assistant',
          content: 'Sorry, I had trouble connecting. Please try again.',
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  }, [input, isLoading, messages, projectId, conversationId]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  return (
    <>
      {/* Chat toggle button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className={`fixed bottom-6 right-6 z-50 p-4 rounded-full shadow-lg transition-all ${
          isOpen
            ? 'bg-gray-600 text-white'
            : 'bg-primary text-white hover:bg-primary-dark'
        }`}
        aria-label={isOpen ? 'Close chat' : 'Open chat'}
      >
        {isOpen ? (
          <X className="w-6 h-6" />
        ) : (
          <MessageSquare className="w-6 h-6" />
        )}
      </button>

      {/* Chat panel */}
      {isOpen && (
        <div className="fixed bottom-24 right-6 z-50 w-96 h-[500px] bg-white rounded-xl shadow-2xl border border-gray-200 flex flex-col overflow-hidden">
          {/* Header */}
          <div className="bg-primary text-white px-4 py-3 flex items-center justify-between">
            <div>
              <h3 className="font-semibold">Project Assistant</h3>
              <p className="text-sm opacity-90">{projectName}</p>
            </div>
            <button
              onClick={() => setIsOpen(false)}
              className="p-1 hover:bg-white/20 rounded"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {messages.map((message) => (
              <div
                key={message.id}
                className={`flex ${
                  message.role === 'user' ? 'justify-end' : 'justify-start'
                }`}
              >
                <div
                  className={`max-w-[85%] rounded-xl px-4 py-2 ${
                    message.role === 'user'
                      ? 'bg-primary text-white'
                      : 'bg-gray-100 text-gray-900'
                  }`}
                >
                  <p className="text-sm whitespace-pre-wrap">{message.content}</p>

                  {/* Show tool activity indicators */}
                  {message.toolCalls && message.toolCalls.length > 0 && (
                    <div className="mt-2 pt-2 border-t border-gray-200/30 space-y-1">
                      {message.toolCalls.map((tool, idx) => (
                        <div
                          key={idx}
                          className="text-xs opacity-75 flex items-center gap-1"
                        >
                          <span className="w-2 h-2 bg-emerald-400 rounded-full" />
                          {formatToolName(tool.tool_name)}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            ))}

            {/* Loading indicator */}
            {isLoading && messages[messages.length - 1]?.role === 'user' && (
              <div className="flex justify-start">
                <div className="bg-gray-100 rounded-xl px-4 py-2">
                  <Loader2 className="w-5 h-5 text-gray-500 animate-spin" />
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* Input */}
          <div className="border-t border-gray-200 p-3">
            <div className="flex gap-2">
              <textarea
                ref={inputRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Type a message..."
                rows={1}
                className="flex-1 resize-none rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
                disabled={isLoading}
              />
              <button
                onClick={sendMessage}
                disabled={!input.trim() || isLoading}
                className="p-2 bg-primary text-white rounded-lg hover:bg-primary-dark disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <Send className="w-5 h-5" />
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

function formatToolName(name: string): string {
  const nameMap: Record<string, string> = {
    update_context_section: 'Updated context',
    add_metric: 'Added metric',
    add_user: 'Added user',
    add_competitor: 'Added competitor',
    add_design_inspiration: 'Added inspiration',
    add_tribal_knowledge: 'Added edge case',
    complete_info_request: 'Completed item',
    get_pending_questions: 'Checked questions',
    get_context_summary: 'Checked progress',
    suggest_next_action: 'Suggesting next step',
  };

  return nameMap[name] || name.replace(/_/g, ' ');
}
