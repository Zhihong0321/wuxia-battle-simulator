from abc import ABC, abstractmethod
from typing import Optional
from .battle_context import BattleContext


class StepProcessor(ABC):
    """
    Abstract base class for all battle step processors.
    Each processor handles a specific aspect of battle resolution.
    """
    
    def __init__(self, name: str, critical: bool = False):
        """
        Initialize processor.
        
        Args:
            name: Human-readable name for this processor
            critical: If True, errors in this processor abort the entire step
        """
        self.name = name
        self.critical = critical
    
    @abstractmethod
    def can_process(self, context: BattleContext) -> bool:
        """
        Check if this processor should run given the current context.
        
        Args:
            context: Current battle context
            
        Returns:
            True if this processor should execute, False to skip
        """
        pass
    
    @abstractmethod
    def process(self, context: BattleContext) -> None:
        """
        Execute this processor's logic.
        
        Args:
            context: Battle context to read from and modify
            
        Raises:
            Exception: If processing fails and this is a critical processor
        """
        pass
    
    def handle_error(self, context: BattleContext, error: Exception) -> bool:
        """
        Handle an error that occurred during processing.
        
        Args:
            context: Current battle context
            error: The exception that occurred
            
        Returns:
            True if processing should continue, False to abort
        """
        error_msg = f"Error in {self.name}: {str(error)}"
        context.set_error(error_msg)
        
        if self.critical:
            context.skip_remaining_processors()
            return False
        else:
            context.log(f"Non-critical error in {self.name}, continuing")
            return True
    
    def __str__(self) -> str:
        return f"{self.name}{'(critical)' if self.critical else ''}"