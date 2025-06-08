import requests
import json
import numpy as np
import logging
import os
import pymysql
from datetime import datetime, timedelta, time as datetime_time
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

HUB_LOCATION = {"lat": 37.5299, "lon": 126.9648, "name": "용산역"}
COSTING_MODEL = "auto"
BACKEND_API_URL = os.environ.get("BACKEND_API_URL", "http://backend:8080")
LKH_SERVICE_URL = os.environ.get("LKH_SERVICE_URL", "http://lkh:5001/solve")
VALHALLA_HOST = os.environ.get("VALHALLA_HOST", "traffic-proxy")
VALHALLA_PORT = os.environ.get("VALHALLA_PORT", "8003")

driver_hub_status = {}

KST = pytz.timezone('Asia/Seoul')
PICKUP_START_TIME = datetime_time(7, 0)
PICKUP_CUTOFF_TIME = datetime_time(12, 0)

DISTRICT_DRIVER_MAPPING = {
   "은평구": 1, "서대문구": 1, "마포구": 1,

   "도봉구": 2, "노원구": 2, "강북구": 2, "성북구": 2,

   "종로구": 3, "중구": 3, "용산구": 3,

   "강서구": 4, "양천구": 4, "구로구": 4, "영등포구": 4, 
   "동작구": 4, "관악구": 4, "금천구": 4,
   
   "성동구": 5, "광진구": 5, "동대문구": 5, "중랑구": 5, 
   "강동구": 5, "송파구": 5, "강남구": 5, "서초구": 5
}

app = Flask(__name__)

def get_db_connection():
   return pymysql.connect(
       host=os.environ.get("MYSQL_HOST", "subtrack-rds.cv860smoa37l.ap-northeast-2.rds.amazonaws.com"),
       user=os.environ.get("MYSQL_USER", "admin"),
       password=os.environ.get("MYSQL_PASSWORD", "adminsubtrack"),
       db=os.environ.get("MYSQL_DATABASE", "subtrack"),
       charset='utf8mb4',
       cursorclass=pymysql.cursors.DictCursor
   )

def get_parcel_from_db(parcel_id):
   conn = get_db_connection()
   try:
       with conn.cursor() as cursor:
           sql = """
           SELECT p.*, 
                  o.name as ownerName, 
                  pd.name as pickupDriverName, 
                  dd.name as deliveryDriverName
           FROM Parcel p
           LEFT JOIN User o ON p.ownerId = o.id
           LEFT JOIN User pd ON p.pickupDriverId = pd.id
           LEFT JOIN User dd ON p.deliveryDriverId = dd.id
           WHERE p.id = %s AND p.isDeleted = 0
           """
           cursor.execute(sql, (parcel_id,))
           parcel = cursor.fetchone()
           
           if parcel:
               if 'pickupDriverId' in parcel:
                   parcel['driverId'] = parcel['pickupDriverId']
               
               for key, value in parcel.items():
                   if isinstance(value, datetime):
                       parcel[key] = value.isoformat()
               
               if parcel['status'] == 'PICKUP_PENDING':
                   parcel['status'] = 'PENDING'
               elif parcel['status'] == 'PICKUP_COMPLETED':
                   parcel['status'] = 'COMPLETED'
               
               return parcel
           return None
   except Exception as e:
       logging.error(f"DB 쿼리 오류: {e}")
       return None
   finally:
       conn.close()

def get_real_pending_pickups(driver_id):
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            today = datetime.now(KST).date()
            sql = """
            SELECT p.*, 
                   o.name as ownerName
            FROM Parcel p
            LEFT JOIN User o ON p.ownerId = o.id
            WHERE p.pickupDriverId = %s 
            AND p.status = 'PICKUP_PENDING'
            AND p.isDeleted = 0
            AND (
                p.pickupScheduledDate IS NULL OR 
                DATE(p.pickupScheduledDate) <= %s
            )
            ORDER BY p.createdAt DESC
            """
            cursor.execute(sql, (driver_id, today))
            parcels = cursor.fetchall()

            result = []
            for p in parcels:
                completed_at = p['pickupCompletedAt'].isoformat() if p['pickupCompletedAt'] else None
                created_at = p['createdAt'].isoformat() if p['createdAt'] else None
                
                item = {
                    'id': p['id'],
                    'status': 'PENDING',
                    'recipientAddr': p['recipientAddr'],
                    'productName': p['productName'],
                    'pickupCompletedAt': completed_at,
                    'assignedAt': created_at,
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

def get_driver_parcels_from_db(driver_id):
   return get_real_pending_pickups(driver_id)

def get_current_driver_location(driver_id):
    if driver_hub_status.get(driver_id, False):
        logging.info(f"기사 {driver_id} 허브 도착 완료 상태")
        return HUB_LOCATION

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            sql = """
            SELECT recipientAddr, pickupCompletedAt
            FROM Parcel
            WHERE pickupDriverId = %s 
            AND status = 'PICKUP_COMPLETED'
            AND DATE(pickupCompletedAt) = CURDATE()
            AND isDeleted = 0
            ORDER BY pickupCompletedAt DESC
            LIMIT 1
            """
            cursor.execute(sql, (driver_id,))
            last_completed = cursor.fetchone()
            
            if last_completed:
                address = last_completed['recipientAddr']
                lat, lon = address_to_coordinates(address)
                logging.info(f"기사 {driver_id} 현재 위치: {address} -> ({lat}, {lon})")
                return {"lat": lat, "lon": lon}
    
    except Exception as e:
        logging.error(f"현재 위치 계산 오류: {e}")
    finally:
        conn.close()

    logging.info(f"기사 {driver_id} 기본 위치: 허브")
    return HUB_LOCATION

def assign_driver_to_parcel_in_db(parcel_id, driver_id):
   conn = get_db_connection()
   try:
       with conn.cursor() as cursor:
           sql = """
           UPDATE Parcel 
           SET pickupDriverId = %s, 
               status = 'PICKUP_PENDING', 
               isNextPickupTarget = TRUE,
               pickupScheduledDate = CURDATE()
           WHERE id = %s AND isDeleted = 0
           """
           cursor.execute(sql, (driver_id, parcel_id))
       conn.commit()
       return cursor.rowcount > 0
   except Exception as e:
       logging.error(f"DB 쿼리 오류: {e}")
       conn.rollback()
       return False
   finally:
       conn.close()

def assign_driver_to_parcel_for_tomorrow(parcel_id, tomorrow_date):
   conn = get_db_connection()
   try:
       with conn.cursor() as cursor:
           parcel = get_parcel_from_db(parcel_id)
           if not parcel:
               return False
           
           address = parcel.get('recipientAddr', '')
           address_parts = address.split()
           district = None
           for part in address_parts:
               if part.endswith('구'):
                   district = part
                   break
           
           if not district:
               return False
           
           driver_id = DISTRICT_DRIVER_MAPPING.get(district)
           if not driver_id:
               return False

           sql = """
           UPDATE Parcel 
           SET pickupDriverId = %s, 
               status = 'PICKUP_PENDING',
               pickupScheduledDate = %s,
               isNextPickupTarget = FALSE
           WHERE id = %s AND isDeleted = 0
           """
           cursor.execute(sql, (driver_id, tomorrow_date, parcel_id))
       conn.commit()
       return cursor.rowcount > 0
   except Exception as e:
       logging.error(f"DB 쿼리 오류: {e}")
       conn.rollback()
       return False
   finally:
       conn.close()

def complete_parcel_in_db(parcel_id):
   conn = get_db_connection()
   try:
       with conn.cursor() as cursor:
           sql = """
           UPDATE Parcel 
           SET status = 'PICKUP_COMPLETED', 
               isNextPickupTarget = FALSE,
               pickupCompletedAt = NOW() 
           WHERE id = %s AND isDeleted = 0
           """
           cursor.execute(sql, (parcel_id,))
       conn.commit()
       return cursor.rowcount > 0
   except Exception as e:
       logging.error(f"DB 쿼리 오류: {e}")
       conn.rollback()
       return False
   finally:
       conn.close()

def get_completed_pickups_today_from_db():
   conn = get_db_connection()
   try:
       with conn.cursor() as cursor:
           sql = """
           SELECT p.*, 
                  o.name as ownerName
           FROM Parcel p
           LEFT JOIN User o ON p.ownerId = o.id
           WHERE p.status = 'PICKUP_COMPLETED' 
           AND DATE(p.pickupCompletedAt) = CURDATE()
           AND p.isDeleted = 0
           """
           cursor.execute(sql)
           parcels = cursor.fetchall()

           result = []
           for p in parcels:
               completed_at = p['pickupCompletedAt'].isoformat() if p['pickupCompletedAt'] else None
               created_at = p['createdAt'].isoformat() if p['createdAt'] else None
               
               item = {
                   'id': p['id'],
                   'status': 'COMPLETED',
                   'recipientAddr': p['recipientAddr'],
                   'productName': p['productName'],
                   'pickupCompletedAt': completed_at,
                   'assignedAt': created_at,
                   'ownerId': p['ownerId'],
                   'ownerName': p.get('ownerName'),
                   'pickupDriverId': p['pickupDriverId'],
                   'size': p['size']
               }
               result.append(item)
           
           return result
   except Exception as e:
       logging.error(f"DB 쿼리 오류: {e}")
       return []
   finally:
       conn.close()

def address_to_coordinates(address):
   try:
       url = f"http://{VALHALLA_HOST}:{VALHALLA_PORT}/search"
       params = {
           "text": address,
           "focus.point.lat": 37.5665,
           "focus.point.lon": 126.9780,
           "boundary.country": "KR",
           "size": 5
       }
       
       response = requests.get(url, params=params, timeout=10)
       
       if response.status_code == 200:
           data = response.json()
           if data.get("features") and len(data["features"]) > 0:
               for feature in data["features"]:
                   coords = feature["geometry"]["coordinates"]
                   confidence = feature.get("properties", {}).get("confidence", 0)

                   if confidence > 0.7:
                       logging.info(f"지오코딩 성공: {address} -> ({coords[1]}, {coords[0]}) 신뢰도: {confidence}")
                       return coords[1], coords[0]

               coords = data["features"][0]["geometry"]["coordinates"]
               logging.info(f"지오코딩 (낮은 신뢰도): {address} -> ({coords[1]}, {coords[0]})")
               return coords[1], coords[0]
       
       logging.warning(f"지오코딩 실패, 기본 좌표 사용: {address}")
       return get_default_coordinates(address)
           
   except Exception as e:
       logging.error(f"지오코딩 오류: {e}")
       return get_default_coordinates(address)

def get_default_coordinates(address):
   district_coords = {
       "강남구": (37.5172, 127.0473),
       "서초구": (37.4837, 127.0324),
       "송파구": (37.5145, 127.1059),
       "강동구": (37.5301, 127.1238),
       "성동구": (37.5634, 127.0369),
       "광진구": (37.5384, 127.0822),
       "동대문구": (37.5744, 127.0396),
       "중랑구": (37.6063, 127.0927),
       "종로구": (37.5735, 126.9790),
       "중구": (37.5641, 126.9979),
       "용산구": (37.5311, 126.9810),
       "성북구": (37.5894, 127.0167),
       "강북구": (37.6396, 127.0253),
       "도봉구": (37.6687, 127.0472),
       "노원구": (37.6543, 127.0568),
       "은평구": (37.6176, 126.9269),
       "서대문구": (37.5791, 126.9368),
       "마포구": (37.5638, 126.9084),
       "양천구": (37.5170, 126.8667),
       "강서구": (37.5509, 126.8496),
       "구로구": (37.4954, 126.8877),
       "금천구": (37.4564, 126.8955),
       "영등포구": (37.5263, 126.8966),
       "동작구": (37.5124, 126.9393),
       "관악구": (37.4784, 126.9516)
   }
   
   for district, coords in district_coords.items():
       if district in address:
           return coords
   
   return (37.5665, 126.9780)

def extract_waypoints_from_route(route_info):
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
       time_matrix, _ = get_time_distance_matrix(location_coords, costing=COSTING_MODEL, use_traffic=True)
       
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
                                   "instruction": "수거 시작"
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

@app.route('/api/pickup/webhook', methods=['POST'])
def webhook_new_pickup():
   try:
       data = request.json
       parcel_id = data.get('parcelId')
       
       if not parcel_id:
           return jsonify({"error": "parcelId is required"}), 400

       current_time = datetime.now(KST).time()
       current_date = datetime.now(KST).date()
       
       if current_time >= PICKUP_CUTOFF_TIME:
           logging.info(f"수거 요청 마감 시간 후 접수 - 내일로 처리: {parcel_id}")

           tomorrow = current_date + timedelta(days=1)
           
           if assign_driver_to_parcel_for_tomorrow(parcel_id, tomorrow):
               return jsonify({
                   "status": "scheduled_tomorrow", 
                   "message": "정오 12시 이후 요청은 다음날 수거로 처리됩니다.",
                   "scheduled_date": tomorrow.isoformat(),
                   "cutoff_time": "12:00",
                   "current_time": current_time.strftime("%H:%M")
               }), 200
           else:
               return jsonify({"error": "Failed to schedule for tomorrow"}), 500

       parcel = get_parcel_from_db(parcel_id)
       if not parcel:
           return jsonify({"error": "Parcel not found"}), 404

       if parcel.get('driverId') or parcel.get('pickupDriverId'):
           return jsonify({"status": "already_processed"}), 200

       address = parcel.get('recipientAddr', '')
       lat, lon = address_to_coordinates(address)

       address_parts = address.split()
       district = None
       for part in address_parts:
           if part.endswith('구'):
               district = part
               break
       
       if not district:
           return jsonify({"error": "Could not determine district"}), 400

       driver_id = DISTRICT_DRIVER_MAPPING.get(district)
       if not driver_id:
           return jsonify({
               "status": "error",
               "message": f"No driver for district {district}"
           }), 500

       if assign_driver_to_parcel_in_db(parcel_id, driver_id):
           return jsonify({
               "status": "success",
               "parcelId": parcel_id,
               "district": district,
               "driverId": driver_id,
               "coordinates": {"lat": lat, "lon": lon},
               "scheduled_for": "today"
           }), 200
       else:
           return jsonify({"error": "Failed to assign driver"}), 500
               
   except Exception as e:
       logging.error(f"Error processing webhook: {e}", exc_info=True)
       return jsonify({"error": "Internal server error"}), 500

@app.route('/api/pickup/hub-arrived', methods=['POST'])
@auth_required
def hub_arrived():
    try:
        driver_info = get_current_driver()
        driver_id = driver_info['user_id']

        if driver_id not in [1, 2, 3, 4, 5]:
            return jsonify({"error": "수거 기사만 접근 가능합니다"}), 403

        pending_pickups = get_real_pending_pickups(driver_id)
        
        if pending_pickups:
            return jsonify({
                "error": "아직 완료하지 않은 수거가 있습니다",
                "remaining_pickups": len(pending_pickups)
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

@app.route('/api/pickup/next', methods=['GET'])
@auth_required
def get_next_destination():
   try:
       driver_info = get_current_driver()
       driver_id = driver_info['user_id']

       if driver_id not in [1, 2, 3, 4, 5]:
           return jsonify({"error": "수거 기사만 접근 가능합니다"}), 403
       
       current_time = datetime.now(KST).time()
       if current_time < PICKUP_START_TIME:
           hours_left = PICKUP_START_TIME.hour - current_time.hour
           minutes_left = PICKUP_START_TIME.minute - current_time.minute
           if minutes_left < 0:
               hours_left -= 1
               minutes_left += 60
           
           return jsonify({
               "status": "waiting",
               "message": f"수거는 오전 7시부터 시작됩니다. {hours_left}시간 {minutes_left}분 남았습니다.",
               "start_time": "07:00",
               "current_time": current_time.strftime("%H:%M")
           }), 200

       pending_pickups = get_real_pending_pickups(driver_id)

       current_location = get_current_driver_location(driver_id)

       if not pending_pickups:
           current_time = datetime.now(KST).time()

           if driver_hub_status.get(driver_id, False):
               return jsonify({
                   "status": "at_hub",
                   "message": "허브에 도착했습니다. 수고하셨습니다!",
                   "current_location": current_location,
                   "remaining_pickups": 0,
                   "is_last": True
               }), 200
           
           if current_time < PICKUP_CUTOFF_TIME:
               return jsonify({
                   "status": "waiting_for_orders",
                   "message": f"현재 할당된 수거가 없습니다. 신규 요청을 대기 중입니다. (마감: 12:00)",
                   "current_time": current_time.strftime("%H:%M"),
                   "cutoff_time": "12:00",
                   "current_location": current_location,
                   "is_last": False,
                   "remaining_pickups": 0
               }), 200

           else:
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
                           "name": "현재위치",
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
                   "message": "모든 수거가 완료되었습니다. 허브로 복귀해주세요.",
                   "next_destination": HUB_LOCATION,
                   "route": route_info,
                   "is_last": True,
                   "remaining_pickups": 0,
                   "current_location": current_location,
                   "distance_to_hub": route_info['trip']['summary']['length'] if route_info else 0
               }), 200
       
       if pending_pickups and driver_hub_status.get(driver_id, False):
           driver_hub_status[driver_id] = False
           logging.info(f"기사 {driver_id} 새로운 수거 시작으로 허브 상태 리셋")

       locations = [current_location]
       for pickup in pending_pickups:
           lat, lon = address_to_coordinates(pickup['recipientAddr'])
           locations.append({
               "lat": lat,
               "lon": lon,
               "parcel_id": pickup['id'],
               "name": pickup['productName'],
               "address": pickup['recipientAddr']
           })

       if len(locations) > 1:
           next_location, route_info, algorithm = calculate_optimal_next_destination(locations, current_location)
           
           return jsonify({
               "status": "success",
               "next_destination": next_location,
               "route": route_info,
               "is_last": False,
               "remaining_pickups": len(pending_pickups),
               "current_location": current_location,
               "algorithm_used": algorithm
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
           "remaining_pickups": len(pending_pickups),
           "current_location": current_location
       }), 200
           
   except Exception as e:
       logging.error(f"Error getting next destination: {e}", exc_info=True)
       return jsonify({"error": "Internal server error"}), 500
    
@app.route('/api/pickup/complete', methods=['POST'])
@auth_required
def complete_pickup():
   try:
       driver_info = get_current_driver()
       driver_id = driver_info['user_id']
       
       data = request.json
       parcel_id = data.get('parcelId')
       
       if not parcel_id:
           return jsonify({"error": "parcelId is required"}), 400

       parcel = get_parcel_from_db(parcel_id)
       if not parcel or parcel.get('pickupDriverId') != driver_id:
           return jsonify({"error": "권한이 없습니다"}), 403

       if complete_parcel_in_db(parcel_id):
           logging.info(f"수거 완료: 기사 {driver_id}, 소포 {parcel_id}")

           remaining_pickups = get_real_pending_pickups(driver_id)
           
           return jsonify({
               "status": "success",
               "message": "수거가 완료되었습니다",
               "remaining_pickups": len(remaining_pickups),
               "completed_at": datetime.now(KST).isoformat()
           }), 200
       else:
           return jsonify({"error": "완료 처리 실패"}), 500
           
   except Exception as e:
       logging.error(f"수거 완료 오류: {e}", exc_info=True)
       return jsonify({"error": "Internal server error"}), 500

@app.route('/api/pickup/all-completed', methods=['GET'])
def check_all_completed():
    try:
        today = datetime.now(KST).strftime('%Y-%m-%d')

        all_drivers = [1, 2, 3, 4, 5]
        total_pending = 0
        total_completed = 0
        first_pending_driver = None
        first_pending_count = 0
        
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                sql_pending = """
                SELECT pickupDriverId, COUNT(*) as pending_count
                FROM Parcel
                WHERE status = 'PICKUP_PENDING' 
                AND (pickupScheduledDate IS NULL OR DATE(pickupScheduledDate) <= CURDATE())
                AND isDeleted = 0
                GROUP BY pickupDriverId
                """
                cursor.execute(sql_pending)
                pending_results = cursor.fetchall()

                sql_completed = """
                SELECT COUNT(*) as completed_count
                FROM Parcel
                WHERE status = 'PICKUP_COMPLETED'
                AND DATE(pickupCompletedAt) = CURDATE()
                AND isDeleted = 0
                """
                cursor.execute(sql_completed)
                completed_result = cursor.fetchone()

                if pending_results:
                    for result in pending_results:
                        driver_id = result['pickupDriverId']
                        pending_count = result['pending_count']
                        total_pending += pending_count

                        if pending_count > 0 and first_pending_driver is None:
                            first_pending_driver = driver_id
                            first_pending_count = pending_count

                total_completed = completed_result['completed_count'] if completed_result else 0
                
        finally:
            conn.close()

        if total_pending > 0:
            return jsonify({
                "completed": False, 
                "remaining": total_pending,
                "completed_count": total_completed,
                "driver_status": f"Driver {first_pending_driver} has {first_pending_count} pending"
            }), 200

        if total_completed > 0:
            try:
                import_response = requests.post("http://delivery-service:5000/api/delivery/import")
                assign_response = requests.post("http://delivery-service:5000/api/delivery/assign")
                
                return jsonify({
                    "completed": True,
                    "message": "All pickups completed and converted to delivery",
                    "total_converted": total_completed,
                    "import_status": import_response.status_code,
                    "assign_status": assign_response.status_code
                }), 200
                
            except Exception as e:
                logging.error(f"Error converting to delivery: {e}")
                return jsonify({
                    "completed": True,
                    "error": "Failed to convert to delivery",
                    "details": str(e)
                }), 500
        else:
            return jsonify({
                "completed": True,
                "message": "No pickups today",
                "total_completed": 0
            }), 200
            
    except Exception as e:
        logging.error(f"Error checking completion: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/pickup/status')
def status():
   return jsonify({"status": "healthy"})

@app.route('/api/debug/db-check')
def check_db_connection():
   try:
       conn = get_db_connection()
       with conn.cursor() as cursor:
           cursor.execute("SELECT COUNT(*) as count FROM Parcel")
           result = cursor.fetchone()
       conn.close()
       
       return jsonify({
           "status": "success",
           "connection": "ok",
           "total_parcels": result['count']
       }), 200
   except Exception as e:
       return jsonify({
           "status": "error",
           "message": f"DB connection failed: {str(e)}"
       }), 500

if __name__ == "__main__":
   port = int(os.environ.get("PORT", 5000))
   host = os.environ.get("HOST", "0.0.0.0")
   
   logging.info(f"Starting TSP optimization service on {host}:{port}")
   app.run(host=host, port=port, debug=False)