import express from 'express';
import dotenv from 'dotenv';
dotenv.config();
import authRoutes from './routes/auth.js'
import ownerRoutes from './routes/owner.js';



const app = express();
app.use(express.json());

//디버깅용
app.use((req, res, next) => {
  console.log(`요청 메서드: ${req.method}, 경로: ${req.path}`);
  next();
});

app.use('/auth', authRoutes);
app.use('/owner', ownerRoutes);



export default app;
