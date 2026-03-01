/** API response types — inventory */
export type RiskFlag = 'healthy' | 'monitor' | 'at_risk' | 'critical'

export interface Vehicle {
  vehicle_id: number
  make: string
  model: string
  trim: string
  year: number
  color_exterior: string
  days_in_stock: number
  list_price_qar: number
  risk_score: number
  risk_flag: RiskFlag
  recommended_action?: string
  body_type: string
}

export interface InventorySummary {
  critical: number
  at_risk: number
  monitor: number
  healthy: number
}
