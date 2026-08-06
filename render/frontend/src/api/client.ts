/**
 * Cliente de API HTTP para o painel React do Agente Jordão.
 * Autenticação por JWT (Bearer token) salvo em localStorage — mesmo
 * padrão dos painéis Astral/Britt.
 */

const TOKEN_KEY = 'jordao_token';
const USUARIO_KEY = 'jordao_usuario';

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function getUsuarioSalvo(): Usuario | null {
  const raw = localStorage.getItem(USUARIO_KEY);
  return raw ? (JSON.parse(raw) as Usuario) : null;
}

export function salvarUsuarioLocal(usuario: Usuario) {
  localStorage.setItem(USUARIO_KEY, JSON.stringify(usuario));
}

export function limparSessao() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USUARIO_KEY);
}

function salvarSessao(token: string, usuario: Usuario) {
  localStorage.setItem(TOKEN_KEY, token);
  salvarUsuarioLocal(usuario);
}

export type TemaExibicao =
  | 'colorido'
  | 'azul-claro'
  | 'azul-escuro'
  | 'verde'
  | 'roxo'
  | 'vermelho'
  | 'dourado'
  | 'marrom'
  | 'preto'
  | 'branco';

export interface Usuario {
  id: number;
  username: string;
  nome: string;
  cargo: 'admin' | 'operacional';
  modo_exibicao: TemaExibicao;
  acesso_automacao: boolean;
  acesso_bi: boolean;
  acesso_tabelas: boolean;
  acesso_auditoria: boolean;
  acesso_backups: boolean;
  acesso_logs: boolean;
  acesso_notificacoes: boolean;
  acesso_usuarios: boolean;
  criado_em?: string;
}

export type FlagPermissao =
  | 'acesso_automacao'
  | 'acesso_bi'
  | 'acesso_tabelas'
  | 'acesso_auditoria'
  | 'acesso_backups'
  | 'acesso_logs'
  | 'acesso_notificacoes'
  | 'acesso_usuarios';

export const FLAGS_PERMISSAO: { key: FlagPermissao; label: string }[] = [
  { key: 'acesso_automacao', label: 'Automação' },
  { key: 'acesso_bi', label: 'Dashboard (BI)' },
  { key: 'acesso_tabelas', label: 'Tabelas' },
  { key: 'acesso_auditoria', label: 'Auditoria' },
  { key: 'acesso_backups', label: 'Backups' },
  { key: 'acesso_logs', label: 'Logs' },
  { key: 'acesso_notificacoes', label: 'Notificações' },
  { key: 'acesso_usuarios', label: 'Usuários' },
];

async function req<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getToken();
  const resp = await fetch(`/api${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(options.headers || {}),
    },
  });

  const isJson = resp.headers.get('content-type')?.includes('application/json');
  const data = isJson ? await resp.json() : null;

  if (resp.status === 401) {
    limparSessao();
  }
  if (!resp.ok) {
    throw new Error(data?.error || `Erro HTTP ${resp.status}`);
  }
  return data as T;
}

export const api = {
  async login(username: string, password: string): Promise<Usuario> {
    const resp = await req<{ token: string; usuario: Usuario }>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ username, password }),
    });
    salvarSessao(resp.token, resp.usuario);
    return resp.usuario;
  },
  me: () => req<{ usuario: Usuario }>('/auth/me'),
  logout: () => limparSessao(),
  ultimaAtualizacao: () => req<{ ultima_atualizacao: string | null }>('/status/ultima-atualizacao'),

  usuarios: () => req<{ usuarios: Usuario[] }>('/usuarios'),
  criarUsuario: (dados: {
    username: string;
    nome: string;
    senha: string;
    cargo: 'admin' | 'operacional';
    acesso_automacao: boolean;
    acesso_bi: boolean;
    acesso_tabelas: boolean;
    acesso_auditoria: boolean;
    acesso_backups: boolean;
    acesso_logs: boolean;
    acesso_notificacoes: boolean;
    acesso_usuarios: boolean;
  }) => req<{ usuario: Usuario }>('/usuarios', { method: 'POST', body: JSON.stringify(dados) }),
  editarUsuario: (id: number, dados: Partial<Usuario>) =>
    req<{ usuario: Usuario }>(`/usuarios/${id}`, { method: 'PUT', body: JSON.stringify(dados) }),
  excluirUsuario: (id: number) => req<{ success: boolean }>(`/usuarios/${id}`, { method: 'DELETE' }),
  aplicarModoATodos: (modo: TemaExibicao) =>
    req<{ success: boolean; atualizados: number }>('/usuarios/modo-massa', {
      method: 'PUT',
      body: JSON.stringify({ modo_exibicao: modo }),
    }),
};

// ===================================================================
// API legada usada pelas páginas (Automacao, BI, Tabelas, ...).
// Mantém a mesma assinatura, mas agora anexa o token JWT automaticamente.
// ===================================================================

export interface RequestOptions extends RequestInit {
  json?: any;
}

export async function apiFetch<T>(endpoint: string, options: RequestOptions = {}): Promise<T> {
  const headers = new Headers(options.headers || {});
  const token = getToken();

  if (token) {
    headers.set('Authorization', `Bearer ${token}`);
  }
  if (options.json && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
    options.body = JSON.stringify(options.json);
  }

  const response = await fetch(endpoint, {
    ...options,
    headers,
  });

  if (response.status === 401) {
    limparSessao();
    if (window.location.pathname !== '/login') {
      window.location.href = '/login';
    }
    throw new Error('Não autorizado. Redirecionando...');
  }

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.error || `Erro HTTP: ${response.status}`);
  }

  if (response.status === 204) {
    return {} as T;
  }

  return response.json() as Promise<T>;
}
