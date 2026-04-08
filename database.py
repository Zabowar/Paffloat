import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Mapped, mapped_column

SQLALCHEMY_DATABASE_URL = "sqlite:///./data/paffloat.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class Skin(Base):
    __tablename__ = "skins"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    steam_id: Mapped[str] = mapped_column(index=True)
    asset_id: Mapped[str] = mapped_column(unique=True, index=True)
    name: Mapped[str] = mapped_column()
    image_url: Mapped[str] = mapped_column(nullable=True)
    float_value: Mapped[float] = mapped_column(nullable=True)
    float_category: Mapped[str] = mapped_column(nullable=True)
    seed: Mapped[int] = mapped_column(nullable=True)
    purchase_price: Mapped[float] = mapped_column(default=0.0)
    batches: Mapped[str] = mapped_column(nullable=True)

class APICache(Base):
    __tablename__ = "api_cache"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    endpoint: Mapped[str] = mapped_column(unique=True, index=True)
    last_called: Mapped[datetime.datetime] = mapped_column(default=datetime.datetime.utcnow)
    response_data: Mapped[str] = mapped_column()