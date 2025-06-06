import dotenv from 'dotenv';
dotenv.config();
import { pool } from '../../config/db.js';
import { s2point } from "../../config/sizeToPoint.js";
import { pad } from "../../config/pad.js";
import { sendPickupWebhook } from '../ai/index.js';

// get 배송 전체 내역
export const getShipmentListView = async (req) => {
  //기본 금일 날짜
  const [syear, smonth, sday] = new Date(+new Date() + 3240 * 10000).toISOString().split("T")[0].split('-');
  try {
    const year = req.query.year || syear;
    const month = req.query.month || smonth;
    const day = req.query.day || sday;
    const userId = req.userId;

    //ex)2025-04-21  day까지만 확인
    const time = year + '-' + pad(month) + '-' + pad(day);

    //날짜기준 배송리스트 조회
    const [result] = await pool.query(
        'SELECT trackingCode, recipientName, recipientAddr, detailAddress, productName, status, deliveryCompletedAt, pickupScheduledDate, size FROM Parcel WHERE ownerId = ? AND DATE(pickupScheduledDate) = ? AND isDeleted = false',
        [userId, time]
    );

    //json 양식
    return { status: true, date: time, data: result };
  } catch (err) {
    console.error(err);
    throw new Error('유효하지 않습니다.'); //오류 분류 추후 수정
  }
};


// get 배송 완료 내역
export const getShipmentCompleteView = async (req) => {
  //기본 금일 날짜
  const [syear, smonth, sday] = new Date(+new Date() + 3240 * 10000).toISOString().split("T")[0].split('-');
  try {
    const year = req.query.year || syear;
    const month = req.query.month || smonth;
    //const day = req.query.day || sday;
    const userId = req.userId;

    //ex)2025-04-00  month까지 확인
    const time = year + '-' + pad(month);// + '-' + day;

    //날짜기준 배송리스트 조회 ( 월간 확인 )
    const [result] = await pool.query(
        "SELECT trackingCode, recipientName, recipientAddr, detailAddress, productName, status, deliveryCompletedAt, pickupScheduledDate, size FROM Parcel WHERE ownerId = ? AND DATE_FORMAT(pickupScheduledDate, '%Y-%m') = ?",
        [userId, time]
    );

    //json 양식
    return { status: true, date: time, data: result };
  } catch (err) {
    console.error(err);
    throw new Error('유효하지 않습니다.'); //오류 분류 추후 수정
  }
};


// get 단일배송정보조회
export const getShipmentDetailView = async (req) => {
  try {
    const track = req.query.track;
    //trackingCode 기준 배송리스트 조회
    const [result] = await pool.query(
        'SELECT * FROM Parcel WHERE trackingCode = ?',
        [track]
    );

    //json 양식
    return { status: true, data: result[0] || {} };
  } catch (err) {
    console.error(err);
    throw new Error('유효하지 않습니다.'); //오류 분류 추후 수정
  }
};

// 단건 배송 화면
export const postShipment = async (req) => {
  const {
    productName, recipientName, recipientPhone,
    recipientAddr, detailAddress, size, caution
  } = req.body;

  console.log(`ownerId: ${req.userId}`);

  if (!productName || !recipientName || !recipientPhone || !recipientAddr || !detailAddress || !size) {
    throw new Error('필수 항목 누락');
  }

  try {
    const userId = req.userId;
    const trackingCode = generateTrackingCode(); // 고유 송장번호 생성

    // pickupScheduledDate 및 deliveryScheduledDate 자동 설정
    const now = new Date();
    const currentHour = now.getHours();

    const scheduledDate = new Date();
    if (currentHour >= 12) {
      // 낮 12시 이후면 내일 날짜로 설정
      scheduledDate.setDate(scheduledDate.getDate() + 1);
    }

    const formattedDate = scheduledDate.toISOString().split('T')[0]; // 'YYYY-MM-DD'
    const pickupScheduledDate = formattedDate;
    const deliveryScheduledDate = formattedDate;

    // 배송 정보 등록
    const [result] = await pool.query(
      `INSERT INTO Parcel (
         ownerId, trackingCode, productName, size, caution,
         recipientName, recipientPhone, recipientAddr, detailAddress,
         pickupScheduledDate, deliveryScheduledDate
       ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
      [
        userId, trackingCode, productName, size, caution,
        recipientName, recipientPhone, recipientAddr, detailAddress,
        pickupScheduledDate, deliveryScheduledDate
      ]
    );

    const parcelId = result.insertId;

    // 포인트 차감
    const spoints = s2point(size);
    const type = 'USE';

    await pool.query(
      'INSERT INTO PointTransaction (userId, amount, type, reason) VALUES (?, ?, ?, ?)',
      [userId, spoints, type, "배송"]
    );

    // AI 수거 요청 Webhook
    await sendPickupWebhook(parcelId);

    return {
      status: true,
      message: '배송 정보가 등록되었습니다.',
      parcelId,
      trackingCode,
      usedPoints: spoints
    };
  } catch (err) {
    console.error(err);
    throw new Error('유효하지 않습니다.');
  }
};

// 삭제 요청(soft delete)
export const softDeleteShipment = async (req, res) => {
  const { trackingCode } = req.body;
  const userId = req.userId;

  if (!trackingCode) {
    return { status: false, message: "운송장 번호가 누락되었습니다." };
  }

  const [rows] = await pool.query(
    'SELECT id FROM Parcel WHERE trackingCode = ? AND ownerId = ? AND isDeleted = false',
    [trackingCode, userId]
  );

  if (rows.length === 0) {
    return { status: false, message: "운송장을 찾을 수 없거나 접근 권한이 없습니다." };
  }

  await pool.query(
    'UPDATE Parcel SET isDeleted = true WHERE trackingCode = ? AND ownerId = ?',
    [trackingCode, userId]
  );

  return {
    status: true,
    message: "삭제 요청이 정상 처리되었습니다.",
    data: { trackingCode }
  };
};

// 송장번호 생성기
function generateTrackingCode() {
  const date = new Date().toISOString().slice(0, 10).replace(/-/g, '');
  const random = Math.random().toString(36).substr(2, 6).toUpperCase();
  return `PKG-${date}-${random}`;
}