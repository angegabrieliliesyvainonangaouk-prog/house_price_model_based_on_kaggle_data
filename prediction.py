import pickle
import numpy as np
from pathlib import Path
from typing import Dict, Any, List

MODEL_DIR = Path(__file__).parent / "modele.ml"
DTYPE = np.float32

FEATURE_NAMES = [
    "MSSubClass", "LotFrontage", "LotArea", "LotShape", "LandContour",
    "Utilities", "LandSlope", "OverallQual", "OverallCond", "YearBuilt",
    "YearRemodAdd", "MasVnrArea", "ExterQual", "ExterCond", "BsmtQual",
    "BsmtCond", "BsmtExposure", "BsmtFinType1", "BsmtFinType2", "BsmtUnfSF",
    "TotalBsmtSF", "HeatingQC", "CentralAir", "LowQualFinSF", "GrLivArea",
    "BedroomAbvGr", "KitchenAbvGr", "KitchenQual", "TotRmsAbvGrd", "Functional",
    "Fireplaces", "FireplaceQu", "GarageFinish", "GarageQual", "GarageCond",
    "PavedDrive", "WoodDeckSF", "OpenPorchSF", "EnclosedPorch", "3SsnPorch",
    "ScreenPorch", "PoolArea", "PoolQC", "Fence", "MiscVal",
    "YearRemodAddp", "GarageYrBltp", "BsmtFinSF", "TotalFlrsf", "Totalbath",
    "GarageArePerCar",
    "MSZoning_C (all)", "MSZoning_FV", "MSZoning_RH", "MSZoning_RL", "MSZoning_RM",
    "Street_Grvl", "Street_Pave",
    "Alley_Grvl", "Alley_Pave", "Alley_unknown",
    "LotConfig_Corner", "LotConfig_CulDSac", "LotConfig_FR2", "LotConfig_FR3", "LotConfig_Inside",
    "Condition1_Artery", "Condition1_Feedr", "Condition1_Norm", "Condition1_PosA", "Condition1_PosN",
    "Condition1_RRAe", "Condition1_RRAn", "Condition1_RRNe", "Condition1_RRNn",
    "Condition2_Artery", "Condition2_Feedr", "Condition2_Norm", "Condition2_PosA", "Condition2_PosN",
    "Condition2_RRAe", "Condition2_RRAn", "Condition2_RRNn",
    "BldgType_1Fam", "BldgType_2fmCon", "BldgType_Duplex", "BldgType_Twnhs", "BldgType_TwnhsE",
    "HouseStyle_1.5Fin", "HouseStyle_1.5Unf", "HouseStyle_1Story", "HouseStyle_2.5Fin",
    "HouseStyle_2.5Unf", "HouseStyle_2Story", "HouseStyle_SFoyer", "HouseStyle_SLvl",
    "RoofStyle_Flat", "RoofStyle_Gable", "RoofStyle_Gambrel", "RoofStyle_Hip",
    "RoofStyle_Mansard", "RoofStyle_Shed",
    "RoofMatl_ClyTile", "RoofMatl_CompShg", "RoofMatl_Membran", "RoofMatl_Metal",
    "RoofMatl_Roll", "RoofMatl_Tar&Grv", "RoofMatl_WdShake", "RoofMatl_WdShngl",
    "MasVnrType_BrkCmn", "MasVnrType_BrkFace", "MasVnrType_Stone", "MasVnrType_unknown",
    "Foundation_BrkTil", "Foundation_CBlock", "Foundation_PConc", "Foundation_Slab",
    "Foundation_Stone", "Foundation_Wood",
    "Heating_Floor", "Heating_GasA", "Heating_GasW", "Heating_Grav", "Heating_OthW", "Heating_Wall",
    "Electrical_FuseA", "Electrical_FuseF", "Electrical_FuseP", "Electrical_Mix",
    "Electrical_SBrkr", "Electrical_unknown",
    "GarageType_2Types", "GarageType_Attchd", "GarageType_Basment", "GarageType_BuiltIn",
    "GarageType_CarPort", "GarageType_Detchd", "GarageType_unknown",
    "MiscFeature_Gar2", "MiscFeature_Othr", "MiscFeature_Shed", "MiscFeature_TenC",
    "MiscFeature_unknown",
    "SaleType_COD", "SaleType_CWD", "SaleType_Con", "SaleType_ConLD", "SaleType_ConLI",
    "SaleType_ConLw", "SaleType_New", "SaleType_Oth", "SaleType_WD",
    "SaleCondition_Abnorml", "SaleCondition_AdjLand", "SaleCondition_Alloca",
    "SaleCondition_Family", "SaleCondition_Normal", "SaleCondition_Partial",
    "Exterior_ta",
    "Neighborhood_ta",
]

FEATURE_SET = frozenset(FEATURE_NAMES)
FEATURE_COUNT = len(FEATURE_NAMES)
RAW_COUNT = 51
BINARY_COUNT = FEATURE_COUNT - RAW_COUNT

ONE_HOT_GROUPS = {
    "MSZoning": ("MSZoning_C (all)", "MSZoning_FV", "MSZoning_RH", "MSZoning_RL", "MSZoning_RM"),
    "Street": ("Street_Grvl", "Street_Pave"),
    "Alley": ("Alley_Grvl", "Alley_Pave", "Alley_unknown"),
    "LotConfig": ("LotConfig_Corner", "LotConfig_CulDSac", "LotConfig_FR2", "LotConfig_FR3", "LotConfig_Inside"),
    "Condition1": ("Condition1_Artery", "Condition1_Feedr", "Condition1_Norm", "Condition1_PosA",
                    "Condition1_PosN", "Condition1_RRAe", "Condition1_RRAn", "Condition1_RRNe", "Condition1_RRNn"),
    "Condition2": ("Condition2_Artery", "Condition2_Feedr", "Condition2_Norm", "Condition2_PosA",
                    "Condition2_PosN", "Condition2_RRAe", "Condition2_RRAn", "Condition2_RRNn"),
    "BldgType": ("BldgType_1Fam", "BldgType_2fmCon", "BldgType_Duplex", "BldgType_Twnhs", "BldgType_TwnhsE"),
    "HouseStyle": ("HouseStyle_1.5Fin", "HouseStyle_1.5Unf", "HouseStyle_1Story", "HouseStyle_2.5Fin",
                    "HouseStyle_2.5Unf", "HouseStyle_2Story", "HouseStyle_SFoyer", "HouseStyle_SLvl"),
    "RoofStyle": ("RoofStyle_Flat", "RoofStyle_Gable", "RoofStyle_Gambrel", "RoofStyle_Hip",
                   "RoofStyle_Mansard", "RoofStyle_Shed"),
    "RoofMatl": ("RoofMatl_ClyTile", "RoofMatl_CompShg", "RoofMatl_Membran", "RoofMatl_Metal",
                  "RoofMatl_Roll", "RoofMatl_Tar&Grv", "RoofMatl_WdShake", "RoofMatl_WdShngl"),
    "MasVnrType": ("MasVnrType_BrkCmn", "MasVnrType_BrkFace", "MasVnrType_Stone", "MasVnrType_unknown"),
    "Foundation": ("Foundation_BrkTil", "Foundation_CBlock", "Foundation_PConc", "Foundation_Slab",
                    "Foundation_Stone", "Foundation_Wood"),
    "Heating": ("Heating_Floor", "Heating_GasA", "Heating_GasW", "Heating_Grav", "Heating_OthW", "Heating_Wall"),
    "Electrical": ("Electrical_FuseA", "Electrical_FuseF", "Electrical_FuseP", "Electrical_Mix",
                    "Electrical_SBrkr", "Electrical_unknown"),
    "GarageType": ("GarageType_2Types", "GarageType_Attchd", "GarageType_Basment", "GarageType_BuiltIn",
                    "GarageType_CarPort", "GarageType_Detchd", "GarageType_unknown"),
    "MiscFeature": ("MiscFeature_Gar2", "MiscFeature_Othr", "MiscFeature_Shed", "MiscFeature_TenC",
                     "MiscFeature_unknown"),
    "SaleType": ("SaleType_COD", "SaleType_CWD", "SaleType_Con", "SaleType_ConLD", "SaleType_ConLI",
                  "SaleType_ConLw", "SaleType_New", "SaleType_Oth", "SaleType_WD"),
    "SaleCondition": ("SaleCondition_Abnorml", "SaleCondition_AdjLand", "SaleCondition_Alloca",
                       "SaleCondition_Family", "SaleCondition_Normal", "SaleCondition_Partial"),
    "Exterior": ("Exterior_ta",),
    "Neighborhood": ("Neighborhood_ta",),
}

ONE_HOT_DEFAULTS = {
    "MSZoning": "MSZoning_RL", "Street": "Street_Pave", "Alley": "Alley_unknown",
    "LotConfig": "LotConfig_Inside", "Condition1": "Condition1_Norm", "Condition2": "Condition2_Norm",
    "BldgType": "BldgType_1Fam", "HouseStyle": "HouseStyle_1Story", "RoofStyle": "RoofStyle_Gable",
    "RoofMatl": "RoofMatl_CompShg", "MasVnrType": "MasVnrType_unknown",
    "Foundation": "Foundation_PConc", "Heating": "Heating_GasA", "Electrical": "Electrical_SBrkr",
    "GarageType": "GarageType_Attchd", "MiscFeature": "MiscFeature_unknown",
    "SaleType": "SaleType_WD", "SaleCondition": "SaleCondition_Normal",
    "Exterior": "Exterior_ta", "Neighborhood": "Neighborhood_ta",
}

_QUAL_MAP = {"Ex": 5.0, "Gd": 4.0, "TA": 3.0, "Fa": 2.0, "Po": 1.0, "NA": 0.0}
_FINISH_MAP = {"Fin": 4.0, "RFn": 3.0, "BL": 2.0, "Unf": 1.0, "NA": 0.0, "No": 0.0}
_EXPOSURE_MAP = {"Gd": 4.0, "Av": 3.0, "Mn": 2.0, "No": 1.0, "NA": 0.0}
_FENCE_MAP = {"GdPrv": 4.0, "MnPrv": 3.0, "GdWo": 2.0, "MnWw": 1.0, "NA": 0.0}
_GARAGE_FINISH_MAP = {"Fin": 3.0, "RFn": 2.0, "Unf": 1.0, "NA": 0.0}
_DRIVE_MAP = {"Y": 2.0, "P": 1.0, "N": 0.0}
_YESNO_MAP = {"Y": 1.0, "N": 0.0}
_FUNC_MAP = {"Typ": 7.0, "Min1": 6.0, "Min2": 5.0, "Mod": 4.0, "Maj1": 3.0, "Maj2": 2.0, "Sev": 1.0, "Sal": 0.0}
_SHAPE_MAP = {"Reg": 3.0, "IR1": 2.0, "IR2": 1.0, "IR3": 0.0}
_CONTOUR_MAP = {"Lvl": 3.0, "Bnk": 2.0, "HLS": 1.0, "Low": 0.0}
_UTIL_MAP = {"AllPub": 2.0, "NoSewr": 1.0, "NoSeWa": 0.0}
_SLOPE_MAP = {"Gtl": 2.0, "Mod": 1.0, "Sev": 0.0}

_STRING_CAT_RAW_INDICES = {
    3: _SHAPE_MAP, 4: _CONTOUR_MAP, 5: _UTIL_MAP, 6: _SLOPE_MAP,
    12: _QUAL_MAP, 13: _QUAL_MAP, 14: _QUAL_MAP, 15: _QUAL_MAP,
    16: _EXPOSURE_MAP, 17: _FINISH_MAP, 18: _FINISH_MAP,
    21: _QUAL_MAP, 22: _YESNO_MAP, 27: _QUAL_MAP,
    29: _FUNC_MAP, 31: _QUAL_MAP, 32: _GARAGE_FINISH_MAP,
    33: _QUAL_MAP, 34: _QUAL_MAP, 35: _DRIVE_MAP,
    42: _QUAL_MAP, 43: _FENCE_MAP,
}

_DEFAULTS_RAW = np.array([
    60, 60.0, 10000.0, 3.0, 3.0, 2.0, 2.0,
    5, 5, 1970, 1980, 0.0,
    3.0, 3.0, 3.0, 3.0, 1.0, 1.0, 1.0,
    400.0, 800.0, 3.0, 1.0, 0.0, 1500.0,
    3, 1, 3.0, 6, 7.0,
    0, 0.0, 1.0, 3.0, 3.0, 2.0,
    0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
    0.0, 0.0, 400.0, 1.5, 1.5, 0.0,
], dtype=DTYPE)

_DEFAULTS_BINARY = np.zeros(BINARY_COUNT, dtype=DTYPE)
for group, cols in ONE_HOT_GROUPS.items():
    default_col = ONE_HOT_DEFAULTS[group]
    for i, name in enumerate(FEATURE_NAMES[RAW_COUNT:]):
        if name == default_col:
            _DEFAULTS_BINARY[i] = 1.0
            break

_DEFAULT_VECTOR = np.concatenate([_DEFAULTS_RAW, _DEFAULTS_BINARY]).reshape(1, -1)


class ModelLoader:
    _models = {}
    _loaded = False

    @classmethod
    def load(cls):
        if cls._loaded:
            return
        xgb_bytes = (MODEL_DIR / "xgb_model.plk").read_bytes()
        cat_bytes = (MODEL_DIR / "cat_model.plk").read_bytes()
        xgb_model = pickle.loads(xgb_bytes)
        cat_model = pickle.loads(cat_bytes)
        xgb_model.get_booster().feature_names = FEATURE_NAMES
        cat_model.set_feature_names(FEATURE_NAMES)
        cls._models["xgboost"] = xgb_model
        cls._models["catboost"] = cat_model
        cls._loaded = True

    @classmethod
    def get_model(cls, name: str):
        if not cls._loaded:
            cls.load()
        return cls._models.get(name)


def _map_str_feature(idx: int, value: str) -> float:
    mapping = _STRING_CAT_RAW_INDICES.get(idx)
    if mapping is None:
        return 0.0
    return float(mapping.get(value, 0.0))


def _build_vector(features: Dict[str, Any], defaults_raw: np.ndarray, defaults_binary: np.ndarray) -> np.ndarray:
    vec = np.empty(FEATURE_COUNT, dtype=DTYPE)
    vec[:RAW_COUNT] = defaults_raw
    vec[RAW_COUNT:] = defaults_binary

    for idx in range(RAW_COUNT):
        name = FEATURE_NAMES[idx]
        val = features.get(name)
        if val is not None and val != "":
            if idx in _STRING_CAT_RAW_INDICES:
                if isinstance(val, str):
                    vec[idx] = _map_str_feature(idx, val)
                else:
                    try:
                        vec[idx] = DTYPE(val)
                    except (ValueError, TypeError):
                        pass
            else:
                try:
                    vec[idx] = DTYPE(val)
                except (ValueError, TypeError):
                    pass

    for idx in range(RAW_COUNT, FEATURE_COUNT):
        name = FEATURE_NAMES[idx]
        val = features.get(name)
        if val is not None and val != "":
            try:
                vec[idx] = DTYPE(val)
            except (ValueError, TypeError):
                pass
            continue
        for group, cols in ONE_HOT_GROUPS.items():
            if name in cols:
                cat_val = features.get(group)
                if cat_val and isinstance(cat_val, str):
                    for ci, cn in enumerate(cols):
                        suffix = cn.replace(f"{group}_", "")
                        if suffix == f"C (all)":
                            suffix = "C (all)"
                        if suffix == cat_val:
                            vec[idx] = DTYPE(ci == cols.index(name))
                            break
                break

    return vec.reshape(1, -1)


def predict_normal(model_name: str, features: Dict[str, Any]) -> float:
    model = ModelLoader.get_model(model_name)
    if model is None:
        raise ValueError(f"Model {model_name} not found")
    vec = _build_vector(features, _DEFAULTS_RAW, _DEFAULTS_BINARY)
    pred = model.predict(vec)
    return float(pred[0])


def predict_csv(model_name: str, records: List[Dict[str, Any]]) -> List[float]:
    model = ModelLoader.get_model(model_name)
    if model is None:
        raise ValueError(f"Model {model_name} not found")
    batch = np.zeros((len(records), FEATURE_COUNT), dtype=DTYPE)
    for i, rec in enumerate(records):
        batch[i] = _build_vector(rec, _DEFAULTS_RAW, _DEFAULTS_BINARY)
    preds = model.predict(batch)
    return [float(p) for p in preds]


COLUMNS_GUIDE = [
   {"name":"MSSubClass","label_fr":"Classe du bien","desc_fr":"Type de logement selon son style et son age. Les valeurs (20 a 190) correspondent a des categories comme maison 1 etage, 2 etages, duplex, etc.","label_en":"Building Class","desc_en":"Type of dwelling based on style and age. Values (20 to 190) correspond to categories like 1-story house, 2-story, duplex, etc.","type":"select","options":["20","30","40","45","50","60","70","75","80","85","90","120","150","160","180","190"]},
   {"name":"LotFrontage","label_fr":"Facade sur rue","desc_fr":"Longueur en metres de la facade du terrain qui donne sur la rue. Plus la facade est grande, plus le terrain est large.","label_en":"Street Frontage","desc_en":"Length in feet of the lot facade facing the street. A wider frontage generally means a wider lot.","type":"number","unit":"pieds"},
   {"name":"LotArea","label_fr":"Superficie du terrain","desc_fr":"Surface totale du terrain en metres carres. Un grand terrain augmente generalement la valeur de la propriete.","label_en":"Lot Area","desc_en":"Total lot area in square feet. A larger lot generally increases the property value.","type":"number","unit":"pi2"},
   {"name":"LotShape","label_fr":"Forme du terrain","desc_fr":"Forme generale du terrain. Un terrain regulier est plus facile a amenager et constructible.","label_en":"Lot Shape","desc_en":"General shape of the lot. A regular lot is easier to develop and build on.","type":"select","options":["Reg","IR1","IR2","IR3"]},
   {"name":"LandContour","label_fr":"Relief du terrain","desc_fr":"Niveau de pente du terrain. Un terrain plat est ideal pour la construction.","label_en":"Land Contour","desc_en":"Levelness of the property. A flat lot is ideal for construction.","type":"select","options":["Lvl","Bnk","HLS","Low"]},
   {"name":"Utilities","label_fr":"Services publics disponibles","desc_fr":"Types de services publics raccordes (electricite, gaz, eau, egouts). Plus il y a de services, mieux c'est.","label_en":"Utilities","desc_en":"Types of public utilities connected (electricity, gas, water, sewer). More utilities means better.","type":"select","options":["AllPub","NoSewr","NoSeWa"]},
   {"name":"LandSlope","label_fr":"Pente du terrain","desc_fr":"Inclinaison naturelle du terrain. Les pentes douces sont preferees pour la construction.","label_en":"Land Slope","desc_en":"Natural inclination of the land. Gentle slopes are preferred for construction.","type":"select","options":["Gtl","Mod","Sev"]},
   {"name":"OverallQual","label_fr":"Qualite generale","desc_fr":"Note globale sur la qualite des materiaux et de la finition de la maison. De 1 (tres mauvais) a 10 (excellent). C'est le critere le plus important pour le prix.","label_en":"Overall Quality","desc_en":"Overall material and finish quality rating. From 1 (very poor) to 10 (excellent). This is the most important factor for price.","type":"number","min":1,"max":10,"step":1},
   {"name":"OverallCond","label_fr":"Etat general","desc_fr":"Note sur l'etat general de la maison. De 1 (tres mauvais) a 10 (excellent). Prend en compte l'usure et l'entretien.","label_en":"Overall Condition","desc_en":"Overall condition rating. From 1 (very poor) to 10 (excellent). Accounts for wear and maintenance.","type":"number","min":1,"max":10,"step":1},
   {"name":"YearBuilt","label_fr":"Annee de construction","desc_fr":"Annee de construction originale de la maison. Les maisons plus recentes ont generalement une valeur plus elevee.","label_en":"Year Built","desc_en":"Original construction year. More recent homes generally have higher values.","type":"number","min":1800,"max":2026,"step":1},
   {"name":"YearRemodAdd","label_fr":"Annee de renovation","desc_fr":"Annee de la derniere renovation ou agrandissement. Identique a l'annee de construction si jamais renove.","label_en":"Year Remodeled","desc_en":"Year of last renovation or addition. Same as year built if never remodeled.","type":"number","min":1800,"max":2026,"step":1},
   {"name":"MasVnrArea","label_fr":"Surface du parement","desc_fr":"Superficie en metres carres du parement en maconnerie (brique, pierre) sur l'exterieur de la maison.","label_en":"Masonry Veneer Area","desc_en":"Masonry veneer area in square feet (brick, stone) on the exterior of the house.","type":"number","unit":"pi2"},
   {"name":"ExterQual","label_fr":"Qualite de l'exterieur","desc_fr":"Qualite des materiaux utilises pour le revetement exterieur de la maison.","label_en":"Exterior Quality","desc_en":"Quality of materials used for the exterior finish of the house.","type":"select","options":["Ex","Gd","TA","Fa","Po"]},
   {"name":"ExterCond","label_fr":"Etat de l'exterieur","desc_fr":"Etat actuel du revetement exterieur. Prend en compte l'usure et les degâts.","label_en":"Exterior Condition","desc_en":"Current condition of the exterior finish. Accounts for wear and damage.","type":"select","options":["Ex","Gd","TA","Fa","Po"]},
   {"name":"BsmtQual","label_fr":"Qualite du sous-sol","desc_fr":"Hauteur du sous-sol. Excellent = plus de 2m50, Bon = 2m30-2m50, Typique = 2m-2m30, etc.","label_en":"Basement Quality","desc_en":"Basement height. Excellent = over 8ft, Good = 7-8ft, Typical = 6-7ft, etc.","type":"select","options":["Ex","Gd","TA","Fa","Po","NA"]},
   {"name":"BsmtCond","label_fr":"Etat du sous-sol","desc_fr":"Etat general du sous-sol. Typique = legerement humide (normal), Mauvais = fissures ou infiltrations.","label_en":"Basement Condition","desc_en":"General basement condition. Typical = slightly damp (normal), Poor = cracks or leaks.","type":"select","options":["Ex","Gd","TA","Fa","Po","NA"]},
   {"name":"BsmtExposure","label_fr":"Exposition du sous-sol","desc_fr":"Presence de murs donnes sur l'exterieur ou de sortie de plain-pied au sous-sol (walk-out).","label_en":"Basement Exposure","desc_en":"Walkout or garden-level basement walls. Good = exposure to daylight, None = below grade only.","type":"select","options":["Gd","Av","Mn","No","NA"]},
   {"name":"BsmtFinType1","label_fr":"Type d'amenagement du sous-sol","desc_fr":"Type de finition de la partie principale du sous-sol. Va de 'Non fini' a 'Bel espace de vie'.","label_en":"Basement Finish Type 1","desc_en":"Type of finish on the main basement area. Ranges from 'Unfinished' to 'Good Living Quarters'.","type":"select","options":["GLQ","ALQ","BLQ","Rec","LwQ","Unf","NA"]},
   {"name":"BsmtFinType2","label_fr":"2e type d'amenagement du sous-sol","desc_fr":"Type de finition d'une seconde zone du sous-sol (si plusieurs types d'amenagement).","label_en":"Basement Finish Type 2","desc_en":"Type of finish on a second basement area (if multiple finish types).","type":"select","options":["GLQ","ALQ","BLQ","Rec","LwQ","Unf","NA"]},
   {"name":"BsmtUnfSF","label_fr":"Surface non finie du sous-sol","desc_fr":"Superficie en metres carres du sous-sol qui n'est pas amenagee.","label_en":"Unfinished Basement Area","desc_en":"Unfinished basement area in square feet.","type":"number","unit":"pi2"},
   {"name":"TotalBsmtSF","label_fr":"Surface totale du sous-sol","desc_fr":"Superficie totale du sous-sol en metres carres, fini et non fini compris.","label_en":"Total Basement Area","desc_en":"Total basement area in square feet, including finished and unfinished.","type":"number","unit":"pi2"},
   {"name":"HeatingQC","label_fr":"Qualite du chauffage","desc_fr":"Qualite et etat du systeme de chauffage.","label_en":"Heating Quality","desc_en":"Quality and condition of the heating system.","type":"select","options":["Ex","Gd","TA","Fa","Po"]},
   {"name":"CentralAir","label_fr":"Climatisation centrale","desc_fr":"Presence d'un systeme de climatisation centrale dans la maison.","label_en":"Central Air Conditioning","desc_en":"Presence of central air conditioning in the house.","type":"select","options":["Y","N"]},
   {"name":"LowQualFinSF","label_fr":"Surface de faible qualite","desc_fr":"Superficie des pieces finies de faible qualite (tous etages confondus).","label_en":"Low Quality Finished Area","desc_en":"Low quality finished area across all floors.","type":"number","unit":"pi2"},
   {"name":"GrLivArea","label_fr":"Surface habitable","desc_fr":"Superficie totale des pieces a vivre au-dessus du sol (hors sous-sol). C'est la surface habitable principale.","label_en":"Above Grade Living Area","desc_en":"Total above grade living area in square feet. This is the main living space.","type":"number","unit":"pi2"},
   {"name":"BedroomAbvGr","label_fr":"Chambres","desc_fr":"Nombre de chambres a coucher au-dessus du sol (ne compte pas les chambres au sous-sol).","label_en":"Bedrooms Above Grade","desc_en":"Number of bedrooms above grade (does not count basement bedrooms).","type":"number","min":0,"max":20,"step":1},
   {"name":"KitchenAbvGr","label_fr":"Cuisines","desc_fr":"Nombre de cuisines au-dessus du sol.","label_en":"Kitchens Above Grade","desc_en":"Number of kitchens above grade.","type":"number","min":0,"max":10,"step":1},
   {"name":"KitchenQual","label_fr":"Qualite de la cuisine","desc_fr":"Qualite de la cuisine et de ses equipements. Excellent, Bon, Moyen, Faible ou Mauvais.","label_en":"Kitchen Quality","desc_en":"Quality of the kitchen and its appliances. Excellent, Good, Typical, Fair, or Poor.","type":"select","options":["Ex","Gd","TA","Fa","Po"]},
   {"name":"TotRmsAbvGrd","label_fr":"Nombre total de pieces","desc_fr":"Nombre total de pieces au-dessus du sol (salle de bains non comprises).","label_en":"Total Rooms Above Grade","desc_en":"Total number of rooms above grade (bathrooms not included).","type":"number","min":1,"max":50,"step":1},
   {"name":"Functional","label_fr":"Fonctionnalite","desc_fr":"Niveau de fonctionnalite de la maison. Typique = tout est normal. Les autres valeurs indiquent des defauts.","label_en":"Functionality","desc_en":"Home functionality level. Typical = all normal. Other values indicate deficiencies.","type":"select","options":["Typ","Min1","Min2","Mod","Maj1","Maj2","Sev","Sal"]},
   {"name":"Fireplaces","label_fr":"Cheminees","desc_fr":"Nombre de cheminees dans la maison.","label_en":"Fireplaces","desc_en":"Number of fireplaces in the house.","type":"number","min":0,"max":10,"step":1},
   {"name":"FireplaceQu","label_fr":"Qualite des cheminees","desc_fr":"Qualite de la ou des cheminees.","label_en":"Fireplace Quality","desc_en":"Quality of the fireplace(s).","type":"select","options":["Ex","Gd","TA","Fa","Po","NA"]},
   {"name":"GarageFinish","label_fr":"Finition du garage","desc_fr":"Type de finition interieure du garage. Fini = murs et sol peints/amenages, Brut = murs nus.","label_en":"Garage Finish","desc_en":"Interior finish of the garage. Finished = painted walls/floor, Rough = bare walls.","type":"select","options":["Fin","RFn","Unf","NA"]},
   {"name":"GarageQual","label_fr":"Qualite du garage","desc_fr":"Qualite de construction du garage.","label_en":"Garage Quality","desc_en":"Quality of the garage construction.","type":"select","options":["Ex","Gd","TA","Fa","Po","NA"]},
   {"name":"GarageCond","label_fr":"Etat du garage","desc_fr":"Etat actuel du garage.","label_en":"Garage Condition","desc_en":"Current condition of the garage.","type":"select","options":["Ex","Gd","TA","Fa","Po","NA"]},
   {"name":"PavedDrive","label_fr":"Entree pavee","desc_fr":"Type d'entree de garage ou de stationnement. Pave, partiellement pave, ou en gravier/terre.","label_en":"Paved Driveway","desc_en":"Type of driveway. Paved, partially paved, or gravel/dirt.","type":"select","options":["Y","P","N"]},
   {"name":"WoodDeckSF","label_fr":"Terrasse en bois","desc_fr":"Superficie de la terrasse en bois en metres carres.","label_en":"Wood Deck Area","desc_en":"Wood deck area in square feet.","type":"number","unit":"pi2"},
   {"name":"OpenPorchSF","label_fr":"Porche ouvert","desc_fr":"Superficie du porche ouvert en metres carres.","label_en":"Open Porch Area","desc_en":"Open porch area in square feet.","type":"number","unit":"pi2"},
   {"name":"EnclosedPorch","label_fr":"Porche ferme","desc_fr":"Superficie du porche ferme (vitre ou moustiquaire) en metres carres.","label_en":"Enclosed Porch Area","desc_en":"Enclosed porch area in square feet.","type":"number","unit":"pi2"},
   {"name":"3SsnPorch","label_fr":"Veranda 3 saisons","desc_fr":"Superficie de la veranda utilisable 3 saisons (printemps, ete, automne) en metres carres.","label_en":"Three-Season Porch","desc_en":"Three-season porch area in square feet (spring, summer, fall).","type":"number","unit":"pi2"},
   {"name":"ScreenPorch","label_fr":"Porche moustiquaire","desc_fr":"Superficie du porche avec ecran moustiquaire en metres carres.","label_en":"Screened Porch","desc_en":"Screened porch area in square feet.","type":"number","unit":"pi2"},
   {"name":"PoolArea","label_fr":"Surface de la piscine","desc_fr":"Superficie de la piscine en metres carres. 0 = pas de piscine.","label_en":"Pool Area","desc_en":"Pool area in square feet. 0 = no pool.","type":"number","unit":"pi2"},
   {"name":"PoolQC","label_fr":"Qualite de la piscine","desc_fr":"Qualite de la piscine si presente.","label_en":"Pool Quality","desc_en":"Quality of the pool if present.","type":"select","options":["Ex","Gd","TA","Fa","NA"]},
   {"name":"Fence","label_fr":"Cloture","desc_fr":"Type et qualite de la cloture autour de la propriete.","label_en":"Fence","desc_en":"Type and quality of fence around the property.","type":"select","options":["GdPrv","MnPrv","GdWo","MnWw","NA"]},
   {"name":"MiscVal","label_fr":"Valeur accessoires","desc_fr":"Valeur en dollars des elements accessoires non couverts ailleurs (remise, tennis, etc.).","label_en":"Miscellaneous Value","desc_en":"Value in dollars of miscellaneous features not covered elsewhere (shed, tennis court, etc.).","type":"number","unit":"$"},
   {"name":"YearRemodAddp","label_fr":"Annee renovation (derive)","desc_fr":"Difference entre l'annee de renovation et l'annee de construction. Indique l'age des renovations.","label_en":"Year Remodeled (derived)","desc_en":"Difference between renovation year and construction year. Indicates age of renovations.","type":"number"},
   {"name":"GarageYrBltp","label_fr":"Annee garage (derive)","desc_fr":"Difference entre l'annee de construction du garage et celle de la maison.","label_en":"Garage Year Built (derived)","desc_en":"Difference between garage construction year and house construction year.","type":"number"},
   {"name":"BsmtFinSF","label_fr":"Surface finie sous-sol (derive)","desc_fr":"Surface totale finie du sous-sol calculee a partir des differents types de finition.","label_en":"Finished Basement Area (derived)","desc_en":"Total finished basement area calculated from different finish types.","type":"number","unit":"pi2"},
   {"name":"TotalFlrsf","label_fr":"Nombre d'etages (derive)","desc_fr":"Nombre d'etages calcule a partir des surfaces. 1 = plain-pied, 2 = deux etages, etc.","label_en":"Total Floors (derived)","desc_en":"Number of floors calculated from areas. 1 = single story, 2 = two story, etc.","type":"number"},
   {"name":"Totalbath","label_fr":"Salles de bains (derive)","desc_fr":"Nombre total de salles de bains (une demi-salle = 0.5, une salle complete = 1).","label_en":"Total Bathrooms (derived)","desc_en":"Total number of bathrooms (half bath = 0.5, full bath = 1).","type":"number","min":0,"max":10,"step":0.5},
   {"name":"GarageArePerCar","label_fr":"Surface garage/voiture (derive)","desc_fr":"Surface du garage divisee par le nombre de voitures qu'il peut contenir.","label_en":"Garage Area per Car (derived)","desc_en":"Garage area divided by the number of cars it can hold.","type":"number"},
   {"name":"MSZoning","label_fr":"Zone urbanistique","desc_fr":"Classification de la zone urbanistique ou se trouve le terrain (residentielle, commerciale, agricole, etc.).","label_en":"Zoning Classification","desc_en":"Classification of the zoning where the property is located (residential, commercial, agricultural, etc.).","type":"select","options":["C (all)","FV","RH","RL","RM"]},
   {"name":"Street","label_fr":"Type de rue","desc_fr":"Type de revetement de la rue donnant sur la propriete.","label_en":"Street Type","desc_en":"Type of road surface adjacent to the property.","type":"select","options":["Grvl","Pave"]},
   {"name":"Alley","label_fr":"Ruelle","desc_fr":"Type d'acces par ruelle si present.","label_en":"Alley Access","desc_en":"Type of alley access if available.","type":"select","options":["Grvl","Pave","unknown"]},
   {"name":"LotConfig","label_fr":"Configuration du terrain","desc_fr":"Position du terrain par rapport aux autres: lot interieur, coin, cul-de-sac, etc.","label_en":"Lot Configuration","desc_en":"Position of the lot relative to others: inside lot, corner, cul-de-sac, etc.","type":"select","options":["Inside","Corner","CulDSac","FR2","FR3"]},
   {"name":"Condition1","label_fr":"Proximite 1","desc_fr":"Proximite a des elements particuliers: rue artere, voie ferree, parc, etc. (principal).","label_en":"Proximity 1","desc_en":"Proximity to various features: arterial road, railroad, park, etc. (primary).","type":"select","options":["Artery","Feedr","Norm","PosA","PosN","RRAe","RRAn","RRNe","RRNn"]},
   {"name":"Condition2","label_fr":"Proximite 2","desc_fr":"Proximite a des elements particuliers (secondaire si plusieurs).","label_en":"Proximity 2","desc_en":"Proximity to various features (secondary if multiple).","type":"select","options":["Artery","Feedr","Norm","PosA","PosN","RRAe","RRAn","RRNe","RRNn"]},
   {"name":"BldgType","label_fr":"Type de batiment","desc_fr":"Type d'habitation: maison individuelle, duplex, maison de ville, etc.","label_en":"Building Type","desc_en":"Type of dwelling: single-family, duplex, townhouse, etc.","type":"select","options":["1Fam","2fmCon","Duplex","Twnhs","TwnhsE"]},
   {"name":"HouseStyle","label_fr":"Style architectural","desc_fr":"Style de la maison: 1 etage, 2 etages, etage partiel, etc.","label_en":"House Style","desc_en":"Style of the house: 1 story, 2 story, split-level, etc.","type":"select","options":["1Story","1.5Fin","1.5Unf","2Story","2.5Fin","2.5Unf","SFoyer","SLvl"]},
   {"name":"RoofStyle","label_fr":"Type de toit","desc_fr":"Forme du toit: plat, a pignon, en croupe, etc.","label_en":"Roof Type","desc_en":"Shape of the roof: flat, gable, hip, etc.","type":"select","options":["Flat","Gable","Gambrel","Hip","Mansard","Shed"]},
   {"name":"RoofMatl","label_fr":"Materiau du toit","desc_fr":"Materiau de couverture du toit: bardeaux, metal, tuiles, etc.","label_en":"Roof Material","desc_en":"Roof covering material: shingles, metal, tiles, etc.","type":"select","options":["ClyTile","CompShg","Membran","Metal","Roll","Tar&Grv","WdShake","WdShngl"]},
   {"name":"MasVnrType","label_fr":"Type de parement","desc_fr":"Type de revetement en maconnerie (brique, pierre) sur l'exterieur.","label_en":"Masonry Type","desc_en":"Type of exterior masonry veneer (brick, stone).","type":"select","options":["BrkCmn","BrkFace","Stone","unknown"]},
   {"name":"Foundation","label_fr":"Type de fondation","desc_fr":"Type de fondation de la maison: beton, parpaing, dalle, brique, etc.","label_en":"Foundation Type","desc_en":"Type of house foundation: concrete, block, slab, brick, etc.","type":"select","options":["BrkTil","CBlock","PConc","Slab","Stone","Wood"]},
   {"name":"Heating","label_fr":"Type de chauffage","desc_fr":"Type de systeme de chauffage installe.","label_en":"Heating Type","desc_en":"Type of heating system installed.","type":"select","options":["Floor","GasA","GasW","Grav","OthW","Wall"]},
   {"name":"Electrical","label_fr":"Systeme electrique","desc_fr":"Type d'installation electrique: circuit standard, fusibles, etc.","label_en":"Electrical System","desc_en":"Type of electrical system: standard circuit, fuses, etc.","type":"select","options":["SBrkr","FuseA","FuseF","FuseP","Mix"]},
   {"name":"GarageType","label_fr":"Type de garage","desc_fr":"Emplacement et type du garage: attache, detache, sous la maison, etc.","label_en":"Garage Type","desc_en":"Location and type of garage: attached, detached, built-in, etc.","type":"select","options":["2Types","Attchd","Basment","BuiltIn","CarPort","Detchd","unknown"]},
   {"name":"MiscFeature","label_fr":"Autres equipements","desc_fr":"Autres equipements notables non couverts ailleurs: remise, court de tennis, ascenseur, etc.","label_en":"Miscellaneous Features","desc_en":"Other notable features not covered elsewhere: shed, tennis court, elevator, etc.","type":"select","options":["Gar2","Othr","Shed","TenC","unknown"]},
   {"name":"SaleType","label_fr":"Type de vente","desc_fr":"Type de transaction immobiliere: vente classique, neuve, cash, etc.","label_en":"Sale Type","desc_en":"Type of real estate transaction: normal sale, new, cash, etc.","type":"select","options":["COD","CWD","Con","ConLD","ConLI","ConLw","New","Oth","WD"]},
   {"name":"SaleCondition","label_fr":"Condition de vente","desc_fr":"Conditions particulieres de la vente: normale, famille, foreclosure, etc.","label_en":"Sale Condition","desc_en":"Special conditions of the sale: normal, family, foreclosure, etc.","type":"select","options":["Abnorml","AdjLand","Alloca","Family","Normal","Partial"]},
   {"name":"Exterior","label_fr":"Revetement exterieur","desc_fr":"Materiau de revetement de la facade principale.","label_en":"Exterior Material","desc_en":"Material of the main facade cladding.","type":"select","options":["ta"]},
   {"name":"Neighborhood","label_fr":"Quartier","desc_fr":"Quartier dans la ville d'Ames (Iowa). Chaque quartier a un niveau de standing different.","label_en":"Neighborhood","desc_en":"Neighborhood in Ames, Iowa. Each neighborhood has a different price level.","type":"select","options":["ta"]},
]

COLUMNS_GUIDE_MAP = {c["name"]: c for c in COLUMNS_GUIDE}
