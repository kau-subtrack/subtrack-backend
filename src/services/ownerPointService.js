import dotenv from 'dotenv';
dotenv.config();
import { pool } from '../config/db.js';

export const subscribeOwnerPlan = async (req) => {
  const { planId } = req.body;
  const userId = req.userId;
  if (!userId) throw new Error('인증 실패: userId 없음');
  
  // 1-1. 요금제 존재 확인
  const [plan] = await pool.query(`SELECT * FROM SubscriptionPlan WHERE id = ?`, [planId]);
  if (plan.length === 0) {
    return { status: false, message: '유효하지 않은 요금제입니다.' };
  }
  
  // 1-2. 유저 구독제 변경 및 포인트 지급
  await pool.query(`
    UPDATE User 
    SET subscriptionPlanId = ?, pointBalance = pointBalance + ? 
    WHERE id = ?
  `, [planId, plan[0].grantedPoint, userId]);
  
  // 1-3. 포인트 지급 기록
  await pool.query(
    `INSERT INTO PointTransaction (userId, amount, type, reason)
    VALUES (?, ?, 'CHARGE', '구독 결제')`,
    [userId, plan[0].grantedPoint]
  );
    
  // 1-4. 현재 포인트 다시 조회
  const [updatedUser] = await pool.query('SELECT pointBalance FROM User WHERE id = ?', [userId]);

  return {
    status: true,
    message: "구독이 완료되었습니다.",
    planName: plan[0].name,
    grantedPoints: plan[0].grantedPoint,
    currentPoints: updatedUser[0]?.pointBalance || 0,
    subscriptionStartDate: new Date().toISOString()
  };
};
  
// 2. 추가 결제
export const chargeOwnerPoints = async (req) => {
  const { planId } = req.body;
  const userId = req.userId;
  if (!userId) throw new Error('인증 실패: userId 없음');
  
  // 1-1. 요금제 존재 확인
  const [plan] = await pool.query(`SELECT * FROM SubscriptionPlan WHERE id = ?`, [planId]);
  if (plan.length === 0) {
    return { status: false, message: '유효하지 않은 요금제입니다.' };
  }
  
  // 1-2. 포인트만 추가 지급 (subscriptionPlanId는 변경 없음)
  await pool.query(`
    UPDATE User 
    SET pointBalance = pointBalance + ? 
    WHERE id = ?
  `, [plan[0].grantedPoint, userId]);
  
  // 1-3. 포인트 추가 결제 기록
  await pool.query(
    `INSERT INTO PointTransaction (userId, amount, type, reason)
    VALUES (?, ?, 'CHARGE', '추가 결제')`,
    [userId, plan[0].grantedPoint]
  );
  
  // 1-4. 현재 포인트 다시 조회
  const [updatedUser] = await pool.query('SELECT pointBalance FROM User WHERE id = ?', [userId]);
  
  return {
    status: true,
    message: "추가 결제가 완료되었습니다.",
    grantedPoints: plan[0].grantedPoint,
    currentPoints: updatedUser[0]?.pointBalance || 0,
    subscriptionStartDate: new Date().toISOString()
  };
};
  
  
  // 3. (선택) 포인트 이력 조회
export const getOwnerPointHistory = async (req) => {
  const userId = req.userId;
  const [history] = await pool.query(`
    SELECT amount, type, reason, createdAt 
    FROM PointTransaction
    WHERE userId = ?
    ORDER BY createdAt DESC
  `, [userId]);
  
  return {
    status: true,
    history
  };
};