import './style.css';

const appearance = document.getElementById('appearance') as HTMLSelectElement;
const systemTheme = matchMedia('(prefers-color-scheme: dark)');
function applyAppearance() {
  document.documentElement.dataset.theme = appearance.value === 'auto'
    ? (systemTheme.matches ? 'dark' : 'light') : appearance.value;
}
appearance.addEventListener('change', applyAppearance);
systemTheme.addEventListener('change', applyAppearance);
applyAppearance();

const get = <T extends HTMLElement>(id: string) => document.getElementById(id) as T;
const input = get<HTMLTextAreaElement>('input');
const output = get<HTMLTextAreaElement>('output');
const password = get<HTMLInputElement>('password');
const status = get('status');
let mode: 'crypto' | 'base64' = 'crypto';
let worker: Worker | undefined;
const button = (id: string) => get<HTMLButtonElement>(id);

function message(text: string, error = false) { status.textContent = text; status.classList.toggle('error', error); }
function busy(value: boolean) {
  for (const id of ['crypto-tab', 'base64-tab', 'forward', 'reverse', 'swap', 'copy', 'clear']) button(id).disabled = value;
  input.disabled = value; password.disabled = value;
  button('cancel').hidden = !value;
  get('status').setAttribute('aria-busy', String(value));
}
function stop() { worker?.terminate(); worker = undefined; busy(false); }
function select(next: typeof mode) {
  mode = next; input.value = ''; output.value = ''; password.value = '';
  password.type = 'password'; button('show-password').textContent = '显示密码'; button('show-password').setAttribute('aria-pressed', 'false');
  get('password-row').hidden = mode === 'base64';
  button('crypto-tab').setAttribute('aria-pressed', String(mode === 'crypto'));
  button('base64-tab').setAttribute('aria-pressed', String(mode === 'base64'));
  button('forward').textContent = mode === 'crypto' ? '加密' : '编码';
  button('reverse').textContent = mode === 'crypto' ? '解密' : '解码';
  get('workspace-kicker').textContent = mode === 'crypto' ? 'TEXT ENCRYPTION' : 'TEXT ENCODING';
  get('workspace-title').textContent = mode === 'crypto' ? '为文字加一把锁' : '换一种方式表达文字';
  get('hint').textContent = mode === 'crypto' ? '兼容 Windows 版 AGV1 文本协议。请妥善保存密码，密码无法找回。' : 'Base64 不是加密。严格模式：不接受空白、非标准字符或缺失填充；解码结果必须为 UTF-8 文本。';
  input.placeholder = mode === 'crypto' ? '输入任意 UTF-8 文本，或粘贴 AGV1. 密文' : '输入 UTF-8 文本或严格 Base64 文本';
  message('已切换工作区并清空文本。');
}
function run(reverse: boolean) {
  if (worker) return;
  output.value = '';
  if (mode === 'crypto' && !password.value) { message('请输入密码。', true); password.focus(); return; }
  if (!globalThis.isSecureContext || !globalThis.crypto?.subtle) { message('此浏览器需要 HTTPS 或 localhost 安全环境及 Web Crypto 支持。', true); return; }
  busy(true); message('正在本地处理，请稍候…');
  try {
    worker = new Worker(new URL('./worker.ts', import.meta.url), { type: 'module' });
    worker.onmessage = ({ data }: MessageEvent<{ output?: string; error?: string }>) => {
      stop();
      if (data.error) message(data.error, true);
      else { output.value = data.output ?? ''; message('完成。结果仅保留在当前页面。'); }
    };
    worker.onerror = event => { event.preventDefault(); stop(); message('本地处理失败，浏览器可能不支持或可用内存不足。', true); };
    worker.postMessage({ action: mode === 'crypto' ? (reverse ? 'decrypt' : 'encrypt') : (reverse ? 'decode' : 'encode'), input: input.value, password: password.value });
  } catch { stop(); message('无法启动本地 Worker，请检查浏览器支持。', true); }
}
button('crypto-tab').onclick = () => select('crypto');
button('base64-tab').onclick = () => select('base64');
button('forward').onclick = () => run(false);
button('reverse').onclick = () => run(true);
button('cancel').onclick = () => { stop(); message('已取消。'); };
button('show-password').onclick = () => {
  const show = password.type === 'password'; password.type = show ? 'text' : 'password';
  button('show-password').textContent = show ? '隐藏密码' : '显示密码'; button('show-password').setAttribute('aria-pressed', String(show));
};
button('swap').onclick = () => { [input.value, output.value] = [output.value, input.value]; message('已交换输入与结果。'); };
button('copy').onclick = async () => {
  try { await navigator.clipboard.writeText(output.value); message('已复制结果到剪贴板。'); }
  catch { output.focus(); output.select(); message('浏览器未允许复制，请手动复制选中的结果。', true); }
};
button('clear').onclick = () => { select(mode); message('已清空密码、输入与结果。'); input.focus(); };
window.addEventListener('pagehide', () => { stop(); input.value = ''; output.value = ''; password.value = ''; });
