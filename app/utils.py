from flask import request


def ler_ordenacao(prefixo, colunas_validas, padrao_col, padrao_dir='desc'):
    """Lê e valida os parâmetros de ordenação `sort_<prefixo>`/`dir_<prefixo>`
    da query string, usados para namespacear múltiplas tabelas ordenáveis
    na mesma página."""
    col = request.args.get(f'sort_{prefixo}', padrao_col)
    if col not in colunas_validas:
        col = padrao_col
    direcao = request.args.get(f'dir_{prefixo}', padrao_dir)
    if direcao not in ('asc', 'desc'):
        direcao = padrao_dir
    return col, direcao
