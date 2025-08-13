from sqlalchemy import Column, BigInteger, String, Text, DateTime, ForeignKey, Integer
from sqlalchemy.sql import func
from Database.Database import Base

class Crystals(Base):
    __tablename__ = "Crystals"
    id = Column(Integer, primary_key=True)
    name = Column(String(100), index=True)
    type = Column(String(50))
    color = Column(String(20))
    sell_price = Column(String(50))
    process_cost = Column(String(50))
    stats_normal = Column(Text)
    stats_equipment_limited = Column(Text)
    obtained_from = Column(Text)