import http from 'http';
import mongoose from 'mongoose';
import dotenv from 'dotenv';
import app from './app.js';
// import { checkS3Connection } from './config/s3config.js';

dotenv.config();

const PORT = process.env.PORT || 3000;
const ENV = process.env.NODE_ENV || 'development';
const server = http.createServer(app);

mongoose.connect(process.env.DATABASE_URL)
  .then(async () => {
    console.log('✅ MongoDB connected');

    server.listen(PORT, async () => {
      console.log(`Server running on http://localhost:${PORT} [${ENV}]`);
      // await checkS3Connection();
    });
  })
  .catch((err) => {
    console.error('MongoDB connection error:', err.message);
    process.exit(1);
  });