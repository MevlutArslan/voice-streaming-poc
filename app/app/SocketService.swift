//
//  SocketService.swift
//  app
//
//  Created by Mevlut Arslan on 1/29/24.
//

import Foundation



protocol WebSocketDelegate: AnyObject {
    func webSocketDidConnect(_ socketService: SocketService)
    func webSocketDidDisconnect(_ socketService: SocketService)
    func webSocket(_ socketService: SocketService, didReceiveData data: Data)
}

class SocketService: NSObject {
//    private let server_url: URL = URL(string: "ws://172.20.10.4:8999/offer")!; // mobile hotspot
    private let server_url: URL = URL(string: "ws://10.0.0.61:8999/offer")!; // home wifi

    private var socket: URLSessionWebSocketTask?
    private var session: URLSession?
    var delegate: WebSocketDelegate?

    private var isConnected = false
    
    override init() {
        super.init()
        
        session = URLSession(configuration: .ephemeral, delegate: self, delegateQueue: OperationQueue())
    }
    
    func connect() {
        socket = session?.webSocketTask(with: server_url)
        socket?.resume()
        isConnected = true
        
        Task.init {
            await receive()
        }
    }
    
    func disconnect() {
        self.socket?.cancel()
        self.socket = nil
        isConnected = false

        self.delegate?.webSocketDidDisconnect(self)
    }
    
    func send(data: Data) async {
        do {
            try await self.socket?.send(.data(data))
        } catch {
            print("Failed to send data: \(error)")
        }
    }
    
    func receive() async {
        do {
            let resp: URLSessionWebSocketTask.Message? = try await socket?.receive()
            
            switch (resp){
            case .data(let data):
                self.delegate?.webSocket(self, didReceiveData: data)
                break
            case .string(let string):
                print("Received String Data: \(string)")
                break
            default:
                print("Received an unexpected type of message!")
            }
        
        } catch {
            print("Received error while waiting for a message from the SignalingServer: \(error)")
        }
        
        if self.isConnected {
            await self.receive()
        }
    }
}

extension SocketService: URLSessionWebSocketDelegate, URLSessionDelegate {
    func urlSession(_ session: URLSession, webSocketTask: URLSessionWebSocketTask, didOpenWithProtocol protocol: String?) {
        self.delegate?.webSocketDidConnect(self)
    }
    
    func urlSession(_ session: URLSession, webSocketTask: URLSessionWebSocketTask, didCloseWith closeCode: URLSessionWebSocketTask.CloseCode, reason: Data?) {
        self.disconnect()
    }
}

