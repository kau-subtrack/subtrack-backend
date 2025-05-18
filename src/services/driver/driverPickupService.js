import dotenv from 'dotenv';
dotenv.config();
import { pool } from "../../config/db.js";

export const getDriverPickupList = async (req) => {
  const driverId = req.userId;

  try {
    const [parcels] = await pool.query(
      `SELECT
         p.ownerId,
         MIN(p.recipientAddr) AS address,
         MIN(p.detailAddress) AS detailAddress,
         MIN(p.pickupTimeWindow) AS pickupTimeWindow,
         MIN(p.productName) AS productName,
         COUNT(p.id) AS parcelCount,
         MAX(p.status) AS status,
         MAX(p.isNextPickupTarget) AS isNextPickupTarget
       FROM Parcel AS p
       WHERE p.pickupDriverId = ? 
         AND DATE(p.pickupScheduledDate) = CURDATE()
         AND p.isDeleted = false
         AND p.status = 'PICKUP_PENDING'
       GROUP BY p.ownerId
       ORDER BY isNextPickupTarget DESC`,
      [driverId]
    );

    return parcels.map(p => ({
      ...p,
      isNextPickupTarget: Boolean(p.isNextPickupTarget)
    }));
  } catch (err) {
    console.error(err);
    throw new Error("서버 오류 발생");
  }
};

export const completeDriverPickup = async (req) => {
  const driverId = req.userId;
  const { ownerId } = req.body;

  if (!ownerId) {
    const error = new Error('ownerId는 필수입니다.');
    error.status = 400;
    throw error;
  }

  try {
    // 권한 및 유효성 확인
    const [parcels] = await pool.query(
      `SELECT id FROM Parcel
       WHERE ownerId = ? AND pickupDriverId = ? AND DATE(pickupScheduledDate) = CURDATE() AND isDeleted = false`,
      [ownerId, driverId]
    );

    if (parcels.length === 0) {
      const error = new Error('해당 가게의 수거 대상이 없거나 권한이 없습니다.');
      error.status = 404;
      throw error;
    }

    // 상태 일괄 업데이트
    await pool.query(
      `UPDATE Parcel
       SET status = 'PICKUP_COMPLETED',
           pickupCompletedAt = NOW(),
           isNextPickupTarget = false
       WHERE ownerId = ? AND pickupDriverId = ? AND DATE(pickupScheduledDate) = CURDATE() AND isDeleted = false`,
      [ownerId, driverId]
    );

    // 응답용 요약 정보
    const [updated] = await pool.query(
      `SELECT
         MIN(recipientAddr) AS address,
         MIN(detailAddress) AS detailAddress,
         MIN(pickupTimeWindow) AS pickupTimeWindow,
         MIN(productName) AS productName,
         COUNT(id) AS parcelCount,
         'PICKUP_COMPLETED' AS status
       FROM Parcel
       WHERE ownerId = ?
         AND pickupDriverId = ?
         AND DATE(pickupScheduledDate) = CURDATE()
         AND isDeleted = false
       GROUP BY ownerId
       LIMIT 1`,
      [ownerId, driverId]
    );

    return updated[0];
  } catch (err) {
    console.error(err);
    const error = new Error("서버 오류 발생");
    error.status = 500;
    throw error;
  }
};