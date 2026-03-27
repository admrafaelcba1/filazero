from services.base import df


def resumo_dashboard():
    return {
        'beneficiarios': int(df('SELECT COUNT(*) qtd FROM beneficiarios').iloc[0]['qtd']),
        'procedimentos': int(df('SELECT COUNT(*) qtd FROM catalogo_procedimentos').iloc[0]['qtd']),
        'propostas': int(df('SELECT COUNT(*) qtd FROM propostas').iloc[0]['qtd']),
        'valor_total_propostas': float(df('SELECT COALESCE(SUM(valor_total),0) total FROM propostas').iloc[0]['total']),
        'valor_aprovado': float(df('SELECT COALESCE(SUM(valor_aprovado),0) total FROM propostas').iloc[0]['total']),
        'valor_executado': float(df('SELECT COALESCE(SUM(valor_total),0) total FROM execucoes').iloc[0]['total']),
        'valor_pago': float(df('SELECT COALESCE(SUM(valor_pago),0) total FROM pagamentos').iloc[0]['total']),
    }


def execucao_por_tipo():
    return df('''SELECT tipo_execucao, COALESCE(SUM(valor_total),0) AS valor
                 FROM execucoes GROUP BY tipo_execucao ORDER BY tipo_execucao''')
