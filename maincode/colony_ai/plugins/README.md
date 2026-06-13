# Colony of Minds AI - Plugins System

This folder enables extending the framework with custom suboperators and tools without modifying the core codebase.

## Directory Structure

```text
plugins/
├── README.md
├── suboperators/    # Place custom suboperator python files here
└── tools/           # Place custom tool definitions here (if any)
```

## Creating a Custom Suboperator

To add a new suboperator, create a python file under `plugins/suboperators/` (e.g. `translation_op.py`):

```python
from colony_ai.colony.operator import BaseSuboperator
from colony_ai.colony.schemas import SuboperatorResponse

class TranslationOperator(BaseSuboperator):
    
    @property
    def name(self) -> str:
        # Unique name matching what the Router selects
        return "translation_op"
        
    def execute(self, query: str, context: dict = None) -> SuboperatorResponse:
        # Custom logic goes here
        # Return a SuboperatorResponse instance
        facts = [{"type": "translation", "source": query, "result": "Translated content"}]
        return SuboperatorResponse(
            operator=self.name,
            success=True,
            confidence=0.95,
            facts=facts
        )
```

During initialization, Colony of Minds scans this folder and automatically registers any class inheriting from `BaseSuboperator` so that it is discoverable by the lazy loading resolver.
