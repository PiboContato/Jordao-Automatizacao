/**
 * Cliente de API HTTP para o painel React do Agente Jordão.
 * Encapsula chamadas fetch e trata erros de autenticação (401).
 */

export interface RequestOptions extends RequestInit {
  json?: any;
}

export async function apiFetch<T>(endpoint: string, options: RequestOptions = {}): Promise<T> {
  const headers = new Headers(options.headers || {});
  
  if (options.json && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
    options.body = JSON.stringify(options.json);
  }

  const response = await fetch(endpoint, {
    ...options,
    headers,
  });

  if (response.status === 401) {
    // Se não autorizado, redireciona o usuário para /login
    if (window.location.pathname !== '/login') {
      window.location.href = '/login';
    }
    throw new Error('Não autorizado. Redirecionando...');
  }

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.error || `Erro HTTP: ${response.status}`);
  }

  // Se resposta vazia (como no logout)
  if (response.status === 204) {
    return {} as T;
  }

  return response.json() as Promise<T>;
}
