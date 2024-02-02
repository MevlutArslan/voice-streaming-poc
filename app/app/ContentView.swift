//
//  ContentView.swift
//  app
//
//  Created by Mevlut Arslan on 1/29/24.
//

import SwiftUI

struct ContentView: View {
    @ObservedObject var socketService = SocketService()
    private var audioRecorder: AudioRecorder!
    @State var message: String = ""
    
    @State var isRecording = false
    @State var isPlaying = false
    
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
                })
            
//            Button(action: {
//                if isPlaying {
//                    audioRecorder.stopPlaying()
//                    isPlaying = false
//                } else {
//                    audioRecorder.startPlaying()
//                    isPlaying = true
//                }
//            }, label: {
//                    ZStack {
//                        Circle()
//                            .strokeBorder(.black)
//                            .fill(.clear)
//                            .frame(width: UIScreen.main.bounds.width * 0.45)
//                        
//                        Image(systemName: isPlaying ? "square" : "play")
//                            .font(.system(size: 50))
//                    }
//                })
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
