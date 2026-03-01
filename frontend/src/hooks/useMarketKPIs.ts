import { useQuery } from '@tanstack/react-query'

const BASE = '/api'

export function useMarketKPIs() {
  return useQuery({
    queryKey: ['market-kpis'],
    queryFn: () => fetch(`${BASE}/market/kpis`).then((r) => r.json()),
    staleTime: 5 * 60 * 1000,
    gcTime: 10 * 60 * 1000,
    refetchOnWindowFocus: false,
  })
}
