from sqlalchemy import Column, Integer, Float, Date, String

from api.models import Base


class QatarEconomicIndicator(Base):
    __tablename__ = "qatar_economic_indicators"

    id = Column(Integer, primary_key=True)
    date = Column(Date)
    overall_market_health_score = Column(Float)


class QatarEconomicMonthlyData(Base):
    __tablename__ = "qatar_economic__monthly_data"

    id = Column(Integer, primary_key=True)
    Year = Column(Integer)
    Date = Column(Date)
    Oil_Price_USD_bbl = Column(Float)
    Interest_Rate_pct = Column(Float)
    Consumer_Conf_Index = Column(Integer)

