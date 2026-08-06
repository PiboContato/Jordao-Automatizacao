import React, { useState } from 'react';
import { X, Palette, Loader2 } from 'lucide-react';
import { api, type TemaExibicao } from '../../api/client';
import { useUsuario } from '../../context/UsuarioContext';
import styles from './ModoExibicaoPopup.module.css';

const OPCOES_TEMAS: { valor: TemaExibicao; label: string; cor: string }[] = [
  { valor: 'preto', label: 'Preto (Escuro)', cor: '#1e1e2e' },
  { valor: 'colorido', label: 'Colorido (Claro)', cor: 'linear-gradient(135deg, #16a34a, #1e5880)' },
  { valor: 'branco', label: 'Branco', cor: '#f8f9fa' },
  { valor: 'azul-claro', label: 'Azul Claro', cor: '#38bdf8' },
  { valor: 'azul-escuro', label: 'Azul Escuro', cor: '#3b82f6' },
  { valor: 'verde', label: 'Verde', cor: '#10b981' },
  { valor: 'roxo', label: 'Roxo', cor: '#a78bfa' },
  { valor: 'vermelho', label: 'Vermelho', cor: '#f87171' },
  { valor: 'dourado', label: 'Dourado', cor: '#fbbf24' },
];

interface Props {
  aplicarATodos?: boolean;
  onClose: () => void;
  onSalvo?: () => void;
}

export const ModoExibicaoPopup: React.FC<Props> = ({ aplicarATodos = false, onClose, onSalvo }) => {
  const { usuario, atualizarUsuario } = useUsuario();
  const [selecionado, setSelecionado] = useState<TemaExibicao>(usuario?.modo_exibicao ?? 'colorido');
  const [salvando, setSalvando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);

  async function salvar() {
    if (!usuario) return;
    setSalvando(true);
    setErro(null);
    try {
      if (aplicarATodos) {
        await api.aplicarModoATodos(selecionado);
      } else {
        await api.editarUsuario(usuario.id, { modo_exibicao: selecionado });
      }
      atualizarUsuario({ modo_exibicao: selecionado });
      onSalvo?.();
      onClose();
    } catch (err) {
      setErro(err instanceof Error ? err.message : 'Falha ao salvar o tema');
    } finally {
      setSalvando(false);
    }
  }

  return (
    <div
      className={styles.backdrop}
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div className={styles.card}>
        <div className={styles.header}>
          <h3 className={styles.title}>
            <Palette size={18} />
            {aplicarATodos ? 'Aplicar tema a todos os usuários' : 'Escolher tema de cor'}
          </h3>
          <button onClick={onClose} className={styles.closeBtn}>
            <X size={20} />
          </button>
        </div>

        <div className={styles.body}>
          {aplicarATodos && (
            <p className={styles.hint}>
              Isso troca o tema de <strong>todos</strong> os usuários do sistema.
            </p>
          )}

          <div className={styles.lista}>
            {OPCOES_TEMAS.map((op) => (
              <label
                key={op.valor}
                className={`${styles.option} ${selecionado === op.valor ? styles.optionSelected : ''}`}
              >
                <input
                  type="radio"
                  name="modo_exibicao"
                  value={op.valor}
                  checked={selecionado === op.valor}
                  onChange={() => setSelecionado(op.valor)}
                  className={styles.radioHidden}
                />
                <span className={styles.swatch} style={{ background: op.cor }} />
                <span className={`${styles.optionLabel} ${selecionado === op.valor ? styles.optionLabelSelected : ''}`}>
                  {op.label}
                </span>
              </label>
            ))}
          </div>

          {erro && <div className={styles.erro}>{erro}</div>}
        </div>

        <div className={styles.footer}>
          <button onClick={onClose} className={styles.cancelBtn}>
            Cancelar
          </button>
          <button onClick={salvar} disabled={salvando} className={styles.saveBtn}>
            {salvando && <Loader2 size={16} className={styles.spin} />}
            Salvar
          </button>
        </div>
      </div>
    </div>
  );
};

export default ModoExibicaoPopup;
