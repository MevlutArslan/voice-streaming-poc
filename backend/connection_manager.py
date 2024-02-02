from fastapi import WebSocket

class ConnectionManager:
    """Class defining socket events"""
    def __init__(self):
        """init method, keeping track of connections"""
        self.active_connections = []
    
    async def connect(self, websocket: WebSocket):
        """connect event"""
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        """disconnect event"""
        self.active_connections.remove(websocket)