import React, { createContext, useContext, useEffect, useState } from 'react';
import { api, getToken, getUsuarioSalvo, limparSessao, salvarUsuarioLocal, type Usuario } from '../api/client';

interface UsuarioContextValue {
  usuario: Usuario | null;
  carregando: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
  atualizarUsuario: (patch: Partial<Usuario>) => void;
}

const UsuarioContext = createContext<UsuarioContextValue>({
  usuario: null,
  carregando: true,
  login: async () => {},
  logout: () => {},
  atualizarUsuario: () => {},
});

export function UsuarioProvider({ children }: { children: React.ReactNode }) {
  const [usuario, setUsuario] = useState<Usuario | null>(getUsuarioSalvo());
  const [carregando, setCarregando] = useState(true);

  useEffect(() => {
    if (!getToken()) {
      setCarregando(false);
      return;
    }
    api
      .me()
      .then((r) => {
        setUsuario(r.usuario);
        salvarUsuarioLocal(r.usuario);
      })
      .catch(() => {
        limparSessao();
        setUsuario(null);
      })
      .finally(() => setCarregando(false));
  }, []);

  async function login(username: string, password: string) {
    const u = await api.login(username, password);
    setUsuario(u);
  }

  function logout() {
    api.logout();
    setUsuario(null);
  }

  function atualizarUsuario(patch: Partial<Usuario>) {
    setUsuario((atual) => {
      if (!atual) return atual;
      const novo = { ...atual, ...patch };
      salvarUsuarioLocal(novo);
      return novo;
    });
  }

  return (
    <UsuarioContext.Provider value={{ usuario, carregando, login, logout, atualizarUsuario }}>
      {children}
    </UsuarioContext.Provider>
  );
}

export function useUsuario() {
  return useContext(UsuarioContext);
}

export function temPermissao(usuario: Usuario | null, flag?: keyof Usuario): boolean {
  if (!usuario) return false;
  if (usuario.cargo === 'admin') return true;
  if (!flag) return true;
  return Boolean(usuario[flag]);
}
