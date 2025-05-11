import dotenv from 'dotenv';
dotenv.config();
import { pool } from "../../config/db.js";

export const getDriverHome = async (req) => {
  try {
    const driverId = req.userId;

    // 1. 담당 위치 (드라이버가 할당된 store 정보)
    const [storeResult] = await pool.query(
      `SELECT s.address, s.detailAddress
       FROM StoreInfo s
       WHERE s.userId = ?`,
      [driverId]
    );
    
    /* store 존재 여부 검사
    if (!storeResult.length) {
      throw new Error("등록된 기사 정보가 없습니다.");
    }*/

    const store = storeResult[0] || {};

    // 2. 이번 달 수행 건수 (수거/배송/총합)
    const [monthlyStats] = await pool.query(
      `SELECT 
        COUNT(DISTINCT p1.id) AS pickupCount,
        COUNT(DISTINCT p2.id) AS deliveryCount
       FROM Parcel p1
       LEFT JOIN Parcel p2 ON p1.id = p2.id
       WHERE 
         (p1.pickupDriverId = ? AND MONTH(p1.pickupCompletedAt) = MONTH(CURRENT_DATE()) AND YEAR(p1.pickupCompletedAt) = YEAR(CURRENT_DATE()))
         OR
         (p2.deliveryDriverId = ? AND MONTH(p2.deliveryCompletedAt) = MONTH(CURRENT_DATE()) AND YEAR(p2.deliveryCompletedAt) = YEAR(CURRENT_DATE()))
      `,
      [driverId, driverId]
    );

    const pickupCount = monthlyStats[0].pickupCount || 0;
    const deliveryCount = monthlyStats[0].deliveryCount || 0;
    const totalCount = pickupCount + deliveryCount;

    // 3. 오늘 업무
    const [todayStats] = await pool.query(
      `SELECT 
        SUM(CASE WHEN pickupDriverId = ? AND DATE(pickupScheduledDate) = CURRENT_DATE() THEN 1 ELSE 0 END) AS todayPickup,
        SUM(CASE WHEN deliveryDriverId = ? AND DATE(deliveryScheduledDate) = CURRENT_DATE() THEN 1 ELSE 0 END) AS todayDelivery
       FROM Parcel`,
      [driverId, driverId]
    );
    
    const todayPickup = todayStats?.[0]?.todayPickup || 0;
    const todayDelivery = todayStats?.[0]?.todayDelivery || 0;

    // 4. 적립 포인트 (User.points)
    const [pointResult] = await pool.query(
      `SELECT pointBalance FROM User WHERE id = ?`,
      [driverId]
    );

    return {
      region: `${store.address || ''} ${store.detailAddress || ''}`.trim(),
      monthlyCount: {
        pickup: pickupCount,
        delivery: deliveryCount,
        total: totalCount,
      },
      todayCount: {
        pickup: todayPickup,
        delivery: todayDelivery,
      },
      points: pointResult[0]?.pointBalance || 0
    };
  } catch (error) {
    console.error("getDriverHome error:", error);
    throw new Error("기사 홈 정보 조회 실패");
  }
};