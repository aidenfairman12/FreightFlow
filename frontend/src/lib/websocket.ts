const WS_URL = process.env.NEXT_PUBLIC_WS_URL ?? 'ws://localhost:8000/ws'

type MessageHandler = (data: unknown) => void

export function createSocket(onMessage: MessageHandler): WebSocket {
  const ws = new WebSocket(WS_URL)

  ws.onmessage = (event) => {
    try {
      const message = JSON.parse(event.data)
      onMessage(message)
    } catch {
      console.error('Failed to parse WebSocket message', event.data)
    }
  }

  ws.onerror = (err) => console.error('WebSocket error', err)

  return ws
}
