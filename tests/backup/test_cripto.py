"""Testes da criptografia dos pacotes de backup (scripts/backup/cripto.py)."""

import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "backup"))

import cripto  # noqa: E402


@pytest.fixture
def chave() -> bytes:
    return os.urandom(32)


def _cifrar(tmp_path: Path, chave: bytes, conteudo: bytes) -> Path:
    origem = tmp_path / "origem.bin"
    origem.write_bytes(conteudo)
    pacote = tmp_path / "pacote.enc"
    cripto.cifrar_arquivo(chave, origem, pacote)
    return pacote


@pytest.mark.parametrize(
    "tamanho",
    [0, 1, cripto.TAMANHO_DO_BLOCO, cripto.TAMANHO_DO_BLOCO + 1, 3 * cripto.TAMANHO_DO_BLOCO],
)
def test_ida_e_volta(tmp_path, chave, tamanho):
    conteudo = os.urandom(tamanho)
    pacote = _cifrar(tmp_path, chave, conteudo)
    saida = tmp_path / "saida.bin"
    cripto.decifrar_arquivo(chave, pacote, saida)
    assert saida.read_bytes() == conteudo


def test_chave_errada_e_recusada_sem_deixar_saida(tmp_path, chave):
    pacote = _cifrar(tmp_path, chave, b"dados")
    saida = tmp_path / "saida.bin"
    with pytest.raises(cripto.CriptografiaError):
        cripto.decifrar_arquivo(os.urandom(32), pacote, saida)
    assert not saida.exists()


def test_byte_alterado_e_detectado(tmp_path, chave):
    pacote = _cifrar(tmp_path, chave, os.urandom(5000))
    dados = bytearray(pacote.read_bytes())
    dados[len(dados) // 2] ^= 0x01
    pacote.write_bytes(bytes(dados))
    with pytest.raises(cripto.CriptografiaError):
        cripto.decifrar_arquivo(chave, pacote, tmp_path / "saida.bin")


def test_truncar_no_limite_de_um_bloco_e_detectado(tmp_path, chave):
    pacote = _cifrar(tmp_path, chave, os.urandom(2 * cripto.TAMANHO_DO_BLOCO + 10))
    dados = pacote.read_bytes()
    # Mantém só o cabeçalho e o primeiro bloco inteiro: parece um arquivo válido, mas falta o fim.
    primeiro = 12 + 4 + cripto.TAMANHO_DO_BLOCO + 16
    pacote.write_bytes(dados[:primeiro])
    with pytest.raises(cripto.CriptografiaError):
        cripto.decifrar_arquivo(chave, pacote, tmp_path / "saida.bin")


def test_blocos_trocados_de_ordem_sao_detectados(tmp_path, chave):
    pacote = _cifrar(tmp_path, chave, os.urandom(2 * cripto.TAMANHO_DO_BLOCO + 10))
    dados = pacote.read_bytes()
    cabecalho, resto = dados[:12], dados[12:]
    tam1 = 4 + cripto.TAMANHO_DO_BLOCO + 16
    bloco1, bloco2, final = resto[:tam1], resto[tam1 : 2 * tam1], resto[2 * tam1 :]
    pacote.write_bytes(cabecalho + bloco2 + bloco1 + final)
    with pytest.raises(cripto.CriptografiaError):
        cripto.decifrar_arquivo(chave, pacote, tmp_path / "saida.bin")


def test_lixo_no_fim_e_detectado(tmp_path, chave):
    pacote = _cifrar(tmp_path, chave, b"conteudo")
    with pacote.open("ab") as arquivo:
        arquivo.write(b"\x00\x00\x00\x20" + os.urandom(32))
    # O último bloco original deixa de ser o final: o AAD não confere.
    with pytest.raises(cripto.CriptografiaError):
        cripto.decifrar_arquivo(chave, pacote, tmp_path / "saida.bin")


def test_arquivo_que_nao_e_pacote(tmp_path, chave):
    falso = tmp_path / "falso.enc"
    falso.write_bytes(b"isto nao e um backup")
    with pytest.raises(cripto.CriptografiaError):
        cripto.decifrar_arquivo(chave, falso, tmp_path / "saida.bin")


def test_chave_gerada_tem_0600_e_nao_sobrescreve(tmp_path):
    caminho = tmp_path / "chave.b64"
    cripto.gerar_chave(caminho)
    assert oct(caminho.stat().st_mode & 0o777) == "0o600"
    assert len(cripto.ler_chave(caminho)) == 32
    with pytest.raises(FileExistsError):
        cripto.gerar_chave(caminho)


def test_chave_invalida_e_recusada(tmp_path):
    caminho = tmp_path / "chave.b64"
    caminho.write_text("curta")
    with pytest.raises(cripto.CriptografiaError):
        cripto.ler_chave(caminho)
