import express from 'express';
import { signup } from '../controllers/signup.js';
import { login } from '../controllers/login.js';

const router = express.Router();

router.post('/signup', signup);
router.post('/login', login);

export default router;