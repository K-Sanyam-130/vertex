/**
 * operations.js — Blender script operation routes
 * 
 * POST /api/serialize — Run serialize.py
 * POST /api/restore  — Run restore.py
 * POST /api/merge    — Run merge.py
 * POST /api/ghost    — Run diff.py
 * POST /api/sync     — Git add + commit + push
 * GET  /api/versions — List version history
 * GET  /api/data/:file — Read a JSON data file
 */

const express = require('express');
const router = express.Router();
const path = require('path');
const fs = require('fs');
const { execSync, exec } = require('child_process');
const { runBlenderScript } = require('../utils/blender');

const PROJECT_ROOT = path.resolve(__dirname, '..', '..');
const SCRIPTS_DIR = path.join(PROJECT_ROOT, 'scripts');
const DATA_DIR = path.join(PROJECT_ROOT, 'data');
const HISTORY_DIR = path.join(DATA_DIR, 'history');

/**
 * Find blend files in the project directory
 */
function findBlendFiles() {
    try {
        const files = fs.readdirSync(PROJECT_ROOT);
        return files
            .filter(f => f.endsWith('.blend') && !f.endsWith('.blend1'))
            .map(f => ({
                name: f,
                path: path.join(PROJECT_ROOT, f),
                size: fs.statSync(path.join(PROJECT_ROOT, f)).size,
            }));
    } catch {
        return [];
    }
}

// GET /api/blend-files — List available .blend files
router.get('/blend-files', (req, res) => {
    res.json(findBlendFiles());
});

// POST /api/serialize — Run serialize.py
router.post('/serialize', async (req, res) => {
    const { blendFile, user } = req.body;
    
    if (!blendFile) {
        return res.status(400).json({ error: 'blendFile is required' });
    }

    const blendPath = path.isAbsolute(blendFile) 
        ? blendFile 
        : path.join(PROJECT_ROOT, blendFile);
    
    if (!fs.existsSync(blendPath)) {
        return res.status(404).json({ error: `Blend file not found: ${blendFile}` });
    }

    const scriptArgs = user ? ['--user', user] : [];
    const result = await runBlenderScript(blendPath, path.join(SCRIPTS_DIR, 'serialize.py'), scriptArgs);
    
    res.json({
        success: result.success,
        output: result.stdout,
        errors: result.stderr,
    });
});

// POST /api/restore — Run restore.py
router.post('/restore', async (req, res) => {
    const { blendFile, version } = req.body;
    
    if (!blendFile) {
        return res.status(400).json({ error: 'blendFile is required' });
    }

    const blendPath = path.isAbsolute(blendFile)
        ? blendFile
        : path.join(PROJECT_ROOT, blendFile);

    if (!fs.existsSync(blendPath)) {
        return res.status(404).json({ error: `Blend file not found: ${blendFile}` });
    }

    // For restore, we pass the version as a script arg if provided
    const scriptArgs = version ? ['--version', String(version)] : [];
    const result = await runBlenderScript(blendPath, path.join(SCRIPTS_DIR, 'restore.py'), scriptArgs);
    
    res.json({
        success: result.success,
        output: result.stdout,
        errors: result.stderr,
    });
});

// POST /api/merge — Run merge.py
router.post('/merge', async (req, res) => {
    const { blendFile, fileA, fileB, mode, strategy } = req.body;
    
    if (!blendFile || !fileA || !fileB) {
        return res.status(400).json({ error: 'blendFile, fileA, and fileB are required' });
    }

    const blendPath = path.isAbsolute(blendFile)
        ? blendFile
        : path.join(PROJECT_ROOT, blendFile);

    const scriptArgs = [fileA, fileB];
    if (mode) {
        scriptArgs.push('--mode', mode);
    }
    if (strategy) {
        scriptArgs.push('--strategy', strategy);
    }

    const result = await runBlenderScript(blendPath, path.join(SCRIPTS_DIR, 'merge.py'), scriptArgs);
    
    res.json({
        success: result.success,
        output: result.stdout,
        errors: result.stderr,
    });
});

// POST /api/ghost — Run diff.py
router.post('/ghost', async (req, res) => {
    const { blendFile } = req.body;
    
    if (!blendFile) {
        return res.status(400).json({ error: 'blendFile is required' });
    }

    const blendPath = path.isAbsolute(blendFile)
        ? blendFile
        : path.join(PROJECT_ROOT, blendFile);

    const result = await runBlenderScript(blendPath, path.join(SCRIPTS_DIR, 'diff.py'));
    
    res.json({
        success: result.success,
        output: result.stdout,
        errors: result.stderr,
    });
});

// POST /api/sync — Git add + commit + push
router.post('/sync', (req, res) => {
    const { message } = req.body;
    const commitMsg = message || 'vertex snapshot';

    try {
        const addOutput = execSync('git add .', { cwd: PROJECT_ROOT, encoding: 'utf8' });
        
        let commitOutput = '';
        try {
            commitOutput = execSync(`git commit -m "${commitMsg.replace(/"/g, '\\"')}"`, { cwd: PROJECT_ROOT, encoding: 'utf8' });
        } catch (e) {
            // Nothing to commit is not an error
            if (e.stdout && e.stdout.includes('nothing to commit')) {
                commitOutput = 'Nothing to commit, working tree clean.';
            } else if (e.stderr && e.stderr.includes('nothing to commit')) {
                commitOutput = 'Nothing to commit, working tree clean.';
            } else {
                throw e;
            }
        }

        let pullOutput = '';
        try {
            // To prevent non-fast-forward reject errors, pull --rebase from remote first
            pullOutput = execSync('git pull --rebase', { cwd: PROJECT_ROOT, encoding: 'utf8', timeout: 30000 });
        } catch (e) {
            // It's fine to fail pulling if there is no remote configured
            pullOutput = e.stderr || e.message || '';
        }

        let pushOutput = '';
        try {
            pushOutput = execSync('git push', { cwd: PROJECT_ROOT, encoding: 'utf8', timeout: 30000 });
        } catch (e) {
            return res.json({
                success: false,
                output: `Commit successful.\n\nPush failed:\n${e.stderr || e.message}`,
                errors: e.stderr || e.message,
            });
        }

        res.json({
            success: true,
            output: `${addOutput}\n${commitOutput}\n${pullOutput}\n${pushOutput}`.trim(),
            errors: '',
        });
    } catch (err) {
        res.json({
            success: false,
            output: '',
            errors: err.stderr || err.message,
        });
    }
});

// GET /api/versions — List version history
router.get('/versions', (req, res) => {
    const domain = req.query.domain || null;

    if (!fs.existsSync(HISTORY_DIR)) {
        return res.json([]);
    }

    try {
        const files = fs.readdirSync(HISTORY_DIR)
            .filter(f => f.startsWith('v') && f.endsWith('.json'))
            .sort();

        const versions = files.map(f => {
            const nameNoExt = f.replace('.json', '');
            const parts = nameNoExt.split('_');
            const verNum = parseInt(parts[0].slice(1), 10);
            
            // Detect domain from filename
            let fileDomain = 'spatial';
            const isMerge = f.includes('merge');
            for (const d of ['spatial', 'lighting', 'materials', 'modifiers']) {
                if (nameNoExt.includes(d)) {
                    fileDomain = d;
                    break;
                }
            }

            const stat = fs.statSync(path.join(HISTORY_DIR, f));

            return {
                version: verNum,
                domain: fileDomain,
                filename: f,
                isMerge,
                timestamp: stat.mtime.toISOString(),
                size: stat.size,
            };
        }).filter(v => !domain || v.domain === domain);

        res.json(versions);
    } catch (err) {
        res.status(500).json({ error: err.message });
    }
});

// GET /api/data/:file — Read a JSON data file  
router.get('/data/:file', (req, res) => {
    const filePath = path.join(DATA_DIR, req.params.file);
    
    if (!fs.existsSync(filePath)) {
        return res.status(404).json({ error: 'File not found' });
    }

    try {
        const data = JSON.parse(fs.readFileSync(filePath, 'utf8'));
        res.json(data);
    } catch (err) {
        res.status(500).json({ error: 'Failed to parse JSON' });
    }
});

module.exports = router;
