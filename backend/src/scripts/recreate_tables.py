"""Recreate all database tables."""
import os
import sys

sys.path.insert(0, '/app/src')
os.chdir('/app/src')

import asyncio

from backend.shared.domain.memory_models import Base
from backend.shared.infrastructure.database.engine import get_engine


async def main():
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print('Tables created successfully')

asyncio.run(main())
