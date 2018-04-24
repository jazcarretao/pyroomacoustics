'''
Blind Source Separation using Independent Vector Analysis with Auxiliary Function

2018 (c) Juan Azcarreta Ortiz, MIT License
'''
import numpy as np

from pyroomacoustics import stft, istft
from .common import projection_back

# A few contrast functions
f_contrasts = {
        'norm' : { 'f' : (lambda r,c,m : c * r), 'df' : (lambda r,c,m : c) },
        'cosh' : { 'f' : (lambda r,c,m : m * np.log(np.cosh(c * r))), 'df' : (lambda r,c,m : c * m * np.tanh(c * r)) }
        }

def ILRMA(X, n_src=None, n_iter=20, proj_back=True, W0=None,
        n_components=3, f_contrast=None,
        f_contrast_args=[], return_filters=False,
        callback=None):

    '''
    Implementation of ILRMA algorithm for BSS presented in

    D. Kitamura, N. Ono, H. Sawada, H. Kameoka, and H. Saruwatari *Determined Blind Source Separation
    with Independent Low-Rank Matrix Analysis*, in Audio Source Separation, S. Makino, Ed. Springer, 2018, pp.  125-156.

    Parameters
    ----------
    X: ndarray (nframes, nfrequencies, nchannels)
        STFT representation of the observed signal
    n_src: int, optional
        The number of sources or independent components
    n_iter: int, optional
        The number of iterations (default 20)
    proj_back: bool, optional
        Scaling on first mic by back projection (default True)
    W0: ndarray (nfrequencies, nchannels, nchannels), optional
        Initial value for demixing matrix
    f_contrast: dict of functions
        A dictionary with two elements 'f' and 'df' containing the contrast
        function taking 3 arguments. This should be a ufunc acting element-wise
        on any array
    return_filters: bool
        If true, the function will return the demixing matrix too
    callback: func
        A callback function called every 10 iterations, allows to monitor convergence

    Returns
    -------
    Returns an (nframes, nfrequencies, nsources) array. Also returns
    the demixing matrix (nfrequencies, nchannels, nsources)
    if ``return_values`` keyword is True.
    '''
    X = np.transpose(X, (1, 0, 2))
    n_freq, n_frames, n_chan = X.shape

    # default to determined case
    if n_src is None:
        n_src = X.shape[2]

    # Only supports determined case
    assert n_chan == n_src

    # initialize the demixing matrices
    if W0 is None:
        W = np.array([np.eye(n_chan, n_src) for f in range(n_freq)], dtype=X.dtype)
    else:
        W = W0.copy()

    if f_contrast is None:
        f_contrast = f_contrasts['norm']
        f_contrast_args = [1, 1]

    # initialize the nonnegative matrixes with random values
    T = abs(np.array(np.random.rand(n_freq, n_components, n_src)))
    V = abs(np.array(np.random.rand(n_components, n_frames, n_src)))
    Y = np.zeros((n_freq, n_frames, n_src), dtype=X.dtype)
    R = np.zeros((n_freq, n_frames, n_src))
    I = np.eye(n_src, n_src)
    U = np.zeros((n_freq, n_src, n_frames, n_chan))

    def NMF(R, T, V, n_src):
        for n in range(0, n_src - 1):
            R[:, :, n] = np.dot(T[:, :, n], V[:, :, n])

    NMF(R, T, V, n_src)
    P = np.power(abs(Y), 2.)

    # Compute the demixed output
    def demix(Y, X, W):
        for f in range(n_freq):
            Y[f,:,:] = np.dot(X[f,:,:], np.conj(W[f,:,:]))

    for epoch in range(n_iter):

        demix(Y, X, W)

        if callback is not None and epoch % 10 == 0:
            if proj_back:
                z = projection_back(Y, X[:,:,0])
                callback(Y * np.conj(z[None,:,:]))
            else:
                callback(Y)

        # simple loop as a start
        # shape: (n_frames, n_src)
        for s in range(n_src):
            T[:, :, s] = np.multiply(T[:, :, s], np.power(np.divide(np.dot(np.multiply(P[:, :, s],
                        np.power(R[:,:,s], -2.)), V[:,:,s].transpose()), np.dot(np.power(R[:,:,s], -1.),
                        np.transpose(V[:,:,s]))), 0.5))

            T[T < 0.0001] = 0.0001

            R[:, :, s] = np.dot(T[:, :, s], V[:, :, s])

            V[:, :, s] = np.multiply(V[:, :, s], np.power(np.divide(np.multiply(np.transpose(T[:, :, s]), P[:, :, s],
                        np.power(R[:, :, s], -2.)), np.dot(np.transpose(T[:, :, s]), np.invert(R[:, :, s]))), 0.5))

            R[:, :, s] = np.dot(T[:, :, s], V[:, :, s])

            # Compute Auxiliary Variable
            for f in range(n_freq):
                U[f,s,:,:] = np.transpose(np.dot(np.conjugate(X[:,f,:].T), np.multiply(X[:,f,:],
                             np.dot(np.inv(R[:, f, s]), np.ones([1, n_chan]))))/n_frames)
                w[f, s, :, :] = np.dot(W, U[f,s,:,:])

        # Update now the demixing matrix
        for f in range(n_freq):
            for s in range(n_src):
                WV = np.dot(np.conj(W[f,:,:].T), V[f,s,:,:])
                W[f,:,s] = np.linalg.solve(WV, I[:,s])
                W[f,:,s] /= np.inner(np.conj(W[f,:,s]), np.dot(V[f,s,:,:], W[f,:,s]))

    demix(Y, X, W)

    if proj_back:
        z = projection_back(Y, X[:,:,0])
        Y *= np.conj(z[None,:,:])

    if return_filters:
        return Y, W
    else:
        return Y
