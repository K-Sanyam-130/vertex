/**
 * auth.js — GitHub OAuth routes
 */

const express = require('express');
const router = express.Router();

const GITHUB_CLIENT_ID = process.env.GITHUB_CLIENT_ID || '';
const GITHUB_CLIENT_SECRET = process.env.GITHUB_CLIENT_SECRET || '';
const FRONTEND_URL = process.env.FRONTEND_URL || 'http://localhost:5173';

// Redirect to GitHub OAuth
router.get('/github', (req, res) => {
    if (!GITHUB_CLIENT_ID) {
        return res.status(500).json({ error: 'GITHUB_CLIENT_ID not configured' });
    }
    const redirectUri = `${req.protocol}://${req.get('host')}/api/auth/github/callback`;
    const url = `https://github.com/login/oauth/authorize?client_id=${GITHUB_CLIENT_ID}&redirect_uri=${encodeURIComponent(redirectUri)}&scope=user,repo`;
    res.redirect(url);
});

// GitHub OAuth callback
router.get('/github/callback', async (req, res) => {
    const { code } = req.query;
    if (!code) {
        return res.redirect(`${FRONTEND_URL}/login?error=no_code`);
    }

    try {
        // Exchange code for access token
        const tokenRes = await fetch('https://github.com/login/oauth/access_token', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json',
            },
            body: JSON.stringify({
                client_id: GITHUB_CLIENT_ID,
                client_secret: GITHUB_CLIENT_SECRET,
                code,
            }),
        });

        const tokenData = await tokenRes.json();
        
        if (tokenData.error) {
            return res.redirect(`${FRONTEND_URL}/login?error=${tokenData.error}`);
        }

        // Redirect to frontend with token
        res.redirect(`${FRONTEND_URL}/dashboard?token=${tokenData.access_token}`);
    } catch (err) {
        console.error('[Auth] GitHub OAuth error:', err);
        res.redirect(`${FRONTEND_URL}/login?error=server_error`);
    }
});

// Get user info from GitHub token
router.get('/user', async (req, res) => {
    const token = req.headers.authorization?.replace('Bearer ', '');
    if (!token) {
        return res.status(401).json({ error: 'No token provided' });
    }

    try {
        const userRes = await fetch('https://api.github.com/user', {
            headers: { 'Authorization': `Bearer ${token}` },
        });
        const user = await userRes.json();
        res.json({
            login: user.login,
            name: user.name,
            avatar_url: user.avatar_url,
            html_url: user.html_url,
        });
    } catch (err) {
        res.status(500).json({ error: 'Failed to fetch user info' });
    }
});

module.exports = router;
