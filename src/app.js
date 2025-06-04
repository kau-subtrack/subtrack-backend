import express from 'express';
import dotenv from 'dotenv';
dotenv.config();
import authRoutes from './routes/auth.js'
import ownerRoutes from './routes/owner.js';
import driverRoutes from './routes/driver.js';
import aiRoutes from './routes/aiRoutes.js';

const app = express();
app.use(express.json());

app.use('/auth', authRoutes);
app.use('/owner', ownerRoutes);
app.use('/driver', driverRoutes);
app.use('/ai', aiRoutes);

// Health Check 엔드포인트
app.get('/health', (req, res) => {
    res.status(200).json({
        status: 'OK',
        uptime: process.uptime(),
        timestamp: Date.now()
    });
});

export default app;
