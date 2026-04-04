import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { acceptPrivacyMutationOptions } from "@/features/privacy/api";
import { Helmet } from "react-helmet-async";
import { useEffect, useRef, useState } from "react";

export const Route = createFileRoute("/privacy")({
  component: PrivacyPage,
});

function PrivacyPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [isScrolledToEnd, setIsScrolledToEnd] = useState(false);
  const policyContentRef = useRef<HTMLDivElement>(null);

  const mutation = useMutation({
    ...acceptPrivacyMutationOptions(),
    onSuccess: () => {
      queryClient.invalidateQueries();
      navigate({ to: "/" });
    },
  });

  useEffect(() => {
    const checkScrollPosition = () => {
      if (!policyContentRef.current) return;

      const { scrollTop, scrollHeight, clientHeight } = policyContentRef.current;
      setIsScrolledToEnd(scrollTop + clientHeight >= scrollHeight - 10);
    };

    const contentElement = policyContentRef.current;
    if (contentElement) {
      contentElement.addEventListener("scroll", checkScrollPosition);
      window.addEventListener("resize", checkScrollPosition);

      checkScrollPosition();

      return () => {
        contentElement.removeEventListener("scroll", checkScrollPosition);
        window.removeEventListener("resize", checkScrollPosition);
      };
    }
  }, []);

  const isButtonDisabled = mutation.isPending || !isScrolledToEnd;

  return (
    <div className="min-h-screen bg-background">
      <Helmet>
        <title>Политика конфиденциальности</title>
      </Helmet>

      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <h1 className="text-3xl font-bold mb-8 text-primary">
          Политика конфиденциальности
        </h1>

        <div
          ref={policyContentRef}
          className="prose dark:prose-invert max-w-none text-base text-foreground
                    max-h-[calc(100vh-280px)] overflow-y-auto pr-4 scrollbar-thin"
        >
          <p className="mb-6">
            Для продолжения работы с системой необходимо принять обновленную политику конфиденциальности. 
            Ниже представлено полное описание того, как мы используем ваши данные.
          </p>

          <h2 className="text-xl font-semibold mt-8 mb-4">Цели обработки данных</h2>
          <p>
            Мы используем ваши данные LTI (уникальный идентификатор, роль в системе) исключительно для организации учебного процесса:
          </p>
          <ul className="mb-6 pl-6">
            <li>Идентификации пользователей в системе обучения</li>
            <li>Определения прав доступа к учебным материалам</li>
            <li>Отслеживания прогресса в учебных курсах</li>
            <li>Формирования отчетов для преподавателей и администрации</li>
          </ul>

          <h2 className="text-xl font-semibold mt-8 mb-4">Ограничения по использованию данных</h2>
          <p>
            Ваши персональные данные не передаются третьим лицам без вашего явного согласия, за исключением случаев, предусмотренных законодательством Российской Федерации.
            Данные хранятся только на защищенных сервисах компании и удаляются автоматически по окончании учебного курса или по вашему запросу.
          </p>

        </div>
      </div>

      <div className="fixed bottom-4 left-0 right-0 z-50 px-4">
        <div className="max-w-4xl mx-auto">
          <button
            onClick={() => mutation.mutate()}
            disabled={isButtonDisabled}
            className={`
              w-full py-4 rounded-lg font-semibold text-white transition-all duration-300
              ${isButtonDisabled 
                ? "bg-muted-foreground cursor-not-allowed opacity-70" 
                : "bg-primary hover:bg-primary/90 shadow-lg hover:shadow-xl transform hover:-translate-y-0.5"}
            `}
          >
            {mutation.isPending ? "Обработка..." : "Принять политику конфиденциальности"}
          </button>

          {!isScrolledToEnd && !mutation.isPending && (
            <p className="mt-2 text-center text-muted-foreground text-sm">
              Пожалуйста, изучите текст до конца, чтобы принять условия
            </p>
          )}

          {mutation.isError && (
            <p className="mt-2 text-center text-destructive text-sm font-medium">
              Произошла ошибка при отправке запроса. Попробуйте еще раз.
            </p>
          )}
        </div>
      </div>
    </div>
  );
}