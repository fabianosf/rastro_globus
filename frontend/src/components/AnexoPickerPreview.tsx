import { useEffect, useMemo, useRef, useState } from "react";
import { FileIcon, FileTextIcon, ImageIcon } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

const DEFAULT_ACCEPT =
  "image/*,.pdf,.doc,.docx,application/pdf,application/msword,application/vnd.openxmlformats-officedocument.wordprocessingml.document";

type Props = {
  files: File[];
  onChange: (files: File[]) => void;
  multiple?: boolean;
  accept?: string;
  label?: string;
  hint?: string;
};

function isImage(file: File) {
  return file.type.startsWith("image/") || /\.(jpe?g|png|gif|webp|bmp)$/i.test(file.name);
}

function isPdf(file: File) {
  return file.type === "application/pdf" || /\.pdf$/i.test(file.name);
}

function fileKind(file: File): "image" | "pdf" | "other" {
  if (isImage(file)) return "image";
  if (isPdf(file)) return "pdf";
  return "other";
}

function sizeLabel(bytes: number) {
  return `${Math.max(1, Math.round(bytes / 1024))} KB`;
}

function KindIcon({ kind }: { kind: "image" | "pdf" | "other" }) {
  if (kind === "image") return <ImageIcon className="size-5 shrink-0 text-cyan" />;
  if (kind === "pdf") return <FileTextIcon className="size-5 shrink-0 text-amber" />;
  return <FileIcon className="size-5 shrink-0 text-muted" />;
}

function PreviewBody({ file, url, large }: { file: File; url: string; large?: boolean }) {
  const kind = fileKind(file);
  if (kind === "image") {
    return (
      <img
        src={url}
        alt={file.name}
        className={
          large
            ? "mx-auto max-h-[70vh] w-auto max-w-full rounded-lg object-contain"
            : "max-h-48 w-full rounded-lg object-contain bg-bg"
        }
      />
    );
  }
  if (kind === "pdf") {
    return (
      <iframe
        title={file.name}
        src={url}
        className={
          large
            ? "h-[70vh] w-full rounded-lg border border-line bg-bg"
            : "h-56 w-full rounded-lg border border-line bg-bg"
        }
      />
    );
  }
  return (
    <div className="flex flex-col items-center justify-center gap-2 rounded-lg border border-dashed border-line bg-bg/60 px-4 py-8 text-center text-sm text-muted">
      <KindIcon kind="other" />
      <p>Pré-visualização não disponível neste tipo de arquivo.</p>
      <p className="text-xs">Use Abrir para conferir no programa do computador.</p>
    </div>
  );
}

export default function AnexoPickerPreview({
  files,
  onChange,
  multiple = true,
  accept = DEFAULT_ACCEPT,
  label = "Anexos",
  hint = "Confira o arquivo. Pode trocar ou remover antes de salvar.",
}: Props) {
  const addRef = useRef<HTMLInputElement>(null);
  const replaceRef = useRef<HTMLInputElement>(null);
  const [replaceIndex, setReplaceIndex] = useState<number | null>(null);
  const [viewIndex, setViewIndex] = useState<number | null>(null);

  const urls = useMemo(() => files.map((f) => URL.createObjectURL(f)), [files]);

  useEffect(() => {
    return () => {
      urls.forEach((u) => URL.revokeObjectURL(u));
    };
  }, [urls]);

  function fileKey(f: File) {
    return `${f.name}:${f.size}:${f.lastModified}`;
  }

  function onPickAdd(list: FileList | null) {
    const picked = Array.from(list || []);
    if (!picked.length) return;
    if (!multiple) {
      onChange(picked.slice(0, 1));
      return;
    }
    const existing = new Set(files.map(fileKey));
    const novos = picked.filter((f) => !existing.has(fileKey(f)));
    onChange([...files, ...novos]);
  }

  function onPickReplace(list: FileList | null) {
    const picked = list?.[0];
    if (!picked || replaceIndex === null) return;
    const next = [...files];
    next[replaceIndex] = picked;
    onChange(next);
    setReplaceIndex(null);
  }

  function openInTab(url: string) {
    window.open(url, "_blank", "noopener,noreferrer");
  }

  const viewFile = viewIndex !== null ? files[viewIndex] : null;
  const viewUrl = viewIndex !== null ? urls[viewIndex] : null;

  return (
    <div className="space-y-2">
      <div>
        <span className="mb-1 block text-sm font-medium text-muted">{label}</span>
        <input
          ref={addRef}
          type="file"
          multiple={multiple}
          accept={accept}
          className="block w-full text-sm text-muted file:mr-3 file:rounded-lg file:border-0 file:bg-cyan/20 file:px-3 file:py-1.5 file:text-sm file:font-semibold file:text-cyan"
          onChange={(e) => {
            onPickAdd(e.target.files);
            e.target.value = "";
          }}
        />
        <p className="mt-1 text-xs text-muted">{hint}</p>
      </div>

      <input
        ref={replaceRef}
        type="file"
        accept={accept}
        className="hidden"
        onChange={(e) => {
          onPickReplace(e.target.files);
          e.target.value = "";
        }}
      />

      {files.length ? (
        <ul className="space-y-3">
          {files.map((f, idx) => {
            const kind = fileKind(f);
            const url = urls[idx];
            return (
              <li
                key={`${fileKey(f)}-${idx}`}
                className="overflow-hidden rounded-xl border border-line bg-bg/40"
              >
                <div className="flex items-start gap-2 border-b border-line px-3 py-2">
                  <KindIcon kind={kind} />
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium text-ink">{f.name}</p>
                    <p className="text-xs text-muted">
                      {sizeLabel(f.size)}
                      {f.type ? ` · ${f.type}` : ""}
                    </p>
                  </div>
                </div>
                <div className="p-2">
                  <PreviewBody file={f} url={url} />
                </div>
                <div className="flex flex-wrap gap-2 border-t border-line px-3 py-2">
                  <Button
                    type="button"
                    size="sm"
                    variant="outline"
                    onClick={() => setViewIndex(idx)}
                  >
                    Ver
                  </Button>
                  <Button
                    type="button"
                    size="sm"
                    variant="outline"
                    onClick={() => openInTab(url)}
                  >
                    Abrir
                  </Button>
                  <Button
                    type="button"
                    size="sm"
                    variant="secondary"
                    onClick={() => {
                      setReplaceIndex(idx);
                      replaceRef.current?.click();
                    }}
                  >
                    Trocar
                  </Button>
                  <Button
                    type="button"
                    size="sm"
                    variant="destructive"
                    onClick={() => onChange(files.filter((_, i) => i !== idx))}
                  >
                    Remover
                  </Button>
                </div>
              </li>
            );
          })}
        </ul>
      ) : null}

      <Dialog
        open={viewIndex !== null}
        onOpenChange={(open) => {
          if (!open) setViewIndex(null);
        }}
      >
        <DialogContent className="max-w-[min(96vw,56rem)]" showCloseButton>
          <DialogHeader>
            <DialogTitle className="truncate pr-8">{viewFile?.name || "Anexo"}</DialogTitle>
            <DialogDescription>
              Confira antes de enviar. Feche e use Trocar se precisar de outro arquivo.
            </DialogDescription>
          </DialogHeader>
          {viewFile && viewUrl ? <PreviewBody file={viewFile} url={viewUrl} large /> : null}
        </DialogContent>
      </Dialog>
    </div>
  );
}
