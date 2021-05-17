%
% Wordpress application in MiniZinc
%
% This MiniZinc model was created by Andrei Iovescu, andrei.iovescu99@e-uvt.ro
%
% Input parameters
%%%%%%%%%%%%%%%%

% maximal number of virtual machines needed to be deployed (taken for each Wordpress instance from running Surrogate.mzn)
int: M;
% number of components of the Wordpress application
int: N;
% number of hardware requirements for a component (e.g. CPU, memory, Storage)
int: HR;
% number of virtual machines offers
int: VMNR;
% the minimum number of Wordpress component instances to be deployed
int: WP;

% minimum requirements for each component
array[1..N, 1..HR] of int: compReq;
% virtual machines offers
array[1..VMNR, 1..HR] of int: vmOffers; 
% the cost of virtual machines offers
array[1..VMNR] of int: prices;
% global variable used in conflict constraints 
set of int : S = { i | i in 1..N};

%%%%%%%%%%%%%%%%
% variables
%%%%%%%%%%%%%%%%
% components number

% assignment matrix a 
array[1..N, 1..M] of var 0..1: a; 
% type of VM
array[1..M] of var int: t; 
% occupancy vector
array[1..M] of var 0..1: v; 
% the following arrays will contain the data of the virtual machine where the i-th component has been deployed on ( i in 1..M )
array[1..M] of var 1..64: cpu; 
array[1..M] of var 1700..976000: mem; 
array[1..M] of var 1000..24000: storage; 
array[1..M] of var 0..16000: price;

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%%%%%% General Constraints %%%%%
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% checks if the component with id "compId" is deployed at least once and returns 1 if so or 0 otherwise
function var int: H(int: compId) 
  = if ( sum ( k in 1..M)(a[compId,k]) > 0 ) then 1  else 0 endif;
             
% a VM which has at least 1 deployed component has type different than 0 
predicate setType ( ) 
  = forall( i in 1..N, k in 1..M ) (a[i, k] == 1 -> t[k] > 0);

% basic allocation %                 
% every component is deployed at least once               
predicate basicAllocation (var set of int:exclusive) 
  = forall( i in S diff exclusive)(sum (k in 1..M) (a[i, k]) >= 1);

% an occupied VM has its corresponding occupancy vector initialized
predicate occupancy ( ) 
  = forall (k in 1..M )(sum ( i in 1..N) (a[i,k]) >= 1 -> v[k] = 1);
  
% capacity %    
% a component should be deployed on a machine that meets its hardware requirements
predicate capacity ()
  = forall( k in 1..M, h in 1..HR )( sum (i in 1..N) ( a[i,k] * compReq[i,h]) <= vmOffers[t[k],h] ); 
  
% if a machine "k" is deployed and has type "o" then the k-th cpu,storage, memory and price values should correspond to it
predicate link ()
  =  forall(k in 1..M, o in 1..VMNR) ( (v[k] == 1 /\ t[k] == o) -> (cpu[k] = vmOffers[o,1] /\ mem[k] = vmOffers[o,2] /\ storage[k] = vmOffers[o,3] /\ price[k] = prices[o] ) );

% an unocuppied VM has no type assigned to it              
predicate link2 ( ) 
  = forall ( k in 1..M)(sum ( i in 1..N) (a[i,k]) == 0 -> t[k] = 0);

% Application-specific constraints
% no other balancer or mysql instance is deployed on the same machine as varnish 
predicate conflict (int: compId, var set of int: conflicts ) 
  = forall ( k in 1..M, i in conflicts )( a[compId, k] + a[i, k] <= 1 );

% sets a lower bound for the number of instances of component with id "compID"
predicate lowerBound (int: compId, int: bound)
  = sum ( k in 1..M) ( a[compId,k] ) >= bound ;
            
% sets a upper bound for the number of instances of component with id "compID"
predicate upperBound (int: compId, int: bound)
  = sum ( k in 1..M) ( a[compId,k] ) <= bound ;

/* % creates a require provide relation between components with id alpha and beta
predicate requireProvide(int: alphaCompId,int: betaCompId, int: alphaCompIdInstances,int: betaCompIdInstances ) 
  = betaCompIdInstances * sum (k in 1..M) (a[alphaCompId,k]) <= alphaCompIdInstances * sum (k in 1..M)(a[betaCompId,k]); */ 
  
  predicate requireProvide(int: alphaCompId,int: betaCompId, int: alphaCompIdInstances,int: betaCompIdInstances ) 
  = alphaCompIdInstances * sum (k in 1..M) (a[alphaCompId,k]) <= betaCompIdInstances * sum (k in 1..M)(a[betaCompId,k]);
  
  
   predicate Provide(int: alphaCompId,int: betaCompId, int: alphaCompIdInstances) 
  =  sum (k in 1..M) (a[alphaCompId,k]) <= alphaCompIdInstances * sum (k in 1..M)(a[betaCompId,k]);
  

% creates an exclusive deployment relation between components with id alpha and beta            
predicate exclusiveDeployment(int: alphaCompId,int: betaCompId)
  = sum(k in 1..M) (a[alphaCompId,k]) > 0 xor sum(k in 1..M) (a[betaCompId,k]) > 0; 
                              
%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%%%% Modelling Wordpress %%%
%%%%%%%%%%%%%%%%%%%%%%%%%%%%                                                              
% if a machine has at least 1 deployed component on it then its type cannot be 0
constraint setType();

% every component which is not in exclusiveDeployment relation should be deployed at least once
constraint basicAllocation({3,4,5});

% marks a machine as occupied in the occupancy array v
constraint occupancy ();

% a component should be deployed on a machine that meets its hardware requirements
constraint capacity();

% makes sure that a deployed machine has its corresponding cpu, memory, storage and price assigned to it
constraint link ();

% an unocuppied machine has no type assigned to it 
constraint link2();

% DNS Balancer requires at least one instance of wordpress and dns balancer can serve at most 7 Wordpress instances
constraint (sum (k in 1..M) (a[3,k]) > 0 ) -> Provide(1, 3, 7);

% HTTP Balancer requires at least one wordpress instance and http balancer can serve at most 3 Wordpress instances.
constraint (sum (k in 1..M) (a[4,k]) > 0 ) -> Provide(1, 4, 3);

% Wordpress requires at least three instances of mysql and mysql can serve at most 2 Wordpress
constraint requireProvide(1, 2, 2, 3);

% only one type of Balancer must be deployed
constraint exclusiveDeployment(3, 4);

% Varnish should not be deployed on the same machine with MySQL, HTTP Balancer or DNS Balancer
constraint conflict(5, {2,3,4});

% set the minimum number of Wordpress component instances to be deployed as a lower bound
constraint lowerBound(1, WP);

% if http balancer is deployed then at least 2 instances of varnish must be deployed too
constraint lowerBound(5, 2);

% at least 2 different entry points to the MySQL cluster
constraint lowerBound(2, 2); 

% no more than 1 DNS server deployed in the administrative domain.
constraint upperBound (3, 1);

% balancer components must be placed on a single VM, so they are considered to be in conflict with all the other components
constraint conflict(3, {1,2,5});

% balancer components must be placed on a single VM, so they are considered to be in conflict with all the other components
constraint conflict(4, {1,2,5});

%constraint forall(k in 1..M - 1)(price[k] >= price[k+1]);

% solve the problem such that the cost of virtual machines is the minimal one
solve minimize sum(p in price) (p);


% output in a csv like style
output ["Min Price"] ++ [", Type Array"] ++ [", Cpu Array"] ++ [", Memory Array"] ++ [", Storage Array"] ++ [", Price Array \n"] ++ 
       [show(sum(p in price)(p))] ++ [","] ++
       [show_int(5,t[k])|k in 1..M] ++ [","]++
       [show_int(5,cpu[k]) | k in 1..M] ++ [","]++
       [show_int(10,mem[k]) | k in 1..M] ++ [","]++
       [show_int(10,storage[k]) | k in 1..M] ++[","]++
       [show_int(10,price[k]) | k in 1..M] ++ [", \n"]++
       [" Assignment Matrix \n"] ++
       [show_int(5,a[i,k]) ++ if k == M then "\n" else "" endif | i in 1..N, k in 1..M ];
        %pret total (min)*/
        
      
  