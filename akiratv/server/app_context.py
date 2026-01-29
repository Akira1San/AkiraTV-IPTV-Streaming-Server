# akiratv/app_context.py
"""
Application context for managing global state and services.
This helps avoid circular dependencies between modules.
"""
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from ..core import AkiraTV  # Only for type hints
# DO NOT IMPORT AkiraTV HERE to avoid circular dependency
# from .core import AkiraTV 

class AppContext:
    _instance: Optional['AppContext'] = None
    # Use a string 'AkiraTV' as a forward reference for the type hint
    _akiratv_instance: Optional['AkiraTV'] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    @property
    def akiratv(self) -> Optional['AkiraTV']:
        """Get the AkiraTV instance."""
        return self._akiratv_instance
    
    def set_akiratv(self, instance: 'AkiraTV'):
        """Set the AkiraTV instance."""
        self._akiratv_instance = instance

# Create a global instance
app_context = AppContext()