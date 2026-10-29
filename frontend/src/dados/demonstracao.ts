// Base de demonstração: dados 100% sintéticos (RNF04), gerados de forma determinística
// para a tela ficar igual em toda execução. Substituída pela API quando ela existir.

import type { Aluno, BaseAcademica, Disciplina, Inscricao } from './tipos';

const NOMES = [
  'Ana Beatriz Lima', 'Bruno Henrique Costa', 'Camila Rodrigues', 'Daniel Oliveira',
  'Eduarda Martins', 'Felipe Almeida', 'Gabriela Santos', 'Henrique Souza',
  'Isabela Ferreira', 'João Pedro Silva', 'Karina Mendes', 'Lucas Ribeiro',
  'Mariana Barbosa', 'Nicolas Araújo', 'Olívia Cardoso', 'Paulo Vitor Dias',
  'Rafaela Nunes', 'Samuel Rocha', 'Talita Fernandes', 'Vinícius Pereira',
  'Alice Monteiro', 'Bernardo Melo', 'Clara Azevedo', 'Davi Teixeira',
  'Elisa Carvalho', 'Francisco Moura', 'Giovana Castro', 'Heitor Freitas',
  'Íris Andrade', 'Júlia Batista', 'Leonardo Cunha', 'Manuela Ramos',
  'Otávio Lopes', 'Pedro Rezende', 'Sofia Duarte', 'Thiago Vieira',
];

const DISCIPLINAS: Disciplina[] = [
  { id: 1, nome: 'Estatística Aplicada', sigla: 'EST' },
  { id: 2, nome: 'Programação Orientada a Objetos', sigla: 'POO' },
  { id: 3, nome: 'Álgebra Linear', sigla: 'ALG' },
];

// Quanto cada disciplina desloca o desempenho médio (Álgebra Linear é a mais difícil).
const DIFICULDADE: Record<number, number> = { 1: 0, 2: 0.25, 3: -0.4 };

const SEMANAS = 16;
const AULAS_POR_SEMANA = 4;

/** Gerador pseudoaleatório com semente fixa (mulberry32). */
function criarAleatorio(semente: number): () => number {
  let estado = semente;
  return () => {
    estado = (estado + 0x6d2b79f5) | 0;
    let t = Math.imul(estado ^ (estado >>> 15), 1 | estado);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

export function gerarBaseDemonstracao(semente = 2026): BaseAcademica {
  const aleatorio = criarAleatorio(semente);
  const normal = (media: number, desvio: number) =>
    media +
    desvio * Math.sqrt(-2 * Math.log(1 - aleatorio())) * Math.cos(2 * Math.PI * aleatorio());
  const limitar = (valor: number, min: number, max: number) =>
    Math.min(max, Math.max(min, valor));
  // Notas lançadas com uma casa decimal, guardadas em centésimos.
  const nota = (valor: number) => limitar(Math.round(valor * 10) * 10, 0, 1000);

  const alunos: Aluno[] = NOMES.map((nome, i) => ({
    id: i + 1,
    nome,
    matricula: `2026${String(i + 1).padStart(4, '0')}`,
    turma: i < 18 ? 'A' : 'B',
  }));

  const inscricoes: Inscricao[] = [];
  for (const aluno of alunos) {
    const habilidade = normal(7.4, 1.0);
    const assiduidade = limitar(normal(0.9, 0.055), 0.62, 1);

    for (const disciplina of DISCIPLINAS) {
      const nivel = habilidade + DIFICULDADE[disciplina.id] + normal(0, 0.45);
      const frequencias = Array.from({ length: SEMANAS }, (_, i) => {
        // Leve queda de presença no fim do semestre.
        const chance = limitar(assiduidade + normal(0, 0.04) - (i >= 12 ? 0.03 : 0), 0, 1);
        let faltas = 0;
        for (let aula = 0; aula < AULAS_POR_SEMANA; aula++) {
          if (aleatorio() > chance) faltas++;
        }
        return { semana: i + 1, aulas: AULAS_POR_SEMANA, faltas };
      });

      inscricoes.push({
        id: inscricoes.length + 1,
        alunoId: aluno.id,
        disciplinaId: disciplina.id,
        avaliacoes: [
          { periodo: 'N1', nota: nota(nivel + normal(-0.1, 0.6)), peso: 4 },
          { periodo: 'N2', nota: nota(nivel + normal(0.15, 0.6)), peso: 6 },
        ],
        frequencias,
      });
    }
  }

  // Casos sem dados suficientes, para exercitar o status Indeterminado (D09).
  inscricoes[3 * 17 + 2].avaliacoes = [];
  inscricoes[3 * 35 + 1].frequencias = [];

  return { periodoLetivo: '2026.2', semanas: SEMANAS, alunos, disciplinas: DISCIPLINAS, inscricoes };
}
