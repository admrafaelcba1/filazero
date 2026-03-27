import streamlit as st

from services.catalogo_service import (
    SHEET_NAME_DECRETO,
    gerar_planilha_modelo_catalogo,
    importar_catalogo_upload,
    listar_catalogo,
    obter_resumo_catalogo,
)
from utils.layout import (
    info_strip,
    kpi_card,
    page_header,
    render_html_table,
    section_header,
)


def _formatar_moeda(valor) -> str:
    return f"R$ {float(valor or 0):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def render():
    page_header(
        "Catálogo de procedimentos",
        "Importação e consulta do catálogo oficial do Decreto 1.083, com visão consolidada da base vigente.",
        tag="Base oficial",
    )

    info_strip(
        "Esta tela é voltada à carga e à consulta do catálogo oficial. "
        "O cadastro manual detalhado permanece disponível em Cadastros Básicos."
    )

    resumo = obter_resumo_catalogo()

    section_header(
        "Resumo do catálogo",
        "Indicadores gerais da base ativa e último processamento realizado.",
    )

    a1, a2, a3, a4, a5 = st.columns(5)
    with a1:
        kpi_card("Total catálogo", str(resumo["total_procedimentos"]))
    with a2:
        kpi_card("Ativos", str(resumo["total_ativos"]))
    with a3:
        kpi_card("AMB", str(resumo["total_amb"]))
    with a4:
        kpi_card("HOSP", str(resumo["total_hosp"]))
    with a5:
        kpi_card("AMB/HOSP", str(resumo["total_amb_hosp"]))

    ultima = resumo.get("ultima_importacao")
    if ultima:
        st.markdown(
            f"""
            **Última importação:** {ultima.get('arquivo_nome') or '-'}  
            **Registros processados:** {int(ultima.get('total_registros') or 0)}  
            **Data/hora:** {ultima.get('created_at') or '-'}
            """
        )
    else:
        st.info("Ainda não houve importação registrada do catálogo.")

    tab1, tab2 = st.tabs(["Importar Decreto", "Consultar Catálogo"])

    with tab1:
        section_header(
            "Importar planilha do Decreto",
            "Utilize uma planilha Excel contendo a aba oficial esperada pelo sistema.",
        )

        st.markdown(
            f"""
            Utilize uma planilha Excel contendo a aba **{SHEET_NAME_DECRETO}**.

            Estrutura esperada:
            - CÓDIGO SIGTAP
            - DESCRIÇÃO DO PROCEDIMENTO
            - VALOR UNITÁRIO
            - COMPLEXIDADE
            - NUMERAÇÃO
            - REGISTRO
            - CLASSIFICAÇÃO INTERNA
            - SUB-GRUPO-COD
            - SUB-GRUPO-DESCRIÇÃO
            - CLASSIFICAÇÃO
            """
        )

        modelo = gerar_planilha_modelo_catalogo()
        st.download_button(
            "Baixar planilha modelo",
            data=modelo,
            file_name="modelo_catalogo_decreto_1083.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )

        arquivo = st.file_uploader(
            "Selecione a planilha Excel",
            type=["xlsx", "xls"],
            key="upload_catalogo_decreto",
        )

        if arquivo is not None:
            if st.button("Importar catálogo do Decreto", use_container_width=True):
                try:
                    resultado = importar_catalogo_upload(arquivo)

                    if resultado["ok"]:
                        st.success(resultado["mensagem"])

                        c1, c2, c3, c4 = st.columns(4)
                        with c1:
                            kpi_card("Processados", str(resultado.get("total_processado", 0)))
                        with c2:
                            kpi_card("Inseridos", str(resultado.get("inseridos", 0)))
                        with c3:
                            kpi_card("Atualizados", str(resultado.get("atualizados", 0)))
                        with c4:
                            kpi_card("Ignorados", str(resultado.get("ignorados", 0)))

                        erros = resultado.get("erros", [])
                        if erros:
                            st.warning("A importação foi concluída com observações.")
                            for erro in erros[:20]:
                                st.write(f"- {erro}")
                    else:
                        st.error(resultado["mensagem"])
                        erros = resultado.get("erros", [])
                        if erros:
                            for erro in erros[:20]:
                                st.write(f"- {erro}")

                except Exception as e:
                    st.error("Não foi possível concluir a importação do catálogo.")
                    st.exception(e)

    with tab2:
        section_header(
            "Consulta ao catálogo",
            "Pesquise registros por código, descrição, classificação, subgrupo ou natureza.",
        )

        filtro = st.text_input(
            "Pesquisar procedimento por código, descrição, classificação interna ou subgrupo",
            placeholder="Digite código SIGTAP, descrição ou outro termo...",
        )

        df = listar_catalogo(filtro=filtro)

        if df.empty:
            st.info("Nenhum procedimento encontrado.")
        else:
            df_exibir = df.copy()

            if "valor_unitario" in df_exibir.columns:
                df_exibir["valor_unitario"] = df_exibir["valor_unitario"].apply(_formatar_moeda)

            mapa_colunas = {
                "id": "ID",
                "codigo_sigtap": "CÓDIGO SIGTAP",
                "descricao_procedimento": "DESCRIÇÃO DO PROCEDIMENTO",
                "valor_unitario": "VALOR UNITÁRIO",
                "complexidade": "COMPLEXIDADE",
                "numeracao": "NUMERAÇÃO",
                "registro": "REGISTRO",
                "classificacao_interna": "CLASSIFICAÇÃO INTERNA",
                "subgrupo_cod": "SUB-GRUPO-COD",
                "subgrupo_descricao": "SUB-GRUPO-DESCRIÇÃO",
                "classificacao": "CLASSIFICAÇÃO",
                "natureza": "NATUREZA",
                "origem": "ORIGEM",
                "ativo": "ATIVO",
            }

            colunas_presentes = [c for c in mapa_colunas.keys() if c in df_exibir.columns]
            df_exibir = df_exibir[colunas_presentes].rename(columns=mapa_colunas)

            render_html_table(df_exibir)