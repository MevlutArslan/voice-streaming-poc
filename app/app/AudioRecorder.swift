//
//  AudioRecorder.swift
//  app
//
//  Created by Mevlut Arslan on 1/30/24.
//

import Foundation
import AVFoundation

extension AVAudioPCMBuffer {
    func data() -> Data {
        let channelCount = 1  // given PCMBuffer channel count is 1
        let channels = UnsafeBufferPointer(start: self.floatChannelData, count: channelCount)
        let ch0Data = NSData(bytes: channels[0], length:Int(self.frameCapacity * self.format.streamDescription.pointee.mBytesPerFrame))
        return ch0Data as Data
    }
}

class AudioRecorder {
    private var audioEngine: AVAudioEngine!
    
    private var inputNode: AVAudioInputNode!
    private var outputNode: AVAudioOutputNode!
    private var playerNode: AVAudioPlayerNode!
    private var audioSession: AVAudioSession!
    private var mainMixerNode: AVAudioMixerNode!
    
    private var socketService: SocketService!

    private var authorizedToRecord = false
    private var buffers: [AVAudioPCMBuffer] = []
    
    var audioDuration = 0.0
    
    init(socketService: SocketService) {
        AVAudioApplication.requestRecordPermission { permissionGiven in
            self.authorizedToRecord = permissionGiven
            if permissionGiven == false {
                print("❌ Failed to gain access to the microphone!")
                return
            }
        }
        
        self.socketService = socketService
        audioSession = AVAudioSession.sharedInstance()
        audioEngine = AVAudioEngine()
        playerNode = AVAudioPlayerNode()
        
        inputNode = audioEngine.inputNode // inputNode is created when you access AVAudioEngine.inputNode
        outputNode = audioEngine.outputNode
        mainMixerNode = audioEngine.mainMixerNode
        
        audioEngine.attach(playerNode)
        
        do {
            try audioSession.setCategory(.playAndRecord)
            try audioSession.overrideOutputAudioPort(.speaker)

//            try audioSession.setMode(.voiceChat)
        }catch {
            print("Failed to set category for AVAudioSession: \(error)")
        }
    }

    func startRecording() {
        guard authorizedToRecord else {
            print("❌ Not authorized to record.")
            return
        }
                
        /* You can activate the audio session at any time after setting its category, but it’s generally preferable to defer this call until your app begins audio playback. */
        try! audioSession.setActive(true)
        
        do {
            print("STARTING AUDIO ENGINE.")
            try audioEngine.start()
        } catch {
            print("❌ Failed to start recording: \(error)")
            return
        }
        
        inputNode.installTap(onBus: .zero, bufferSize: 4096, format: nil, block: { (buffer, time) in
            let duration = Double(buffer.frameLength) / Double(buffer.format.sampleRate)
            self.audioDuration += duration
            if self.socketService.isConnected {
                let bytebuffer = buffer.data()
                self.socketService.send(data: bytebuffer)
            }
        })
        
        
    }
    
    func stopRecording() {
        if audioEngine.isRunning {
            inputNode.removeTap(onBus: .zero)
                
            audioEngine.stop()
            print("Audio recorded for \(audioDuration) seconds.")
            audioDuration = 0
        }
    }
    
    func startPlaying() {
        
        audioEngine.connect(playerNode, to:outputNode, format: buffers[0].format)

        // Start audio engine
        try! self.audioEngine.start()
        
        for buffer in buffers {
            playerNode.scheduleBuffer(buffer) {
                print("completed playing buffer")
            }
        }
        
        playerNode.play()
    }
    
    func stopPlaying() {
        playerNode.stop()
        audioEngine.stop()
        
        buffers = []
    }
    
}
