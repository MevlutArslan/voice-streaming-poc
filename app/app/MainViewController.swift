//
//  MainViewController.swift
//  app
//
//  Created by Mevlut Arslan on 3/8/24.
//

import Foundation
import WebRTC

class MainViewController: ObservableObject {
    private var webRtcClient: WebRtcClient?
    private let iceServers: [String] = ["stun:stun.l.google.com:19302",
                                        "stun:stun1.l.google.com:19302",
                                        "stun:stun2.l.google.com:19302",
                                        "stun:stun3.l.google.com:19302",
                                        "stun:stun4.l.google.com:19302"]
    private let socketService: SocketService
    private let signalingClient: SignalingClient
    
    @Published var isConnected = false
    @Published var isRecording = false
    
    @Published var isConnecting = false
    
    init() {
        self.socketService = SocketService()
        self.signalingClient = SignalingClient(socketService: self.socketService)
        self.webRtcClient = WebRtcClient(iceServers: self.iceServers)
        
        
        self.signalingClient.delegate = self
        self.webRtcClient?.delegate = self
    }
    
    func connect() {
        DispatchQueue.main.async {
            self.isConnecting = true
        }
        if self.webRtcClient == nil {
            self.webRtcClient = WebRtcClient(iceServers: self.iceServers)
            self.webRtcClient?.delegate = self
        }
        
        self.webRtcClient?.offer(completion: { sdp in
            Task.init {
                await self.signalingClient.send(sdp: sdp)
            }
        })
    }
    
    func disconnect() {
        self.webRtcClient?.close()
    }
    
}

extension MainViewController: WebRtcClientDelegate {
    func webRTCClient(_ client: WebRtcClient, didChangeConnectionState state: RTCIceConnectionState) {
        print("Connection State Changed: \(state)")
        if state == .connected {
            DispatchQueue.main.async {
                self.isConnected = true
                self.isConnecting = false
            }
        }else if(state == .disconnected || state == .closed || state == .failed) {
            DispatchQueue.main.async {
                self.isConnected = false
                self.isConnecting = false
            }
            
            self.webRtcClient = nil
        }
    }
        
    func webRTCClient(_ client: WebRtcClient, didDiscoverLocalCandidate candidate: RTCIceCandidate) {
//        print("Sending ice candidate")
        Task.init {
            await self.signalingClient.send(iceCandidate: candidate)
        }
    }
    
    func webRTCClient(_ client: WebRtcClient, didReceiveData data: Data) {
        
    }
}


extension MainViewController: SignalingClientDelegate {
    func signalClientDidConnect(_ signalClient: SignalingClient) {
//        print("Established connection to signaling server")
    }
    
    func signalClientDidDisconnect(_ signalClient: SignalingClient) {
        
    }
    
    func signalClient(_ signalClient: SignalingClient, didReceiveRemoteSdp sdp: RTCSessionDescription) {
        self.webRtcClient?.set(remoteSdp: sdp, completion: { _ in
            print("Received remote sdp")
        })
    }
    
    func signalClient(_ signalClient: SignalingClient, didReceiveCandidate candidate: RTCIceCandidate) {
        self.webRtcClient?.set(remoteCandidate: candidate) { error in
            print("Received remote candidate")
        }
    }
}
