
// 홈
import { getOwnerHome } from "../services/ownerhomeService.js";
import { subscribeOwnerPlan, chargeOwnerPoints, getOwnerPointHistory  } from "../services/ownerPointService.js";

export const getHomeInfo = async (req, res, next) => {
  try {
    const homeInfo = await getOwnerHome(req);
    res.status(200).json( homeInfo );
  } catch (err) {
    console.error(err);
    res.status(500).json({ message: '서버 오류 발생' });
  }
};

// 발송
export const getCompletedShipments = async (req, res, next) => {
  try {
    res.status(200).json({ message: '배송 완료된 발송 내역 반환' });
  } catch (err) {
    console.error(err);
    res.status(500).json({ message: '서버 오류 발생' });
  }
};

export const getShipmentList = async (req, res, next) => {
  try {
    res.status(200).json({ message: '전체 발송 내역 반환' });
  } catch (err) {
    console.error(err);
    res.status(500).json({ message: '서버 오류 발생' });
  }
};

export const getShipmentDetail = async (req, res, next) => {
  try {
    res.status(200).json({ message: '단건 발송 조회 (보류 상태)' });
  } catch (err) {
    console.error(err);
    res.status(500).json({ message: '서버 오류 발생' });
  }
};

export const registerShipment = async (req, res, next) => {
  try {
    res.status(200).json({ message: '배송 정보 등록 완료' });
  } catch (err) {
    console.error(err);
    res.status(500).json({ message: '서버 오류 발생' });
  }
};

// 포인트/구독
export const subscribePlan = async (req, res, next) => {
  try {
    const result = await subscribeOwnerPlan(req, res);
    res.status(200).json(result);
  } catch (err) {
    console.error(err);
    const statusCode = err.status || 500;
    res.status(statusCode).json({ message: err.message || '서버 오류 발생' });
  }
};

export const chargePoints = async (req, res, next) => {
  try {
    const result = await chargeOwnerPoints(req);
    res.status(200).json(result);
  } catch (err) {
    console.error(err);
    const statusCode = err.status || 500;
    res.status(statusCode).json({ message: err.message || '서버 오류 발생' });
  }
};

export const getPointHistory = async (req, res, next) => {
  try {
    const result = await getOwnerPointHistory(req, res);
    res.status(200).json(result);
  } catch (err) {
    console.error(err); 
    const statusCode = err.status || 500;
    res.status(statusCode).json({ message: err.message || '서버 오류 발생' });
  }
};

// 마이페이지
export const updateStoreInfo = async (req, res, next) => {
  try {
    res.status(200).json({ message: '가게 정보 수정 완료' });
  } catch (err) {
    console.error(err);
    res.status(500).json({ message: '서버 오류 발생' });
  }
};

export const changePassword = async (req, res, next) => {
  try {
    res.status(200).json({ message: '비밀번호 변경 완료' });
  } catch (err) {
    console.error(err);
    res.status(500).json({ message: '서버 오류 발생' });
  }
};