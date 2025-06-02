import streamlit as st
import re
import networkx as nx
import matplotlib.pyplot as plt
import matplotlib # Necesario para configurar el backend
import os # Importar os para verificar el PATH (opcional para diagnóstico futuro)
import sys # Importar sys para la versión de Python (opcional para diagnóstico futuro)

# Configurar Matplotlib para que no intente usar un backend interactivo en el servidor
# Esto es importante para evitar errores en entornos sin GUI como Streamlit Cloud.
try:
    matplotlib.use('Agg')
except Exception as e:
    # Este print irá a los logs del servidor de Streamlit si hay un problema aquí.
    print(f"Advertencia al configurar matplotlib.use('Agg'): {e}")


# --- SECCIÓN DE DIAGNÓSTICO DE PYDOTPLUS/GRAPHVIZ (se mostrará en la sidebar) ---
# Es importante que esta sección se ejecute para definir HAS_PYDOT_AND_GRAPHVIZ globalmente.
HAS_PYDOT_AND_GRAPHVIZ_FLAG_INIT = False # Bandera inicial
try:
    import pydotplus
    # No mostramos mensajes de éxito aquí para no llenar la sidebar innecesariamente
    # a menos que haya un problema.
    
    graphviz_check_result = pydotplus.find_graphviz() 
    
    if graphviz_check_result and 'dot' in graphviz_check_result and graphviz_check_result['dot'] is not None:
        # Si 'dot' es encontrado, intentamos importar graphviz_layout.
        # Este import puede fallar si NetworkX no tiene bien pydotplus o si hay otro problema.
        from networkx.drawing.nx_pydot import graphviz_layout
        HAS_PYDOT_AND_GRAPHVIZ_FLAG_INIT = True # Todo parece estar bien
    else:
        # Si find_graphviz() falla o no encuentra 'dot'.
        HAS_PYDOT_AND_GRAPHVIZ_FLAG_INIT = False
        # Los mensajes de error específicos se mostrarán en la UI principal si se intenta usar.

except ImportError as ie:
    # Falló la importación de pydotplus o nx_pydot
    HAS_PYDOT_AND_GRAPHVIZ_FLAG_INIT = False
except Exception as e_diag:
    # Otra excepción durante el chequeo
    HAS_PYDOT_AND_GRAPHVIZ_FLAG_INIT = False
# --- FIN DE SECCIÓN DE DIAGNÓSTICO ---

# Variable global que usarán las funciones y la UI
HAS_PYDOT_AND_GRAPHVIZ = HAS_PYDOT_AND_GRAPHVIZ_FLAG_INIT


def parse_visual_shape(visual_shape_clause: str):
    """
    Analiza la cláusula WITH VISUAL SHAPE para extraer la estructura de los ejes.
    """
    structure = {"ROWS": [], "COLUMNS": []}
    current_axis = None
    axis_regex = re.compile(r"AXIS\s+(rows|columns)", re.IGNORECASE)
    group_regex = re.compile(r"GROUP\s+\[([^\]]+)\]", re.IGNORECASE)

    for line in visual_shape_clause.splitlines():
        line = line.strip()
        if not line:
            continue
        axis_match = axis_regex.search(line)
        if axis_match:
            current_axis = axis_match.group(1).upper()
            if current_axis not in structure:
                 structure[current_axis] = []
            continue
        if current_axis:
            group_match = group_regex.search(line)
            if group_match:
                field_name = group_match.group(1)
                if current_axis in structure:
                    structure[current_axis].append(field_name)
    return structure

def create_precise_lattice_figure(parsed_structure: dict):
    """
    Genera la figura de Matplotlib para el reticulado ("lattice") preciso.
    Devuelve el objeto de la figura (fig) o None si no se puede graficar.
    """
    G = nx.DiGraph()
    
    # Usar la variable global HAS_PYDOT_AND_GRAPHVIZ definida arriba
    if HAS_PYDOT_AND_GRAPHVIZ:
        G.graph['graph'] = {
            'rankdir': 'TB', 'splines': 'spline',
            'nodesep': '0.6', 'ranksep': '1.2', 
            'overlap': 'false',
        }

    labels = {}
    gv_node_styles = {} 
    mpl_node_colors = {}
    mpl_default_color = 'lightgray'

    gv_style_root = {'shape': 'box', 'style': 'filled', 'fillcolor': 'lightblue', 'fontsize': '9'}
    gv_style_rows = {'shape': 'box', 'style': 'filled', 'fillcolor': 'lightgreen', 'fontsize': '7'} 
    gv_style_cols = {'shape': 'box', 'style': 'filled', 'fillcolor': 'lightgoldenrodyellow', 'fontsize': '7'}
    gv_style_intersection = {'shape': 'box', 'style': 'filled', 'fillcolor': 'salmon', 'fontsize': '7'}

    root_id = 'Nivel 0'
    labels[root_id] = 'Nivel 0' 
    G.add_node(root_id)
    gv_node_styles[root_id] = gv_style_root
    mpl_node_colors[root_id] = gv_style_root.get('fillcolor', mpl_default_color)

    row_fields = parsed_structure.get("ROWS", [])
    col_fields = parsed_structure.get("COLUMNS", [])

    row_level_nodes_map = {} 
    parent_in_row_hierarchy = root_id
    current_row_path_fields_for_label = []
    for i, field in enumerate(row_fields):
        node_id = f'R{i+1}_[{field.replace(" ","_")}]' 
        current_row_path_fields_for_label.append(f"[{field}]")
        labels[node_id] = " X ".join(current_row_path_fields_for_label)
        G.add_node(node_id)
        gv_node_styles[node_id] = gv_style_rows
        mpl_node_colors[node_id] = gv_style_rows.get('fillcolor', mpl_default_color)
        G.add_edge(parent_in_row_hierarchy, node_id)
        row_level_nodes_map[i] = node_id 
        parent_in_row_hierarchy = node_id
        
    col_level_nodes_map = {} 
    parent_in_col_hierarchy = root_id
    current_col_path_fields_for_label = []
    for i, field in enumerate(col_fields):
        node_id = f'C{i+1}_[{field.replace(" ","_")}]' 
        current_col_path_fields_for_label.append(f"[{field}]")
        labels[node_id] = " X ".join(current_col_path_fields_for_label)
        G.add_node(node_id)
        gv_node_styles[node_id] = gv_style_cols
        mpl_node_colors[node_id] = gv_style_cols.get('fillcolor', mpl_default_color)
        G.add_edge(parent_in_col_hierarchy, node_id)
        col_level_nodes_map[i] = node_id 
        parent_in_col_hierarchy = node_id

    intersection_nodes_map = [[None for _ in range(len(col_fields))] for _ in range(len(row_fields))]

    if row_fields and col_fields:
        for k_idx in range(len(row_fields)): 
            for l_idx in range(len(col_fields)): 
                current_row_fields_for_intersect_label = row_fields[:k_idx+1]
                current_col_fields_for_intersect_label = col_fields[:l_idx+1]
                
                row_part_label = " | ".join([f"[{rf}]" for rf in current_row_fields_for_intersect_label])
                col_part_label = " | ".join([f"[{cf}]" for cf in current_col_fields_for_intersect_label])
                node_label = f'{row_part_label}\n X \n{col_part_label}'
                
                node_id = f'I_{k_idx+1}_{l_idx+1}' 
                
                labels[node_id] = node_label
                G.add_node(node_id)
                gv_node_styles[node_id] = gv_style_intersection
                mpl_node_colors[node_id] = gv_style_intersection.get('fillcolor', mpl_default_color)
                intersection_nodes_map[k_idx][l_idx] = node_id

                parent1_id, parent2_id = None, None
                if k_idx == 0 and l_idx == 0: 
                    parent1_id = row_level_nodes_map[0] 
                    parent2_id = col_level_nodes_map[0] 
                elif k_idx > 0 and l_idx == 0: 
                    parent1_id = row_level_nodes_map[k_idx] 
                    parent2_id = intersection_nodes_map[k_idx-1][0] 
                elif k_idx == 0 and l_idx > 0: 
                    parent1_id = col_level_nodes_map[l_idx] 
                    parent2_id = intersection_nodes_map[0][l_idx-1] 
                elif k_idx > 0 and l_idx > 0: 
                    parent1_id = intersection_nodes_map[k_idx-1][l_idx] 
                    parent2_id = intersection_nodes_map[k_idx][l_idx-1] 
                
                if parent1_id and G.has_node(parent1_id): G.add_edge(parent1_id, node_id)
                if parent2_id and G.has_node(parent2_id): G.add_edge(parent2_id, node_id)
                
    for node_id, styles_dict in gv_node_styles.items():
        if G.has_node(node_id): G.nodes[node_id].update(styles_dict)
            
    ordered_mpl_node_colors = [mpl_node_colors.get(node, mpl_default_color) for node in G.nodes()]

    num_nodes = G.number_of_nodes()
    if num_nodes <= 1: 
        st.info("No hay suficientes nodos para generar un gráfico significativo (solo nodo raíz o ninguno).")
        return None 

    base_node_size = 2000 
    font_node_size = 6 
    fig_width = max(12, num_nodes * 0.5 if num_nodes > 10 else 12) 
    fig_height = max(8, num_nodes * 0.4 if num_nodes > 10 else 8)
    
    fig, ax = plt.subplots(figsize=(min(fig_width, 45), min(fig_height, 35)))

    pos = None
    layout_engine_used = "Spring Layout (inicial)" 

    if HAS_PYDOT_AND_GRAPHVIZ and G.number_of_nodes() > 0 :
        # Este mensaje aparecerá en el panel principal cuando se intente generar el gráfico.
        st.info("ℹ️ Intentando usar `graphviz_layout` con `prog='dot'`...")
        try:
            # Re-importar localmente por si acaso, aunque la bandera global debería ser suficiente.
            from networkx.drawing.nx_pydot import graphviz_layout 
            pos = graphviz_layout(G, prog='dot')
            layout_engine_used = "Graphviz 'dot' Layout ✨"
            st.success("✅ `graphviz_layout` con `prog='dot'` parece haber funcionado para calcular posiciones.")
        except Exception as e_layout:
            st.error(f"❌ Falló el intento de usar `graphviz_layout(G, prog='dot')`: {type(e_layout).__name__}: {e_layout}")
            st.warning("Se usará 'spring_layout' como alternativa debido al error anterior.")
            pos = None 
            layout_engine_used = "Spring Layout (excepción en dot)"
    
    if pos is None and G.number_of_nodes() > 0: 
        if not layout_engine_used.endswith("(excepción en dot)"): # Solo mostrar si no es por error de dot
            st.info("ℹ️ Calculando 'spring_layout' como alternativa...")
        pos = nx.spring_layout(G, k=2.5/max(1, (G.number_of_nodes()**0.5)), iterations=100, seed=42)
        if not layout_engine_used.endswith("(excepción en dot)"):
             layout_engine_used = "Spring Layout (fallback general)"
    
    if G.number_of_nodes() > 0 and pos is not None:
        nx.draw_networkx_nodes(G, pos, ax=ax, node_shape='s', node_size=base_node_size, 
                               node_color=ordered_mpl_node_colors,
                               linewidths=0.5, edgecolors='black')
        nx.draw_networkx_labels(G, pos, ax=ax, labels=labels, font_size=font_node_size, font_weight='normal')
        nx.draw_networkx_edges(G, pos, ax=ax, width=1.0, edge_color='dimgray', 
                               arrows=True, arrowstyle='-|>', arrowsize=10) 
        ax.set_title(f"Diagrama de Reticulado (Motor: {layout_engine_used})", fontsize=14)
    else:
        # Este caso no debería darse si retornamos None antes para num_nodes <=1
        # Pero lo dejamos por si acaso pos es None por otra razón.
        st.error("No se pudo calcular la posición de los nodos para el gráfico.")
        return None # Devuelve None si no se pudo generar el gráfico
    
    fig.tight_layout() 
    return fig

# --- Interfaz de Usuario con Streamlit ---
st.set_page_config(page_title="Context Grid DAX Visualizer", layout="wide")

st.title("📊 Visualizador del Reticulado de Contexto DAX")
st.markdown("""
Esta herramienta te ayuda a visualizar la estructura jerárquica (el "reticulado") 
definida por una cláusula `WITH VISUAL SHAPE` de DAX. Pega tu código abajo.
""")

# Sección de diagnóstico en la sidebar (movida aquí para que se muestre al inicio)
st.sidebar.subheader("Estado de Graphviz/Pydot")
if HAS_PYDOT_AND_GRAPHVIZ:
    st.sidebar.success("🎉 Graphviz y pydotplus parecen estar listos para el layout jerárquico!")
    # Podríamos añadir aquí la info de find_graphviz si queremos, pero mantenemos simple.
    # diagnostic_info = pydotplus.find_graphviz() # Asumimos que pydotplus está importado
    # if diagnostic_info and diagnostic_info.get('dot'):
    #    st.sidebar.caption(f"Dot path: {diagnostic_info['dot']}")
else:
    st.sidebar.error("⚠️ Graphviz/pydotplus no detectados correctamente. El layout jerárquico ('dot') podría no funcionar y se usará un layout alternativo.")


ejemplo_dax = """AXIS rows
    GROUP [Anio]
    GROUP [Trimestre]
    GROUP [Mes]
AXIS columns
    GROUP [Categoria]
    GROUP [Subcategoria]
    GROUP [Producto]
"""

dax_clause_input = st.text_area(
    "Introduce tu cláusula `WITH VISUAL SHAPE` (o el contenido desde `AXIS ROWS`):",
    height=250,
    placeholder=ejemplo_dax
)

if st.button("🔍 Generar Gráfico del Reticulado"):
    if dax_clause_input.strip():
        # La advertencia principal sobre Graphviz ahora se maneja con la info de la sidebar
        # y los mensajes dentro de create_precise_lattice_figure.
        
        with st.spinner("Analizando DAX y generando gráfico... ⏳"):
            parsed_struct = parse_visual_shape(dax_clause_input)
            
            st.subheader("Estructura Parseada (para referencia):")
            st.json(parsed_struct)

            if not parsed_struct.get("ROWS") and not parsed_struct.get("COLUMNS"):
                st.warning("La entrada no definió campos para ROWS ni para COLUMNS. No se puede generar el gráfico principal.")
            # No necesitamos la siguiente condición elif ya que create_precise_lattice_figure maneja el caso de 1 solo eje
            # (no dibujará intersecciones, pero sí la jerarquía de ese eje).
            else:
                fig = create_precise_lattice_figure(parsed_struct)
                if fig:
                    st.subheader("Gráfico del Reticulado:")
                    st.pyplot(fig)
                else:
                    # create_precise_lattice_figure ya habrá mostrado un st.info si no hay nodos suficientes.
                    # Podemos añadir un mensaje genérico si fig es None por otra razón.
                    if G.number_of_nodes() > 1: # Si G se hubiera pasado o accedido
                         st.error("Ocurrió un error al generar la figura del gráfico.")
    else:
        st.warning("Por favor, introduce una cláusula DAX para visualizar.")

st.sidebar.header("Acerca de")
st.sidebar.info(
    "Esta aplicación es un MVP para visualizar el 'Context Grid' de los cálculos visuales en DAX. "
    "Ayuda a entender la estructura lógica sobre la que operan dichos cálculos."
)
