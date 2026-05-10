import { apiFetch } from "../lib/api";
import type { AcceptPolicyResponse } from "../model/privacy";

export const privacyApi = {
  acceptPolicy: () =>
    apiFetch<AcceptPolicyResponse>("/lti/accept-policy", {
      method: "POST",
    }),
};
