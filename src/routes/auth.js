import express from 'express';
import { signup } from '../controllers/signup.js';
import { login } from '../controllers/login.js';
import {health} from "../controllers/health.js";

const router = express.Router();

router.post('/signup', signup);
router.post('/login', login);
router.get('/health', health);

export default router;