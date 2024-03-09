//
//  ContentView.swift
//  app
//
//  Created by Mevlut Arslan on 1/29/24.
//

import SwiftUI

struct ContentView: View {

    @ObservedObject var viewController = MainViewController()
    
    var body: some View {
        VStack {
            Image(systemName: viewController.isConnected ? "network" : "network.slash")
                .font(.system(size:50))
            
            ZStack {
                VStack {
                    Button(action: {
                        viewController.connect()
                    }, label: {
                        Text("Connect to Server")
                    })
                    .disabled(viewController.isConnected)
                    
                    
                    Button(action: {
                        viewController.disconnect()
                    }, label: {
                        Text("Disconnect from the server")
                    })
                    .disabled(!viewController.isConnected)
                    
                }
                
                if viewController.isConnecting {
                    ProgressView()
                        .controlSize(.extraLarge)
                }
            }
            
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
