import { Client } from '@langchain/langgraph-sdk';

const DEFAULT_AGENT_PATH = '/api';

function resolveAbsoluteUrl(url: string): string {
  if (url.startsWith('http://') || url.startsWith('https://')) {
    return url;
  }

  const normalizedPath = url.startsWith('/') ? url : `/${url}`;

  if (typeof window !== 'undefined' && window.location?.origin) {
    return `${window.location.origin}${normalizedPath}`;
  }

  return normalizedPath;
}

export function createClient(apiKey?: string): Client {
  const envUrl = import.meta.env.VITE_LANGGRAPH_API_URL;
  const apiUrl = resolveAbsoluteUrl(envUrl || DEFAULT_AGENT_PATH);

  const config: ConstructorParameters<typeof Client>[0] = {
    apiUrl,
  };

  if (apiKey && apiKey.trim().length > 0) {
    config.apiKey = apiKey;
  }

  return new Client(config);
}
