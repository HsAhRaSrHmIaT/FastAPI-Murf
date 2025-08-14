// == GLOBALS ==
let mediaRecorder, record, stop, reset;
let chunks = [];
let sessionId;
let userAudioBlobs = [];
let isRecording = false;
let conversationCount = 0;

// -- DOM ------------------------------------------------------------
const $ = (sel) => document.getElementById(sel);

// Enhanced status display function - now just uses conversation panel
function showStatus(type, message, duration = 3000) {
    // Use the conversation panel for status messages instead of separate status area
    addSystemMessage(message, type);
}

// Health status display
function updateHealthStatus(healthData) {
    const sessionInfo = $("sessionInfo");
    if (!sessionInfo) return;

    let statusIcon = "🟢";
    let statusText = "Healthy";
    let statusClass = "text-green-300";

    if (healthData.status === "degraded") {
        statusIcon = "🟡";
        statusText = "Degraded";
        statusClass = "text-yellow-300";
    } else if (healthData.status === "down") {
        statusIcon = "🔴";
        statusText = "Down";
        statusClass = "text-red-300";
    }

    let healthInfo = `${statusIcon} Server: ${statusText}`;
    if (healthData.missing_api_keys && healthData.missing_api_keys.length > 0) {
        healthInfo += ` (Missing: ${healthData.missing_api_keys.join(", ")})`;
    }

    const sessionElement = $("sessionId");
    if (sessionElement) {
        sessionElement.innerHTML = `
      <div class="italic">ID: ${sessionId}</div>
      <div class="${statusClass} text-xs mt-1 text-center select-none">${healthInfo}</div>
    `;
    }
}

// == SESSION INIT ==
function getSessionId() {
    const urlParams = new URLSearchParams(window.location.search);
    let s = urlParams.get("session");
    if (!s) {
        s =
            "session_" +
            Date.now() +
            "_" +
            Math.random().toString(36).substring(2, 11);
        urlParams.set("session", s);
        window.history.replaceState(
            {},
            "",
            `${window.location.pathname}?${urlParams}`
        );
    }
    return s;
}
sessionId = getSessionId();

// Initialize session display
function initializeSessionDisplay() {
    const sessionElement = $("sessionId");
    const sessionInfoElement = $("sessionInfo");

    if (sessionElement) {
        sessionElement.textContent = `Session: ${sessionId}`;
    }

    if (sessionInfoElement) {
        sessionInfoElement.classList.remove("hidden");
    }
}

// == RECORD CONTROLS ==
function enableRecordingUI(recording) {
    if (!record || !stop || !reset) return;

    record.disabled = recording;
    stop.disabled = !recording;
    reset.disabled = recording;

    record.classList.toggle("opacity-50", recording);
    stop.classList.toggle("opacity-50", !recording);
    record.classList.toggle("cursor-not-allowed", recording);
    stop.classList.toggle("cursor-not-allowed", !recording);

    if (recording) {
        record.classList.add("animate-pulse");
    } else {
        record.classList.remove("animate-pulse");
    }
}

// Conversation Panel Management
function addMessageToConversation(content, isUser = true, timestamp = null) {
    const messagesContainer = $("messagesContainer");
    if (!messagesContainer) return;

    // Clear welcome message on first interaction
    if (conversationCount === 0) {
        messagesContainer.innerHTML = "";
    }

    conversationCount++;
    const messageTime =
        timestamp ||
        new Date().toLocaleTimeString([], {
            hour: "2-digit",
            minute: "2-digit",
        });

    const messageElement = document.createElement("div");
    messageElement.className = "message-item mb-4 animate-fadeIn";

    if (isUser) {
        messageElement.innerHTML = `
      <div class="flex items-start gap-3 justify-end">
        <div class="bg-gradient-to-r from-blue-600/80 to-blue-500/80 rounded-2xl rounded-tr-none p-4 max-w-xs lg:max-w-md border border-blue-500/30 shadow-lg">
          <p class="text-white text-sm leading-relaxed">${escapeHtml(
              content
          )}</p>
          <div class="flex items-center justify-between mt-2 pt-2 border-t border-blue-400/20">
            <span class="text-xs text-blue-200/70">#${conversationCount}</span>
            <span class="text-xs text-blue-200/70">${messageTime}</span>
          </div>
        </div>
        <div class="w-8 h-8 bg-gradient-to-r from-blue-600 to-blue-500 rounded-full flex items-center justify-center flex-shrink-0">
          <svg class="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"></path>
          </svg>
        </div>
      </div>
    `;
    } else {
        messageElement.innerHTML = `
      <div class="flex items-start gap-3">
        <div class="w-8 h-8 bg-gradient-to-r from-purple-500 to-blue-500 rounded-full flex items-center justify-center flex-shrink-0">
          <svg class="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"></path>
          </svg>
        </div>
        <div class="bg-gradient-to-r from-purple-500/20 to-blue-500/20 rounded-2xl rounded-tl-none p-4 max-w-xs lg:max-w-md border border-purple-500/30 shadow-lg">
          <p class="text-white text-sm leading-relaxed">${escapeHtml(
              content
          )}</p>
          <div class="flex items-center justify-between mt-2 pt-2 border-t border-purple-400/20">
            <span class="text-xs text-purple-200/70">#${conversationCount}</span>
            <span class="text-xs text-purple-200/70">${messageTime}</span>
          </div>
        </div>
      </div>
    `;
    }

    messagesContainer.appendChild(messageElement);

    // Scroll to bottom
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

function addSystemMessage(content, type = "info") {
    const messagesContainer = $("messagesContainer");
    if (!messagesContainer) return;

    const messageElement = document.createElement("div");
    messageElement.className = "system-message text-center my-4 animate-fadeIn";

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
        case "warning":
        case "warn":
            bgClass = "bg-yellow-500/10 border-yellow-400/20";
            textClass = "text-yellow-300";
            icon = "⚠️";
            break;
        default:
            bgClass = "bg-blue-500/10 border-blue-400/20";
            textClass = "text-blue-300";
            icon = "ℹ️";
    }

    messageElement.innerHTML = `
    <div class="inline-flex items-center gap-2 px-4 py-2 rounded-full ${bgClass} border backdrop-blur-sm ${textClass}">
      <span>${icon}</span>
      <span class="text-xs font-medium">${escapeHtml(content)}</span>
    </div>
  `;

    messagesContainer.appendChild(messageElement);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

function clearConversation() {
    const messagesContainer = $("messagesContainer");
    if (!messagesContainer) return;

    messagesContainer.innerHTML = `
    <div class="flex items-start gap-3">
      <div class="w-8 h-8 bg-gradient-to-r from-purple-500 to-blue-500 rounded-full flex items-center justify-center flex-shrink-0">
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"></path>
        </svg>
      </div>
      <div class="bg-gradient-to-r from-purple-500/20 to-blue-500/20 rounded-2xl rounded-tl-none p-4 max-w-xs border border-purple-500/30">
        <p class="text-white text-sm">👋 Hi! I'm your AI voice assistant. Click Record to start our conversation!</p>
      </div>
    </div>
  `;
    conversationCount = 0;
}

function escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
}

// Typing indicator functions
function showTypingIndicator() {
    const typingIndicator = $("typingIndicator");
    if (typingIndicator) {
        typingIndicator.classList.remove("hidden");
        const messagesContainer = $("messagesContainer");
        if (messagesContainer) {
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
        }
    }
}

function hideTypingIndicator() {
    const typingIndicator = $("typingIndicator");
    if (typingIndicator) {
        typingIndicator.classList.add("hidden");
    }
}

// Health check function
async function checkServerHealth() {
    try {
        const response = await fetch("/health");
        if (response.ok) {
            const healthData = await response.json();
            updateHealthStatus(healthData);

            if (healthData.status === "degraded") {
                addSystemMessage(
                    `Server degraded: Missing ${healthData.missing_api_keys.join(
                        ", "
                    )}`,
                    "warning"
                );
            }
        } else {
            updateHealthStatus({ status: "down" });
            addSystemMessage("Server connection failed", "error");
        }
    } catch (error) {
        updateHealthStatus({ status: "down" });
        console.error("Health check failed:", error);
    }
}

// == RECORDING LOGIC ==
async function initializeRecording() {
    try {
        console.log("Requesting microphone access...");
        addSystemMessage("Requesting microphone access...", "info");

        const stream = await navigator.mediaDevices.getUserMedia({
            audio: {
                echoCancellation: true,
                noiseSuppression: true,
                autoGainControl: true,
            },
        });

        console.log("Microphone access granted");
        addSystemMessage(
            "Microphone access granted! Ready to record.",
            "success"
        );

        mediaRecorder = new MediaRecorder(stream, {
            mimeType: "audio/webm;codecs=opus",
        });

        record = $("record");
        stop = $("stop");
        reset = $("reset");

        // UI
        enableRecordingUI(false);

        // Handlers
        record.onclick = () => {
            if (isRecording) return;

            chunks = [];
            isRecording = true;
            enableRecordingUI(true);
            mediaRecorder.start();
            showStatus("info", "🎙️ Recording... Speak now!");
            addSystemMessage("Recording started - speak now!", "info");
        };

        stop.onclick = () => {
            if (!isRecording) return;

            isRecording = false;
            enableRecordingUI(false);
            mediaRecorder.stop();
            showStatus("info", "🛑 Recording stopped, processing...");
            addSystemMessage("Recording stopped, processing...", "info");
        };

        reset.onclick = doReset;

        mediaRecorder.ondataavailable = (e) => {
            if (e.data.size > 0) {
                chunks.push(e.data);
            }
        };

        mediaRecorder.onstop = async () => {
            if (chunks.length === 0) {
                showStatus("error", "No audio data recorded");
                addSystemMessage("No audio data recorded", "error");
                return;
            }

            let blob = new Blob(chunks, { type: "audio/webm" });
            console.log("Audio blob created:", blob.size, "bytes");

            // Save to buffer in case user clicks play on user's message
            userAudioBlobs.push(blob);
            await sendAudio(blob);
        };

        mediaRecorder.onerror = (event) => {
            console.error("MediaRecorder error:", event.error);
            showStatus("error", `Recording error: ${event.error.name}`);
            addSystemMessage(`Recording error: ${event.error.name}`, "error");
            isRecording = false;
            enableRecordingUI(false);
        };
    } catch (err) {
        console.error("Error accessing microphone:", err);
        let errorMessage = "Microphone access denied";
        let suggestion = "Please reload and allow microphone permission.";

        if (err.name === "NotAllowedError") {
            errorMessage = "Microphone permission denied";
            suggestion =
                "Please click on the microphone icon in the address bar and allow access, then refresh.";
        } else if (err.name === "NotFoundError") {
            errorMessage = "No microphone found";
            suggestion = "Please connect a microphone and refresh the page.";
        } else if (err.name === "NotReadableError") {
            errorMessage = "Microphone is busy";
            suggestion =
                "Close other applications using the microphone and refresh.";
        }

        showStatus("error", `${errorMessage}. ${suggestion}`);
        addSystemMessage(`${errorMessage}. ${suggestion}`, "error");

        // Disable recording buttons
        record = $("record");
        stop = $("stop");
        reset = $("reset");

        [record, stop, reset].forEach((btn) => {
            if (btn) {
                btn.disabled = true;
                btn.classList.add("opacity-50", "cursor-not-allowed");
            }
        });

        if (record) {
            record.onclick = () => {
                showStatus(
                    "error",
                    "Microphone access required. Please refresh and allow permission."
                );
                addSystemMessage(
                    "Microphone access required. Please refresh and allow permission.",
                    "error"
                );
            };
        }
    }
}

async function sendAudio(blob) {
    // Add typing indicator
    showStatus("info", "🤖 AI is thinking...");
    showTypingIndicator();

    // 1. Get transcription/AI response and TTS from server
    const formData = new FormData();
    formData.append("file", blob, "useraudio.webm");

    try {
        const resp = await fetch(`/agent/chat/${sessionId}`, {
            method: "POST",
            body: formData,
        });

        if (!resp.ok) {
            const errorText = await resp.text().catch(() => "Unknown error");
            showStatus("error", `Server error: ${resp.status} - ${errorText}`);
            addSystemMessage(`Server error: ${resp.status}`, "error");
            hideTypingIndicator();
            return;
        }

        const result = await resp.json();
        console.log("Server response:", result);

        // Hide typing indicator
        hideTypingIndicator();

        // Get user text from result (transcription), AI text, TTS url if available
        const userText =
            result.user_message || result.user_prompt_text || "[Audio message]";
        const aiText =
            result.assistant_response ||
            result.ai_response_text ||
            "No response received";
        const audioUrl = result.audio_url;

        // Add messages to conversation
        addMessageToConversation(userText, true);
        addMessageToConversation(aiText, false);

        // Handle errors if any
        if (result.errors) {
            const errors = result.errors;
            let errorMessages = [];

            if (errors.transcription_error) {
                errorMessages.push(
                    `Speech-to-text: ${errors.transcription_error}`
                );
            }
            if (errors.llm_error) {
                errorMessages.push(`AI processing: ${errors.llm_error}`);
            }
            if (errors.tts_error) {
                errorMessages.push(`Text-to-speech: ${errors.tts_error}`);
            }

            if (errorMessages.length > 0) {
                showStatus(
                    "warn",
                    `Partial success: ${errorMessages.join(", ")}`
                );
                addSystemMessage(
                    `Some services had issues: ${errorMessages.join(", ")}`,
                    "warning"
                );
            }
        }

        // 2. Play AI response if available
        if (audioUrl) {
            try {
                showStatus("success", "🔊 Playing AI response...");

                // Create or get audio player for AI response
                let aiAudioPlayer = $("aiAudioPlayer");
                if (!aiAudioPlayer) {
                    aiAudioPlayer = new Audio();
                    aiAudioPlayer.id = "aiAudioPlayer";
                    aiAudioPlayer.preload = "none";
                }

                aiAudioPlayer.src = audioUrl;
                await aiAudioPlayer.play();

                aiAudioPlayer.onended = () => {
                    showStatus("success", "✅ Response complete");
                };

                aiAudioPlayer.onerror = (e) => {
                    console.error("Audio playback error:", e);
                    showStatus(
                        "warn",
                        "Audio playback failed, but text response is available"
                    );
                    addSystemMessage(
                        "Audio playback failed, but you can read the text response",
                        "warning"
                    );
                };
            } catch (playError) {
                console.error("Failed to play AI audio:", playError);
                showStatus("warn", "Could not play audio response");
                addSystemMessage(
                    "Could not play audio response, but text is available",
                    "warning"
                );
            }
        } else {
            showStatus("success", "✅ Text response received (no audio)");
            if (result.errors && result.errors.tts_error) {
                addSystemMessage(
                    "Text-to-speech unavailable, but text response is ready",
                    "warning"
                );
            }
        }
    } catch (err) {
        console.error("Network error:", err);
        hideTypingIndicator();

        let errorMsg = "Network error";

        if (err.name === "TypeError" && err.message.includes("fetch")) {
            errorMsg = "Cannot connect to server";
        } else if (err.name === "AbortError") {
            errorMsg = "Request timed out";
        }

        showStatus("error", `${errorMsg}: ${err.message}`);
        addSystemMessage(`${errorMsg}: Please check your connection`, "error");
    }
}

// == RESET HANDLER ==
function doReset() {
    // Reset UI and clear chat on backend
    userAudioBlobs = [];
    isRecording = false;
    enableRecordingUI(false);
    hideTypingIndicator();

    fetch(`/agent/chat/${sessionId}`, { method: "DELETE" })
        .then(() => {
            showStatus("success", "Session reset!");
            addSystemMessage("Session reset successfully", "success");
        })
        .catch(() => {
            showStatus("error", "Could not reset on server.");
            addSystemMessage("Could not reset session on server", "error");
        });

    // Clear conversation
    clearConversation();
}

// == DOM READY ==
document.addEventListener("DOMContentLoaded", async () => {
    console.log("DOM loaded, initializing...");

    // Initialize session display
    initializeSessionDisplay();

    // Check server health
    await checkServerHealth();

    // Check browser compatibility
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        showStatus(
            "error",
            "Browser not supported. Please use Chrome, Firefox, or Safari."
        );
        addSystemMessage(
            "Browser not supported. Please use Chrome, Firefox, or Safari.",
            "error"
        );
        return;
    }

    if (!window.MediaRecorder) {
        showStatus("error", "MediaRecorder not supported in this browser.");
        addSystemMessage(
            "MediaRecorder not supported in this browser.",
            "error"
        );
        return;
    }

    // Initialize recording
    await initializeRecording();

    // Set up periodic health checks
    setInterval(checkServerHealth, 30000); // Check every 30 seconds
});

// Add CSS animations
const style = document.createElement("style");
style.textContent = `
  @keyframes fadeIn {
    from {
      opacity: 0;
      transform: translateY(10px);
    }
    to {
      opacity: 1;
      transform: translateY(0);
    }
  }

  .animate-fadeIn {
    animation: fadeIn 0.3s ease-out;
  }

  .message-item:hover {
    transform: translateY(-2px);
    transition: transform 0.2s ease;
  }

  .system-message {
    animation: fadeIn 0.4s ease-out;
  }

  #messagesContainer {
    scroll-behavior: smooth;
  }

  /* Custom scrollbar for WebKit browsers */
  #messagesContainer::-webkit-scrollbar {
    width: 6px;
  }

  #messagesContainer::-webkit-scrollbar-track {
    background: rgba(255, 255, 255, 0.1);
    border-radius: 3px;
  }

  #messagesContainer::-webkit-scrollbar-thumb {
    background: rgba(255, 255, 255, 0.3);
    border-radius: 3px;
  }

  #messagesContainer::-webkit-scrollbar-thumb:hover {
    background: rgba(255, 255, 255, 0.5);
  }

  /* For Firefox */
  #messagesContainer {
    scrollbar-width: thin;
    scrollbar-color: rgba(255, 255, 255, 0.3) rgba(255, 255, 255, 0.1);
  }
  
  /* Ensure proper height calculation on mobile */
  @media (max-height: 600px) {
    #messagesContainer {
      max-height: calc(100vh - 320px) !important;
    }
  }
`;

document.head.appendChild(style);
