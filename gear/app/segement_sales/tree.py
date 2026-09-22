from .data import get_tree_data
import dash_mantine_components as dmc
from dash_iconify import DashIconify
from dash import dcc, html, Input, Output, State, no_update

# ---------- Функция построения дерева с динамическим id ----------
def make_tree(mode='tree', br=None, sub_id=None, tree_id='general-tree'):
    """
    mode='tree'  -> уровни 1-2 (бренд → категория)
    mode='items' -> уровни 3-4 (PID → товар)
    """
    # df = get_tree_data(subject_id=sub_id, brand=br)
    tree_dict = {}
    # print(df)

    # Поля в зависимости от режима
    if mode == 'tree':
        df = get_tree_data(subject_id=sub_id, brand=br)
        level1_field = 'lv1_id'
        level2_field = 'lv2_id'
        label1_field = 'lv1_label'
        label2_field = 'lv2_label'
        
    else:
        df = get_tree_data(subject_id=sub_id, brand=br)
        level1_field = 'lv3_id'
        level2_field = 'lv4_id'
        label1_field = 'lv3_label'
        label2_field = 'item_label'
        

    for row in df.itertuples():
        lv1_val = getattr(row, level1_field)
        lv2_val = getattr(row, level2_field)
        lv1_label = getattr(row, label1_field)
        lv2_label = getattr(row, label2_field)

        if lv1_val not in tree_dict:
            tree_dict[lv1_val] = {
                "value": lv1_val,
                "label": lv1_label,
                "children": [],
                "children_map": {}
            }
        lv1_node = tree_dict[lv1_val]

        if lv2_val not in lv1_node["children_map"]:
            leaf = {"value": lv2_val, "label": lv2_label}
            lv1_node["children"].append(leaf)
            lv1_node["children_map"][lv2_val] = leaf

    def clean(node):
        node.pop("children_map", None)
        for child in node.get("children", []):
            clean(child)
        return node

    data = [clean(node) for node in tree_dict.values()]
    # print(data)

    return dmc.Tree(
        id=tree_id,  # <-- уникальный id
        data=data,
        className="compact-tree",
        expandedIcon=DashIconify(icon="line-md:chevron-right-circle", width=20),
        collapsedIcon=DashIconify(icon="line-md:arrow-up-circle", width=20),
        checkboxes=True,
    )

# ---------- Содержимое Drawer ----------
def make_drawer_content(brand, subject_id):
    return dmc.Container(
        [
        make_tree(mode='items', br=brand, sub_id=subject_id, tree_id='item-tree')
    ], fluid=True,
        )

# ---------- Класс MainWindow ----------
class MainWindow:
    def __init__(self):
        self.tree_container_id = 'tree-container-id'
        self.item_drawer_id = 'item-drawer-id'   # исправил опечатку drawer

    def layout(self):
        return dmc.Container([
            dmc.Title("Дерево номенклатур", order=1),
            dmc.Space(h=20),
            dmc.Text('Выберите категорию', id='info-text'),
            dmc.Drawer(
                children=[
                    dmc.Container(id='side-tree')
                    ],                       # будет заменено в callback
                position="right",
                title='Заголовок',
                opened=False,
                id=self.item_drawer_id,
                size='65%'
            ),
            dmc.Container(
                [make_tree(tree_id='general-tree')],  # основное дерево
                id=self.tree_container_id,
                fluid=True
            )
        ], fluid=True)

    def register_callbacks(self,app):
        # 1. Ограничение одиночного выбора
        @app.callback(
            Output('general-tree', 'checked'),
            Input('general-tree', 'checked')
        )
        def enforce_single_selection(checked_values):
            if checked_values and len(checked_values) > 1:
                return [checked_values[-1]]
            return checked_values

        # 2. Открытие Drawer с содержимым
        @app.callback(
            Output(self.item_drawer_id, 'opened'),
            Output(self.item_drawer_id, 'title'),
            Output('side-tree', 'children'),
            Input('general-tree', 'checked'),
            prevent_initial_call=True
        )
        def open_drawer(checked_values):
            print("Выбрано:", checked_values)  # отладка
            if checked_values:
                selected = checked_values[0]
                parts = str(selected).split('_')
                # Формат lv2_id: "2_subjectId_brand"
                if len(parts) >= 3:
                    subject_id = int(parts[1])
                    brand = parts[2]
                    print(subject_id, brand)
                    # Возвращаем: открыть, заголовок, содержимое
                    return (
                        True,
                        f"Бренд: {brand}, Категория: {subject_id}",
                        make_tree(mode='items', br=brand, sub_id=int(subject_id), tree_id='item-tree')
                    )
            # Если ничего не выбрано – ничего не меняем
            return no_update, no_update, no_update


