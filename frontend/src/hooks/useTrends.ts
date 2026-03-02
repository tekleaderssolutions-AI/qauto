import { useQuery } from '@tanstack/react-query'
import { getMarketTrends, getMarketTrendSeries, getMarketAnalysis, getMarketSentiment, getMarketEvents } from '../api'

export function useMarketTrends() {
  return useQuery({
    queryKey: ['market-trends'],
    queryFn: () => getMarketTrends(),
    staleTime: 30 * 60 * 1000,
    refetchOnWindowFocus: false,
  })
}

export function useMarketTrendSeries(weeks = 5) {
  return useQuery({
    queryKey: ['market-trend-series', weeks],
    queryFn: () => getMarketTrendSeries(weeks),
    staleTime: 30 * 60 * 1000,
    refetchOnWindowFocus: false,
  })
}

export function useMarketAnalysis(limit = 20) {
  return useQuery({
    queryKey: ['market-analysis', limit],
    queryFn: () => getMarketAnalysis(limit),
    staleTime: 5 * 60 * 1000,
    refetchOnWindowFocus: false,
  })
}

export function useMarketSentiment() {
  return useQuery({
    queryKey: ['market-sentiment'],
    queryFn: () => getMarketSentiment(),
    staleTime: 30 * 60 * 1000,
    refetchOnWindowFocus: false,
  })
}

export function useMarketEvents(limit = 10) {
  return useQuery({
    queryKey: ['market-events', limit],
    queryFn: () => getMarketEvents(limit),
    staleTime: 60 * 60 * 1000,
    refetchOnWindowFocus: false,
  })
}

