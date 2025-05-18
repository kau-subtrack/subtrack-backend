import dotenv from 'dotenv';
dotenv.config();
import { pool } from "../../config/db.js";

export const getDriverDeliveryList = async (req) => {
  const driverId = req.userId;

  try {
    const [parcels] = await pool.query(
      `SELECT
         trackingCode,
         productName,
         recipientAddr AS address,
         detailAddress,
         deliveryTimeWindow,
         status,
         isNextDeliveryTarget
       FROM Parcel
       WHERE deliveryDriverId = ?
         AND DATE(deliveryScheduledDate) = CURDATE()
         AND isDeleted = false
         AND status = 'DELIVERY_PENDING'
       ORDER BY isNextDeliveryTarget DESC`,
      [driverId]
    );

    return parcels.map(p => ({
      trackingCode: p.trackingCode,
      productName: p.productName,
      deliveryAddress: {
        address: p.address,
        detailAddress: p.detailAddress
      },
      deliveryTimeWindow: p.deliveryTimeWindow,
      status: p.status,
      isNextDeliveryTarget: Boolean(p.isNextDeliveryTarget)
    }));
  } catch (err) {
    throw new Error("서버 오류 발생");
  }
};

export const completeDriverDelivery = async (req) => {
  const driverId = req.userId;
  const { trackingCode } = req.body;

  if (!trackingCode) {
    const error = new Error('trackingCode는 필수입니다.');
    error.status = 400;
    throw error;
  }

  try {
    // 권한 및 유효성 확인
    const [parcels] = await pool.query(
      `SELECT * FROM Parcel
       WHERE trackingCode = ?
         AND deliveryDriverId = ?
         AND isDeleted = false`,
      [trackingCode, driverId]
    );

    if (parcels.length === 0) {
      const error = new Error('해당 송장번호를 찾을 수 없거나 권한이 없습니다.');
      error.status = 404;
      throw error;
    }

    // DELIVERY_PENDING인지 체크
    if (parcels[0].status !== 'DELIVERY_PENDING') {
      const error = new Error('이미 완료된 배송입니다.');
      error.status = 400;
      throw error;
    }

    // 상태 업데이트
    await pool.query(
      `UPDATE Parcel
       SET status = 'DELIVERY_COMPLETED',
           deliveryCompletedAt = NOW(),
           isNextDeliveryTarget = false
       WHERE trackingCode = ? AND deliveryDriverId = ?`,
      [trackingCode, driverId]
    );

    // 응답용 데이터
    const parcel = parcels[0];
    return {
      trackingCode: parcel.trackingCode,
      productName: parcel.productName,
      deliveryAddress: {
        address: parcel.recipientAddr,
        detailAddress: parcel.detailAddress
      },
      deliveryTimeWindow: parcel.deliveryTimeWindow,
      status: 'DELIVERY_COMPLETED'
    };
  } catch (err) {
    if (err.status) throw err; // 400/404 같은 사용자 에러는 그대로 rethrow
    const error = new Error("서버 오류 발생");
    error.status = 500;
    throw error;
  }
};