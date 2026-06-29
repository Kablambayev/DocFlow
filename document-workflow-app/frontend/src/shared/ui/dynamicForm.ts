import dayjs from "dayjs";

import type { DynamicFormSchema } from "../types/document";

export const normalizeDynamicInitialValues = (values: Record<string, unknown> = {}, schema: DynamicFormSchema) => {
  const result: Record<string, unknown> = { ...values };
  for (const section of schema.sections) {
    for (const field of section.fields) {
      const value = result[field.code];
      if ((field.type === "date" || field.type === "datetime") && typeof value === "string") {
        result[field.code] = dayjs(value);
      }
    }
  }
  return result;
};
