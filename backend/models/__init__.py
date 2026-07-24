"""
models/__init__.py

WHY THIS FILE EXISTS
---------------------
SQLAlchemy resolves string-based relationship references (e.g.,
`Mapped["Document"]` inside `models/user.py`) lazily, at mapper-configuration
time -- which means every model class must have been imported *somewhere*
before the ORM is used, or those string references fail to resolve.

Importing every model here, and importing this package from
`database/session.py`'s consumers (in practice, from `main.py` at startup),
guarantees the full mapper graph is configured exactly once, in one
predictable place, instead of relying on import-order accidents.

SOFTWARE ENGINEERING PRINCIPLE
--------------------------------
Explicit registration over implicit/accidental import ordering -- this is
the same problem Django's `AppConfig.ready()` and Alembic's `target_metadata`
both solve; here it's solved with a single, obvious package init.
"""

from models.agent_execution_log import AgentExecutionLog  # noqa: F401
from models.conversation import Conversation  # noqa: F401
from models.document import Document  # noqa: F401
from models.document_chunk import DocumentChunk  # noqa: F401
from models.embedding import Embedding  # noqa: F401
from models.learning_profile import LearningProfile  # noqa: F401
from models.memory import Memory  # noqa: F401
from models.memory_access_log import MemoryAccessLog  # noqa: F401
from models.memory_embedding import MemoryEmbedding  # noqa: F401
from models.message import Message  # noqa: F401
from models.orchestration_event import OrchestrationEvent  # noqa: F401
from models.user import User  # noqa: F401

__all__ = [
    "AgentExecutionLog",
    "Conversation",
    "Document",
    "DocumentChunk",
    "Embedding",
    "LearningProfile",
    "Memory",
    "MemoryAccessLog",
    "MemoryEmbedding",
    "Message",
    "OrchestrationEvent",
    "User",
]
