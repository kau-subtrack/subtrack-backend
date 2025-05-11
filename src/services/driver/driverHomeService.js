import dotenv from 'dotenv';
dotenv.config();
import { pool } from "../../config/db.js";

export const getDriverHome = async (req) => {
  try {
    // TODO: 기사 홈 화면 데이터 조회
    return {
      store: {},
      assignedDriver: {},
      pickupDate: null,
    };
  } catch (error) {
    console.error("getDriverHome error:", error);
    throw new Error("기사 홈 정보를 불러오는 데 실패했습니다.");
  }
};