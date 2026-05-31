'use strict';

// Redirect to /login if no token on protected pages
(function() {
  const publicPaths = ['/login'];
  const path = window.location.pathname;
  if (!publicPaths.includes(path) && !localStorage.getItem('token')) {
    window.location.href = '/login';
  }
})();

// Logout
const logoutLink = document.getElementById('logout-link');
if (logoutLink) {
  logoutLink.addEventListener('click', async (e) => {
    e.preventDefault();
    localStorage.removeItem('token');
    await fetch('/auth/logout', { method: 'POST' }).catch(() => {});
    window.location.href = '/login';
  });
}
