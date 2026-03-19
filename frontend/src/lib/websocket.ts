import type { StateVector } from '@/types'

const WS_URL = process.env.NEXT_PUBLIC_WS_URL ?? 'ws://localhost:8000/ws/flights'

type FlightUpdateHandler = (flights: StateVector[]) => void

export function createFlightSocket(onUpdate: FlightUpdateHandler): WebSocket {
  const ws = new WebSocket(WS_URL)

  ws.onmessage = (event) => {
    try {
      const message = JSON.parse(event.data)
      if (message.type === 'flight_update') {
        onUpdate(message.data)
      }
    } catch {
      console.error('Failed to parse WebSocket message', event.data)
    }
  }

  ws.onerror = (err) => console.error('WebSocket error', err)

  return ws
}
