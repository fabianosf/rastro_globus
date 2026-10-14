import { BrowserMultiFormatReader } from "@zxing/browser";

export type GlobusNfGarantia = {
  numero?: string;
  serie?: string;
  data_emissao?: string;
  valor?: string | number;
  fornecedor_nome?: string;
  peca_codigo?: string;
  peca_descricao?: string;
  codigo_fornecedor?: string | number;
};

export type ConsultaChaveNfe = {
  chave: string;
  nf_remessa_numero: string;
  nf_remessa_serie: string;
  nf_remessa_data: string;
  cnpj_emitente?: string;
  globus: {
    count: number;
    results: GlobusNfGarantia[];
    ok: boolean;
    detail?: string;
  };
};

export function soDigitos(valor: string) {
  return (valor || "").replace(/\D/g, "");
}

/** Tenta ler a chave NFe (44 dígitos) do código de barras da foto. */
export async function lerChaveDaImagem(file: File): Promise<string | null> {
  const native = await lerChaveBarcodeDetector(file);
  if (native) return native;

  const url = URL.createObjectURL(file);
  try {
    const reader = new BrowserMultiFormatReader();
    const result = await reader.decodeFromImageUrl(url);
    return normalizarChave(result.getText());
  } catch {
    return null;
  } finally {
    URL.revokeObjectURL(url);
  }
}

async function lerChaveBarcodeDetector(file: File): Promise<string | null> {
  const BD = (window as unknown as { BarcodeDetector?: new (opts?: { formats: string[] }) => {
    detect: (source: ImageBitmapSource) => Promise<Array<{ rawValue: string }>>;
  } }).BarcodeDetector;
  if (!BD) return null;
  try {
    const detector = new BD({
      formats: ["code_128", "ean_13", "ean_8", "code_39", "itf", "qr_code"],
    });
    const bitmap = await createImageBitmap(file);
    try {
      const codes = await detector.detect(bitmap);
      for (const c of codes) {
        const chave = normalizarChave(c.rawValue);
        if (chave) return chave;
      }
    } finally {
      bitmap.close();
    }
  } catch {
    return null;
  }
  return null;
}

function normalizarChave(raw: string): string | null {
  const digits = soDigitos(raw);
  if (digits.length === 44) return digits;
  // alguns leitores devolvem texto com prefixo; pega sequência de 44
  const m = digits.match(/\d{44}/);
  return m ? m[0] : null;
}
