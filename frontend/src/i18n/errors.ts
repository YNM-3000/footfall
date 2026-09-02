/**
 * API error codes with a translation. Listed explicitly so the compiler can
 * check every one against the catalogue — an unlisted code falls back to the
 * server's English message rather than rendering a raw key.
 */
export const TRANSLATED_ERROR_CODES = [
  "unsupported_file_type",
  "unreadable_video",
  "video_not_found",
  "frame_unreadable",
  "job_not_found",
  "preview_not_ready",
  "job_already_finished",
] as const;

export type TranslatedErrorCode = (typeof TRANSLATED_ERROR_CODES)[number];

export const isTranslatedErrorCode = (code: string): code is TranslatedErrorCode =>
  (TRANSLATED_ERROR_CODES as readonly string[]).includes(code);
