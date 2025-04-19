import dotenv from 'dotenv';
dotenv.config();
import bcrypt from 'bcrypt';
import { pool } from '../config/db.js';


// 회원가입

export const signup = async (req, res) => {
  const { email, password, name, userType,
    address, detailAddress, latitude, longitude,
    phoneNumber, vehicleNumber , regionCity, regionDistrict } = req.body;

  if (!email || !password || !name || !userType) {
    return res.status(400).json({ message: '필수 항목 누락' });
  }
  if(userType == "OWNER"){
    if (!address || !detailAddress || !latitude || !longitude) {
      return res.status(400).json({ message: '필수 항목 누락' });
    }
  }else if(userType == "DRIVER"){
    if (!phoneNumber || !vehicleNumber || !regionCity || !regionDistrict) {
      return res.status(400).json({ message: '필수 항목 누락' });
    }
  }

  try{

    const [exist] = await pool.query('SELECT * FROM User WHERE email = ?', [email])
    if (exist.length > 0) {
      return res.status(400).json({ message: '이미 등록된 이메일입니다' });
    }

    const hashedPassword = await bcrypt.hash(password, 10);
    const date = new Date(+new Date() + 3240 * 10000).toISOString().split("T")[0];

    // 관리자 승인 미구현
    const [result] = await pool.query(
        'INSERT INTO User (email, password, name, userType, isApproved, createdAt) VALUES (?, ?, ?, ?, ?, ?)',
        [email, hashedPassword, name, userType, true, date]
    );

    const [ids] = await pool.query('SELECT * FROM User WHERE email = ?', [email]);
    const userId = ids[0].id;

    //소상공인, 택배기사 정보 기입
    if(userType == "OWNER"){
      //미기입 기본 설정
      const expectedSize = "소형";
      const monthlyCount = 0;
      const pickupPreference = "";
      
      //User 정보 추가기입. 구독제 id? points. defaultpick

      // StoreInfo 등록
      await pool.query(
          `INSERT INTO StoreInfo 
            (userId, address, detailAddress, expectedSize, monthlyCount, latitude, longitude, pickupPreference)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)`,
            [userId, address, detailAddress, expectedSize, monthlyCount, latitude, longitude, pickupPreference]
      );

    }else if(userType == "DRIVER"){
      //화물 운송 자격증 파일, 운전 경력 증명서 파일
      /*
      const [result] = await pool.query(
          `INSERT INTO DocumnetUpload  
          (userId, type, fileUrl)
           VALUES (?, ?, ?)`,
          [userId, ,]
      );
      */
      
      //DriverInfo 등록
      await pool.query(
          `INSERT INTO DriverInfo 
          (userId, phoneNumber, vehicleNumber, regionCity, regionDistrict)
           VALUES (?, ?, ?, ?, ?)`,
          [userId, phoneNumber, vehicleNumber, regionCity, regionDistrict]
      );

    }

    return res.status(200).json({ success: true, message: '성공', userId: result.id });
  } catch (err) {
    console.error(err);
    return res.status(500).json({ message: '서버 에러' });
  }
};
