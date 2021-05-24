from minizinc import Instance, Model, Solver
from datetime import timedelta
import csv
import time
import os
import json


# This function returns the mapping between the number of components deployed and the max machine number
# For ex: 3 wordpress -> max 8 machines, 4 wordpress -> max 10 machines, in our case 3 and 4 are "component_number"
def get_min_machine_number(file, component_number):
    with open(file, 'r') as f:
        content = csv.DictReader(f)
        # Since the content of the csv file depends on what problem we solve, we want to extract the problem name
        # In this convention, we do that by removing the _surrogate.csv part and also the directory header
        application_name = file.replace('_Surrogate.csv', '').lower()
        application_name = application_name.replace('surrogate\\', '')
        # We go through the csv file and if we find the number received as parameter we can return it's mapping
        for row in content:
            if row[f'{application_name}_instances'] == str(component_number):
                return int(row['vm_number'])


def solve_model_minizinc(model_path, problem_instances_number, solver, offers_number):
    # Load the model from the corresponding file
    model = Model(model_path)
    # Find the solver configuration
    solver = Solver.lookup(solver)
    # Create an instance of the problem using the previous solver
    instance = Instance(solver, model)
    # Links the corresponding dzn file to the model
    instance.add_file(f"DZN_Files\\{model_path.replace('.mzn', '')}_Offers{offers_number}.dzn")
    # Assign the number of wordpress instances and the minimum machines number
    instance["M"] = get_min_machine_number(
        f"Surrogate\\{model_path.replace('.mzn', '')}_Surrogate.csv",
        problem_instances_number
    )
    instance["WP"] = problem_instances_number
    start_time = time.time()
    result = instance.solve(timeout=timedelta(milliseconds=2400000))
    run_time = time.time() - start_time
    return result, run_time


def write_output(model_file, component_number, offer_number, price_array, run_time):
    create_directory("MiniZinc_Output")
    file = f"MiniZinc_Output\\{model_file.replace('.mzn', '')}{component_number}_Offers{offer_number}_MiniZinc.csv"
    with open(file, mode='w', newline='') as f:
        fieldnames = ['Price min value', 'Price for each machine', 'Time']
        writer = csv.DictWriter(f, fieldnames=fieldnames)

        writer.writeheader()
        min_price = sum(price_array)
        writer.writerow({'Price min value': min_price, 'Price for each machine': price_array, 'Time': run_time})


def create_greedy_input(model_file, component_number, offer_number, assignment_matrix, price_array, type_array):
    create_directory("Greedy_Input")
    file = f"Greedy_Input\\{model_file.replace('.mzn', '')}{component_number}_Offers{offer_number}_Input.json"
    data = {
        "Assignment Matrix": assignment_matrix,
        "Price Array": price_array,
        "Type Array": type_array
    }
    with open(file, 'w') as f:
        json.dump(data, f)


# A function that checks if the directory with provided name already exists and it creates it if it doesn't
def create_directory(directory_name):
    if not os.path.exists(directory_name):
        os.makedirs(directory_name)


if __name__ == '__main__':
    output, runtime = solve_model_minizinc("Wordpress.mzn", 3, "chuffed", 20)
    write_output("Wordpress.mzn", 3, 20, output['price'], runtime)
    create_greedy_input("Wordpress.mzn", 3, 20, output['a'], output['price'],  output['t'])
    """model_file = "Wordpress.mzn"
    Solvers = ["chuffed", "gecode", "or-tools"]
    offers_numbers = [20, 40, 250, 500]
    for solver in Solvers:
        for component_instances in range(3, 13):
            for number in offers_numbers:
                output = solve_model_minizinc(model_file, component_instances, solver, number)
                print(output)"""
