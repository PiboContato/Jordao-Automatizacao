// Import the functions you need from the SDKs you need
import { initializeApp } from "firebase/app";
import { getMessaging, getToken, onMessage } from "firebase/messaging";

// Sua configuração do Firebase web app
// Preencha no arquivo .env do frontend
const firebaseConfig = {
  apiKey: import.meta.env.VITE_FIREBASE_API_KEY,
  authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN,
  projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID,
  storageBucket: import.meta.env.VITE_FIREBASE_STORAGE_BUCKET,
  messagingSenderId: import.meta.env.VITE_FIREBASE_MESSAGING_SENDER_ID,
  appId: import.meta.env.VITE_FIREBASE_APP_ID
};

// Inicializar Firebase
let app: any;
let messaging: any;

try {
  app = initializeApp(firebaseConfig);
  messaging = getMessaging(app);
} catch (error) {
  console.error("Erro ao inicializar Firebase (configuração ausente?):", error);
}

// Chave pública VAPID (Voluntary Application Server Identification) do Firebase
const VAPID_KEY = import.meta.env.VITE_FIREBASE_VAPID_KEY;

export const requestFirebaseNotificationPermission = async () => {
  if (!messaging) return null;
  
  try {
    const permission = await Notification.requestPermission();
    if (permission === 'granted') {
      let registration = null;
      if ('serviceWorker' in navigator) {
        registration = await navigator.serviceWorker.register('/firebase-messaging-sw.js');
      }

      const options: any = { vapidKey: VAPID_KEY };
      if (registration) {
        options.serviceWorkerRegistration = registration;
      }

      const currentToken = await getToken(messaging, options);
      if (currentToken) {
        return currentToken;
      } else {
        console.warn("Nenhum token de registro disponível.");
      }
    } else {
      console.warn("Permissão de notificação negada.");
    }
  } catch (err) {
    console.error("Erro ao recuperar token FCM:", err);
  }
  return null;
};

export const onMessageListener = () =>
  new Promise((resolve) => {
    if (messaging) {
      onMessage(messaging, (payload) => {
        resolve(payload);
      });
    }
  });

export { messaging };
