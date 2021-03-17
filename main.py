component_requirements = []
offers = []
assignment_matrix = []
vm_types = []


def get_component_requirements():
    with open('components_requirements.txt', 'r') as f:
        components_list = [(line.strip()).split('[],') for line in f]
        return components_list


def get_offers():
    with open('offers.txt', 'r') as f:
        offers_list = [(line.strip()).split('[],') for line in f]
        return offers_list


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    component_requirements = get_component_requirements()
    print(component_requirements)
    for component in component_requirements:
        print(component)

    offers = get_offers()
    print(offers)
    for offer in offers:
        print(offer)

