from django.urls import reverse_lazy

""" 
Данные для сеттинга


WACC -> admin:macro_wacc_changelist
Inflation -> admin:macro_inflation_changelist
KeyRate -> admin:macro_keyrate_changelist
CalendarExceptions -> admin:macro_calendarexceptions_changelist
TaxesList -> admin:macro_taxeslist_changelist
TaxRates -> admin:macro_taxrates_changelist
CurrencyRate -> admin:macro_currencyrate_changelist
MarketRegion -> admin:macro_marketregion_changelist
MarketDistrict -> admin:macro_marketdistrict_changelist
OfficeClass -> admin:macro_officeclass_changelist
MarketSource -> admin:macro_marketsource_changelist
PropertyType -> admin:macro_propertytype_changelist
MarketListing -> admin:macro_marketlisting_changelist
MarketListingObservation -> admin:macro_marketlistingobservation_changelist
MarketSnapshot -> admin:macro_marketsnapshot_changelist
Owners -> admin:corporate_owners_changelist
Bank -> admin:corporate_bank_changelist
COAFn -> admin:corporate_coafn_changelist
COA -> admin:corporate_coa_changelist
CfItems -> admin:corporate_cfitems_changelist
ConditionsCOA -> admin:corporate_conditionscoa_changelist
BankAccount -> admin:corporate_bankaccount_changelist
Countries -> admin:corporate_countries_changelist
Subconto -> admin:corporate_subconto_changelist
Gr -> admin:counterparties_gr_changelist
Counterparty -> admin:counterparties_counterparty_changelist
GlyphKind -> admin:counterparties_glyphkind_changelist
Glyph -> admin:counterparties_glyph_changelist
Tenant -> admin:counterparties_tenant_changelist
CounterpartyFinancialYear -> admin:counterparties_counterpartyfinancialyear_changelist
ContractsTitle -> admin:contracts_contractstitle_changelist
Contracts -> admin:contracts_contracts_changelist
ContractItems -> admin:contracts_contractitems_changelist
AccountingMethod -> admin:contracts_accountingmethod_changelist
AccuralFn -> admin:contracts_accuralfn_changelist
Conditions -> admin:contracts_conditions_changelist
ContractFiles -> admin:contracts_contractfiles_changelist
CfItemAuto -> admin:contracts_cfitemauto_changelist
BankStatements -> admin:treasury_bankstatements_changelist
CfData -> admin:treasury_cfdata_changelist
CfSplits -> admin:treasury_cfsplits_changelist
ContractsRexex -> admin:treasury_contractsrexex_changelist
ProductGroup -> admin:sales_productgroup_changelist
Category -> admin:sales_category_changelist
Brand -> admin:sales_brand_changelist
SellerSKU -> admin:sales_sellersku_changelist
Barcode -> admin:sales_barcode_changelist
Size -> admin:sales_size_changelist
Product -> admin:sales_product_changelist
ProductData -> admin:sales_productdata_changelist
WBDocument -> admin:sales_wbdocument_changelist
NMs -> admin:sales_nms_changelist
MVSalesProductData -> admin:sales_mvsalesproductdata_changelist
Warehouse -> admin:sales_warehouse_changelist
Order -> admin:sales_order_changelist
SalesData -> admin:sales_salesdata_changelist
MVSalesDaily -> admin:sales_mvsalesdaily_changelist
MVDataMartProduct -> admin:sales_mvdatamartproduct_changelist
Manual -> admin:grossbook_manual_changelist
AnalysisScript -> admin:accounting_analysis_analysisscript_changelist
AccountingAnalysis -> admin:accounting_analysis_accountinganalysis_changelist
AccountingMetric -> admin:accounting_analysis_accountingmetric_changelist
TechSize -> admin:wb_techsize_changelist
Subject -> admin:wb_subject_changelist
Product -> admin:wb_product_changelist
BudgetVersion -> admin:budget_budgetversion_changelist
Gl -> admin:budget_gl_changelist
WbCardRaw -> admin:cards_wbcardraw_changelist
WbSizes -> admin:cards_wbsizes_changelist
WbBarcodes -> admin:cards_wbbarcodes_changelist
Lot -> admin:cards_lot_changelist
LotFile -> admin:cards_lotfile_changelist
UpdDocument -> admin:cards_upddocument_changelist
UpdDocumentFile -> admin:cards_upddocumentfile_changelist
WbProduct -> admin:cards_wbproduct_changelist
UPDData -> admin:cards_upddata_changelist
USK -> admin:cards_usk_changelist
UskUpd -> admin:cards_uskupd_changelist
WODashboard -> admin:cards_wodashboard_changelist
Lot -> admin:inventories_lot_changelist
Delivery -> admin:inventories_delivery_changelist
LotFile -> admin:inventories_lotfile_changelist
DeliveryFile -> admin:inventories_deliveryfile_changelist
SlideRegistered -> admin:reports_slideregistered_changelist
Report -> admin:reports_report_changelist
Section -> admin:reports_section_changelist
ReportConstructor -> admin:reports_reportconstructor_changelist
StatelessApp -> admin:django_plotly_dash_statelessapp_changelist
DashApp -> admin:django_plotly_dash_dashapp_changelist
LogEntry -> admin:admin_logentry_changelist
Permission -> admin:auth_permission_changelist
Group -> admin:auth_group_changelist
User -> admin:auth_user_changelist
ContentType -> admin:contenttypes_contenttype_changelist
Session -> admin:sessions_session_changelist
"""


UNFOLD_SETTINGD = {
    "SITE_TITLE": "ТРЕНДСЕТТЕР",
    "SITE_HEADER": "ТРЕНДСЕТТЕР",
    "SITE_SUBHEADER": "Финансы и операционная аналитика",
    "SITE_SYMBOL": "monitoring",
    "SHOW_HISTORY": True,
    "SHOW_VIEW_ON_SITE": False,
    "SHOW_BACK_BUTTON": True,
    "BORDER_RADIUS": "10px",
    "SIDEBAR": {
        "show_search": True,
        "show_all_applications": True,
        "navigation": [
            {
                "title": "Навигация",
                "separator": True,
                "collapsible": True,
                "items": [
                    {
                        "title": "Центр отчетов",
                        "icon": "analytics",
                        "link": reverse_lazy("admin:reports_report_changelist"),
                    },
                    {
                        "title": "Компания",
                        "icon": "business_center",
                        "link": reverse_lazy("admin:corporate_owners_changelist"),
                    },
                    
                ],
            }
        ],
    },
    "TABS": [
        {
            "models": ["reports.report", "reports.slideregistered", "reports.section"],
            "items": [
                {
                    "title": "Отчеты",
                    "link": reverse_lazy("admin:reports_report_changelist"),
                },
                {
                    "title": "Слайды",
                    "link": reverse_lazy("admin:reports_slideregistered_changelist"),
                },
                {
                    "title": "Секции",
                    "link": reverse_lazy("admin:reports_section_changelist"),
                },
            ],
        },
        {
            "models": ["corporate.owners", "corporate.bank", "corporate.bankaccount, corporate.countries"],
            "items": [
                {
                    "title": "Компания",
                    "link": reverse_lazy("admin:corporate_owners_changelist"),
                },
                {
                    "title": "Банки",
                    "link": reverse_lazy("admin:corporate_bank_changelist"),
                },
                {
                    "title": "Банковские счета",
                    "link": reverse_lazy("admin:corporate_bankaccount_changelist"),
                },
                {
                    "title": "География",
                    "link": reverse_lazy("admin:corporate_countries_changelist"),
                },
            ],
        },
    ],
}
