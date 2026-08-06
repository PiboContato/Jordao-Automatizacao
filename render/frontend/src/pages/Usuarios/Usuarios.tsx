import React, { useEffect, useState, type FormEvent } from 'react';
import { UserPlus, Trash2, Palette, Users as UsersIcon } from 'lucide-react';
import { api, FLAGS_PERMISSAO, type Usuario } from '../../api/client';
import { useUsuario } from '../../context/UsuarioContext';
import ModoExibicaoPopup from '../../components/ModoExibicaoPopup/ModoExibicaoPopup';
import styles from './Usuarios.module.css';

export const Usuarios: React.FC = () => {
  const { usuario: usuarioAtual } = useUsuario();
  const isAdmin = usuarioAtual?.cargo === 'admin';

  const [usuarios, setUsuarios] = useState<Usuario[]>([]);
  const [erro, setErro] = useState<string | null>(null);
  const [mostrarForm, setMostrarForm] = useState(false);
  const [temaMassaAberto, setTemaMassaAberto] = useState(false);

  const [novo, setNovo] = useState({
    username: '',
    nome: '',
    senha: '',
    cargo: 'operacional' as 'admin' | 'operacional',
    acesso_automacao: true,
    acesso_bi: true,
    acesso_tabelas: true,
    acesso_auditoria: true,
    acesso_backups: true,
    acesso_logs: true,
    acesso_notificacoes: true,
    acesso_usuarios: false,
  });

  function carregar() {
    api
      .usuarios()
      .then((r) => setUsuarios(r.usuarios))
      .catch((e) => setErro(e instanceof Error ? e.message : 'Falha ao carregar usuários'));
  }

  useEffect(carregar, []);

  async function criar(e: FormEvent) {
    e.preventDefault();
    setErro(null);
    try {
      await api.criarUsuario(novo);
      setNovo({
        username: '',
        nome: '',
        senha: '',
        cargo: 'operacional',
        acesso_automacao: true,
        acesso_bi: true,
        acesso_tabelas: true,
        acesso_auditoria: true,
        acesso_backups: true,
        acesso_logs: true,
        acesso_notificacoes: true,
        acesso_usuarios: false,
      });
      setMostrarForm(false);
      carregar();
    } catch (err) {
      setErro(err instanceof Error ? err.message : 'Falha ao criar usuário');
    }
  }

  async function alternarFlag(u: Usuario, flag: keyof Usuario) {
    try {
      await api.editarUsuario(u.id, { [flag]: !u[flag] });
      carregar();
    } catch (err) {
      setErro(err instanceof Error ? err.message : 'Falha ao atualizar permissão');
    }
  }

  async function excluir(u: Usuario) {
    if (!window.confirm(`Excluir o usuário "${u.nome}"?`)) return;
    try {
      await api.excluirUsuario(u.id);
      carregar();
    } catch (err) {
      setErro(err instanceof Error ? err.message : 'Falha ao excluir usuário');
    }
  }

  return (
    <div className={styles.wrapper}>
      <div className={styles.topbar}>
        <h2 className={styles.title}>
          <UsersIcon size={24} />
          Usuários
        </h2>
        {isAdmin && (
          <div className={styles.topActions}>
            <button onClick={() => setTemaMassaAberto(true)} className={styles.ghostBtn}>
              <Palette size={16} /> Aplicar tema a todos
            </button>
            <button onClick={() => setMostrarForm((v) => !v)} className={styles.primaryBtn}>
              <UserPlus size={16} /> Novo usuário
            </button>
          </div>
        )}
      </div>

      {temaMassaAberto && (
        <ModoExibicaoPopup aplicarATodos onClose={() => setTemaMassaAberto(false)} onSalvo={carregar} />
      )}

      {erro && <p className={styles.erro}>{erro}</p>}

      {isAdmin && mostrarForm && (
        <form onSubmit={criar} className={styles.form}>
          <input
            placeholder="Login (ex: joao.silva)"
            className={styles.input}
            value={novo.username}
            onChange={(e) => setNovo({ ...novo, username: e.target.value })}
            required
          />
          <input
            placeholder="Nome completo"
            className={styles.input}
            value={novo.nome}
            onChange={(e) => setNovo({ ...novo, nome: e.target.value })}
            required
          />
          <input
            type="password"
            placeholder="Senha"
            className={styles.input}
            value={novo.senha}
            onChange={(e) => setNovo({ ...novo, senha: e.target.value })}
            required
          />
          <select
            className={styles.input}
            value={novo.cargo}
            onChange={(e) => setNovo({ ...novo, cargo: e.target.value as 'admin' | 'operacional' })}
          >
            <option value="operacional">Operacional</option>
            <option value="admin">Administrador</option>
          </select>
          <div className={styles.flagsGrid}>
            {FLAGS_PERMISSAO.map((f) => (
              <label key={f.key} className={styles.flagLabel}>
                <input
                  type="checkbox"
                  checked={Boolean(novo[f.key])}
                  onChange={(e) => setNovo({ ...novo, [f.key]: e.target.checked })}
                />
                {f.label}
              </label>
            ))}
          </div>
          <button type="submit" className={styles.primaryBtn}>
            Criar usuário
          </button>
        </form>
      )}

      <div className={styles.tableCard}>
        <table className={styles.table}>
          <thead>
            <tr>
              <th>Nome</th>
              <th>Login</th>
              <th>Cargo</th>
              {FLAGS_PERMISSAO.map((f) => (
                <th key={f.key}>{f.label}</th>
              ))}
              {isAdmin && <th></th>}
            </tr>
          </thead>
          <tbody>
            {usuarios.map((u) => (
              <tr key={u.id}>
                <td>{u.nome}</td>
                <td className={styles.muted}>{u.username}</td>
                <td>
                  <span className={`${styles.badge} ${u.cargo === 'admin' ? styles.badgeAdmin : styles.badgeOp}`}>
                    {u.cargo}
                  </span>
                </td>
                {FLAGS_PERMISSAO.map((f) => (
                  <td key={f.key}>
                    <input
                      type="checkbox"
                      checked={u.cargo === 'admin' ? true : Boolean(u[f.key])}
                      disabled={!isAdmin || u.cargo === 'admin'}
                      onChange={() => alternarFlag(u, f.key)}
                    />
                  </td>
                ))}
                {isAdmin && (
                  <td>
                    {u.cargo !== 'admin' && u.id !== usuarioAtual?.id && (
                      <button onClick={() => excluir(u)} className={styles.delBtn} title="Excluir">
                        <Trash2 size={16} />
                      </button>
                    )}
                  </td>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default Usuarios;
