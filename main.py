import json
from copy import deepcopy

# input from MiniZinc results
assignment_matrix = []
vm_types = []
prices = []

# problem input
components = []
offers = []
added_component = []
constraints = {}

# variables to hold the output of the algorithm
new_assignment_matrix = []
new_price_array = []
new_vm_types = []


def get_components():
    with open('data.txt') as f:
        components_list = json.load(f)
        return components_list["Components"]


def get_offers():
    with open('data.txt') as f:
        components_list = json.load(f)
        return components_list["Offers"]


def get_assignment_matrix():
    with open('data.txt') as f:
        components_list = json.load(f)
        return components_list["Assignment Matrix"]


def get_vm_types():
    with open('data.txt') as f:
        components_list = json.load(f)
        return components_list["Type Array"]


def get_constraints():
    with open('data.txt') as f:
        components_list = json.load(f)
        constraints_dict = components_list["Constraints"]
        return constraints_dict


def get_added_component():
    with open('data.txt') as f:
        components_list = json.load(f)
        added_component_id = components_list["Added Component"]
        return components[added_component_id]


def get_prices(offers_array):
    price_array = [offer['Price'] for offer in offers_array]
    return price_array


# this function computes the number of deployed instances for the component with the provided id
# that means it goes trough the assignment matrix at row 'component_id' and adds all the elements
# since a value of 1 in the assignment matrix means 'deployed' we can find the occurrence of a certain component
def compute_frequency(component_id, matrix):
    component_frequency = sum(matrix[component_id])
    return component_frequency


# checks on each machine if the component with parameter id and his conflict are both deployed
# returns true if no such conflict exists
def check_conflict(constraint, matrix, component_id):
    conflict_component_id = constraint['compId']
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
def handle_provide(constraint, matrix, component_id):
    if constraint['alphaCompId'] == component_id:
        problem_component_id = constraint['betaCompId']
    else:
        problem_component_id = constraint['alphaCompId']
    # we try to place the new component on any new machine besides the original ones
    for column in range(len(assignment_matrix[0]), len(matrix[0])):
        if check_column_placement(matrix, column, problem_component_id):
            matrix[problem_component_id][column] = 1
            return matrix
    # if we can't place it on an existing machine, we add a new one, with the problem component deployed on it
    matrix = add_column(matrix, problem_component_id)
    return matrix


# a function that tries to fix a require_provide constraint that is false
def handle_require_provide(constraint, matrix, component_id):
    if constraint['betaCompId'] == component_id:
        problem_component_id = constraint['alphaCompId']
    else:
        problem_component_id = constraint['betaCompId']
    # we try to place the new component on any new machine besides the original ones
    for column in range(len(assignment_matrix[0]), len(matrix[0])):
        if check_column_placement(matrix, column, problem_component_id):
            matrix[problem_component_id][column] = 1
            return matrix
    # if we can't place it on an existing machine, we add a new one, with the problem component deployed on it
    matrix = add_column(matrix, problem_component_id)
    return matrix


# function that returns for a given component all the conflicts
# it checks the conflicts dictionary for both keys and values, adding them to the conflict array for that component
def get_component_conflicts(component_id):
    conflicts = [constraint for constraint in constraints if constraint['type'] == 'Conflict']
    component_conflicts = []
    for conflict in conflicts:
        if conflict['compId'] == component_id:
            for component in conflict['compIdList']:
                if component not in component_conflicts:
                    component_conflicts.append(component)
        if component_id in conflict['compIdList'] and conflict['compId'] not in component_conflicts:
            component_conflicts.append(conflict['compId'])
    return component_conflicts


# a function that checks whether we can deploy the component with given id on the machine with given id
# to do that, we have to check such that the machine has no components that are in conflict with the given one
def check_column_placement(matrix, column_id, component_id):
    if matrix[component_id][column_id] == 1:
        return False
    component_conflicts = get_component_conflicts(component_id)
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
def get_free_space(machine_id, matrix, column):
    deployed_components = get_deployed_components(matrix, column)
    if not deployed_components:
        # we return the entire machine capacity since there is no deployed component
        free_space = [offers[machine_id][resource] for resource in offers[machine_id] if resource != 'Price']
        return free_space
    else:
        resources = [resource for resource in offers[machine_id] if resource != 'Price']
        # we return the remaining between the machine capacity and the already occupied space
        free_space = [offers[machine_id][resource] - components[deployed_component][resource]
                      for resource in resources for deployed_component in deployed_components]
        return free_space


# checks if the free space on a machine is enough to deploy the component with provided id
def check_enough_space(free_space, component_id):
    resources = [resource for resource in components[component_id] if resource != 'Name']
    # compute remaining space by subtracting the component requirements from the free space
    remaining_space = [free_space[index] - components[component_id][resources[index]]
                       for index in range(len(free_space))]
    for space in remaining_space:
        if space < 0:
            return False
    return True


# build a list of all the constraints that involve the component with the parameter id
def get_component_constraints(component_id):
    component_constraints = []
    # the only keys that can contain a component id
    id_keys = ['compId', 'alphaCompId', 'betaCompId', 'compIdList']
    for constraint in constraints:
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
def handle_false_constraints(false_constraints, matrix, component_id):
    for constraint in false_constraints:
        constraint_name = constraint['type']
        matrix = eval(f'handle_{constraint_name}'.lower() + "(constraint, matrix, component_id)")
    return matrix


# a function that handles the false constraints until we have a matrix that satisfies all of them
def get_final_matrix(matrix, component_id, component_constraints):
    matrix = add_column(matrix, component_id)
    false_constraints = check_constraints(component_constraints, matrix, component_id)
    while false_constraints:
        matrix = handle_false_constraints(false_constraints, matrix, component_id)
        false_constraints = check_constraints(component_constraints, matrix, component_id)
    return matrix


# a function that returns a list containing the resource that each of the new components consume
# for each machine we have a dictionary with the sum of resources on that machine, all of those held in a list
def get_new_resources(matrix):
    new_components_resources = []
    resources_keys = [key for key in components[0] if key != 'Name']
    for column in range(len(assignment_matrix[0]), len(matrix[0])):
        deployed_components_id = get_deployed_components(matrix, column)
        components_dict = [components[index] for index in deployed_components_id]
        machine_resources = {resource: 0 for resource in resources_keys}
        for component in components_dict:
            for key in resources_keys:
                machine_resources[key] = machine_resources[key] + component[key]
        new_components_resources.append(machine_resources)
    return new_components_resources


def greedy(component_id):
    component_constraints = get_component_constraints(component_id)
    for column in range(len(assignment_matrix[component_id])):
        if check_column_placement(assignment_matrix, column, component_id):
            free_space = get_free_space(vm_types[column], assignment_matrix, column)
            if check_enough_space(free_space, component_id):
                new_matrix = deepcopy(assignment_matrix)
                new_matrix[component_id][column] = 1
            else:
                new_matrix = deepcopy(assignment_matrix)
                new_matrix = get_final_matrix(new_matrix, component_id, component_constraints)
                deployed_components = get_new_resources(new_matrix)
                return deployed_components


if __name__ == '__main__':
    # initialize global variables
    components = get_components()

    offers = get_offers()
    prices = get_prices(offers)

    assignment_matrix = get_assignment_matrix()

    vm_types = get_vm_types()

    added_component = get_added_component()

    constraints = get_constraints()

    print(greedy(0))
