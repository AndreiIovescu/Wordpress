import json
from copy import deepcopy

# input from MiniZinc results
assignment_matrix = []
vm_types = []
prices = []

# input
components = []
offers = []
added_component = []

# constraints
constraints = {}
conflicts = {}
provide = {}
require_provide = {}

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
        conflict_dict = [constraint for constraint in constraints_dict if constraint['type'] == 'Conflict']
        provide_dict = [constraint for constraint in constraints_dict if constraint['type'] == 'Provide']
        require_provide_dict = [constraint for constraint in constraints_dict if constraint['type'] == 'RequireProvide']
        return constraints_dict, conflict_dict, provide_dict, require_provide_dict


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


# the function first checks whether the two components could be in conflict
# if they can't, it will return false as there is no conflict and we don't have to check
# if the two can be in conflict, then we have to check the assignment matrix
# if the two rows that correspond to the components have the value 1 at the same position, then there exists a conflict
# that is because they have been deployed on the same machine although that does not follow the constraints
def check_conflict(component_id, component2_id):
    for conflict in conflicts:
        if conflict['compId'] == component_id and component2_id in conflict['compIdList']:
            for i in range(len(assignment_matrix[0])):
                if assignment_matrix[component_id][i] == assignment_matrix[component2_id][i] == 1:
                    return True
        else:
            return False
    return False


# checks whether the component with provided id is deployed at least 'bound' times
def check_lower_bound(component_id, bound):
    if compute_frequency(component_id) >= bound:
        return True
    return False


# checks whether the component with provided id is deployed at most 'bound' times
def check_upper_bound(component_id, bound):
    if compute_frequency(component_id) <= bound:
        return True
    return False


# this function checks whether the components with the provided id are both deployed in the system
# it returns false if both are deployed, since there is no 'exclusive deployment' which needs just one to be deployed
def check_exclusive_deployment(component_id, component2_id):
    if compute_frequency(component_id) > 0 and compute_frequency(component2_id) > 0:
        return False
    return True


# this function verifies that the numerical constraint between two components is respected
# Ex: Wordpress requires at least three instances of mysql and mysql can serve at most 2 Wordpress
# this is a require provide constraint since we have limitations for both 'require' and 'provider'
def check_require_provide(component_id, component2_id, comp_instances, comp2_instances, matrix):
    if compute_frequency(component_id, matrix) * comp_instances <= compute_frequency(component2_id,
                                                                                     matrix) * comp2_instances:
        return True
    return False


# this function is similar to require provide, but this time we have no knowledge about one component in the relation
# Ex:HTTP Balancer requires at least one wordpress instance and http balancer can serve at most 3 Wordpress instances.
# we know that http requires at least 1 wordpress can serve at most 3, but we know nothing about what wordpress offers.
def check_provide(component_id, component2_id, comp_instances, matrix):
    if compute_frequency(component_id, matrix) <= comp_instances * compute_frequency(component2_id, matrix):
        return True
    return False


# function that returns for a given component all the conflicts
# it checks the conflicts dictionary for both keys and values, adding them to the conflict array for that component
def get_component_conflicts(component_id):
    component_conflicts = []
    for conflict in conflicts:
        if conflict['compId'] == component_id:
            for component in conflict['compIdList']:
                if component not in component_conflicts:
                    component_conflicts.append(component)
        if component_id in conflict['compIdList'] and conflict['compId'] not in component_conflicts:
            component_conflicts.append(conflict['compId'])
    return component_conflicts


# this function checks whether on a column from the assignment matrix(machine) we could add the new component
# to do this, we first find all the components that are in conflict with the added component
# then we look on the column with the provided id if there are any components deployed that are in conflict with the
# component that we want to add
# if there is at least one we cannot possibly deploy the new component on that machine
def check_column_placement(column_id, component_id):
    if assignment_matrix[component_id][column_id] == 1:
        return False
    component_conflicts = get_component_conflicts(component_id)
    for row in range(len(assignment_matrix)):
        if assignment_matrix[row][column_id] == 1 and row in component_conflicts:
            return False
    return True


# function that returns the id of the deployed component on the column(machine) with provided id
# if no component is deployed the function returns -1
def get_deployed_component(column_id):
    for row in range(len(assignment_matrix)):
        if assignment_matrix[row][column_id] == 1:
            return row
    return -1


# function that returns the free amount of space on a given machine
# if a component is already deployed on that machine it will compute the remaining space
# otherwise it returns the entire capacity of the machine
def get_free_space(machine_id, column):
    deployed_component = get_deployed_component(column)
    if deployed_component == -1:
        free_space = [offers[machine_id][resource] for resource in offers[machine_id] if resource != 'Price']
        return free_space
    else:
        resources = [resource for resource in offers[machine_id] if resource != 'Price']
        free_space = [offers[machine_id][resource] - components[deployed_component][resource] for resource in resources]
        return free_space


# checks if the free space on a machine is enough to deploy the component with provided id
# we create a new list made of the difference between the free space on the machine and the component requirements
# therefore, if any value is smaller than 0 that means we can not deploy a component of that type on the machine
def check_enough_space(free_space, component_id):
    resources = [resource for resource in components[component_id] if resource != 'Name']
    remaining_space = [free_space[index] - components[component_id][resources[index]] for index in range(len(free_space))]
    for space in remaining_space:
        if space < 0:
            return False
    return True


# receives a component id and a matrix and checks on the matrix if the constraints that involve the component
# are satisfied; if they are we return an empty list, otherwise all problem constraints are returned
# since we we need to check only the provide and require provide constraints, we can go trough them at a time,
# and check each one if is true; add to the list only the bad ones
def check_constraints(component_id, matrix):
    problem_constraints = []
    for provide_rule in provide:
        if provide_rule['alphaCompId'] == component_id or provide_rule['betaCompId'] == component_id:
            if not check_provide(provide_rule['alphaCompId'], provide_rule['betaCompId'],
                                 provide_rule['alphaCompIdInstances'], matrix):
                problem_constraints.append(provide_rule)
    for req_prov_rule in require_provide:
        if req_prov_rule['alphaCompId'] == component_id or req_prov_rule['betaCompId'] == component_id:
            if not check_require_provide(req_prov_rule['alphaCompId'], req_prov_rule['betaCompId'],
                                         req_prov_rule['alphaCompIdInstances'], req_prov_rule['betaCompIdInstances'],
                                         matrix):
                problem_constraints.append(req_prov_rule)
    return problem_constraints


# receives a matrix and a component id, and adds a new column in the matrix
# the column is filled with 0's besides the corresponding row for the component
# we use this function to build a new assignment matrix for our solution
def add_column(matrix, component_id):
    return_matrix = deepcopy(matrix)
    counter = 0
    for row in return_matrix:
        if counter == component_id:
            row.append(1)
        else:
            row.append(0)
        counter += 1
    return return_matrix


# goes on each column (which represents a machine) in our assignment matrix and checks:
# if we can put the new component on that machine regarding the conflict constraints that means,
# we can deploy it on that machine if there exists no other component, or one that is not in conflict
# then, in case we could make a case for deploying on a machine, we also have to check the capacity
# that means, we have to go and check if on that machine, there is enough space to also add the new component
# if we find a machine that satisfies both previous checks, we have to look for one last thing
# we need to take the possible new assignment matrix and verify that all the numerical constraints regarding
# the new component are satisfied
def greedy(component_id):
    for column in range(len(assignment_matrix[component_id])):
        if check_column_placement(column, component_id):
            free_space = get_free_space(vm_types[column], column)
            if check_enough_space(free_space, component_id):
                new_matrix = list.copy(assignment_matrix)
                new_matrix[component_id][column] = 1
                print(check_constraints(component_id, new_matrix))
            else:
                new_matrix = add_column(assignment_matrix, component_id)
                print(check_constraints(component_id, new_matrix))
                if not check_constraints(component_id, new_matrix):
                    return new_matrix


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    # initialize global variables
    components = get_components()

    offers = get_offers()
    prices = get_prices(offers)

    assignment_matrix = get_assignment_matrix()

    vm_types = get_vm_types()

    added_component = get_added_component()

    constraints, conflicts, provide, require_provide = get_constraints()

    # greedy(0)

    # to ask: how to deal with unknown constraints in code
