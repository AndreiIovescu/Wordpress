import pandas as pd

if __name__ == '__main__':
    problem_name = "Wordpress"
    upper_bound = 12
    lower_bound = 3
    offers = [20, 40, 250, 500]
    extension = 'csv'

    for component_instances in range(lower_bound, upper_bound + 1):
        for offers_number in offers:
            files_list = [
                          f"Output/Greedy_Output/DistinctVM/{problem_name}{component_instances + 1}"
                          f"_Offers{offers_number}_DistinctVM.csv",
                          f"Output/Greedy_Output/MinVM/{problem_name}{component_instances + 1}"
                          f"_Offers{offers_number}_MinVM.csv",
                          f"Output/MiniZinc_Output/chuffed/{problem_name}{component_instances}"
                          f"_Offers{offers_number}_chuffed.csv"
            ]

            combined_csv = pd.concat([pd.read_csv(f) for f in files_list])
            # export to csv
            combined_csv.to_csv(f"Output/Combined_CSV/{problem_name}{component_instances}_Offers{offers_number}.csv",
                                index=False, encoding='utf-8-sig')





