import http from 'http';
import dotenv from 'dotenv';
dotenv.config();
import app from './app.js';
import { connectDB } from './config/db.js';
// import { checkS3Connection } from './config/s3config.js';



const PORT = process.env.PORT || 3000;
const ENV = process.env.NODE_ENV || 'development';
const server = http.createServer(app);

server.listen(PORT, async () => {
  await connectDB();
  console.log(`🚀 Server running on http://localhost:${PORT} [${ENV}]`);
  // await checkS3Connection();
});
