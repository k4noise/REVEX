import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { acceptPrivacyMutationOptions } from "@/features/privacy/api";
import { Helmet } from "react-helmet-async";

export const Route = createFileRoute("/privacy")({
  component: PrivacyPage,
});

function PrivacyPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const mutation = useMutation({
    ...acceptPrivacyMutationOptions(),
    onSuccess: () => {
      queryClient.invalidateQueries();
      navigate({ to: "/" });
    },
  });

  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-background p-4">
      <Helmet>
        <title>Политика конфиденциальности</title>
      </Helmet>

      <div className="max-w-lg w-full bg-card border rounded-xl p-8 shadow-sm">
        <h1 className="text-2xl font-bold mb-6 text-center">
          Требуется действие
        </h1>

        <div className="prose dark:prose-invert max-w-none mb-8 text-sm text-muted-foreground">
          <p>
            Для продолжения работы с системой необходимо принять обновленную
            политику конфиденциальности. Мы используем ваши данные LTI (ID, роль)
            исключительно для учебного процесса.
          </p>
        </div>

        <button
          onClick={() => mutation.mutate()}
          disabled={mutation.isPending}
          className={`
            w-full py-3 rounded-lg font-bold text-white transition-all
            ${mutation.isPending 
              ? "bg-muted-foreground cursor-wait" 
              : "bg-primary hover:bg-primary/90"}
          `}
        >
          {mutation.isPending ? "Обработка..." : "Принять условия"}
        </button>

        {mutation.isError && (
          <p className="mt-4 text-center text-destructive text-sm font-medium">
            Произошла ошибка при отправке. Попробуйте еще раз.
          </p>
        )}
      </div>
    </div>
  );
}