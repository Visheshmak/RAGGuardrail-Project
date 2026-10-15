from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base
from app.core.config import settings

engine = create_async_engine(settings.DATABASE_URL, echo=(settings.APP_ENV == "development"))
async_session_maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

Base = declarative_base()

async def get_db():
    async with async_session_maker() as session:
        yield session
