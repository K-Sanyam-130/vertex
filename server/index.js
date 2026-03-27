/**
 * Vertex Web Dashboard — Express Server
 * 
 * API server that bridges the React frontend to the Python/Blender scripts.
 * Handles file uploads, Blender subprocess execution, and GitHub OAuth.
 */

require('dotenv').config();

const express = require('express');
const cors = require('cors');
const path = require('path');

const authRoutes = require('./routes/auth');
const operationRoutes = require('./routes/operations');

const app = express();
const PORT = process.env.PORT || 3001;

// Middleware
app.use(cors({
    origin: process.env.FRONTEND_URL || 'http://localhost:5173',
    credentials: true,
}));
app.use(express.json());

// Routes
app.use('/api/auth', authRoutes);
app.use('/api', operationRoutes);

// Health check
app.get('/api/health', (req, res) => {
    res.json({ status: 'ok', timestamp: new Date().toISOString() });
});

// Start server
app.listen(PORT, () => {
    console.log(`\n  ⬡  Vertex API Server`);
    console.log(`     Running on http://localhost:${PORT}`);
    console.log(`     Frontend:  ${process.env.FRONTEND_URL || 'http://localhost:5173'}\n`);
});
