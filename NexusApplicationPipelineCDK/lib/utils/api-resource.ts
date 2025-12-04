export interface ApiResource {
  path: string; // e.g., '/users', '/orders'
  method: string; // e.g., 'GET', 'POST'
}

export const API_RESOURCE_PUT_INGESTION: ApiResource = {
  path: 'ingestion',
  method: 'PUT',
};

export const API_RESOURCE_GET_QUERY: ApiResource = {
  path: 'query',
  method: 'GET',
};

export const API_RESOURCE_DELETE_SESSION_ID: ApiResource = {
  path: '{sessionId}',
  method: 'DELETE',
};

export const API_RESOURCE_DEFAULT: ApiResource = {
  path: 'default',
  method: 'GET',
};

export const API_RESOURCE_SET: Set<ApiResource> = new Set<ApiResource>([
  API_RESOURCE_PUT_INGESTION,
  API_RESOURCE_GET_QUERY,
  API_RESOURCE_DELETE_SESSION_ID,
]);
