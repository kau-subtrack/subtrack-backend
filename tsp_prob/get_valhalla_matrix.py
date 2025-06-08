import requests
import json
import numpy as np
import time
import logging
import argparse
import os

parser = argparse.ArgumentParser(description="Valhalla 매트릭스 유틸리티")
parser.add_argument("--host", default=os.environ.get("VALHALLA_HOST", "localhost"), 
                    help="Valhalla 호스트 (기본값: localhost 또는 환경변수 VALHALLA_HOST)")
parser.add_argument("--port", type=int, default=int(os.environ.get("VALHALLA_PORT", "8002")), 
                    help="Valhalla 포트 (기본값: 8002 또는 환경변수 VALHALLA_PORT)")
args = parser.parse_args()

logging.basicConfig(level=logging.INFO)

def get_time_distance_matrix(locations, costing="auto", use_traffic=True):
    if not locations or len(locations) < 2:
        logging.error("Error: Need at least two locations for matrix calculation.")
        return None, None

    host = os.environ.get("VALHALLA_HOST", args.host)
    port = int(os.environ.get("VALHALLA_PORT", args.port))
    valhalla_url = f"http://{host}:{port}"

    n = len(locations)
    payload = {
        "sources": locations,
        "targets": locations,
        "costing": costing,
        "units": "kilometers",
        "costing_options": {
            costing: {
                "use_live_traffic": use_traffic
            }
        }
    }

    headers = {'Content-type': 'application/json'}
    max_retries = 3
    retry_delay = 2
    timeout_seconds = 60

    for attempt in range(max_retries):
        try:
            logging.info(f"Requesting matrix from Valhalla at {valhalla_url} (Attempt {attempt + 1}/{max_retries})...")
            logging.info(f"교통량 데이터 사용: {use_traffic}")

            response = requests.post(f"{valhalla_url}/matrix", json=payload, headers=headers, timeout=timeout_seconds)
            response.raise_for_status()
            data = response.json()


            time_matrix = np.full((n, n), -1.0, dtype=float)
            distance_matrix = np.full((n, n), -1.0, dtype=float)
            found_routes = 0

            if 'sources_to_targets' in data:
                for i, source_data in enumerate(data['sources_to_targets']):
                    if source_data:
                        for j, target_data in enumerate(source_data):
                            if target_data and target_data.get('time') is not None and target_data.get('distance') is not None:
                                time_matrix[i, j] = target_data['time']
                                distance_matrix[i, j] = target_data['distance']
                                found_routes += 1
                            else:
                                logging.warning(f"No route found between location {i} and {j}. Assigning large penalty.")
                                time_matrix[i, j] = 9999999
                                distance_matrix[i, j] = 9999999
                    else:
                        logging.warning(f"No target data found for source {i}. Assigning large penalties for this row.")
                        time_matrix[i, :] = 9999999
                        distance_matrix[i, :] = 9999999

            if found_routes == 0:
                logging.error("Failed to calculate any routes between locations.")
                return None, None
            elif np.any(time_matrix == -1.0) or np.any(distance_matrix == -1.0):
                logging.warning("Some routes could not be calculated. Matrix might be incomplete.")

            logging.info("Matrix calculation successful.")
            return time_matrix, distance_matrix

        except requests.exceptions.Timeout:
            logging.error(f"Valhalla API request timed out after {timeout_seconds}s (Attempt {attempt + 1}/{max_retries}).")
        except requests.exceptions.RequestException as e:
            logging.error(f"Error querying Valhalla API (Attempt {attempt + 1}/{max_retries}): {e}")
        except json.JSONDecodeError as e:
            logging.error(f"Error decoding Valhalla response: {e}")
            try:
                logging.error(f"Response text: {response.text}")
            except:
                pass
            return None, None
        except Exception as e:
            logging.error(f"Unexpected error during matrix calculation: {e}", exc_info=True)
            return None, None

        if attempt < max_retries - 1:
            logging.info(f"Retrying in {retry_delay} seconds...")
            time.sleep(retry_delay)
        else:
            logging.error("Max retries reached. Failed to get matrix.")
            return None, None