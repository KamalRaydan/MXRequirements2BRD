// Minimal, secure preload bridge.
//
// The renderer is same-origin with the backend, so all API traffic uses normal
// fetch/EventSource — no IPC needed for that. This only exposes a tiny read-only
// surface (so the UI can tell it's running inside the desktop shell), with
// contextIsolation on and nodeIntegration off (see main.js).

const { contextBridge } = require('electron')

contextBridge.exposeInMainWorld('maximobrd', {
  isDesktop: true,
  platform: process.platform,
})
