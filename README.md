# Wordpress
The structure of this repository is the following:

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
  
    This directory will contain MiniZinc models for any problem (we have Wordpress so far).
    
  - ### **Output**
  
  - ### **Surrogate**
