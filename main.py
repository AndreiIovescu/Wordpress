import json
from copy import deepcopy


def get_components(file):
    with open(file) as f:
        components_list = []
        json_list = json.load(f)
        for entry in json_list['components']:
            component = {
                'Name': entry['name'],
                'Cpu': entry['Compute']['CPU'],
                'Memory': entry['Compute']['CPU'],
                'Storage': entry['Storage']['StorageSize']
            }
            components_list.append(component)
    return components_list


def get_constraints(file):
    with open(file) as f:
        json_list = json.load(f)
        return json_list['restrictions']


def get_offers(file):
    with open(file) as f:
        offers_list = []
        json_list = json.load(f)
        for entry in json_list:
            offer = {
                'Cpu': json_list[entry]['cpu'],
                'Memory': json_list[entry]['memory'],
                'Storage': json_list[entry]['storage'],
                'Price': json_list[entry]['price']
            }
            offers_list.append(offer)
        return offers_list


def parse_existing_solution(file):
    with open(file) as f:
        json_list = json.load(f)
        return json_list


# this function computes the number of deployed instances for the component with the provided id
# that means it goes trough the assignment matrix at row 'component_id' and adds all the elements
# since a value of 1 in the assignment matrix means 'deployed' we can find the occurrence of a certain component
def compute_frequency(component_id, matrix):
    component_frequency = sum(matrix[component_id])
    return component_frequency


# checks on each machine if the component with parameter id and his conflict are both deployed
# returns true if no such conflict exists
def check_conflicts(constraint, matrix, component_id):
    conflict_component_id = constraint['alphaCompId']
    for column in range(len(matrix[0])):
        conflict_component_deployed = False
        component_id_deployed = False
        for row in range(len(matrix)):
            if matrix[row][column] == 1 and row == conflict_component_id:
                conflict_component_deployed = True
            elif matrix[row][column] == 1 and row == component_id:
                component_id_deployed = True
        if component_id_deployed is True and conflict_component_deployed is True:
            return False
    return True


# checks whether the component with provided id is deployed at least 'bound' times
def check_lower_bound(constraint, matrix, component_id):
    if compute_frequency(component_id, matrix) >= constraint['bound']:
        return True
    return False


# checks whether the component with provided id is deployed at most 'bound' times
def check_upper_bound(constraint, matrix, component_id):
    if compute_frequency(component_id, matrix) <= constraint['bound']:
        return True
    return False


# this function checks whether the components with the provided id are both deployed in the system
def check_exclusive_deployment(constraint, matrix, component_id):
    if compute_frequency(constraint['alphaCompId'], matrix) > 0 \
            and compute_frequency(constraint['betaCompId'], matrix) > 0:
        return False
    return True


# this function verifies that the numerical constraint between two components is respected
# Ex: Wordpress requires at least three instances of mysql and mysql can serve at most 2 Wordpress
# this is a require provide constraint since we have limitations for both 'require' and 'provider'
def check_require_provide(constraint, matrix, component_id):
    if compute_frequency(constraint['alphaCompId'], matrix) * constraint['alphaCompIdInstances'] <= \
            compute_frequency(constraint['betaCompId'], matrix) * constraint['betaCompIdInstances']:
        return True
    return False


# this function is similar to require provide, but this time we have no knowledge about one component in the relation
# Ex:HTTP Balancer requires at least one wordpress instance and http balancer can serve at most 3 Wordpress instances.
# we know that http requires at least 1 wordpress can serve at most 3, but we know nothing about what wordpress offers.
def check_provide(constraint, matrix, component_id):
    if compute_frequency(constraint['alphaCompId'], matrix) == 0 \
            or compute_frequency(constraint['betaCompId'], matrix) == 0:
        return True
    if compute_frequency(constraint['alphaCompId'], matrix) <= \
            constraint['alphaCompIdInstances'] * compute_frequency(constraint['betaCompId'], matrix):
        return True
    return False


# a function that tries to fix a provide constraint that is false
def handle_provide(constraint, new_matrix, initial_matrix, component_id, constraints_list):
    if constraint['alphaCompId'] == component_id:
        problem_component_id = constraint['betaCompId']
    else:
        problem_component_id = constraint['alphaCompId']
    # we try to place the new component on any new machine besides the original ones
    for column in range(len(initial_matrix[0]), len(new_matrix[0])):
        if check_column_placement(new_matrix, column, problem_component_id, constraints_list):
            new_matrix[problem_component_id][column] = 1
            return new_matrix
    # if we can't place it on an existing machine, we add a new one, with the problem component deployed on it
    matrix = add_column(new_matrix, problem_component_id)
    return matrix


# a function that tries to fix a require_provide constraint that is false
def handle_require_provide(constraint, new_matrix, initial_matrix, component_id, constraints_list):
    if constraint['betaCompId'] == component_id:
        problem_component_id = constraint['alphaCompId']
    else:
        problem_component_id = constraint['betaCompId']
    # we try to place the new component on any new machine besides the original ones
    for column in range(len(initial_matrix[0]), len(new_matrix[0])):
        if check_column_placement(new_matrix, column, problem_component_id, constraints_list):
            new_matrix[problem_component_id][column] = 1
            return new_matrix
    # if we can't place it on an existing machine, we add a new one, with the problem component deployed on it
    matrix = add_column(new_matrix, problem_component_id)
    return matrix


def handle_upper_bound(constraint, new_matrix, initial_matrix, component_id, constraints_list):
    pass


# function that returns for a given component all the conflicts
# it checks the conflicts dictionary for both keys and values, adding them to the conflict array for that component
def get_component_conflicts(component_id, constraints_list):
    conflicts = [constraint for constraint in constraints_list if constraint['type'] == 'Conflicts']
    component_conflicts = []
    for conflict in conflicts:
        if conflict['alphaCompId'] == component_id:
            for component in conflict['compsIdList']:
                if component not in component_conflicts:
                    component_conflicts.append(component)
        if component_id in conflict['compsIdList'] and conflict['alphaCompId'] not in component_conflicts:
            component_conflicts.append(conflict['alphaCompId'])
    return component_conflicts


# a function that checks whether we can deploy the component with given id on the machine with given id
# to do that, we have to check such that the machine has no components that are in conflict with the given one
def check_column_placement(matrix, column_id, component_id, constraints_list):
    if matrix[component_id][column_id] == 1:
        return False
    component_conflicts = get_component_conflicts(component_id, constraints_list)
    for row in range(len(matrix)):
        if matrix[row][column_id] == 1 and row in component_conflicts:
            return False
    return True


# function that returns the id of the deployed component on the column(machine) with provided id
def get_deployed_components(matrix, column_id):
    deployed_components = []
    for row in range(len(matrix)):
        if matrix[row][column_id] == 1:
            deployed_components.append(row)
    return deployed_components


# function that returns the free amount of space on a given machine
def get_free_space(machine_id, matrix, column, offers_list, components_list):
    deployed_components = get_deployed_components(matrix, column)
    if not deployed_components:
        # we return the entire machine capacity since there is no deployed component
        free_space = [offers_list[machine_id][resource] for resource in offers_list[machine_id] if resource != 'Price']
        return free_space
    else:
        resources = [resource for resource in offers[machine_id] if resource != 'Price']
        # we return the remaining between the machine capacity and the already occupied space
        free_space = [offers_list[machine_id][resource] - components_list[deployed_component][resource]
                      for resource in resources for deployed_component in deployed_components]
        return free_space


# checks if the free space on a machine is enough to deploy the component with provided id
def check_enough_space(free_space, component_id, components_list):
    resources = [resource for resource in components_list[component_id] if resource != 'Name']
    # compute remaining space by subtracting the component requirements from the free space
    remaining_space = [free_space[index] - components_list[component_id][resources[index]]
                       for index in range(len(free_space))]
    for space in remaining_space:
        if space < 0:
            return False
    return True


# build a list of all the constraints that involve the component with the parameter id
def get_component_constraints(component_id, constraints_list):
    component_constraints = []
    # the only keys that can contain a component id
    id_keys = ['alphaCompId', 'betaCompId', 'compsIdList']
    for constraint in constraints_list:
        # gets the corresponding keys for that specific constraint
        constraint_keys = [value for value in constraint if value in id_keys]
        for id_key in constraint_keys:
            # some of the keys can have lists as value so we have to check if they contain our component id
            if type(constraint[id_key]) is list:
                if component_id in constraint[id_key]:
                    component_constraints.append(constraint)
            else:
                if component_id == constraint[id_key]:
                    component_constraints.append(constraint)
    return component_constraints


# function that checks all the constraints that involve the component with parameter id and returns the false ones
def check_constraints(constraints_list, matrix, component_id):
    false_constraints = []
    for constraint in constraints_list:
        constraint_name = constraint['type']
        corresponding_function_result = eval(f'check_{constraint_name}'.lower() + "(constraint, matrix, component_id)")
        if not corresponding_function_result:
            false_constraints.append(constraint)
    return false_constraints


# builds a new matrix by adding a column to the parameter one
# the new column has 0 on every row but the one corresponding to the component with the parameter id
def add_column(matrix, component_id):
    return_matrix = deepcopy(matrix)
    row_counter = 0
    for row in return_matrix:
        if row_counter == component_id:
            row.append(1)
        else:
            row.append(0)
        row_counter += 1
    return return_matrix


# a function that gets the name of each false constraint and calls the corresponding function to handle it
def handle_false_constraints(false_constraints, new_matrix, initial_matrix, component_id, constraints_list):
    for constraint in false_constraints:
        constraint_name = constraint['type']
        new_matrix = eval(
            f'handle_{constraint_name}'.lower() + "(constraint, new_matrix, initial_matrix, component_id, "
                                                  "constraints_list)")
    return new_matrix


# a function that handles the false constraints until we have a matrix that satisfies all of them
def get_final_matrix(matrix, component_id, component_constraints, constraints_list):
    initial_matrix = deepcopy(matrix)
    matrix = add_column(matrix, component_id)
    false_constraints = check_constraints(component_constraints, matrix, component_id)
    while false_constraints:
        matrix = handle_false_constraints(false_constraints, matrix, initial_matrix, component_id, constraints_list)
        false_constraints = check_constraints(component_constraints, matrix, component_id)
    return matrix


# a function that returns a list containing the resource that each of the new components consume
# for each machine we have a dictionary with the sum of resources on that machine, all of those held in a list
def get_new_resources(new_matrix, initial_matrix):
    new_components_resources = []
    resources_keys = [key for key in components[0] if key != 'Name']
    for column in range(len(initial_matrix[0]), len(new_matrix[0])):
        deployed_components_id = get_deployed_components(new_matrix, column)
        components_dict = [components[index] for index in deployed_components_id]
        machine_resources = {resource: 0 for resource in resources_keys}
        for component in components_dict:
            for key in resources_keys:
                machine_resources[key] = machine_resources[key] + component[key]
        new_components_resources.append(machine_resources)
    return new_components_resources


#
def sort_offers(offers_list):
    sorted_list = sorted(offers_list, key=lambda i: (i['Cpu'], i['Memory'], i['Storage'], i['Price']))
    return sorted_list


def choose_machine(offers_list, components_resources):
    new_machines = []
    for machine_resources in components_resources:
        for offer in offers_list:
            is_good = True
            for key in offer:
                if key != 'Price':
                    if offer[key] < machine_resources[key]:
                        is_good = False
                        break
            if is_good:
                new_machines.append(offers.index(offer))
                break
    return new_machines


def greedy(solution, components_list, component_id, constraints_list, offers_list):
    assignment_matrix = solution['Assignment Matrix']
    vm_types = solution["Type Array"]
    prices = solution["Price Array"]
    component_constraints = get_component_constraints(component_id, constraints_list)

    for column in range(len(assignment_matrix[component_id])):
        if check_column_placement(assignment_matrix, column, component_id, constraints_list):
            free_space = get_free_space(vm_types[column], assignment_matrix, column, offers_list, components_list)
            if check_enough_space(free_space, component_id, components_list):
                new_matrix = deepcopy(assignment_matrix)
                new_matrix[component_id][column] = 1
                if check_constraints(component_constraints, new_matrix, component_id):
                    return new_matrix, vm_types, prices
            else:
                new_matrix = deepcopy(assignment_matrix)
                new_matrix = get_final_matrix(new_matrix, component_id, component_constraints, constraints_list)
                new_components_resources = get_new_resources(new_matrix, assignment_matrix)
                sorted_offers = sort_offers(offers)
                new_machines_id = choose_machine(sorted_offers, new_components_resources)
                for machine_id in new_machines_id:
                    vm_types.append(machine_id)
                    prices.append(offers[machine_id]['Price'])
                output_dictionary = {
                    'Assignment Matrix': new_matrix,
                    'Type Array': vm_types,
                    'Price Array': prices
                }
                with open("Wordpress3_Offers20_Output.json", "w") as f:
                    f.write(json.dumps(output_dictionary))
                return new_matrix, vm_types, prices


if __name__ == '__main__':
    # initialize global variables
    components = get_components("Wordpress3.json")

    constraints = get_constraints("Wordpress3.json")

    offers = get_offers("offers_20.json")

    existing_solution = parse_existing_solution("Wordpress3_Offers20_Input.json")

    comp_id = existing_solution['Added Component']

    new_assignment_matrix, new_vm_types, new_price_array = greedy(existing_solution, components, comp_id,
                                                                  constraints, offers)

    # existing_solution = parse_existing_solution(file) ✓
    # output wordpress3_offers20 - contine new matrix, types, price ✓
    # greedy(existing solution, components_list, component_id, offers_list)✓
    # fisier de input general ✓
    # var. globale ✓
    # output csv/json ✓
    # split input file : application, offers, wordpress3_offers20.json ✓
    # impossible constraint -> explain why plus output
    # minizinc python
    # sort offers

    for row in new_assignment_matrix:
        print(row)
    print(new_vm_types)
    print(new_price_array)
