import "i18next";

import type { zh } from "./locales/zh";

declare module "i18next" {
  interface CustomTypeOptions {
    defaultNS: "translation";
    // Keys are checked against the Chinese catalogue, which is the source of
    // truth; en.ts is typed as `typeof zh`, so the two cannot drift.
    resources: { translation: typeof zh };
  }
}
