import os
import uuid

from flask import current_app
from PIL import Image, ImageOps

EXTENSOES_PERMITIDAS = {'jpg', 'jpeg', 'png', 'webp'}
TAMANHO_MAX = (300, 300)
PASTA_RELATIVA = os.path.join('uploads', 'fotos')


def extensao_valida(filename):
    if not filename or '.' not in filename:
        return False
    return filename.rsplit('.', 1)[-1].lower() in EXTENSOES_PERMITIDAS


def salvar_foto(colaborador_id, file_storage):
    """Redimensiona (máx 300x300) e salva a foto como JPEG.

    Retorna o caminho relativo à pasta static (usado com url_for('static', ...)).
    """
    pasta = os.path.join(current_app.static_folder, PASTA_RELATIVA)
    os.makedirs(pasta, exist_ok=True)

    nome_arquivo = f'{colaborador_id}_{uuid.uuid4().hex}.jpg'
    caminho_absoluto = os.path.join(pasta, nome_arquivo)

    imagem = Image.open(file_storage.stream)
    imagem = ImageOps.exif_transpose(imagem)

    if imagem.mode in ('RGBA', 'LA') or (imagem.mode == 'P' and 'transparency' in imagem.info):
        fundo = Image.new('RGB', imagem.size, (255, 255, 255))
        imagem = imagem.convert('RGBA')
        fundo.paste(imagem, mask=imagem.split()[-1])
        imagem = fundo
    else:
        imagem = imagem.convert('RGB')

    imagem.thumbnail(TAMANHO_MAX, Image.LANCZOS)
    imagem.save(caminho_absoluto, 'JPEG', quality=88, optimize=True)

    return f'{PASTA_RELATIVA}/{nome_arquivo}'.replace(os.sep, '/')


def remover_foto(foto_path):
    if not foto_path:
        return
    caminho_absoluto = os.path.join(current_app.static_folder, foto_path)
    if os.path.isfile(caminho_absoluto):
        os.remove(caminho_absoluto)
