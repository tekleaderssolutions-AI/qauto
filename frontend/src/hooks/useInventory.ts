import { useQuery } from '@tanstack/react-query'
import { getInventory, getInventorySummary } from '../api'

export function useInventory(params: Record<string, string | number | undefined> = {}) {
  return useQuery({
    queryKey: ['inventory', params],
    queryFn: () => getInventory(params),
    staleTime: 2 * 60 * 1000,
    refetchOnWindowFocus: false,
  })
}

export function useInventorySummary() {
  return useQuery({
    queryKey: ['inventory-summary'],
    queryFn: () => getInventorySummary(),
    staleTime: 5 * 60 * 1000,
    refetchOnWindowFocus: false,
  })
}

