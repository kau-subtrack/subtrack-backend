import express from 'express';
import dotenv from 'dotenv';

dotenv.config();

const app = express();
app.use(express.json());

// 라우트 예시
app.get('/', (req, res) => {
  res.send('Hello, MongoDB Backend!');
});

export default app;
