//
//  WebRTCManager.swift
//  app
//
//  Created by Mevlut Arslan on 3/3/24.
//

import Foundation
import WebRTC

class WebRTCManager {
    private let rtcConfiguration = RTCConfiguration()
    private var peerConnection: RTCPeerConnection
    private let factory = RTCPeerConnectionFactory()
    init() {
        self.peerConnection = factory.peerConnectionWithConfiguration(rtcConfiguration)
    }
}
