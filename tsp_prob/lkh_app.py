from flask import Flask, request, jsonify
import numpy as np
import logging
import os
from run_lkh_internal import solve_tsp_with_lkh

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
app = Flask(__name__)

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy"})

@app.route('/solve', methods=['POST'])
def solve_tsp():
    try:
        data = request.json

        if 'distances' in data:
            distances = data['distances']
        elif 'matrix' in data:
            distances = data['matrix']
        else:
            return jsonify({"error": "Missing 'distances' or 'matrix' field"}), 400

        if not isinstance(distances, list) or not all(isinstance(row, list) for row in distances):
            return jsonify({"error": "Invalid distance matrix format"}), 400

        n = len(distances)
        if n == 0 or any(len(row) != n for row in distances):
            return jsonify({"error": "Distance matrix must be square"}), 400

        distance_matrix = np.array(distances)

        if n <= 2:
            logging.info(f"특별 처리: {n}개 노드")
            if n == 1:
                return jsonify({"tour": [0], "tour_length": 0.0})
            else:
                return jsonify({"tour": [0, 1], "tour_length": float(distance_matrix[0][1])})

        if n <= 5:
            default_runs = 3
        elif n <= 10:
            default_runs = 5
        elif n <= 20:
            default_runs = 8
        elif n <= 50:
            default_runs = 12
        else:
            default_runs = 15

        runs = data.get('runs', default_runs)
        max_trials = data.get('max_trials', None)
        time_limit = data.get('time_limit', None)
        seed = data.get('seed', 1)

        logging.info(f"TSP 해결 중 (노드 수: {n}, runs: {runs})")
        
        try:
            tour, tour_length = solve_tsp_with_lkh(
                distance_matrix, 
                runs=runs
            )
            
            if tour is None:
                logging.error(f"LKH 실행 실패: tour is None")
                return jsonify({"error": "LKH solver returned None"}), 500
                
            logging.info(f"TSP 해결 완료: 경로 길이 = {tour_length:.2f}, 노드 수 = {len(tour)}")
            
            return jsonify({
                "tour": tour,
                "tour_length": float(tour_length),
                "nodes": n,
                "runs_used": runs
            })
            
        except Exception as e:
            logging.error(f"LKH 실행 중 오류: {str(e)}", exc_info=True)
            return jsonify({"error": f"LKH execution error: {str(e)}"}), 500
        
    except Exception as e:
        logging.error(f"Error solving TSP: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    logging.info("최적화된 LKH TSP 서비스 시작...")
    app.run(host='0.0.0.0', port=5001)