# Компоненты которые одинаковые для dash
import dash_mantine_components as dmc

THEME = {
        "primaryColor": "indigo",
        "defaultRadius": "lg",
        "fontFamily": "Manrope, Inter, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif",
        "components": {
            "Card": {"defaultProps": {"shadow": "sm", "padding": "md", "radius": "lg"}},
            "Badge": {"defaultProps": {"variant": "light"}},
            "Divider": {"styles": {"label": {"fontWeight": 700}}},
            "Tabs": {"styles": {"tab": {"fontWeight": 600}}},
        },
    }

class CommonComponents:
    
    
    @staticmethod
    def report_title(text = "", id=None):        
        kwargs = {}
        if id is not None:
            kwargs["id"] = id
        
        return dmc.Title(
                text,
                order=2,
                c='blue',
                **kwargs
                
                # свистоперделки ниже             
            )
    
    @staticmethod
    def report_subtitle(text = "",id=None):        
        kwargs = {}
        if id is not None:
            kwargs["id"] = id
        return dmc.Title(
                text,
                order=4,
                c='teal',
                **kwargs
                
                # свистоперделки ниже          
            )
    
    @staticmethod
    def help_hover(text=""):
        pass
        
    @staticmethod  
    def select(data=[],id=None):
        kwargs = {}
        if id is not None:
            kwargs["id"] = id
        pass
    
    @staticmethod
    def multiselect(left_icon=None,data=[]):
        kwargs = {}
        if id is not None:
            kwargs["id"] = id
        pass