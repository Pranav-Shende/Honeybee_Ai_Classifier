
const form = document.getElementById("uploadForm");
const fileInput = document.getElementById("imageFile");
const confidenceInput = document.getElementById("confidence");
const confidenceValue = document.getElementById("confidenceValue");
const button = document.getElementById("analyzeButton");
const message = document.getElementById("message");
const results = document.getElementById("results");

confidenceInput.addEventListener("input", () => {
    confidenceValue.textContent = Number(confidenceInput.value).toFixed(2);
});

async function checkModelStatus() {
    const status = document.getElementById("modelStatus");

    try {
        const response = await fetch("/api/status");
        const data = await response.json();

        status.textContent = data.model_loaded
            ? `Model ready: ${data.model}`
            : "Model weights missing";
    } catch {
        status.textContent = "Backend unavailable";
    }
}

function classCount(counts, target) {
    const key = Object.keys(counts).find(
        name => name.toLowerCase().replaceAll(" ", "_") === target
    );

    return key ? counts[key] : 0;
}

form.addEventListener("submit", async event => {
    event.preventDefault();

    const file = fileInput.files[0];

    if (!file) {
        message.textContent = "Please select an image.";
        return;
    }

    const formData = new FormData();
    formData.append("file", file);
    formData.append("confidence", confidenceInput.value);

    button.disabled = true;
    button.textContent = "Analyzing...";
    message.textContent = "Running bee detection...";
    results.hidden = true;

    try {
        const response = await fetch("/api/detect-image", {
            method: "POST",
            body: formData
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || "Detection failed.");
        }

        document.getElementById("totalCount").textContent =
            data.total_bees_detected;

        document.getElementById("normalCount").textContent =
            classCount(data.class_counts, "normal_bee") +
            classCount(data.class_counts, "normal_bees");

        document.getElementById("pollenCount").textContent =
            classCount(data.class_counts, "pollen_carrying_bee") +
            classCount(data.class_counts, "pollen_bees") +
            classCount(data.class_counts, "pollen_carrying_bees");

        const imageUrl = data.result_url + "?t=" + Date.now();

        document.getElementById("annotatedImage").src = imageUrl;
        document.getElementById("downloadImage").href = data.result_url;

        const rows = document.getElementById("detectionRows");
        rows.replaceChildren();

        for (const detection of data.detections) {
            const row = document.createElement("tr");

            for (const value of [
                detection.class,
                `${(detection.confidence * 100).toFixed(1)}%`,
                detection.box.map(n => Math.round(n)).join(", ")
            ]) {
                const cell = document.createElement("td");
                cell.textContent = value;
                row.appendChild(cell);
            }

            rows.appendChild(row);
        }

        results.hidden = false;
        message.textContent = "Analysis complete.";
    } catch (error) {
        message.textContent = error.message;
    } finally {
        button.disabled = false;
        button.textContent = "Analyze image";
    }
});

checkModelStatus();
