import { useQuery } from '@tanstack/react-query'
import { getReadyBuyers, getMatchDashboard } from '../api'

export function useReadyBuyers(limit = 20) {
  return useQuery({
    queryKey: ['ready-buyers', limit],
    queryFn: () => getReadyBuyers(limit),
    staleTime: 5 * 60 * 1000,
    refetchOnWindowFocus: false,
  })
}

export function useMatchDashboard(topPerBuyer = 3) {
  return useQuery({
    queryKey: ['match-dashboard', topPerBuyer],
    queryFn: () => getMatchDashboard(topPerBuyer),
    staleTime: 5 * 60 * 1000,
    refetchOnWindowFocus: false,
  })
}

