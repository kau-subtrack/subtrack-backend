import dotenv from 'dotenv';
dotenv.config();
import { pool } from '../config/db.js';

// 소상공인 홈화면
export const getOwnerHome = async (req, res) => {
  try {
    const userId = req.userId;

    //기본 인출 정보
    const [user] = await pool.query('SELECT pointBalance FROM User WHERE id = ?', [userId]);

    const [plan] = await pool.query(`
      SELECT sp.name, sp.price
      FROM User u
      JOIN SubscriptionPlan sp ON u.subscriptionPlanId = sp.id
      WHERE u.id = ?
    `, [userId]);
    const cur_plan = (plan.length !== 0 ? plan[0].name : '미구독');

    //const [driver] = await pool.query('SELECT SubstriptionPlan FROM DriverInfo WHERE userId = ?', [userId]);
    
    const [store] = await pool.query('SELECT address, latitude, longitude FROM StoreInfo WHERE userId = ?', [userId]);

    //json 양식 
    return {
      status: true,
      data: {
        store: store[0] || {},
        assignedDriver: 'none',
        pickupDate: '',
        points: user[0]?.pointBalance || 0,
        subscriptionName: cur_plan
      }
    };
  } catch (err) {
    console.error(err);
    throw new Error('유효하지 않습니다.'); //오류 분류 추후 수정
  }
};
