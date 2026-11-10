"""A restauração recusa o que é perigoso ANTES de escrever no destino (não precisa de Docker)."""

import json
import sys
import tarfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "backup"))

import ambiente  # noqa: E402
import cripto  # noqa: E402
import restaurar_backup  # noqa: E402

CHAVE = bytes(range(32))


def _pacote(
    tmp_path: Path, *, adulterar_arquivo: bool = False, membro: str = "auth_db.dump"
) -> Path:
    pasta = tmp_path / "montagem"
    pasta.mkdir()
    (pasta / "auth_db.dump").write_bytes(b"conteudo do dump")
    manifesto = {
        "formato": ambiente.FORMATO_DO_PACOTE,
        "arquivos": {"auth_db.dump": cripto.sha256_do_arquivo(pasta / "auth_db.dump")},
    }
    (pasta / "manifesto.json").write_text(json.dumps(manifesto))
    if adulterar_arquivo:
        (pasta / "auth_db.dump").write_bytes(b"conteudo ALTERADO")
    tar = tmp_path / "pacote.tar"
    with tarfile.open(tar, "w") as t:
        t.add(pasta / "auth_db.dump", arcname=membro)
        t.add(pasta / "manifesto.json", arcname="manifesto.json")
    pacote = tmp_path / "pacote.backup"
    cripto.cifrar_arquivo(CHAVE, tar, pacote)
    return pacote


def test_pacote_valido_abre(tmp_path):
    destino = tmp_path / "saida"
    destino.mkdir()
    manifesto = restaurar_backup.abrir_pacote(_pacote(tmp_path), CHAVE, destino)
    assert manifesto["formato"] == ambiente.FORMATO_DO_PACOTE


def test_arquivo_com_hash_diferente_do_manifesto_e_recusado(tmp_path):
    destino = tmp_path / "saida"
    destino.mkdir()
    with pytest.raises(ambiente.OperacaoError, match="hash"):
        restaurar_backup.abrir_pacote(_pacote(tmp_path, adulterar_arquivo=True), CHAVE, destino)


def test_caminho_perigoso_no_tar_e_recusado(tmp_path):
    destino = tmp_path / "saida"
    destino.mkdir()
    with pytest.raises(ambiente.OperacaoError, match="inesperado"):
        restaurar_backup.abrir_pacote(_pacote(tmp_path, membro="../fora.dump"), CHAVE, destino)


def test_chave_errada_nao_escreve_nada(tmp_path):
    destino = tmp_path / "saida"
    destino.mkdir()
    with pytest.raises(cripto.CriptografiaError):
        restaurar_backup.abrir_pacote(_pacote(tmp_path), bytes(32), destino)
    assert not (destino / "conteudo").exists()


@pytest.mark.parametrize("projeto", ["simpa", "simpa-prod", "producao", "simpa-test-x/../simpa"])
def test_destino_que_nao_e_de_teste_e_recusado(projeto):
    with pytest.raises(ambiente.OperacaoError, match="descartável"):
        restaurar_backup.validar_destino(projeto, projeto)


def test_exige_repetir_o_nome_do_destino():
    with pytest.raises(ambiente.OperacaoError, match="confirmo-destino"):
        restaurar_backup.validar_destino("simpa-restore-test", "")
    restaurar_backup.validar_destino("simpa-restore-test", "simpa-restore-test")
