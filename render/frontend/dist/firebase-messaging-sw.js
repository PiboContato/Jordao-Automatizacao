// Import and configure the Firebase SDK
importScripts('https://www.gstatic.com/firebasejs/10.9.0/firebase-app-compat.js');
importScripts('https://www.gstatic.com/firebasejs/10.9.0/firebase-messaging-compat.js');

// ATENÇÃO: Preencha com as mesmas chaves do seu projeto Firebase
// No Service Worker as variáveis de ambiente do Vite (import.meta.env) não funcionam diretamente
const firebaseConfig = {
  apiKey: "AIzaSyD5jsNuEBhXYDdvRMUtf7b9sOjKjUJIQLA",
  authDomain: "espaco-clif-app.firebaseapp.com",
  projectId: "espaco-clif-app",
  storageBucket: "espaco-clif-app.firebasestorage.app",
  messagingSenderId: "1023782578609",
  appId: "1:1023782578609:web:8fcf5c3fd90ffb5982f590"
};

try {
  firebase.initializeApp(firebaseConfig);
  const messaging = firebase.messaging();

  // Tratamento de mensagens em background
  messaging.onBackgroundMessage((payload) => {
    console.log('[firebase-messaging-sw.js] Mensagem recebida em background:', payload);
    
    // Se a mensagem já possui o objeto 'notification', o próprio Chrome/Android já exibe o Push nativamente.
    // Invocamos showNotification apenas se a notificação vier exclusivamente no objeto 'data'.
    if (!payload.notification) {
      const notificationTitle = payload.data?.title || 'Notificação Jordão Automatização';
      const notificationOptions = {
        body: payload.data?.body || '',
        icon: '/favicon.png', // Substitua pelo ícone real do projeto se houver
        tag: payload.data?.tag || 'jordao-notif',
        renotify: true,
        data: payload.data || {}
      };

      self.registration.showNotification(notificationTitle, notificationOptions);
    }
  });
} catch (error) {
  console.error("Erro ao inicializar Firebase SW:", error);
}

// Manipulador de clique na notificação nativa (abrir/focar o app)
self.addEventListener('notificationclick', (event) => {
  event.notification.close();

  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true }).then((windowClients) => {
      for (let client of windowClients) {
        if (client.url.includes('/') && 'focus' in client) {
          return client.focus();
        }
      }
      if (clients.openWindow) {
        return clients.openWindow('/');
      }
    })
  );
});
