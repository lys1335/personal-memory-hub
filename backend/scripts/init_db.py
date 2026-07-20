"""Database initialization script.

Creates all tables and default workspace in the database.
Run this once to set up the database schema and initial data.
"""

import asyncio
import asyncpg


async def init_db():
    """Create all tables and default workspace in the database."""
    from backend.shared.infrastructure.config.settings import get_settings
    from backend.shared.domain.memory_models import Base
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine
    
    settings = get_settings()
    
    # Create engine
    engine = create_async_engine(settings.DATABASE_URL)
    
    try:
        async with engine.begin() as conn:
            # Create schema
            await conn.execute(text("CREATE SCHEMA IF NOT EXISTS memory_hub"))
            
            # Create all tables
            await conn.run_sync(Base.metadata.create_all)
        
        print("✓ Database tables created successfully!")
        
        # Now insert default workspace
        from uuid import uuid4
        workspace_id = str(uuid4())
        
        async with engine.connect() as conn:
            await conn.execute(
                text("""
                    INSERT INTO memory_hub.workspace (id, name, description, created_at, updated_at)
                    VALUES (:id, :name, :description, NOW(), NOW())
                    ON CONFLICT DO NOTHING
                """),
                {
                    "id": workspace_id,
                    "name": "default-workspace",
                    "description": "Default workspace for Personal Memory Hub"
                }
            )
            await conn.commit()
        
        print(f"✓ Default workspace created with ID: {workspace_id}")
        return workspace_id
        
    finally:
        await engine.dispose()


if __name__ == "__main__":
    workspace_id = asyncio.run(init_db())
    print(f"\n🎉 Database initialized successfully!")
    print(f"   Workspace ID: {workspace_id}")
    print(f"   Use this ID when calling the Import API.")
