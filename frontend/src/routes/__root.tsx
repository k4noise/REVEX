import {
  createRootRouteWithContext,
  Outlet,
  useRouter,
} from "@tanstack/react-router";
import { lazy, Suspense, useEffect, useRef } from "react";
import type { QueryClient } from "@tanstack/react-query";
import { useQueryClient } from "@tanstack/react-query";
import { Helmet, HelmetProvider } from "react-helmet-async";
import { Toaster } from "sonner";
import { isApiError, isJwtError } from "../lib/api";

const RouterDevtools = import.meta.env.DEV
  ? lazy(() =>
      import("@tanstack/react-router-devtools").then((m) => ({
        default: m.TanStackRouterDevtools,
      })),
    )
  : () => null;

export interface RouterContext {
  queryClient: QueryClient;
}

function GlobalErrorHandler() {
  const queryClient = useQueryClient();
  const router = useRouter();

  useEffect(() => {
    const handlePrivacyRedirect = (error: unknown) => {
      if (isApiError(error) && error.status === 451) {
        const currentPath = router.state.location.pathname;
        if (currentPath !== "/privacy") {
          router.navigate({ to: "/privacy", replace: true });
        }
      }
    };

    const handleAuthError = (error: unknown) => {
      if (isJwtError(error)) {
        const currentPath = router.state.location.pathname;

        if (currentPath !== "/") {
          router.navigate({ to: "/", replace: true });
        }
      }
    };

    const queryUnsubscribe = queryClient.getQueryCache().subscribe((event) => {
      const query = event?.query;
      const state = query?.state;
      const error = state?.error;

      if (!error) return;

      handlePrivacyRedirect(error);
      handleAuthError(error);
    });

    const mutationUnsubscribe = queryClient
      .getMutationCache()
      .subscribe((event) => {
        const mutation = event?.mutation;
        const state = mutation?.state;
        const error = state?.error;

        if (!error) return;

        handlePrivacyRedirect(error);
        handleAuthError(error);
      });

    return () => {
      queryUnsubscribe();
      mutationUnsubscribe();
    };
  }, [queryClient, router]);

  return null;
}

function RootComponent() {
  return (
    <HelmetProvider>
      <Helmet>
        <html lang="ru" />
      </Helmet>
      <Outlet />
      <GlobalErrorHandler />
      <Toaster richColors position="top-center" />
      <Suspense>
        <RouterDevtools position="bottom-right" />
      </Suspense>
    </HelmetProvider>
  );
}

function LoadingComponent() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-[#F8FAFC] dark:bg-[#141416]">
      <div className="flex flex-col items-center gap-4">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-zinc-300 border-t-zinc-900 dark:border-zinc-700 dark:border-t-zinc-100" />
        <span className="text-sm text-zinc-500 dark:text-zinc-400">
          Загрузка...
        </span>
      </div>
    </div>
  );
}

function getErrorMessage(error: unknown): string {
  if (isApiError(error) && error.body && typeof error.body === "object") {
    const detail = (error.body as { detail?: string }).detail;
    if (detail) return detail;
  }
  if (error instanceof Error) {
    return error.message;
  }
  return "Произошла непредвиденная ошибка";
}

function RootErrorComponent({ error }: { error: unknown }) {
  const router = useRouter();
  const didNavigateRef = useRef(false);

  useEffect(() => {
    if (didNavigateRef.current) return;

    const currentPath = router.state.location.pathname;

    if (isApiError(error) && error.status === 451) {
      if (currentPath !== "/privacy") {
        didNavigateRef.current = true;
        router.navigate({ to: "/privacy", replace: true });
      }
      return;
    }

    if (isJwtError(error)) {
      if (currentPath !== "/") {
        didNavigateRef.current = true;
        router.navigate({ to: "/", replace: true });
      }
      return;
    }
  }, [error, router]);

  const currentPath = router.state.location.pathname;
  const shouldAutoRedirectToPrivacy =
    isApiError(error) && error.status === 451 && currentPath !== "/privacy";
  const shouldAutoRedirectToHome = isJwtError(error) && currentPath !== "/";

  if (shouldAutoRedirectToPrivacy || shouldAutoRedirectToHome) {
    return null;
  }

  const message = getErrorMessage(error);

  const isRetryable = !(
    isApiError(error) &&
    (error.status === 404 || error.status === 403)
  );

  return (
    <div className="flex min-h-screen items-center justify-center bg-[#F8FAFC] dark:bg-[#141416] px-4">
      <div className="w-full max-w-md rounded-2xl border border-zinc-200 bg-white p-8 text-center shadow-sm dark:border-zinc-800 dark:bg-[#1E1E22]">
        <h1 className="text-2xl font-bold text-zinc-900 dark:text-zinc-50 mb-2">
          Что-то пошло не так
        </h1>

        <p className="text-sm text-zinc-500 dark:text-zinc-400 mb-6">
          {message}
        </p>

        <div className="flex justify-center gap-3">
          {isRetryable && (
            <button
              type="button"
              onClick={() => router.invalidate()}
              className="rounded-xl border border-zinc-300 bg-white px-4 py-2 text-sm font-medium text-zinc-700 hover:bg-zinc-50 dark:border-zinc-700 dark:bg-zinc-800 dark:text-zinc-200 dark:hover:bg-zinc-700"
            >
              Повторить
            </button>
          )}

          <button
            type="button"
            onClick={() => router.navigate({ to: "/" })}
            className="rounded-xl bg-zinc-900 px-4 py-2 text-sm font-medium text-white hover:bg-zinc-800 dark:bg-zinc-100 dark:text-zinc-900 dark:hover:bg-zinc-200"
          >
            На главную
          </button>
        </div>
      </div>
    </div>
  );
}

function NotFoundComponent() {
  const router = useRouter();

  return (
    <div className="flex min-h-screen items-center justify-center bg-[#F8FAFC] dark:bg-[#141416] px-4">
      <div className="w-full max-w-md rounded-2xl border border-zinc-200 bg-white p-8 text-center shadow-sm dark:border-zinc-800 dark:bg-[#1E1E22]">
        <div className="text-6xl font-bold text-zinc-200 dark:text-zinc-800 mb-4">
          404
        </div>
        <h1 className="text-xl font-bold text-zinc-900 dark:text-zinc-50 mb-2">
          Страница не найдена
        </h1>
        <p className="text-sm text-zinc-500 dark:text-zinc-400 mb-6">
          Возможно, она была удалена или вы перешли по неверной ссылке
        </p>
        <button
          type="button"
          onClick={() => router.navigate({ to: "/" })}
          className="rounded-xl bg-zinc-900 px-5 py-2.5 text-sm font-medium text-white hover:bg-zinc-800 dark:bg-zinc-100 dark:text-zinc-900 dark:hover:bg-zinc-200"
        >
          На главную
        </button>
      </div>
    </div>
  );
}

export const Route = createRootRouteWithContext<RouterContext>()({
  component: RootComponent,
  errorComponent: RootErrorComponent,
  notFoundComponent: NotFoundComponent,
  pendingComponent: LoadingComponent,
});
