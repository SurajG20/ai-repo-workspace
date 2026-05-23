from __future__ import annotations

from enum import Enum


class ProviderType(str, Enum):
    GITHUB = "github"
    GITLAB = "gitlab"
    LOCAL = "local"
    GITEA = "gitea"
    BITBUCKET = "bitbucket"


class RepositoryStatus(str, Enum):
    PENDING = "pending"
    CLONING = "cloning"
    ACTIVE = "active"
    INDEXING = "indexing"
    ERROR = "error"
    ARCHIVED = "archived"


class JobStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobType(str, Enum):
    CLONE = "clone"
    SYNC = "sync"
    PARSE = "parse"
    GRAPH_SYNC = "graph_sync"
    EMBED = "embed"
    VECTOR_SYNC = "vector_sync"
    DEAD_CODE = "dead_code"
    PR_ANALYSIS = "pr_analysis"
    ONBOARDING_GEN = "onboarding_gen"
    SNAPSHOT = "snapshot"


class EventType(str, Enum):
    PUSH = "push"
    PULL_REQUEST = "pull_request"
    PULL_REQUEST_REVIEW = "pull_request_review"
    CREATE = "create"
    DELETE = "delete"
    REPOSITORY = "repository"


class ChunkType(str, Enum):
    FUNCTION = "function"
    CLASS = "class"
    MODULE = "module"
    INTERFACE = "interface"
    TYPE = "type"
    EXPORT = "export"
    COMMENT = "comment"
    DOCSTRING = "docstring"


class SymbolKind(str, Enum):
    FUNCTION = "function"
    CLASS = "class"
    INTERFACE = "interface"
    TYPE = "type"
    ENUM = "enum"
    VARIABLE = "variable"
    IMPORT = "import"
    EXPORT = "export"
    PARAMETER = "parameter"


class SessionType(str, Enum):
    CHAT = "chat"
    PR_REVIEW = "pr_review"
    ONBOARDING = "onboarding"
    ARCHITECTURE = "architecture"
    DEAD_CODE = "dead_code"
