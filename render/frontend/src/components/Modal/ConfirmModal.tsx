import React from 'react';
import { AlertCircle } from 'lucide-react';
import styles from './ConfirmModal.module.css';

interface ConfirmModalProps {
  isOpen: boolean;
  title: string;
  message: string;
  confirmLabel?: string;
  cancelLabel?: string;
  onConfirm: () => void;
  onCancel: () => void;
  isLoading?: boolean;
}

export const ConfirmModal: React.FC<ConfirmModalProps> = ({
  isOpen,
  title,
  message,
  confirmLabel = 'Confirmar',
  cancelLabel = 'Cancelar',
  onConfirm,
  onCancel,
  isLoading = false
}) => {
  if (!isOpen) return null;

  return (
    <div className={styles.overlay} onClick={onCancel}>
      <div className={styles.content} onClick={(e) => e.stopPropagation()}>
        <h3 className={styles.title}>
          <AlertCircle size={20} color="#16a34a" />
          <span>{title}</span>
        </h3>
        <div className={styles.body}>
          {message}
        </div>
        <div className={styles.actions}>
          <button 
            type="button" 
            className={`${styles.btn} ${styles.btnCancel}`} 
            onClick={onCancel}
            disabled={isLoading}
          >
            {cancelLabel}
          </button>
          <button 
            type="button" 
            className={`${styles.btn} ${styles.btnConfirm}`} 
            onClick={onConfirm}
            disabled={isLoading}
          >
            {isLoading ? 'Aguardando...' : confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
};
