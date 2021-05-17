from minizinc import Instance, Model, Solver
import csv


def get_min_machine_number(file, component_number):
    with open(file, 'r') as f:
        content = csv.DictReader(f)
        application_name = file.replace('_Surrogate.csv', '').lower()
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
    instance.add_file(f"{model_path.replace('.mzn','')}_Offers{offers_number}.dzn")
    # Assign the number of wordpress instances and the minimum machines number
    instance["M"] = get_min_machine_number(f"{model_path.replace('.mzn','')}_Surrogate.csv", problem_instances_number)
    instance["WP"] = problem_instances_number
    result = instance.solve()
    return result


if __name__ == '__main__':
    model_file = "Wordpress.mzn"
    Solvers = ["chuffed", "gecode", "or-tools"]
    offers_numbers = [20, 40, 250, 500]
    for solver in Solvers:
        for component_instances in range(3, 13):
            for number in offers_numbers:
                output = solve_model_minizinc(model_file, component_instances, solver, number)
                print(output)


