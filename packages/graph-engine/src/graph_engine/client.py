from __future__ import annotations

import os
from typing import AsyncGenerator

import structlog
from neo4j import AsyncGraphDatabase, AsyncSession

logger = structlog.get_logger(__name__)


class Neo4jClient:
    def __init__(
        self,
        uri: str | None = None,
        user: str | None = None,
        password: str | None = None,
    ) -> None:
        self.uri = uri or os.getenv("NEO4J_URI", "bolt://localhost:7687")
        self.user = user or os.getenv("NEO4J_USER", "neo4j")
        self.password = password or os.getenv("NEO4J_PASSWORD", "aiworkspace")
        self._driver = AsyncGraphDatabase.driver(
            self.uri,
            auth=(self.user, self.password),
            max_connection_lifetime=3600,
            max_connection_pool_size=20,
            connection_acquisition_timeout=30,
        )

    async def session(self) -> AsyncGenerator[AsyncSession, None]:
        async with self._driver.session() as session:
            yield session
            await session.close()

    async def _execute(self, tx, query: str, params: dict) -> list:
        result = await tx.run(query, params or {})
        return await result.data()

    async def execute_write(self, query: str, params: dict | None = None) -> list:
        async with self._driver.session() as session:
            return await session.execute_write(self._execute, query, params or {})

    async def execute_read(self, query: str, params: dict | None = None) -> list:
        async with self._driver.session() as session:
            return await session.execute_read(self._execute, query, params or {})

    async def health_check(self) -> bool:
        try:
            await self.execute_read("RETURN 1")
            return True
        except Exception:
            return False

    async def close(self) -> None:
        await self._driver.close()


neo4j_client = Neo4jClient()
