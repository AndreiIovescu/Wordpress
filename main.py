import csv
import json
import time
from copy import deepcopy


def get_components(file):
    """
    Reads the file received as parameter and builds the components list in the desired way
    We use in code just a component's name and the requirements for cpu, memory and storage

    Args:
        file: The file location

    Returns:
        components_list: A list of dictionaries, each dictionary representing a component used in the application
        and the requirements that we use in the code
    """
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
    """
    Loads the list of constraints from the received file

    Args:
       file: The file location

    Returns:
        json_list: a list of dictionaries, where each dictionary represents a constraint used in our problem and
        the information we have about it
    """
    with open(file) as f:
        json_list = json.load(f)
        return json_list['restrictions']


def get_offers(file):
    """
    Extracts from the parameter file a list with the virtual machine offers and their hardware requirements

    Args:
       file: The file location

    Returns:
        offers_list: A list of dictionaries, where each dictionary represents a virtual machine offer and it's hardware
         requirements like: cpu, memory and storage
    """
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
    """
    Reads the content of the received file, that represents the input from a problem solved with Minizinc

    Args:
       file: The file location

    Returns:
        json_list: A list that contains information from a problem solved using MiniZinc. It's content are: the assignment
         matrix, the type array and the price array
    """
    with open(file) as f:
        json_list = json.load(f)
        return json_list


def compute_frequency(component_id, matrix):
    """
    This function computes the number of deployed instances for the component with the provided id
    That means it goes trough the assignment matrix at row 'component_id' and adds all the elements
    Since a value of 1 in the assignment matrix means 'deployed' we can find the occurrence of a certain component

    Args:
        component_id: The index of the assignment matrix row that corresponds to the involved component
        matrix: The assignment matrix on which the frequency is computed

    Returns:
       component_frequency: an integer representing the number of times that the component with id 'component_id' was
       deployed in the application
    """
    component_frequency = sum(matrix[component_id])
    return component_frequency


def check_conflicts(constraint, matrix, component_id, constraints_list):
    """
    Checks on each machine if the component with parameter id and his conflict are both deployed
    Returns true if no such conflict exists

    Args:
        constraint: The constraint instance that is going to be checked
        matrix: The assignment matrix on which the constraint is going to be checked
        component_id: The index of the assignment matrix row that corresponds to the involved component
        constraints_list:

    Returns:
        response: boolean value that takes value True when the constraint is fulfilled or False otherwise
    """
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


def check_lower_bound(constraint, matrix, component_id, constraints_list):
    """
    Checks whether the component with provided id is deployed at least 'bound' times

    Args:
        constraint: The constraint instance that is going to be checked
        matrix: The assignment matrix on which the constraint is going to be checked
        component_id:
        constraints_list:

    Returns:
        response: boolean value that takes value True when the constraint is fulfilled or False otherwise
    """
    if compute_frequency(constraint['compsIdList'][0], matrix) >= constraint['bound']:
        return True
    return False


def check_upper_bound(constraint, matrix, component_id, constraints_list):
    """
    Checks whether the component with provided id is deployed at most 'bound' times

    Args:
        constraint: The constraint instance that is going to be checked
        matrix: The assignment matrix on which the constraint is going to be checked
        component_id:
        constraints_list:

    Returns:
        response: boolean value that takes value True when the constraint is fulfilled or False otherwise
    """
    if compute_frequency(constraint['compsIdList'][0], matrix) <= constraint['bound']:
        return True
    return False


def check_equal_bound(constraint, matrix, component_id, constraints_list):
    """
    Checks whether the component with provided id is deployed exactly 'bound' times

    Args:
        constraint: The constraint instance that is going to be checked
        matrix: The assignment matrix on which the constraint is going to be checked
        component_id:
        constraints_list:

    Returns:
        response: boolean value that takes value True when the constraint is fulfilled or False otherwise
    """
    if compute_frequency(constraint['compsIdList'][0], matrix) == constraint['bound']:
        return True
    return False


def check_exclusive_deployment(constraint, matrix, component_id, constraints_list):
    """
       This function checks whether the components with the provided id are both deployed in the system

        Args:
            constraint: The constraint instance that is going to be checked
            matrix: The assignment matrix on which the constraint is going to be checked
            component_id:
            constraints_list:

        Returns:
            response: boolean value that takes value True when the constraint is fulfilled or False otherwise
    """
    if compute_frequency(constraint['alphaCompId'], matrix) > 0 \
            and compute_frequency(constraint['betaCompId'], matrix) > 0:
        return False
    return True


def check_require_provide(constraint, matrix, component_id, constraints_list):
    """
    This function verifies that the numerical constraint between two components is respected
    Ex: Wordpress requires at least three instances of mysql and mysql can serve at most 2 Wordpress
    This is a require provide constraint since we have limitations for both 'require' and 'provider'

    Args:
        constraint: The constraint instance that is going to be checked
        matrix: The assignment matrix on which the constraint is going to be checked
        component_id:
        constraints_list:

    Returns:
        response: boolean value that takes value True when the constraint is fulfilled or False otherwise
    """
    if compute_frequency(constraint['alphaCompId'], matrix) * constraint['alphaCompIdInstances'] <= \
            compute_frequency(constraint['betaCompId'], matrix) * constraint['betaCompIdInstances']:
        return True
    return False


def check_provide(constraint, matrix, component_id, constraints_list):
    """
    This function is similar to require provide, but this time we have no knowledge about one component in the relation
    Ex:HTTP Balancer requires at least one wordpress instance and http balancer can serve at most 3 Wordpress instances.
    We know that http requires at least 1 wordpress and can serve at most 3,
    but we know nothing about what wordpress offers.

    Args:
        constraint: The constraint instance that is going to be checked
        matrix: The assignment matrix on which the constraint is going to be checked
        component_id:
        constraints_list:

    Returns:
        response: boolean value that takes value True when the constraint is fulfilled or False otherwise
    """
    if compute_frequency(constraint['alphaCompId'], matrix) == 0 \
            or compute_frequency(constraint['betaCompId'], matrix) == 0:
        return True
    if compute_frequency(constraint['alphaCompId'], matrix) <= \
            constraint['alphaCompIdInstances'] * compute_frequency(constraint['betaCompId'], matrix):
        return True
    return False


def check_collocation(constraint, matrix, component_id, constraints_list):
    """
    This function checks whether two components are in collocation relation.
    A collocation relation means that on every machine where one of the components is deployed,
    the other one must be deployed too.

    Args:
        constraint: The constraint instance that is going to be checked
        matrix: The assignment matrix on which the constraint is going to be checked
        component_id:
        constraints_list:

    Returns:
        response: boolean value that takes value True when the constraint is fulfilled or False otherwise
    """
    for column in range(len(matrix[0])):
        if matrix[constraint['alphaCompId']][column] != matrix[constraint['betaCompId']][column]:
            return False
    return True


def check_full_deployment(constraint, matrix, component_id, constraints_list):
    """
    This function checks that the component with provided id is deployed on every machine that allows it.
    If there is a machine where the component would cause a conflict that machine is not included.

    Args:
        constraint: The constraint instance that is going to be checked
        matrix: The assignment matrix on which the constraint is going to be checked
        component_id:
        constraints_list: The list with all the constraints that our problem must fulfill

    Returns:
         response: boolean value that takes value True when the constraint is fulfilled or False otherwise
    """
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


def handle_collocation(constraint, new_matrix, types, component_id, components_list,
                       constraints_list, offers_list, initial_matrix, check_new_columns):
    """
       A function that will handle a collocation constraint that was broken.
       We check all the new machines, and we add all the missing components.

       Args:
           constraint: The constraint instance that is going to be checked
           new_matrix: The assignment matrix on which the constraint is going to be checked
           types:
           component_id:
           components_list:
           constraints_list:
           offers_list:
           initial_matrix:
           check_new_columns:

       Returns:
            new_matrix: The new assignment matrix, updated after trying to fix the false constraint
       """
    for column in range(len(initial_matrix[0]), len(new_matrix[0])):
        deployed_components = get_deployed_components(new_matrix, column)
        if constraint['alphaCompId'] in deployed_components and constraint['betaCompId'] not in deployed_components:
            new_matrix[constraint['betaCompId']][column] = 1
        elif constraint['betaCompId'] in deployed_components and constraint['alphaCompId'] not in deployed_components:
            new_matrix[constraint['alphaCompId']][column] = 1
    return new_matrix


def handle_full_deployment(constraint, new_matrix, types, component_id, components_list,
                           constraints_list, offers_list, initial_matrix, check_new_columns):
    """
        A function that will try to deploy the component with parameter id on any machine where it was not deployed.
        It will do so only on the machine where no conflict would be created.

        Args:
            constraint: The constraint instance that is going to be checked
            new_matrix: The assignment matrix on which the constraint is going to be checked
            types:
            component_id:
            components_list:
            constraints_list: The list with all the constraints that our problem must fulfill
            offers_list:
            initial_matrix: The first assignment matrix configuration, before trying to solve the problem
            check_new_columns:

        Returns:
            new_matrix: The new assignment matrix, updated after trying to fix the false constraint
    """
    conflict_components = get_component_conflicts(constraint['alphaCompId'], constraints_list)
    for column in range(len(initial_matrix[0]), len(new_matrix[0])):
        deployed_components = get_deployed_components(new_matrix, column)
        deployed_but_conflict = [component for component in deployed_components if component in conflict_components]
        if constraint['alphaCompId'] not in deployed_components and deployed_but_conflict is None:
            new_matrix[constraint['alphaCompId']][column] = 1
    return new_matrix


def handle_provide(constraint, new_matrix, types, component_id, components_list,
                   constraints_list, offers_list, initial_matrix, check_new_columns):
    """
        A function that tries to fix a provide constraint that is false

        Args:
            constraint: The constraint instance that is going to be checked
            new_matrix: The assignment matrix on which the constraint is going to be checked
            types: The type array that corresponds to the assignment matrix
            component_id: The index of the assignment matrix row that corresponds to the involved component
            components_list: The list of components involved in our problem and their hardware requirements
            constraints_list: The list with all the constraints that our problem must fulfill
            offers_list: The list of virtual machine offers from which we can choose
            initial_matrix: The first assignment matrix configuration, before trying to solve the problem
            check_new_columns: A boolean variable, if it is True we can check the machines that were not in the
                               initial setup and if it is False we just take a new machine for a new component

        Returns:
            new_matrix: The new assignment matrix, updated after trying to fix the false constraint
        """

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

        # If we can place the new component on a machine the we already had
        # This variable will take the value of that machine's id (it will be -1 if we can't place it on any machine)
        new_component_column = check_existing_machines(initial_matrix, types, component_id,
                                                       components_list, constraints_list, offers_list)
        # In case we can place the component on previous machines, we just update the assignment matrix accordingly
        # We don't have to check anything else, because we don't rent a new machine
        if new_component_column >= 0:
            new_matrix[problem_component_id][new_component_column] = 1
            return new_matrix

    if check_new_columns == "Yes":
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


def handle_require_provide(constraint, new_matrix, types, component_id, components_list,
                           constraints_list, offers_list, initial_matrix, check_new_columns):
    """
        A function that tries to fix a require_provide constraint that is false

        Args:
            constraint: The constraint instance that is going to be checked
            new_matrix: The assignment matrix on which the constraint is going to be checked
            types: The type array that corresponds to the assignment matrix
            component_id: The index of the assignment matrix row that corresponds to the involved component
            components_list: The list of components involved in our problem and their hardware requirements
            constraints_list: The list with all the constraints that our problem must fulfill
            offers_list: The list of virtual machine offers from which we can choose
            initial_matrix: The first assignment matrix configuration, before trying to solve the problem
            check_new_columns: A boolean variable, if it is True we can check the machines that were not in the
                               initial setup and if it is False we just take a new machine for a new component

        Returns:
            new_matrix: The new assignment matrix, updated after trying to fix the false constraint
    """
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

    # If we can place the new component on a machine the we already had
    # This variable will take the value of that machine's id (it will be -1 if we can't place it on any machine)
    new_component_column = check_existing_machines(initial_matrix, types, component_id,
                                                   components_list, constraints_list, offers_list)
    # In case we can place the component on previous machines, we just update the assignment matrix accordingly
    # We don't have to check anything else, because we don't rent a new machine
    if new_component_column >= 0:
        new_matrix[problem_component_id][new_component_column] = 1
        return new_matrix

    if check_new_columns == "Yes":
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


def handle_upper_bound(constraint, new_matrix, types, component_id, components_list,
                       constraints_list, offers_list, initial_matrix, check_new_columns):
    """
        A function that will return a message to inform the user that the maximum number of component with provided
        id was already deployed, therefore we can no longer deploy an instance of that component

        Args:
            constraint: The constraint instance that is going to be checked
            new_matrix:
            types:
            component_id:
            components_list:
            constraints_list:
            offers_list:
            initial_matrix:
            check_new_columns:

        Returns:
            message: Message that explains that this constraint cannot be fixed
    """
    return f"Upper bound reached for the component with id {constraint['compsIdList'][0]}." \
           f"No more instances can be deployed."


def handle_equal_bound(constraint, new_matrix, types, component_id, components_list,
                       constraints_list, offers_list, initial_matrix, check_new_columns):
    """
        A function that will return a message to inform the user that the component with provided id
        Must have an exact number of instances

        Args:
            constraint: The constraint instance that is going to be checked
            new_matrix:
            types:
            component_id:
            components_list:
            constraints_list:
            offers_list:
            initial_matrix:
            check_new_columns:

        Returns:
            message: Message that explains that this constraint cannot be fixed
        """
    return f"Cannot deploy another instance of component with id {component_id}. There should be exactly" \
           f" {constraint['bound']} instances of this component."


def handle_exclusive_deployment(constraint, new_matrix, types, component_id, components_list,
                                constraints_list, offers_list, initial_matrix, check_new_columns):
    """
        A function that will inform the user that he wants to add a component that cannot be deployed.
        Components that are in exclusive deployment cannot be deployed in the application together

        Args:
            constraint: The constraint instance that is going to be checked
            new_matrix:
            types:
            component_id:
            components_list:
            constraints_list:
            offers_list:
            initial_matrix:
            check_new_columns:

        Returns:
            message: Message that explains that this constraint cannot be fixed
        """
    if constraint['alphaCompId'] == component_id:
        problem_component_id = constraint['betaCompId']
    else:
        problem_component_id = constraint['alphaCompId']
    return f"Cannot deploy component with id {component_id} in the application. " \
           f"Component with id {problem_component_id} is deployed and they are in exclusive deployment relation."


def get_component_conflicts(component_id, constraints_list):
    """
       Function that returns all the conflicts for a given component
       It checks every conflict constraint if it contains the component with given id

       Args:
           component_id: The index of the assignment matrix row that corresponds to the involved component
           constraints_list: List with all the constraints that must be fulfilled

       Returns:
          component_conflicts: list containing the id of the components that are in conflict with the given one
    """
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


def check_column_placement(matrix, column_id, component_id, constraints_list):
    """
    A function that checks whether we can deploy the component with given id on the machine with given id
    To do that, we have to check such that the machine has no components that are in conflict with the given one

    Args:
       matrix: The assignment matrix on which we will verify if we can place a new component
       column_id: The index of the assignment matrix column that corresponds to the involved component
       component_id: The index of the assignment matrix row that corresponds to the involved component
       constraints_list: List with all the constraints that must be fulfilled

    Returns:
      response: Boolean value that takes value True if we can place the component with given id on the given column and
                takes value False otherwise
    """

    if matrix[component_id][column_id] == 1:
        return False
    component_conflicts = get_component_conflicts(component_id, constraints_list)
    for row in range(len(matrix)):
        if matrix[row][column_id] == 1 and row in component_conflicts:
            return False
    return True


def get_deployed_components(matrix, column_id):
    """
    Function that returns the id/id's of the deployed component/s on the column(machine) with provided id

    Args:
        matrix: The assignment matrix on which we will verify if we can place a new component
        column_id: The index of the assignment matrix column that corresponds to the involved component

    Returns:
        deployed_components: List that contains the id/id's of the component/s deployed on the machine with given id
    """
    deployed_components = []
    # By looping from 0 to len(matrix) we will check every component
    for row in range(len(matrix)):
        if matrix[row][column_id] == 1:
            deployed_components.append(row)
    return deployed_components


def get_free_space(machine_id, matrix, column_id, offers_list, components_list):
    """
    Function that returns the free amount of space on a given machine

    Args:
        machine_id: The index of the machine on which we want to compute the free space
        matrix: The assignment matrix on which we will verify if we can place a new component
        column_id: The index of the assignment matrix column that corresponds to the involved component
        offers_list: The list of virtual machine offers from which we can choose
        components_list: The list of components involved in our problem and their hardware requirements

    Returns:
       free_space: List that contains the free space left on a machine, after subtracting from the total machine
                   capacity, the amount occupied by the already deployed component/s on it
    """
    # We need to see first if there is anything deployed on the machine
    deployed_components = get_deployed_components(matrix, column_id)
    if not deployed_components:
        # We return the entire machine capacity since there is no deployed component
        free_space = [offers_list[machine_id][resource] for resource in offers_list[machine_id] if resource != 'Price']
        return free_space
    else:
        resources = [resource for resource in offers_list[machine_id] if resource != 'Price']
        # We return the remaining between the machine capacity and the already occupied space
        free_space = [offers_list[machine_id][resource] - components_list[deployed_component][resource]
                      for resource in resources for deployed_component in deployed_components]
        return free_space


def check_enough_space(free_space, component_id, components_list):
    """
    Checks if the free space on a machine is enough to deploy the component with provided id

    Args:
        free_space: List that contains the amount of free space available for the new component
        component_id: The index of the assignment matrix row that corresponds to the involved component
        components_list: The list of components involved in our problem and their hardware requirements

    Returns:
       response: Boolean variable that takes value of True if the free space on a machine is enough to deploy the
                 component with given id or value of False otherwise
    """

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


def get_component_constraints(component_id, constraints_list):
    """
    Build a list of all the constraints that involve the component with the parameter id

    Args:
        component_id: The index of the assignment matrix row that corresponds to the involved component
        constraints_list: List with all the constraints that must be fulfilled

    Returns:
       component_constraints: List that contains all the constraints that involve the given component
    """

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


def check_constraints(constraints_list, matrix, component_id):
    """
    Function that checks all the constraints that involve the component with parameter id and returns the false ones
    For each constraint we call the corresponding method that will check if it is false or not

    Args:
        constraints_list: List with all the constraints that must be fulfilled
        matrix: The assignment matrix on which we will verify if we can place a new component
        component_id: The index of the assignment matrix row that corresponds to the involved component

    Returns:
        false_constraints: List that contains all the false constraints from the given constraint list
    """
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


def add_column(matrix, component_id):
    """
    Builds a new matrix by adding a column to the one received as parameter
    The new column has 0 on every row but the one corresponding to the component with the parameter id

    Args:
        matrix: The assignment matrix on which we will verify if we can place a new component
        component_id: The index of the assignment matrix row that corresponds to the involved component

    Returns:
        new_matrix: A new assignment matrix obtained by adding a new column to the given one, with the component
                    with given id deployed on it
    """
    new_matrix = deepcopy(matrix)
    row_counter = 0
    for row in new_matrix:
        if row_counter == component_id:
            row.append(1)
        else:
            row.append(0)
        row_counter += 1
    return new_matrix


def handle_false_constraints(false_constraints, new_matrix, types, component_id, components_list,
                             constraints_list, offers_list, initial_matrix, check_new_columns):

    """
    A function that gets the name of each false constraint and calls the corresponding function to handle it

    Args:
        false_constraints: A list with constraints that were found to be false
        new_matrix: The assignment matrix on which the constraint is going to be checked
        types: The type array that corresponds to the assignment matrix
        component_id: The index of the assignment matrix row that corresponds to the involved component
        components_list: The list of components involved in our problem and their hardware requirements
        constraints_list: The list with all the constraints that our problem must fulfill
        offers_list: The list of virtual machine offers from which we can choose
        initial_matrix: The first assignment matrix configuration, before trying to solve the problem
        check_new_columns: A boolean variable, if it is True we can check the machines that were not in the
                           initial setup and if it is False we just take a new machine for a new component

    Returns:
        new_matrix: The new assignment matrix, updated after trying to fix the false constraints
    """
    for constraint in false_constraints:
        constraint_name = constraint['type']
        # All handling functions follow the convention: handle_constraint_name
        new_matrix = eval(
            f'handle_{constraint_name}'.lower() + "(constraint, new_matrix, types, component_id, components_list,"
                                                  "constraints_list, offers_list, initial_matrix, check_new_columns)"
        )
        # We check after every handle function call if the false constraint can be fixed or not
        # In general the result should be a new matrix, after fixing a constraint
        # If the type of new matrix is string, it means the constraint can't be fixed and the result is an error message
        if type(new_matrix) == str:
            return new_matrix
    return new_matrix


def get_final_matrix(new_matrix, types, component_id, components_list, component_constraints,
                     constraints_list, offers_list, initial_matrix, check_new_columns):
    """
    A function that handles the false constraints until we have a matrix that satisfies all the constraints

    Args:
        new_matrix: The assignment matrix on which the constraint is going to be checked
        types: The type array that corresponds to the assignment matrix
        component_id: The index of the assignment matrix row that corresponds to the involved component
        components_list: The list of components involved in our problem and their hardware requirements
        component_constraints: The list of constraints that involve the component with given id
        constraints_list: The list with all the constraints that our problem must fulfill
        offers_list: The list of virtual machine offers from which we can choose
        initial_matrix: The first assignment matrix configuration, before trying to solve the problem
        check_new_columns: A boolean variable, if it is True we can check the machines that were not in the
                           initial setup and if it is False we just take a new machine for a new component

    Returns:
        new_matrix: The new assignment matrix, updated after trying to fix the all the false constraints
    """
    false_constraints = check_constraints(constraints_list, new_matrix, component_id)
    while false_constraints:
        new_matrix = handle_false_constraints(
            false_constraints, new_matrix, types, component_id, components_list,
            constraints_list, offers_list, initial_matrix, check_new_columns
        )
        # After every attempt of fixing false constraints we want to see if the handling was able to run
        # If all went ok, then matrix will be the expected way, but if we were not able to fix then it's type is str
        # It will contain the error message regarding what went wrong
        if type(new_matrix) == str:
            return new_matrix
        false_constraints = check_constraints(constraints_list, new_matrix, component_id)
    return new_matrix


def get_new_resources(new_matrix, initial_matrix, components_list):
    """
    A function that returns a list containing the resource that each of the new components consume
    For each machine we have a dictionary with the sum of resources on that machine, all of those held in a list

    Args:
        new_matrix: The assignment matrix on which the constraint is going to be checked
        initial_matrix: The first assignment matrix configuration, before trying to solve the problem
        components_list: List that contains hardware requirements for all the components of our application

    Returns:
        new_components_resources: List that contains the hardware requirements of all the new components that have to
                                  to be added to our application
    """
    new_components_resources = []
    resources_keys = [key for key in components_list[0] if key != 'Name']
    # We check only the new machines
    for column in range(len(initial_matrix[0]), len(new_matrix[0])):
        deployed_components_id = get_deployed_components(new_matrix, column)
        components_dict = [components_list[index] for index in deployed_components_id]
        machine_resources = {resource: 0 for resource in resources_keys}
        for component in components_dict:
            for key in resources_keys:
                machine_resources[key] = machine_resources[key] + component[key]
        new_components_resources.append(machine_resources)
    return new_components_resources


def sort_offers(offers_list):
    """
    Sorts the received list in ascending order after the price

    Args:
        offers_list: The list that contains all the virtual machine offers, with their hardware requirements

    Returns:
        sorted_list: The offer list received as parameter, sorted in ascending order after their renting price
    """
    sorted_list = sorted(offers_list, key=lambda i: (i['Price']))
    return sorted_list


def choose_machine(offers_list, components_resources):
    """
    This function receives the list of offers and a list with the resources needed by the new components to be added
    It will return a list with the id of the chosen machines

    Args:
       offers_list: The list that contains all the virtual machine offers, with their hardware requirements
       components_resources: List that contains the hardware requirements of all the new components that have to
                             to be added to our application

    Returns:
       new machines: The id's of the machines that have been selected to deploy the new components on
    """
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


def check_existing_machines(matrix, types, component_id, components_list, constraints_list, offers_list):
    """
    A function that will verify if we can place the component with parameter id anywhere on the matrix received
    It returns the column/machine where we can deploy the component (if it exists) or -1 otherwise

    Args:
        matrix: The assignment matrix on which the constraint is going to be checked
        types: The type array that corresponds to the assignment matrix
        component_id: The index of the assignment matrix row that corresponds to the involved component
        components_list: The list of components involved in our problem and their hardware requirements
        constraints_list: The list with all the constraints that our problem must fulfill
        offers_list: The list of virtual machine offers from which we can choose

    Returns:
       column: Integer value that represents the already deployed column/machine on which we can place a new component.
               If there is no such column, it takes value -1
    """
    for column in range(len(matrix[component_id])):
        if check_column_placement(matrix, column, component_id, constraints_list):
            free_space = get_free_space(types[column], matrix, column, offers_list, components_list)
            if check_enough_space(free_space, component_id, components_list):
                test_matrix = deepcopy(matrix)
                test_matrix[component_id][column] = 1
                false_constraints = check_constraints(constraints_list, test_matrix, component_id)
                if not false_constraints:
                    return column
    return -1


def get_solution(matrix, initial_matrix, types, prices, offers_list, components_list):
    """
    We can have 2 kinds of solution handling

    Args:
       matrix: The assignment matrix on which the constraint is going to be checked
       initial_matrix: The first assignment matrix configuration, before trying to solve the problem
       types: The type array that corresponds to the assignment matrix
       prices: The price array that corresponds to the assignment matrix
       offers_list: The list of virtual machine offers from which we can choose
       components_list: The list of components involved in our problem and their hardware requirements

    Returns:
       column: Integer value that represents the already deployed column/machine on which we can place a new component.
              If there is no such column, it takes value -1
   """
    new_components_resources = get_new_resources(matrix, initial_matrix, components_list)

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


def write_solution(file, dictionary, runtime):
    """
    This function receives a file and a dictionary that contains the problem solution
    It will write the solution in the file, using csv convention

    Args:
       file: Path to the output file that we want to write to
       dictionary: A list of dictionaries that contain our problem's output (minimum price, minimum price for each vm)
       runtime: The time it took for the problem to be solved
    """
    with open(file, mode='w', newline='') as f:
        fieldnames = ['Price min value', 'Price for each machine', 'Time']
        writer = csv.DictWriter(f, fieldnames=fieldnames)

        writer.writeheader()
        min_price = sum(dictionary['Price Array'])
        writer.writerow({'Price min value': min_price, 'Price for each machine': dictionary['Price Array'],
                         'Time': runtime})


def solve_existing_machines(assignment_matrix, component_id, types, prices,
                            components_list, new_component_column, offers_list):
    """
    This method handles the case where we can solve the problem just by adding one more component to the initial matrix
    We just have to update the assignment matrix accordingly as the price and type array will remain the same
    This is done by calling the get_solution method

    Args:
       assignment_matrix: The assignment matrix that we work with
       component_id: The index of the assignment matrix row that corresponds to the involved component
       types: The type array that corresponds to the assignment matrix
       prices: The price array that corresponds to the assignment matrix
       components_list: The list of components involved in our problem and their hardware requirements
       new_component_column: The machine/column where the component with given id will be placed
       offers_list: The list of virtual machine offers from which we can choose

    Returns:
       output_dictionary: A list of dictionaries that contain our problem's output
                          (minimum price, minimum price for each vm)
    """
    new_matrix = deepcopy(assignment_matrix)
    new_matrix[component_id][new_component_column] = 1
    output_dictionary = get_solution(assignment_matrix, assignment_matrix, types,
                                     prices, offers_list, components_list)
    return output_dictionary


def greedy(assignment_matrix, component_id, types, prices, components_list,
           component_constraints, constraints_list, offers_list, greedy_type):
    """
    This method is used to apply the suitable greedy algorithm of the two options (min vm or distinct vm)
    Since the process is almost identical, we have this method that can apply both of them
    We know which one to apply because of the greedy type parameter (can be "min_vm" or "distinct_vm")

    Args:
        assignment_matrix: The first assignment matrix configuration, before trying to solve the problem
        component_id: The index of the assignment matrix row that corresponds to the involved component
        types: The type array that corresponds to the assignment matrix
        prices: The price array that corresponds to the assignment matrix
        components_list: The list of components involved in our problem and their hardware requirements
        component_constraints: The constraints that involve the component with given id
        constraints_list: The list with all the constraints that our problem must fulfill
        offers_list: The list of virtual machine offers from which we can choose
        greedy_type: We need to specify which type of Greedy approach we will use to solve the problem
                     The 2 possible values are min_vm or distinct_vm

    Returns:
        output_dictionary: A list of dictionaries that contain our problem's output
                          (minimum price, minimum price for each vm)
                          If the problem can't be solved this will be a message that tries to explain what went wrong
    """
    new_matrix = deepcopy(assignment_matrix)
    new_matrix = add_column(new_matrix, component_id)

    if greedy_type == "min_vm":
        new_matrix = get_final_matrix(
            new_matrix, types, component_id, components_list, component_constraints,
            constraints_list, offers_list, assignment_matrix, "Yes"
        )
    elif greedy_type == "distinct_vm":
        new_matrix = get_final_matrix(
            new_matrix, types, component_id, components_list, component_constraints,
            constraints_list, offers_list, assignment_matrix, "No"
        )

    if type(new_matrix) == str:
        return new_matrix
    else:
        new_vm_types = deepcopy(types)
        new_price_array = deepcopy(prices)
        output_dictionary = get_solution(new_matrix, assignment_matrix, new_vm_types,
                                         new_price_array, offers_list, components_list)
        return output_dictionary


def validate_result(result, minizinc_solution, greedy_type, runtime):
    """
    This function is used to verify if the problem was solved or not

    Args:
        result: The result that was obtained after solving the problem
        minizinc_solution: The name of the minizinc problem that was used as input to our problem
        greedy_type: The greedy method that was used to obtain this particular result
        runtime: The time that it took for the problem to be solved
    """
    # If the length of the output is 1, it means the output is just the error message saying what went wrong
    if len(result) == 1:
        print(result)
    # If the output is ok, we can write the solution to the corresponding file
    # We use the minizinc solution name to create the name for the output csv, to which we also add the greedy type
    else:
        minizinc_solution = minizinc_solution.replace('Input/Greedy_Input/', '')
        minizinc_solution = minizinc_solution.replace('_Input.json', '')
        write_solution(f"Output/Greedy_Output/{greedy_type}/{minizinc_solution}_{greedy_type}.csv", result, runtime)


def solve_problem(problem_file, offers_file, minizinc_solution, added_component):
    """
    The actual 'solving' method, where we apply the previous functions to solve the problem

    Args:
        problem_file: The path to the file that contains the problem information (the components and constraints)
        offers_file: The path to the file that contains the virtual machine offers
        minizinc_solution: The path to the minizinc solution that will be used as input to our problem
        added_component: The id of the component that we want to add to the application
    """
    components_list = get_components(problem_file)

    constraints_list = get_constraints(problem_file)

    offers_list = get_offers(offers_file)

    existing_solution = parse_existing_solution(minizinc_solution)

    # Load the necessary input from the existing solution
    assignment_matrix = existing_solution['Assignment Matrix']
    vm_types = existing_solution["Type Array"]
    prices = existing_solution["Price Array"]
    component_id = added_component
    # Get the constraints that involve the added component
    component_constraints = get_component_constraints(component_id, constraints_list)

    start_time = time.time()

    # If we can place the component on a machine that we already have, this will get the value of that machine's id
    # In case there is no such machine, it will have value -1
    new_component_column = check_existing_machines(assignment_matrix, vm_types, component_id,
                                                   components_list, constraints_list, offers_list)

    # Since we can place the component on existing machines, we just have to update the information we want to output
    # We are interested in the new assignment matrix, price array and vm types array
    if new_component_column >= 0:
        result = solve_existing_machines(assignment_matrix, component_id, vm_types, prices,
                                         components_list, new_component_column, offers_list)

        run_time = time.time() - start_time
        write_solution(f"{minizinc_solution.replace('_Input.json', '')}_Output.csv", result, run_time)
        return
    # If we reach here it means we will need at least 1 new machine (for the added component)
    # Using the get_final_matrix method we find out either the new assignment matrix or an error message
    # The matrix that satisfies all requirements or an error message explaining what causes the error
    else:
        # This is the time before applying each algorithm so it is needed for both of them
        # We save it now so we can add it later to the second algorithm
        intermediary_time = time.time() - start_time
        result_min_vm = greedy(assignment_matrix, component_id, vm_types, prices, components_list,
                               component_constraints, constraints_list, offers_list, "min_vm")

        run_time_min_vm = time.time() - start_time
        start_time = time.time()

        result_distinct_vm = greedy(assignment_matrix, component_id, vm_types, prices, components_list,
                                    component_constraints, constraints_list, offers_list, "distinct_vm")

        run_time_distinct_vm = time.time() - start_time + intermediary_time

        validate_result(result_min_vm, minizinc_solution, "MinVM", run_time_min_vm)
        validate_result(result_distinct_vm, minizinc_solution, "DistinctVM", run_time_distinct_vm)

        return


if __name__ == '__main__':
    problem_name = "Wordpress"
    offers_number = 20
    wordpress_instances = 3
    component_to_add = 0

    solve_problem(
        f"Input/Problem_Description/{problem_name}.json",
        f"Input/Offers/offers_{offers_number}.json",
        f"Input/Greedy_Input/{problem_name}{wordpress_instances}_Offers{offers_number}_Input.json",
        component_to_add
    )
