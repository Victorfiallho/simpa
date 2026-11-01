import { useEffect, useRef, useState } from 'react';

import { api, buscarImagem } from '../api/cliente';
import type { Perfil, Resposta } from '../api/tipos';

const LADO = 256; // a foto é recortada em quadrado e reduzida antes de enviar (limite de 1 MB)
const TIPOS = ['image/jpeg', 'image/png', 'image/webp'];

/** Recorta o centro da imagem em quadrado e devolve um JPEG de LADO x LADO. */
async function reduzir(arquivo: File): Promise<Blob> {
  const bitmap = await createImageBitmap(arquivo);
  const lado = Math.min(bitmap.width, bitmap.height);
  const tela = document.createElement('canvas');
  tela.width = tela.height = LADO;
  tela
    .getContext('2d')!
    .drawImage(
      bitmap,
      (bitmap.width - lado) / 2,
      (bitmap.height - lado) / 2,
      lado,
      lado,
      0,
      0,
      LADO,
      LADO,
    );
  bitmap.close();
  return new Promise((resolver, rejeitar) =>
    tela.toBlob((b) => (b ? resolver(b) : rejeitar(new Error('Não foi possível ler a imagem.'))), 'image/jpeg', 0.85),
  );
}

/** Mostra a foto do usuário logado e permite trocar ou remover. */
export function FotoDePerfil({ perfil, aoMudar }: { perfil: Perfil; aoMudar: () => void }) {
  const [url, setUrl] = useState<string | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [ocupado, setOcupado] = useState(false);
  const [versao, setVersao] = useState(0);
  const entrada = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!perfil.tem_foto) {
      setUrl(null);
      return;
    }
    let ativo = true;
    let criada: string | null = null;
    buscarImagem('/auth/me/foto')
      .then((blob) => {
        criada = URL.createObjectURL(blob);
        if (ativo) setUrl(criada);
        else URL.revokeObjectURL(criada);
      })
      .catch(() => ativo && setUrl(null));
    return () => {
      ativo = false;
      if (criada) URL.revokeObjectURL(criada);
    };
  }, [perfil.tem_foto, versao]);

  async function escolher(arquivo: File | undefined) {
    if (!arquivo) return;
    setErro(null);
    if (!TIPOS.includes(arquivo.type)) {
      setErro('Use uma imagem JPG, PNG ou WebP.');
      return;
    }
    setOcupado(true);
    try {
      const imagem = await reduzir(arquivo);
      await api<Resposta<Perfil>>('/auth/me/foto', {
        method: 'PUT',
        headers: { 'Content-Type': 'image/jpeg' },
        body: imagem,
      });
      setVersao((v) => v + 1);
      aoMudar();
    } catch (e) {
      setErro((e as Error).message);
    } finally {
      setOcupado(false);
      if (entrada.current) entrada.current.value = '';
    }
  }

  async function remover() {
    setErro(null);
    setOcupado(true);
    try {
      await api('/auth/me/foto', { method: 'DELETE' });
      aoMudar();
    } catch (e) {
      setErro((e as Error).message);
    } finally {
      setOcupado(false);
    }
  }

  return (
    <div className="foto-perfil">
      {url ? (
        <img src={url} alt="Sua foto de perfil" width={96} height={96} />
      ) : (
        <span className="foto-vazia" aria-hidden="true">
          {perfil.nome_usuario.slice(0, 2).toUpperCase()}
        </span>
      )}
      <div>
        <input
          ref={entrada}
          type="file"
          accept={TIPOS.join(',')}
          hidden
          onChange={(e) => escolher(e.target.files?.[0])}
        />
        <button type="button" className="botao-texto" disabled={ocupado} onClick={() => entrada.current?.click()}>
          {perfil.tem_foto ? 'Trocar foto' : 'Enviar foto'}
        </button>
        {perfil.tem_foto && (
          <button type="button" className="botao-texto" disabled={ocupado} onClick={remover}>
            Remover
          </button>
        )}
        {erro && (
          <p className="erro-campo" role="alert">
            {erro}
          </p>
        )}
      </div>
    </div>
  );
}
