from numpy import *

def hurst(sequence):
    N = len(sequence)
    mlarge = floor(N/5.0)
    M = array([floor(logspace(0,log10(mlarge),50))])
    M = unique(M[M>1])
    n = len(M)
    cut_min = int(ceil(n/10.0))
    cut_max = int(floor(6.0*n/10.0))
    V = zeros(n)
    for i in range(n):
        m = int(M[i])
        k = int(floor(N/m))
        matrix_sequence = array(sequence[:m*k]).reshape((k,m))
        V[i] = var(sum(matrix_sequence,1)/float(m))

    x = log10(M)
    y = log10(V)
    y1 = -x+y[0]+x[0]
    X = x[cut_min:cut_max]
    Y = y[cut_min:cut_max]

    p1 = polyfit(X,Y,1)
    Yfit = polyval(p1,X)
    yfit = polyval(p1,x)

    beta = -(Yfit[-1]-Yfit[0])/(X[-1]-X[0]);
    H = 1.0-beta/2.0
    # if plots:
    #     plot(x,y,'*')
    #     plot(X, Yfit)
    #     plot(x[:cut_min],yfit[:cut_min],'r:')
    #     plot(x[cut_max:],yfit[cut_max:],'r:')
    #
    #     show()
    return H