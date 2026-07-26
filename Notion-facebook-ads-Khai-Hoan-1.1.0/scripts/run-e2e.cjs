const { spawn } = require('node:child_process');
const fs = require('node:fs');
const http = require('node:http');
const path = require('node:path');

const projectRoot = path.resolve(__dirname, '..');

function findPython() {
  if (process.platform !== 'win32') {
    return { command: 'python3', prefix: [] };
  }

  const localRoot = process.env.LOCALAPPDATA
    ? path.join(process.env.LOCALAPPDATA, 'Python')
    : '';
  if (localRoot && fs.existsSync(localRoot)) {
    const installed = fs.readdirSync(localRoot)
      .filter(name => name.startsWith('pythoncore-'))
      .sort()
      .reverse()
      .map(name => path.join(localRoot, name, 'python.exe'))
      .find(candidate => fs.existsSync(candidate));
    if (installed) return { command: installed, prefix: [] };

    const managerPython = path.join(localRoot, 'bin', 'python.exe');
    if (fs.existsSync(managerPython)) return { command: managerPython, prefix: [] };
  }

  return { command: 'py', prefix: ['-3'] };
}

function healthCheck() {
  return new Promise(resolve => {
    const request = http.get('http://127.0.0.1:8000/api/health', response => {
      response.resume();
      resolve(response.statusCode === 200);
    });
    request.on('error', () => resolve(false));
    request.setTimeout(1_000, () => {
      request.destroy();
      resolve(false);
    });
  });
}

async function waitForServer(server) {
  const deadline = Date.now() + 30_000;
  while (Date.now() < deadline) {
    if (server.exitCode !== null) {
      throw new Error(`Local web server stopped with exit code ${server.exitCode}.`);
    }
    if (await healthCheck()) return;
    await new Promise(resolve => setTimeout(resolve, 200));
  }
  throw new Error('Local web server did not become ready within 30 seconds.');
}

function stopServer(server) {
  if (!server || server.exitCode !== null) return;
  server.kill('SIGTERM');
}

async function main() {
  const python = findPython();
  const server = spawn(
    python.command,
    [...python.prefix, 'web_app.py', '--no-browser'],
    {
      cwd: projectRoot,
      stdio: 'inherit',
      windowsHide: true
    }
  );

  try {
    await waitForServer(server);
    const playwrightCli = path.join(projectRoot, 'node_modules', '@playwright', 'test', 'cli.js');
    const tests = spawn(
      process.execPath,
      [playwrightCli, 'test'],
      {
        cwd: projectRoot,
        env: { ...process.env, PLAYWRIGHT_EXTERNAL_SERVER: '1' },
        stdio: 'inherit',
        windowsHide: true
      }
    );
    const exitCode = await new Promise((resolve, reject) => {
      tests.once('error', reject);
      tests.once('exit', code => resolve(code ?? 1));
    });
    process.exitCode = exitCode;
  } finally {
    stopServer(server);
  }
}

main().catch(error => {
  console.error(error);
  process.exitCode = 1;
});
