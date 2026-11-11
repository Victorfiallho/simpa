"""Criptografia dos pacotes de backup: AES-256-GCM em blocos, com detecção de truncamento.

Por que em blocos: um pacote pode passar de centenas de MB, e o AES-GCM comum cifra tudo de uma vez
na memória. Aqui o arquivo é cifrado em blocos de 1 MiB (construção "STREAM"):

- cada bloco tem o próprio nonce: 4 bytes aleatórios do arquivo + um contador de 8 bytes, então a
  ordem dos blocos não pode ser trocada nem um bloco repetido;
- o bloco final é marcado nos dados autenticados (AAD): cortar o arquivo no fim de um bloco, ou
  acrescentar lixo, faz a verificação falhar em vez de devolver um backup incompleto.

Formato: b"SIMPABK1" + prefixo do nonce (4 bytes) + blocos [tamanho (4 bytes) + texto cifrado].

A chave tem 32 bytes aleatórios, em base64, num arquivo com permissão 0600. Ela nunca é passada na
linha de comando (o histórico do shell e `ps` a mostrariam).
"""

from __future__ import annotations

import base64
import hashlib
import os
import secrets
import struct
from pathlib import Path

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

MAGIA = b"SIMPABK1"
TAMANHO_DO_BLOCO = 1024 * 1024
TAMANHO_DA_CHAVE = 32
LIMITE_DO_BLOCO_CIFRADO = TAMANHO_DO_BLOCO + 16  # texto + etiqueta de autenticação do GCM


class CriptografiaError(Exception):
    """Chave incorreta, arquivo corrompido, truncado ou que não é um pacote de backup."""


def gerar_chave(caminho: Path) -> None:
    """Cria um arquivo de chave novo (0600). Recusa sobrescrever uma chave existente."""
    descritor = os.open(caminho, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descritor, "wb") as arquivo:
        arquivo.write(base64.b64encode(secrets.token_bytes(TAMANHO_DA_CHAVE)) + b"\n")


def ler_chave(caminho: Path) -> bytes:
    try:
        chave = base64.b64decode(caminho.read_bytes().strip(), validate=True)
    except (OSError, ValueError) as erro:
        raise CriptografiaError(f"não foi possível ler a chave em {caminho}: {erro}") from erro
    if len(chave) != TAMANHO_DA_CHAVE:
        raise CriptografiaError("a chave deve ter 32 bytes (AES-256)")
    return chave


def _nonce(prefixo: bytes, contador: int) -> bytes:
    return prefixo + struct.pack(">Q", contador)


def _aad(final: bool) -> bytes:
    return MAGIA + (b"\x01" if final else b"\x00")


def cifrar_arquivo(chave: bytes, origem: Path, destino: Path) -> None:
    """Cifra `origem` em `destino`. `destino` não pode existir."""
    aes = AESGCM(chave)
    prefixo = secrets.token_bytes(4)
    with origem.open("rb") as entrada, destino.open("xb") as saida:
        saida.write(MAGIA + prefixo)
        contador = 0
        atual = entrada.read(TAMANHO_DO_BLOCO)
        while True:
            proximo = entrada.read(TAMANHO_DO_BLOCO)
            final = not proximo
            cifrado = aes.encrypt(_nonce(prefixo, contador), atual, _aad(final))
            saida.write(struct.pack(">I", len(cifrado)) + cifrado)
            if final:
                return
            atual, contador = proximo, contador + 1


def decifrar_arquivo(chave: bytes, origem: Path, destino: Path) -> None:
    """Decifra `origem` em `destino` (que não pode existir); não deixa saída parcial se falhar."""
    aes = AESGCM(chave)
    try:
        with origem.open("rb") as entrada, destino.open("xb") as saida:
            cabecalho = entrada.read(len(MAGIA) + 4)
            if len(cabecalho) != len(MAGIA) + 4 or cabecalho[: len(MAGIA)] != MAGIA:
                raise CriptografiaError("o arquivo não é um pacote de backup do SIMPA")
            prefixo = cabecalho[len(MAGIA) :]
            contador = 0
            while True:
                tamanho_bruto = entrada.read(4)
                if len(tamanho_bruto) != 4:
                    raise CriptografiaError("pacote truncado: faltam blocos")
                (tamanho,) = struct.unpack(">I", tamanho_bruto)
                if not 16 <= tamanho <= LIMITE_DO_BLOCO_CIFRADO:
                    raise CriptografiaError("pacote corrompido: tamanho de bloco inválido")
                cifrado = entrada.read(tamanho)
                if len(cifrado) != tamanho:
                    raise CriptografiaError("pacote truncado: bloco incompleto")
                final = not entrada.peek(1)  # nada depois deste bloco: é o último
                try:
                    saida.write(aes.decrypt(_nonce(prefixo, contador), cifrado, _aad(final)))
                except InvalidTag as erro:
                    raise CriptografiaError(
                        "chave incorreta, ou pacote corrompido, truncado ou alterado"
                    ) from erro
                if final:
                    return
                contador += 1
    except BaseException:
        destino.unlink(missing_ok=True)
        raise


def sha256_do_arquivo(caminho: Path) -> str:
    resumo = hashlib.sha256()
    with caminho.open("rb") as arquivo:
        for bloco in iter(lambda: arquivo.read(TAMANHO_DO_BLOCO), b""):
            resumo.update(bloco)
    return resumo.hexdigest()
