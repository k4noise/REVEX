import { createFileRoute } from "@tanstack/react-router";
import { templateApi, queryKeys } from "@/api/template";
import { TemplatePage } from "@/pages/Template";

export const Route = createFileRoute("/template/$templateId")({
  loader: ({ context: { queryClient }, params: { templateId } }) =>
    queryClient.ensureQueryData({
      queryKey: queryKeys.detail(templateId),
      queryFn: () => templateApi.getById(templateId),
      staleTime: 1000 * 60 * 5,
    }),
  component: () => {
    const { templateId } = Route.useParams();
    const initialData = Route.useLoaderData();
    return <TemplatePage templateId={templateId} initialData={initialData} />;
  },
});
