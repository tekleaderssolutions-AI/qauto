from sqlalchemy import Column, Integer, String, Float

from api.models import Base


class VehicleInventory(Base):
    __tablename__ = "vehicle_inventory"

    vehicle_id = Column(Integer, primary_key=True, index=True)
    make = Column(String(100), index=True)
    model = Column(String(100), index=True)
    trim = Column(String(100))
    year = Column(Integer, index=True)
    color_exterior = Column(String(100))
    body_type = Column(String(100))
    days_in_stock = Column(Integer)
    list_price_qar = Column(Float)
    risk_score = Column(Float)
    risk_flag = Column(String(50), index=True)

