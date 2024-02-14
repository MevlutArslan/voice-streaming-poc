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
        try:
            self.active_connections.remove(websocket)
        except ValueError:
            pass  # Connection not in the list, no need to remove


def get_eth0_ip():
    import socket
    try:
        # Get the host name of the machine
        host_name = socket.gethostname()
        # Get the IP address of the machine
        ip_address = socket.gethostbyname(host_name)
        return ip_address
    except socket.error:
        return None