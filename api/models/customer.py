from sqlalchemy import Column, Integer, String, Float, Date

from api.models import Base


class Customer(Base):
    __tablename__ = "customers"

    customer_id = Column(Integer, primary_key=True, index=True)
    preferred_body_type = Column(String(100))
    preferred_color = Column(String(100))
    next_upgrade_prediction = Column(Date)
    lifetime_value_qar = Column(Float)

