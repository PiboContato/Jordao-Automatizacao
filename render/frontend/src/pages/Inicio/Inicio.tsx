import React, { cloneElement, isValidElement } from 'react';
import { useNavigate } from 'react-router-dom';
import { useUsuario, temPermissao } from '../../context/UsuarioContext';
import { NAV_ITEMS } from '../../components/navItems';
import styles from './Inicio.module.css';

export const Inicio: React.FC = () => {
  const navigate = useNavigate();
  const { usuario } = useUsuario();

  const visiveis = NAV_ITEMS.filter(
    (item) => item.id !== 'inicio' && temPermissao(usuario, item.flag)
  );

  return (
    <div>
      <div className={`${styles.headerBox} sticky-header`} style={{ marginBottom: 0 }}>
        <h1 className={styles.title}>Bem-vindo à Jordão Imobiliária,</h1>
        <p className={styles.subtitle}>Selecione uma opção para começar</p>
      </div>

      <div className={styles.cardShortcutGrid}>
        {visiveis.map((item) => (
          <div
            key={item.id}
            className={styles.shortcutCard}
            onClick={() => navigate(item.path)}
          >
            <div className={styles.shortcutIcon}>
              {isValidElement(item.icon)
                ? cloneElement(item.icon as React.ReactElement<{ size?: number }>, { size: 40 })
                : item.icon}
            </div>
            <h3 className={styles.shortcutTitle}>{item.label}</h3>
          </div>
        ))}
      </div>
    </div>
  );
};
