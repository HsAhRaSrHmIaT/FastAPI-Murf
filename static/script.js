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

            record.onclick = () => {
                chunks = [];
                mediaRecorder.start();
                record.classList.add("opacity-50");
                initializeProgress("Recording...");
            };

            stop.onclick = () => {
                mediaRecorder.stop();
                record.classList.remove("opacity-50");
                updateProgressStep(0, "Recording stopped", "success");
            };

            reset.onclick = () => {
                chunks = [];
                audioSource.src = "";
                audioPlayer.load();
                aiAudioSource.src = "";
                aiAudioPlayer.load();
                record.classList.remove("opacity-50");
                clearProgress();
                clearTranscription();
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
                addProgressStep("Transcribing and generating response...");

                // updateUploadStatus(
                //     "Step 1/3: Transcribing and generating response...",
                //     "info"
                // );

                const formData = new FormData();
                formData.append("file", audioBlob, "question.webm");

                try {
                    // Send to LLM query endpoint
                    const llmResponse = await fetch("/llm/query", {
                        method: "POST",
                        body: formData,
                    });

                    if (llmResponse.ok) {
                        const result = await llmResponse.json();
                        console.log("LLM Query Result:", result);

                        updateProgressStep(
                            1,
                            "AI response generated",
                            "success"
                        );
                        addProgressStep(
                            "Generating speech from AI response..."
                        );
                        // updateUploadStatus(
                        //     "Step 2/3: LLM Generating speech from AI response...",
                        //     "success"
                        // );

                        const ttsResponse = await fetch("/generate-speech", {
                            method: "POST",
                            body: JSON.stringify({
                                text: result.response,
                            }),
                            headers: {
                                "Content-Type": "application/json",
                            },
                        });

                        if (!ttsResponse.ok) {
                            console.error(
                                "TTS generation failed:",
                                await ttsResponse.text()
                            );
                            updateProgressStep(
                                2,
                                "TTS generation failed",
                                "error"
                            );
                            return;
                        }

                        const ttsResult = await ttsResponse.json();
                        console.log("TTS Generation Result:", ttsResult);

                        updateProgressStep(
                            2,
                            "Generated speech from AI response",
                            "success"
                        );
                        // updateUploadStatus(
                        //     `Step 3/3: Generated speech from AI response...`,
                        //     "success"
                        // );

                        if (aiAudioSource && aiAudioPlayer) {
                            aiAudioSource.src = ttsResult.audio_url;
                            aiAudioPlayer.load();

                            // Add event listeners for debugging
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
                                })
                                .catch((e) => {
                                    console.error(
                                        "AI speech playback failed:",
                                        e
                                    );
                                });
                        } else {
                            console.error("Audio elements not found:", {
                                aiAudioSource: !!aiAudioSource,
                                aiAudioPlayer: !!aiAudioPlayer,
                            });
                        }
                    } else {
                        const errorData = await llmResponse.json();
                        updateProgressStep(
                            1,
                            `LLM Query failed: ${errorData.detail}`,
                            "error"
                        );
                    }
                } catch (err) {
                    console.error("Voice-to-voice chat error:", err);
                    updateProgressStep(
                        1,
                        "Voice-to-voice chat failed: Network error",
                        "error"
                    );
                }
            }

            // Function to display transcription
            // function displayTranscription(text) {
            //     const transcriptionContent = document.getElementById(
            //         "transcriptionContent"
            //     );

            //     if (transcriptionContent && text) {
            //         // Update the content in the existing container
            //         transcriptionContent.innerHTML = `
            //             <p class="text-white text-base leading-relaxed">"${text}"</p>
            //         `;

            //         // Auto-scroll to bottom if content overflows
            //         const container = document.getElementById(
            //             "transcriptionContainer"
            //         );
            //         if (container) {
            //             container.scrollTop = container.scrollHeight;
            //         }
            //     }
            // }

            // Function to clear transcription
            function clearTranscription() {
                const transcriptionContent = document.getElementById(
                    "transcriptionContent"
                );

                if (transcriptionContent) {
                    transcriptionContent.innerHTML = `
                        <div class="text-gray-400 text-sm text-center italic">
                            Record audio to see generated results here...
                        </div>
                    `;
                }
            }

            function initializeProgress(message) {
                progressSteps = [{ message, type: "info" }];
                renderProgress();
            }

            function addProgressStep(message, type = "info") {
                progressSteps.push({ message, type });
                renderProgress();
            }

            function updateProgressStep(index, message, type = "info") {
                if (index < 0 || index >= progressSteps.length) return;
                progressSteps[index] = { message, type };
                renderProgress();
            }

            function clearProgress() {
                progressSteps = [];
                const statusElement = document.getElementById("uploadStatus");
                if (statusElement) {
                    statusElement.classList.add("hidden");
                }
            }

            function renderProgress() {
                const statusElement = document.getElementById("uploadStatus");
                if (statusElement && progressSteps.length > 0) {
                    statusElement.classList.remove("hidden");
                    
                    const stepsHtml = progressSteps.map((step, index) => {
                        const emoji = step.type === "success" ? "✅" :step.type === "error" ? "❌" : "🔄";

                        const textClass = step.type === "success" ? "text-green-300" : step.type === "error" ? "text-red-300" : "text-blue-300";

                        return `
                            <div class="flex items-center mb-1">
                                <span class="mr-2">${emoji}</span>
                                <span class="${textClass}">${step.message}</span>
                            </div>
                        `;
                    }).join("");

                    statusElement.innerHTML = stepsHtml;
                    statusElement.className = `rounded-xl p-4 text-sm font-medium border backdrop-blur-sm bg-white/5 text-gray-300 border-white/10`;
                }
            }

            // Status update function
            // function updateUploadStatus(message, type) {
            //     let statusElement = document.getElementById("uploadStatus");
            //     if (statusElement) {
            //         if (message === "" && type === "") {
            //             statusElement.classList.add("hidden");
            //             return;
            //         }

            //         statusElement.classList.remove("hidden");
            //         statusElement.innerHTML = message;
            //         statusElement.className = `rounded-xl p-4 text-sm font-medium border backdrop-blur-sm ${getStatusClass(
            //             type
            //         )}`;
            //     }
            // }

            // function getStatusClass(type) {
            //     switch (type) {
            //         case "info":
            //             return "bg-blue-500/20 text-blue-300 border-blue-400/30";
            //         case "success":
            //             return "bg-green-500/20 text-green-300 border-green-400/30";
            //         case "error":
            //             return "bg-red-500/20 text-red-300 border-red-400/30";
            //         default:
            //             return "hidden";
            //     }
            // }
        })
        .catch((err) => {
            console.error("The following error occurred: " + err);
            initializeProgress("Error accessing microphone");
            updateProgressStep(
                0,
                "Microphone access failed: " + err.message,
                "error"
            );
        });
}
