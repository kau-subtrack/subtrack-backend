import express from 'express';
import { getHomeInfo, getPickupList, completePickup, getDeliveryList, completeDelivery, /*getRouteInfo, postRouteRequest*/ } from "../controllers/driverControllers.js";
import { jwtMiddleware } from '../middlewares/jwtMiddleware.js';  // 필요 시 추가

const router = express.Router();

router.use(jwtMiddleware);  // 전체 인증 필요 시 사용

// 홈
router.get('/home', jwtMiddleware, getHomeInfo); // 홈 화면 정보

// 수거
router.get('/pick-up', jwtMiddleware, getPickupList); // 수거 정보 조회
router.patch('/pick-up/completed', jwtMiddleware, completePickup); // 수거 정보 변경 요청

// 배송
router.get('/delivery', jwtMiddleware, getDeliveryList); // 배송 정보 조회
router.patch('/delivery/completed', jwtMiddleware, completeDelivery); // 배송 정보 변경 요청

// 최적경로안내
// router.get('/route', getCompletedShipments); // 최적 경로 조회
// router.post('/route-request', changePassword); // 최적 경로 요청하기

export default router;