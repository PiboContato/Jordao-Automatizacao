-- ===================================================================
-- 001_jordao_usuarios.sql — Tabela de usuários do painel Jordão (Render)
-- Mesmo padrão do Astral/Britt: senha com hash bcrypt, cargo, tema de
-- cor (modo_exibicao) e flags de permissão por módulo.
--
-- EXECUTAR MANUALMENTE no SQL Editor do Supabase antes do deploy.
-- ===================================================================

create table if not exists public.jordao_usuarios (
  id            bigint generated always as identity primary key,
  username      text not null unique,
  nome          text not null,
  senha_hash    text not null,
  cargo         text not null default 'operacional' check (cargo in ('admin', 'operacional')),
  modo_exibicao text not null default 'colorido',

  -- Flags de permissão por módulo (admin ignora: sempre tem acesso)
  acesso_automacao     boolean not null default true,
  acesso_bi            boolean not null default true,
  acesso_tabelas       boolean not null default true,
  acesso_auditoria     boolean not null default true,
  acesso_backups       boolean not null default true,
  acesso_logs          boolean not null default true,
  acesso_notificacoes  boolean not null default true,
  acesso_usuarios      boolean not null default false,

  criado_em      timestamptz not null default now(),
  atualizado_em  timestamptz not null default now()
);

-- Índice para login por username (case-insensitive)
create index if not exists idx_jordao_usuarios_username
  on public.jordao_usuarios (lower(username));

-- ===================================================================
-- RLS: o painel acessa o Supabase com a service_role_key (bypass RLS).
-- Mantemos a política desabilitada por padrão, igual às tabelas atuais.
-- ===================================================================
alter table public.jordao_usuarios enable row level security;
