'''
Created on Jun 30, 2018

@author: Rodrigo Silva
'''

from pyFTS.common import fts
import numpy as np
import skfuzzy as fuzz
from skfuzzy import control as ctrl
import matplotlib.pyplot as mplt
import time
#import plotly.offline as plt
#import plotly.graph_objs as go
import itertools
#plt.init_notebook_mode()

class SilvaIncrementalFTS(fts.FTS):
    
    #def __init__(self, **kwargs):
    #    
    #    #super(SilvaIncrementalFTS, self)._init_(order=1, **kwargs)
    #    self.name = "Incremental FTS"
    #    self.shortname = "IncFTS"
    #    self.incremental_init()
    def __init__(self,fs_params = [], ftype = 'triang', order = 1, nsets = 7,
                         do_plots = False):
        
        self.incremental_init(fs_params, ftype, order, nsets, do_plots)
    
    def incremental_init(self, fs_params = [], ftype = 'triang', order = 1, nsets = 7,
                         do_plots = False):
        ''' SilvaIncrementalFTS class parameters
    
        Args:
            fs_params: fuzzy sets paramenters
            ftype:     fuzzy set type (FOR NOW IT ONLY IMPLEMENTS TRIANGULAR FUZZY SETSD)
            order:     FTS order
            nsets:     number of fuzzy sets
        
        '''
        
        self.do_plots = do_plots
        self.fs_params = fs_params # Fuzzy set parameters
        self.ftype = ftype # Type of fuzzy set (For nor now it only implements triangular fuzzy sets)
        self.order = order #  FTS order (For now it only implements first order FTSs)
        
        self.centers = [] # Fuzzy sets centers
        self.rules = [] # Fuzzy logic Rules 
        
        self.lastx = [] # Last seen sample
        self.nsets = nsets # number of fuzzy sets
        self.data_mu = 0 # Data mean
        self.data_sigma = 0 # Data standard deviation
        self.data_n = 0  # Total number of samples
        self.data_max = 0
        self.data_min = 0
        self.sigma_multiplier = 3
        
        
    def generate_sets(self,lb,ub,nsets):
        
        self.fs_params = []
        self.centers = []
        
        self.centers = np.linspace(lb, ub, nsets)
        step = self.centers[1]-self.centers[0]
        self.fs_params = self.fs_params + [[s-step, s, s+step] for s in self.centers]
        
        self.fs_params[0][0] = -np.inf
        self.fs_params[len(self.fs_params)-1][2] = np.inf
    # Compute memberships
    
    def membership(self,x,fs_params,ftype):
        ''' Computes the membership values
    
        Args:
            x:         stream of values
            fs_params: fuzzy sets paramenters
            ftype:     fuzzy set type (FOR NOW IT ONLY IMPLEMENTS TRIANGULAR FUZZY SETSD)
        
        Returns:
            membership: membership (n x m)-matrix (len(x) x len(fuzzy_sets))  
        '''
    
        x = np.array(x) #Convert to numpy arrays
        # Compute memberships based on the type of fuzzy set
        mb = []
        if ftype == 'triang':
            for par in fs_params:
                mb.append([self.triangular_membership(i_x, par) for i_x in x])
                        
        mb = np.vstack(mb) # membership from list to matrix
        
        return mb
    
    def triangular_membership(self,x,setparams):
        """Computes the membership of a value with respect to the fuzzy set defined by setparameters. 
        This specific method implements triangular fuzzy sets. 

        Args:
            x: Point
            setparams: Fuzzy set paramenters

        Returns:
            mu: membership 
            
        """
    
            # For readability
        a = setparams[0];
        b = setparams[1];
        c = setparams[2];
        
        #print('Partitioner: {} {} {}'.format(a,b,c))
        
        if np.isinf(-a) and x < b:
            return 1
        if np.isinf(c) and x > b:
            return 1
        
        if x < a or x > c:
            return 0
        elif x >= a and x <= b:
            return (x-a)/(b-a)
        elif x == b:
            return 1
        elif x>b and x<=c:
            return (c-x)/(c-b)
        
        return None
    
    def plot_fuzzy_sets(self, start, stop, begin = 0, scale = 1, nsteps = 1000):       
        """Plots the fuzzy sets for a given interval.
    
        Args:
            start: starting point
            stop: stopping point
            nsteps: number of steps
            
        """
        #generate array of points
        x = np.linspace(start,stop,nsteps)
        
        #Compute memberships
        membership = self.membership(x,self.fs_params,self.ftype) 
    
        #Plot sets
        for i in range(membership.shape[0]):
            mplt.plot(membership[i,:]*scale + begin,x)
            
        #mplt.show()
            
    # Convert to fuzzy values
    
    def fuzzify(self,x, mb = []):
        ''' Fuzzify a set of values given the respective membership matrix
    
        Args:
            x:   stream of crisp values
            mb: matrix of membership values
        
        Returns:
            fx: a list of fuzzified values 
        '''
        if not mb:
            mb = self.membership(x,self.fs_params,self.ftype)
    
        fx = [np.argmax(mb[:,i]) for i in np.arange(len(x))] #fuzzified values
        
        return fx
    
    def generate_rules(self,x):
        ''' Generates a set of fuzzy rules given an stream of data (len(x) >= order) 
    
        Args:
            x:    data values
        
        Returns:
            rules: a list of fuzzy rules 
        '''
        
        fuzzified_data = self.fuzzify(x)
        rules = []
                
        # Start using sets because it is neater
        for i in range(len(self.centers)):
            rules.append(set())
        
        for i in range(len(fuzzified_data)-1):
            rules[fuzzified_data[i]].update(set([fuzzified_data[i+1]]))
        
        # Convert back to lists 
        for i in range(len(rules)):
            rules[i] = list(rules[i])
        
        return rules
    
    def print_rules(self):
        ''' Prints the sets of fuzzy logic relationships (FLRs) derived from data x
    
        Args:
            x:    x values
        
        '''
        
        if self.order == 1:
            for i in np.arange(len(self.rules)):
                s = 'A{} -> '.format(i)
                for r in self.rules[i]:
                    s  = s + 'A{} '.format(r)
                print(s)
                
    def update_bounds(self):
        
        lb = np.minimum(self.data_min,self.data_mu - self.sigma_multiplier*self.data_sigma)
        ub = np.maximum(self.data_max,self.data_mu + self.sigma_multiplier*self.data_sigma)
        
        #lb = self.data_mu - self.sigma_multiplier*self.data_sigma
        #ub = self.data_mu + self.sigma_multiplier*self.data_sigma
        
        #lb = self.data_min
        #ub = self.data_max
        
        return [lb,ub]
    
    def train(self, data, **kwargs):
        #fts.FTS.train(self, data, **kwargs)
        """Initializes the FTS with some data

        Args:
            data: list of data values 
        """
        
        
        # Compute data stastistics
        self.data_n = len(data)
        self.data_mu = np.mean(data)
        self.data_sigma = np.std(data)
        self.data_max = np.max(data)
        self.data_min = np.min(data)
        
        bounds = self.update_bounds()
        lb = bounds[0]
        ub = bounds[1]
        
        # Generate fuzzy sets 
        self.generate_sets(lb,ub,self.nsets)
        
        # Generate Rules
        self.rules = self.generate_rules(data)
        
        #Store last value
        self.lastx = data[len(data)-1]
    
    def forecast(self, data, **kwargs):
        
        forecasts = []
        if self.do_plots:
            times = []
            samples = []
            t = 0
        
        for x in data:
            if self.do_plots:
                times.append(t)
                samples.append(x)
                mplt.cla()
                
            # 1) update fuzzy sets
            old_centers = self.centers.copy()
            # Update data stats
            self.data_n = self.data_n+1 
            self.data_mu = self.data_mu + (x - self.data_mu)/self.data_n
            var = self.data_sigma**2
            self.data_sigma =  np.sqrt( (self.data_n-2)/(self.data_n-1) 
                                        * var + (1/self.data_n) * (x - self.data_mu)**2)
            
            self.data_max = np.maximum(self.data_max,x)
            self.data_min = np.minimum(self.data_min,x)
            # Update sets
            
            bounds = self.update_bounds()
            lb = bounds[0]
            ub = bounds[1]
            self.generate_sets(lb,ub,self.nsets)
            
            
            # 2) Update rules
            self.update_rules(old_centers)
            self.print_rules()
            
            #3) Add latest rule
            # Fuzzify
            
            # Update
            ## Update rules with the new point
            antecendent = self.fuzzify([self.lastx])
            consequent = self.fuzzify([x])
            
            print(antecendent)
            print(consequent)
                       
            self.rules[antecendent[0]].update(consequent)
            
            ## Update current state
            ### Convert back to lists 
            self.rules = [list(r) for r in self.rules]
            
            self.lastx = x.copy()
            
            # 3) Forecast
            forecasts.append(self.forecast_weighted_average([x]))
            
            # plots
            print(self.do_plots)
            if self.do_plots:
                self.plot_fuzzy_sets(2000,14000,
                                 begin = -500, scale = 400, nsteps = 1000)
                
                mplt.plot(np.array(times)+1,forecasts,'b')
                mplt.plot(times,samples,'r')
                mplt.draw()
                mplt.pause(1e-17)
                time.sleep(1e-8)
                t += 1 
        
        if self.do_plots:
            mplt.show()
        return forecasts 
    
    def update_rules(self,old_centers):
        
        #centers_membership_matrix = self.membership(old_centers,self.fs_params,self.ftype)
        mappings = self.fuzzify(old_centers)
        
        ########## Improve this for efficiency! ################
        new_rules = self.rules.copy()
        
        for i in range(self.nsets):
            for j in range(len(new_rules[i])):
                new_rules[i][j] = mappings[new_rules[i][j]] 
        
        for i in range(self.nsets):
            self.rules[i] = set() # Eliminates copies if different fuzzy sets are mapped onto a single set
            
        for i in range(self.nsets):
            self.rules[mappings[i]].update(set(new_rules[i]))  # Eliminates copies if different fuzzy sets mapped onto a single set
        
        # Eliminate copies on the consequent
        #self.rules = [list(set(r)) for r in new_rules]
        ########################################################
    
                   
    def forecast_weighted_average(self,x):
        """Computes the defuzzified (numerical) values of x according to the model defined by this fts .

        Args:
            x: list of data values 
            
        """
        # Fuzzify
        membership_matrix = self.membership(x,self.fs_params,self.ftype)
        centers = self.centers;
        
        def_vals = np.zeros(len(x)) #storage for the defuzified values
        # Find matching antecendents
        
        for i in range(len(x)):
            memberships = membership_matrix[:,i]                        
        
            # Defuzzify
            #For each rule
            for j in range(len(self.rules)):
                # Compute the membership of x in the antecendent j
                mu = memberships[j]
                term = 0;
                 
                if self.rules[j]:
                    for k in range(len(self.rules[j])):
                        term = term + centers[self.rules[j][k]]
                    
                    def_vals[i] = def_vals[i] + (term/len(self.rules[j]))*mu
                else: # If the rule is empty, adopt persistence
                    def_vals[i] = def_vals[i] + centers[j]*mu
              
        # Return defuzified values
        return def_vals 