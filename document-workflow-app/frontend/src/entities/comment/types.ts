export type DocumentCommentType = "general" | "approval" | "system";

export interface DocumentComment {
  id: string;
  document_id: string;
  author_id: string;
  author_name: string | null;
  comment_text: string;
  comment_type: DocumentCommentType;
  parent_comment_id: string | null;
  created_at: string;
  updated_at: string | null;
}

export interface CreateCommentPayload {
  comment_text: string;
  parent_comment_id?: string | null;
}

export interface UpdateCommentPayload {
  comment_text: string;
}
