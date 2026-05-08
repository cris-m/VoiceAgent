export interface ApiFieldErrors {
  [field: string]: string[];
}

export interface ApiError {
  code: string;
  message: string;
  fields?: ApiFieldErrors;
}

export interface NormalizedError {
  status: number;
  error: ApiError;
}

export function fieldError(
  err: NormalizedError | undefined,
  field: string
): string | undefined {
  return err?.error.fields?.[field]?.[0];
}

export function hasErrorCode(
  err: NormalizedError | undefined,
  code: string
): boolean {
  return err?.error.code === code;
}
