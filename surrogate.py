import csv
from minizinc import Instance, Model, Solver

"""
This file is used to run a surrogate problem needed before solving the main one.
We solve it with the MiniZinc Python Interface and write the results to a csv file.
The file will contain the relationship between the number of wordpress components and the 
number of virtual machines that are needed for deployment. (3 wordpress - 8 machines, 4 wordpress - 10 machines, ...)
"""


def solve_surrogate_minizinc(model_path, problem_instances_number, solver):
    """
    This function is used to solve the model given as parameter, using the specified solver.

    Args:
      model_path: The path to the location of the MiniZinc model file
      problem_instances_number: The minimum number of main component that will be deployed
      solver: The name of the solver that will be used to find the solution

    Returns:
       result: A MiniZinc object, that contains the result of the model given as parameter
    """
    # Load the model from the corresponding file
    surrogate = Model(model_path)
    # Find the solver configuration
    solver = Solver.lookup(solver)
    # Create an instance of the problem using the previous solver
    instance = Instance(solver, surrogate)
    # Assign the number of wordpress instances to n
    instance["n"] = problem_instances_number
    result = instance.solve()
    return result


def write_csv(file, result_dict, component):
    """
    This function writes to a csv file the results passed as parameter for the given component

    Args:
      file: The path to the file that we want to write to
      result_dict: A dictionary that contains the mapping between the number of components deployed and the maximum
                   number of virtual machines that can be deployed
      component: The name of the component that we built the mapping for
    """
    with open(file, mode='w', newline='') as f:
        fieldnames = [f'{component}_instances', 'vm_number']
        writer = csv.DictWriter(f, fieldnames=fieldnames)

        writer.writeheader()
        for key in result_dict:
            writer.writerow({f'{component}_instances': key, 'vm_number': result_dict[key]})


def get_surrogate_results(model, solver, lower_bound, upper_bound):
    """
    This function is used to solve one at a time, each instance of our problem
    It will go through each solver and solve the problem for every case ( the number will vary between the lower and
    upper bound )

    Args:
      model: The path to the location of the MiniZinc model file
      solver: The name of the solver that will be used to find the solution
      lower_bound: Integer value that represents the minimum number of instances that can be deployed in the system
      upper_bound: Integer value that represents the maximum number of instances that can be deployed in the system

    Returns:
       result: A MiniZinc object, that contains the result of the model given as parameter
    """
    solution_dict = {}
    for component_instances in range(lower_bound, upper_bound + 1):
        solution = solve_surrogate_minizinc(model, component_instances, solver)
        solution_dict[component_instances] = solution['objective']
    return solution_dict


if __name__ == '__main__':
    problem_name = input("Introduce the problem name(should start with uppercase letter:\n")
    lower_bound = int(input(f"Introduce the lower bound for the number of {problem_name} instances:\n"))
    upper_bound = int(input(f"Introduce the upper bound for the number of {problem_name} instances:\n"))

    Surrogate = f"Surrogate\\{problem_name}_Surrogate.mzn"

    surrogate_results = get_surrogate_results(Surrogate, "chuffed", lower_bound, upper_bound)

    write_csv(f"Surrogate\\{problem_name}_Surrogate.csv", surrogate_results, f"{problem_name.lower()}")
