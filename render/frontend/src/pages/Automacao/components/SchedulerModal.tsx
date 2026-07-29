import React, { useEffect, useState } from 'react';
import { Clock } from 'lucide-react';
import { apiFetch } from '../../../api/client';
import styles from '../../../components/Modal/ConfirmModal.module.css'; // Reutiliza estilo de modal genérico

interface SchedulerModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const SchedulerModal: React.FC<SchedulerModalProps> = ({ isOpen, onClose }) => {
  const [horarios, setHorarios] = useState<string[]>(Array(8).fill(''));
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    if (isOpen) {
      carregarHorarios();
    }
  }, [isOpen]);

  const carregarHorarios = async () => {
    try {
      const data = await apiFetch<{ horarios: string[] }>('/api/agendamento');
      const loaded = data.horarios || [];
      const padded = Array(8).fill('').map((_, i) => loaded[i] || '');
      setHorarios(padded);
    } catch (err) {
      console.error("Erro ao carregar agendamentos:", err);
    }
  };

  const handleTimeChange = (index: number, val: string) => {
    const next = [...horarios];
    next[index] = val;
    setHorarios(next);
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);

    const activeTimes = horarios.filter(h => h.trim() !== '');

    try {
      await apiFetch<{ status: string }>('/api/agendamento', {
        method: 'POST',
        json: { horarios: activeTimes }
      });
      alert("Agendamento enviado para a VM com sucesso! O arquivo da VM será atualizado.");
      onClose();
    } catch (err: any) {
      alert("Erro ao salvar horários: " + (err.message || 'Falha desconhecida'));
    } finally {
      setIsLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className={styles.overlay} onClick={onClose}>
      <div 
        className={styles.content} 
        style={{ maxWidth: '500px', padding: '30px' }} 
        onClick={(e) => e.stopPropagation()}
      >
        <h3 className={styles.title} style={{ borderBottom: '2px solid #3b82f6' }}>
          <Clock size={20} color="#3b82f6" />
          <span>Agendador Diário (VM)</span>
        </h3>
        <p style={{ color: '#666', fontSize: '0.9rem', marginTop: '10px', marginBottom: '20px' }}>
          Programe até 8 horários por dia para o robô rodar automaticamente na VM:
        </p>

        <form onSubmit={handleSave}>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '15px', marginBottom: '25px' }}>
            {horarios.map((time, idx) => (
              <div key={idx}>
                <label style={{ fontSize: '0.85rem', fontWeight: 600, display: 'block', marginBottom: '5px', color: '#444' }}>
                  Horário {idx + 1}
                </label>
                <input
                  type="time"
                  value={time}
                  onChange={(e) => handleTimeChange(idx, e.target.value)}
                  style={{ width: '100%', padding: '8px', border: '1px solid #dee2e6', borderRadius: '4px' }}
                  disabled={isLoading}
                />
              </div>
            ))}
          </div>

          <div className={styles.actions} style={{ gap: '10px' }}>
            <button
              type="button"
              className={`${styles.btn} ${styles.btnCancel}`}
              onClick={onClose}
              disabled={isLoading}
            >
              Cancelar
            </button>
            <button
              type="submit"
              className={`${styles.btn} ${styles.btnConfirm}`}
              style={{ backgroundColor: '#ef4444' }}
              disabled={isLoading}
            >
              {isLoading ? 'Salvando...' : 'Salvar Horários'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
