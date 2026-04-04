import { createFileRoute } from "@tanstack/react-router";
import { TemplatesPage } from "../pages/Templates";
import { templateApi, queryKeys } from "@/api/template";

export const Route = createFileRoute("/")({
  loader: ({ context: { queryClient } }) =>
    queryClient.ensureQueryData({
      queryKey: queryKeys.collection(),
      queryFn: () => templateApi.getCollection(),
    }),
  component: () => <TemplatesPage initialData={Route.useLoaderData()} />, 
});