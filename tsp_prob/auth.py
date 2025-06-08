import os
import jwt
import pymysql
import logging
from flask import request, jsonify
from functools import wraps

JWT_SECRET = os.environ.get("JWT_SECRET", "your-secret-key")
BACKEND_API_URL = os.environ.get("BACKEND_API_URL", "http://backend:8080")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_db_connection():
    return pymysql.connect(
        host=os.environ.get("MYSQL_HOST", "subtrack-rds.cv860smoa37l.ap-northeast-2.rds.amazonaws.com"),
        user=os.environ.get("MYSQL_USER", "admin"),
        password=os.environ.get("MYSQL_PASSWORD", "adminsubtrack"),
        db=os.environ.get("MYSQL_DATABASE", "subtrack"),
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )

def auth_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = None
        
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            try:
                token = auth_header.split(' ')[1]
            except IndexError:
                return jsonify({"error": "잘못된 토큰 형식입니다"}), 401
        
        if not token:
            return jsonify({"error": "토큰이 없습니다"}), 401
        
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
            
            if 'userId' in payload:
                request.current_user_id = payload['userId']
            elif 'user_id' in payload:
                request.current_user_id = payload['user_id']
            else:
                return jsonify({"error": "토큰에 사용자 ID 정보가 없습니다"}), 401
            
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "토큰이 만료되었습니다"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "유효하지 않은 토큰입니다"}), 401
            
        return f(*args, **kwargs)
    
    return decorated_function

def determine_zone_by_district(district):
    district_zone_mapping = {
        "은평구": "강북서부", "서대문구": "강북서부", "마포구": "강북서부",
        "도봉구": "강북동부", "노원구": "강북동부", "강북구": "강북동부", "성북구": "강북동부",
        "종로구": "강북중부", "중구": "강북중부", "용산구": "강북중부",
        "강서구": "강남서부", "양천구": "강남서부", "구로구": "강남서부", 
        "영등포구": "강남서부", "동작구": "강남서부", "관악구": "강남서부", "금천구": "강남서부",
        "성동구": "강남동부", "광진구": "강남동부", "동대문구": "강남동부", "중랑구": "강남동부",
        "강동구": "강남동부", "송파구": "강남동부", "강남구": "강남동부", "서초구": "강남동부"
    }
    return district_zone_mapping.get(district, "Unknown")

def get_current_driver():
    try:
        if not hasattr(request, 'current_user_id'):
            logger.error("current_user_id가 request 객체에 없습니다.")
            return {
                "id": 1,
                "name": "Default Driver",
                "zone": "강남서부",
                "district": "강남구"
            }
        
        user_id = request.current_user_id
        logger.info(f"인증된 사용자 ID: {user_id}")
        
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                sql = """
                SELECT id, name, email, userType, isApproved
                FROM User 
                WHERE id = %s
                """
                cursor.execute(sql, (user_id,))
                user_data = cursor.fetchone()
                
                if not user_data:
                    logger.warning(f"사용자 ID {user_id}에 대한 정보를 찾을 수 없습니다.")
                    return {
                        "id": user_id,
                        "name": "Unknown Driver",
                        "zone": "Unknown",
                        "district": ""
                    }
                
                sql = """
                SELECT id, userId, phoneNumber, vehicleNumber, regionCity, regionDistrict
                FROM DriverInfo
                WHERE userId = %s
                """
                cursor.execute(sql, (user_id,))
                driver_data = cursor.fetchone()
                
                if not driver_data:
                    logger.warning(f"사용자 ID {user_id}에 대한 기사 정보를 찾을 수 없습니다.")
                    return {
                        "id": user_id,
                        "name": user_data.get('name', 'Unknown Driver'),
                        "zone": "Unknown",
                        "district": ""
                    }
                
                district = driver_data.get("regionDistrict", "")
                zone = determine_zone_by_district(district)
                
                result = {
                    "id": driver_data.get("id"),
                    "name": user_data.get("name"),
                    "zone": zone,
                    "district": district,
                    "user_id": user_id,
                    "phoneNumber": driver_data.get("phoneNumber"),
                    "vehicleNumber": driver_data.get("vehicleNumber"),
                    "regionCity": driver_data.get("regionCity")
                }
                
                logger.info(f"기사 정보 조회 성공: {result}")
                return result
                
        except Exception as e:
            logger.error(f"DB 쿼리 실행 오류: {e}")
            return {
                "id": user_id,
                "name": "Error Driver",
                "zone": "Unknown",
                "district": ""
            }
        finally:
            conn.close()
            
    except Exception as e:
        logger.error(f"DB에서 기사 정보 조회 오류: {e}")
        return {
            "id": getattr(request, 'current_user_id', 1),
            "name": "Default Driver",
            "zone": "강남서부",
            "district": "강남구"
        }