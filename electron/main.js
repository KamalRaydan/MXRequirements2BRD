// Electron main process for MaximoBRD (spec §13.2).
//
// Lifecycle: pick a free port → spawn the Python backend on it → poll /health until
// ready → open a window pointed at http://127.0.0.1:<port>/. Because FastAPI already
// serves the built React app at "/" and the API at "/api", the renderer is same-origin
// with the backend, so the existing frontend (fetch / EventSource / uploads) works
// unchanged — no IPC bridge needed.
//
// On quit the backend child is asked to stop with SIGTERM, then SIGKILL after a grace
// period. In development, BACKEND_DEV=1 reuses an externally running uvicorn instead.

const { app, BrowserWindow, shell } = require('electron')
const { spawn } = require('child_process')
const http = require('http')
const net = require('net')
const path = require('path')

const HEALTH_TIMEOUT_MS = 30000
const HEALTH_INTERVAL_MS = 500
const SHUTDOWN_GRACE_MS = 5000

let backendProcess = null
let mainWindow = null
let backendPort = null

// Ask the OS for a free TCP port by binding to 0 and reading what we got.
function findFreePort() {
  return new Promise((resolve, reject) => {
    const server = net.createServer()
    server.unref()
    server.on('error', reject)
    server.listen(0, '127.0.0.1', () => {
      const { port } = server.address()
      server.close(() => resolve(port))
    })
  })
}

// Decide how to launch the backend for the current run mode.
function backendLaunchSpec(port) {
  const env = { ...process.env, MAXIMOBRD_PORT: String(port) }

  if (app.isPackaged) {
    // Production: the PyInstaller binary bundled under resources/backend/.
    const exe = path.join(process.resourcesPath, 'backend', 'maximobrd-backend')
    return { command: exe, args: [], cwd: path.dirname(exe), env }
  }

  // Unpackaged dev run (`npm run dev:electron`): use the backend venv's Python.
  const backendDir = path.join(__dirname, '..', 'backend')
  const venvPython = path.join(backendDir, '.venv', 'bin', 'python')
  return { command: venvPython, args: [path.join(backendDir, 'run_server.py')], cwd: backendDir, env }
}

function startBackend(port) {
  const { command, args, cwd, env } = backendLaunchSpec(port)
  backendProcess = spawn(command, args, { cwd, env, stdio: ['ignore', 'pipe', 'pipe'] })

  backendProcess.stdout.on('data', (d) => process.stdout.write(`[backend] ${d}`))
  backendProcess.stderr.on('data', (d) => process.stderr.write(`[backend] ${d}`))
  backendProcess.on('exit', (code, signal) => {
    console.log(`[backend] exited (code=${code}, signal=${signal})`)
    backendProcess = null
  })
}

// Resolve once GET /health returns 200, or reject after HEALTH_TIMEOUT_MS.
function waitForHealth(port) {
  const deadline = Date.now() + HEALTH_TIMEOUT_MS
  return new Promise((resolve, reject) => {
    const attempt = () => {
      const req = http.get({ host: '127.0.0.1', port, path: '/health', timeout: 2000 }, (res) => {
        res.resume()
        if (res.statusCode === 200) return resolve()
        retry()
      })
      req.on('error', retry)
      req.on('timeout', () => { req.destroy(); retry() })
    }
    const retry = () => {
      if (Date.now() > deadline) return reject(new Error('Backend did not become healthy in time'))
      setTimeout(attempt, HEALTH_INTERVAL_MS)
    }
    attempt()
  })
}

function createWindow(port) {
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 820,
    minWidth: 900,
    minHeight: 600,
    title: 'MaximoBRD',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
  })

  // Open target="_blank" / external links in the user's real browser, not a new
  // Electron window (e.g. the provider model-docs links on the Settings page).
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url)
    return { action: 'deny' }
  })

  mainWindow.loadURL(`http://127.0.0.1:${port}/`)
  mainWindow.on('closed', () => { mainWindow = null })
}

function showFatalError(message) {
  const { dialog } = require('electron')
  dialog.showErrorBox('MaximoBRD could not start', message)
}

async function boot() {
  try {
    if (process.env.BACKEND_DEV === '1') {
      // Reuse an externally running uvicorn (started with --reload during development).
      backendPort = Number(process.env.MAXIMOBRD_PORT || 8765)
    } else {
      backendPort = await findFreePort()
      startBackend(backendPort)
    }
    await waitForHealth(backendPort)
    createWindow(backendPort)
  } catch (err) {
    console.error(err)
    showFatalError(String(err && err.message ? err.message : err))
    app.quit()
  }
}

// Stop the backend child: SIGTERM, then SIGKILL if it hasn't exited in time.
function stopBackend() {
  if (!backendProcess) return
  const child = backendProcess
  child.kill('SIGTERM')
  setTimeout(() => {
    if (backendProcess === child) child.kill('SIGKILL')
  }, SHUTDOWN_GRACE_MS)
}

app.whenReady().then(boot)

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0 && backendPort) createWindow(backendPort)
})

app.on('window-all-closed', () => {
  // Standard macOS apps stay alive without windows, but this is a single-window tool —
  // quitting when the window closes is the expected behavior here.
  app.quit()
})

app.on('before-quit', stopBackend)
app.on('will-quit', stopBackend)
