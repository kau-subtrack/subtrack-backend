import dotenv from 'dotenv';
dotenv.config();
import { pool } from "../../config/db.js";
import bcrypt from 'bcrypt';

// 마이페이지 - 가게 정보 수정
export const updateOwnerStoreInfo = async (req) => {
  const { address, detailAddress, latitude, longitude } = req.body;
  const userId = req.userId;
  console.log('userId:', req.userId);

  // 1. 유효성 검사
  if (!address || !latitude || !longitude) {
    const error = new Error('주소 정보가 올바르지 않습니다.');
    error.status = 400;
    throw error;
  }

  // 2. 업데이트
  const [result] = await pool.query(`
    UPDATE StoreInfo
    SET address = ?, detailAddress = ?, latitude = ?, longitude = ?
    WHERE userId = ?
  `, [address, detailAddress, latitude, longitude, userId]);

  console.log('수정 결과:', result);

  if (result.affectedRows === 0) {
    const error = new Error('가게 정보 수정 실패: 일치하는 사용자 없음');
    error.status = 404;
    throw error;
  }

  // 3. 수정된 데이터 반환
  return {
    status: true,
    message: "가게 정보가 수정되었습니다.",
    store: {
      address,
      detailAddress,
      latitude,
      longitude,
    },
  };
};

export const changeOwnerPassword = async (req) => {
  const { currentPassword, newPassword } = req.body;
  const userId = req.userId;

  if (!userId) throw new Error('인증 실패: userId 없음');

  // 1. 현재 비밀번호 확인
  const [userRows] = await pool.query('SELECT password FROM User WHERE id = ?', [userId]);
  if (userRows.length === 0) {
    const error = new Error('권한이 없습니다.');
    error.status = 404;
    throw error;
  }

  const isMatch = await bcrypt.compare(currentPassword, userRows[0].password);
  if (!isMatch) {
    const error = new Error('현재 비밀번호가 일치하지 않습니다.');
    error.status = 400;
    throw error;
  }

  // 2. 새 비밀번호 해싱 후 업데이트
  const hashedNewPassword = await bcrypt.hash(newPassword, 10);
  await pool.query('UPDATE User SET password = ? WHERE id = ?', [hashedNewPassword, userId]);

  return { status: true, message: '비밀번호가 변경되었습니다.' };
};

