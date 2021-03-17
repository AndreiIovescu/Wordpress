import json

component_requirements = []
offers = []
assignment_matrix = []
vm_types = []


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