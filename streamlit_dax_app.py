import streamlit as st
import re
import networkx as nx
import matplotlib.pyplot as plt
import matplotlib # Necesario para configurar el backend

# Configurar Matplotlib para que no intente usar un backend interactivo en el servidor
try:
    matplotlib.use('Agg')
except Exception as e:
    # Este print irá a los logs del servidor de Streamlit si hay un problema aquí.
    # No es visible para el usuario final en la UI.
    print(f"Advertencia al configurar matplotlib.use('Agg'): {e}")

# Variable global para el estado de Graphviz/Pydot
HAS_PYDOT_AND_GRAPHVIZ = False
try:
    import pydotplus # Necesario para que NetworkX interactúe con Graphviz via nx_pydot
    import pydot # NetworkX puede intentar importar 'pydot' directamente
    
    # Verifica si pydotplus puede encontrar los ejecutables de Graphviz
    # y si la función de layout de NetworkX se puede importar.
    if pydotplus.find_graphviz() and pydotplus.find_graphviz().get('dot'):
        from networkx.drawing.nx_pydot import graphviz_layout
        HAS_PYDOT_AND_GRAPHVIZ = True
except ImportError:
    # pydotplus, pydot o nx_pydot.graphviz_layout no se pudieron importar
    HAS_PYDOT_AND_GRAPHVIZ = False
except Exception:
    # Otra excepción durante el chequeo (ej. find_graphviz falla)
    HAS_PYDOT_AND_GRAPHVIZ = False


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
        # No mostrar error en UI aquí, se maneja en la UI principal si fig es None
        return None 

    base_node_size = 2000 
    font_node_size = 6 
    fig_width = max(12, num_nodes * 0.5 if num_nodes > 10 else 12) 
    fig_height = max(8, num_nodes * 0.4 if num_nodes > 10 else 8)
    
    fig, ax = plt.subplots(figsize=(min(fig_width, 45), min(fig_height, 35)))

    pos = None
    layout_engine_used = "Spring Layout (inicial)" 

    if HAS_PYDOT_AND_GRAPHVIZ and G.number_of_nodes() > 0 :
        try:
            from networkx.drawing.nx_pydot import graphviz_layout # Asegurar importación local
            pos = graphviz_layout(G, prog='dot')
            layout_engine_used = "Graphviz 'dot' Layout ✨"
        except Exception as e_layout:
            # Este error SÍ se muestra en la UI principal si ocurre
            st.error(f"❌ Falló el intento de usar `graphviz_layout(G, prog='dot')`: {type(e_layout).__name__}: {e_layout}")
            st.warning("Se usará 'spring_layout' como alternativa debido al error anterior.")
            pos = None 
            layout_engine_used = "Spring Layout (excepción en dot)"
    
    if pos is None and G.number_of_nodes() > 0: 
        pos = nx.spring_layout(G, k=2.5/max(1, (G.number_of_nodes()**0.5)), iterations=100, seed=42)
        if not layout_engine_used.endswith("(excepción en dot)"): # Solo actualizar si no fue por error de dot
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
        # Si pos es None pero hay nodos, es un problema de layout no manejado antes.
        # Ya retornamos None si num_nodes <= 1.
        if num_nodes > 1 and pos is None:
             st.error("No se pudo calcular la posición de los nodos para el gráfico.")
        return None 
    
    fig.tight_layout() 
    return fig

# --- Interfaz de Usuario con Streamlit ---
st.set_page_config(page_title="Context Grid DAX Visualizer", layout="wide")

st.title("📊 Visualizador del Reticulado de Contexto DAX")
st.markdown("""
Esta herramienta te ayuda a visualizar la estructura jerárquica (el "reticulado") 
definida por una cláusula `WITH VISUAL SHAPE` de DAX. Pega tu código abajo.
""")

# Sección de diagnóstico simplificada en la sidebar:
st.sidebar.subheader("Estado del Motor de Layout")
if HAS_PYDOT_AND_GRAPHVIZ:
    st.sidebar.success("✅ Layout jerárquico (Graphviz) activado.")
else:
    st.sidebar.warning("⚠️ Layout jerárquico (Graphviz) no disponible. Se usará layout alternativo.")


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
        with st.spinner("Analizando DAX y generando gráfico... ⏳"):
            parsed_struct = parse_visual_shape(dax_clause_input)
            
            # Es útil mostrar la estructura parseada incluso si el gráfico falla o está vacío
            st.subheader("Estructura Parseada (para referencia):")
            st.json(parsed_struct)

            if not parsed_struct.get("ROWS") and not parsed_struct.get("COLUMNS"):
                st.warning("La entrada no definió campos para ROWS ni para COLUMNS. No se puede generar el gráfico principal del reticulado.")
                # Podríamos optar por no llamar a create_precise_lattice_figure aquí
            elif not parsed_struct.get("ROWS") or not parsed_struct.get("COLUMNS"):
                 st.warning("Se requieren campos tanto en ROWS como en COLUMNS para el reticulado completo de intersecciones. Se mostrará la jerarquía de un solo eje si está definida.")
                 # Intentar graficar lo que hay (la función create_precise_lattice_figure manejará un solo eje sin intersecciones)
                 fig = create_precise_lattice_figure(parsed_struct)
                 if fig:
                     st.subheader("Gráfico del Reticulado (parcial):")
                     st.pyplot(fig)
                 else:
                     st.info("No se generó ningún gráfico (posiblemente solo nodo raíz).")
            else:
                # Caso normal con ROWS y COLUMNS
                fig = create_precise_lattice_figure(parsed_struct)
                if fig:
                    st.subheader("Gráfico del Reticulado:")
                    st.pyplot(fig)
                else:
                    # Este caso es si create_precise_lattice_figure devuelve None
                    # (ej. solo nodo raíz o error no capturado antes, aunque debería ser raro)
                    st.error("No se pudo generar la figura del gráfico.")
    else:
        st.warning("Por favor, introduce una cláusula DAX para visualizar.")

st.sidebar.header("Acerca de")
st.sidebar.info(
    "Esta aplicación es un MVP para visualizar el 'Context Grid' de los cálculos visuales en DAX. "
    "Ayuda a entender la estructura lógica sobre la que operan dichos cálculos."
)
