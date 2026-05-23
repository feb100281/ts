# cards/upd_app/components/header.py
import dash_mantine_components as dmc


def build_upd_header(upd):

    return dmc.Paper(
        [
            dmc.Group(
                [
                    dmc.Group(
                        [
                            dmc.Text(
                                f"УПД №{upd.number}",
                                fw=700,
                                size="24px",
                            ),

                            dmc.Badge(
                                upd.date.strftime("%d.%m.%Y"),
                                color="gray",
                                variant="outline",
                                size="md",
                                radius="sm",
                            ),
                        ],
                        gap="sm",
                        align="center",
                    ),

                    
                    dmc.Badge(
                        str(upd.counterparty),
                        color="blue",
                        variant="outline",
                        size="lg",
                        radius="sm",
                        style={
                            "fontWeight": 600,
                            "paddingLeft": "14px",
                            "paddingRight": "14px",
                        },
                    ),
                ],
                justify="space-between",
                align="center",
            ),

           
        ],
        p="md",
        radius="md",
        withBorder=True,
        mb="lg",
       
    )



