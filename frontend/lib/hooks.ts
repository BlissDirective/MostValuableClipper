/**
 * React Query-style hooks for MVC API data fetching.
 * Built on top of the api client with caching, refetching, and error handling.
 */

import { useState, useEffect, useCallback, useRef } from 'react';

// ── Types ───────────────────────────────────────────────────────────

interface UseQueryOptions {
  enabled?: boolean;
  refetchInterval?: number;
  retry?: number;
}

interface UseQueryResult<T> {
  data: T | null;
  isLoading: boolean;
  isError: boolean;
  error: Error | null;
  refetch: () => void;
}

interface UseMutationResult<T, V> {
  mutate: (variables: V) => Promise<T>;
  data: T | null;
  isLoading: boolean;
  isError: boolean;
  error: Error | null;
  reset: () => void;
}

// ── useQuery ──────────────────────────────────────────────────────

export function useQuery<T>(
  key: string,
  fetcher: () => Promise<T>,
  options: UseQueryOptions = {}
): UseQueryResult<T> {
  const { enabled = true, refetchInterval, retry = 3 } = options;
  
  const [data, setData] = useState<T | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isError, setIsError] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  
  const retryCount = useRef(0);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);
  
  const fetchData = useCallback(async () => {
    if (!enabled) return;
    
    setIsLoading(true);
    setIsError(false);
    setError(null);
    
    try {
      const result = await fetcher();
      setData(result);
      retryCount.current = 0;
    } catch (err) {
      retryCount.current++;
      
      if (retryCount.current <= retry) {
        // Retry with exponential backoff
        const delay = Math.min(1000 * Math.pow(2, retryCount.current - 1), 10000);
        setTimeout(() => fetchData(), delay);
        return;
      }
      
      setIsError(true);
      setError(err instanceof Error ? err : new Error(String(err)));
    } finally {
      setIsLoading(false);
    }
  }, [enabled, fetcher, retry]);
  
  useEffect(() => {
    fetchData();
    
    if (refetchInterval) {
      intervalRef.current = setInterval(fetchData, refetchInterval);
    }
    
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, [fetchData, refetchInterval]);
  
  return {
    data,
    isLoading,
    isError,
    error,
    refetch: fetchData,
  };
}

// ── useMutation ───────────────────────────────────────────────────

export function useMutation<T, V>(
  mutationFn: (variables: V) => Promise<T>
): UseMutationResult<T, V> {
  const [data, setData] = useState<T | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isError, setIsError] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  
  const mutate = useCallback(async (variables: V) => {
    setIsLoading(true);
    setIsError(false);
    setError(null);
    
    try {
      const result = await mutationFn(variables);
      setData(result);
      return result;
    } catch (err) {
      setIsError(true);
      setError(err instanceof Error ? err : new Error(String(err)));
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, [mutationFn]);
  
  const reset = useCallback(() => {
    setData(null);
    setIsLoading(false);
    setIsError(false);
    setError(null);
  }, []);
  
  return {
    mutate,
    data,
    isLoading,
    isError,
    error,
    reset,
  };
}

// ── Optimistic Updates ────────────────────────────────────────────

export function useOptimisticMutation<T, V>(
  mutationFn: (variables: V) => Promise<T>,
  optimisticUpdate: (currentData: T | null, variables: V) => T
): UseMutationResult<T, V> {
  const [optimisticData, setOptimisticData] = useState<T | null>(null);
  
  const baseMutation = useMutation<T, V>(async (variables: V) => {
    // Apply optimistic update immediately
    setOptimisticData(prev => optimisticUpdate(prev, variables));
    
    try {
      const result = await mutationFn(variables);
      setOptimisticData(result);
      return result;
    } catch (err) {
      // Revert on error
      setOptimisticData(null);
      throw err;
    }
  });
  
  return {
    ...baseMutation,
    data: optimisticData ?? baseMutation.data,
  };
}
