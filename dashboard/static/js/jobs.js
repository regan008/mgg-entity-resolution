/**
 * Polls /api/jobs/<job_id>/log and renders into a log panel element.
 * Usage: pollJob(jobId, logElementId, onDone)
 */
function pollJob(jobId, logElementId, onDone) {
    const panel = document.getElementById(logElementId);
    let since = 0;

    function tick() {
        fetch(`/api/jobs/${jobId}/log?since=${since}`)
            .then((r) => r.json())
            .then((data) => {
                if (!data || data.error) return;
                for (const line of data.lines) {
                    const div = document.createElement("div");
                    let cls = "log-line-info";
                    if (line.includes("WARN")) cls = "log-line-warn";
                    if (line.includes("ERROR") || line.includes("Traceback")) cls = "log-line-error";
                    div.className = cls;
                    div.textContent = line;
                    panel.appendChild(div);
                }
                since = data.total_lines;
                panel.scrollTop = panel.scrollHeight;

                if (data.status === "running") {
                    setTimeout(tick, 1500);
                } else if (typeof onDone === "function") {
                    onDone(data);
                }
            })
            .catch(() => setTimeout(tick, 3000));
    }
    tick();
}

function runStage(state, scriptKey, flags, logElementId, onDone) {
    fetch(`/api/state/${state}/run`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ script: scriptKey, flags: flags || [] }),
    })
        .then((r) => r.json())
        .then((data) => {
            if (data.error) {
                alert(data.error);
                return;
            }
            pollJob(data.job_id, logElementId, onDone);
        });
}
