import { getDriverHome } from "../services/driver/driverHomeService.js";
import { getPickUpInfo, updatePickUpInfo } from "../services/driver/driverPickupService.js";
import { getDeliveryInfo, updateDeliveryInfo } from "../services/driver/driverDeliveryService.js";
import { getRoute, requestRoute } from "../services/driver/driverRouteService.js";

// 홈 화면
export const getHomeInfo = async (req, res, next) => {
  try {
    const data = await getDriverHome(req);
    res.status(200).json({ status: true, data });
  } catch (err) {
    console.error(err);
    res.status(500).json({ status: false, message: "서버 오류 발생" });
  }
};

// 수거 화면
export const getPickUpList = async (req, res, next) => {
  try {
    const data = await getPickUpInfo(req);
    res.status(200).json({ status: true, data });
  } catch (err) {
    console.error(err);
    res.status(500).json({ status: false, message: "서버 오류 발생" });
  }
};

export const patchPickUp = async (req, res, next) => {
  try {
    const { storeId } = req.params;
    const data = await updatePickUpInfo(req, storeId);
    res.status(200).json({ status: true, data });
  } catch (err) {
    console.error(err);
    res.status(err.status || 500).json({ status: false, message: err.message || "서버 오류 발생" });
  }
};

// 배송 화면
export const getDeliveryList = async (req, res, next) => {
  try {
    const data = await getDeliveryInfo(req);
    res.status(200).json({ status: true, data });
  } catch (err) {
    console.error(err);
    res.status(500).json({ status: false, message: "서버 오류 발생" });
  }
};

export const patchDelivery = async (req, res, next) => {
  try {
    const { trackingCode } = req.params;
    const data = await updateDeliveryInfo(req, trackingCode);
    res.status(200).json({ status: true, data });
  } catch (err) {
    console.error(err);
    res.status(err.status || 500).json({ status: false, message: err.message || "서버 오류 발생" });
  }
};

// 최적 경로 안내
/*
export const getRouteInfo = async (req, res, next) => {
  try {
    const data = await getRoute(req);
    res.status(200).json({ status: true, data });
  } catch (err) {
    console.error(err);
    res.status(500).json({ status: false, message: "서버 오류 발생" });
  }
};

export const postRouteRequest = async (req, res, next) => {
  try {
    const data = await requestRoute(req);
    res.status(200).json({ status: true, data });
  } catch (err) {
    console.error(err);
    res.status(err.status || 500).json({ status: false, message: err.message || "서버 오류 발생" });
  }
};
*/