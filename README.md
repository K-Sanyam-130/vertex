# ⬡ Vertex — Version Control for Blender

> **Git-style version control, branching, merging, and visual diffing — built natively for Blender `.blend` files.**

Vertex bridges the gap between Blender and modern software collaboration workflows. It serializes 3D scene state into human-readable JSON, enabling real diff, merge, restore, and sync operations — all without touching the binary `.blend` format.

---

## ✨ Features

| Feature | Description |
|---|---|
| 📦 **Serialize** | Extract scene data (transforms, materials, lights, modifiers) into structured JSON |
| ⏪ **Restore** | Revert a scene to any previous snapshot with phased reconstruction |
| 🔀 **Merge** | Combine two scene files with union or 3-way Git-style merge |
| 👻 **Ghost / Diff** | Visual wireframe overlay showing what moved, changed, or was removed |
| 🔄 **Sync** | One-click: serialize → stage → commit → push to GitHub |
| 🌿 **Branch** | Create, switch, and delete Git branches from inside Blender |
| 🌐 **Web Dashboard** | React + Node.js web UI to run all operations from a browser |

---

## 🗂️ Project Structure

```
vertex/
├── scripts/          # Python scripts that run inside Blender (via --background)
│   ├── serialize.py  # Extract scene → JSON (spatial, lighting, materials, modifiers)
│   ├── restore.py    # Phased scene reconstruction from JSON snapshots
│   ├── merge.py      # Union or 3-way spatial merge
│   ├── diff.py       # Visual ghost-overlay diff
│   ├── sync.py       # All-in-one: serialize + git add + commit + push
│   ├── branch.py     # Git branch management from Blender
│   └── git_ops.py    # Shared Git subprocess helpers
│
├── server/           # Express.js API server (bridges frontend ↔ Blender)
│   ├── index.js      # Server entry point (port 3001)
│   ├── routes/
│   │   ├── auth.js       # GitHub OAuth (login / callback / user info)
│   │   └── operations.js # API routes for all script operations
│   └── utils/
│       └── blender.js    # Blender subprocess runner
│
├── frontend/         # React + Vite web dashboard (port 5173)
│   └── src/
│       ├── pages/
│       │   ├── LoginPage.jsx   # GitHub OAuth login page
│       │   └── Dashboard.jsx   # Main operations dashboard
│       ├── components/         # Navbar, ActionCard, Modal, OutputConsole
│       └── modals/             # Per-operation modal UIs
│
├── website/          # Standalone static site + Python dev server (port 8080)
│   ├── index.html    # Landing / marketing page
│   ├── app.js        # Standalone frontend logic
│   ├── style.css     # Styles
│   └── server.py     # Lightweight Python HTTP server
│
├── data/             # Runtime JSON state (auto-generated, committed to Git)
│   ├── spatial.json    # Object transforms (location, rotation, scale)
│   ├── lighting.json   # Light datablocks (type, energy, color, shadow)
│   ├── materials.json  # Principled BSDF properties + texture paths
│   ├── modifiers.json  # Per-object modifier stacks
│   ├── conflicts.json  # 3-way merge conflict log (if any)
│   └── history/        # Versioned snapshots (v001_spatial_..., etc.)
│
└── .env              # Local environment config (not committed)
```

---

## 🚀 Quick Start

### Prerequisites

- [Blender](https://www.blender.org/) (3.x or 4.x) — must be in your system PATH or configured in `.env`
- [Node.js](https://nodejs.org/) v18+
- [Python](https://www.python.org/) 3.8+ (for the standalone website server)
- A [GitHub OAuth App](https://github.com/settings/developers) (for login)

---

### 1. Clone the Repository

```bash
git clone https://github.com/K-Sanyam-130/vertex.git
cd vertex
```

---

### 2. Configure Environment

Copy the example config and fill in your values:

```bash
cp .env.example .env
```

Edit `.env`:

```env
# GitHub OAuth (create at https://github.com/settings/developers)
GITHUB_CLIENT_ID=your_client_id_here
GITHUB_CLIENT_SECRET=your_client_secret_here

# Path to Blender executable (leave as 'blender' if it's in your PATH)
BLENDER_PATH=blender

# Server
PORT=3001
FRONTEND_URL=http://localhost:5173
```

---

### 3. Start the API Server

```bash
npm install        # in the root directory
node server/index.js
```

The API server will start at **http://localhost:3001**.

---

### 4. Start the Web Dashboard

```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173** in your browser. Log in with GitHub to get started.

---

### 5. (Optional) Start the Standalone Website

```bash
cd website
python server.py
```

Open **http://localhost:8080** for the static landing page.

---

## 🐍 Python Scripts (CLI)

All scripts run inside Blender's Python environment using the `--background` flag. This means Blender processes the file without opening a GUI.

### 📦 Serialize

Extract all scene data to JSON:

```bash
blender --background yourfile.blend --python scripts/serialize.py
# With user attribution:
blender --background yourfile.blend --python scripts/serialize.py -- --user sanyam
```

**Output files** (written to `data/`):
- `spatial.json` — object transforms
- `lighting.json` — light datablocks
- `materials.json` — Principled BSDF properties + textures
- `modifiers.json` — modifier stacks

A versioned snapshot is saved to `data/history/` on every run (max 10 kept per domain).

---

### ⏪ Restore

Revert the scene to a previous state:

```bash
# Restore from the latest data/
blender --background yourfile.blend --python scripts/restore.py

# Restore from a specific version snapshot:
blender --background yourfile.blend --python scripts/restore.py -- --version 5
```

Restoration runs in **4 phases** to satisfy dependencies:
1. **Materials** — create Principled BSDF shaders
2. **Spatial** — place objects at saved transforms
3. **Lights** — restore light datablocks (energy, color, shadow)
4. **Modifiers** — apply modifier stacks (after all objects exist)

---

### 🔀 Merge

Combine two scene JSON files:

```bash
# Union merge (default) — all objects from both files:
blender --background file.blend --python scripts/merge.py -- data/fileA.json data/fileB.json

# 3-way merge (Git-style, using spatial.json as ancestor):
blender --background file.blend --python scripts/merge.py -- data/fileA.json data/fileB.json --mode 3way

# 3-way merge — prefer "ours" on conflicts:
blender --background file.blend --python scripts/merge.py -- data/fileA.json data/fileB.json --mode 3way --strategy ours
```

**Merge modes:**

| Mode | Behaviour |
|---|---|
| `union` | Additive — all objects from both files. Conflicts renamed `Name_A` / `Name_B` |
| `3way` | Git-style — uses `spatial.json` as the common ancestor. Conflicts resolved via `--strategy` |

**Conflict strategies:** `ours` (keep A) or `theirs` (keep B, default).

Conflict details are saved to `data/conflicts.json` for review.

---

### 👻 Ghost / Diff

Overlay wireframe "ghosts" to visualize changes:

```bash
# Compare against last serialized state:
blender yourfile.blend --python scripts/diff.py

# Compare against a specific version:
blender yourfile.blend --python scripts/diff.py -- --version 3

# Compare against state ~10 minutes ago:
blender yourfile.blend --python scripts/diff.py -- --ago 10

# Clear all ghost overlays:
blender yourfile.blend --python scripts/diff.py -- --clear
```

**Ghost colours:**
- 🟢 **Green** — object moved
- 🔴 **Red** — object was removed
- 🟡 **Yellow** — object was added since the comparison point

Ghosts auto-clean after 2 file opens via an embedded Blender auto-run script.

---

### 🔄 Sync

All-in-one: serialize → stage → commit → push:

```bash
blender --background file.blend --python scripts/sync.py

# With attribution and custom commit message:
blender --background file.blend --python scripts/sync.py -- --user sanyam -m "updated lighting setup"

# Pull latest before syncing:
blender --background file.blend --python scripts/sync.py -- --pull
```

---

### 🌿 Branch

Manage Git branches from Blender:

```bash
# List all branches:
blender --background file.blend --python scripts/branch.py

# Create and switch to a new branch:
blender --background file.blend --python scripts/branch.py -- --create lighting-v2

# Switch to an existing branch:
blender --background file.blend --python scripts/branch.py -- --switch main

# Delete a branch:
blender --background file.blend --python scripts/branch.py -- --delete lighting-v2
```

---

## 🌐 Web Dashboard API Reference

The Express server exposes the following REST API:

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/health` | Health check |
| `GET` | `/api/blend-files` | List `.blend` files in the project root |
| `POST` | `/api/serialize` | Run `serialize.py` on a blend file |
| `POST` | `/api/restore` | Run `restore.py` on a blend file |
| `POST` | `/api/merge` | Run `merge.py` (union or 3-way) |
| `POST` | `/api/ghost` | Run `diff.py` on a blend file |
| `POST` | `/api/sync` | Git add + commit + push |
| `GET` | `/api/versions` | List version history (filterable by domain) |
| `GET` | `/api/data/:file` | Read a JSON data file from `data/` |
| `GET` | `/api/auth/github` | Redirect to GitHub OAuth |
| `GET` | `/api/auth/github/callback` | OAuth callback handler |
| `GET` | `/api/auth/user` | Get authenticated GitHub user info |

---

## 🔐 GitHub OAuth Setup

1. Go to [GitHub Developer Settings](https://github.com/settings/developers) → **OAuth Apps** → **New OAuth App**
2. Set the **Authorization callback URL** to:
   ```
   http://localhost:3001/api/auth/github/callback
   ```
3. Copy the **Client ID** and **Client Secret** into your `.env` file

---

## 📊 Data Format

### `spatial.json`

```json
[
  {
    "name": "Cube",
    "loc": [0.0, 0.0, 0.0],
    "rot": [0.0, 0.0, 0.0],
    "scale": [1.0, 1.0, 1.0],
    "modified_by": "sanyam",
    "modified_at": "2026-05-14T18:30:00"
  }
]
```

### `materials.json`

```json
[
  {
    "material_name": "Material",
    "base_color": [0.8, 0.8, 0.8],
    "metallic": 0.0,
    "roughness": 0.5,
    "specular": 0.5,
    "ior": 1.45,
    "alpha": 1.0,
    "emission": { "color": [0.0, 0.0, 0.0], "strength": 0.0 },
    "textures": []
  }
]
```

### `history/` Naming Convention

Snapshot filenames follow the pattern:

```
v{version:03d}_{domain}_{YYYY-MM-DD}_{HH-MM-SS}.json
```

Examples:
- `v001_spatial_2026-05-14_18-30-00.json`
- `v003_merge_2026-05-14_19-00-00.json`
- `v007_lighting_2026-05-14_20-15-00.json`

---

## 🛠️ Supported Modifier Types

The following Blender modifier types are serialized and restored:

| Modifier | Serialized Properties |
|---|---|
| **Subdivision Surface** | Viewport & render levels |
| **Array** | Count, relative offset |
| **Boolean** | Operation, target object |
| **Mirror** | Axes, bisect axes, mirror object |
| **Solidify** | Thickness, offset, even offset |
| **Bevel** | Width, segments, limit method |
| **Edge Split** | Split angle, edge angle, sharp edge |
| **Decimate** | Type (Collapse/Un-subdivide/Dissolve), ratio/iterations/angle |
| **Wireframe** | Thickness, even offset, replace |
| **Screw** | Angle, steps, render steps, offset, axis |

---

## ⚙️ Blender Version Compatibility

| Blender Version | Status |
|---|---|
| 3.x | ✅ Fully supported |
| 4.x | ✅ Fully supported (handles `Specular IOR Level` rename, `Emission Color` rename) |
| 5.x / 6.x | ✅ Compatible (handles `use_nodes` deprecation in Blender 6.0+) |

---

## 🤝 Multi-User Collaboration Workflow

1. Each artist works on their own **Git branch**
2. On save, run **Serialize** to update `data/*.json`
3. Use **Sync** to commit and push changes
4. To integrate changes, use **Merge** (union or 3-way)
5. Use **Ghost** to visually review what changed between versions
6. Use **Restore** to roll back to any snapshot

---

## 📄 License

This project is open source. See [LICENSE](LICENSE) for details.

---

*Built for Blender artists who want the power of Git without leaving their 3D workspace.*
