import http from 'http';
import dotenv from 'dotenv';
import app from './app.js';
// import { checkS3Connection } from './config/s3config.js';

dotenv.config();

const PORT = process.env.PORT || 3000;
const ENV = process.env.NODE_ENV || 'development';
const server = http.createServer(app);

server.listen(PORT, async () => {
  console.log(`🚀 Server running on http://localhost:${PORT} [${ENV}]`);
  // await checkS3Connection();
});
