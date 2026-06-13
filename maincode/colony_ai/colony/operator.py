"""
Base operator structures and abstractions for the Colony of Minds framework.
"""

from abc import ABC, abstractmethod
from typing import Optional
from colony.schemas import SuboperatorResponse

class BaseSuboperator(ABC):
    """
    Abstract base class for all specialist suboperators.
    Ensures that every operator implements a standard run sequence and returns
    a typed SuboperatorResponse.
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """The identifier of the operator, matching the schema's operator name."""
        pass

    @abstractmethod
    def execute(self, query: str, context: Optional[dict] = None) -> SuboperatorResponse:
        """
        Process the given query and generate a structured response.
        
        Args:
            query: The user query string.
            context: Optional contextual metadata.
            
        Returns:
            A SuboperatorResponse instance containing facts, errors, or evidence.
        """
        pass

