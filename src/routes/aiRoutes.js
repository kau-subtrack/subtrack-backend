import express from 'express';
import { getPickupCompletionStatus } from '../controllers/aiController.js';

const router = express.Router();

router.get('/pickup/all-completed', getPickupCompletionStatus);

export default router;