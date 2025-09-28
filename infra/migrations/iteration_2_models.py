"""Migration for Iteration 2 models: User, Message, Intent, Task."""

import asyncio
from sqlalchemy import text

from app.adapters.db import DatabaseAdapter


async def run_migration():
    """Run database migration for new models."""

    # Initialize database connection
    db = DatabaseAdapter()
    await db.connect()

    try:
        # Create tables
        await db._engine.execute(text("""
            -- Users table
            CREATE TABLE IF NOT EXISTS users (
                id UUID PRIMARY KEY,
                telegram_id INTEGER UNIQUE,
                name VARCHAR(255),
                language VARCHAR(10) DEFAULT 'ru',
                timezone VARCHAR(50) DEFAULT 'Europe/Moscow',
                preferences JSONB DEFAULT '{}',
                roles JSONB DEFAULT '["user"]',
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW(),
                last_seen TIMESTAMPTZ
            );

            -- Create indexes for users
            CREATE INDEX IF NOT EXISTS idx_users_telegram_id ON users(telegram_id);
            CREATE INDEX IF NOT EXISTS idx_users_created_at ON users(created_at);

            -- Messages table
            CREATE TABLE IF NOT EXISTS messages (
                id UUID PRIMARY KEY,
                user_id UUID NOT NULL REFERENCES users(id),
                session_id UUID,
                source VARCHAR(50) NOT NULL,
                channel VARCHAR(50),
                content_type VARCHAR(50) DEFAULT 'text',
                content TEXT NOT NULL,
                metadata JSONB DEFAULT '{}',
                timestamp TIMESTAMPTZ DEFAULT NOW(),
                processed BOOLEAN DEFAULT FALSE,
                intent_id UUID
            );

            -- Create indexes for messages
            CREATE INDEX IF NOT EXISTS idx_messages_user_id ON messages(user_id);
            CREATE INDEX IF NOT EXISTS idx_messages_session_id ON messages(session_id);
            CREATE INDEX IF NOT EXISTS idx_messages_source ON messages(source);
            CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON messages(timestamp);
            CREATE INDEX IF NOT EXISTS idx_messages_processed ON messages(processed);

            -- Intents table
            CREATE TABLE IF NOT EXISTS intents (
                id UUID PRIMARY KEY,
                user_id UUID NOT NULL REFERENCES users(id),
                session_id UUID,
                message_id UUID REFERENCES messages(id),
                intent_type VARCHAR(100) NOT NULL,
                confidence FLOAT NOT NULL,
                slots JSONB DEFAULT '{}',
                raw_text TEXT NOT NULL,
                source VARCHAR(50) NOT NULL,
                language VARCHAR(10),
                explanation TEXT,
                processed BOOLEAN DEFAULT FALSE,
                plan_id VARCHAR(255),
                created_at TIMESTAMPTZ DEFAULT NOW()
            );

            -- Create indexes for intents
            CREATE INDEX IF NOT EXISTS idx_intents_user_id ON intents(user_id);
            CREATE INDEX IF NOT EXISTS idx_intents_session_id ON intents(session_id);
            CREATE INDEX IF NOT EXISTS idx_intents_intent_type ON intents(intent_type);
            CREATE INDEX IF NOT EXISTS idx_intents_source ON intents(source);
            CREATE INDEX IF NOT EXISTS idx_intents_created_at ON intents(created_at);

            -- Update messages foreign key for intents
            ALTER TABLE messages ADD CONSTRAINT fk_messages_intent_id
                FOREIGN KEY (intent_id) REFERENCES intents(id);

            -- Tasks table
            CREATE TABLE IF NOT EXISTS tasks (
                id UUID PRIMARY KEY,
                user_id UUID NOT NULL REFERENCES users(id),
                type VARCHAR(100) NOT NULL,
                title VARCHAR(500) NOT NULL,
                description TEXT,
                payload JSONB DEFAULT '{}',
                status VARCHAR(50) DEFAULT 'pending',
                priority INTEGER DEFAULT 1,
                cron_spec VARCHAR(255),
                next_run TIMESTAMPTZ,
                last_run TIMESTAMPTZ,
                retry_count INTEGER DEFAULT 0,
                max_retries INTEGER DEFAULT 3,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW()
            );

            -- Create indexes for tasks
            CREATE INDEX IF NOT EXISTS idx_tasks_user_id ON tasks(user_id);
            CREATE INDEX IF NOT EXISTS idx_tasks_type ON tasks(type);
            CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
            CREATE INDEX IF NOT EXISTS idx_tasks_next_run ON tasks(next_run);
        """))

        print("✅ Migration completed successfully!")

    except Exception as e:
        print(f"❌ Migration failed: {e}")
        raise
    finally:
        await db.disconnect()


if __name__ == "__main__":
    asyncio.run(run_migration())
