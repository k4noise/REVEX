import { createFileRoute } from "@tanstack/react-router";
import { TemplatePage } from "../../../pages/Template";
import { Route as ParentRoute } from "../$templateId";

export const Route = createFileRoute("/template/$templateId/")({
  component: TemplateIndexComponent,
});

function TemplateIndexComponent() {
  const { templateId } = Route.useParams();
  const initialData = ParentRoute.useLoaderData();

  return <TemplatePage templateId={templateId} initialData={initialData} />;
}
