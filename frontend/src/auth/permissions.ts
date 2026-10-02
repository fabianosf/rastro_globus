/** Espelha a matriz de perfis do backend (spec §2.9). */

export type Perfil = "oficina" | "compras" | "manutencao" | "direcao" | "admin" | string;

export function canCreateGarantia(perfil?: string | null): boolean {
  return ["oficina", "manutencao", "admin"].includes(perfil || "");
}

export function canEditGarantia(perfil?: string | null): boolean {
  return ["oficina", "compras", "manutencao", "admin"].includes(perfil || "");
}

/** Excluir de verdade: abertos para quem edita; admin também pode apagar fechados. */
export function canDeleteGarantia(perfil?: string | null, status?: string | null): boolean {
  if (!canEditGarantia(perfil)) return false;
  if (perfil === "admin") return Boolean(status);
  return ["aberta", "enviada", "em_analise"].includes(status || "");
}

export function canAnexar(perfil?: string | null): boolean {
  return ["oficina", "compras", "manutencao", "admin"].includes(perfil || "");
}

export function canVincularNf(perfil?: string | null): boolean {
  return ["compras", "admin"].includes(perfil || "");
}

/** Avanço intermediário: enviada, em_analise, cancelada (de aberta/enviada). */
export function canAdvanceStatus(perfil?: string | null): boolean {
  return ["compras", "manutencao", "admin"].includes(perfil || "");
}

/** Fechamento: procedente, improcedente, cortesia. */
export function canCloseStatus(perfil?: string | null): boolean {
  return ["manutencao", "admin"].includes(perfil || "");
}

export function canCancel(perfil?: string | null, statusAtual?: string): boolean {
  if (!perfil || perfil === "direcao") return false;
  if (perfil === "admin") return true;
  if (!canAdvanceStatus(perfil)) return false;
  return statusAtual === "aberta" || statusAtual === "enviada";
}

export function canManageRegrasPrazo(perfil?: string | null): boolean {
  return ["manutencao", "admin"].includes(perfil || "");
}
