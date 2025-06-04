import dotenv from 'dotenv';
dotenv.config();
import { pool } from "../../config/db.js";
import axios from 'axios';

const AI_HOST = process.env.AI_HOST;

export const getDriverPickupList = async (req) => {
  const driverId = req.userId;
  const token = req.headers.authorization;

  if (!token) {
    throw new Error("AI 요청 토큰 누락");
  }

  try {
    const { data } = await axios.get(`${AI_HOST}/api/pickup/next`, {
      headers: {
        Authorization: token
      }
    });

    // 모든 isNextPickupTarget 초기화 (어차피 항상 수행)
    await pool.query(
      `UPDATE Parcel 
       SET isNextPickupTarget = false 
       WHERE pickupDriverId = ? 
         AND DATE(pickupScheduledDate) = CURDATE()
         AND isDeleted = false`,
      [driverId]
    );

    // AI가 수거 진행 중일 때만 하나를 true로 설정
    if (data?.status === 'success' && data?.next_destination?.parcel_id) {
      const nextParcelId = data.next_destination.parcel_id;

      await pool.query(
        `UPDATE Parcel 
         SET isNextPickupTarget = true 
         WHERE id = ?`,
        [nextParcelId]
      );
    }

    // 어떤 상태든 항상 오늘자 수거 목록은 출력
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
        AND (p.status = 'PICKUP_PENDING' OR p.status = 'PICKUP_COMPLETED')
      GROUP BY p.ownerId
      ORDER BY isNextPickupTarget DESC`,
      [driverId]
    );

    return parcels.map(p => ({
      ...p,
      isNextPickupTarget: Boolean(p.isNextPickupTarget)
    }));
  } catch (err) {
    console.error('[ERROR] getDriverPickupList:', err.message);
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
      `SELECT id, status FROM Parcel
       WHERE ownerId = ? AND pickupDriverId = ? AND DATE(pickupScheduledDate) = CURDATE() AND isDeleted = false`,
      [ownerId, driverId]
    );

    if (parcels.length === 0) {
      const error = new Error('해당 가게의 수거 대상이 없거나 권한이 없습니다.');
      error.status = 404;
      throw error;
    }

    if (parcels.every(p => p.status !== 'PICKUP_PENDING')) {
      const error = new Error('이미 완료된 수거입니다.');
      error.status = 400;
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

    // AI에 수거 완료 보고 (모든 pending인 parcelId에 대해 개별 호출)
    const pendingParcels = parcels.filter(p => p.status === 'PICKUP_PENDING');

    await Promise.all(
      pendingParcels.map(({ id }) =>
        axios.post(`${process.env.AI_HOST}/api/pickup/complete`, { parcelId: id })
          .catch(err => {
            console.warn(`AI 서버 호출 실패 - parcelId: ${id}`, err.message);
          })
      )
    );

    // 전체 완료 여부 확인
    const { data } = await axios.get(`${process.env.AI_HOST}/api/pickup/all-completed`);
    if (data.completed) {
      console.log('🎉 모든 수거 완료 → 배달 전환됨');
    }

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
       WHERE ownerId = ? AND pickupDriverId = ? AND DATE(pickupScheduledDate) = CURDATE() AND isDeleted = false
       GROUP BY ownerId
       LIMIT 1`,
      [ownerId, driverId]
    );

    return updated[0];
  } catch (err) {
    if (err.status) throw err;
    const error = new Error('서버 오류 발생');
    error.status = 500;
    throw error;
  }
};