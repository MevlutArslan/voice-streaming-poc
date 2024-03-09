//
//  SignalingClient.swift
//  app
//
//  Created by Mevlut Arslan on 3/8/24.
//

import Foundation
import WebRTC

protocol SignalingClientDelegate: AnyObject {
    func signalClientDidConnect(_ signalClient: SignalingClient)
    func signalClientDidDisconnect(_ signalClient: SignalingClient)
    func signalClient(_ signalClient: SignalingClient, didReceiveRemoteSdp sdp: RTCSessionDescription)
    func signalClient(_ signalClient: SignalingClient, didReceiveCandidate candidate: RTCIceCandidate)
}

/// Manages connections to the SignalingServer
class SignalingClient {
    
    private var webSocketProvider: WebSocketProvider
    private var is_connected = false
    var delegate: SignalingClientDelegate?
    
    init(webSocketProvider: WebSocketProvider) {
        self.webSocketProvider = webSocketProvider
        self.connect()
    }
    
    func connect() {
        self.webSocketProvider.delegate = self
        self.webSocketProvider.connect()
    }
    
    func send(sdp: RTCSessionDescription) async {
        if is_connected == false {
            self.connect()
        }
        // encode
        let data = try! JSONEncoder().encode(SessionDescription(from: sdp))
        // send
        await self.webSocketProvider.send(data: data)
    }
    
    func send(iceCandidate: RTCIceCandidate) async {
        let data = try! JSONEncoder().encode(IceCandidate(from: iceCandidate))
        
        await self.webSocketProvider.send(data: data)
    }
    
}

extension SignalingClient: WebSocketProviderDelegate {
    func webSocketDidConnect(_ webSocket: WebSocketProvider) {
        print("Connected to the Signaling Server.")
        is_connected = true
    }
    
    func webSocketDidDisconnect(_ webSocket: WebSocketProvider) {
        print("Disconnected from the Signaling Server")
        is_connected = false
    }
    
    func webSocket(_ webSocket: WebSocketProvider, didReceiveData data: Data) {
        print("Received Data from the Signaling Server")
        do {
            let sdp = try JSONDecoder().decode(SessionDescription.self, from: data)
            self.delegate?.signalClient(self, didReceiveRemoteSdp: sdp.rtcSessionDescription)
        } catch {
            print("Failed to decode data received from the signaling server")
        }
    }
}

