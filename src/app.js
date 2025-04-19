import express from 'express';
import dotenv from 'dotenv';
dotenv.config();
import authRoutes from './routes/auth.js'



const app = express();
app.use(express.json());

// 라우트 예시
app.get('/', (req, res) => {
  res.send('Hello, MongoDB Backend!');
});
app.use('/auth', authRoutes);

export default app;
