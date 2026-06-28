"""Testes de autenticação."""


def test_login_valido(client, colaborador, login_as):
    resp = login_as(colaborador)
    assert resp.status_code == 200
    body = resp.data.decode('utf-8')
    # Após login bem-sucedido o navbar exibe o primeiro nome e o link de sair
    assert 'João' in body or 'Sair' in body


def test_login_invalido(client, colaborador, login_as):
    resp = login_as(colaborador, senha='senhaerrada')
    assert resp.status_code == 200
    body = resp.data.decode('utf-8')
    # Deve permanecer na página de login com mensagem de erro
    assert 'incorretos' in body or 'login' in body.lower()


def test_acesso_sem_login_redireciona(client):
    resp = client.get('/ferias/', follow_redirects=False)
    assert resp.status_code == 302
    assert 'login' in resp.headers['Location'].lower()
