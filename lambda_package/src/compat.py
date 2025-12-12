"""
Compatibility shim for optional ML dependencies.
Makes scipy optional for ADPA components.
"""

# Check what's available
HAS_SCIPY = False
try:
    import scipy
    from scipy.sparse import issparse
    HAS_SCIPY = True
except ImportError:
    pass

# Make sklearn imports safe even without scipy
if not HAS_SCIPY:
    import sys
    import types
    import numpy as np
    
    # Create mock functions for scipy.sparse
    def mock_issparse(x):
        """Mock issparse function - always returns False for non-scipy environments"""
        return False
    
    def mock_isspmatrix(x):
        """Mock isspmatrix function - always returns False for non-scipy environments"""
        return False
    
    def mock_csr_matrix(*args, **kwargs):
        """Mock csr_matrix - returns a numpy array"""
        if args:
            return np.array(args[0])
        return np.array([])
    
    # Create a mock scipy module to satisfy sklearn's import checks
    scipy_mock = types.ModuleType('scipy')
    scipy_mock.__version__ = '1.10.0'  # Mock version to satisfy sklearn checks
    scipy_mock.stats = types.ModuleType('scipy.stats')
    scipy_mock.sparse = types.ModuleType('scipy.sparse')
    scipy_mock.linalg = types.ModuleType('scipy.linalg')
    scipy_mock.optimize = types.ModuleType('scipy.optimize')
    scipy_mock.special = types.ModuleType('scipy.special')
    
    # Add required functions to scipy.sparse
    scipy_mock.sparse.issparse = mock_issparse
    scipy_mock.sparse.isspmatrix = mock_isspmatrix
    scipy_mock.sparse.csr_matrix = mock_csr_matrix
    scipy_mock.sparse.csc_matrix = mock_csr_matrix
    scipy_mock.sparse.coo_matrix = mock_csr_matrix
    scipy_mock.sparse.lil_matrix = mock_csr_matrix
    scipy_mock.sparse.dok_matrix = mock_csr_matrix
    scipy_mock.sparse.bsr_matrix = mock_csr_matrix
    scipy_mock.sparse.dia_matrix = mock_csr_matrix
    scipy_mock.sparse.spmatrix = type('spmatrix', (), {})
    
    # Add required functions to scipy.linalg
    scipy_mock.linalg.svd = np.linalg.svd
    scipy_mock.linalg.qr = np.linalg.qr
    scipy_mock.linalg.eigh = np.linalg.eigh
    scipy_mock.linalg.inv = np.linalg.inv
    scipy_mock.linalg.norm = np.linalg.norm
    scipy_mock.linalg.solve = np.linalg.solve
    
    # Add required constants/functions to scipy.special
    def mock_expit(x):
        """Sigmoid function"""
        return 1 / (1 + np.exp(-np.asarray(x)))
    
    def mock_softmax(x, axis=None):
        """Softmax function"""
        x = np.asarray(x)
        e_x = np.exp(x - np.max(x, axis=axis, keepdims=True))
        return e_x / e_x.sum(axis=axis, keepdims=True)
    
    scipy_mock.special.expit = mock_expit
    scipy_mock.special.softmax = mock_softmax
    
    sys.modules['scipy'] = scipy_mock
    sys.modules['scipy.stats'] = scipy_mock.stats
    sys.modules['scipy.sparse'] = scipy_mock.sparse
    sys.modules['scipy.linalg'] = scipy_mock.linalg
    sys.modules['scipy.optimize'] = scipy_mock.optimize
    sys.modules['scipy.special'] = scipy_mock.special
