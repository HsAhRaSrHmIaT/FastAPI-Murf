// document.addEventListener("DOMContentLoaded", () => {
//     const form = document.getElementById("ttsForm");
//     const btnText = document.getElementById("btnText");
//     const btnLoader = document.getElementById("btnLoader");
//     const audioPlayer = document.getElementById("audioPlayer");
//     const audioSource = document.getElementById("audioSource");
//     const userInput = document.getElementById("userInput");
//     const charCount = document.getElementById("charCount");

//     // Only add event listeners if elements exist (Text-to-Speech section might be commented out)
//     // if (userInput && charCount) {
//     //     // Character counter
//     //     userInput.addEventListener("input", () => {
//     //         const count = userInput.value.length;
//     //         charCount.textContent = `${count} character${
//     //             count !== 1 ? "s" : ""
//     //         }`;

//     //         // Change color based on length
//     //         if (count > 500) {
//     //             charCount.className =
//     //                 "absolute bottom-3 right-3 text-xs text-red-400";
//     //         } else if (count > 300) {
//     //             charCount.className =
//     //                 "absolute bottom-3 right-3 text-xs text-yellow-400";
//     //         } else {
//     //             charCount.className =
//     //                 "absolute bottom-3 right-3 text-xs text-gray-400";
//     //         }
//     //     });
//     // }

//     if (
//         form &&
//         btnText &&
//         btnLoader &&
//         audioPlayer &&
//         audioSource &&
//         userInput
//     ) {
//         form.addEventListener("submit", async function (e) {
//             e.preventDefault();

//             const inputText = userInput.value.trim();

//             if (!inputText) {
//                 showNotification("Please enter a message.", "error");
//                 return;
//             }

//             btnText.textContent = "Generating...";
//             btnLoader.classList.remove("hidden");

//             try {
//                 const response = await fetch("/generate-speech", {
//                     method: "POST",
//                     headers: {
//                         "Content-Type": "application/json",
//                     },
//                     body: JSON.stringify({
//                         text: inputText,
//                     }),
//                 });

//                 if (response.ok) {
//                     const result = await response.json();
//                     audioSource.src = result.audio_url;
//                     audioPlayer.load();
//                     audioPlayer.play();
//                     showNotification(
//                         "Speech generated successfully!",
//                         "success"
//                     );
//                 } else {
//                     const errorData = await response.json();
//                     showNotification(`Error: ${errorData.detail}`, "error");
//                 }
//             } catch (err) {
//                 showNotification(
//                     "Something went wrong! Please try again.",
//                     "error"
//                 );
//                 console.error(err);
//             } finally {
//                 btnText.textContent = "Generate Speech";
//                 btnLoader.classList.add("hidden");
//             }
//         });

//         // Notification system
//         // function showNotification(message, type) {
//         //     const notification = document.createElement("div");
//         //     notification.className = `fixed top-4 right-4 p-4 rounded-xl shadow-lg z-50 text-white font-medium max-w-sm transform transition-all duration-300 ${
//         //         type === "success"
//         //             ? "bg-green-500 border border-green-400"
//         //             : "bg-red-500 border border-red-400"
//         //     }`;
//         //     notification.textContent = message;

//         //     document.body.appendChild(notification);

//         //     // Animate in
//         //     setTimeout(() => {
//         //         notification.style.transform = "translateX(0)";
//         //         notification.style.opacity = "1";
//         //     }, 10);

//         //     // Remove after 3 seconds
//         //     setTimeout(() => {
//         //         notification.style.transform = "translateX(100%)";
//         //         notification.style.opacity = "0";
//         //         setTimeout(() => {
//         //             document.body.removeChild(notification);
//         //         }, 300);
//         //     }, 3000);
//         // }
//     } // Close the form conditional block
// });

if (navigator.mediaDevices) {
    const constraints = { audio: true };
    let chunks = [];
    let sessionId = null;
    let isAutoRecording = false;

    // Get or create session ID from URL params
    function getSessionId() {
        const urlParams = new URLSearchParams(window.location.search);
        let sessionId = urlParams.get("session");

        if (!sessionId) {
            sessionId =
                "session_" +
                Date.now() +
                "_" +
                Math.random().toString(36).substr(2, 9);
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
                    })
                    .catch((err) => {
                        console.error("Failed to clear chat history:", err);
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

                        updateProgressStep(
                            1,
                            `AI response generated (History: ${result.chat_history_length} messages)`,
                            "success"
                        );
                        addProgressStep("Playing AI response...");

                        if (aiAudioSource && aiAudioPlayer) {
                            aiAudioSource.src = result.audio_url;
                            aiAudioPlayer.load();

                            aiAudioPlayer.onloadeddata = () =>
                                console.log("AI speech loaded successfully");
                            aiAudioPlayer.onerror = (e) =>
                                console.error("AI speech error:", e);
                            aiAudioPlayer.oncanplay = () =>
                                console.log("AI speech can play");

                            aiAudioPlayer
                                .play()
                                .then(() => {
                                    console.log("AI speech playback started");
                                    updateProgressStep(
                                        2,
                                        "Playing AI response...",
                                        "success"
                                    );
                                })
                                .catch((e) => {
                                    console.error(
                                        "AI speech playback failed:",
                                        e
                                    );
                                    updateProgressStep(
                                        2,
                                        "Playback failed",
                                        "error"
                                    );
                                });
                        } else {
                            console.error("Audio elements not found");
                        }
                    } else {
                        const errorData = await chatResponse.json();
                        updateProgressStep(
                            1,
                            `Chat failed: ${errorData.detail}`,
                            "error"
                        );
                    }
                } catch (err) {
                    console.error("Chat error:", err);
                    updateProgressStep(
                        1,
                        "Chat failed: Network error",
                        "error"
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
        });
}
