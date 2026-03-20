import { useState, useCallback } from "react";

export function useApi<T>() {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const request = useCallback(async (apiFunc: () => Promise<any>) => {
    setIsLoading(true);
    setError(null);
    try {
      const result = await apiFunc();
      if (result && result.data !== undefined) {
         setData(result.data);
         return result.data;
      }
      setData(result);
      return result;
    } catch (err: any) {
      setError(err.message || "An error occurred");
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, []);

  return { data, error, isLoading, request, setData };
}
