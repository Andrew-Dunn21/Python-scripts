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
    n = 0
    f_k,g_k = f(x)
    n+= 1
    f_k1,g_k1 = f(x + (a*p))
    ex = (f_k + c*a*np.transpose(g_k)*p)
    n+= 1
    while alfa > 0:
        if f_k1.all()<=ex.all():
            return alfa, n
        alfa *= r
        f_k1,g_k1 = f(x + (alfa*p))
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
    r = 0.1 # Used in myArmijo, tune for optimality
    a = 1   # Another tunable for getting more efficient search
    for i in range(its):
        val,grad = f(opt)
        if la.norm(grad) < tol:
            return opt, val, n
        
        alfa,n_i = myArmijo(x,-grad,a,r,f)
        opt += alfa
        n += 1+n_i
    
    
    print("Conditions not met, returning what we found.")
    return opt, val, n

########################################################################
####### Attempts at testing methods; Not too trustworthy ###############
########################################################################
def gradTestQ(x):
    """ Verifies the gradient against an approximate calculation.
    """
    x = np.array(x)
    n = x.size
    Q,b = randQuad(n)
    # Build some tools
    outShape = x.shape
    dells = np.zeros(x.shape)
    # Loop x
    for i in range(x.size):
        d_i = np.zeros(x.shape)
        d_i[i] = abs(np.random.rand() * 1e-4)
        delta = d_i[i]
        xp = x + d_i
        xm = x - d_i
        val1 = 0.5 * np.matmul(xp.transpose(), np.matmul(Q, xp)) - np.matmul(b.transpose(), xp)
        val2 = 0.5 * np.matmul(xm.transpose(), np.matmul(Q, xm)) - np.matmul(b.transpose(), xm)
        fval = (val1 - val2) / delta
        dells[i] = fval
    _,g = myQuad(x,Q,b)
    eps = abs(g-dells)
    print(eps)
    return

def gradTestP(x):
    """ Verifies the gradient against an approximate calculation.
    """
    x = np.array(x)
    # Build some tools
    dells = np.zeros(x.shape)
    delta = abs(np.random.rand() * 1e-7)
    # Loop x
    for i in range(x.size):
        d_i = np.zeros(x.shape)
        d_i[i] = delta
        xp = x + d_i
        xm = x - d_i
        val1 = permIt(xp)
        val2 = permIt(xm)
        fval = (val1 - val2) / (2*delta)
        dells[i] = fval
    return dells

def permIt(x):
    """ Takes an nx1 bector x as input and computes the PermII
        value of that vector.
    """
    n = x.size
    v = 0
    for k in range(1,n+1):
        v_j = 0
        for j in range(1,n+1):
            v_j += (j+10) * (x[j-1]**k -(1/(j**k)))
        v += v_j**2
    return v

########################################################################
##################### Main Method ######################################
########################################################################
if __name__ == '__main__':
    
    """ Beginning of main method
    """
    #print("This doesn't do anything yet ¯\_(ツ)_/¯")
    print("Execute mySteep test!")
    n = 5 # Dimensionality of the test
    t = 1e-2
    x = np.random.rand(n,1)*10
    Q,b = randQuad(n)
    f = lambda x:myQuad(x,Q,b)
    v,g = f(x)
    y,z = myArmijo(x,-g,4,0.1,f)
    opt,val,n = mySteep(x,t,f)
    Q_i = np.invert(Q)
    topt = np.matmul(Q_i,b)
    print(abs(opt-topt))
    