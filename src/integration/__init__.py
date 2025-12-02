"""
ADPA Integration Module
Connects Adariprasad's implementation with deployed AWS infrastructure
"""

from .unified_monitoring import UnifiedADPAMonitoring, get_unified_monitoring

__all__ = ['UnifiedADPAMonitoring', 'get_unified_monitoring']