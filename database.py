import datetime
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker

SQLALCHEMY_DATABASE_URL = "sqlite:///./paffloat.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class Skin(Base):
    __tablename__ = "skins"

    id = Column(Integer, primary_key=True, index=True)
    steam_id = Column(String, index=True)
    asset_id = Column(String, unique=True, index=True)
    name = Column(String)
    image_url = Column(String)
    float_value = Column(Float, nullable=True)
    float_category = Column(String, nullable=True)
    seed = Column(Integer, nullable=True)
    purchase_price = Column(Float, default=0.0)
    batches = Column(String, nullable=True)

class APICache(Base):
    __tablename__ = "api_cache"

    id = Column(Integer, primary_key=True, index=True)
    endpoint = Column(String, unique=True, index=True)
    last_called = Column(DateTime, default=datetime.datetime.utcnow)
    response_data = Column(String)