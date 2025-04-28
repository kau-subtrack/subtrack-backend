
// 홈
import {getOwnerHome} from "../services/owner/ownerhomeService.js";
import {postShipment, getShipmentListView, getShipmentDetailView, getShipmentCompleteView} from "../services/owner/ownershipmentService.js";

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
    res.status(200).json({ message: '구독 완료' });
  } catch (err) {
    console.error(err);
    res.status(500).json({ message: '서버 오류 발생' });
  }
};

export const chargePoints = async (req, res, next) => {
  try {
    res.status(200).json({ message: '포인트 충전 완료' });
  } catch (err) {
    console.error(err);
    res.status(500).json({ message: '서버 오류 발생' });
  }
};

export const getPointHistory = async (req, res, next) => {
  try {
    res.status(200).json({ message: '포인트 사용 이력 조회 (보류 상태)' });
  } catch (err) {
    console.error(err);
    res.status(500).json({ message: '서버 오류 발생' });
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