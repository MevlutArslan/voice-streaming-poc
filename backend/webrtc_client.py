from enum import Enum
import aiortc
import asyncio

class WebRtcConnectionState(Enum):
    NONE = 0
    NEW = 1
    CONNECTING = 2
    CONNECTED = 3
    FAILED = 4
    CLOSED = 5

    @staticmethod
    def from_string(str_input: str) -> 'WebRtcConnectionState':
        match str_input:
            case "new":
                return WebRtcConnectionState.NEW
            case "connecting":
                return WebRtcConnectionState.CONNECTING
            case "connected":
                return WebRtcConnectionState.CONNECTED
            case "failed":
                return WebRtcConnectionState.FAILED
            case "closed":
                return WebRtcConnectionState.CLOSED
            case _:
                raise ValueError(f"Invalid string input: {str_input}")
            
    def to_str(self) -> str:
        match self:
            case WebRtcConnectionState.NEW:
                return "new"
            case WebRtcConnectionState.CONNECTING:
                return "connecting"
            case WebRtcConnectionState.CONNECTED:
                return "connected"
            case WebRtcConnectionState.FAILED:
                return "failed"
            case WebRtcConnectionState.CLOSED:
                return "closed"
            
class WebRtcClient:
    def __init__(self, handle_audio_stream_func) -> None:
        self.peer_connection: aiortc.RTCPeerConnection = None
        self.connection_state: WebRtcConnectionState = WebRtcConnectionState.NONE
        self.receive_audio_task: asyncio.Task = None
        self.handle_audio_stream = handle_audio_stream_func

    
    async def connect_to_connection(self, remote_sdp: aiortc.RTCSessionDescription) -> aiortc.RTCSessionDescription:
        '''Exclusively generates an answer to an attempt at a WebRTC connection'''
        if self.peer_connection is not None:
            self.close_connection()
            
        self.peer_connection = aiortc.RTCPeerConnection()
        self.peer_connection.on("icegatheringstatechange", self.on_icegatheringstatechange)
        self.peer_connection.on("connectionstatechange", self.on_connectionstatechange)
        self.peer_connection.on("track", self.on_track)

        await self.peer_connection.setRemoteDescription(remote_sdp)

        answer = await self.peer_connection.createAnswer()
        
        await self.peer_connection.setLocalDescription(answer)

        return answer
    
    async def add_ice_candidate(self, candidate: aiortc.RTCIceCandidate):
        if self.peer_connection is None:
            return
        
        await self.peer_connection.addIceCandidate(candidate)
        

    def close_connection(self):
        if self.receive_audio_task:
            self.receive_audio_task.cancel()
            self.receive_audio_task = None

        if self.peer_connection:
            self.peer_connection.close()
            self.peer_connection = None

    async def on_icegatheringstatechange(self):
        print("Ice Gather state changed: {}".format(self.peer_connection.iceConnectionState))
        pass

    async def on_connectionstatechange(self):
        self.connection_state = WebRtcConnectionState.from_string(self.peer_connection.connectionState)
        print("Peer connection state Updated: {}".format(self.connection_state))

        if self.connection_state is WebRtcConnectionState.NEW or self.connection_state is WebRtcConnectionState.CONNECTING:
            return
        
        if self.connection_state is WebRtcConnectionState.CONNECTED:
            print("CONNECTED TO WebRTC CONNECTION")
        else:
            print("Detected {}".format(self.connection_state.to_str()))
                

    async def on_track(self, track: aiortc.MediaStreamTrack):
        if track.kind == "audio":
            print("Received audio track")
            if self.receive_audio_task:
                self.receive_audio_task.cancel()
            self.receive_audio_task = asyncio.create_task(self.handle_audio_stream(track))

        @track.on("ended")
        async def on_ended():
            print("Audio Track ended")
            if self.receive_audio_task is not None:
                self.receive_audio_task.cancel()
                self.receive_audio_task = None
                