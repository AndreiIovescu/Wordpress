# Wordpress
The structure of this repository is the following:

 - ### **main.py**
   
   This is the file where the Greedy algorithms are implemented. 
 
 - ### **surrogate.py**

   This file is used to run the surrogate problem with the MiniZinc Python Interface. It will run it for any number of Wordpress instances, between two given values, the lower and upper bounds namely. 
   
 - ### **script.py**
 
   This file is used to access the MiniZinc Python Interface. Using it we solve every possible instance of our problem: WordpressN_OffersVMNRFor every N in [3,4,...,12] and VMNR in [20, 40, 250, 500]
   
 - ### **Input directory**
    - **DZN_Files**
    
      Contains the input data for the problems solved with MiniZinc. They can serve for any number of Wordpress instances , only the vm offers change (20, 40, 250, 500 offers)
 
    - **Greedy_Input**

      Contains configurations that were obtained with MiniZinc. We use them as inputs for the greedy algorithms, to obtain a new configuration based on them, with at least 1 more Wordpress component deployed.
      
    - **Offers**
    
      Contains json files with vm offers from cloud providers. We have a file for each different number of offers (20, 40, 250, or 500). 
      
    - **Problem_Description**
    
      Contains a file with the description of the problem, in our case Wordpress. The file specifies the components of the application and the constraints between them. 
      
  - ### **Models**
  
    This directory will contain the MiniZinc models for any problem (we have Wordpress so far).
    
  - ### **Output**
  
    - **Greedy_Output**
      - **DistinctVM**
      
        In this directory we can find the results of the greedy algorithm *DistinctVM*, that places new components on different vms.
      - **MinVM**
    
        In this directory we can find the results of the greedy algorithm *MinVM*, that places new components on the same vm as long as the application constraints allow it.
    - **MiniZinc_Output**
      - **Chuffed**
      
        In this directory we can find the results of the MiniZinc model that was solved using Chuffed.
      - **Gecode**
      
        In this directory we can find the results of the MiniZinc model that was solved using Gecode.
      - **OR-TOOLS**
      
        In this directory we can find the results of the MiniZinc model that was solved using OR-TOOLS.
  - ### **Surrogate**
    
    In this directory we can find the MiniZinc model of the surrogate problem (Surrogate.mzn). We must solve this problem in order to estimate the number of virtual machines needed to deploy the entire application, based on the minimum number of wordpress components to be deployed. 
    
    There is also a file called Surrogate.csv which contains a mapping between a particular problem and the estimated number of vm's estimated using the surrogate problem. Ex: 3 Wordpress -> 8 vms, 4 Wordpress -> 10 vms , ..., etc.
