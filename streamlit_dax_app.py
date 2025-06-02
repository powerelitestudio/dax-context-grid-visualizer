import streamlit as st
import re
import networkx as nx
import matplotlib.pyplot as plt
import matplotlib # Necesario para configurar el backend

# Configurar Matplotlib para que no intente usar un backend interactivo en el servidor
try:
    matplotlib.use('Agg')
except Exception as e:
    print(f"Advertencia al configurar matplotlib.use('Agg'): {e}")

# Variable global para el estado de Graphviz/Pydot
HAS_PYDOT_AND_GRAPHVIZ = False
try:
    import pydotplus 
    import pydot 
    if pydotplus.find_graphviz() and pydotplus.find_graphviz().get('dot'):
        from networkx.drawing.nx_pydot import graphviz_layout
        HAS_PYDOT_AND_GRAPHVIZ = True
except ImportError:
    HAS_PYDOT_AND_GRAPHVIZ = False
except Exception:
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
            from networkx.drawing.nx_pydot import graphviz_layout 
            pos = graphviz_layout(G, prog='dot')
            layout_engine_used = "Graphviz 'dot' Layout ✨"
        except Exception as e_layout:
            st.error(f"❌ Falló el intento de usar `graphviz_layout(G, prog='dot')`: {type(e_layout).__name__}: {e_layout}")
            st.warning("Se usará 'spring_layout' como alternativa debido al error anterior.")
            pos = None 
            layout_engine_used = "Spring Layout (excepción en dot)"
    
    if pos is None and G.number_of_nodes() > 0: 
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
        if num_nodes > 1 and pos is None:
             st.error("No se pudo calcular la posición de los nodos para el gráfico.")
        return None 
    
    fig.tight_layout() 
    return fig

# --- Interfaz de Usuario con Streamlit ---
st.set_page_config(page_title="Visualizador de Reticulado DAX", layout="wide")

# MODIFICACIÓN: AÑADIR LOGO CON NUEVO TAMAÑO
st.image("https://powerelite.studio/wp-content/uploads/2025/05/LogoPowerEliteSquareWithName.png", width=100) # Logo más pequeño

# MODIFICACIÓN DEL TÍTULO PRINCIPAL:
st.title("Visualizador del Reticulado en DAX")

# MODIFICACIÓN DEL TEXTO INTRODUCTORIO:
st.markdown("""
Esta herramienta te ayuda a visualizar la estructura jerárquica (el "reticulado") 
definida por la Tabla Virtual en conjunto con la cláusula `WITH VISUAL SHAPE` de DAX.
""") # Se eliminó "Pega tu código abajo."

# --- Barra Lateral (Sidebar) ---
st.sidebar.header("Acerca de")
st.sidebar.info(
    "Esta aplicación es un MVP de la app 'Context Grid' de Power Elite Studio, "
    "cuya funcionalidad actual es poder visualizar el 'Retiulado' o 'Lattice' "
    "de la Tabla Virtual para Cálculos Visuales DAX, esto para ayudar a entender "
    "la estructura lógica sobre la que operan dichos cálculos."
)

st.sidebar.subheader("¿Quieres aprender Lenguaje DAX?")
# MODIFICACIÓN: AÑADIR FONDO DE COLOR AL TEXTO DEL CURSO
curso_dax_texto = (
    "El curso 'Magíster en Lenguaje DAX' de Power Elite Studio es curso/capacitación "
    "número uno en español para dominar el Lenguaje DAX de básico a experto y estar "
    "en constante actualización: "
    "[clic aquí para conocer más](https://powerelite.studio/cursos/magister-en-lenguaje-dax/)."
)
st.sidebar.markdown(
    f'<div style="background-color: #FFFACD; padding: 10px; border-radius: 5px;">{curso_dax_texto}</div>',
    unsafe_allow_html=True
)

st.sidebar.subheader("Autor")
st.sidebar.markdown(
    "Microsoft MVP Miguel Caballero, [www.powerelite.studio](https://www.powerelite.studio)"
)

# --- Fin de la Barra Lateral (Sidebar) ---


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
             st.warning("⚠️ Layout jerárquico (Graphviz) no disponible o no detectado. Se usará un layout alternativo. Asegúrate de que Graphviz esté instalado y en el PATH del sistema donde se ejecuta esta app si es localmente, o que esté incluido en `packages.txt` si se despliega en Streamlit Cloud.")
             
        with st.spinner("Analizando DAX y generando gráfico... ⏳"):
            parsed_struct = parse_visual_shape(dax_clause_input)
            
            st.subheader("Estructura Parseada (para referencia):")
            st.json(parsed_struct)

            if not parsed_struct.get("ROWS") and not parsed_struct.get("COLUMNS"):
                st.warning("La entrada no definió campos para ROWS ni para COLUMNS. No se puede generar el gráfico principal del reticulado.")
            elif not parsed_struct.get("ROWS") or not parsed_struct.get("COLUMNS"):
                 st.warning("Se requieren campos tanto en ROWS como en COLUMNS para el reticulado completo de intersecciones. Se mostrará la jerarquía de un solo eje si está definida.")
                 fig = create_precise_lattice_figure(parsed_struct)
                 if fig:
                     st.subheader("Gráfico del Reticulado (parcial):")
                     st.pyplot(fig)
                 else:
                     st.info("No se generó ningún gráfico (posiblemente solo nodo raíz).")
            else:
                fig = create_precise_lattice_figure(parsed_struct)
                if fig:
                    st.subheader("Gráfico del Reticulado:")
                    st.pyplot(fig)
                else:
                    st.error("No se pudo generar la figura del gráfico.")
    else:
        st.warning("Por favor, introduce una cláusula DAX para visualizar.")
