import dotenv from 'dotenv';
dotenv.config();
import { pool } from "../../config/db.js";

export const getDeliveryInfo = async (req) => {
  try {
    // TODO: 기사 배송 목록 조회
    return [];
  } catch (error) {
    console.error("getDeliveryInfo error:", error);
    throw new Error("배송 정보를 불러오는 데 실패했습니다.");
  }
};

export const updateDeliveryInfo = async (req, trackingCode) => {
  try {
    // TODO: trackingCode에 해당하는 배송 상태 업데이트
    return {
      trackingCode,
      updated: true,
    };
  } catch (error) {
    console.error("updateDeliveryInfo error:", error);
    throw new Error("배송 상태 변경에 실패했습니다.");
  }
};