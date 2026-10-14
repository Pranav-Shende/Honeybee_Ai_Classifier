const form = document.getElementById("videoForm");
const fileInput = document.getElementById("videoFile");
const confidence = document.getElementById("confidence");
const linePosition = document.getElementById("linePosition");
const button = document.getElementById("processButton");
const message = document.getElementById("message");
const progressArea = document.getElementById("progressArea");
const results = document.getElementById("results");

confidence.addEventListener("input", () => {
    document.getElementById("confidenceValue").textContent =
        Number(confidence.value).toFixed(2);
});

linePosition.addEventListener("input", () => {
    document.getElementById("lineValue").textContent = `${linePosition.value}%`;
});

async function checkModel() {
    const status = document.getElementById("modelStatus");
    try {
        const response = await fetch("/api/status");
        const data = await response.json();
        status.textContent = data.model_loaded ? `Model ready: ${data.model}` : "Model weights missing";
    } catch {
        status.textContent = "Backend unavailable";
    }
}

function addCell(row, value) {
    const cell = document.createElement("td");
    cell.textContent = value;
    row.appendChild(cell);
}

function fillCrossingTable(crossings) {
    const tbody = document.getElementById("crossingRows");
    tbody.replaceChildren();
    const classNames = new Set([
        ...Object.keys(crossings.IN || {}),
        ...Object.keys(crossings.OUT || {})
    ]);
    for (const name of classNames) {
        const row = document.createElement("tr");
        addCell(row, name);
        addCell(row, crossings.IN?.[name] ?? 0);
        addCell(row, crossings.OUT?.[name] ?? 0);
        tbody.appendChild(row);
    }
}

function getCurrentUserId(session) {
    return session?.user?.id || null;
}

async function saveAnalysis(data, fileName, session) {
    const client = window.supabaseClient;
    const userId = getCurrentUserId(session);
    if (!client || !userId) throw new Error("Your session is unavailable. Please sign in again.");

    const record = {
        user_id: userId,
        video_name: fileName,
        processed_frames: Number(data.processed_frames || 0),
        source_frames: Number(data.source_frames || 0),
        processing_seconds: Number(data.processing_seconds || 0),
        processing_fps: Number(data.processing_fps || 0),
        unique_tracks_seen: Number(data.unique_tracks_seen || 0),
        detection_totals: data.detection_totals_across_frames || {},
        unique_tracks_by_class: data.unique_tracks_by_class || {},
        crossings: data.crossings || {},
        result_url: data.result_url || null,
        note: data.note || null
    };

    const { error } = await client.from("video_analyses").insert(record);
    if (error) throw error;
}

function formatDate(value) {
    if (!value) return "—";
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? "—" : date.toLocaleString([], {
        year: "numeric", month: "short", day: "numeric",
        hour: "2-digit", minute: "2-digit"
    });
}

function numberValue(value) {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : 0;
}

function renderDistribution(records) {
    const container = document.getElementById("classDistribution");
    container.replaceChildren();
    const totals = { "Normal bees": 0, "Pollen bees": 0 };
    for (const record of records) {
        const classes = record.unique_tracks_by_class || {};
        for (const [name, count] of Object.entries(classes)) {
            totals[name] = (totals[name] || 0) + numberValue(count);
        }
    }
    const total = Object.values(totals).reduce((sum, count) => sum + count, 0);
    if (!total) {
        const empty = document.createElement("p");
        empty.className = "empty-analytics";
        empty.textContent = "No tracked bees recorded yet.";
        container.appendChild(empty);
        return;
    }

    for (const [name, count] of Object.entries(totals)) {
        const row = document.createElement("div");
        row.className = "distribution-row";
        const label = document.createElement("div");
        label.className = "distribution-label";
        const title = document.createElement("span");
        title.textContent = name;
        const value = document.createElement("strong");
        value.textContent = `${count.toLocaleString()} · ${Math.round(count / total * 100)}%`;
        label.append(title, value);
        const track = document.createElement("div");
        track.className = "distribution-track";
        const fill = document.createElement("div");
        fill.className = `distribution-fill${name === "Pollen bees" ? " pollen" : ""}`;
        fill.style.width = `${Math.max(0, count / total * 100)}%`;
        track.appendChild(fill);
        row.append(label, track);
        container.appendChild(row);
    }
}

function renderActivity(records) {
    const container = document.getElementById("activityChart");
    container.replaceChildren();
    const recent = [...records].slice(0, 7).reverse();
    if (!recent.length) {
        const empty = document.createElement("p");
        empty.className = "empty-analytics";
        empty.textContent = "Your saved analyses will appear here.";
        container.appendChild(empty);
        return;
    }
    const max = Math.max(1, ...recent.map(item => numberValue(item.unique_tracks_seen)));
    for (const record of recent) {
        const wrap = document.createElement("div");
        wrap.className = "activity-bar-wrap";
        const value = document.createElement("span");
        value.className = "activity-value";
        value.textContent = numberValue(record.unique_tracks_seen).toLocaleString();
        const bar = document.createElement("div");
        bar.className = "activity-bar";
        bar.style.height = `${Math.max(4, numberValue(record.unique_tracks_seen) / max * 84)}px`;
        bar.title = `${record.video_name}: ${record.unique_tracks_seen} tracks`;
        const label = document.createElement("span");
        label.className = "activity-label";
        label.textContent = new Date(record.created_at).toLocaleDateString([], { month: "short", day: "numeric" });
        label.title = record.video_name;
        wrap.append(value, bar, label);
        container.appendChild(wrap);
    }
}

function renderVideoComparison(records) {
    const container = document.getElementById("videoComparisonChart");
    container.replaceChildren();
    const recent = [...records].slice(0, 6).reverse();
    if (!recent.length) {
        const empty = document.createElement("p");
        empty.className = "empty-analytics";
        empty.textContent = "Saved video comparisons will appear here.";
        container.appendChild(empty);
        return;
    }

    const max = Math.max(1, ...recent.map(record => {
        const classes = record.unique_tracks_by_class || {};
        return numberValue(classes["Normal bees"]) + numberValue(classes["Pollen bees"]);
    }));

    for (const record of recent) {
        const classes = record.unique_tracks_by_class || {};
        const normal = numberValue(classes["Normal bees"]);
        const pollen = numberValue(classes["Pollen bees"]);
        const total = normal + pollen;
        const item = document.createElement("div");
        item.className = "comparison-item";
        const heading = document.createElement("div");
        heading.className = "comparison-heading";
        const name = document.createElement("span");
        name.className = "comparison-name";
        name.textContent = record.video_name || "Untitled video";
        name.title = name.textContent;
        const value = document.createElement("strong");
        value.textContent = `${total.toLocaleString()} tracks`;
        heading.append(name, value);
        const track = document.createElement("div");
        track.className = "comparison-track";
        const normalBar = document.createElement("div");
        normalBar.className = "comparison-normal";
        normalBar.style.width = `${normal / max * 100}%`;
        const pollenBar = document.createElement("div");
        pollenBar.className = "comparison-pollen";
        pollenBar.style.width = `${pollen / max * 100}%`;
        track.append(normalBar, pollenBar);
        const legend = document.createElement("div");
        legend.className = "comparison-legend";
        legend.textContent = `Normal ${normal.toLocaleString()}  ·  Pollen ${pollen.toLocaleString()}`;
        item.append(heading, track, legend);
        container.appendChild(item);
    }
}

function renderPerformance(records) {
    const container = document.getElementById("performanceChart");
    container.replaceChildren();
    const recent = records.slice(0, 6);
    if (!recent.length) {
        const empty = document.createElement("p");
        empty.className = "empty-analytics";
        empty.textContent = "Processing metrics will appear here.";
        container.appendChild(empty);
        return;
    }

    const averageSeconds = recent.reduce((sum, record) => sum + numberValue(record.processing_seconds), 0) / recent.length;
    const averageFps = recent.reduce((sum, record) => sum + numberValue(record.processing_fps), 0) / recent.length;
    const averageFrames = recent.reduce((sum, record) => sum + numberValue(record.processed_frames), 0) / recent.length;
    const summary = document.createElement("div");
    summary.className = "performance-summary";
    for (const [label, value] of [
        ["Avg. processing time", `${averageSeconds.toFixed(1)} s`],
        ["Avg. processing speed", `${averageFps.toFixed(1)} FPS`],
        ["Avg. frames processed", Math.round(averageFrames).toLocaleString()]
    ]) {
        const metric = document.createElement("div");
        metric.className = "performance-metric";
        const metricLabel = document.createElement("span");
        metricLabel.textContent = label;
        const metricValue = document.createElement("strong");
        metricValue.textContent = value;
        metric.append(metricLabel, metricValue);
        summary.appendChild(metric);
    }
    container.appendChild(summary);

    const maxSeconds = Math.max(1, ...recent.map(record => numberValue(record.processing_seconds)));
    const chartTitle = document.createElement("p");
    chartTitle.className = "performance-chart-label";
    chartTitle.textContent = "Processing time by video";
    container.appendChild(chartTitle);
    for (const record of [...recent].reverse()) {
        const row = document.createElement("div");
        row.className = "performance-row";
        const name = document.createElement("span");
        name.className = "performance-name";
        name.textContent = record.video_name || "Untitled video";
        name.title = name.textContent;
        const track = document.createElement("div");
        track.className = "performance-track";
        const bar = document.createElement("div");
        bar.className = "performance-fill";
        bar.style.width = `${numberValue(record.processing_seconds) / maxSeconds * 100}%`;
        track.appendChild(bar);
        const value = document.createElement("strong");
        value.textContent = `${numberValue(record.processing_seconds).toFixed(1)}s`;
        row.append(name, track, value);
        container.appendChild(row);
    }
}

function renderHistory(records) {
    const tbody = document.getElementById("historyRows");
    const search = (document.getElementById("historySearch").value || "").trim().toLowerCase();
    const filtered = records.filter(record => String(record.video_name || "").toLowerCase().includes(search));
    tbody.replaceChildren();
    if (!filtered.length) {
        const row = document.createElement("tr");
        const cell = document.createElement("td");
        cell.colSpan = 6;
        cell.className = "empty-analytics";
        cell.textContent = records.length ? "No matching video filenames." : "No saved analyses yet. Process a video to create your first record.";
        row.appendChild(cell);
        tbody.appendChild(row);
        return;
    }

    for (const record of filtered) {
        const row = document.createElement("tr");
        addCell(row, formatDate(record.created_at));
        const nameCell = document.createElement("td");
        const name = document.createElement("span");
        name.className = "history-file";
        name.textContent = record.video_name || "Untitled video";
        name.title = name.textContent;
        nameCell.appendChild(name);
        row.appendChild(nameCell);
        addCell(row, numberValue(record.unique_tracks_seen).toLocaleString());
        addCell(row, `${numberValue(record.processed_frames).toLocaleString()} / ${numberValue(record.source_frames).toLocaleString()}`);
        addCell(row, `${numberValue(record.processing_seconds).toFixed(1)} s`);
        const resultCell = document.createElement("td");
        if (record.result_url) {
            const link = document.createElement("a");
            link.className = "history-download";
            link.href = record.result_url;
            link.download = "";
            link.textContent = "Download";
            resultCell.appendChild(link);
        } else {
            resultCell.textContent = "Unavailable";
        }
        row.appendChild(resultCell);
        tbody.appendChild(row);
    }
}

let savedAnalyses = [];

function renderAnalytics(records) {
    savedAnalyses = records;
    const totalTracks = records.reduce((sum, item) => sum + numberValue(item.unique_tracks_seen), 0);
    const normal = records.reduce((sum, item) => sum + numberValue(item.unique_tracks_by_class?.["Normal bees"]), 0);
    const pollen = records.reduce((sum, item) => sum + numberValue(item.unique_tracks_by_class?.["Pollen bees"]), 0);
    document.getElementById("totalAnalyses").textContent = records.length.toLocaleString();
    document.getElementById("analyticsTotal").textContent = records.length.toLocaleString();
    document.getElementById("analyticsTracks").textContent = totalTracks.toLocaleString();
    document.getElementById("analyticsNormal").textContent = normal.toLocaleString();
    document.getElementById("analyticsPollen").textContent = pollen.toLocaleString();
    renderDistribution(records);
    renderActivity(records);
    renderVideoComparison(records);
    renderPerformance(records);
    renderHistory(records);
}

async function loadAnalytics() {
    const status = document.getElementById("analyticsMessage");
    status.textContent = "Loading your saved analytics...";
    try {
        await window.initializeSupabase();
        const { data: { session }, error: sessionError } = await window.supabaseClient.auth.getSession();
        if (sessionError) throw sessionError;
        if (!session) {
            window.location.replace("/login");
            return;
        }
        const { data, error } = await window.supabaseClient
            .from("video_analyses")
            .select("id, created_at, video_name, processed_frames, source_frames, processing_seconds, processing_fps, unique_tracks_seen, detection_totals, unique_tracks_by_class, crossings, result_url, note")
            .order("created_at", { ascending: false })
            .limit(100);
        if (error) throw error;
        renderAnalytics(data || []);
        status.textContent = data?.length
            ? `Showing ${data.length} most recent saved analyses.`
            : "No saved analyses yet. Your next completed video will appear here.";
    } catch (error) {
        console.error("Analytics load failed:", error);
        status.textContent = error.message?.includes("video_analyses")
            ? "Analytics table not found. Run the supplied SQL in your Supabase SQL Editor."
            : `Could not load analytics: ${error.message || "Unknown error"}`;
    }
}

document.getElementById("refreshAnalytics")?.addEventListener("click", loadAnalytics);
document.getElementById("historySearch")?.addEventListener("input", () => renderHistory(savedAnalyses));

form.addEventListener("submit", async event => {
    event.preventDefault();
    const file = fileInput.files[0];
    if (!file) {
        message.textContent = "Please select a video.";
        return;
    }

    const formData = new FormData();
    formData.append("video", file);
    formData.append("confidence", confidence.value);
    formData.append("line_percent", linePosition.value);

    button.disabled = true;
    progressArea.hidden = false;
    results.hidden = true;
    message.textContent = "";
    document.getElementById("statusMessage").textContent =
        "Uploading and processing video. Longer videos may take some time.";

    try {
        await window.initializeSupabase();
        const { data: { session }, error: sessionError } = await window.supabaseClient.auth.getSession();
        if (sessionError) throw sessionError;
        if (!session) {
            window.location.replace("/login");
            return;
        }

        const response = await fetch("/api/process-video", {
            method: "POST",
            headers: { Authorization: `Bearer ${session.access_token}` },
            body: formData
        });
        const data = await response.json();

        if (!response.ok) {
            if (response.status === 401) {
                await window.supabaseClient.auth.signOut();
                window.location.replace("/login");
                return;
            }
            throw new Error(data.error || "Video processing failed.");
        }

        document.getElementById("downloadResult").href = data.result_url;
        document.getElementById("uniqueTracks").textContent = data.unique_tracks_seen ?? 0;
        document.getElementById("inCount").textContent =
            Object.values(data.crossings?.IN || {}).reduce((a, b) => a + b, 0);
        document.getElementById("outCount").textContent =
            Object.values(data.crossings?.OUT || {}).reduce((a, b) => a + b, 0);

        const classCounts = document.getElementById("classCounts");
        classCounts.replaceChildren();
        for (const [name, count] of Object.entries(data.unique_tracks_by_class || {})) {
            const item = document.createElement("p");
            item.textContent = `${name}: ${count}`;
            classCounts.appendChild(item);
        }
        fillCrossingTable(data.crossings || { IN: {}, OUT: {} });
        document.getElementById("analysisNote").textContent =
            `${data.note || ""} Frames processed: ${data.processed_frames ?? 0}.`;
        results.hidden = false;
        message.textContent = "Video processing completed.";

        try {
            await saveAnalysis(data, file.name, session);
            message.textContent = "Video processing completed and analytics saved.";
            await loadAnalytics();
        } catch (saveError) {
            console.error("Could not save analysis:", saveError);
            message.textContent = `Video processed successfully, but analytics could not be saved: ${saveError.message || "check Supabase table permissions"}`;
        }
    } catch (error) {
        message.textContent = error.message || "Video processing failed.";
    } finally {
        progressArea.hidden = true;
        button.disabled = false;
    }
});

checkModel();
loadAnalytics();
