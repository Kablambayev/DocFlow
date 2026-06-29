import { Checkbox, DatePicker, Form, Input, InputNumber, Select, Typography } from "antd";
import TextArea from "antd/es/input/TextArea";
import dayjs from "dayjs";
import { useQuery } from "@tanstack/react-query";
import { useEffect } from "react";

import type { DynamicFieldSchema, DynamicFormSchema } from "../types/document";
import {
  getCashFlowOperationTypes,
  getCashFlowItems,
  getCounterparties,
  getCounterpartyContracts,
  getCurrencies,
  getExpenseItems,
  getOrganizations,
  getProjects,
} from "../../entities/accounting";
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

const dictionaryLoaders = {
  organizations: getOrganizations,
  counterparties: getCounterparties,
  counterparty_contracts: getCounterpartyContracts,
  currencies: getCurrencies,
  expense_items: getExpenseItems,
  cash_flow_items: getCashFlowItems,
  cash_flow_operation_types: getCashFlowOperationTypes,
  projects: getProjects,
} as const;

const getDictionaryValue = (item: unknown, key: string): unknown => {
  if (typeof item !== "object" || item === null) {
    return undefined;
  }
  return (item as Record<string, unknown>)[key];
};

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

const DictionaryField = ({ field, disabled }: { field: DynamicFieldSchema; disabled?: boolean }) => {
  const form = Form.useFormInstance();
  const isDisabled = disabled || field.readonly;
  const settings = field.settings ?? {};
  const dictionaryName = settings.dictionary;
  const valueField = settings.valueField ?? "id";
  const labelField = settings.labelField ?? "name";
  const dependsOn = settings.dependsOn ?? [];
  const dependencies = form.getFieldsValue(true) as Record<string, unknown>;
  const dependsReady = dependsOn.every((dependency) => Boolean(dependencies?.[dependency.field]));
  const isContractDictionary = dictionaryName === "counterparty_contracts";

  const loader = dictionaryName ? dictionaryLoaders[dictionaryName as keyof typeof dictionaryLoaders] : undefined;
  if (!loader) {
    if (dictionaryName) {
      console.warn(`Unknown dictionary loader: ${dictionaryName}`);
    }
    return <Select disabled placeholder="Неизвестный справочник" options={[]} />;
  }

  const params: Record<string, unknown> = { is_active: true, limit: 50, offset: 0 };
  for (const dependency of dependsOn) {
    params[dependency.param] = dependencies?.[dependency.field] ?? undefined;
  }

  // eslint-disable-next-line react-hooks/rules-of-hooks
  const query = useQuery({
    queryKey: ["dictionary", dictionaryName, params],
    queryFn: () => (loader ? loader(params as never) : Promise.resolve([])),
    enabled: Boolean(loader) && !isDisabled && (!dependsOn.length || dependsReady),
  });

  // eslint-disable-next-line react-hooks/rules-of-hooks
  useEffect(() => {
    if (!loader) return;
    if (!dependsOn.length) return;
    const currentValue = form.getFieldValue(field.code);
    if (!dependsReady && currentValue) {
      form.setFieldValue(field.code, undefined);
      return;
    }
    if (!currentValue) return;
    const exists = (query.data ?? []).some((item) => String(getDictionaryValue(item, valueField)) === String(currentValue));
    if (!exists) {
      form.setFieldValue(field.code, undefined);
    }
  }, [dependsReady, field.code, form, loader, query.data, valueField, dependsOn.length]);

  const options = (query.data ?? []).map((item) => ({
    value: String(getDictionaryValue(item, valueField)),
    label: String(getDictionaryValue(item, labelField) ?? getDictionaryValue(item, "name") ?? getDictionaryValue(item, "code") ?? getDictionaryValue(item, "id")),
  }));

  const blockedByDependencies = dependsOn.length > 0 && !dependsReady;
  const placeholder = blockedByDependencies
    ? isContractDictionary
      ? "Сначала выберите организацию и контрагента"
      : "Сначала заполните зависимые поля"
    : "Выберите значение";

  return (
    <Select
      showSearch={settings.searchable !== false}
      allowClear
      disabled={isDisabled || blockedByDependencies}
      loading={query.isLoading}
      placeholder={placeholder}
      options={options}
      filterOption={(input, option) => String(option?.label ?? "").toLowerCase().includes(input.toLowerCase())}
    />
  );
};

export const DynamicFormRenderer = ({ schema, disabled, documentId, documentStatus }: DynamicFormRendererProps) => {
  const sections = [...schema.sections].sort((a, b) => (a.sortOrder ?? 0) - (b.sortOrder ?? 0));

  return (
    <>
      {sections.map((section) => (
        <div key={section.code} style={{ marginBottom: 20 }}>
          <Typography.Title level={5}>{section.name}</Typography.Title>
          {[...section.fields].sort((a, b) => (a.sortOrder ?? 0) - (b.sortOrder ?? 0)).map((field) => {
            const renderItem = () => (
              <Form.Item
                key={field.code}
                name={field.code}
                label={field.name}
                valuePropName={field.type === "boolean" ? "checked" : "value"}
                normalize={(value) => (dayjs.isDayjs(value) ? value.toISOString() : value)}
                rules={field.required ? [{ required: true, message: `Поле ${field.name} обязательно` }] : undefined}
              >
                {field.type === "dictionary" ? (
                  <DictionaryField field={field} disabled={disabled} />
                ) : (
                  renderField(field, disabled, documentId, documentStatus)
                )}
              </Form.Item>
            );
            if (field.type !== "dictionary" || !field.settings?.dependsOn?.length) return renderItem();
            const dependencyFields = field.settings.dependsOn.map((dependency) => dependency.field);
            return (
              <Form.Item key={`${field.code}-dependencies`} noStyle shouldUpdate={(previous, current) => dependencyFields.some((code) => previous[code] !== current[code])}>
                {renderItem}
              </Form.Item>
            );
          })}
        </div>
      ))}
    </>
  );
};
