import json
from copy import deepcopy


# Reads the file received as parameter and builds the components list in the desired way
# We use in code just a component's name and the requirements for cpu, memory and storage
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


# Loads the list of constraints from the received file
def get_constraints(file):
    with open(file) as f:
        json_list = json.load(f)
        return json_list['restrictions']


# Returns a list with the offers and their requirements that will be used in code: cpu, memory, storage, price
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


# Returns a list with the content of the received file, that represents the input from a problem solved with minizinc
def parse_existing_solution(file):
    with open(file) as f:
        json_list = json.load(f)
        return json_list


# This function computes the number of deployed instances for the component with the provided id
# That means it goes trough the assignment matrix at row 'component_id' and adds all the elements
# Since a value of 1 in the assignment matrix means 'deployed' we can find the occurrence of a certain component
def compute_frequency(component_id, matrix):
    component_frequency = sum(matrix[component_id])
    return component_frequency


# Checks on each machine if the component with parameter id and his conflict are both deployed
# Returns true if no such conflict exists
def check_conflicts(constraint, matrix, component_id, constraints_list):
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


# Checks whether the component with provided id is deployed at least 'bound' times
def check_lower_bound(constraint, matrix, component_id, constraints_list):
    if compute_frequency(constraint['compsIdList'][0], matrix) >= constraint['bound']:
        return True
    return False


# Checks whether the component with provided id is deployed at most 'bound' times
def check_upper_bound(constraint, matrix, component_id, constraints_list):
    if compute_frequency(constraint['compsIdList'][0], matrix) <= constraint['bound']:
        return True
    return False


# Checks whether the component with provided id is deployed exactly 'bound' times
def check_equal_bound(constraint, matrix, component_id, constraints_list):
    if compute_frequency(constraint['compsIdList'][0], matrix) == constraint['bound']:
        return True
    return False


# This function checks whether the components with the provided id are both deployed in the system
def check_exclusive_deployment(constraint, matrix, component_id, constraints_list):
    if compute_frequency(constraint['alphaCompId'], matrix) > 0 \
            and compute_frequency(constraint['betaCompId'], matrix) > 0:
        return False
    return True


# This function verifies that the numerical constraint between two components is respected
# Ex: Wordpress requires at least three instances of mysql and mysql can serve at most 2 Wordpress
# This is a require provide constraint since we have limitations for both 'require' and 'provider'
def check_require_provide(constraint, matrix, component_id, constraints_list):
    if compute_frequency(constraint['alphaCompId'], matrix) * constraint['alphaCompIdInstances'] <= \
            compute_frequency(constraint['betaCompId'], matrix) * constraint['betaCompIdInstances']:
        return True
    return False


# This function is similar to require provide, but this time we have no knowledge about one component in the relation
# Ex:HTTP Balancer requires at least one wordpress instance and http balancer can serve at most 3 Wordpress instances.
# We know that http requires at least 1 wordpress can serve at most 3, but we know nothing about what wordpress offers.
def check_provide(constraint, matrix, component_id, constraints_list):
    if compute_frequency(constraint['alphaCompId'], matrix) == 0 \
            or compute_frequency(constraint['betaCompId'], matrix) == 0:
        return True
    if compute_frequency(constraint['alphaCompId'], matrix) <= \
            constraint['alphaCompIdInstances'] * compute_frequency(constraint['betaCompId'], matrix):
        return True
    return False


# This function checks whether two components are in collocation relation.
# A collocation relation means that on every machine where one of the components is deployed, the other one must be too.
def check_collocation(constraint, matrix, component_id, constraints_list):
    for column in range(len(matrix[0])):
        if matrix[constraint['alphaCompId']][column] != matrix[constraint['betaCompId']][column]:
            return False
    return True


# This function checks that the component with provided id is deployed on every machine that allows it.
# If there is a machine where the component would cause a conflict that machine is not included.
def check_full_deployment(constraint, matrix, component_id, constraints_list):
    conflicts = get_component_conflicts(constraint['alphaCompId'], constraints_list)
    for column in range(len(matrix[0])):
        deployed_components = get_deployed_components(matrix, column)
        # We create a list with the elements that are deployed but are in conflict with the component
        components_in_conflict = [
                    component for component in deployed_components
                    if constraint['alphaCompId'] not in conflicts
        ]
        # If on any machine the component is not deployed, but there is no conflict to stop that, we return false
        # The list being empty means that the component could actually be deployed on that machine
        if matrix[constraint['alphaCompId']][column] == 0 and components_in_conflict is None:
            return False
    return True


# A function that will handle a collocation constraint that was broken.
# We check all the new machines, and we add all the missing components
def handle_collocation(constraint, new_matrix, types, component_id, components_list,
                       constraints_list, offers_list, initial_matrix):
    for column in range(len(initial_matrix[0]), len(new_matrix[0])):
        deployed_components = get_deployed_components(new_matrix, column)
        if constraint['alphaCompId'] in deployed_components and constraint['betaCompId'] not in deployed_components:
            new_matrix[constraint['betaCompId']][column] = 1
        elif constraint['betaCompId'] in deployed_components and constraint['alphaCompId'] not in deployed_components:
            new_matrix[constraint['alphaCompId']][column] = 1
    return new_matrix


# A function that will try to deploy the component with parameter id on any machine where it was not deployed.
# It will do so only on the machine where no conflict would be created.
def handle_full_deployment(constraint, new_matrix, types, component_id, components_list,
                           constraints_list, offers_list, initial_matrix):
    conflict_components = get_component_conflicts(constraint['alphaCompId'], constraints_list)
    for column in range(len(initial_matrix[0]), len(new_matrix[0])):
        deployed_components = get_deployed_components(new_matrix, column)
        deployed_but_conflict = [component for component in deployed_components if component in conflict_components]
        if constraint['alphaCompId'] not in deployed_components and deployed_but_conflict is None:
            new_matrix[constraint['alphaCompId']][column] = 1
    return new_matrix


# A function that tries to fix a provide constraint that is false
def handle_provide(constraint, new_matrix, types, component_id, components_list,
                   constraints_list, offers_list, initial_matrix, check_initial_matrix):
    problem_component_id = None

    # To know which component we will have to add, we must identify the problem component
    # We go from the last column of the assignment matrix and check each column
    # If we find any of the components involved in the constraint, we found the component that caused the inequality
    for column in reversed(range(len(initial_matrix[0]), len(new_matrix[0]))):
        deployed_components = get_deployed_components(new_matrix, column)
        if constraint['alphaCompId'] in deployed_components:
            # We have to add instances of this component since the alphaCompId was deployed and messed the constraint
            problem_component_id = constraint['betaCompId']
            component_id = constraint['alphaCompId']
            break
        elif constraint['betaCompId'] in deployed_components:
            problem_component_id = constraint['alphaCompId']
            component_id = constraint['betaCompId']
            break

    if check_initial_matrix == "Yes":

        # If we can place the new component on a machine the we already had
        # This variable will take the value of that machine's id (it will be -1 if we can't place it on any machine)
        new_component_column = check_existing_machines(initial_matrix, types, component_id,
                                                       components_list, constraints_list, offers_list)
        # In case we can place the component on previous machines, we just update the assignment matrix accordingly
        # We don't have to check anything else, because we don't rent a new machine
        if new_component_column >= 0:
            new_matrix[problem_component_id][new_component_column] = 1
            return new_matrix

        # With new columns we want to see if we work with the original matrix, or with a matrix with new
        # machines/columns
        new_columns = len(new_matrix[0]) - len(initial_matrix[0])
        # In case there are new machines, we don't actually know yet what kind of machine they are At this step,
        # we have to check on the new machines if we can place the new component, regarding the constraints
        if new_columns > 0:
            for column in range(len(initial_matrix[0]), len(new_matrix[0])):
                if check_column_placement(new_matrix, column, problem_component_id, constraints_list):
                    new_matrix[problem_component_id][column] = 1
                    return new_matrix

    # If we can't place the component on what we already have, we have to get a new machine and update the matrix
    matrix = add_column(new_matrix, problem_component_id)
    return matrix


# A function that tries to fix a require_provide constraint that is false
def handle_require_provide(constraint, new_matrix, types, component_id, components_list,
                           constraints_list, offers_list, initial_matrix, check_initial_matrix):
    problem_component_id = None

    # To know which component we will have to add, we must identify the problem component
    # We go from the last column of the assignment matrix and check each column
    # If we find any of the components involved in the constraint, we found the component that caused the inequality
    for column in reversed(range(len(initial_matrix[0]), len(new_matrix[0]))):
        deployed_components = get_deployed_components(new_matrix, column)
        if constraint['alphaCompId'] in deployed_components:
            # We have to add instances of this component since the alphaCompId was deployed and messed the constraint
            problem_component_id = constraint['betaCompId']
            component_id = constraint['alphaCompId']
            break
        elif constraint['betaCompId'] in deployed_components:
            problem_component_id = constraint['alphaCompId']
            component_id = constraint['betaCompId']
            break

    if check_initial_matrix == "Yes":

        # If we can place the new component on a machine the we already had
        # This variable will take the value of that machine's id (it will be -1 if we can't place it on any machine)
        new_component_column = check_existing_machines(initial_matrix, types, component_id,
                                                       components_list, constraints_list, offers_list)
        # In case we can place the component on previous machines, we just update the assignment matrix accordingly
        # We don't have to check anything else, because we don't rent a new machine
        if new_component_column >= 0:
            new_matrix[problem_component_id][new_component_column] = 1
            return new_matrix

        # With new columns we want to see if we work with the original matrix,or with a matrix with new machines/columns
        new_columns = len(new_matrix[0]) - len(initial_matrix[0])
        # In case there are new machines, we don't actually know yet what kind of machine they are
        # At this step,we have to check on the new machines if we can place the new component, regarding the constraints
        if new_columns > 0:
            for column in range(len(initial_matrix[0]), len(new_matrix[0])):
                if check_column_placement(new_matrix, column, problem_component_id, constraints_list):
                    new_matrix[problem_component_id][column] = 1
                    return new_matrix

    # If we can't place the component on what we already have, we have to get a new machine and update the matrix
    matrix = add_column(new_matrix, problem_component_id)
    return matrix


# A function that will return a message to inform the user that the maximum number of component with provided id
# was already deployed, therefore we can no longer deploy an instance of that component
def handle_upper_bound(constraint, new_matrix, types, component_id, components_list,
                       constraints_list, offers_list, initial_matrix):
    return f"Upper bound reached for the component with id {constraint['compsIdList'][0]}." \
           f"No more instances can be deployed."


# A function that will return a message to inform the user that the component with provided id
# Must have an exact number of instances
def handle_equal_bound(constraint, new_matrix, initial_matrix, component_id, constraints_list):
    return f"Cannot deploy another instance of component with id {component_id}. There should be exactly" \
           f" {constraint['bound']} instances of this component."


# A function that will inform the user that he wants to add a component that cannot be deployed.
# Components that are in exclusive deployment cannot be deployed in the application together
def handle_exclusive_deployment(constraint, new_matrix, initial_matrix, component_id, constraints_list):
    if constraint['alphaCompId'] == component_id:
        problem_component_id = constraint['betaCompId']
    else:
        problem_component_id = constraint['alphaCompId']
    return f"Cannot deploy component with id {component_id} in the application. " \
           f"Component with id {problem_component_id} is deployed and they are in exclusive deployment relation."


# Function that returns all the conflicts for a given component
# It checks every conflict constraint if it contains the component with given id
def get_component_conflicts(component_id, constraints_list):
    conflicts = [constraint for constraint in constraints_list if constraint['type'] == 'Conflicts']
    component_conflicts = []
    for conflict in conflicts:
        # A component id could be found in the 'alphaCompId' field
        # It means our component has a list of components that conflict with it, that are found in 'compsIdList'
        if conflict['alphaCompId'] == component_id:
            for component in conflict['compsIdList']:
                if component not in component_conflicts:
                    component_conflicts.append(component)
        # Also, we could find the given id in the conflict list of another component
        # If that is the case, and that component's id is not in the conflict list already , we add it too
        if component_id in conflict['compsIdList'] and conflict['alphaCompId'] not in component_conflicts:
            component_conflicts.append(conflict['alphaCompId'])
    return component_conflicts


# A function that checks whether we can deploy the component with given id on the machine with given id
# To do that, we have to check such that the machine has no components that are in conflict with the given one
def check_column_placement(matrix, column_id, component_id, constraints_list):
    if matrix[component_id][column_id] == 1:
        return False
    component_conflicts = get_component_conflicts(component_id, constraints_list)
    for row in range(len(matrix)):
        if matrix[row][column_id] == 1 and row in component_conflicts:
            return False
    return True


# Function that returns the id/id's of the deployed component/s on the column(machine) with provided id
def get_deployed_components(matrix, column_id):
    deployed_components = []
    # By looping from 0 to len(matrix) we will check every component
    for row in range(len(matrix)):
        if matrix[row][column_id] == 1:
            deployed_components.append(row)
    return deployed_components


# Function that returns the free amount of space on a given machine
def get_free_space(machine_id, matrix, column, offers_list, components_list):
    # We need to see first if there is anything deployed on the machine
    deployed_components = get_deployed_components(matrix, column)
    if not deployed_components:
        # We return the entire machine capacity since there is no deployed component
        free_space = [offers_list[machine_id][resource] for resource in offers_list[machine_id] if resource != 'Price']
        return free_space
    else:
        resources = [resource for resource in offers[machine_id] if resource != 'Price']
        # We return the remaining between the machine capacity and the already occupied space
        free_space = [offers_list[machine_id][resource] - components_list[deployed_component][resource]
                      for resource in resources for deployed_component in deployed_components]
        return free_space


# Checks if the free space on a machine is enough to deploy the component with provided id
def check_enough_space(free_space, component_id, components_list):
    # Resources will contain cpu, memory and storage
    resources = [resource for resource in components_list[component_id] if resource != 'Name']
    # Compute remaining space by subtracting the component requirements from the free space
    remaining_space = [
        free_space[index] - components_list[component_id][resources[index]]
        for index in range(len(free_space))
    ]
    # If the space left for any of the requirements is smaller than 0, it means we don't have enough space
    for space in remaining_space:
        if space <= 0:
            return False
    return True


# Build a list of all the constraints that involve the component with the parameter id
def get_component_constraints(component_id, constraints_list):
    component_constraints = []
    # The only keys that can contain a component id
    id_keys = ['alphaCompId', 'betaCompId', 'compsIdList']
    for constraint in constraints_list:
        # Gets the corresponding keys for that specific constraint
        constraint_keys = [value for value in constraint if value in id_keys]
        for id_key in constraint_keys:
            # Some of the keys can have lists as value so we have to check if they contain our component id
            if type(constraint[id_key]) is list:
                if component_id in constraint[id_key]:
                    component_constraints.append(constraint)
            else:
                if component_id == constraint[id_key]:
                    component_constraints.append(constraint)
    return component_constraints


# Function that checks all the constraints that involve the component with parameter id and returns the false ones
# For each constraint we call the corresponding method that will check if it is false or not
def check_constraints(constraints_list, matrix, component_id):
    false_constraints = []
    for constraint in constraints_list:
        constraint_name = constraint['type']
        # Calls the the corresponding function using the constraint's name
        # The check functions all follow the convention: check_constraint_name
        corresponding_function_result = eval(
            f'check_{constraint_name}'.lower() + "(constraint, matrix, component_id, constraints_list)"
        )
        if not corresponding_function_result:
            false_constraints.append(constraint)
    return false_constraints


# Builds a new matrix by adding a column to the one received as parameter
# The new column has 0 on every row but the one corresponding to the component with the parameter id
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


# A function that gets the name of each false constraint and calls the corresponding function to handle it
def handle_false_constraints(false_constraints, new_matrix, types, component_id, components_list,
                             constraints_list, offers_list, initial_matrix, check_initial_matrix):
    for constraint in false_constraints:
        constraint_name = constraint['type']
        # All handling functions follow the convention: handle_constraint_name
        new_matrix = eval(
            f'handle_{constraint_name}'.lower() + "(constraint, new_matrix, types, component_id, components_list,"
                                                  "constraints_list, offers_list, initial_matrix, check_initial_matrix)"
        )
        # We check after every handle function call if the false constraint can be fixed or not
        # In general the result should be a new matrix, after fixing a constraint
        # If the type of new matrix is string, it means the constraint can't be fixed and the result is an error message
        if type(new_matrix) == str:
            return new_matrix
    return new_matrix


# A function that handles the false constraints until we have a matrix that satisfies all the constraints
def get_final_matrix(matrix, types, component_id, components_list, component_constraints,
                     constraints_list, offers_list, initial_matrix, check_initial_matrix):
    false_constraints = check_constraints(constraints_list, matrix, component_id)
    while false_constraints:
        matrix = handle_false_constraints(
            false_constraints, matrix, types, component_id,components_list,
            constraints_list, offers_list, initial_matrix, check_initial_matrix
        )
        # After every attempt of fixing false constraints we want to see if the handling was able to run
        # If all went ok, then matrix will be the expected way, but if we were not able to fix then it's type is str
        # It will contain the error message regarding what went wrong
        if type(matrix) == str:
            return matrix
        false_constraints = check_constraints(constraints_list, matrix, component_id)
    return matrix


# A function that returns a list containing the resource that each of the new components consume
# For each machine we have a dictionary with the sum of resources on that machine, all of those held in a list
def get_new_resources(new_matrix, initial_matrix):
    new_components_resources = []
    resources_keys = [key for key in components[0] if key != 'Name']
    # We check only the new machines
    for column in range(len(initial_matrix[0]), len(new_matrix[0])):
        deployed_components_id = get_deployed_components(new_matrix, column)
        components_dict = [components[index] for index in deployed_components_id]
        machine_resources = {resource: 0 for resource in resources_keys}
        for component in components_dict:
            for key in resources_keys:
                machine_resources[key] = machine_resources[key] + component[key]
        new_components_resources.append(machine_resources)
    return new_components_resources


# Sorts the received list in ascending order after the price
def sort_offers(offers_list):
    sorted_list = sorted(offers_list, key=lambda i: (i['Price']))
    return sorted_list


# This function receives the list of offers and a list with the resources needed by the new components to be added
# It will return a list with the id of the chosen machines
def choose_machine(offers_list, components_resources):
    new_machines = []
    sorted_offers = deepcopy(offers_list)
    # To choose a corresponding machine, we sort the list of offers in ascending order after price
    sorted_offers = sort_offers(sorted_offers)

    for machine_resources in components_resources:
        # We consider only the offers that satisfy the hardware requirements
        matching_offers = [
            offer for offer in sorted_offers
            if offer['Cpu'] >= machine_resources['Cpu']
            and offer['Memory'] >= machine_resources['Memory']
            and offer['Storage'] >= machine_resources['Storage']
        ]

        # We take the first machine from the matching offers
        # By doing this, we make sure that the hardware requirements are satisfied and we have the lowest price
        new_machines.append(offers_list.index(matching_offers[0]))
    return new_machines


# A function that will verify if we can place the component with parameter id anywhere on the matrix received
# It returns the column/machine where we can deploy the component (if it exists) or -1 otherwise
def check_existing_machines(matrix, types_array, component_id, components_list, constraints_list, offers_list):
    for column in range(len(matrix[component_id])):
        if check_column_placement(matrix, column, component_id, constraints_list):
            free_space = get_free_space(types_array[column], matrix, column, offers_list, components_list)
            if check_enough_space(free_space, component_id, components_list):
                test_matrix = deepcopy(matrix)
                test_matrix[component_id][column] = 1
                false_constraints = check_constraints(constraints_list, test_matrix, component_id)
                if not false_constraints:
                    return column
    return -1


# We can have 2 kinds of solution handling
def get_solution(matrix, initial_matrix, types, prices, offers_list):
    new_components_resources = get_new_resources(matrix, initial_matrix)

    # If this is empty, it means we were able to deploy the component/s on the machines we already had
    # In that case, we just need to return the matrix and arrays with price and vm types; they are not modified
    if not new_components_resources:
        output_dictionary = {
            'Assignment Matrix': matrix,
            'Type Array': types,
            'Price Array': prices
        }
        return output_dictionary

    # If we needed new machines for deployment, we now have to choose the new machines type
    new_machines_id = choose_machine(offers_list, new_components_resources)
    for machine_id in new_machines_id:
        types.append(machine_id)
        prices.append(offers_list[machine_id]['Price'])
    output_dictionary = {
        'Assignment Matrix': matrix,
        'Type Array': types,
        'Price Array': prices
    }
    # We can return the updated values after choosing the machines
    return output_dictionary


# This function receives a file and a dictionary that contains the problem solution
# It will write the solution in the file, using json convention
def write_solution_to_file(file, operation, dictionary):
    with open(file, "w") as f:
        f.write(json.dumps(dictionary))


# The actual 'solving' method, where we apply the previous functions to solve the problem
def solve_problem(solution, components_list, component_id, constraints_list, offers_list):
    assignment_matrix = solution['Assignment Matrix']
    vm_types = solution["Type Array"]
    prices = solution["Price Array"]
    component_constraints = get_component_constraints(component_id, constraints_list)

    new_component_column = check_existing_machines(assignment_matrix, vm_types, component_id,
                                                   components_list, constraints_list, offers_list)

    if new_component_column >= 0:
        new_matrix = deepcopy(assignment_matrix)
        new_matrix[component_id][new_component_column] = 1
        output_dictionary = get_solution(assignment_matrix, assignment_matrix, vm_types, prices, offers_list)
        write_solution_to_file("Wordpress3_Offers20_Output.json", "w", output_dictionary)
        return
    else:
        less_machines_matrix = deepcopy(assignment_matrix)
        less_machines_matrix = add_column(less_machines_matrix, component_id)
        less_machines_matrix = get_final_matrix(
            less_machines_matrix, vm_types, component_id, components_list, component_constraints,
            constraints_list, offers_list, assignment_matrix, "Yes"
        )

        if type(less_machines_matrix) == str:
            print(less_machines_matrix)
        else:
            output_dictionary = get_solution(less_machines_matrix, assignment_matrix, vm_types, prices, offers_list)
            write_solution_to_file("Wordpress3_Offers20_Output.json", "w", output_dictionary)

        one_comp_machines_matrix = deepcopy(assignment_matrix)
        one_comp_machines_matrix = add_column(one_comp_machines_matrix, component_id)
        one_comp_machines_matrix = get_final_matrix(
            one_comp_machines_matrix, vm_types, component_id, components_list, component_constraints,
            constraints_list, offers_list, assignment_matrix, "No"
        )

        if type(one_comp_machines_matrix) == str:
            print(one_comp_machines_matrix)
        else:
            output_dictionary = get_solution(one_comp_machines_matrix, assignment_matrix, vm_types, prices, offers_list)
            write_solution_to_file("Wordpress3_Offers20_Output.json", "a", output_dictionary)
        return one_comp_machines_matrix, vm_types, prices


if __name__ == '__main__':
    components = get_components("Wordpress3.json")

    constraints = get_constraints("Wordpress3.json")

    offers = get_offers("offers_20.json")

    existing_solution = parse_existing_solution("Wordpress3_Offers20_Input.json")

    comp_id = existing_solution['Added Component']

    new_assignment_matrix, new_vm_types, new_price_array = solve_problem(existing_solution, components,
                                                                         comp_id, constraints, offers)

    for row in new_assignment_matrix:
        print(row)
    print(new_vm_types)
    print(new_price_array)
