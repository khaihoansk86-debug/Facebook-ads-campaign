const { defineConfig, devices } = require('@playwright/test');
const fs = require('node:fs');
const path = require('node:path');

const localPythonRoot = process.env.LOCALAPPDATA
  ? path.join(process.env.LOCALAPPDATA, 'Python')
  : '';
const installedPython = localPythonRoot && fs.existsSync(localPythonRoot)
  ? fs.readdirSync(localPythonRoot)
      .filter(name => name.startsWith('pythoncore-'))
      .sort()
      .reverse()
      .map(name => path.join(localPythonRoot, name, 'python.exe'))
      .find(candidate => fs.existsSync(candidate))
  : '';
const localPython = installedPython
  || (localPythonRoot ? path.join(localPythonRoot, 'bin', 'python.exe') : '');
const pythonCommand = localPython && fs.existsSync(localPython)
  ? `"${localPython}"`
  : process.platform === 'win32'
    ? 'py -3'
    : 'python3';

module.exports = defineConfig({
  testDir: './tests/e2e',
  fullyParallel: false,
  retries: 0,
  reporter: [['list'], ['html', { outputFolder: 'playwright-report', open: 'never' }]],
  use: {
    baseURL: 'http://127.0.0.1:8000',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    actionTimeout: 10_000,
    navigationTimeout: 30_000,
  },
  projects: [
    { name: 'máy tính', use: { ...devices['Desktop Chrome'] } },
    { name: 'điện thoại', use: { ...devices['Pixel 5'] } },
  ],
  webServer: process.env.PLAYWRIGHT_EXTERNAL_SERVER ? undefined : {
    command: `${pythonCommand} web_app.py --no-browser`,
    url: 'http://127.0.0.1:8000/api/health',
    reuseExistingServer: true,
    timeout: 30_000,
  },
});
