from minizinc import Instance, Model, Solver
from datetime import timedelta
import csv
import time
import os
import json


def get_min_machine_number(file, component_number):
    """
    This function returns the mapping between the number of components deployed and the max machine number
    For ex: 3 wordpress -> max 8 machines, 4 wordpress -> max 10 machines, in our case 3 and 4 are "component_number"

    Args:
       file: The path to the file that contains the mapping
       component_number: The number of component instances to which we need to find the mapping

    Returns:
        value: Integer value that represents the maximum number of virtual machines that can be deployed, if we know
               the number of components that are already deployed
    """
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
    """
    This function is used to solve the model given as parameter, using the specified solver.

    Args:
      model_path: The path to the location of the MiniZinc model file
      problem_instances_number: The minimum number of main component that will be deployed
      solver: The name of the solver that will be used to find the solution
      offers_number: The number of offers that is used for this particular solution

    Returns:
       result: A MiniZinc object, that contains the result of the model given as parameter
       runtime: Integer value that represents the runtime of the model, in seconds
    """
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


def write_output(model_path, component_number, offer_number, price_array, run_time, solver):
    """
    This function writes to a csv file the output of our problem.
    We are interested to output the price array, the minimum price value and the runtime.

    Args:
      model_path: The path to the location of the MiniZinc model file
      component_number: The minimum number of main component that will be deployed
      offer_number: The number of offers that is used for this particular solution
      price_array: The price array that corresponds to the given model
      run_time: Integer value that represents the runtime of the model, in seconds
      solver: The name of the solver that will be used to find the solution
    """
    create_directory(f"Output\\MiniZinc_Output\\{solver}")
    model_path = model_path.replace('Models\\', '')
    file = f"Output\\MiniZinc_Output\\{solver}\\{model_path.replace('.mzn', '')}" \
           f"{component_number}_Offers{offer_number}_{solver}.csv"
    with open(file, mode='w', newline='') as f:
        fieldnames = ['Price min value', 'Price for each machine', 'Time']
        writer = csv.DictWriter(f, fieldnames=fieldnames)

        writer.writeheader()
        min_price = sum(price_array)
        writer.writerow({'Price min value': min_price, 'Price for each machine': price_array, 'Time': run_time})


def create_greedy_input(model_path, component_number, offer_number, assignment_matrix, price_array, type_array):
    """
    This function writes to a json file the necessary information that will be used as input to a greedy algorithm

    Args:
      model_path: The path to the location of the MiniZinc model file
      component_number: The minimum number of main component that will be deployed
      offer_number: The number of offers that is used for this particular solution
      assignment_matrix: The assignment matrix obtained by solving the given model
      price_array: The price array that corresponds to the given model
      type_array: The type array that corresponds to the given model
    """
    create_directory("Input\\Greedy_Input")
    model_path = model_path.replace('Models\\', '')
    file = f"Input\\Greedy_Input\\{model_path.replace('.mzn', '')}{component_number}_Offers{offer_number}_Input.json"
    data = {
        "Assignment Matrix": assignment_matrix,
        "Price Array": price_array,
        "Type Array": type_array
    }
    with open(file, 'w') as f:
        json.dump(data, f)


def create_directory(directory_name):
    """
    A function that checks if the directory with provided name already exists and it creates it if it doesn't

    Args:
      directory_name: A string value that represents the name of a directory
    """
    if not os.path.exists(directory_name):
        os.makedirs(directory_name)


if __name__ == '__main__':
    problem_name = input("Introduce the problem name(should start with uppercase letter):\n")
    lower_bound = int(input(f"Introduce the lower bound for the number of {problem_name} instances:\n"))
    upper_bound = int(input(f"Introduce the upper bound for the number of {problem_name} instances:\n"))
    time_limit = int(input("Introduce the time limit(in seconds) for each problem\n"))
    model_file = f"Models\\{problem_name}.mzn"
    Solvers = ["chuffed", "gecode", "or-tools"]
    offers_numbers = [20, 40, 250, 500]
    for solver in Solvers:
        stop = False
        for component_instances in range(lower_bound, upper_bound):
            if stop:
                break
            for number in offers_numbers:
                output, runtime = solve_model_minizinc(model_file, component_instances, solver, number)
                # If a run with 20 offers goes over the time limit there is no purpose to further test
                if runtime >= time_limit and number == 20:
                    stop = True
                    break
                # If the runtime is beaten at any other value than 20, it could mean we will miss some solutions
                # For ex: wordpress 3 offers 40 -> time limit ( it means for sure 250 and 500 will also beat the limit)
                # But, at the same time we would still have to check wordpress 4 offers 20 and so on..
                elif runtime >= time_limit:
                    break
                write_output(model_file, component_instances, number, output['price'], runtime, solver)
                create_greedy_input(model_file, component_instances, number,
                                    output['a'], output['price'], output['t'])
