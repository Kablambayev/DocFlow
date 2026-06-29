export interface AccountingDictionaryItem {
  id: string;
  code?: string | null;
  name: string;
  full_name?: string | null;
  is_active: boolean;
  source_system?: string;
  synced_at?: string | null;
}

export interface CashFlowItemDictionaryItem extends AccountingDictionaryItem {
  external_id?: string | null;
  direction: string;
}

export interface CounterpartyContractItem {
  id: string;
  organization_id: string;
  counterparty_id: string;
  currency_id?: string | null;
  code?: string | null;
  name: string;
  number?: string | null;
  contract_date?: string | null;
  is_active: boolean;
  source_system?: string;
  synced_at?: string | null;
}

export interface AccountingQueryParams {
  search?: string;
  is_active?: boolean;
  limit?: number;
  offset?: number;
}

export interface CounterpartyContractsQueryParams extends AccountingQueryParams {
  organization_id?: string;
  counterparty_id?: string;
}

export interface CashFlowOperationTypePayload {
  code: string;
  name: string;
  description?: string | null;
  sort_order?: number;
}

export interface CashFlowItemPayload {
  external_id?: string | null;
  code?: string | null;
  name: string;
  full_name?: string | null;
  direction?: string;
  is_active?: boolean;
  source_system?: string;
  raw_data?: Record<string, unknown>;
}

export interface ProjectPayload {
  code: string;
  name: string;
  description?: string | null;
  start_date?: string | null;
  end_date?: string | null;
  responsible_user_id?: string | null;
}
