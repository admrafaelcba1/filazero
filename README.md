# Fila Zero na Cirurgia - V3 Modular

## Como rodar

```bash
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

## O que mudou na V3

- `database.py` completo
- separação por serviços:
  - `catalogo_service.py`
  - `proposta_service.py`
  - `execucao_service.py`
  - `pagamento_service.py`
  - `remanejamento_service.py`
  - `dashboard_service.py`
- proposta e autorização em uma única tela
- regras de negócio principais isoladas nos serviços

## Regras implementadas

- proposta não pode aprovar acima do total
- item não pode autorizar acima da quantidade proposta
- execução não pode ultrapassar o autorizado
- pagamento não pode ultrapassar o executado
- remanejamento não altera o valor total da proposta
