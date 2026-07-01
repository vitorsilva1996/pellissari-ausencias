/**
 * Paginação client-side genérica para tabelas.
 *
 * Uso: <table data-paginate="algum-id" data-page-size="20"> ... </table>
 *      <div id="algum-id"></div>  (controles são injetados aqui)
 *
 * data-page-size é opcional (padrão 10) e deve ser um dos valores em TAMANHOS.
 *
 * Linhas que não devem ser paginadas nem contadas (ex: "nenhum resultado")
 * recebem o atributo data-empty. Linhas que pertencem ao mesmo "item" (ex:
 * uma linha de dados + a linha de comentário associada) recebem o mesmo
 * valor em data-item, para que sejam mostradas/ocultadas juntas.
 */
(function () {
  var TAMANHOS = [10, 20, 50, 100];

  function agrupar(linhas) {
    var grupos = [];
    var posicaoPorChave = {};
    linhas.forEach(function (tr) {
      var chave = tr.hasAttribute('data-item') ? 'item:' + tr.getAttribute('data-item') : null;
      if (chave === null || !(chave in posicaoPorChave)) {
        if (chave !== null) posicaoPorChave[chave] = grupos.length;
        grupos.push([tr]);
      } else {
        grupos[posicaoPorChave[chave]].push(tr);
      }
    });
    return grupos;
  }

  function criarBotao(texto, aoClicar, desabilitado, ativo) {
    var btn = document.createElement('button');
    btn.type = 'button';
    btn.textContent = texto;
    btn.className = 'btn btn-sm ' + (ativo ? 'btn-primary' : 'btn-outline-secondary');
    if (desabilitado) btn.disabled = true;
    btn.addEventListener('click', aoClicar);
    return btn;
  }

  function iniciar(table) {
    var tbody = table.tBodies[0];
    if (!tbody) return;

    var linhas = Array.prototype.filter.call(tbody.rows, function (tr) {
      return !tr.hasAttribute('data-empty');
    });
    if (linhas.length === 0) return;

    var grupos = agrupar(linhas);
    var total = grupos.length;

    var controlesId = table.getAttribute('data-paginate');
    var controles = controlesId ? document.getElementById(controlesId) : null;
    if (!controles) return;

    var padrao = parseInt(table.getAttribute('data-page-size'), 10);
    if (TAMANHOS.indexOf(padrao) === -1) padrao = TAMANHOS[0];

    if (total <= padrao) {
      controles.innerHTML = '';
      return;
    }

    var pagina = 1;
    var porPagina = padrao;

    function totalPaginas() {
      return Math.max(1, Math.ceil(total / porPagina));
    }

    function aplicar() {
      var tp = totalPaginas();
      if (pagina > tp) pagina = tp;
      var inicio = (pagina - 1) * porPagina;
      var fim = inicio + porPagina;
      grupos.forEach(function (linhasDoGrupo, i) {
        var visivel = i >= inicio && i < fim;
        linhasDoGrupo.forEach(function (tr) {
          tr.style.display = visivel ? '' : 'none';
        });
      });
      desenhar(tp);
    }

    function irPara(p) {
      pagina = p;
      aplicar();
    }

    function desenhar(tp) {
      controles.innerHTML = '';

      var esquerda = document.createElement('div');
      esquerda.className = 'd-flex align-items-center gap-2 small text-muted flex-wrap';

      var rotulo = document.createElement('span');
      rotulo.textContent = 'Mostrar';
      esquerda.appendChild(rotulo);

      var select = document.createElement('select');
      select.className = 'form-select form-select-sm d-inline-block';
      select.style.width = 'auto';
      TAMANHOS.forEach(function (n) {
        var opt = document.createElement('option');
        opt.value = String(n);
        opt.textContent = String(n);
        if (n === porPagina) opt.selected = true;
        select.appendChild(opt);
      });
      select.addEventListener('change', function () {
        porPagina = parseInt(select.value, 10);
        pagina = 1;
        aplicar();
      });
      esquerda.appendChild(select);

      var totalLabel = document.createElement('span');
      totalLabel.textContent = 'de ' + total + ' registro(s)';
      esquerda.appendChild(totalLabel);

      var direita = document.createElement('div');
      direita.className = 'd-flex align-items-center gap-1 flex-wrap';

      direita.appendChild(criarBotao('‹', function () { irPara(Math.max(1, pagina - 1)); }, pagina === 1, false));

      var janela = 2;
      for (var p = 1; p <= tp; p++) {
        var proximoDoAtual = Math.abs(p - pagina) <= janela;
        var extremidade = p === 1 || p === tp;
        if (proximoDoAtual || extremidade) {
          direita.appendChild(criarBotao(String(p), (function (pagina_) {
            return function () { irPara(pagina_); };
          })(p), false, p === pagina));
        } else if (p === 2 || p === tp - 1) {
          var span = document.createElement('span');
          span.className = 'px-1 text-muted';
          span.textContent = '…';
          direita.appendChild(span);
        }
      }

      direita.appendChild(criarBotao('›', function () { irPara(Math.min(tp, pagina + 1)); }, pagina === tp, false));

      var wrap = document.createElement('div');
      wrap.className = 'd-flex justify-content-between align-items-center gap-3 flex-wrap w-100';
      wrap.appendChild(esquerda);
      wrap.appendChild(direita);
      controles.appendChild(wrap);
    }

    aplicar();
  }

  document.addEventListener('DOMContentLoaded', function () {
    var tabelas = document.querySelectorAll('table[data-paginate]');
    tabelas.forEach(iniciar);
  });
})();
