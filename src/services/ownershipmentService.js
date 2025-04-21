import dotenv from 'dotenv';
dotenv.config();
import { pool } from '../config/db.js';
import {s2point} from "../config/sizeToPoint.js";

// 단건 배송 화면
export const postShipment = async (req, res) => {
  const { productName, recipientName, recipientPhone, recipientAddr, detailAddress, size, caution, pickupDate } = req.body;

  if (!productName || !recipientName || !recipientPhone || !recipientAddr || !detailAddress || !size) {
    throw new Error('필수 항목 누락');
  }

  try {
    //0.이거 항상 이렇게 받으면, auth header가 항상 필요하다는 것임?
    const userId = req.userId;

    //trackingcode 송장번호 고유 기입 - 수거시 생성

    //parcel 단건 배송정보 입력
    const [result] = await pool.query(
        'INSERT INTO Parcel ( ownerid, productName, size, caution, recipientname, recipientPhone, recipientAddr, detailAddress, pickupDate) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
        [userId, productName, size, caution, recipientName, recipientPhone, recipientAddr, detailAddress, pickupDate]
    );

    //포인트 양식
    const spoints = s2point(size);
    const type = 'USE';

    //포인트 충분 조건 확인. 추후 추가.


    //소모 포인트 테이블 입력
    await pool.query(
        'INSERT INTO PointTransaction ( userid, amount, type, reason ) VALUES (?, ?, ?, ?)',
        [userId, spoints, type, "배송" ]
    );

    //json 양식
    return { status: true, message: '배송 정보가 등록되었습니다.', parcelId: result.insertId, usedPoints: spoints  };
  } catch (err) {
    console.error(err);
    throw new Error('유효하지 않습니다.'); //오류 분류 추후 수정
  }
};
