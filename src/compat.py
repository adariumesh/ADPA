"""
Compatibility shim for optional ML dependencies.
Makes scipy optional for ADPA components.
"""

# Check what's available
HAS_SCIPY = False
try:
    import scipy
    HAS_SCIPY = True
except ImportError:
    pass

# Make sklearn imports safe even without scipy
if not HAS_SCIPY:
    import sys
    import types
    
    # Create a mock scipy module to satisfy sklearn's import checks
    scipy_mock = types.ModuleType('scipy')
    scipy_mock.stats = types.ModuleType('scipy.stats')
    scipy_mock.sparse = types.ModuleType('scipy.sparse')
    scipy_mock.linalg = types.ModuleType('scipy.linalg')
    scipy_mock.optimize = types.ModuleType('scipy.optimize')
    scipy_mock.special = types.ModuleType('scipy.special')
    
    sys.modules['scipy'] = scipy_mock
    sys.modules['scipy.stats'] = scipy_mock.stats
    sys.modules['scipy.sparse'] = scipy_mock.sparse
    sys.modules['scipy.linalg'] = scipy_mock.linalg
    sys.modules['scipy.optimize'] = scipy_mock.optimize
    sys.modules['scipy.special'] = scipy_mock.special
