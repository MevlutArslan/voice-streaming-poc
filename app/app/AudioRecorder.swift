//
//  AudioRecorder.swift
//  app
//
//  Created by Mevlut Arslan on 1/30/24.
//

import Foundation
import AVFoundation
import Speech

extension AVAudioPCMBuffer {
    func data() -> Data {
        let channelCount = 1  // given PCMBuffer channel count is 1
        if self.int16ChannelData == nil {
            print("failed to get int16 data")
            return Data()
        }
        let channels = UnsafeBufferPointer(start: self.int16ChannelData, count: channelCount)
        let ch0Data = Data(bytes: channels[0], count: Int(frameCapacity * format.streamDescription.pointee.mBytesPerFrame))
        return ch0Data
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
    
    private let speechRecognizer = SFSpeechRecognizer()!
    var recognitionRequest = SFSpeechAudioBufferRecognitionRequest()
    var recognitionTask: SFSpeechRecognitionTask?
    
    private let recordingFormat = AVAudioFormat(commonFormat: .pcmFormatInt16, sampleRate: 48000, channels: 1, interleaved: false)
    
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
    
    private func isPunctuation(word: String) -> Bool {
        let punctuationSet: Set<Character> = Set(".,?!;:-")
        return word.count >= 1 && punctuationSet.contains(word.last ?? Character(""))
    }

    func startRecording() {
        guard authorizedToRecord else {
            print("❌ Not authorized to record.")
            return
        }
        
        self.recognitionRequest.shouldReportPartialResults = true
        self.recognitionRequest.addsPunctuation = true
        
        self.recognitionTask = speechRecognizer.recognitionTask(with: recognitionRequest) { result, error in
//            var isFinal = false
                        
            if let result = result {
                print("IS_FINAL: \(result.isFinal)")
                print("Transcription: \(result.bestTranscription.formattedString)")
                
//                if result.isFinal {
//                    print("FULL TRANSCRIPTION: \(result.bestTranscription.formattedString)")
//                }
//                // Handle the current transcribed word
//                let bestString = result.bestTranscription.formattedString
//                let words = bestString.components(separatedBy: " ")
//                let lastWord = words.last ?? ""
//                
//                print(lastWord)
//                let isPunctuation = self.isPunctuation(word: lastWord)
//
//                if isPunctuation {
//                    print("Last word transcribed is punctuation: \(lastWord)")
//                } else {
//                    print("Last word transcribed is not punctuation: \(lastWord)")
//                }
            }
            
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
        
        var isInASilentWindow = false
        var silentWindowStartTime: Date?
        
        inputNode.installTap(onBus: .zero, bufferSize: 4096, format: recordingFormat) { [weak self] (buffer, time) in
            guard let self = self else { return }
            
//            self.recognitionRequest.append(buffer)

            if self.socketService.isConnected {
//                var shouldSendBuffer = true
                let bytebuffer = buffer.data()
//
//                let isSilent = self.audioIsSilent(buffer)
//                
//                if !isSilent {
//                    // Reset silent window state when non-silent audio is detected
//                    isInASilentWindow = false
//                    silentWindowStartTime = nil
//                }
//
//                if isSilent && !isInASilentWindow {
//                    // Start a new silent window
//                    isInASilentWindow = true
//                    silentWindowStartTime = Date()
//                } else if isSilent && isInASilentWindow {
//                    // Calculate the time passed since the start of the silent window
//                    if let silentWindowStartTime = silentWindowStartTime {
//                        let timePassed = Date().timeIntervalSince(silentWindowStartTime)
//
//                        if timePassed >= 10 {
//                            // If silent window duration exceeds 1 second, block streaming of the buffer
////                            shouldSendBuffer = false
//                        }
//                    }
//                }

//                if shouldSendBuffer {
//                    print("sending data!")
                Task.init {
                    await self.socketService.send(data: bytebuffer)
                }
//                }
            }
        }
        
    }
    
    private func audioIsSilent(_ buffer: AVAudioPCMBuffer) -> Bool {
        let rms = calculateRMS(buffer: buffer)
        if rms < 0.01 {
            return true
        }
        
        return false
    }
    
    func stopRecording() {
        if audioEngine.isRunning {
            recognitionRequest.endAudio()
            inputNode.removeTap(onBus: .zero)
            
            audioEngine.stop()
            print("Audio recorded for \(audioDuration) seconds.")
            audioDuration = 0
        }
    }
    
    private func calculateRMS(buffer: AVAudioPCMBuffer) -> Float {
        let audioData = UnsafeBufferPointer(start: buffer.int16ChannelData![0], count: Int(buffer.frameLength))
        let sumOfSquares = audioData.reduce(0) { (result, sample) -> Int in
            let squaredSample = Int(sample) * Int(sample)
            return result + squaredSample
        }
        let rms = sqrt(Float(sumOfSquares) / Float(buffer.frameLength))
        return rms
    }
    
}
