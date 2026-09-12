import { test, expect } from '@playwright/test';
import { readFileSync, existsSync } from 'node:fs';
import { spawnSync } from 'node:child_process';
import { resolve } from 'node:path';

const fixture = JSON.parse(readFileSync('../tests/fixtures/agv1-text.json', 'utf8'));

test('Python AGV1 to real Web Worker and back preserves mixed line endings', async ({ page }) => {
  const original = '\ufeff中文\0🔐\r\ne\u0301\rx\ny';
  const password = 'synthetic-interop-password';
  const localPython = resolve('../.venv', process.platform === 'win32' ? 'Scripts/python.exe' : 'bin/python');
  const pythonExecutable = process.env.AEGISVAULT_PYTHON ?? (existsSync(localPython) ? localPython : 'python');
  const python = (action: string, value: string) => {
    const result = spawnSync(pythonExecutable, ['-c',
      'import sys,json; from aegisvault.core.crypto import encrypt_text,decrypt_text; d=json.load(sys.stdin); print(json.dumps(encrypt_text(d["value"],d["password"]).ciphertext if d["action"]=="encrypt" else decrypt_text(d["value"],d["password"]).plaintext,ensure_ascii=True))'],
      { input: JSON.stringify({ action, value, password }), encoding: 'utf8', timeout: 15000,
        env: { ...process.env, PYTHONPATH: resolve('../src'), PYTHONUTF8: '1' } });
    expect(result.status, result.stderr).toBe(0);
    return JSON.parse(result.stdout) as string;
  };
  const token = python('encrypt', original);
  await page.addInitScript(() => Object.defineProperty(navigator.clipboard, 'writeText', {
    value: async (text: string) => { (window as unknown as { copied: string }).copied = text; },
  }));
  await page.goto('./');
  await page.locator('#input').fill(token);
  await page.locator('#password').fill(password);
  await page.locator('#reverse').click();
  await expect(page.locator('#status')).toContainText('完成');
  await page.locator('#copy').click();
  expect(await page.evaluate(() => (window as unknown as { copied: string }).copied)).toBe(original);
  await page.locator('#swap').click();
  await page.locator('#forward').click();
  await expect(page.locator('#output')).toHaveValue(/^AGV1\./);
  expect(python('decrypt', await page.locator('#output').inputValue())).toBe(original);
});

for (const original of ['a\r\nb', 'a\rb', 'a\nb', '\ufeff中文\0🔐\r\ne\u0301\rx\ny', '', 'ascii']) {
  test(`result copy and reuse preserve code points: ${JSON.stringify(original)}`, async ({ page }) => {
    await page.addInitScript(() => {
      Object.defineProperty(navigator.clipboard, 'writeText', {
        value: async (text: string) => { (window as unknown as { copied: string }).copied = text; },
      });
    });
    await page.goto('./');
    await page.locator('#base64-tab').click();
    const encoded = Buffer.from(original).toString('base64');
    await page.locator('#input').fill(encoded);
    await page.locator('#reverse').click();
    await expect(page.locator('#status')).toContainText('完成');
    await page.locator('#copy').click();
    expect(await page.evaluate(() => (window as unknown as { copied: string }).copied)).toBe(original);
    await page.locator('#swap').click();
    await page.locator('#forward').click();
    await expect(page.locator('#status')).toContainText('完成');
    await expect(page.locator('#output')).toHaveValue(encoded);
    // Editing a reused result replaces the raw input; stale CR must not return.
    await page.locator('#input').fill('edited\ntext');
    await page.locator('#forward').click();
    await expect(page.locator('#output')).toHaveValue(Buffer.from('edited\ntext').toString('base64'));
    await page.locator('#clear').click();
    await page.locator('#forward').click();
    await expect(page.locator('#status')).toContainText('完成');
    await expect(page.locator('#output')).toHaveValue('');
  });
}

test('real Worker decrypts Windows fixture; roundtrip, copy, cancellation and no network/storage', async ({ page, context }) => {
  const requests: string[] = [];
  const errors: string[] = [];
  page.on('request', r => requests.push(r.url()));
  page.on('pageerror', e => errors.push(e.message));
  await page.goto('./');
  await page.getByLabel('输入', { exact: true }).fill(fixture.token);
  await page.getByLabel('密码', { exact: true }).fill(fixture.password);
  await page.getByRole('button', { name: '显示密码' }).click();
  await expect(page.locator('#password')).toHaveAttribute('type', 'text');
  await page.getByRole('button', { name: '解密', exact: true }).click();
  await expect(page.locator('#output')).toHaveValue(fixture.plaintext);
  await context.grantPermissions(['clipboard-read', 'clipboard-write']);
  await page.getByRole('button', { name: '复制结果' }).click();
  await expect(page.locator('#status')).toContainText('已复制');
  expect(await page.evaluate(() => navigator.clipboard.readText())).toBe(fixture.plaintext);
  await page.getByRole('button', { name: '交换输入输出' }).click();
  await page.getByRole('button', { name: '加密', exact: true }).click();
  await expect(page.locator('#output')).toHaveValue(/^AGV1\./);
  await page.getByRole('button', { name: '交换输入输出' }).click();
  await page.getByRole('button', { name: '解密', exact: true }).click();
  await expect(page.locator('#output')).toHaveValue(fixture.plaintext);
  await page.getByLabel('密码', { exact: true }).fill('wrong');
  await page.getByRole('button', { name: '解密', exact: true }).click();
  await expect(page.locator('#status')).toContainText('密码错误');
  await expect(page.locator('#output')).toHaveValue('');
  await page.getByRole('button', { name: '加密', exact: true }).click();
  await page.getByRole('button', { name: '取消', exact: true }).click();
  await expect(page.locator('#status')).toHaveText('已取消。');
  await page.getByRole('button', { name: '清空', exact: true }).click();
  await expect(page.locator('#password')).toHaveValue('');
  expect(await page.evaluate(() => [localStorage.length, sessionStorage.length])).toEqual([0, 0]);
  expect(requests.every(url => url.startsWith('http://127.0.0.1:4173/AegisVaultWindows/'))).toBe(true);
  expect(errors).toEqual([]);
});

test('strict Base64, keyboard access, dark mobile layout', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.emulateMedia({ colorScheme: 'dark' });
  await page.goto('./');
  await page.getByRole('button', { name: 'Base64', exact: true }).focus();
  await page.keyboard.press('Enter');
  await expect(page.locator('#hint')).toContainText('Base64 不是加密');
  await expect(page.locator('#password')).toBeHidden();
  await page.locator('#input').fill('你好 🔐');
  await page.getByRole('button', { name: '编码', exact: true }).click();
  await expect(page.locator('#output')).toHaveValue(Buffer.from('你好 🔐').toString('base64'));
  await page.getByRole('button', { name: '交换输入输出' }).click();
  await page.getByRole('button', { name: '解码', exact: true }).click();
  await expect(page.locator('#output')).toHaveValue('你好 🔐');
  await page.locator('#input').fill('YQ==\n');
  await page.getByRole('button', { name: '解码', exact: true }).click();
  await expect(page.locator('#status')).toContainText('Base64 格式无效');
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.screenshot({ path: '../output/playwright/web-mobile-dark.png', fullPage: true, animations: 'disabled' });
  await page.setViewportSize({ width: 1280, height: 900 });
  await page.emulateMedia({ colorScheme: 'light' });
  await page.getByRole('button', { name: '加密 / 解密', exact: true }).click();
  await page.screenshot({ path: '../output/playwright/web-desktop-light.png', fullPage: true, animations: 'disabled' });
});

test('appearance follows system or explicit choice without changing drafts or using storage', async ({ page }) => {
  await page.emulateMedia({ colorScheme: 'dark', reducedMotion: 'reduce' });
  await page.goto('./');
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark');
  await page.locator('#input').fill('主题切换保留文本 🔐');
  await page.locator('#password').fill('synthetic-test-password');
  await page.getByLabel('外观', { exact: true }).selectOption('light');
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'light');
  await page.emulateMedia({ colorScheme: 'dark' });
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'light');
  await page.getByLabel('外观', { exact: true }).selectOption('auto');
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark');
  await page.emulateMedia({ colorScheme: 'light' });
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'light');
  await expect(page.locator('#input')).toHaveValue('主题切换保留文本 🔐');
  await expect(page.locator('#password')).toHaveValue('synthetic-test-password');
  await page.setViewportSize({ width: 320, height: 740 });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  expect(await page.evaluate(() => [localStorage.length, sessionStorage.length])).toEqual([0, 0]);
});
