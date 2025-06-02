# streamlit_dax_app.py

import streamlit as st
import re
import networkx as nx
import matplotlib.pyplot as plt
import matplotlib
import os # Importar os para verificar el PATH
import sys # Importar sys para la versión de Python

matplotlib.use('Agg')

# --- SECCIÓN DE DIAGNÓSTICO DE PYDOTPLUS/GRAPHVIZ ---
st.sidebar.subheader("Diagnóstico de Graphviz/Pydot")
try:
    import pydotplus
    st.sidebar.success("✅ pydotplus importado correctamente.")
    
    # Intentar encontrar Graphviz
    # find_graphviz() devuelve un diccionario con las rutas a los ejecutables si los encuentra
    graphviz_check_result = pydotplus.find_graphviz() 
    
    if graphviz_check_result:
        st.sidebar.write("`pydotplus.find_graphviz()` encontró:")
        # Convertir a strings para evitar problemas de serialización con st.json
        stringified_result = {k: str(v) for k, v in graphviz_check_result.items()}
        st.sidebar.json(stringified_result)
        if 'dot' in graphviz_check_result and graphviz_check_result['dot'] is not None:
            st.sidebar.success(f"✅ 'dot' ejecutable encontrado en: {graphviz_check_result['dot']}")
            HAS_PYDOT_AND_GRAPHVIZ_FLAG = True
        else:
            st.sidebar.error("❌ 'dot' NO encontrado por `pydotplus.find_graphviz()`.")
            HAS_PYDOT_AND_GRAPHVIZ_FLAG = False
    else:
        st.sidebar.error("❌ `pydotplus.find_graphviz()` devolvió None o un resultado vacío.")
        HAS_PYDOT_AND_GRAPHVIZ_FLAG = False
        
    # Verificar importación de graphviz_layout de NetworkX
    from networkx.drawing.nx_pydot import graphviz_layout
    st.sidebar.success("✅ `nx_pydot.graphviz_layout` importado.")
    
    if not HAS_PYDOT_AND_GRAPHVIZ_FLAG: # Si find_graphviz falló, la bandera global debe ser False
         raise Exception("Fallo en encontrar 'dot' con pydotplus.find_graphviz()")

except ImportError as ie:
    st.sidebar.error(f"ImportError: {ie}")
    HAS_PYDOT_AND_GRAPHVIZ_FLAG = False
except Exception as e:
    st.sidebar.error(f"Excepción durante chequeo de Graphviz/Pydot: {e}")
    HAS_PYDOT_AND_GRAPHVIZ_FLAG = False

# Usamos la nueva bandera para la lógica de la app
HAS_PYDOT_AND_GRAPHVIZ = HAS_PYDOT_AND_GRAPHVIZ_FLAG
if HAS_PYDOT_AND_GRAPHVIZ:
    st.sidebar.success("🎉 ¡Graphviz y pydotplus parecen estar listos para el layout jerárquico!")
else:
    st.sidebar.error("⚠️ Graphviz/pydotplus no están listos. Se usará layout alternativo.")
# --- FIN DE SECCIÓN DE DIAGNÓSTICO ---


# ... (resto de tu código: parse_visual_shape, create_precise_lattice_figure, interfaz de Streamlit) ...
# Asegúrate de que la función create_precise_lattice_figure y la lógica principal usen
# esta variable global HAS_PYDOT_AND_GRAPHVIZ actualizada.
# Por ejemplo, dentro de create_precise_lattice_figure, cuando decides qué layout usar:
# if HAS_PYDOT_AND_GRAPHVIZ and G.number_of_nodes() > 0 :
#    try:
#        pos = graphviz_layout(G, prog='dot') # Aquí se usa la variable global
# ...

# Y en la UI principal donde muestras la advertencia:
# if st.button("🔍 Generar Gráfico del Reticulado"):
#    if dax_clause_input.strip():
#        if not HAS_PYDOT_AND_GRAPHVIZ: # Usa la variable global actualizada
#            st.warning(
#                "Advertencia: `pydotplus` o Graphviz no están correctamente configurados..."
#            )
# ... (el resto de tu código)
