import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { apiFetch } from '../../api/client';
import styles from './Login.module.css';

interface LoginProps {
  onLoginSuccess: () => void;
}

export const Login: React.FC<LoginProps> = ({ onLoginSuccess }) => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError(null);

    try {
      await apiFetch<{ success: boolean }>('/api/auth/login', {
        method: 'POST',
        json: { username, password }
      });
      onLoginSuccess();
      navigate('/');
    } catch (err: any) {
      setError(err.message || 'Credenciais inválidas');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className={styles.container}>
      <div className={styles.glassCard}>
        <div style={{ width: '48px', height: '48px', margin: '0 auto 16px auto', borderRadius: '12px', backgroundColor: '#a0522d', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'white', fontWeight: '900', fontSize: '24px', boxShadow: '0 1px 2px 0 rgba(0, 0, 0, 0.05)' }}>
          J
        </div>
        <h1 className={styles.title}>Agente Jordão</h1>
        <p className={styles.subtitle}>Painel Remoto (Read-Only)</p>

        {error && (
          <div className={styles.errorMsg}>
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit}>
          <div className={styles.formGroup}>
            <label htmlFor="username">Usuário</label>
            <input
              type="text"
              id="username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
              autoComplete="username"
              autoFocus
              disabled={isLoading}
            />
          </div>
          <div className={styles.formGroup}>
            <label htmlFor="password">Senha</label>
            <input
              type="password"
              id="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              autoComplete="current-password"
              disabled={isLoading}
            />
          </div>
          <button 
            type="submit" 
            className={styles.btn}
            disabled={isLoading}
          >
            {isLoading ? 'Conectando...' : 'Entrar no Painel'}
          </button>
        </form>
      </div>
    </div>
  );
};
