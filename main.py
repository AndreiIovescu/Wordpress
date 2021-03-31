import json

component_requirements = []
offers = []
assignment_matrix = []
vm_types = []
conflicts = {}
added_component = []
prices = []

# variables to hold the output of the algorithm
new_assignment_matrix = []
new_price_array = []
new_vm_types = []


def get_component_requirements():
    with open('data.txt') as f:
        components_list = json.load(f)
        return components_list["Components Requirements"]


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


def get_conflicts():
    with open('data.txt') as f:
        components_list = json.load(f)
        return components_list["Conflicts"]


def get_added_component():
    with open('data.txt') as f:
        components_list = json.load(f)
        added_component_id = components_list["Added Component"]
        return component_requirements[added_component_id]


def get_prices(offers_array):
    price_array = [row[len(offers_array[0]) - 1] for row in offers_array]
    return price_array


# this function computes the number of deployed instances for the component with the provided id
# that means it goes trough the assignment matrix at row 'component_id' and adds all the elements
# since a value of 1 in the assignment matrix means 'deployed' we can find the occurrence of a certain component
def compute_frequency(component_id):
    component_frequency = sum(assignment_matrix[component_id])
    return component_frequency


# the function first checks whether the two components could be in conflict
# if they can't, it will return false as there is no conflict and we don't have to check
# if the two can be in conflict, then we have to check the assignment matrix
# if the two rows that correspond to the components have the value 1 at the same position, then there exists a conflict
# that is because they have been deployed on the same machine although that does not follow the constraints
def check_conflict(component_id, component2_id):
    for component in conflicts:
        if int(component) == component_id and component2_id in conflicts[component]:
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
def check_require_provide(component_id, component2_id, comp_instances, comp2_instances):
    if compute_frequency(component_id) * comp_instances <= compute_frequency(component2_id) * comp2_instances:
        return True
    return False


# this function is similar to require provide, but this time we have no knowledge about one component in the relation
# Ex:HTTP Balancer requires at least one wordpress instance and http balancer can serve at most 3 Wordpress instances.
# we know that http requires at least 1 wordpress can serve at most 3, but we know nothing about what wordpress offers.
def check_provide(component_id, component2_id, comp_instances):
    if compute_frequency(component_id) <= comp_instances * compute_frequency(component2_id):
        return True
    return False


# function that returns for a given component all the conflicts
# it checks the conflicts dictionary for both keys and values, adding them to the conflict array for that component
def get_component_conflicts(component_id):
    component_conflicts = []
    for component in conflicts:
        if int(component) == component_id:
            component_conflicts = conflicts[component]
        if component_id in conflicts[component]:
            component_conflicts.append(int(component))
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
# if no component is deployed the function returns false
def get_deployed_component(column_id):
    for row in range(len(assignment_matrix)):
        if assignment_matrix[row][column_id] == 1:
            return row
    return False


# function that returns the free amount of space on a given machine
# if a component is already deployed on that machine it will compute the remaining space
# otherwise it returns the entire capacity of the machine
def get_free_space(machine_id, column):
    free_space = []
    deployed_component = get_deployed_component(column)
    if not deployed_component:
        for specification_index in range(len(offers[machine_id]) - 1):
            free_space.append(offers[machine_id][specification_index] - component_requirements[deployed_component][
                specification_index + 1])
        return free_space
    else:
        for specification_index in range(len(offers[machine_id]) - 1):
            free_space.append(offers[machine_id][specification_index] - component_requirements[deployed_component][
                specification_index + 1])
        return free_space


# checks if the free space on a machine is enough to deploy the component with provided id
# we create a new list made of the difference between the free space on the machine and the component requirements
# therefore, if any value is smaller than 0 that means we can not deploy a component of that type on the machine
def check_enough_space(free_space, component_id):
    remaining_space = [free_space[index - 1] - component_requirements[component_id][index] for index in range(1, 4)]
    for specification in remaining_space:
        if specification < 0:
            return False
    return True


# goes on each column (which represents a machine) in our assignment matrix and checks:
# if we can put the new component on that machine regarding the conflict constraints that means,
# we can deploy it on that machine if there exists no other component, or one that is not in conflict
# then, in case we could make a case for deploying on a machine, we also have to check the capacity
# that means, we have to go and check if on that machine, there is enough space to also add the new component
# if we find a machine that satisfies both previous checks, we can return the new variables
# we add the new component in the assignment matrix that we already have, while the type and price array remain the same
def greedy(component_id):
    for column in range(len(assignment_matrix[component_id])):
        if check_column_placement(column, component_id):
            free_space = get_free_space(vm_types[column], column)
            if check_enough_space(free_space, component_id):
                new_matrix = assignment_matrix
                new_matrix[component_id][column] = 1
                return new_matrix, prices, vm_types


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    # initialize global variables
    component_requirements = get_component_requirements()

    offers = get_offers()
    prices = get_prices(offers)

    assignment_matrix = get_assignment_matrix()

    vm_types = get_vm_types()

    conflicts = get_conflicts()

    added_component = get_added_component()

    greedy(0)


