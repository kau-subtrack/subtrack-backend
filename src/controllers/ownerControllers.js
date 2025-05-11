import { getOwnerHome } from "../services/owner/ownerhomeService.js";
import { postShipment, getShipmentListView, getShipmentDetailView, getShipmentCompleteView } from "../services/owner/ownershipmentService.js";
import { subscribeOwnerPlan, chargeOwnerPoints, getOwnerPointHistory  } from "../services/owner/ownerPointService.js";
import { updateOwnerStoreInfo, changeOwnerPassword } from "../services/owner/ownerMypageService.js";

// 홈
export const getHomeInfo = async (req, res, next) => {
  try {
    const homeInfo = await getOwnerHome(req, res);
    res.status(200).json( homeInfo );
  } catch (err) {
    console.error(err);
    res.status(500).json({ message: '서버 오류 발생' });
  }
};

// 발송
export const getCompletedShipments = async (req, res, next) => {
  try {
    const completed = await getShipmentCompleteView(req, res);
    res.status(200).json(completed);
  } catch (err) {
    console.error(err);
    res.status(500).json({ message: '서버 오류 발생' });
  }
};

export const getShipmentList = async (req, res, next) => {
  try {
    const list = await getShipmentListView(req, res);
    res.status(200).json(list);
  } catch (err) {
    console.error(err);
    res.status(500).json({ message: '서버 오류 발생' });
  }
};

export const getShipmentDetail = async (req, res, next) => {
  try {
    const detail = await getShipmentDetailView(req, res);
    res.status(200).json(detail);
  } catch (err) {
    console.error(err);
    res.status(500).json({ message: '서버 오류 발생' });
  }
};

export const registerShipment = async (req, res, next) => {
  try {
    const shipmentInfo = await postShipment(req);
    res.status(200).json(shipmentInfo);
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

// 마이페이지 - 가게 주소 수정
export const updateStoreInfo = async (req, res, next) => {
  try {
    const result = await updateOwnerStoreInfo(req);
    res.status(200).json(result);
  } catch (err) {
    console.error(err);
    const statusCode = err.status || 500;
    res.status(statusCode).json({ message: err.message || '서버 오류 발생' });
  }
};

export const changePassword = async (req, res, next) => {
  try {
    const result = await changeOwnerPassword(req);
    res.status(200).json(result);
  } catch (err) {
    console.error(err);
    const statusCode = err.status || 500;
    res.status(statusCode).json({ message: err.message || '서버 오류 발생' });
  }
};