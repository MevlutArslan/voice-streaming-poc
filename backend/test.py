import asyncio
import websockets

async def communicate():
    uri = "ws://127.0.0.1:8000/communicate"
    async with websockets.connect(uri) as websocket:
        while True:
            # Send a test message
            message_to_send = input("Enter message to send (type 'exit' to stop): ")
            await websocket.send(message_to_send)

            # Receive and print the response
            response = await websocket.recv()
            print(f"Received: {response}")

            if message_to_send.lower() == 'exit':
                break

if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(communicate())
