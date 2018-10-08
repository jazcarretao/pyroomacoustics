# @version: 1.0  2018, Juan Azcarreta
from unittest import TestCase

import numpy as np
import pyroomacoustics as pra

# Create multivariate distribution
mean = [0, 0]  # zero mean
covx = [[100, 5], [5, 2]]  # diagonal covariance positive-semidefinite, e.g., covx = [[100, 5], [5, 2]]
samples = 5000

dimensions = len(covx)  # should be equal to two
X = np.zeros([samples, 1, dimensions])
# Create multivariate Gaussian distribution
x0, x1 = np.random.multivariate_normal(mean, covx, samples).T
X[:, :, 0] = x0[:, None]
X[:, :, 1] = x1[:, None]

class TestWhitening(TestCase):

    def test_whitening(self):
        # Apply whitening
        Y = pra.whitening(X)
        covy = np.dot(Y[:,0,:].T,np.conj(Y[:,0,:])).T/samples

        # Verify that the new correlation matrix is orthonormal (i.e., identity matrix)
        self.assertTrue(np.allclose(np.all(abs(np.eye(dimensions), covy))))

if __name__ == "__main__":
    print()
    print("Mean " + str(mean) + ". Input covariance: " + str(covx))
