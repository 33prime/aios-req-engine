// SSE response builders for Playwright chat tests.
//
// Usage:
//   await page.route('**/v1/chat*', route =>
//     route.fulfill({ body: textSSE('Hello!'), ... })
//   )

export interface SSEEvent {
  type: string
  [key: string]: unknown
}

/** Encode an array of event objects into an SSE body string. */
export function buildSSE(events: SSEEvent[]): string {
  return events.map((e) => `data: ${JSON.stringify(e)}\n\n`).join('')
}

/** Build a minimal text-only SSE stream with conversation_id + text + done. */
export function textSSE(text: string, convId = 'conv-test-001'): string {
  return buildSSE([
    { type: 'conversation_id', conversation_id: convId },
    { type: 'text', content: text },
    { type: 'done' },
  ])
}

/** Build an SSE stream that includes a tool_result event before the text. */
export function toolResultSSE(
  toolName: string,
  result: Record<string, unknown>,
  text = 'Done.',
  convId = 'conv-test-001',
): string {
  return buildSSE([
    { type: 'conversation_id', conversation_id: convId },
    { type: 'tool_result', tool_name: toolName, result },
    { type: 'text', content: text },
    { type: 'done' },
  ])
}

/** Build an SSE stream whose tool_result is a suggest_actions payload. */
export function actionCardsSSE(
  cards: Array<{ card_type: string; id: string; data: Record<string, unknown> }>,
  text = '',
  convId = 'conv-test-001',
): string {
  return toolResultSSE('suggest_actions', { cards }, text, convId)
}
