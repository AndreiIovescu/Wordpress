import json

component_requirements = []
offers = []
assignment_matrix = []
vm_types = []
conflicts = {}
added_component = []


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
def check_conflict(assign_matrix, component_id, component2_id):
    for component in conflicts:
        if int(component) == component_id and component2_id in conflicts[component]:
            for i in range(len(assign_matrix[0])):
                if assign_matrix[component_id][i] == assign_matrix[component2_id][i] == 1:
                    return True
        else:
            return False
    return False


def check_lower_bound(component_id, bound):
    if compute_frequency(component_id) >= bound:
        return True
    return False


def check_upper_bound(component_id, bound):
    if compute_frequency(component_id) <= bound:
        return True
    return False


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    component_requirements = get_component_requirements()
    print(component_requirements)

    offers = get_offers()
    print(offers)

    assignment_matrix = get_assignment_matrix()
    print(assignment_matrix)

    vm_types = get_vm_types()
    print(vm_types)

    conflicts = get_conflicts()
    print(conflicts)

    print(check_conflict(assignment_matrix, 4, 1))

    added_component = get_added_component()
    print(added_component)

    print(compute_frequency(0))

    print(check_lower_bound(1, 2))

