import requests
import json
import time
import logging
import argparse
import os

parser = argparse.ArgumentParser(description="Valhalla 경로 유틸리티")
parser.add_argument("--host", default=os.environ.get("VALHALLA_HOST", "localhost"), 
                    help="Valhalla 호스트 (기본값: localhost 또는 환경변수 VALHALLA_HOST)")
parser.add_argument("--port", type=int, default=int(os.environ.get("VALHALLA_PORT", "8002")), 
                    help="Valhalla 포트 (기본값: 8002 또는 환경변수 VALHALLA_PORT)")
args = parser.parse_args()

logging.basicConfig(level=logging.INFO)

def get_turn_by_turn_route(start_loc, end_loc, costing="auto", use_traffic=True):
    if not start_loc or not end_loc:
         logging.error("Start and end locations are required.")
         return None

    host = os.environ.get("VALHALLA_HOST", args.host)
    port = int(os.environ.get("VALHALLA_PORT", args.port))
    valhalla_url = f"http://{host}:{port}"

    payload = {
        "locations": [start_loc, end_loc],
        "costing": costing,
        "directions_options": {
            "units": "kilometers",
            "language": "ko-KR",
            "narrative": True,
            "banner_instructions": True,
            "voice_instructions": True
        },
        "costing_options": {
            costing: {
                "use_live_traffic": use_traffic
            }
        },
        "directions_type": "maneuvers",
        "shape_match": "edge_walk",
        "filters": {
            "attributes": ["edge.way_id", "edge.names", "edge.length"],
            "action": "include"
        }
    }

    headers = {'Content-type': 'application/json'}
    max_retries = 3
    retry_delay = 2
    timeout_seconds = 30

    for attempt in range(max_retries):
        try:
            logging.info(f"Requesting route from {start_loc} to {end_loc} (Attempt {attempt+1}/{max_retries})...")
            logging.info(f"교통량 데이터 사용: {use_traffic}")
            response = requests.post(f"{valhalla_url}/route", json=payload, headers=headers, timeout=timeout_seconds)
            response.raise_for_status()
            route_data = response.json()

            if 'trip' not in route_data:
                 logging.warning(f"Valhalla response successful but missing 'trip' data: {route_data}")
                 return None
            return route_data

        except requests.exceptions.Timeout:
             logging.error(f"Valhalla /route API request timed out after {timeout_seconds}s (Attempt {attempt + 1}/{max_retries}).")
        except requests.exceptions.RequestException as e:
            logging.error(f"Error querying Valhalla /route API (Attempt {attempt + 1}/{max_retries}): {e}")
        except json.JSONDecodeError as e:
             logging.error(f"Error decoding Valhalla route response: {e}")
             try:
                 logging.error(f"Response text: {response.text}")
             except:
                 pass
             return None
        except Exception as e:
             logging.error(f"Unexpected error during route calculation: {e}", exc_info=True)
             return None

        if attempt < max_retries - 1:
            logging.info(f"Retrying in {retry_delay} seconds...")
            time.sleep(retry_delay)
        else:
            logging.error("Max retries reached. Failed to get route.")
            return None