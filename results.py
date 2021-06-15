import pandas as pd
from pathlib import Path

if __name__ == '__main__':
    problem_name = "Wordpress"
    upper_bound = 12
    lower_bound = 3
    offers = [20, 40, 250, 500]
    extension = 'csv'

    for component_instances in range(lower_bound, upper_bound + 1):
        for offers_number in offers:
            files_list = []
            distinct_vm_file = Path(
                f"Output/Greedy_Output/DistinctVM/{problem_name}{component_instances}"
                f"_Offers{offers_number}_DistinctVM.csv",
            )
            if distinct_vm_file.is_file():
                files_list.append(distinct_vm_file)

            min_vm_file = Path(
                f"Output/Greedy_Output/MinVM/{problem_name}{component_instances}"
                f"_Offers{offers_number}_MinVM.csv",
            )
            if min_vm_file.is_file():
                files_list.append(min_vm_file)

            minizinc_file = Path(
                f"Output/MiniZinc_Output/chuffed/{problem_name}{component_instances}"
                f"_Offers{offers_number}_chuffed.csv"
            )
            if minizinc_file.is_file():
                files_list.append(minizinc_file)
                
            if files_list:
                combined_csv = pd.concat([pd.read_csv(f) for f in files_list])
                # export to csv
                combined_csv.to_csv(
                    f"Output/Combined_CSV/{problem_name}{component_instances}_Offers{offers_number}.csv",
                    index=False, encoding='utf-8-sig'
                )
