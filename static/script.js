let websocket = null;
let audioContext = null;
let audioWorkletNode = null;
let audioStream = null;
let isRecording = false;
let turnCount = 0;

// Audio playback variables
let playbackAudioContext = null;

let toggleChatBtn,
    toggleChatText,
    clearBtn,
    connectionStatus,
    listeningStatus,
    realTimeStatus,
    interimText,
    transcriptionContainer;

// Initialize audio context for playback
async function initializePlaybackAudio() {
    if (!playbackAudioContext) {
        playbackAudioContext = new (window.AudioContext ||
            window.webkitAudioContext)({
            sampleRate: 44100,
        });
    }

    // Resume context if suspended (required by browser policies)
    if (playbackAudioContext.state === "suspended") {
        await playbackAudioContext.resume();
    }
}

// Play base64 audio data
async function playAudioFromBase64(base64Audio) {
    try {
        await initializePlaybackAudio();

        const binaryString = atob(base64Audio);
        const arrayBuffer = new ArrayBuffer(binaryString.length);
        const uint8Array = new Uint8Array(arrayBuffer);

        for (let i = 0; i < binaryString.length; i++) {
            uint8Array[i] = binaryString.charCodeAt(i);
        }

        const audioBuffer = await playbackAudioContext.decodeAudioData(
            arrayBuffer
        );

        const source = playbackAudioContext.createBufferSource();
        source.buffer = audioBuffer;
        source.connect(playbackAudioContext.destination);

        console.log("Playing TTS audio...");
        source.start(0);

        // Add visual feedback
        realTimeStatus.textContent = "🔊 Playing AI response...";

        // Reset status when audio ends
        source.onended = () => {
            realTimeStatus.textContent = "🎤 Ready for your next message...";
        };
    } catch (error) {
        console.error("Error playing audio:", error);
        addSystemMessage("Failed to play audio: " + error.message, "error");
        realTimeStatus.textContent = "🎤 Ready for your next message...";
    }
}

// Connect to WebSocket
function connectWebSocket() {
    const wsUrl = `ws://${window.location.host}/ws`;
    console.log("Attempting to connect to WebSocket:", wsUrl);

    websocket = new WebSocket(wsUrl);

    websocket.onopen = () => {
        console.log("WebSocket connected");
        connectionStatus.innerHTML =
            '<span class="text-green-300">● Connected</span>';
        addSystemMessage("Connected to AI voice chat server", "success");

        // Test interim text element
        interimText.textContent = "Connection test - interim text working";
        setTimeout(() => {
            interimText.textContent = "";
        }, 2000);
    };

    websocket.onmessage = (event) => {
        const data = JSON.parse(event.data);
        handleWebSocketMessage(data);
    };

    websocket.onclose = () => {
        console.log("WebSocket disconnected");
        connectionStatus.innerHTML =
            '<span class="text-red-300">● Disconnected</span>';
        addSystemMessage("Disconnected from server", "error");
    };

    websocket.onerror = (error) => {
        console.error("WebSocket error:", error);
        connectionStatus.innerHTML =
            '<span class="text-red-300">● Error</span>';
        addSystemMessage("Connection error", "error");
    };
}

function handleWebSocketMessage(data) {
    switch (data.type) {
        case "connection":
            addSystemMessage(data.message, "info");
            break;
        case "status":
            addSystemMessage(data.message, "info");
            if (data.message.includes("started")) {
                realTimeStatus.textContent =
                    "🎤 Listening... Speak to start AI conversation";
                listeningStatus.classList.remove("hidden");
            }
            break;
        case "interim_transcript":
            // console.log("Received interim transcript:", data.text);
            interimText.textContent = `Speaking: "${data.text}"`;
            realTimeStatus.textContent = "Processing speech...";
            break;
        case "turn_end":
            addTurnTranscript(data.text);
            interimText.textContent = "";
            realTimeStatus.textContent = "🤖 Processing with AI...";
            break;
        case "turn_update":
            updateLastTurnTranscript(data.text);
            break;
        case "llm_thinking":
            realTimeStatus.textContent = "🤖 AI is thinking...";
            addSystemMessage("AI is processing your message...", "info");
            break;
        case "llm_response_start":
            realTimeStatus.textContent = "🤖 AI is responding...";
            startAIResponse();
            break;
        case "llm_response_chunk":
            // console.log("LLM chunk received:", data.chunk);
            appendAIResponseChunk(data.chunk);
            break;
        case "llm_response_complete":
            // console.log("WebSocket message received:", data.final_response);
            completeAIResponse(data.final_response);
            realTimeStatus.textContent = "🎤 Ready for your next message...";
            break;
        case "tts_response":
            // Handle TTS audio response
            console.log(
                `Received TTS audio (base64 length: ${data.audio.length})`
            );
            if (data.audio) {
                playAudioFromBase64(data.audio);
            }
            break;
        case "llm_error":
            addSystemMessage(data.message, "error");
            realTimeStatus.textContent = "🎤 Ready for your next message...";
            break;
        case "error":
            addSystemMessage(data.message, "error");
            break;
    }
}

let currentAIResponseElement = null;
let currentAIResponseText = "";

function startAIResponse() {
    // Create a new AI response element
    const responseElement = document.createElement("div");
    responseElement.className = "mb-4 animate-fadeIn";
    responseElement.innerHTML = `
    <div class="bg-gradient-to-r from-purple-500/20 to-pink-500/20 rounded-2xl p-4 border border-purple-500/30">
        <div class="flex items-start gap-3">
            <div class="w-8 h-8 bg-gradient-to-r from-purple-500 to-pink-500 rounded-full flex items-center justify-center flex-shrink-0">
                <span class="text-white text-sm font-bold">🤖</span>
            </div>
            <div class="flex-1">
                <p class="ai-response-text text-white text-sm leading-relaxed"></p>
                <div class="flex items-center justify-between mt-2 pt-2 border-t border-purple-400/20">
                    <span class="text-xs text-purple-200/70">🤖 AI Response</span>
                    <span class="text-xs text-purple-200/70">${new Date().toLocaleTimeString()}</span>
                </div>
            </div>
        </div>
    </div>
`;

    transcriptionContainer.appendChild(responseElement);
    currentAIResponseElement =
        responseElement.querySelector(".ai-response-text");
    currentAIResponseText = "";

    // Scroll to bottom
    transcriptionContainer.scrollTop = transcriptionContainer.scrollHeight;
}

function appendAIResponseChunk(chunk) {
    if (currentAIResponseElement) {
        currentAIResponseText += chunk;
        currentAIResponseElement.textContent = currentAIResponseText;

        // Auto-scroll to keep the response visible
        transcriptionContainer.scrollTop = transcriptionContainer.scrollHeight;
    }
}

function completeAIResponse(finalResponse) {
    if (currentAIResponseElement) {
        // Ensure the final response is complete
        currentAIResponseElement.textContent = finalResponse;

        // Add a subtle animation to indicate completion
        currentAIResponseElement.parentElement.style.animation =
            "pulse 0.5s ease-in-out";

        // Clear current response tracking
        currentAIResponseElement = null;
        currentAIResponseText = "";

        // Scroll to bottom
        transcriptionContainer.scrollTop = transcriptionContainer.scrollHeight;
    }
}

function updateLastTurnTranscript(newText) {
    // Find the last turn card and update its text
    const lastCard = transcriptionContainer.lastElementChild;
    if (lastCard && lastCard.querySelector(".transcript-text")) {
        lastCard.querySelector(".transcript-text").textContent = newText;
        console.log(`Updated last turn with: ${newText}`);
    }
}

// Audio processing worklet
const audioWorkletCode = `
class AudioProcessor extends AudioWorkletProcessor {
    constructor() {
        super();
        this.bufferSize = 1600; // 100ms at 16kHz
        this.buffer = new Float32Array(this.bufferSize);
        this.bufferIndex = 0;
    }

    process(inputs, outputs, parameters) {
        const input = inputs[0];
        if (input.length > 0) {
            const inputChannel = input[0];
            
            for (let i = 0; i < inputChannel.length; i++) {
                this.buffer[this.bufferIndex] = inputChannel[i];
                this.bufferIndex++;
                
                if (this.bufferIndex >= this.bufferSize) {
                    // Convert to 16-bit PCM
                    const pcmData = new Int16Array(this.bufferSize);
                    for (let j = 0; j < this.bufferSize; j++) {
                        const sample = Math.max(-1, Math.min(1, this.buffer[j]));
                        pcmData[j] = sample < 0 ? sample * 0x8000 : sample * 0x7FFF;
                    }
                    
                    // Send PCM data
                    this.port.postMessage(pcmData.buffer);
                    
                    // Reset buffer
                    this.bufferIndex = 0;
                }
            }
        }
        return true;
    }
}

registerProcessor('audio-processor', AudioProcessor);
`;

async function startRecording() {
    try {
        // Initialize playback audio context early (user interaction required)
        await initializePlaybackAudio();

        // Get audio stream
        audioStream = await navigator.mediaDevices.getUserMedia({
            audio: {
                sampleRate: 16000,
                channelCount: 1,
                echoCancellation: true,
                noiseSuppression: true,
                autoGainControl: true,
            },
        });

        // Create audio context
        audioContext = new AudioContext({ sampleRate: 16000 });

        // Create worklet
        const workletBlob = new Blob([audioWorkletCode], {
            type: "application/javascript",
        });
        const workletUrl = URL.createObjectURL(workletBlob);

        await audioContext.audioWorklet.addModule(workletUrl);
        audioWorkletNode = new AudioWorkletNode(
            audioContext,
            "audio-processor"
        );

        // Create source and connect
        const source = audioContext.createMediaStreamSource(audioStream);
        source.connect(audioWorkletNode);

        // Handle audio data
        audioWorkletNode.port.onmessage = (event) => {
            if (
                websocket &&
                websocket.readyState === WebSocket.OPEN &&
                isRecording
            ) {
                websocket.send(event.data);
            }
        };

        // Send start command
        websocket.send(JSON.stringify({ command: "start_recording" }));

        isRecording = true;
        realTimeStatus.textContent = "🎤 Starting AI voice chat...";
    } catch (error) {
        console.error("Error starting recording:", error);
        addSystemMessage(
            "Failed to start recording: " + error.message,
            "error"
        );
    }
}

function stopRecording() {
    if (isRecording) {
        // Send stop command
        websocket.send(JSON.stringify({ command: "stop_recording" }));

        // Clean up audio resources
        if (audioWorkletNode) {
            audioWorkletNode.disconnect();
            audioWorkletNode = null;
        }

        if (audioContext) {
            audioContext.close();
            audioContext = null;
        }

        if (audioStream) {
            audioStream.getTracks().forEach((track) => track.stop());
            audioStream = null;
        }

        isRecording = false;
        realTimeStatus.textContent = "AI voice chat stopped";
        interimText.textContent = "";
        listeningStatus.classList.add("hidden");
    }
}

function clearTranscripts() {
    transcriptionContainer.innerHTML =
        '<div class="text-center text-gray-400 mt-8"><p>Conversation cleared - start AI chat again</p></div>';
    turnCount = 0;
    realTimeStatus.textContent = "Ready for AI voice conversation";
    interimText.textContent = "";
}

function addTurnTranscript(text) {
    if (turnCount === 0) {
        transcriptionContainer.innerHTML = "";
    }

    turnCount++;

    // Create turn transcript
    const transcriptElement = document.createElement("div");
    transcriptElement.className = "mb-4 animate-fadeIn";
    transcriptElement.innerHTML = `
    <div class="bg-gradient-to-r from-green-500/20 to-blue-500/20 rounded-2xl p-4 border border-green-500/30">
        <div class="flex items-start gap-3">
            <div class="w-8 h-8 bg-gradient-to-r from-green-500 to-blue-500 rounded-full flex items-center justify-center flex-shrink-0">
                <span class="text-white text-sm font-bold">${turnCount}</span>
            </div>
            <div class="flex-1">
                <p class="transcript-text text-white text-sm leading-relaxed">${escapeHtml(
                    text
                )}</p>
                <div class="flex items-center justify-between mt-2 pt-2 border-t border-green-400/20">
                    <span class="text-xs text-green-200/70">👨🏻User</span>
                    <span class="text-xs text-green-200/70">${new Date().toLocaleTimeString()}</span>
                </div>
            </div>
        </div>
    </div>
`;

    transcriptionContainer.appendChild(transcriptElement);

    // Scroll to bottom
    transcriptionContainer.scrollTop = transcriptionContainer.scrollHeight;
}

function addSystemMessage(message, type = "info") {
    const messageElement = document.createElement("div");
    messageElement.className = "text-center my-4 animate-fadeIn";

    let bgClass, textClass, icon;
    switch (type) {
        case "error":
            bgClass = "bg-red-500/10 border-red-400/20";
            textClass = "text-red-300";
            icon = "❌";
            break;
        case "success":
            bgClass = "bg-green-500/10 border-green-400/20";
            textClass = "text-green-300";
            icon = "✅";
            break;
        default:
            bgClass = "bg-blue-500/10 border-blue-400/20";
            textClass = "text-blue-300";
            icon = "ℹ️";
    }

    messageElement.innerHTML = `
    <div class="inline-flex items-center gap-2 px-4 py-2 rounded-full ${bgClass} border backdrop-blur-sm ${textClass}">
        <span>${icon}</span>
        <span class="text-xs font-medium">${escapeHtml(message)}</span>
    </div>
`;

    transcriptionContainer.appendChild(messageElement);
    transcriptionContainer.scrollTop = transcriptionContainer.scrollHeight;
}

function escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
}

// Initialize on page load
document.addEventListener("DOMContentLoaded", function () {
    toggleChatBtn = document.getElementById("toggleChatBtn");
    clearBtn = document.getElementById("clearBtn");
    connectionStatus = document.getElementById("connectionStatus");
    listeningStatus = document.getElementById("listeningStatus");
    realTimeStatus = document.getElementById("realTimeStatus");
    interimText = document.getElementById("interimText");
    transcriptionContainer = document.getElementById("transcriptionContainer");

    if (toggleChatBtn) {
        toggleChatText = document.getElementById("toggleChatText");
        toggleChatBtn.addEventListener("click", async () => {
            if (!isRecording) {
                await startRecording();
                toggleChatText.innerHTML = `
                                    <div
                                        class="w-4 h-4 bg-white rounded-full animate-pulse"
                                    ></div>
                `;
                toggleChatBtn.classList.add("bg-red-400/50", "border-red-400");
                toggleChatBtn.classList.remove(
                    "hover:bg-green-400/50",
                    "hover:border-green-400"
                );
            } else {
                stopRecording();
                toggleChatText.innerHTML = `
                <svg
                                        xmlns="http://www.w3.org/2000/svg"
                                        width="32px"
                                        height="32px"
                                        viewBox="0 0 24 24"
                                        fill="none"
                                    >
                                        <path
                                            d="M20 12V13C20 17.4183 16.4183 21 12 21C7.58172 21 4 17.4183 4 13V12M12 17C9.79086 17 8 15.2091 8 13V7C8 4.79086 9.79086 3 12 3C14.2091 3 16 4.79086 16 7V13C16 15.2091 14.2091 17 12 17Z"
                                            stroke="#ffffff"
                                            stroke-width="2"
                                            stroke-linecap="round"
                                            stroke-linejoin="round"
                                        />
                                    </svg>
                                    `;
                toggleChatBtn.classList.remove(
                    "bg-red-400/50",
                    "border-red-400"
                );
                toggleChatBtn.classList.add(
                    "hover:bg-green-400/50",
                    "hover:border-green-400"
                );
            }
        });
    }
    if (clearBtn) clearBtn.addEventListener("click", clearTranscripts);

    console.log("Connecting to WebSocket...");
    // Connect WebSocket
    connectWebSocket();
});