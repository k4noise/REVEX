import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { privacyApi } from "../api/privacy";
import { Helmet } from "react-helmet-async";
import { useEffect, useRef, useState } from "react";
import { cx } from "../features/template/utils/styles";

export const Route = createFileRoute("/privacy")({
  component: PrivacyPage,
});

function PrivacyPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [isScrolledToEnd, setIsScrolledToEnd] = useState(false);
  const policyContentRef = useRef<HTMLDivElement>(null);

  const mutation = useMutation({
    mutationFn: privacyApi.acceptPolicy,
    onSuccess: () => {
      queryClient.invalidateQueries();
      navigate({ to: "/" });
    },
  });

  useEffect(() => {
    const contentElement = policyContentRef.current;
    if (!contentElement) return;

    const checkScrollPosition = () => {
      const { scrollTop, scrollHeight, clientHeight } = contentElement;
      setIsScrolledToEnd(scrollTop + clientHeight >= scrollHeight - 10);
    };

    contentElement.addEventListener("scroll", checkScrollPosition);
    window.addEventListener("resize", checkScrollPosition);
    checkScrollPosition();

    return () => {
      contentElement.removeEventListener("scroll", checkScrollPosition);
      window.removeEventListener("resize", checkScrollPosition);
    };
  }, []);

  const isButtonDisabled = mutation.isPending || !isScrolledToEnd;

  return (
    <div className="min-h-screen bg-[#F8FAFC] dark:bg-[#141416]">
      <Helmet>
        <title>Политика конфиденциальности</title>
      </Helmet>

      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <h1 className="text-3xl font-bold mb-8 text-zinc-900 dark:text-zinc-50">
          Политика конфиденциальности
        </h1>

        <div
          ref={policyContentRef}
          className="prose dark:prose-invert max-w-none text-base text-zinc-800 dark:text-zinc-200 max-h-[calc(100vh-280px)] overflow-y-auto pr-4"
        >
          <p className="mb-6">
            Система проверки лабораторных работ собирает и обрабатывает
            минимальный набор данных, необходимый для организации учебного
            процесса. Ниже описано, что именно мы храним и зачем.
          </p>

          <h2 className="text-xl font-semibold mt-8 mb-4">
            Что мы получаем при входе
          </h2>
          <p>
            Авторизация происходит через вашу систему обучения (LMS) по
            протоколу LTI. Мы получаем:
          </p>
          <ul className="mb-4 pl-6 list-disc">
            <li>Ваш идентификатор в LMS</li>
            <li>Роль (студент или преподаватель)</li>
            <li>Отображаемое имя (если LMS его передаёт)</li>
            <li>Идентификатор и название курса</li>
          </ul>
          <p>Мы не запрашиваем пароль, email и другие контактные данные.</p>

          <h2 className="text-xl font-semibold mt-8 mb-4">
            Что сохраняется в процессе работы
          </h2>
          <ul className="mb-4 pl-6 list-disc">
            <li>Ваши ответы в отчётах</li>
            <li>Оценки и комментарии преподавателя</li>
            <li>Результаты автоматической проверки</li>
            <li>Даты и статусы отправки работ</li>
          </ul>

          <h2 className="text-xl font-semibold mt-8 mb-4">
            Автоматическая проверка и подсказки
          </h2>
          <p>
            Система использует языковую модель для двух задач: предварительная
            проверка ответов (результат подтверждается преподавателем) и
            формирование наводящих вопросов при заполнении (без раскрытия
            правильного ответа).
          </p>
          <p>
            Обработка выполняется на серверах, контролируемых оператором
            системы. Данные не отправляются сторонним сервисам.
          </p>

          <h2 className="text-xl font-semibold mt-8 mb-4">
            Кто имеет доступ к данным
          </h2>
          <ul className="mb-4 pl-6 list-disc">
            <li>Вы — к своим отчётам и оценкам</li>
            <li>Преподаватели вашего курса — к отчётам студентов курса</li>
          </ul>
          <p>
            Данные не передаются третьим лицам, за исключением передачи оценок
            обратно в LMS (это часть учебного процесса) и случаев,
            предусмотренных законодательством РФ.
          </p>

          <h2 className="text-xl font-semibold mt-8 mb-4">Хранение</h2>
          <p>
            Данные хранятся на протяжении действия учебного курса. Временные
            данные подсказок автоматически удаляются в течение суток.
          </p>

          <h2 className="text-xl font-semibold mt-8 mb-4">
            Изменение политики
          </h2>
          <p className="mb-8">
            При существенных изменениях вам будет предложено повторно
            ознакомиться с текстом и подтвердить согласие.
          </p>
        </div>
      </div>

      <div className="fixed bottom-4 left-0 right-0 z-50 px-4">
        <div className="max-w-4xl mx-auto">
          <button
            onClick={() => mutation.mutate()}
            disabled={isButtonDisabled}
            className={cx(
              "w-full py-4 rounded-xl font-semibold text-white transition-all duration-300",
              isButtonDisabled
                ? "bg-zinc-400 cursor-not-allowed opacity-70 dark:bg-zinc-600"
                : "bg-zinc-900 hover:bg-zinc-800 shadow-lg hover:shadow-xl transform hover:-translate-y-0.5 dark:bg-zinc-100 dark:text-zinc-900 dark:hover:bg-zinc-200",
            )}
          >
            {mutation.isPending
              ? "Обработка..."
              : "Принять политику конфиденциальности"}
          </button>

          {!isScrolledToEnd && !mutation.isPending && (
            <p className="mt-2 text-center text-zinc-500 dark:text-zinc-400 text-sm">
              Прочитайте текст до конца, чтобы принять условия
            </p>
          )}

          {mutation.isError && (
            <p className="mt-2 text-center text-red-600 dark:text-red-400 text-sm font-medium">
              Произошла ошибка. Попробуйте ещё раз.
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
