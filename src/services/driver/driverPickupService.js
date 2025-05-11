import dotenv from 'dotenv';
dotenv.config();
import { pool } from "../../config/db.js";

export const getPickUpInfo = async (req) => {
  try {
    // TODO: 기사 수거 목록 조회
    return [];
  } catch (error) {
    console.error("getPickUpInfo error:", error);
    throw new Error("수거 목록을 불러오는 데 실패했습니다.");
  }
};

export const updatePickUpInfo = async (req, storeId) => {
  try {
    // TODO: storeId에 해당하는 수거 상태 업데이트
    return {
      storeId,
      updated: true,
    };
  } catch (error) {
    console.error("updatePickUpInfo error:", error);
    throw new Error("수거 상태 변경에 실패했습니다.");
  }
};