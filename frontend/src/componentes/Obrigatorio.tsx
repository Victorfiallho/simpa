// Indicação visível de campo obrigatório (RNF11). Quem usa leitor de tela já ouve o "obrigatório"
// pelo atributo `required` do campo, por isso o asterisco fica escondido da árvore de acessibilidade.

/** Rótulo do campo, com o asterisco quando ele é obrigatório. */
export function Rotulo({ texto, obrigatorio = false }: { texto: string; obrigatorio?: boolean }) {
  return (
    <span>
      {texto}
      {obrigatorio && (
        <span className="obrigatorio" aria-hidden="true">
          {' *'}
        </span>
      )}
    </span>
  );
}

/** Legenda do asterisco, no topo de um formulário que tem campos obrigatórios. */
export function LegendaObrigatorios() {
  return (
    <p className="legenda-obrigatorios">
      Campos com <span className="obrigatorio">*</span> são obrigatórios.
    </p>
  );
}
