console.log("Script loaded - initializing voice recording functionality");

// Check if all required HTML elements exist
function checkRequiredElements() {
    const requiredElements = [
        "record",
        "stop",
        "reset",
        "audioPlayer",
        "audioSource",
        "aiAudioPlayer",
        "aiAudioSource",
        "uploadStatus",
        "sessionId",
    ];

    const missing = [];
    for (const id of requiredElements) {
        const element = document.getElementById(id);
        if (!element) {
            missing.push(id);
        }
    }

    if (missing.length > 0) {
        console.error("Missing required HTML elements:", missing);
        return false;
    }

    console.log("All required HTML elements found");
    return true;
}

if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
    const constraints = { audio: true };
    let chunks = [];
    let sessionId = null;
    let isAutoRecording = false;

    function fallbackTextToSpeech(text) {
        return new Promise((resolve, reject) => {
            if ("speechSynthesis" in window) {
                const utterance = new SpeechSynthesisUtterance(text);
                utterance.lang = "en-IN";
                utterance.rate = 0.9;
                utterance.pitch = 1;

                const voices = speechSynthesis.getVoices();
                const selectedVoice = voices.find(
                    (voice) =>
                        voice.name.includes("Arohi") ||
                        voice.name.includes("Priya") ||
                        voice.name.includes("Isha") ||
                        voice.name.includes("Alia")
                );
                if (selectedVoice) {
                    utterance.voice = selectedVoice;
                }

                utterance.onend = () => resolve();
                utterance.onerror = (e) => reject(e);

                speechSynthesis.speak(utterance);
            } else {
                reject(new Error("Speech synthesis not supported"));
            }
        });
    }

    function showError(message, details = null, duration = 5000) {
        const errorContainer = document.getElementById("uploadStatus");
        if (errorContainer) {
            errorContainer.classList.remove("hidden");
            errorContainer.className =
                "rounded-xl p-4 text-sm font-medium border backdrop-blur-sm bg-red-500/10 border-red-400/20 text-red-300";

            let errorHtml = `<div class="flex items-center gap-2">
                <div class="w-2 h-2 bg-red-400 rounded-full"></div>
                <strong>Error: ${message}</strong>
            </div>`;

            if (details) {
                errorHtml += `<div class="text-xs opacity-80 ml-4">${details}</div>`;
            }
            errorContainer.innerHTML = errorHtml;

            // Auto-hide after duration
            setTimeout(() => {
                if (errorContainer.innerHTML.includes("Error:")) {
                    errorContainer.classList.add("hidden");
                }
            }, duration);
        }
    }

    function showSuccess(message, details = null) {
        const statusContainer = document.getElementById("uploadStatus");
        if (statusContainer) {
            statusContainer.classList.remove("hidden");
            statusContainer.className =
                "rounded-xl p-4 text-sm font-medium border backdrop-blur-sm bg-green-500/10 border-green-400/20 text-green-300";

            let successHtml = `
            <div class="flex items-center gap-2">
                <div class="w-2 h-2 bg-green-400 rounded-full"></div>
                <strong>Success: ${message}</strong>
            </div>`;
            if (details) {
                successHtml += `<div class="text-xs opacity-80 ml-4">${details}</div>`;
            }
            statusContainer.innerHTML = successHtml;
        }
    }

    // Get or create session ID from URL params
    function getSessionId() {
        const urlParams = new URLSearchParams(window.location.search);
        let sessionId = urlParams.get("session");

        if (!sessionId) {
            sessionId =
                "session_" +
                Date.now() +
                "_" +
                Math.random().toString(36).substring(2, 11);
            urlParams.set("session", sessionId);
            window.history.replaceState(
                {},
                "",
                `${window.location.pathname}?${urlParams}`
            );
        }

        return sessionId;
    }

    sessionId = getSessionId();

    navigator.mediaDevices
        .getUserMedia(constraints)
        .then((stream) => {
            const mediaRecorder = new MediaRecorder(stream);
            const record = document.getElementById("record");
            const stop = document.getElementById("stop");
            const reset = document.getElementById("reset");
            const audioPlayer = document.getElementById("audioPlayer");
            const audioSource = document.getElementById("audioSource");
            const aiAudioPlayer = document.getElementById("aiAudioPlayer");
            const aiAudioSource = document.getElementById("aiAudioSource");

            let progressSteps = [];

            // Auto-start recording after AI response ends
            aiAudioPlayer.addEventListener("ended", () => {
                if (isAutoRecording) {
                    setTimeout(() => {
                        startRecording();
                    }, 1000); // Wait 1 second before auto-recording
                }
            });

            function startRecording() {
                chunks = [];
                mediaRecorder.start();
                record.classList.add("opacity-50");
                initializeProgress("Recording...");
            }

            record.onclick = () => {
                isAutoRecording = true; // Enable auto-recording for subsequent interactions
                startRecording();
            };

            stop.onclick = () => {
                mediaRecorder.stop();
                record.classList.remove("opacity-50");
                updateProgressStep(0, "Recording stopped", "success");
            };

            reset.onclick = () => {
                isAutoRecording = false; // Disable auto-recording
                chunks = [];
                audioSource.src = "";
                audioPlayer.load();
                aiAudioSource.src = "";
                aiAudioPlayer.load();
                record.classList.remove("opacity-50");
                clearProgress();

                // Clear chat history on server
                fetch(`/agent/chat/${sessionId}`, {
                    method: "DELETE",
                })
                    .then(() => {
                        console.log("Chat history cleared");
                        showSuccess("Session reset successfully");
                    })
                    .catch((err) => {
                        console.error("Failed to clear chat history:", err);
                        showError(
                            "Failed to reset session",
                            "Session may be unavailable"
                        );
                    });
            };

            mediaRecorder.ondataavailable = (e) => {
                chunks.push(e.data);
            };

            mediaRecorder.onstop = async () => {
                const blob = new Blob(chunks, {
                    type: "audio/ogg; codecs=opus",
                });

                const audioURL = URL.createObjectURL(blob);
                if (audioSource && audioPlayer) {
                    audioSource.src = audioURL;
                    audioPlayer.load();
                    audioPlayer.play();
                }

                await uploadAudio(blob);
            };

            async function uploadAudio(audioBlob) {
                addProgressStep("Processing with chat history...");

                const formData = new FormData();
                formData.append("file", audioBlob, "question.webm");

                try {
                    // Send to new chat endpoint with session ID
                    const chatResponse = await fetch(
                        `/agent/chat/${sessionId}`,
                        {
                            method: "POST",
                            body: formData,
                        }
                    );

                    if (chatResponse.ok) {
                        const result = await chatResponse.json();
                        console.log("Chat Result:", result);

                        const errors = result.errors || {};
                        let hasErrors = false;
                        let errorDetails = [];

                        if (errors.transcription_error) {
                            hasErrors = true;
                            errorDetails.push(
                                `Speech recognition: ${errors.transcription_error}`
                            );
                        }
                        if (errors.llm_error) {
                            hasErrors = true;
                            errorDetails.push(
                                `AI processing: ${errors.llm_error}`
                            );
                        }
                        if (errors.tts_error) {
                            hasErrors = true;
                            errorDetails.push(
                                `Voice synthesis: ${errors.tts_error}`
                            );
                        }

                        if (hasErrors) {
                            updateProgressStep(
                                1,
                                `AI response generated with issues (History: ${result.chat_history_length} messages)`,
                                "warning"
                            );
                            showError(
                                "Some services experienced issues",
                                errorDetails.join("; "),
                                7000
                            );
                        } else {
                            updateProgressStep(
                                1,
                                `AI response generated (History: ${result.chat_history_length} messages)`,
                                "success"
                            );
                        }

                        addProgressStep("Playing AI response...");

                        if (
                            result.audio_url &&
                            aiAudioSource &&
                            aiAudioPlayer
                        ) {
                            aiAudioSource.src = result.audio_url;
                            aiAudioPlayer.load();

                            aiAudioPlayer.onloadeddata = () =>
                                console.log("AI speech loaded successfully");
                            aiAudioPlayer.onerror = async (e) => {
                                console.error(
                                    "AI speech error: falling back to browser TTS: ",
                                    e
                                );
                                await handleFallbackTTS(
                                    result.assistant_response
                                );
                            };

                            try {
                                await aiAudioPlayer.play();
                                console.log("AI speech playback started");
                                updateProgressStep(
                                    2,
                                    "Playing AI response...",
                                    "success"
                                );
                            } catch (playError) {
                                console.error(
                                    "AI speech playback failed:",
                                    playError
                                );
                                await handleFallbackTTS(
                                    result.assistant_response
                                );
                            }
                        } else if (result.assistant_response) {
                            console.log(
                                "No server audio available, using browser TTS"
                            );
                            await handleFallbackTTS(result.assistant_response);
                        } else {
                            updateProgressStep(
                                2,
                                "No AI response available",
                                "error"
                            );
                            showError(
                                "No AI response available",
                                "error",
                                "Please try again!"
                            );
                        }
                    } else {
                        const errorData = await chatResponse
                            .json()
                            .catch(() => ({ detail: "Unknown error" }));
                        updateProgressStep(
                            1,
                            `Chat failed: ${errorData.detail}`,
                            "error"
                        );
                        showError("Server error", errorData.detail);
                        await handleFallbackTTS(
                            "I'm having trouble connecting to the server."
                        );
                    }
                } catch (err) {
                    console.error("Chat error:", err);

                    let errorMessage = "Network error";
                    let errorDetails = "Please check your connection";

                    if (err.name === "AbortError") {
                        errorMessage = "Request timeout";
                        errorDetails = "The request took too long to complete";
                    } else if (err.message.includes("Failed to fetch")) {
                        errorMessage = "Connection failed";
                        errorDetails = "Unable to reach the server";
                    }

                    updateProgressStep(
                        1,
                        `Chat failed: ${errorMessage}`,
                        "error"
                    );
                    showError(errorMessage, errorDetails);

                    await handleFallbackTTS(
                        "I'm having trouble connecting to the server."
                    );
                }
            }

            async function handleFallbackTTS(text) {
                try {
                    addProgressStep("Using fallback voice synthesis");
                    await fallbackTextToSpeech(text);
                    updateProgressStep(
                        2,
                        "Fallback voice synthesis completed",
                        "success"
                    );
                } catch (error) {
                    console.error("Fallback TTS error:", error);
                    updateProgressStep(
                        2,
                        "Fallback voice synthesis failed",
                        "error"
                    );
                    showError(
                        "Audio playback failed",
                        "Voice synthesis is not available"
                    );
                }
            }

            // Progress tracking functions
            function initializeProgress(initialStep) {
                progressSteps = [initialStep];
                updateProgressDisplay();
            }

            function addProgressStep(stepText) {
                progressSteps.push(stepText);
                updateProgressDisplay();
            }

            function updateProgressStep(stepIndex, newText, status = "info") {
                if (stepIndex < progressSteps.length) {
                    progressSteps[stepIndex] = newText;
                    updateProgressDisplay(status);
                }
            }

            function updateProgressDisplay(status = "info") {
                const uploadStatus = document.getElementById("uploadStatus");
                if (uploadStatus) {
                    uploadStatus.classList.remove("hidden");

                    let statusClass =
                        "bg-blue-500/10 border-blue-400/20 text-blue-300";
                    if (status === "success") {
                        statusClass =
                            "bg-green-500/10 border-green-400/20 text-green-300";
                    } else if (status === "error") {
                        statusClass =
                            "bg-red-500/10 border-red-400/20 text-red-300";
                    } else if (status === "warning") {
                        statusClass =
                            "bg-yellow-500/10 border-yellow-400/20 text-yellow-300";
                    }

                    uploadStatus.className = `rounded-xl p-4 text-sm font-medium border backdrop-blur-sm ${statusClass}`;
                    uploadStatus.innerHTML = progressSteps
                        .map(
                            (step, index) =>
                                `<div class="flex items-center gap-2">
                            <div class="w-2 h-2 bg-current rounded-full opacity-60"></div>
                            ${step}
                        </div>`
                        )
                        .join("");
                }
            }

            function clearProgress() {
                const uploadStatus = document.getElementById("uploadStatus");
                if (uploadStatus) {
                    uploadStatus.classList.add("hidden");
                }
                progressSteps = [];
            }
        })
        .catch((err) => {
            console.error("Error accessing microphone:", err);
            showError(
                "Microphone access denied",
                "Please allow microphone access and refresh the page to use voice recording.",
                10000
            );

            // Disable recording buttons
            const record = document.getElementById("record");
            const stop = document.getElementById("stop");
            const reset = document.getElementById("reset");

            if (record) {
                record.disabled = true;
                record.classList.add("opacity-50", "cursor-not-allowed");
                record.onclick = () =>
                    showError(
                        "Microphone access required",
                        "Please refresh and allow microphone access"
                    );
            }
            if (stop) {
                stop.disabled = true;
                stop.classList.add("opacity-50", "cursor-not-allowed");
            }
            if (reset) {
                reset.disabled = true;
                reset.classList.add("opacity-50", "cursor-not-allowed");
            }
        });
} else {
    console.error("MediaDevices not supported");
    showError(
        "Browser not supported",
        "Your browser doesn't support audio recording. Please use Chrome, Firefox, or Safari.",
        10000
    );
}

document.addEventListener("DOMContentLoaded", () => {
    console.log("DOM loaded - checking browser compatibility and elements");

    // Check if all required elements exist
    if (!checkRequiredElements()) {
        showError(
            "Page setup error",
            "Some required page elements are missing. Please refresh the page.",
            10000
        );
        return;
    }

    const missingFeatures = [];

    if (!navigator.mediaDevices) {
        missingFeatures.push("Media Devices API");
    }
    if (!window.MediaRecorder) {
        missingFeatures.push("Media recording");
    }
    if (!window.speechSynthesis) {
        console.warn("Speech synthesis not supported in this browser.");
    }

    if (missingFeatures.length > 0) {
        showError(
            "Browser compatibility issues",
            `Missing features: ${missingFeatures.join(
                ", "
            )}. Please use a different browser.`,
            10000
        );
    }

    const urlParams = new URLSearchParams(window.location.search);
    const sessionId = urlParams.get("session") || "No session ID";
    const sessionElement = document.getElementById("sessionId");
    if (sessionElement) {
        sessionElement.textContent = `Session ID: ${sessionId}`;
    }

    // Test server health on page load
    testServerHealth();
});

// Function to test server health
function testServerHealth() {
    fetch("/health")
        .then((response) => response.json())
        .then((data) => {
            console.log("Server health:", data);
            if (data.status === "degraded") {
                showError(
                    "Server status: degraded",
                    `Missing API keys: ${data.missing_api_keys.join(
                        ", "
                    )}. Some features may not work properly.`,
                    8000
                );
            } else {
                console.log("Server is healthy");
            }
        })
        .catch((error) => {
            console.error("Failed to check server health:", error);
            showError(
                "Server connection issue",
                "Cannot connect to the server. Please check if the server is running.",
                10000
            );
        });
}
