
-- 1. 사용자 이름 + 요금제 이름 및 가격
SELECT u.name, u.email, p.name AS plan_name, p.price
FROM users u
JOIN subscription_plans p ON u.subscriptionPlanId = p.id;

-- 2. 점주(OWNER) 이름 + 가게 주소
SELECT u.name, s.address
FROM users u
JOIN store_infos s ON u.id = s.userId
WHERE u.userType = 'OWNER';

-- 3. 드라이버 이름 + 담당 지역
SELECT u.name, d.regionCity, d.regionDistrict
FROM users u
JOIN driver_infos d ON u.id = d.userId
WHERE u.userType = 'DRIVER';

-- 4. 주문 ID + 주문자 이름 + 드라이버 이름
SELECT o.id AS order_id, owner.name AS owner_name, driver.name AS driver_name
FROM orders o
JOIN users owner ON o.userId = owner.id
JOIN users driver ON o.driverId = driver.id;

-- 5. 택배 + 수령인 + 드라이버 이름
SELECT p.trackingCode, p.recipientName, u.name AS driver_name
FROM parcels p
JOIN users u ON p.driverId = u.id;

-- 6. 챗봇 대화 로그 + 사용자 이름
SELECT u.name, c.message, c.response, c.intent
FROM chatbot_logs c
JOIN users u ON c.userId = u.id;

-- 7. 알림 + 사용자 이메일
SELECT u.email, n.message, n.createdAt
FROM notifications n
JOIN users u ON n.userId = u.id;

-- 8. 포인트 거래내역 + 사용자 이름
SELECT u.name, pt.amount, pt.type, pt.createdAt
FROM point_transactions pt
JOIN users u ON pt.userId = u.id;

-- 9. 운전자 위치 정보 + 이름
SELECT u.name, d.latitude, d.longitude, d.updatedAt
FROM driver_locations d
JOIN users u ON d.driverId = u.id;

-- 10. 사용자 + 업로드한 문서 종류/URL
SELECT u.name, d.type, d.fileUrl
FROM document_uploads d
JOIN users u ON d.userId = u.id;
