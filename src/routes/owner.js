import express from 'express';
import { getHomeInfo, getCompletedShipments, getShipmentList, getShipmentDetail, registerShipment, 
         subscribePlan, chargePoints, getPointHistory, updateStoreInfo, changePassword } from '../controllers/ownerControllers.js';
import { jwtMiddleware } from '../middlewares/jwtMiddleware.js';  // 필요 시 추가

const router = express.Router();

//router.use(jwtMiddleware);  // 전체 인증 필요 시 사용

// 홈
router.get('/home', jwtMiddleware, getHomeInfo); // 홈 화면 정보

// 발송
router.get('/shipment-history/completed', getCompletedShipments); // 배송완료된 등록 내역
router.get('/shipment/list', getShipmentList); // 전체 발송 내역 조회
router.get('/shipment/trackingNumber', getShipmentDetail); // (보류 상태) 단건 발송 조회
router.post('/shipment/register', registerShipment); // 배송 정보 입력 

// 구독/포인트
router.post('/points/subscribe', subscribePlan); // 구독하기
router.post('/points/charge', chargePoints); // 추가 결제하기
router.get('/points/history', getPointHistory); // (보류 상태)사용 이력 조회

// 마이페이지
router.post('/my-page', updateStoreInfo); // 가게 정보 수정하기
router.post('/my-page/change-password', changePassword); // 비밀번호 수정하기

export default router;
