import { checkAllPickupsCompleted } from '../services/ai/index.js';

export const getPickupCompletionStatus = async (req, res, next) => {
  try {
    const result = await checkAllPickupsCompleted();
    res.json({ status: true, data: result });
  } catch (err) {
    next(err);
  }
};