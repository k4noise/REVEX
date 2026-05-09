import { createFileRoute } from "@tanstack/react-router";
import { templateApi, queryKeys } from "../../api/template";
import type { TemplateDetailResponse } from "../../model/template";

export const Route = createFileRoute("/template/$templateId")({
  loader: ({
    context: { queryClient },
    params: { templateId },
  }): Promise<TemplateDetailResponse> =>
    queryClient.ensureQueryData({
      queryKey: queryKeys.detail(templateId),
      queryFn: () => templateApi.getById(templateId),
      staleTime: 1000 * 60 * 5,
    }),
});
