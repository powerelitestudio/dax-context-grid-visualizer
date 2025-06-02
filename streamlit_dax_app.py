import streamlit as st
import re
import networkx as nx
import matplotlib.pyplot as plt
import matplotlib # Necesario para configurar el backend si se ejecuta en un entorno sin GUI

# Configurar Matplotlib para que no intente usar un backend interactivo en el servidor
matplotlib.use('Agg')


# Intentar importar pydot para usar el motor de layout de Graphviz
try:
    import pydot
    from networkx.drawing.nx_pydot import graphviz_layout
    HAS_PYDOT_AND_GRAPHVIZ = True
except ImportError:
    HAS_PYDOT_AND_GRAPHVIZ = False
except Exception as e: # Podría ser que pydot esté pero Graphviz no en el PATH
    if "dot" in str(e).lower() and "executable" in str(e).lower():
        # Este print aparecerá en la consola donde se ejecuta Streamlit
        print("⚠️ Advertencia: pydot está instalado, pero no se encontró el ejecutable 'dot' de Graphviz.")
        print("   Asegúrate de que Graphviz esté instalado y en el PATH del sistema donde se ejecuta Streamlit.")
    else:
        print(f"⚠️ Advertencia al importar o usar pydot/graphviz_layout: {e}")
    HAS_PYDOT_AND_GRAPHVIZ = False


def parse_visual_shape(visual_shape_clause: str):
    """
    Analiza la cláusula WITH VISUAL SHAPE para extraer la estructura de los ejes.
    (Esta función se mantiene igual que antes)
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
    MODIFICADO: Genera la figura de Matplotlib para el reticulado ("lattice") preciso.
    Ahora devuelve el objeto de la figura (fig) en lugar de mostrarla.
    """
    G = nx.DiGraph()
    
    # Atributos del grafo para Graphviz (si está disponible)
    graph_attrs = {}
    if HAS_PYDOT_AND_GRAPHVIZ:
        graph_attrs = {
            'rankdir': 'TB', 'splines': 'spline',
            'nodesep': '0.6', 'ranksep': '1.2', 
            'overlap': 'false',
        }
    # Aplicar atributos al grafo de NetworkX para que pydot los recoja
    # (NetworkX no tiene un G.graph['graph'] directo para pydot como se pensó,
    # los atributos se ponen en G.graph o se pasan al convertir a pydot.
    # graphviz_layout los toma de G.graph)
    G.graph.update(graph_attrs)


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

    if row_fields and col_fields: # Solo crear intersecciones si hay ambos ejes
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
                
                if parent1_id: G.add_edge(parent1_id, node_id)
                if parent2_id: G.add_edge(parent2_id, node_id)
                
    for node_id, styles_dict in gv_node_styles.items():
        if G.has_node(node_id): G.nodes[node_id].update(styles_dict)
            
    ordered_mpl_node_colors = [mpl_node_colors.get(node, mpl_default_color) for node in G.nodes()]

    num_nodes = G.number_of_nodes()
    if num_nodes <= 1: # Si solo está el nodo raíz o menos
        return None # No hay nada significativo que graficar

    base_node_size = 2000 
    font_node_size = 6 
    fig_width = max(12, num_nodes * 0.5 if num_nodes > 10 else 12) 
    fig_height = max(8, num_nodes * 0.4 if num_nodes > 10 else 8)
    
    # MODIFICACIÓN: Crear figura y ejes de Matplotlib
    fig, ax = plt.subplots(figsize=(min(fig_width, 45), min(fig_height, 35)))

    pos = None
    layout_engine_used = "Spring Layout (fallback)"
    if HAS_PYDOT_AND_GRAPHVIZ and G.number_of_nodes() > 0 :
        try:
            pos = graphviz_layout(G, prog='dot')
            layout_engine_used = "Graphviz 'dot' Layout ✨"
        except Exception as e:
            st.warning(f"No se pudo usar graphviz_layout (dot): {e}. Usando spring_layout como alternativa.")
            pos = None # Asegurar que se usa el fallback
    
    if pos is None and G.number_of_nodes() > 0:
        pos = nx.spring_layout(G, k=2.5/max(1, (G.number_of_nodes()**0.5)), iterations=100, seed=42)

    if G.number_of_nodes() > 0 and pos is not None:
        nx.draw_networkx_nodes(G, pos, ax=ax, node_shape='s', node_size=base_node_size, 
                               node_color=ordered_mpl_node_colors,
                               linewidths=0.5, edgecolors='black')

        nx.draw_networkx_labels(G, pos, ax=ax, labels=labels, font_size=font_node_size, font_weight='normal')

        nx.draw_networkx_edges(G, pos, ax=ax, width=1.0, edge_color='dimgray', 
                               arrows=True, arrowstyle='-|>', arrowsize=10) 
        
        ax.set_title(f"Diagrama de Reticulado (Motor: {layout_engine_used})", fontsize=14) # Usar ax.set_title
    else:
        # Si no hay nodos o pos es None, la figura estará vacía, se podría manejar.
        # Por ahora, si no hay nodos, la función retorna None antes.
        pass

    fig.tight_layout() # Usar fig.tight_layout()
    # MODIFICACIÓN: No usar plt.show(), retornar la figura
    return fig

# --- Interfaz de Usuario con Streamlit ---
st.set_page_config(page_title="Context Grid DAX Visualizer", layout="wide") # Configura el título de la pestaña y el layout

st.title("📊 Visualizador del Reticulado de Contexto DAX")
st.markdown("""
Esta herramienta te ayuda a visualizar la estructura jerárquica (el "reticulado") 
definida por una cláusula `WITH VISUAL SHAPE` de DAX. Pega tu código abajo.
""")

# Ejemplo de cláusula DAX para el placeholder
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
        if not HAS_PYDOT_AND_GRAPHVIZ:
            st.warning(
                "Advertencia: `pydot` o Graphviz no están correctamente configurados en el entorno del servidor. "
                "El diseño del gráfico ('layout') podría no ser el jerárquico esperado y usará un 'spring layout' como alternativa."
            )
        
        with st.spinner("Analizando DAX y generando gráfico... ⏳"):
            parsed_struct = parse_visual_shape(dax_clause_input)
            
            st.subheader("Estructura Parseada (para referencia):")
            st.json(parsed_struct) # Mostrar la estructura parseada

            if not parsed_struct.get("ROWS") and not parsed_struct.get("COLUMNS"):
                st.warning("La entrada no definió campos para ROWS ni para COLUMNS. No se puede generar el gráfico principal.")
            elif not parsed_struct.get("ROWS") or not parsed_struct.get("COLUMNS"):
                 st.warning("Se requieren campos tanto en ROWS como en COLUMNS para el reticulado completo de intersecciones.")
                 # Podríamos aún intentar graficar solo la jerarquía de un eje si existe
                 fig = create_precise_lattice_figure(parsed_struct)
                 if fig:
                     st.pyplot(fig)
                 else:
                     st.info("No se generó ningún gráfico.")
            else:
                fig = create_precise_lattice_figure(parsed_struct)
                if fig:
                    st.subheader("Gráfico del Reticulado:")
                    st.pyplot(fig)
                else:
                    st.error("No se pudo generar el gráfico (posiblemente no hay nodos suficientes después del parseo).")
    else:
        st.warning("Por favor, introduce una cláusula DAX para visualizar.")

st.sidebar.header("Acerca de")
st.sidebar.info(
    "Esta aplicación es un MVP para visualizar el 'Context Grid' de los cálculos visuales en DAX. "
    "Ayuda a entender la estructura lógica sobre la que operan dichos cálculos."
)
if not HAS_PYDOT_AND_GRAPHVIZ:
    st.sidebar.error("¡IMPORTANTE! El motor de diseño Graphviz no está disponible. Los gráficos usarán un layout alternativo.")