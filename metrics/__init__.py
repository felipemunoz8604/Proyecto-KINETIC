"""
Metricas, benchmarks y pruebas de robustez.

Modulo nuevo de la Fase 2 (decision D3). Existe porque la Fase 1 midio
contra dos referencias internas -- no elegir parametro, y el mejor parametro
en retrospectiva -- y nunca contra comprar el activo y no hacer nada. En un
mercado direccional al alza y con estrategia mayormente larga, el competidor
real no es cero: es el activo.

Todo lo de aca opera sobre una CURVA DE PATRIMONIO diaria, no sobre
operaciones. Es a proposito: la decision D2 cambia la contabilidad de
operaciones a pesos de cartera, y una metrica atada al concepto de "operacion
abierta y cerrada" habria que reescribirla otra vez. Una curva de patrimonio
la produce cualquier cosa -- una estrategia, un benchmark, comprar y esperar.
"""
