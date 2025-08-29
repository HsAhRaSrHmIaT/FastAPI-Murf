document.addEventListener("DOMContentLoaded", function () {
    const form = document.getElementById("settingsForm");
    const saveButton = document.getElementById("saveButton");
    const messageDiv = document.getElementById("message");
    const inputs = document.querySelectorAll(
        'input[name="assemblyai_api_key"], input[name="google_api_key"], input[name="murf_api_key"], input[name="ws_murf_api_url"]'
    );

    // Function to check if any input has a value and toggle button state
    function checkInputs() {
        const anyFilled = Array.from(inputs).some(
            (input) => input.value.trim() !== ""
        );
        saveButton.disabled = !anyFilled;
    }

    // Add event listeners to inputs for real-time checking
    inputs.forEach((input) => input.addEventListener("input", checkInputs));

    // Initial check on page load
    checkInputs();

    // Handle form submission asynchronously
    form.addEventListener("submit", async function (event) {
        event.preventDefault(); // Prevent default form submission and redirect

        const formData = new FormData(form);
        try {
            const response = await fetch("/update-keys", {
                method: "POST",
                body: formData,
            });

            if (response.ok) {
                const result = await response.json();
                messageDiv.innerText = result.message;
                messageDiv.className = "text-green-400 text-center mt-4"; // Style success message
            } else {
                messageDiv.innerText = "Error saving keys.";
                messageDiv.className = "text-red-400 text-center mt-4"; // Style error message
            }
        } catch (error) {
            messageDiv.innerText = "Network error.";
            messageDiv.className = "text-red-400 text-center mt-4";
        }
    });
});
