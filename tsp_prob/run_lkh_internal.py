import subprocess
import os
import numpy as np
import tempfile

LKH_EXECUTABLE = "/usr/local/bin/LKH"

def solve_tsp_with_lkh(time_matrix, initial_tour=None, runs=5):
    n = time_matrix.shape[0]
    if n == 0:
        return [], 0.0
    if n == 1:
        return [0], 0.0

    if n <= 5:
        runs = max(3, runs)
        time_limit = 5
        max_trials = 500
    elif n <= 10:
        runs = max(5, runs)
        time_limit = 8
        max_trials = 1000
    elif n <= 20:
        runs = max(8, runs)
        time_limit = 12
        max_trials = 3000
    elif n <= 50:
        runs = max(10, runs)
        time_limit = 15
        max_trials = 5000
    else:
        runs = max(12, runs)
        time_limit = 20
        max_trials = 8000

    int_time_matrix = np.round(time_matrix).astype(int)

    with tempfile.TemporaryDirectory() as tempdir:
        problem_filename = os.path.join(tempdir, "problem.tsp")
        param_filename = os.path.join(tempdir, "params.par")
        output_filename = os.path.join(tempdir, "output.tour")
        initial_tour_filename = os.path.join(tempdir, "initial.tour") if initial_tour else None

        with open(problem_filename, 'w') as f:
            f.write(f"NAME : dynamic_tsp_{n}\n")
            f.write(f"TYPE : TSP\n")
            f.write(f"COMMENT : Dynamic TSP for delivery\n")
            f.write(f"DIMENSION : {n}\n")
            f.write(f"EDGE_WEIGHT_TYPE : EXPLICIT\n")
            f.write(f"EDGE_WEIGHT_FORMAT: FULL_MATRIX\n")
            f.write("EDGE_WEIGHT_SECTION\n")
            for i in range(n):
                f.write(" ".join(map(str, int_time_matrix[i])) + "\n")
            f.write("EOF\n")

        if initial_tour_filename and initial_tour:
            with open(initial_tour_filename, 'w') as f:
                f.write(f"NAME : initial_tour_{n}\n")
                f.write(f"TYPE : TOUR\n")
                f.write(f"DIMENSION : {n}\n")
                f.write("TOUR_SECTION\n")
                for node_index in initial_tour:
                    f.write(f"{node_index + 1}\n")
                f.write("-1\n")
                f.write("EOF\n")

        with open(param_filename, 'w') as f:
            f.write(f"PROBLEM_FILE = {problem_filename}\n")
            f.write(f"OUTPUT_TOUR_FILE = {output_filename}\n")
            f.write(f"RUNS = {min(runs, 5)}\n")
            f.write(f"TRACE_LEVEL = 1\n")
            f.write(f"TIME_LIMIT = {time_limit}\n")
            f.write(f"MAX_TRIALS = {max_trials}\n")

            f.write("INITIAL_PERIOD = 10\n")
            f.write("MAX_CANDIDATES = 5\n")

            if n <= 10:
                pass
            elif n <= 30:
                f.write("CANDIDATE_SET_TYPE = POPMUSIC\n")
                f.write("POPMUSIC_SAMPLE_SIZE = 8\n")
                f.write("POPMUSIC_SOLUTIONS = 30\n")
                f.write("POPMUSIC_MAX_NEIGHBORS = 3\n")
                f.write("POPMUSIC_TRIALS = 1\n")
            else:
                f.write("CANDIDATE_SET_TYPE = POPMUSIC\n")
                f.write("POPMUSIC_SAMPLE_SIZE = 10\n")
                f.write("POPMUSIC_SOLUTIONS = 50\n")
                f.write("POPMUSIC_MAX_NEIGHBORS = 5\n")
                f.write("POPMUSIC_TRIALS = 1\n")
                f.write("SUBGRADIENT = YES\n")
                f.write("ASCENT_CANDIDATES = 30\n")
            
            if initial_tour_filename and initial_tour:
                f.write(f"INITIAL_TOUR_FILE = {initial_tour_filename}\n")

        try:
            process = subprocess.run([LKH_EXECUTABLE, param_filename], capture_output=True, text=True, check=True, timeout=time_limit + 30)
            
        except FileNotFoundError:
            print(f"Error: LKH executable not found at {LKH_EXECUTABLE}")
            return None, None
        except subprocess.CalledProcessError as e:
            print(f"Error running LKH: {e}")
            print(f"LKH stdout:\n{e.stdout}")
            print(f"LKH stderr:\n{e.stderr}")
            return None, None
        except subprocess.TimeoutExpired as e:
            print(f"Error: LKH execution timed out ({e.timeout} seconds).")
            print(f"LKH stdout so far:\n{e.stdout}")
            print(f"LKH stderr so far:\n{e.stderr}")
            return None, None

        try:
            with open(output_filename, 'r') as f:
                lines = f.readlines()

            optimal_cost = -1.0
            cost_line = next((line for line in process.stdout.split('\n') if "Cost.min =" in line or "Cost =" in line), None)
            if cost_line:
                 try:
                    optimal_cost_str = cost_line.split('=')[-1].strip()
                    optimal_cost = float(optimal_cost_str)
                 except ValueError:
                    print(f"Warning: Could not parse cost from LKH output line: {cost_line}")
            else:
                 print("Warning: Could not find cost information in LKH standard output.")

            tour_section_start = -1
            for i, line in enumerate(lines):
                if line.strip() == "TOUR_SECTION":
                    tour_section_start = i + 1
                    break

            if tour_section_start == -1:
                print(f"Error: Could not find TOUR_SECTION in {output_filename}")
                return None, None

            optimal_tour = []
            for line in lines[tour_section_start:]:
                node_str = line.strip()
                if node_str == "-1" or node_str == "EOF":
                    break
                try:
                    node_index_1based = int(node_str)
                    optimal_tour.append(node_index_1based - 1)
                except ValueError:
                    print(f"Warning: Skipping invalid node index in tour file: {node_str}")
                    continue

            if not optimal_tour:
                 print(f"Error: No valid tour found in {output_filename}")
                 return None, None

            if len(optimal_tour) != n or set(optimal_tour) != set(range(n)):
                 print(f"Error: Parsed tour is invalid. Expected {n} unique nodes, got {len(optimal_tour)}: {optimal_tour}")

            calculated_cost = 0.0
            if optimal_cost < 0 and len(optimal_tour) == n :
                print("Recalculating tour cost from the matrix...")
                for i in range(n):
                    from_node = optimal_tour[i]
                    to_node = optimal_tour[(i + 1) % n]
                    calculated_cost += time_matrix[from_node, to_node]
                optimal_cost = calculated_cost
                print(f"Recalculated cost: {optimal_cost}")

            return optimal_tour, optimal_cost

        except FileNotFoundError:
            print(f"Error: LKH output file not found at {output_filename}")
            return None, None
        except Exception as e:
            print(f"Error parsing LKH output: {e}")
            return None, None