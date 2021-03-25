# Andrew Dunn
# 1/13/21
# M/CS 435

import numpy as np
from numpy import linalg as la

def randQuad(n):
    """ Takes an integer n as input and returns an nxn matrix, Q,
        and an nx1 vector, b. Q and b are randomly generated.
    """
    A = np.random.rand(n,n)
    b = np.random.rand(n,1)
    Q = np.matmul(A.transpose(), A)
    return Q,b

def myQuad(x,Q,b):
    """ Takes an nx1 vector x, an nxn matrix Q, and an nx1 vector
        b as inputs and returns r and g, where r is the value of
        the function f(x) = 0.5*x^T*Q*x - b^T*x and g is the gradient
        of f at x.
    """
    #Make sure the input is numpy compatible
    x = np.array(x)
    Q = np.array(Q)
    b = np.array(b)
    # Run f(x)
    r = 0.5 * np.matmul(x.transpose(), np.matmul(Q, x)) - np.matmul(b.transpose(), x)
    # Since we're hoping for a symmetric, positive definite Q, I'm taking
    # the shortcut to the gradient where d/dx[x^TAx] = 2Ax if A is symmetric
    # and positive definite.
    g = np.matmul(Q,x) - b
    return r,g

def myPerm(x):
    """ Takes the nx1 vector x as input and returns r,g where r is the value
        of the PermII function evaluated at x and g is the gradient of the
        PermII function at x.
    """
    # Generate output
    r = 0
    g = np.zeros(x.shape)
    n = x.size
    # Loop the function and compute
    for i in range(1,n+1):
        r_i = 0
        g_i = np.zeros(x.shape)
        for j in range(1,n+1):
            # Inner sum that gets squared before adding to outer sum
            r_i += (j + 10)*(x[j-1]**i - (1/(j**i)))
        #g[i-1] = 2*r_i + (i+10)*i*(x[i-1]**i-1)
        g_i[:] = 2*r_i
        r += r_i**2
        for l in range(1,n+1):
            #Add the inside part of the chain rule expression
            g_i[l-1] = g_i[l-1]*(10 + l)*(i * x[l-1]**(i-1))
        g += g_i
            
    return r,g

def myArmijo(x,p,a,r,f):
    """ An implementation of Armijo line search with c=1e-4
        Input: x- current point, p- descent direction, a- largest step size,
                r- reduction factor, f- function being minimized
        Output: alfa- calculated step size, n- number of calls to f
    """
    # Establish constants and output
    c = 1e-4
    alfa = a
    gamma = 0.95 # c < gamma < 1 has to hold
    n = 0
    f_k,g_k = f(x)
    n+= 1
    f_k1,g_k1 = f(x + (a*p))
    ex = f_k + c*a*np.transpose(g_k)*p
    ct = gamma * abs(np.matmul(np.transpose(g_k),p))
    n+= 1
    curve = abs(np.matmul(np.transpose(g_k1),p)) <= ct
    while alfa > 0:
        if f_k1.all()<=ex.all() & curve:
            return alfa, n
        alfa *= r
        f_k1,g_k1 = f(x + (alfa*p))
        curve = abs(np.matmul(np.transpose(g_k1),p)) <= ct
        ex = (f_k + c*alfa*np.transpose(g_k)*p)
        n+= 1
    raise Exception("Line search failure!")
    
def mySteep(x, tol, f):
    """ Implements the steepest descent algorithm using
        Armijo line search.
        Inputs: x- the point to be evaluated, tol- tolerance,
                f- the function to be minimized
        Output: opt- the approximate optimum, val- the function value at opt
                n- the number of function calls to f
    """
    # Declare output
    val = np.inf
    n = 1 # Start at 1 since we'll call the function at least once
    opt = x
    its = 1000 # Adjustable constant for max number of iterations
    r = 0.25 # Used in myArmijo, tune for optimality
    a = 4   # Another tunable for getting more efficient search
    for i in range(its):
        val,grad = f(opt)
        if la.norm(grad) < tol:
            return opt, val, n
        p = -grad
        alfa,n_i = myArmijo(opt,p,a,r,f)
        opt += alfa*p
        n += 1+n_i
    
    return opt, val, n

def myBFGS(x, tol, f):
    """ Implements the BFGS algorithm using
        Armijo line search.
        Inputs: x- the point to be evaluated, tol- tolerance,
                f- the function to be minimized
        Output: opt- the approximate optimum, val- the function value at opt
                n- the number of function calls to f
    """
    ##Output declaration
    opt = x
    val = np.inf
    n = 2 #We're guaranteed to call f at least twice
    its = 1000 #Max iterations, make it bigger if you want
    
    ##Adding constants
    h_k = np.eye(np.shape(x)[0]) #read col. dims from x, make h_0 = I_x
    r = 0.85 # Used in myArmijo, tune for optimality
    a = 1# Another tunable for getting more efficient search
    
    #Time to iterate the loop
    val, grad = f(opt)
    for i in range(its):
        if la.norm(grad) <= tol:
##            print("Step: ", i) #Uncomment to see how many iterations in execution
            return opt, val, n
        pk = -np.dot(h_k, grad)
        
        #Do that line search
        alfa, n_i = myArmijo(opt,pk,a,r,f)
        dx = (opt+alfa*pk)-opt

        opt = opt + alfa*pk #update x_k+1
        
        dxt = dx.transpose()
        nVal, nGrad = f(opt)
        if nVal > val:
            opt = opt - 0.5*alfa*pk
            nVal, nGrad = f(opt)
        dg = nGrad - grad
        dgt = dg.transpose()
        
        #Now the fancy bit
        denom1 = np.dot(dgt, dx)[0,0] #indexed to extract raw float
        if denom1 != 0:
            denom1 = 1/denom1
        denom2 = np.dot(dxt, dg)[0,0] #same as denom1
        if denom2 != 0:
            denom2 = 1/denom2
        if (denom1==0) & (denom2==0):#had some issues with this debugging
            print(dx) #So it stayed in as error-proofing
            print(dg)
            raise Exception("Change not possible! H_{k+1} == H_k")
        sca = 1 + np.dot(dgt, np.dot(h_k, dg)) * denom1
        mat1 = sca * np.dot(dx,dxt) * denom2
        mat2 = np.matmul(h_k, np.dot(dg,dxt))
        mat2 = mat2 + mat2.transpose()
        mat2 = mat2* denom2
        h_k = h_k + (mat1 - mat2)
        
        #Book-keeping
        n += 1+n_i
        grad = nGrad
        val = nVal
    return opt, val, n

    
########################################################################
##################### Main Method ######################################
########################################################################
if __name__ == '__main__':
    
    """ Beginning of main method
    """
    #print("This doesn't do anything yet ¯\_(ツ)_/¯")
    print("Execute myBFGS test!", '~^~v'*12, "Begin quadratic test\n", sep='\n')
    n = 5 # Dimensionality of the test
    t = 1e-4
    x = np.random.rand(n,1)+10
    Q,b = randQuad(n)
    f = lambda j:myQuad(j,Q,b)
    v,g = f(x)
    opt,val,count = myBFGS(x,t,f)
    print("Initial value: ", v)
    print("Final value: ", val)
    if val == f(opt)[0]:
        print("Checks out")
    print("Function value difference: ", v-val)
    print("X value difference:\n ", x-opt)
    truMin = np.dot(la.inv(Q), b)
    print("Absolute min diff:\n", truMin-opt)
    
    ########################################################################
    #######Perm Test: Kind of questionable
    print('\n','~^~v'*12, "Begin PermII test\n", sep='\n')
    
    #Establish ground truth minimizer
    permMin = np.ones((n,1))
    for i in range(np.size(permMin)):
        permMin[i] = 1/ (i+1)
    per = lambda y:myPerm(y)
    x = np.random.rand(n,1)
    vp,gp = per(x)
    optp, valp, m = myBFGS(x,t,per)
    print("Initial value: ", vp)
    print("Final value: ", valp)
    print("Function value difference: ", vp-valp)
    print("X value difference:\n ", x-optp)
    print("Difference to true minimizer: ", abs(optp-permMin))
    
    