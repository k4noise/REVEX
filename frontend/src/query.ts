import { QueryClient } from "@tanstack/react-query";
import { ApiError, isJwtError } from "./lib/api";

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: (failureCount, error) => {
        if (error instanceof ApiError && error.status === 451) return false;
        if (isJwtError(error)) return false;
        if (error instanceof ApiError && error.status >= 500) {
          return failureCount < 3;
        }
        if (error instanceof ApiError && error.status >= 400) {
          return false;
        }
        return failureCount < 3;
      },
      refetchOnWindowFocus: import.meta.env.PROD,
      staleTime: 1000 * 60 * 5,
    },
  },
});
