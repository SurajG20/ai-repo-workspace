from __future__ import annotations

from .models import Stage

NEXT_STAGES: dict[Stage, tuple[Stage, ...]] = {
    Stage.CLONE: (Stage.PARSE,),
    Stage.SNAPSHOT: (Stage.PARSE,),
    Stage.PARSE: (Stage.GRAPH_SYNC, Stage.EMBED),
}

TERMINAL_STAGES: frozenset[Stage] = frozenset({Stage.GRAPH_SYNC, Stage.EMBED})
