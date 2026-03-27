/**
 * blender.js — Blender subprocess helper
 * 
 * Spawns Blender in background mode to run Python scripts.
 * Captures stdout/stderr and returns structured results.
 */

const { spawn } = require('child_process');
const path = require('path');

const BLENDER_PATH = process.env.BLENDER_PATH || 'blender';

/**
 * Run a Blender script with optional arguments.
 * 
 * @param {string} blendFile - Path to the .blend file
 * @param {string} scriptPath - Path to the Python script
 * @param {string[]} scriptArgs - Arguments to pass after '--'
 * @returns {Promise<{success: boolean, stdout: string, stderr: string, code: number}>}
 */
function runBlenderScript(blendFile, scriptPath, scriptArgs = []) {
    return new Promise((resolve) => {
        const args = ['--background', blendFile, '--python', scriptPath];
        
        if (scriptArgs.length > 0) {
            args.push('--');
            args.push(...scriptArgs);
        }

        console.log(`[Blender] Running: ${BLENDER_PATH} ${args.join(' ')}`);

        const proc = spawn(BLENDER_PATH, args, {
            cwd: path.dirname(blendFile),
            env: { ...process.env },
        });

        let stdout = '';
        let stderr = '';

        proc.stdout.on('data', (data) => {
            stdout += data.toString();
        });

        proc.stderr.on('data', (data) => {
            stderr += data.toString();
        });

        proc.on('close', (code) => {
            resolve({
                success: code === 0,
                stdout,
                stderr,
                code: code ?? -1,
            });
        });

        proc.on('error', (err) => {
            resolve({
                success: false,
                stdout,
                stderr: err.message,
                code: -1,
            });
        });
    });
}

module.exports = { runBlenderScript, BLENDER_PATH };
