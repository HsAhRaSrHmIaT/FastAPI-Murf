document.addEventListener("DOMContentLoaded", () => {
    const form = document.getElementById("ttsForm");
    const btnText = document.getElementById("btnText");
    const btnLoader = document.getElementById("btnLoader");
    const audioPlayer = document.getElementById("audioPlayer");
    const audioSource = document.getElementById("audioSource");

    form.addEventListener("submit", async function (e) {
        e.preventDefault();

        const userInput = document.getElementById("userInput").value;

        if (!userInput) {
            alert("Please enter a message.");
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
                    text: userInput,
                }),
            });

            if (response.ok) {
                const result = await response.json();
                audioSource.src = result.audio_url;
                audioPlayer.load();
                audioPlayer.play();
            } else {
                const errorData = await response.json();
                alert("Error: " + errorData.detail);
            }
        } catch (err) {
            alert("Something went wrong!");
            console.error(err);
        } finally {
            btnText.textContent = "Generate Speech";
            btnLoader.classList.add("hidden");
        }
    });
});
