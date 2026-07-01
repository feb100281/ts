from .data import get_tree_data
import dash_mantine_components as dmc
from dash_iconify import DashIconify

class MainWindow:
    def __init__(self):
        self.tree_container_id = 'tree-container-id'
        
    def make_tree(self):
        df = get_tree_data()
        # Строим вложенную структуру
        tree_dict = {}  # ключ - lv1_id, значение - узел с полями value, label, children, children_map

        for row in df.itertuples():
            lv1_id = row.lv1_id
            lv2_id = row.lv2_id
            lv3_id = row.lv3_id
            lv4_id = row.lv4_id

            # Уровень 1
            if lv1_id not in tree_dict:
                tree_dict[lv1_id] = {
                    "value": lv1_id,
                    "label": row.lv1_label,
                    "children": [],
                    "children_map": {}
                }
            lv1_node = tree_dict[lv1_id]

            # Уровень 2
            if lv2_id not in lv1_node["children_map"]:
                new_node = {
                    "value": lv2_id,
                    "label": row.lv2_label,
                    "children": [],
                    "children_map": {}
                }
                lv1_node["children"].append(new_node)
                lv1_node["children_map"][lv2_id] = new_node
            lv2_node = lv1_node["children_map"][lv2_id]

            # Уровень 3
            if lv3_id not in lv2_node["children_map"]:
                new_node = {
                    "value": lv3_id,
                    "label": row.lv3_label,
                    "children": [],
                    "children_map": {}
                }
                lv2_node["children"].append(new_node)
                lv2_node["children_map"][lv3_id] = new_node
            lv3_node = lv2_node["children_map"][lv3_id]

            # Уровень 4 (лист) – проверяем, нет ли уже такого значения
            if not any(child["value"] == lv4_id for child in lv3_node["children"]):
                leaf = {"value": lv4_id, "label": row.item_label}
                lv3_node["children"].append(leaf)

        # Преобразуем словарь в список корневых узлов и удаляем служебные children_map
        def clean_node(node):
            node.pop("children_map", None)
            if "children" in node:
                for child in node["children"]:
                    clean_node(child)
            return node

        data = [clean_node(node) for node in tree_dict.values()]

        return dmc.Tree(
            id='tree-id',
            data=data,
            expandedIcon=DashIconify(icon="line-md:chevron-right-circle", width=20),
            collapsedIcon=DashIconify(icon="line-md:arrow-up-circle", width=20),
            checkboxes=True,
        )

    def layout(self):
        return dmc.Container([
            dmc.Title("Дерево номенклатур", order=1),
            dmc.Space(h=20),
            dmc.Container(
                [self.make_tree()],   # помещаем дерево в контейнер
                id=self.tree_container_id,
                fluid=True
            )
        ], fluid=True)