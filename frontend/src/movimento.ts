// Sistema de movimento do SIMPA. Movimento discreto e com função: mostrar de onde algo veio,
// para onde foi e o que mudou, nunca só enfeite. As mesmas durações e curvas valem para o CSS
// (variáveis --mov-* em global.css) e para os componentes animados aqui.
//
// Quem pede menos movimento no sistema (prefers-reduced-motion) vê tudo no estado final, sem
// animação. Os testes de navegador rodam assim (playwright.config.ts).

import { type Transition, useReducedMotion } from 'motion/react';
import { useEffect, useRef, useState } from 'react';

/** Curva de saída suave (ease-out-quint): rápida no começo, assenta devagar. */
export const CURVA_SAIDA = [0.22, 1, 0.36, 1] as const;

export const DURACAO = {
  rapida: 0.14,
  media: 0.24,
  lenta: 0.42,
  numeros: 0.9,
} as const;

/**
 * Atraso de partida do que entra junto com os dados: a primeira renderização das telas (com os
 * gráficos) ocupa o navegador por uns 100 ms, e o começo da animação se perderia nesse tempo.
 */
export const ATRASO_DE_PARTIDA = 0.1;

/** A mesma curva de CURVA_SAIDA (ease-out-quint), para o que é animado à mão. */
function saidaQuinta(t: number): number {
  return 1 - (1 - t) ** 5;
}

/** Mola das superfícies que entram e saem (gaveta, indicador do menu): firme, sem quicar. */
export const MOLA: Transition = { type: 'spring', stiffness: 420, damping: 40, mass: 0.9 };

const SEM_MOVIMENTO: Transition = { duration: 0 };

/** Entrada e saída das gavetas laterais: o fundo esmaece e o painel desliza da direita. */
export function useGavetaAnimada() {
  const reduzido = useReducedMotion();
  return {
    fundo: {
      initial: { opacity: 0 },
      animate: { opacity: 1 },
      exit: { opacity: 0 },
      transition: reduzido ? SEM_MOVIMENTO : { duration: DURACAO.media, ease: CURVA_SAIDA },
    },
    painel: {
      initial: { x: reduzido ? 0 : 56, opacity: reduzido ? 1 : 0 },
      animate: { x: 0, opacity: 1 },
      exit: { x: reduzido ? 0 : 56, opacity: reduzido ? 1 : 0 },
      transition: reduzido ? SEM_MOVIMENTO : MOLA,
    },
  };
}

/** Entrada de uma tela nova: sobe alguns pixels e aparece. Sem saída, para a navegação ser imediata. */
export function useEntradaDePagina() {
  const reduzido = useReducedMotion();
  return {
    initial: reduzido ? false : ({ opacity: 0, y: 8 } as const),
    animate: { opacity: 1, y: 0 },
    transition: { duration: DURACAO.lenta, ease: CURVA_SAIDA },
  };
}

/**
 * Número que conta do valor anterior até o novo (do zero, na primeira vez). Devolve o valor do
 * quadro atual; quem chama formata. Com movimento reduzido, devolve o valor final direto.
 */
export function useNumeroAnimado(valor: number | null): number | null {
  const reduzido = useReducedMotion();
  const [atual, setAtual] = useState<number | null>(reduzido ? valor : valor === null ? null : 0);
  // O valor que está na tela agora. Uma mudança no meio da contagem continua daqui, sem saltar.
  const exibido = useRef(0);

  useEffect(() => {
    if (valor === null) {
      setAtual(null);
      return;
    }
    if (reduzido) {
      setAtual(valor);
      exibido.current = valor;
      return;
    }
    // Laço próprio com requestAnimationFrame: contar um número não precisa do motor do motion.
    const de = exibido.current;
    const inicio = performance.now() + ATRASO_DE_PARTIDA * 1000;
    let quadro = requestAnimationFrame(function passo(agora) {
      const t = Math.min(1, Math.max(0, (agora - inicio) / (DURACAO.numeros * 1000)));
      const v = de + (valor - de) * saidaQuinta(t);
      exibido.current = v;
      setAtual(v);
      if (t < 1) quadro = requestAnimationFrame(passo);
    });
    return () => cancelAnimationFrame(quadro);
  }, [valor, reduzido]);

  return atual;
}

/** Animação de entrada dos gráficos do Recharts, no mesmo ritmo do resto da interface. */
export function useAnimacaoDosGraficos() {
  const reduzido = useReducedMotion();
  return {
    isAnimationActive: !reduzido,
    animationDuration: 700,
    animationEasing: 'ease-out' as const,
  };
}
