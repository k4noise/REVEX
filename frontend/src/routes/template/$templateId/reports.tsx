import { createFileRoute } from "@tanstack/react-router";
import { templateApi, queryKeys } from "../../../api/template";
import type { AllReportsResponse } from "../../../model/report";
import { ReportsListPage } from "../../../pages/ReportsList";

export const Route = createFileRoute("/template/$templateId/reports")({
  loader: async ({ context: { queryClient }, params: { templateId } }) => {
    const template = await queryClient.ensureQueryData({
      queryKey: queryKeys.detail(templateId),
      queryFn: () => templateApi.getById(templateId),
      staleTime: 1000 * 60 * 5,
    });

    const reportsHref = template._links.get_reports?.href;

    if (!reportsHref) {
      return {
        templateName: template.name,
        templateId,
        maxScore: template.maxScore,
        reports: { owned: [], toGrade: [] },
        _links: {},
      } satisfies AllReportsResponse;
    }

    return queryClient.ensureQueryData({
      queryKey: queryKeys.reports(templateId),
      queryFn: () => templateApi.getReports(reportsHref),
      staleTime: 1000 * 60 * 5,
    });
  },
  component: ReportsRouteComponent,
});

function ReportsRouteComponent() {
  const data = Route.useLoaderData();
  return <ReportsListPage data={data} />;
}
