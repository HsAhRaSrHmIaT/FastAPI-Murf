document.addEventListener("DOMContentLoaded", () => {
    const form = document.getElementById("ttsForm");
    const btnText = document.getElementById("btnText");
    const btnLoader = document.getElementById("btnLoader");
    const audioPlayer = document.getElementById("audioPlayer");
    const audioSource = document.getElementById("audioSource");
    const userInput = document.getElementById("userInput");
    const charCount = document.getElementById("charCount");

    // Character counter
    userInput.addEventListener("input", () => {
        const count = userInput.value.length;
        charCount.textContent = `${count} character${count !== 1 ? "s" : ""}`;

        // Change color based on length
        if (count > 500) {
            charCount.className =
                "absolute bottom-3 right-3 text-xs text-red-400";
        } else if (count > 300) {
            charCount.className =
                "absolute bottom-3 right-3 text-xs text-yellow-400";
        } else {
            charCount.className =
                "absolute bottom-3 right-3 text-xs text-gray-400";
        }
    });

    form.addEventListener("submit", async function (e) {
        e.preventDefault();

        const inputText = userInput.value.trim();

        if (!inputText) {
            showNotification("Please enter a message.", "error");
            return;
        }

        btnText.textContent = "Generating...";
        btnLoader.classList.remove("hidden");

        try {
            const response = await fetch("/generate-speech", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({
                    text: inputText,
                }),
            });

            if (response.ok) {
                const result = await response.json();
                audioSource.src = result.audio_url;
                audioPlayer.load();
                audioPlayer.play();
                showNotification("Speech generated successfully!", "success");
            } else {
                const errorData = await response.json();
                showNotification(`Error: ${errorData.detail}`, "error");
            }
        } catch (err) {
            showNotification(
                "Something went wrong! Please try again.",
                "error"
            );
            console.error(err);
        } finally {
            btnText.textContent = "Generate Speech";
            btnLoader.classList.add("hidden");
        }
    });

    // Notification system
    function showNotification(message, type) {
        const notification = document.createElement("div");
        notification.className = `fixed top-4 right-4 p-4 rounded-xl shadow-lg z-50 text-white font-medium max-w-sm transform transition-all duration-300 ${
            type === "success"
                ? "bg-green-500 border border-green-400"
                : "bg-red-500 border border-red-400"
        }`;
        notification.textContent = message;

        document.body.appendChild(notification);

        // Animate in
        setTimeout(() => {
            notification.style.transform = "translateX(0)";
            notification.style.opacity = "1";
        }, 10);

        // Remove after 3 seconds
        setTimeout(() => {
            notification.style.transform = "translateX(100%)";
            notification.style.opacity = "0";
            setTimeout(() => {
                document.body.removeChild(notification);
            }, 300);
        }, 3000);
    }
});

if (navigator.mediaDevices) {
    const constraints = { audio: true };
    let chunks = [];

    navigator.mediaDevices
        .getUserMedia(constraints)
        .then((stream) => {
            const mediaRecorder = new MediaRecorder(stream);
            const record = document.getElementById("record");
            const stop = document.getElementById("stop");
            const reset = document.getElementById("reset");
            const audioPlayer = document.getElementById("recordedAudio");
            const audioSource = document.getElementById("recordedAudioSource");

            record.onclick = () => {
                chunks = [];
                mediaRecorder.start();
                record.classList.add("opacity-50");
                updateUploadStatus("Recording...", "info");
            };

            stop.onclick = () => {
                mediaRecorder.stop();
                record.classList.remove("opacity-50");
                updateUploadStatus("Processing recording...", "info");
            };

            reset.onclick = () => {
                chunks = [];
                audioSource.src = "";
                audioPlayer.load();
                record.classList.remove("opacity-50");
                updateUploadStatus("", "");

                // Clear transcription using the new function
                clearTranscription();
            };

            mediaRecorder.ondataavailable = (e) => {
                chunks.push(e.data);
            };

            mediaRecorder.onstop = async () => {
                const blob = new Blob(chunks, {
                    type: "audio/ogg; codecs=opus",
                });

                await uploadAudio(blob);
            };

            async function uploadAudio(audioBlob) {
                updateUploadStatus(
                    "Uploading and transcribing audio...",
                    "info"
                );

                const formData = new FormData();
                formData.append("file", audioBlob, "recording.ogg");

                try {
                    // Send to transcription endpoint instead of upload
                    const response = await fetch("/transcribe-file", {
                        method: "POST",
                        body: formData,
                    });

                    if (response.ok) {
                        const result = await response.json();
                        updateUploadStatus(
                            `<b>Transcription successful!</b><br>Duration: ${
                                result.audio_duration - 1 || "N/A"
                            }s<br>Confidence: ${
                                result.confidence + "%" || "N/A"
                            }`,
                            "success"
                        );

                        // Display transcription in a dedicated area
                        displayTranscription(result.transcription);

                        // Play the local recording
                        const audioURL = URL.createObjectURL(audioBlob);
                        audioSource.src = audioURL;
                        audioPlayer.load();
                        audioPlayer.play();
                    } else {
                        const errorData = await response.json();
                        updateUploadStatus(
                            `Transcription failed: ${errorData.detail}`,
                            "error"
                        );

                        // Fallback: play local recording
                        const audioURL = URL.createObjectURL(audioBlob);
                        audioSource.src = audioURL;
                        audioPlayer.load();
                        audioPlayer.play();
                    }
                } catch (err) {
                    console.error("Transcription error:", err);
                    updateUploadStatus(
                        "Transcription failed: Network error",
                        "error"
                    );

                    // Fallback: play local recording
                    const audioURL = URL.createObjectURL(audioBlob);
                    audioSource.src = audioURL;
                    audioPlayer.load();
                    audioPlayer.play();
                }
            }

            // Function to display transcription
            function displayTranscription(text) {
                const transcriptionContent = document.getElementById(
                    "transcriptionContent"
                );

                if (transcriptionContent && text) {
                    // Update the content in the existing container
                    transcriptionContent.innerHTML = `
                        <p class="text-white text-base leading-relaxed">"${text}"</p>
                    `;

                    // Auto-scroll to bottom if content overflows
                    const container = document.getElementById(
                        "transcriptionContainer"
                    );
                    if (container) {
                        container.scrollTop = container.scrollHeight;
                    }
                }
            }

            // Function to clear transcription
            function clearTranscription() {
                const transcriptionContent = document.getElementById(
                    "transcriptionContent"
                );

                if (transcriptionContent) {
                    transcriptionContent.innerHTML = `
                        <div class="text-gray-400 text-sm text-center italic">
                            Record audio to see transcription results here...
                        </div>
                    `;
                }
            }

            // Status update function
            function updateUploadStatus(message, type) {
                let statusElement = document.getElementById("uploadStatus");
                if (statusElement) {
                    if (message === "" && type === "") {
                        statusElement.classList.add("hidden");
                        return;
                    }

                    statusElement.classList.remove("hidden");
                    statusElement.innerHTML = message;
                    statusElement.className = `rounded-xl p-4 text-sm font-medium border backdrop-blur-sm ${getStatusClass(
                        type
                    )}`;
                }
            }

            function getStatusClass(type) {
                switch (type) {
                    case "info":
                        return "bg-blue-500/20 text-blue-300 border-blue-400/30";
                    case "success":
                        return "bg-green-500/20 text-green-300 border-green-400/30";
                    case "error":
                        return "bg-red-500/20 text-red-300 border-red-400/30";
                    default:
                        return "hidden";
                }
            }
        })
        .catch((err) => {
            console.error("The following error occurred: " + err);
            updateUploadStatus("Error accessing microphone", "error");
        });
}
