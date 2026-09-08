import { decryptText, encryptText } from './agv1';
import { decodeBase64, encodeBase64 } from './encoding';

self.onmessage = async ({ data }: MessageEvent<{ action: string; input: string; password: string }>) => {
  try {
    const { action, input, password } = data;
    const output = action === 'encrypt' ? await encryptText(input, password)
      : action === 'decrypt' ? await decryptText(input, password)
      : action === 'encode' ? encodeBase64(input)
      : action === 'decode' ? decodeBase64(input) : (() => { throw new Error('未知操作。'); })();
    self.postMessage({ output });
  } catch (error) {
    self.postMessage({ error: error instanceof Error ? error.message : '操作失败，请检查输入或设备可用内存。' });
  }
};
