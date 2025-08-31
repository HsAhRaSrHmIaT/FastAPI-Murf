function maskValue(value) {
    if (!value || value.length <= 4) {
        return value;
    }
    return "•".repeat(value.length);
}

function toggleVisibility(inputId) {
    const input = document.getElementById(inputId);
    const prefix = inputId.split("_")[0];
    const openEye = document.getElementById(`eye-open-${prefix}`);
    const closedEye = document.getElementById(`eye-closed-${prefix}`);

    if (input.type === "password") {
        // (unmask)
        if (input.dataset.masked === "true" && input.dataset.originalValue) {
            input.value = input.dataset.originalValue;
        }
        input.type = "text";
        if (openEye) openEye.classList.add("hidden");
        if (closedEye) closedEye.classList.remove("hidden");
    } else {
        // (mask)
        if (input.value.trim() !== "") {
            input.dataset.originalValue = input.value;
            input.value = maskValue(input.value);
            input.dataset.masked = "true";
        }
        input.type = "password";
        if (closedEye) closedEye.classList.add("hidden");
        if (openEye) openEye.classList.remove("hidden");
    }
}

document.addEventListener("DOMContentLoaded", function () {
    const form = document.getElementById("settingsForm");
    const saveButton = document.getElementById("saveButton");
    const messageDiv = document.getElementById("message");
    const inputs = document.querySelectorAll(
        'input[name="assemblyai_api_key"], input[name="google_api_key"], input[name="murf_api_key"]'
    );

    // Prefill from localStorage if available
    const inputIds = ["assemblyai_api_key", "google_api_key", "murf_api_key"];
    inputIds.forEach((id) => {
        const input = document.getElementById(id);
        const stored = localStorage.getItem(id);
        if (input && stored) {
            input.value = stored;
            input.dataset.originalValue = stored;
            input.value = maskValue(stored);
            input.dataset.masked = "true";
        } else if (input && input.value.trim()) {
            input.dataset.originalValue = input.value;
            input.value = maskValue(input.value);
            input.dataset.masked = "true";
        }
    });

    function checkInputs() {
        const anyFilled = Array.from(inputs).some((input) => {
            const valueToCheck =
                input.dataset.masked === "true" && input.dataset.originalValue
                    ? input.dataset.originalValue
                    : input.value;
            return valueToCheck.trim() !== "";
        });
        saveButton.disabled = !anyFilled;
    }

    inputs.forEach((input) => {
        input.addEventListener("input", function () {
            if (input.type === "text") {
                input.dataset.originalValue = input.value;
                input.dataset.masked = "false";
            }
            checkInputs();
        });

        // Handle focus events to unmask if needed
        input.addEventListener("focus", function () {
            if (
                input.dataset.masked === "true" &&
                input.dataset.originalValue &&
                input.type === "password"
            ) {
                // Don't unmask on focus for password fields, let the eye toggle handle it
                return;
            }
        });

        // Handle blur events to mask if it's a password field
        input.addEventListener("blur", function () {
            if (input.type === "password" && input.value.trim() !== "") {
                input.dataset.originalValue = input.value;
                input.value = maskValue(input.value);
                input.dataset.masked = "true";
            }
        });
    });

    // Initial check on page load
    checkInputs();

    // Handle form submission: save to localStorage only
    form.addEventListener("submit", function (event) {
        event.preventDefault();
        inputs.forEach((input) => {
            const originalValue = input.dataset.originalValue || input.value;
            if (originalValue.trim()) {
                localStorage.setItem(input.name, originalValue.trim());
            }
        });
        messageDiv.innerText = "API keys saved locally!";
        messageDiv.className = "text-green-400 text-center mt-4";
        setTimeout(() => {
            messageDiv.innerText = "";
            messageDiv.className = "";
        }, 3000);

        // After save, re-mask all password fields
        inputs.forEach((input) => {
            if (input.type === "password" && input.value.trim() !== "") {
                input.dataset.originalValue =
                    input.dataset.originalValue || input.value;
                input.value = maskValue(input.dataset.originalValue);
                input.dataset.masked = "true";
            }
        });
    });
});

async function fetchHealthStatus() {
    const headers = {};
    const assemblyaiKey = localStorage.getItem("assemblyai_api_key");
    const googleKey = localStorage.getItem("google_api_key");
    const murfKey = localStorage.getItem("murf_api_key");

    if (assemblyaiKey) headers["x-assemblyai-api-key"] = assemblyaiKey;
    if (googleKey) headers["x-google-api-key"] = googleKey;
    if (murfKey) headers["x-murf-api-key"] = murfKey;

    const res = await fetch("/health/", { headers });
    const data = await res.json();
    let html = `<p class="${
        data.status === "Healthy"
            ? "text-green-400"
            : data.status === "Degraded"
            ? "text-yellow-400"
            : "text-red-400"
    }"><strong>Status:</strong> ${data.status}</p>`;
    // if (data.missing_api_keys && data.missing_api_keys.length > 0) {
    //     html += `<strong>Missing API Keys:</strong> <ul>`;
    //     data.missing_api_keys.forEach((key) => {
    //         html += `<li>${key}</li>`;
    //     });
    //     html += `</ul>`;
    // }
    document.getElementById("health-status").innerHTML = html;
}

// Call this function when the page loads
window.addEventListener("DOMContentLoaded", fetchHealthStatus);
