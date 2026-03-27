/* ══════════════════════════════════════════════════════════════
   Vertex — App Logic (Kinetic Workspace edition)
   Slide-in panels, command generators, JSON viewer, history
   ══════════════════════════════════════════════════════════════ */

// ══════════════════════════════════════════════════════════════
// 0. GITHUB AUTHENTICATION
// ══════════════════════════════════════════════════════════════

async function connectGitHub() {
    const btn = document.getElementById("btn-gh-connect");
    const err = document.getElementById("gh-err");
    const user = document.getElementById("gh-username").value.trim();
    
    if (!user) { err.textContent = "Please enter a username."; return; }
    
    btn.innerHTML = `<span class="material-symbols-outlined" style="animation: spin 1s linear infinite; margin-right:8px;">sync</span> Connecting...`;
    btn.disabled = true;
    err.textContent = "";
    
    try {
        const r = await fetch(`https://api.github.com/users/${user}`);
        if (!r.ok) throw new Error("User not found on GitHub");
        const data = await r.json();
        
        // Save to vertex_settings
        const s = loadSettings();
        s.userName = data.login;
        s.avatar_url = data.avatar_url;
        localStorage.setItem(STORE_SET, JSON.stringify(s));
        
        applyGitHubUser();
    } catch(e) {
        err.textContent = "❌ " + e.message;
        btn.innerHTML = `<svg height="20" viewBox="0 0 16 16" width="20" fill="currentColor"><path d="M8 0c4.42 0 8 3.58 8 8a8.013 8.013 0 0 1-5.45 7.59c-.4.08-.55-.17-.55-.38 0-.27.01-1.13.01-2.2 0-.75-.25-1.23-.54-1.48 1.78-.2 3.65-.88 3.65-3.95 0-.88-.31-1.59-.82-2.15.08-.2.36-1.02-.08-2.12 0 0-.67-.22-2.2.82-.64-.18-1.32-.27-2-.27-.68 0-1.36.09-2 .27-1.53-1.03-2.2-.82-2.2-.82-.44 1.1-.16 1.92-.08 2.12-.51.56-.82 1.28-.82 2.15 0 3.06 1.86 3.75 3.64 3.95-.23.2-.44.55-.51 1.07-.46.21-1.61.55-2.33-.66-.15-.24-.6-.83-1.23-.82-.67.01-.27.38.01.53.34.19.73.9.82 1.13.16.45.68 1.31 2.69.94 0 .67.01 1.3.01 1.49 0 .21-.15.45-.55.38A7.995 7.995 0 0 1 0 8c0-4.42 3.58-8 8-8Z"></path></svg> Continue with GitHub`;
        btn.disabled = false;
    }
}

function applyGitHubUser() {
    const s = loadSettings();
    const overlay = document.getElementById("gh-auth-overlay");
    if (!overlay) return;

    if (s.userName && s.avatar_url) {
        overlay.classList.add("hidden");
        // Update navbar with avatar
        const navRight = document.querySelector(".nav-actions");
        if (navRight && !document.getElementById("nav-avatar")) {
             navRight.insertAdjacentHTML("afterbegin", 
                `<img id="nav-avatar" src="${s.avatar_url}" title="${s.userName}" style="width:36px;height:36px;border-radius:50%;border:1px solid var(--outline);margin-right:16px;">`
             );
        }
    } else {
        overlay.classList.remove("hidden");
    }
}

document.addEventListener("DOMContentLoaded", applyGitHubUser);

// ══════════════════════════════════════════════════════════════
// 1. SLIDE-IN PANEL
// ══════════════════════════════════════════════════════════════

function showPanel(type) {
    const content = document.getElementById("panelContent");
    content.innerHTML = getPanelHTML(type);

    document.getElementById("panelOverlay").classList.add("open");
    document.getElementById("panel").classList.add("open");

    // If history panel, render it
    if (type === "history") setTimeout(renderHistPanel, 50);
}

function hidePanel() {
    document.getElementById("panelOverlay").classList.remove("open");
    document.getElementById("panel").classList.remove("open");
}

document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") hidePanel();
});

// ══════════════════════════════════════════════════════════════
// 2. PANEL HTML TEMPLATES
// ══════════════════════════════════════════════════════════════

function getPanelHTML(type) {
    const s = loadSettings();
    const blend = s.blendFile || "Untitled.blend";
    const user  = s.userName  || "sanyam";

    switch (type) {
        case "serialize": return `
            <h2 class="p-title">📦 Serialize</h2>
            <p class="p-desc">Extract spatial data from your Blender scene to JSON with user attribution. Each run saves a versioned snapshot.</p>
            <div class="p-group">
                <label class="p-label">Blend File</label>
                <input type="text" class="p-input" id="p-ser-blend" value="${esc(blend)}">
            </div>
            <div class="p-group">
                <label class="p-label">User</label>
                <input type="text" class="p-input" id="p-ser-user" value="${esc(user)}">
            </div>
            <button class="p-btn" onclick="genSerialize()">Execute</button>
            <div id="p-ser-out"></div>`;

        case "restore": return `
            <h2 class="p-title">⏪ Restore</h2>
            <p class="p-desc">Revert your scene to any previous version. Lists all snapshots including [MERGE] tagged ones.</p>
            <div class="p-group">
                <label class="p-label">Blend File</label>
                <input type="text" class="p-input" id="p-res-blend" value="${esc(blend)}">
            </div>
            <div class="p-group">
                <label class="p-label">Version Number</label>
                <input type="number" class="p-input" id="p-res-version" placeholder="e.g. 5 (Leave empty to list all)">
            </div>
            <button class="p-btn" onclick="genRestore()">Execute</button>
            <div id="p-res-out"></div>`;

        case "merge": return `
            <h2 class="p-title">🔀 Merge</h2>
            <p class="p-desc">Combine spatial data from multiple artists. Union keeps all; 3-way resolves conflicts Git-style.</p>
            <div class="p-group">
                <label class="p-label">Target Blend File</label>
                <input type="text" class="p-input" id="p-mrg-blend" value="${esc(blend)}">
            </div>
            <div class="p-row">
                <div class="p-group">
                    <label class="p-label">File A</label>
                    <input type="text" class="p-input" id="p-mrg-a" placeholder="data/Untitled.json">
                </div>
                <div class="p-group">
                    <label class="p-label">File B</label>
                    <input type="text" class="p-input" id="p-mrg-b" placeholder="data/t1.json">
                </div>
            </div>
            <div class="p-row">
                <div class="p-group">
                    <label class="p-label">Mode</label>
                    <select class="p-input" id="p-mrg-mode">
                        <option value="union">Union (keep all)</option>
                        <option value="3way">3-Way (Git-style)</option>
                    </select>
                </div>
                <div class="p-group">
                    <label class="p-label">Strategy</label>
                    <select class="p-input" id="p-mrg-strategy">
                        <option value="theirs">Theirs</option>
                        <option value="ours">Ours</option>
                    </select>
                </div>
            </div>
            <button class="p-btn" onclick="genMerge()">Execute</button>
            <div id="p-mrg-out"></div>`;

        case "diff": return `
            <h2 class="p-title">👻 Ghost Diff</h2>
            <p class="p-desc">Visualize scene history with transparent wireframe ghosts. See where objects were in the past.</p>
            <div class="p-group">
                <label class="p-label">Blend File</label>
                <input type="text" class="p-input" id="p-diff-blend" value="${esc(blend)}">
            </div>
            <div class="p-group">
                <label class="p-label">Compare Mode</label>
                <select class="p-input" id="p-diff-mode" onchange="toggleDiffVal()">
                    <option value="latest">vs Last Saved</option>
                    <option value="ago">Minutes Ago</option>
                    <option value="version">Specific Version</option>
                    <option value="clear">Clear Ghosts</option>
                </select>
            </div>
            <div class="p-group" id="p-diff-val-g">
                <label class="p-label" id="p-diff-val-l">Value</label>
                <input type="number" class="p-input" id="p-diff-val" placeholder="10">
            </div>
            <button class="p-btn" onclick="genDiff()">Execute</button>
            <div id="p-diff-out"></div>`;

        case "branch": return `
            <h2 class="p-title">🌿 Branch</h2>
            <p class="p-desc">Create, switch, list, and delete Git branches for parallel workflows.</p>
            <div class="p-group">
                <label class="p-label">Blend File</label>
                <input type="text" class="p-input" id="p-br-blend" value="${esc(blend)}">
            </div>
            <div class="p-group">
                <label class="p-label">Action</label>
                <select class="p-input" id="p-br-action" onchange="toggleBrName()">
                    <option value="list">List Branches</option>
                    <option value="create">Create Branch</option>
                    <option value="switch">Switch Branch</option>
                    <option value="delete">Delete Branch</option>
                </select>
            </div>
            <div class="p-group" id="p-br-name-g" style="display:none">
                <label class="p-label">Branch Name</label>
                <input type="text" class="p-input" id="p-br-name" placeholder="lighting-v2">
            </div>
            <button class="p-btn" onclick="genBranch()">Execute</button>
            <div id="p-br-out"></div>`;

        case "sync": return `
            <h2 class="p-title">🔄 Sync</h2>
            <p class="p-desc">One command: serialize → commit → push. Full round-trip to GitHub.</p>
            <div class="p-group">
                <label class="p-label">Blend File</label>
                <input type="text" class="p-input" id="p-sync-blend" value="${esc(blend)}">
            </div>
            <div class="p-group">
                <label class="p-label">User</label>
                <input type="text" class="p-input" id="p-sync-user" value="${esc(user)}">
            </div>
            <div class="p-group">
                <label class="p-label">Commit Message</label>
                <input type="text" class="p-input" id="p-sync-msg" placeholder="updated scene layout">
            </div>
            <div class="p-check">
                <input type="checkbox" id="p-sync-pull">
                <label for="p-sync-pull">Pull before push</label>
            </div>
            <button class="p-btn" onclick="genSync()">Execute</button>
            <div id="p-sync-out"></div>`;

        case "viewer": return `
            <h2 class="p-title">📊 JSON Viewer</h2>
            <p class="p-desc">Paste your spatial.json to visualize objects, transforms, and user attribution.</p>
            <textarea class="v-textarea" id="p-json" placeholder='[{"name":"Cube","loc":[0,0,0],"rot":[0,0,0],"scale":[1,1,1],"modified_by":"sanyam"}]'></textarea>
            <button class="p-btn" onclick="parseViewer()">Visualize</button>
            <div id="p-viewer-out"></div>`;

        case "history": return `
            <h2 class="p-title">📜 Command History</h2>
            <p class="p-desc">All generated commands logged for quick reference.</p>
            <button class="h-clear" onclick="clearHist()">Clear</button>
            <div style="clear:both"></div>
            <div id="p-hist-list"></div>`;

        case "setup": return `
            <h2 class="p-title">⚙️ Settings</h2>
            <p class="p-desc">Configure defaults. Everything is saved to your browser's localStorage.</p>
            <div class="p-group">
                <label class="p-label">Default Blend File</label>
                <input type="text" class="p-input" id="p-set-blend" value="${esc(s.blendFile||"")}" placeholder="Untitled.blend">
            </div>
            <div class="p-group">
                <label class="p-label">Username</label>
                <input type="text" class="p-input" id="p-set-user" value="${esc(s.userName||"")}" placeholder="sanyam">
            </div>
            <div class="p-group">
                <label class="p-label">GitHub Repo</label>
                <input type="text" class="p-input" id="p-set-repo" value="${esc(s.githubRepo||"")}" placeholder="https://github.com/user/repo">
            </div>
            <button class="p-btn" onclick="saveSetup()">Save Settings</button>
            <div id="p-set-out"></div>`;

        default: return `<p>Unknown panel</p>`;
    }
}


// ══════════════════════════════════════════════════════════════
// 3. COMMAND GENERATORS & EXECUTION
// ══════════════════════════════════════════════════════════════

function val(id, fb = "") { return document.getElementById(id)?.value.trim() || fb; }
function esc(s) { return String(s).replace(/"/g, "&quot;").replace(/</g, "&lt;"); }

function cmdHTML(cmd) {
    return `<div class="cmd-box">
        <button class="cmd-copy" onclick="copyCmd(this)">Copy</button>
        <span class="cmd-text">${escHTML(cmd)}</span>
    </div>`;
}
function escHTML(s) { return s.replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;"); }

async function copyCmd(btn) {
    const text = btn.parentElement.querySelector(".cmd-text").textContent;
    try { await navigator.clipboard.writeText(text); } catch {}
    btn.textContent = "Copied!";
    setTimeout(() => btn.textContent = "Copy", 1200);
}

async function runCommand(cmd, outElementId) {
    const outEl = document.getElementById(outElementId);
    outEl.innerHTML = cmdHTML(cmd) + `<div class="cmd-box" style="color:var(--on-surface-variant)">Executing in background...</div>`;
    addHist("command", cmd);
    
    try {
        const res = await fetch("/api/run", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ command: cmd })
        });
        
        const data = await res.json();
        
        let outputHTML = cmdHTML(cmd);
        if (data.returncode === 0) {
            outputHTML += `<div class="cmd-box" style="color:#55efc4; white-space:pre-wrap; max-height:200px; overflow:auto; margin-top:8px">✅ Success\n${escHTML(data.stdout)}</div>`;
        } else {
            outputHTML += `<div class="cmd-box" style="color:var(--error); white-space:pre-wrap; max-height:200px; overflow:auto; margin-top:8px">❌ Error (Code ${data.returncode})\n${escHTML(data.stderr || data.stdout)}</div>`;
        }
        outEl.innerHTML = outputHTML;
    } catch (e) {
        outEl.innerHTML = cmdHTML(cmd) + `<div class="cmd-box" style="color:var(--error); margin-top:8px">❌ Failed to connect to local server. Make sure you are running 'python server.py'</div>`;
    }
}

function genSerialize() {
    const b = val("p-ser-blend", "Untitled.blend");
    const u = val("p-ser-user", "unknown");
    const cmd = `blender --background ${b} --python scripts/serialize.py -- --user ${u}`;
    runCommand(cmd, "p-ser-out");
}

function genRestore() {
    const b = val("p-res-blend", "Untitled.blend");
    const v = val("p-res-version");
    let cmd = `blender --background ${b} --python scripts/restore.py`;
    if (v) cmd += ` -- --version ${v}`;
    runCommand(cmd, "p-res-out");
}

function genMerge() {
    const b = val("p-mrg-blend", "Untitled.blend");
    const a = val("p-mrg-a", "data/fileA.json");
    const fileB = val("p-mrg-b", "data/fileB.json");
    const mode = val("p-mrg-mode", "union");
    const strat = val("p-mrg-strategy", "theirs");
    let cmd = `blender --background ${b} --python scripts/merge.py -- ${a} ${fileB}`;
    if (mode !== "union") cmd += ` --mode ${mode} --strategy ${strat}`;
    runCommand(cmd, "p-mrg-out");
}

function genDiff() {
    const b = val("p-diff-blend", "Untitled.blend");
    const mode = val("p-diff-mode", "latest");
    const v = val("p-diff-val");
    let cmd = `blender ${b} --python scripts/diff.py`;
    if (mode === "ago" && v) cmd += ` -- --ago ${v}`;
    else if (mode === "version" && v) cmd += ` -- --version ${v}`;
    else if (mode === "clear") cmd += ` -- --clear`;
    runCommand(cmd, "p-diff-out");
}

function genBranch() {
    const b = val("p-br-blend", "Untitled.blend");
    const action = val("p-br-action", "list");
    const name = val("p-br-name");
    let cmd = `blender --background ${b} --python scripts/branch.py`;
    if (action !== "list") cmd += ` -- --${action} ${name || "branch-name"}`;
    runCommand(cmd, "p-br-out");
}

function genSync() {
    const b = val("p-sync-blend", "Untitled.blend");
    const u = val("p-sync-user", "unknown");
    const msg = val("p-sync-msg", "vertex sync");
    const pull = document.getElementById("p-sync-pull")?.checked;
    let cmd = `blender --background ${b} --python scripts/sync.py -- --user ${u} -m "${msg}"`;
    if (pull) cmd += ` --pull`;
    runCommand(cmd, "p-sync-out");
}


// ══════════════════════════════════════════════════════════════
// 4. TOGGLE HELPERS
// ══════════════════════════════════════════════════════════════

function toggleDiffVal() {
    const m = val("p-diff-mode");
    const g = document.getElementById("p-diff-val-g");
    const l = document.getElementById("p-diff-val-l");
    if (m === "ago")      { g.style.display = "block"; l.textContent = "Minutes Ago"; }
    else if (m === "version") { g.style.display = "block"; l.textContent = "Version #"; }
    else { g.style.display = "none"; }
}

function toggleBrName() {
    const a = val("p-br-action");
    document.getElementById("p-br-name-g").style.display = a === "list" ? "none" : "block";
}


// ══════════════════════════════════════════════════════════════
// 5. JSON VIEWER
// ══════════════════════════════════════════════════════════════

const UCOLORS = ["user-0","user-1","user-2","user-3","user-4"];
const umap = {};
let uidx = 0;

function ucolor(u) {
    if (!u) return "user-0";
    if (!(u in umap)) { umap[u] = UCOLORS[uidx % UCOLORS.length]; uidx++; }
    return umap[u];
}

function fmtVec(a) {
    if (!Array.isArray(a)) return "—";
    return a.map(v => typeof v === "number" ? v.toFixed(2) : v).join(", ");
}

function parseViewer() {
    const raw = document.getElementById("p-json").value.trim();
    const out = document.getElementById("p-viewer-out");
    try {
        const data = JSON.parse(raw);
        if (!Array.isArray(data)) throw new Error("Expected array");
        let html = `<table class="v-table"><thead><tr>
            <th>Name</th><th>Location</th><th>Rotation</th><th>Scale</th><th>User</th>
        </tr></thead><tbody>`;
        for (const o of data) {
            const c = ucolor(o.modified_by);
            const tag = o.modified_by
                ? `<span class="user-tag ${c}">${escHTML(o.modified_by)}</span>` : "—";
            html += `<tr>
                <td style="color:var(--on-surface);font-weight:500">${escHTML(o.name)}</td>
                <td>${fmtVec(o.loc)}</td><td>${fmtVec(o.rot)}</td><td>${fmtVec(o.scale)}</td>
                <td>${tag}</td></tr>`;
        }
        html += `</tbody></table>`;
        out.innerHTML = html;
    } catch (e) {
        out.innerHTML = `<div class="cmd-box" style="color:var(--error)">❌ ${escHTML(e.message)}</div>`;
    }
}


// ══════════════════════════════════════════════════════════════
// 6. SETTINGS + HISTORY (localStorage)
// ══════════════════════════════════════════════════════════════

const STORE_SET = "vertex_settings";
const STORE_HIS = "vertex_history";

function loadSettings() {
    try { return JSON.parse(localStorage.getItem(STORE_SET) || "{}"); } catch { return {}; }
}
function loadHist() {
    try { return JSON.parse(localStorage.getItem(STORE_HIS) || "[]"); } catch { return []; }
}

function addHist(type, cmd) {
    const h = loadHist();
    h.unshift({ type, cmd, time: new Date().toLocaleTimeString() });
    if (h.length > 50) h.length = 50;
    localStorage.setItem(STORE_HIS, JSON.stringify(h));
}

function clearHist() {
    localStorage.removeItem(STORE_HIS);
    const el = document.getElementById("p-hist-list");
    if (el) el.innerHTML = '<div class="h-empty">No commands yet</div>';
}

function saveSetup() {
    const s = {
        blendFile: val("p-set-blend"),
        userName: val("p-set-user"),
        githubRepo: val("p-set-repo"),
    };
    localStorage.setItem(STORE_SET, JSON.stringify(s));
    document.getElementById("p-set-out").innerHTML =
        `<div class="cmd-box" style="color:#55efc4">✅ Settings saved!</div>`;
}

function renderHistPanel() {
    const el = document.getElementById("p-hist-list");
    if (!el) return;
    const h = loadHist();
    if (h.length === 0) {
        el.innerHTML = '<div class="h-empty">No commands generated yet</div>';
        return;
    }
    el.innerHTML = h.map(i => `
        <div class="h-item">
            <span class="h-type">${escHTML(i.type)}</span>
            <span class="h-cmd">${escHTML(i.cmd)}</span>
            <span class="h-time">${i.time}</span>
            <button class="h-copy" onclick="navigator.clipboard.writeText(\`${i.cmd.replace(/`/g,"\\`")}\`)">Copy</button>
        </div>
    `).join("");
}
