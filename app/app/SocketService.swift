//
//  SocketService.swift
//  app
//
//  Created by Mevlut Arslan on 1/29/24.
//

import Foundation

/*
    * Connect to the socket
    * Start Ping Pong
    * Start Receiving Data
    * Be Able to Send Data
    * Disconnect from the socket
*/
class SocketService: NSObject, URLSessionWebSocketDelegate, ObservableObject {
    private let url = URL(string: "ws://10.0.0.169:8000/communicate")!

    private var socket: URLSessionWebSocketTask?
    private var session: URLSession?
    
    @Published var isConnected = false
    @Published var receivedMessages: [String] = []
    
    override init() {
        super.init()
        
        session = URLSession(configuration: .ephemeral, delegate: self, delegateQueue: OperationQueue())
    }
    
    func connect() {
        print("Attempting to connect to the socket at url: \(url)")
        socket = session?.webSocketTask(with: url)
        
        socket?.resume()
    }
    
    func disconnect() {
        print("📵 Closing socket...")
        socket?.cancel(with: .normalClosure, reason: String("Closing socket").data(using: .utf8))
    }
    
    func send(message: String) {
        socket?.send(.string(message), completionHandler: { error in
            if let error = error {
                print("❌ Error encountered while sending message: \(String(describing: error))")
            }
        })
    }
    
    func receive() {
        if !self.isConnected {
            return
        }
        
        socket?.receive(completionHandler: { [weak self] result in
            switch result {
            case .success(let message):
                switch message {
                case .string(let string):
                    print("Received Message as String: \(string)")
                    self?.receivedMessages.append(string)
                    break
                case .data(let data):
                    print("Received Message as Data: \(data)")
                    break
                @unknown default:
                    fatalError("Received an unexpected type of message!")
                }
                break
            case .failure(let error):
                print("Received Error: \(error)")
                self?.isConnected = false
                break
            }
            
            self?.receive()
        })
    }
    
    func ping() {
        socket?.sendPing(pongReceiveHandler: { [weak self] error in
            if let error = error {
                print("❌ Received error while pinging server: \(error)")
                self?.isConnected = false
            }
            
            DispatchQueue.main.asyncAfter(deadline: .now() + .seconds(5)) {
                self?.ping()
            }
        })
    }
    
    func urlSession(_ session: URLSession, task: URLSessionTask, didCompleteWithError error: Error?) {
        if let error = error {
            print("❌ URLSession task did complete with error: \(error)")
            isConnected = false
        }
    }
    
    func urlSession(_ session: URLSession, webSocketTask: URLSessionWebSocketTask, didOpenWithProtocol protocol: String?) {
        print("🤝 Completed Handshake Successfully.")
        isConnected = true
        receive()
    }
    
    func urlSession(_ session: URLSession, webSocketTask: URLSessionWebSocketTask, didCloseWith closeCode: URLSessionWebSocketTask.CloseCode, reason: Data?) {
        print("Closed connection to socket due to : \(closeCode)")
        isConnected = false
    }
}