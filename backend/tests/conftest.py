import pytest
from app.db.base import Base
from app.db.session import engine


@pytest.fixture(autouse=True, scope="function")
async def init_test_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
