import requests
import json
import numpy as np
import logging
import os
import pymysql
from datetime import datetime, time as datetime_time
from flask import Flask, request, jsonify
import pytz
import polyline

from auth import auth_required, get_current_driver

from get_valhalla_matrix import get_time_distance_matrix
from get_valhalla_route import get_turn_by_turn_route

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

driver_hub_status = {}

BACKEND_API_URL = os.environ.get("BACKEND_API_URL")
LKH_SERVICE_URL = os.environ.get("LKH_SERVICE_URL", "http://lkh:5001/solve")
DELIVERY_START_TIME = datetime_time(15, 0)
HUB_LOCATION = {"lat": 37.5299, "lon": 126.9648, "name": "용산역"}
COSTING_MODEL = "auto"
KST = pytz.timezone('Asia/Seoul')

KAKAO_API_KEY = os.environ.get('KAKAO_API_KEY', 'YOUR_KAKAO_API_KEY_HERE')
KAKAO_ADDRESS_API = "https://dapi.kakao.com/v2/local/search/address.json"
KAKAO_KEYWORD_API = "https://dapi.kakao.com/v2/local/search/keyword.json"

DISTRICT_DRIVER_MAPPING = {
    "은평구": 6, "서대문구": 6, "마포구": 6,

    "도봉구": 7, "노원구": 7, "강북구": 7, "성북구": 7,

    "종로구": 8, "중구": 8, "용산구": 8,

    "강서구": 9, "양천구": 9, "구로구": 9, "영등포구": 9, 
    "동작구": 9, "관악구": 9, "금천구": 9,

    "성동구": 10, "광진구": 10, "동대문구": 10, "중랑구": 10, 
    "강동구": 10, "송파구": 10, "강남구": 10, "서초구": 10
}

app = Flask(__name__)

def get_enhanced_time_distance_matrix(locations, costing="auto"):
    time_matrix, distance_matrix = get_time_distance_matrix(locations, costing=costing, use_traffic=True)
    return time_matrix, distance_matrix

def get_db_connection():
    return pymysql.connect(
        host=os.environ.get("MYSQL_HOST", "subtrack-rds.cv860smoa37l.ap-northeast-2.rds.amazonaws.com"),
        user=os.environ.get("MYSQL_USER", "admin"),
        password=os.environ.get("MYSQL_PASSWORD", "adminsubtrack"),
        db=os.environ.get("MYSQL_DATABASE", "subtrack"),
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )

def get_completed_pickups_today_from_db():
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            sql = """
            SELECT p.*, 
                   o.name as ownerName, 
                   pd.name as pickupDriverName
            FROM Parcel p
            LEFT JOIN User o ON p.ownerId = o.id
            LEFT JOIN User pd ON p.pickupDriverId = pd.id
            WHERE p.status = 'PICKUP_COMPLETED' 
            AND DATE(p.pickupCompletedAt) = CURDATE()
            AND p.isDeleted = 0
            AND p.deliveryDriverId IS NULL
            """
            cursor.execute(sql)
            parcels = cursor.fetchall()

            for p in parcels:
                for key, value in p.items():
                    if isinstance(value, datetime):
                        p[key] = value.isoformat()
            
            return parcels
    except Exception as e:
        logging.error(f"DB 쿼리 오류: {e}")
        return []
    finally:
        conn.close()

def get_unassigned_deliveries_today_from_db():
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            sql = """
            SELECT p.*, 
                   o.name as ownerName
            FROM Parcel p
            LEFT JOIN User o ON p.ownerId = o.id
            WHERE p.status = 'DELIVERY_PENDING' 
            AND deliveryDriverId IS NULL
            AND DATE(p.pickupCompletedAt) = CURDATE()
            AND p.isDeleted = 0
            """
            cursor.execute(sql)
            deliveries = cursor.fetchall()

            for p in deliveries:
                for key, value in p.items():
                    if isinstance(value, datetime):
                        p[key] = value.isoformat()
            
            return deliveries
    except Exception as e:
        logging.error(f"DB 쿼리 오류: {e}")
        return []
    finally:
        conn.close()

def get_real_pending_deliveries(driver_id):
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            today = datetime.now(KST).date()
            sql = """
            SELECT p.*, 
                   o.name as ownerName
            FROM Parcel p
            LEFT JOIN User o ON p.ownerId = o.id
            WHERE p.deliveryDriverId = %s 
            AND p.status = 'DELIVERY_PENDING'
            AND p.isDeleted = 0
            ORDER BY p.createdAt DESC
            """
            cursor.execute(sql, (driver_id,))
            parcels = cursor.fetchall()

            result = []
            for p in parcels:
                completed_at = p['deliveryCompletedAt'].isoformat() if p['deliveryCompletedAt'] else None
                created_at = p['createdAt'].isoformat() if p['createdAt'] else None
                
                item = {
                    'id': p['id'],
                    'status': 'IN_PROGRESS',
                    'productName': p['productName'],
                    'recipientName': p['recipientName'],
                    'recipientPhone': p['recipientPhone'],
                    'recipientAddr': p['recipientAddr'],
                    'deliveryCompletedAt': completed_at,
                    'createdAt': created_at,
                    'ownerId': p['ownerId'],
                    'ownerName': p.get('ownerName'),
                    'size': p['size']
                }
                result.append(item)
            
            return result
    except Exception as e:
        logging.error(f"DB 쿼리 오류: {e}")
        return []
    finally:
        conn.close()

def get_current_driver_location(driver_id):
    if driver_hub_status.get(driver_id, False):
        logging.info(f"배달 기사 {driver_id} 허브 도착 완료 상태")
        return HUB_LOCATION

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            sql = """
            SELECT recipientAddr, deliveryCompletedAt
            FROM Parcel
            WHERE deliveryDriverId = %s 
            AND status = 'DELIVERY_COMPLETED'
            AND DATE(deliveryCompletedAt) = CURDATE()
            AND isDeleted = 0
            ORDER BY deliveryCompletedAt DESC
            LIMIT 1
            """
            cursor.execute(sql, (driver_id,))
            last_completed = cursor.fetchone()
            
            if last_completed:
                address = last_completed['recipientAddr']
                lat, lon, _ = kakao_geocoding(address)
                logging.info(f"배달 기사 {driver_id} 현재 위치: {address} -> ({lat}, {lon})")
                return {"lat": lat, "lon": lon}
    
    except Exception as e:
        logging.error(f"현재 위치 계산 오류: {e}")
    finally:
        conn.close()

    logging.info(f"배달 기사 {driver_id} 기본 위치: 허브")
    return HUB_LOCATION
        
def convert_pickup_to_delivery_in_db(pickup_id):
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            sql = """
            UPDATE Parcel 
            SET status = 'DELIVERY_PENDING' 
            WHERE id = %s 
            AND status = 'PICKUP_COMPLETED'
            AND isDeleted = 0
            """
            cursor.execute(sql, (pickup_id,))
        conn.commit()
        return cursor.rowcount > 0
    except Exception as e:
        logging.error(f"DB 쿼리 오류: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def assign_delivery_driver_in_db(delivery_id, driver_id):
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            sql = """
            UPDATE Parcel 
            SET deliveryDriverId = %s,
                isNextDeliveryTarget = TRUE
            WHERE id = %s 
            AND status = 'DELIVERY_PENDING'
            AND isDeleted = 0
            """
            cursor.execute(sql, (driver_id, delivery_id))
        conn.commit()
        return cursor.rowcount > 0
    except Exception as e:
        logging.error(f"DB 쿼리 오류: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def complete_delivery_in_db(delivery_id):
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            sql = """
            UPDATE Parcel 
            SET status = 'DELIVERY_COMPLETED',
                isNextDeliveryTarget = FALSE,
                deliveryCompletedAt = NOW()
            WHERE id = %s 
            AND status = 'DELIVERY_PENDING'
            AND isDeleted = 0
            """
            cursor.execute(sql, (delivery_id,))
        conn.commit()
        return cursor.rowcount > 0
    except Exception as e:
        logging.error(f"DB 쿼리 오류: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def kakao_geocoding(address):
    try:
        headers = {"Authorization": f"KakaoAK {KAKAO_API_KEY}"}

        params = {"query": address}
        response = requests.get(KAKAO_ADDRESS_API, headers=headers, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            documents = data.get("documents", [])
            
            if documents:
                doc = documents[0]
                lat = float(doc["y"])
                lon = float(doc["x"])
                address_name = doc.get("address_name", address)
                
                logging.info(f"카카오 주소 검색 성공: {address} -> ({lat}, {lon}) [{address_name}]")
                return lat, lon, address_name

        response = requests.get(KAKAO_KEYWORD_API, headers=headers, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            documents = data.get("documents", [])
            
            if documents:
                doc = documents[0]
                lat = float(doc["y"])
                lon = float(doc["x"])
                place_name = doc.get("place_name", address)
                
                logging.info(f"카카오 키워드 검색 성공: {address} -> ({lat}, {lon}) [{place_name}]")
                return lat, lon, place_name

        logging.warning(f"카카오 지오코딩 실패, 기본 좌표 사용: {address}")
        return get_default_coordinates_by_district(address)
        
    except Exception as e:
        logging.error(f"카카오 지오코딩 오류: {e}")
        return get_default_coordinates_by_district(address)

def extract_district_from_kakao_geocoding(address):
    try:
        headers = {"Authorization": f"KakaoAK {KAKAO_API_KEY}"}
        params = {"query": address}

        response = requests.get(KAKAO_ADDRESS_API, headers=headers, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            documents = data.get("documents", [])
            
            if documents:
                doc = documents[0]

                address_info = doc.get("address", {})
                if address_info:
                    district = address_info.get("region_2depth_name", "")
                    if district and district.endswith("구"):
                        logging.info(f"카카오 API로 구 추출 성공: {address} -> {district}")
                        return district

                road_address = doc.get("road_address", {})
                if road_address:
                    district = road_address.get("region_2depth_name", "")
                    if district and district.endswith("구"):
                        logging.info(f"카카오 API로 구 추출 성공 (도로명): {address} -> {district}")
                        return district

        address_parts = address.split()
        for part in address_parts:
            if part.endswith('구'):
                logging.info(f"텍스트에서 구 추출: {address} -> {part}")
                return part
        
        logging.warning(f"구 정보 추출 실패: {address}")
        return None
        
    except Exception as e:
        logging.error(f"구 추출 오류: {e}")
        address_parts = address.split()
        for part in address_parts:
            if part.endswith('구'):
                return part
        return None

def address_to_coordinates(address):
    lat, lon, _ = kakao_geocoding(address)
    return lat, lon

def get_default_coordinates_by_district(address):
    district_coords = {
        "강남구": (37.5172, 127.0473, "강남구 역삼동"),
        "서초구": (37.4837, 127.0324, "서초구 서초동"),
        "송파구": (37.5145, 127.1059, "송파구 잠실동"),
        "강동구": (37.5301, 127.1238, "강동구 천호동"),
        "성동구": (37.5634, 127.0369, "성동구 성수동"),
        "광진구": (37.5384, 127.0822, "광진구 광장동"),
        "동대문구": (37.5744, 127.0396, "동대문구 전농동"),
        "중랑구": (37.6063, 127.0927, "중랑구 면목동"),
        "종로구": (37.5735, 126.9790, "종로구 종로"),
        "중구": (37.5641, 126.9979, "중구 명동"),
        "용산구": (37.5311, 126.9810, "용산구 한강로"),
        "성북구": (37.5894, 127.0167, "성북구 성북동"),
        "강북구": (37.6396, 127.0253, "강북구 번동"),
        "도봉구": (37.6687, 127.0472, "도봉구 방학동"),
        "노원구": (37.6543, 127.0568, "노원구 상계동"),
        "은평구": (37.6176, 126.9269, "은평구 불광동"),
        "서대문구": (37.5791, 126.9368, "서대문구 신촌동"),
        "마포구": (37.5638, 126.9084, "마포구 공덕동"),
        "양천구": (37.5170, 126.8667, "양천구 목동"),
        "강서구": (37.5509, 126.8496, "강서구 화곡동"),
        "구로구": (37.4954, 126.8877, "구로구 구로동"),
        "금천구": (37.4564, 126.8955, "금천구 가산동"),
        "영등포구": (37.5263, 126.8966, "영등포구 영등포동"),
        "동작구": (37.5124, 126.9393, "동작구 상도동"),
        "관악구": (37.4784, 126.9516, "관악구 봉천동")
    }
    
    for district, (lat, lon, name) in district_coords.items():
        if district in address:
            logging.info(f"기본 좌표 사용: {address} -> ({lat}, {lon}) [{name}]")
            return lat, lon, name

    logging.warning(f"구를 찾을 수 없어 서울시청 좌표 사용: {address}")
    return 37.5665, 126.9780, "서울시청"

def extract_waypoints_from_route(route_info):
    """Valhalla route 응답에서 waypoints와 coordinates 추출"""
    waypoints = []
    coordinates = []
    
    try:
        if not route_info or 'trip' not in route_info:
            return waypoints, coordinates
        
        trip = route_info['trip']
        if 'legs' not in trip or not trip['legs']:
            return waypoints, coordinates
            
        leg = trip['legs'][0]
        maneuvers = leg.get('maneuvers', [])

        if 'shape' in leg and leg['shape']:
            try:
                decoded_coords = polyline.decode(leg['shape'], precision = 6)
                coordinates = [{"lat": lat, "lon": lon} for lat, lon in decoded_coords]
                logging.info(f"Decoded {len(coordinates)} coordinates from shape")
            except Exception as e:
                logging.error(f"Shape decoding error: {e}")
                coordinates = []

        for i, maneuver in enumerate(maneuvers):
            instruction = maneuver.get('instruction', f'구간 {i+1}')
            street_names = maneuver.get('street_names', [])
            street_name = street_names[0] if street_names else f'구간{i+1}'

            begin_idx = maneuver.get('begin_shape_index', 0)
            
            if coordinates and begin_idx < len(coordinates):
                lat = coordinates[begin_idx]["lat"]
                lon = coordinates[begin_idx]["lon"]
            else:
                lat = 0.0
                lon = 0.0
            
            waypoint = {
                "lat": lat,
                "lon": lon,
                "name": street_name,
                "instruction": instruction
            }
            waypoints.append(waypoint)
        
        logging.info(f"Extracted {len(waypoints)} waypoints and {len(coordinates)} coordinates")
        
    except Exception as e:
        logging.error(f"Error extracting waypoints: {e}")
    
    return waypoints, coordinates

def calculate_optimal_next_destination(locations, current_location):
   try:
       location_coords = [{"lat": loc["lat"], "lon": loc["lon"]} for loc in locations]
       time_matrix, _ = get_enhanced_time_distance_matrix(location_coords, costing=COSTING_MODEL)
       
       if time_matrix is not None:
           response = requests.post(
               LKH_SERVICE_URL,
               json={"matrix": time_matrix.tolist()}
           )
           
           if response.status_code == 200:
               result = response.json()
               optimal_tour = result.get("tour")
               
               if optimal_tour and len(optimal_tour) > 1:
                   next_idx = None
                   for idx in optimal_tour[1:]:
                       if idx != 0:
                           next_idx = idx
                           break

                   if next_idx is None and len(locations) > 1:
                       next_idx = 1
                       
                   if next_idx is not None:
                       next_location = locations[next_idx]

                       route_info = get_turn_by_turn_route(
                           current_location,
                           {"lat": next_location["lat"], "lon": next_location["lon"]},
                           costing=COSTING_MODEL
                       )

                       waypoints, coordinates = extract_waypoints_from_route(route_info)
                       if not waypoints:
                           waypoints = [
                               {
                                   "lat": current_location["lat"],
                                   "lon": current_location["lon"],
                                   "name": "현재위치",
                                   "instruction": "배달 시작"
                               },
                               {
                                   "lat": next_location["lat"],
                                   "lon": next_location["lon"],
                                   "name": next_location["name"],
                                   "instruction": "목적지 도착"
                               }
                           ]
                           coordinates = [
                               {"lat": current_location["lat"], "lon": current_location["lon"]},
                               {"lat": next_location["lat"], "lon": next_location["lon"]}
                           ]

                       if route_info and 'trip' in route_info:
                           route_info['waypoints'] = waypoints
                           route_info['coordinates'] = coordinates
                       
                       return next_location, route_info, "LKH_TSP"

       next_location = locations[1] if len(locations) > 1 else locations[0]
       route_info = get_turn_by_turn_route(
           current_location,
           {"lat": next_location["lat"], "lon": next_location["lon"]},
           costing=COSTING_MODEL
       )
       
       waypoints, coordinates = extract_waypoints_from_route(route_info)
       if route_info and 'trip' in route_info:
           route_info['waypoints'] = waypoints
           route_info['coordinates'] = coordinates
       
       return next_location, route_info, "nearest"
       
   except Exception as e:
       logging.error(f"TSP 계산 오류: {e}")
       fallback_location = locations[1] if len(locations) > 1 else locations[0]
       return fallback_location, None, "fallback"

@app.route('/api/delivery/import', methods=['POST'])
def import_todays_pickups():
    try:
        completed_pickups = get_completed_pickups_today_from_db()
        
        converted_count = 0
        district_stats = {}
        
        for pickup in completed_pickups:
            if convert_pickup_to_delivery_in_db(pickup['id']):
                converted_count += 1

                address = pickup['recipientAddr']
                district = extract_district_from_kakao_geocoding(address)
                if district:
                    district_stats[district] = district_stats.get(district, 0) + 1
                else:
                    for part in address.split():
                        if part.endswith('구'):
                            district_stats[part] = district_stats.get(part, 0) + 1
                            break
        
        return jsonify({
            "status": "success",
            "converted": converted_count,
            "by_district": district_stats,
            "geocoding_method": "kakao"
        }), 200
        
    except Exception as e:
        logging.error(f"Error importing pickups: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/delivery/assign', methods=['POST'])
def assign_to_drivers():
    try:
        unassigned = get_unassigned_deliveries_today_from_db()

        district_deliveries = {}
        for delivery in unassigned:
            address = delivery['recipientAddr']

            district = extract_district_from_kakao_geocoding(address)
            
            if not district:
                for part in address.split():
                    if part.endswith('구'):
                        district = part
                        break
            
            if district:
                if district not in district_deliveries:
                    district_deliveries[district] = []
                district_deliveries[district].append(delivery)
            else:
                logging.warning(f"구 정보 추출 실패: {address}")

        results = {}
        for district, deliveries in district_deliveries.items():
            driver_id = DISTRICT_DRIVER_MAPPING.get(district)
            
            if driver_id:
                assign_count = 0
                for delivery in deliveries:
                    if assign_delivery_driver_in_db(delivery['id'], driver_id):
                        assign_count += 1
                
                results[district] = {
                    "driver_id": driver_id,
                    "count": assign_count
                }
            else:
                logging.warning(f"해당 구에 대응하는 배달 기사 없음: {district}")
        
        return jsonify({
            "status": "success", 
            "assignments": results,
            "geocoding_method": "kakao"
        }), 200
        
    except Exception as e:
        logging.error(f"Error assigning deliveries: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/delivery/next', methods=['GET'])
@auth_required
def get_next_delivery():
    try:
        driver_info = get_current_driver()
        driver_id = driver_info['user_id']

        current_time = datetime.now(KST).time()
        if current_time < DELIVERY_START_TIME:
            hours_left = DELIVERY_START_TIME.hour - current_time.hour
            minutes_left = DELIVERY_START_TIME.minute - current_time.minute
            if minutes_left < 0:
                hours_left -= 1
                minutes_left += 60
            
            return jsonify({
                "status": "waiting",
                "message": f"배달은 오후 3시부터 시작됩니다. {hours_left}시간 {minutes_left}분 남았습니다.",
                "start_time": "15:00",
                "current_time": current_time.strftime("%H:%M")
            }), 200

        pending_deliveries = get_real_pending_deliveries(driver_id)

        current_location = get_current_driver_location(driver_id)

        if not pending_deliveries:
            current_time = datetime.now(KST).time()

            if driver_hub_status.get(driver_id, False):
                return jsonify({
                    "status": "at_hub",
                    "message": "허브에 도착했습니다. 수고하셨습니다!",
                    "current_location": current_location,
                    "remaining": 0,
                    "is_last": True
                }), 200

            route_info = get_turn_by_turn_route(
                current_location,
                HUB_LOCATION,
                costing=COSTING_MODEL
            )

            waypoints, coordinates = extract_waypoints_from_route(route_info)
            if not waypoints:
                waypoints = [
                    {
                        "lat": current_location["lat"],
                        "lon": current_location["lon"],
                        "name": current_location.get("name", "현재위치"),
                        "instruction": "허브로 복귀 시작"
                    },
                    {
                        "lat": HUB_LOCATION["lat"],
                        "lon": HUB_LOCATION["lon"],
                        "name": HUB_LOCATION["name"],
                        "instruction": "허브 도착"
                    }
                ]
                coordinates = [
                    {"lat": current_location["lat"], "lon": current_location["lon"]},
                    {"lat": HUB_LOCATION["lat"], "lon": HUB_LOCATION["lon"]}
                ]

            if route_info and 'trip' in route_info:
                route_info['waypoints'] = waypoints
                route_info['coordinates'] = coordinates
            
            return jsonify({
                "status": "return_to_hub",
                "message": "모든 배달이 완료되었습니다. 허브로 복귀해주세요.",
                "next_destination": HUB_LOCATION,
                "route": route_info,
                "is_last": True,
                "remaining": 0,
                "current_location": current_location,
                "distance_to_hub": route_info['trip']['summary']['length'] if route_info else 0
            }), 200

        if pending_deliveries and driver_hub_status.get(driver_id, False):
            driver_hub_status[driver_id] = False
            logging.info(f"배달 기사 {driver_id} 새로운 배달 시작으로 허브 상태 리셋")

        locations = [current_location]
        for delivery in pending_deliveries:
            lat, lon, location_name = kakao_geocoding(delivery['recipientAddr'])
            locations.append({
                "lat": lat,
                "lon": lon,
                "delivery_id": delivery['id'],
                "parcelId": str(delivery['id']),
                "name": delivery.get('productName', ''),
                "productName": delivery.get('productName', ''),
                "address": delivery['recipientAddr'],
                "location_name": location_name,
                "recipientName": delivery.get('recipientName', ''),
                "recipientPhone": delivery.get('recipientPhone', '')
            })
        
        if len(locations) > 1:
            next_location, route_info, algorithm = calculate_optimal_next_destination(locations, current_location)
            
            return jsonify({
                "status": "success",
                "next_destination": {
                    "lat": next_location["lat"],
                    "lon": next_location["lon"],
                    "delivery_id": next_location.get("delivery_id"),
                    "parcelId": next_location.get("parcelId"),
                    "name": next_location.get("productName"),
                    "productName": next_location.get("productName"),
                    "address": next_location.get("address"),
                    "location_name": next_location.get("location_name"),
                    "recipientName": next_location.get("recipientName"),
                    "recipientPhone": next_location.get("recipientPhone")
                },
                "route": route_info,
                "is_last": False,
                "remaining": len(pending_deliveries),
                "current_location": current_location,
                "algorithm_used": algorithm,
                "geocoding_method": "kakao"
            }), 200
            
        next_location = locations[1] if len(locations) > 1 else HUB_LOCATION
        route_info = get_turn_by_turn_route(
            current_location,
            {"lat": next_location["lat"], "lon": next_location["lon"]},
            costing=COSTING_MODEL
        )
        
        waypoints, coordinates = extract_waypoints_from_route(route_info)
        if route_info and 'trip' in route_info:
            route_info['waypoints'] = waypoints
            route_info['coordinates'] = coordinates
        
        return jsonify({
            "status": "success",
            "next_destination": next_location,
            "route": route_info,
            "is_last": False,
            "remaining": len(pending_deliveries),
            "current_location": current_location,
            "geocoding_method": "kakao"
        }), 200
        
    except Exception as e:
        logging.error(f"Error getting next delivery: {e}", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500
     
@app.route('/api/delivery/complete', methods=['POST'])
@auth_required
def complete_delivery():
    try:
        driver_info = get_current_driver()
        driver_id = driver_info['user_id']
        
        data = request.json
        delivery_id = data.get('deliveryId')
        
        if not delivery_id:
            return jsonify({"error": "deliveryId required"}), 400

        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT deliveryDriverId FROM Parcel WHERE id = %s", (delivery_id,))
                parcel = cursor.fetchone()
                
                if not parcel or parcel['deliveryDriverId'] != driver_id:
                    return jsonify({"error": "권한이 없습니다"}), 403
        finally:
            conn.close()

        if complete_delivery_in_db(delivery_id):
            logging.info(f"배달 완료: 기사 {driver_id}, 배달 {delivery_id}")

            remaining_deliveries = get_real_pending_deliveries(driver_id)
            
            return jsonify({
                "status": "success",
                "message": "배달이 완료되었습니다",
                "remaining": len(remaining_deliveries),
                "completed_at": datetime.now(KST).isoformat()
            }), 200
        else:
            return jsonify({"error": "완료 처리 실패"}), 500
            
    except Exception as e:
        logging.error(f"배달 완료 오류: {e}", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500

@app.route('/api/delivery/hub-arrived', methods=['POST'])
@auth_required
def hub_arrived():
    try:
        driver_info = get_current_driver()
        driver_id = driver_info['user_id']

        if driver_id not in [6, 7, 8, 9, 10]:
            return jsonify({"error": "배달 기사만 접근 가능합니다"}), 403

        pending_deliveries = get_real_pending_deliveries(driver_id)
        
        if pending_deliveries:
            return jsonify({
                "error": "아직 완료하지 않은 배달이 있습니다",
                "remaining_deliveries": len(pending_deliveries)
            }), 400

        driver_hub_status[driver_id] = True
        
        return jsonify({
            "status": "success",
            "message": "허브 도착이 완료되었습니다. 수고하셨습니다!",
            "location": HUB_LOCATION,
            "arrival_time": datetime.now(KST).strftime("%H:%M")
        }), 200
            
    except Exception as e:
        logging.error(f"Error processing hub arrival: {e}", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500

@app.route('/api/delivery/status')  
def status():
    return jsonify({
        "status": "healthy",
        "geocoding": "kakao",
        "kakao_api_configured": bool(KAKAO_API_KEY and KAKAO_API_KEY != 'YOUR_KAKAO_API_KEY_HERE')
    })

@app.route('/api/debug/db-check')
def check_db_connection():
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT status, COUNT(*) as count 
                FROM Parcel 
                WHERE isDeleted = 0
                GROUP BY status
            """)
            status_counts = cursor.fetchall()

            cursor.execute("SELECT CURDATE() as today")
            today = cursor.fetchone()

            cursor.execute("""
                SELECT 
                    COUNT(CASE WHEN status = 'PICKUP_COMPLETED' AND DATE(pickupCompletedAt) = CURDATE() THEN 1 END) as pickup_completed,
                    COUNT(CASE WHEN status = 'DELIVERY_COMPLETED' AND DATE(deliveryCompletedAt) = CURDATE() THEN 1 END) as delivery_completed
                FROM Parcel
                WHERE isDeleted = 0
            """)
            today_counts = cursor.fetchone()
        
        conn.close()
        
        return jsonify({
            "status": "success",
            "connection": "ok",
            "today": today['today'].isoformat() if today else None,
            "status_counts": status_counts,
            "today_counts": today_counts,
            "geocoding": "kakao"
        }), 200
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"DB connection failed: {str(e)}"
        }), 500

@app.route('/api/debug/kakao-test', methods=['POST'])
def test_kakao_geocoding():
    """카카오 지오코딩 테스트 엔드포인트"""
    try:
        data = request.json
        address = data.get('address', '')
        
        if not address:
            return jsonify({"error": "address is required"}), 400

        lat, lon, location_name = kakao_geocoding(address)

        district = extract_district_from_kakao_geocoding(address)

        driver_id = DISTRICT_DRIVER_MAPPING.get(district) if district else None
        
        return jsonify({
            "input_address": address,
            "coordinates": {"lat": lat, "lon": lon},
            "location_name": location_name,
            "extracted_district": district,
            "assigned_driver": driver_id,
            "api_status": "ok" if KAKAO_API_KEY and KAKAO_API_KEY != 'YOUR_KAKAO_API_KEY_HERE' else "api_key_needed"
        }), 200
        
    except Exception as e:
        logging.error(f"카카오 지오코딩 테스트 오류: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5002))
    host = os.environ.get("HOST", "0.0.0.0")
    
    logging.info(f"Starting delivery service on {host}:{port}")
    logging.info(f"카카오 API 설정: {'OK' if KAKAO_API_KEY and KAKAO_API_KEY != 'YOUR_KAKAO_API_KEY_HERE' else 'API KEY 필요'}")
    app.run(host=host, port=port, debug=False)