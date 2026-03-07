import { apiFetch } from "@/lib/api";

export const acceptPrivacyMutationOptions = () => ({
  mutationFn: () => apiFetch("/api/v1/lti/accept-policy", { method: "POST" }),
});
