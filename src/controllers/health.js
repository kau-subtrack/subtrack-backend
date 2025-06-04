import dotenv from 'dotenv';
dotenv.config();


export const health = async (req, res) => {
    return res.status(200).json({
        status: 'OK',
        uptime: process.uptime(),
        timestamp: Date.now()
    });
}