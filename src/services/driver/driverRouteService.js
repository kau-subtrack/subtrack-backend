import dotenv from 'dotenv';
dotenv.config();
import { pool } from "../../config/db.js";

export const getRoute = async (req) => {
  try {
    // TODO: 기사 최적 경로 조회
    return {
      routes: [],
    };
  } catch (error) {
    console.error("getRoute error:", error);
    throw new Error("최적 경로 조회에 실패했습니다.");
  }
};

export const requestRoute = async (req) => {
  try {
    // TODO: 기사 경로 요청 처리
    return {
      requestAccepted: true,
    };
  } catch (error) {
    console.error("requestRoute error:", error);
    throw new Error("최적 경로 요청에 실패했습니다.");
  }
};