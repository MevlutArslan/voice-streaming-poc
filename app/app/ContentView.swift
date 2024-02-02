//
//  ContentView.swift
//  app
//
//  Created by Mevlut Arslan on 1/29/24.
//

import SwiftUI

struct ContentView: View {
    @ObservedObject var socketService = SocketService()
    
    @State var message: String = ""
    
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
            
            HStack {
                TextField("Message", text: $message)
                Button(action: {
                    socketService.send(message: message)
                    message = ""
                }, label: {
                    Text("Send Message")
                }).disabled(!socketService.isConnected)
            }
            .padding()
            .border(.black, width: /*@START_MENU_TOKEN@*/1/*@END_MENU_TOKEN@*/)
            VStack {
                List {
                    ForEach(socketService.receivedMessages, id: \.self) { message in
                        Text(message)
                    }
                }
            }
        }
        .padding()
    }
} 

#Preview {
    ContentView()
}
