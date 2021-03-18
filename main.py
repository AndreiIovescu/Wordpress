import json

component_requirements = []
offers = []
assignment_matrix = []
vm_types = []
conflicts = {}


def get_component_requirements():
    with open('data.txt') as f:
        components_list = json.load(f)
        return components_list["Assignment Matrix"]


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


# the function first checks whether the two components could be in conflict
# if they can't, it will return false as there is no conflict and we don't have to check
# if the two can be in conflict, then we have to check the assignment matrix
# if the two rows that correspond to the components have the value 1 at the same position, then there exists a conflict
# that is because they have been deployed on the same machine although that does not follow the constraints
def check_conflict(assign_matrix, conf, component_id, component2_id):
    for component in conf:
        if int(component) == component_id and component2_id in conf[component]:
            for i in range(len(assign_matrix[0])):
                if assign_matrix[component_id][i] == assign_matrix[component2_id][i] == 1:
                    return True
        else:
            return False
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

    print(check_conflict(assignment_matrix, conflicts, 4, 1))
