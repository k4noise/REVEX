import { createFileRoute } from "@tanstack/react-router";
import { reportApi, reportQueryKeys } from "../../api/report";
import type { FullWorkResponse } from "../../model/report";
import { ReportPage } from "../../pages/Report";

export const Route = createFileRoute("/report/$reportId")({
  loader: async ({
    context: { queryClient },
    params: { reportId },
  }): Promise<FullWorkResponse> =>
    queryClient.ensureQueryData({
      queryKey: reportQueryKeys.detail(reportId),
      queryFn: () => reportApi.getById(reportId),
    }),
  component: ReportRouteComponent,
});

function ReportRouteComponent() {
  const { reportId } = Route.useParams();
  const initialData = Route.useLoaderData();

  return <ReportPage reportId={reportId} initialData={initialData} />;
}
