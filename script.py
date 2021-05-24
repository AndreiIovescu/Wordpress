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
    model_path = model_path.replace('Models\\', '')
    instance.add_file(f"Input\\DZN_Files\\{model_path.replace('.mzn', '')}_Offers{offers_number}.dzn")
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


def write_output(model_file, component_number, offer_number, price_array, run_time, solver):
    create_directory(f"Output\\MiniZinc_Output\\{solver}")
    model_file = model_file.replace('Models\\', '')
    file = f"Output\\MiniZinc_Output\\{solver}\\{model_file.replace('.mzn', '')}" \
           f"{component_number}_Offers{offer_number}_{solver}.csv"
    with open(file, mode='w', newline='') as f:
        fieldnames = ['Price min value', 'Price for each machine', 'Time']
        writer = csv.DictWriter(f, fieldnames=fieldnames)

        writer.writeheader()
        min_price = sum(price_array)
        writer.writerow({'Price min value': min_price, 'Price for each machine': price_array, 'Time': run_time})


def create_greedy_input(model_file, component_number, offer_number, assignment_matrix, price_array, type_array):
    create_directory("Input\\Greedy_Input")
    model_file = model_file.replace('Models\\', '')
    file = f"Input\\Greedy_Input\\{model_file.replace('.mzn', '')}{component_number}_Offers{offer_number}_Input.json"
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
    model_file = "Models\\Wordpress.mzn"
    Solvers = ["chuffed", "gecode", "or-tools"]
    offers_numbers = [20, 40, 250, 500]
    for solver in Solvers:
        stop = False
        for component_instances in range(3, 13):
            if stop:
                break
            for number in offers_numbers:
                output, runtime = solve_model_minizinc(model_file, component_instances, solver, number)
                # If a run with 20 offers goes past the time limit there is no purpose to further test
                if runtime >= 2400 and number == 20:
                    stop = True
                    break
                # If the runtime is beaten at any other value than 20, it could mean we will miss some solutions
                # For ex: wordpress 3 offers 40 -> time limit ( it means for sure 250 and 500 will also beat the limit)
                # But, at the same time we would still have to check wordpress 4 offers 20 and so on..
                elif runtime >= 2400:
                    break
                write_output(model_file, component_instances, number, output['price'], runtime, solver)
                create_greedy_input(model_file, component_instances, number,
                                    output['a'], output['price'], output['t'])
