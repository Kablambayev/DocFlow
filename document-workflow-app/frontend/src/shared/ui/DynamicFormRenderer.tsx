import { Checkbox, DatePicker, Form, Input, InputNumber, Select, Typography } from "antd";
import TextArea from "antd/es/input/TextArea";
import dayjs from "dayjs";

import type { DynamicFieldSchema, DynamicFormSchema } from "../types/document";
import { DocumentFilesPanel } from "./DocumentFilesPanel";

interface DynamicFormRendererProps {
  schema: DynamicFormSchema;
  disabled?: boolean;
  documentId?: string;
  documentStatus?: string;
}

const enumOptions = (field: DynamicFieldSchema) =>
  (field.settings?.options ?? []).map((option) =>
    typeof option === "string" ? { label: option, value: option } : option,
  );

const renderField = (field: DynamicFieldSchema, disabled?: boolean, documentId?: string, documentStatus?: string) => {
  const isDisabled = disabled || field.readonly;
  switch (field.type) {
    case "string":
      return <Input disabled={isDisabled} />;
    case "text":
      return <TextArea rows={4} disabled={isDisabled} />;
    case "integer":
      return <InputNumber style={{ width: "100%" }} precision={0} disabled={isDisabled} />;
    case "decimal":
    case "money":
      return (
        <InputNumber
          style={{ width: "100%" }}
          precision={field.settings?.precision}
          min={field.settings?.min}
          max={field.settings?.max}
          disabled={isDisabled}
        />
      );
    case "date":
      return <DatePicker style={{ width: "100%" }} disabled={isDisabled} />;
    case "datetime":
      return <DatePicker style={{ width: "100%" }} showTime disabled={isDisabled} />;
    case "boolean":
      return <Checkbox>Да</Checkbox>;
    case "enum":
      return <Select options={enumOptions(field)} disabled={isDisabled} />;
    case "reference":
      return <Select placeholder="Reference value" options={[]} disabled={isDisabled} />;
    case "file":
      if (documentId && documentStatus) {
        return <DocumentFilesPanel documentId={documentId} documentStatus={documentStatus} fieldCode={field.code} readonly={isDisabled} />;
      }
      return <Typography.Text type="secondary">Файл можно будет прикрепить после сохранения документа</Typography.Text>;
    case "table":
      return <Typography.Text type="secondary">TODO: table field renderer</Typography.Text>;
    default:
      return <Input disabled={isDisabled} />;
  }
};

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

export const DynamicFormRenderer = ({ schema, disabled, documentId, documentStatus }: DynamicFormRendererProps) => {
  const sections = [...schema.sections].sort((a, b) => (a.sortOrder ?? 0) - (b.sortOrder ?? 0));

  return (
    <>
      {sections.map((section) => (
        <div key={section.code} style={{ marginBottom: 20 }}>
          <Typography.Title level={5}>{section.name}</Typography.Title>
          {[...section.fields].sort((a, b) => (a.sortOrder ?? 0) - (b.sortOrder ?? 0)).map((field) => (
            <Form.Item
              key={field.code}
              name={field.code}
              label={field.name}
              valuePropName={field.type === "boolean" ? "checked" : "value"}
              normalize={(value) => (dayjs.isDayjs(value) ? value.toISOString() : value)}
              rules={field.required ? [{ required: true, message: `Поле ${field.name} обязательно` }] : undefined}
            >
              {renderField(field, disabled, documentId, documentStatus)}
            </Form.Item>
          ))}
        </div>
      ))}
    </>
  );
};
