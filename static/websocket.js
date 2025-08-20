let websocket = null;
let audioContext = null;
let mediaRecorder = null;
let audioWorkletNode = null;
let audioStream = null;
let isRecording = false;
let turnCount = 0;

const startBtn = document.getElementById("startBtn");
const stopBtn = document.getElementById("stopBtn");
const clearBtn = document.getElementById("clearBtn");
const connectionStatus = document.getElementById("connectionStatus");
const listeningStatus = document.getElementById("listeningStatus");
const realTimeStatus = document.getElementById("realTimeStatus");
const interimText = document.getElementById("interimText");
const transcriptionContainer = document.getElementById(
    "transcriptionContainer"
);

// Connect to WebSocket
function connectWebSocket() {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const wsUrl = `${protocol}//${window.location.host}/ws`;

    websocket = new WebSocket(wsUrl);

    websocket.onopen = () => {
        console.log("WebSocket connected");
        connectionStatus.innerHTML =
            '<span class="text-green-300">● Connected</span>';
        addSystemMessage("Connected to turn detection server", "success");
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
                    "Listening for speech... Speak and pause to see results";
                listeningStatus.classList.remove("hidden");
            }
            break;
        case "interim_transcript":
            // Show interim results in the status area
            console.log("Received interim transcript:", data.text);
            console.log("interimText element:", interimText);
            interimText.textContent = `Speaking: "${data.text}"`;
            realTimeStatus.textContent = "Processing speech...";
            console.log(
                "Updated interimText content:",
                interimText.textContent
            );
            break;
        case "turn_end":
            // Turn ended - display final transcript
            addTurnTranscript(data.text);
            interimText.textContent = "";
            realTimeStatus.textContent =
                "Turn completed. Listening for next turn...";
            break;
        case "turn_update":
            // Update the last turn with better formatted text
            updateLastTurnTranscript(data.text);
            break;
        case "error":
            addSystemMessage(data.message, "error");
            break;
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

// Audio processing worklet (same as before)
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
        updateButtonStates();
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
        updateButtonStates();
        realTimeStatus.textContent = "Turn detection stopped";
        interimText.textContent = "";
        listeningStatus.classList.add("hidden");
    }
}

function clearTranscripts() {
    transcriptionContainer.innerHTML =
        '<div class="text-center text-gray-400 mt-8"><p>Transcripts cleared - start recording again</p></div>';
    turnCount = 0;
    realTimeStatus.textContent = "Ready to detect speech turns";
    interimText.textContent = "";
}

function updateButtonStates() {
    startBtn.disabled = isRecording;
    stopBtn.disabled = !isRecording;

    startBtn.classList.toggle("opacity-50", isRecording);
    stopBtn.classList.toggle("opacity-50", !isRecording);
    startBtn.classList.toggle("cursor-not-allowed", isRecording);
    stopBtn.classList.toggle("cursor-not-allowed", !isRecording);
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
                                    <span class="text-xs text-green-200/70">🎤 Turn Complete</span>
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
                    <span class="text-xs font-medium">${escapeHtml(
                        message
                    )}</span>
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

// Event listeners
startBtn.addEventListener("click", startRecording);
stopBtn.addEventListener("click", stopRecording);
clearBtn.addEventListener("click", clearTranscripts);

// Initialize
connectWebSocket();
