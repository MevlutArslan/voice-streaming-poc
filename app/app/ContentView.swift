//
//  ContentView.swift
//  app
//
//  Created by Mevlut Arslan on 1/29/24.
//

import SwiftUI

struct ContentView: View {
    @ObservedObject var socketService = SocketService()
    @State var isRecording = false
    private var audioRecorder: AudioRecorder!

    init() {
        self.audioRecorder = AudioRecorder(socketService: socketService)
    }

    var body: some View {
        VStack {
            Image(systemName: socketService.isConnected ? "network" : "network.slash")
                .font(.system(size:50))
            
            Button(action: {
                socketService.connect()
            }, label: {
                Text("Connect to Server")
            }).disabled(socketService.isConnected)
            
            Button(action: {
                socketService.disconnect()
            }, label: {
                Text("Disconnect from the server")
            }).disabled(!socketService.isConnected)
            
            /*
                Record Audio
             */
            
            // Record Audio
            Button(action: {
                if isRecording {
                    audioRecorder.stopRecording()
                    isRecording = false
                } else {
                    audioRecorder.startRecording()
                    isRecording = true
                }
            }, label: {
                    ZStack {
                        Circle()
                            .strokeBorder(.black)
                            .fill(.clear)
                            .frame(width: UIScreen.main.bounds.width * 0.45)
                        
                        Image(systemName: isRecording ? "square" : "mic")
                            .font(.system(size: 50))
                    }
                }
            )
//            .disabled(!socketService.isConnected)
        }
        .padding()
    }
} 

struct MessageView: View {
    @State var messages: [String]
    
    var body: some View {
        VStack {
            List {
                ForEach(messages, id: \.self) { message in
                    Text(message)
                }
            }
        }
    }
}

#Preview {
    ContentView()
}
