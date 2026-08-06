import type { ReactNode } from 'react';
import {
  Home,
  Settings,
  BarChart3,
  Table2,
  ClipboardList,
  Bell,
  Database,
  ScrollText,
  Users,
} from 'lucide-react';
import type { Usuario } from '../api/client';

export interface NavItem {
  id: string;
  label: string;
  path: string;
  icon: ReactNode;
  flag?: keyof Usuario;
}

export const NAV_ITEMS: NavItem[] = [
  { id: 'inicio', label: 'Menu', path: '/', icon: <Home size={20} /> },
  { id: 'automacao', label: 'Automação', path: '/automacao', icon: <Settings size={20} />, flag: 'acesso_automacao' },
  { id: 'bi', label: 'BI', path: '/bi', icon: <BarChart3 size={20} />, flag: 'acesso_bi' },
  { id: 'tabelas', label: 'Tabelas', path: '/tabelas', icon: <Table2 size={20} />, flag: 'acesso_tabelas' },
  { id: 'auditoria', label: 'Auditoria', path: '/auditoria', icon: <ClipboardList size={20} />, flag: 'acesso_auditoria' },
  { id: 'notificacoes', label: 'Notificações', path: '/indicadores-notificacoes', icon: <Bell size={20} />, flag: 'acesso_notificacoes' },
  { id: 'backups', label: 'Backups', path: '/backups', icon: <Database size={20} />, flag: 'acesso_backups' },
  { id: 'logs', label: 'Logs', path: '/logs', icon: <ScrollText size={20} />, flag: 'acesso_logs' },
  { id: 'usuarios', label: 'Usuários', path: '/usuarios', icon: <Users size={20} />, flag: 'acesso_usuarios' },
];
