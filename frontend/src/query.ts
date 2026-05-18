import { QueryClient } from "@tanstack/react-query";
import { isApiError, isJwtError } from "./lib/api";

const DEBUG_RQ = import.meta.env.DEV;

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: (failureCount, error) => {
        if (DEBUG_RQ) {
          const status = isApiError(error) ? error.status : undefined;
          console.debug("[RQ retry]", {
            failureCount,
            status,
            isApiError: isApiError(error),
            isJwtError: isJwtError(error),
            error,
          });
        }

        if (isApiError(error) && error.status === 451) return false;
        if (isJwtError(error)) return false;

        if (isApiError(error) && error.status >= 500) {
          return failureCount < 3;
        }

        if (isApiError(error) && error.status >= 400) {
          return false;
        }

        return failureCount < 3;
      },

      refetchOnWindowFocus: import.meta.env.PROD,
      staleTime: 1000 * 60 * 5,
    },
  },
});
