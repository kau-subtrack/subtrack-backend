import axios from 'axios';

export const checkAllPickupsCompleted = async () => {
  const { data } = await axios.get(`${process.env.AI_HOST}/api/pickup/all-completed`);
  return data;
};