import ReactDOM from "react-dom/client";
import { RouterProvider, createRouter } from "@tanstack/react-router";
import {
  QueryClient,
  QueryClientProvider,
  QueryCache,
  MutationCache,
} from "@tanstack/react-query";
import { routeTree } from "./routeTree.gen";
import { ApiError } from "./lib/api";
import "./index.css";

import { Toaster } from "sonner";

function shouldRedirectToPrivacy(error: unknown) {
  return error instanceof ApiError && error.status === 451;
}

function isJwtError(error: unknown) {
  return (
    error instanceof ApiError &&
    error.status === 401 &&
    typeof error.body === "object" &&
    error.body !== null &&
    "error_type" in error.body &&
    (error.body as Record<string, unknown>).error_type === "JWTDecodeError"
  );
}

const queryClient = new QueryClient({
  queryCache: new QueryCache({
    onError: (error) => {
      if (shouldRedirectToPrivacy(error)) {
        if (window.location.pathname !== "/privacy") {
          router.navigate({ to: "/privacy" });
        }
        return;
      }
      if (isJwtError(error)) {
        router.navigate({ to: "/privacy" });
      }
    },
  }),
  mutationCache: new MutationCache({
    onError: (error) => {
      if (isJwtError(error)) {
        router.navigate({ to: "/privacy" });
      }
    },
  }),
  defaultOptions: {
    queries: {
      retry: (failureCount, error) => {
        if (error instanceof ApiError && error.status === 451) return false;
        if (isJwtError(error)) return false;
        return failureCount < 3;
      },
    },
  },
});

const router = createRouter({
  routeTree,
  context: { queryClient },
});

declare module "@tanstack/react-router" {
  interface Register {
    router: typeof router;
  }
}

const rootElement = document.getElementById("root")!;
if (!rootElement.innerHTML) {
  const root = ReactDOM.createRoot(rootElement);
  root.render(
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
      <Toaster position="top-right" richColors closeButton />
    </QueryClientProvider>,
  );
}
