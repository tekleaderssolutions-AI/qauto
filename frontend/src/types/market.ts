/** API response types — market KPIs and trends */
export interface MarketKPIs {
  market_health_score?: number
  avg_days_to_sell_suv?: number
  critical_inventory_count?: number
  active_buyers_60d?: number
  oil_price_usd?: number
  interest_rate_pct?: number
  consumer_confidence_index?: number
}

export interface MarketTrends {
  months: string[]
  volumes: number[]
}
