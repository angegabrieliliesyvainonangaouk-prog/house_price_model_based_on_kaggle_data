// cleaner.js — Browser-side CSV cleaning, ported from prediction_cleaner.py

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const TRAIN_COLUMNS = [
  "Id","MSSubClass","MSZoning","LotFrontage","LotArea","Street","Alley",
  "LotShape","LandContour","Utilities","LotConfig","LandSlope","Neighborhood",
  "Condition1","Condition2","BldgType","HouseStyle","OverallQual","OverallCond",
  "YearBuilt","YearRemodAdd","RoofStyle","RoofMatl","Exterior1st","Exterior2nd",
  "MasVnrType","MasVnrArea","ExterQual","ExterCond","Foundation","BsmtQual",
  "BsmtCond","BsmtExposure","BsmtFinType1","BsmtFinSF1","BsmtFinType2",
  "BsmtFinSF2","BsmtUnfSF","TotalBsmtSF","Heating","HeatingQC","CentralAir",
  "Electrical","1stFlrSF","2ndFlrSF","LowQualFinSF","GrLivArea","BsmtFullBath",
  "BsmtHalfBath","FullBath","HalfBath","BedroomAbvGr","KitchenAbvGr",
  "KitchenQual","TotRmsAbvGrd","Functional","Fireplaces","FireplaceQu",
  "GarageType","GarageYrBlt","GarageFinish","GarageCars","GarageArea",
  "GarageQual","GarageCond","PavedDrive","WoodDeckSF","OpenPorchSF",
  "EnclosedPorch","3SsnPorch","ScreenPorch","PoolArea","PoolQC","Fence",
  "MiscFeature","MiscVal","MoSold","YrSold","SaleType","SaleCondition",
];

const TRAIN_COLUMNS_NO_ID = TRAIN_COLUMNS.filter(c => c !== "Id");

const NUMERIC_FILL_ZERO = [
  "LotFrontage","LotArea","OverallQual","OverallCond","YearBuilt",
  "YearRemodAdd","MasVnrArea","BsmtFinSF1","BsmtFinSF2","BsmtUnfSF",
  "TotalBsmtSF","LowQualFinSF","GrLivArea","BsmtFullBath","BsmtHalfBath",
  "FullBath","HalfBath","BedroomAbvGr","KitchenAbvGr","TotRmsAbvGrd",
  "Fireplaces","GarageYrBlt","GarageCars","GarageArea","WoodDeckSF",
  "OpenPorchSF","EnclosedPorch","3SsnPorch","ScreenPorch","PoolArea",
  "MiscVal","MoSold","YrSold","MSSubClass",
];

const INT_COLUMNS = [
  "BsmtFullBath","BsmtHalfBath","GarageYrBlt","GarageCars","FullBath",
  "HalfBath","YearBuilt","YearRemodAdd","MoSold","YrSold","BedroomAbvGr",
  "KitchenAbvGr","Fireplaces",
];

const COLUMNS_TO_DROP = [
  "YrSold","MoSold","GarageYrBlt","BsmtFinSF1","BsmtFinSF2",
  "2ndFlrSF","1stFlrSF","FullBath","HalfBath","BsmtHalfBath",
  "BsmtFullBath","GarageArea","GarageCars",
];

const QUAL_MAP = { unknown: 0, Po: 1, Fa: 2, TA: 3, Gd: 4, Ex: 5 };
const QUAL_MAP_NO_UNK = { Po: 1, Fa: 2, TA: 3, Gd: 4, Ex: 5 };

const ORDINAL_1 = [
  "ExterQual","ExterCond","BsmtQual","BsmtCond","HeatingQC",
  "KitchenQual","FireplaceQu","GarageQual","GarageCond","PoolQC",
];

const ORDINAL_2_MAPS = {
  LotShape:      { unknown: 0, IR3: 1, IR2: 2, IR1: 3, Reg: 4 },
  LandContour:   { unknown: 0, Low: 1, Bnk: 2, HLS: 3, Lvl: 4 },
  LandSlope:     { unknown: 0, Sev: 1, Mod: 2, Gtl: 3 },
  BsmtExposure:  { unknown: 0, No: 1, Mn: 2, Av: 3, Gd: 4 },
  BsmtFinType1:  { unknown: 0, Unf: 1, LwQ: 2, Rec: 3, BLQ: 4, ALQ: 5, GLQ: 6 },
  BsmtFinType2:  { unknown: 0, Unf: 1, LwQ: 2, Rec: 3, BLQ: 4, ALQ: 5, GLQ: 6 },
  Utilities:     { unknown: 0, ELO: 1, NoSeWa: 2, NoSewr: 3, AllPub: 4 },
  CentralAir:    { unknown: 0, N: 1, Y: 2 },
  Functional:    { unknown: 0, Sal: 1, Sev: 2, Maj2: 3, Maj1: 4, Mod: 5, Min2: 6, Min1: 7, Typ: 8 },
  GarageFinish:  { unknown: 0, Unf: 1, RFn: 2, Fin: 3 },
  PavedDrive:    { unknown: 0, N: 1, P: 2, Y: 3 },
  Fence:         { unknown: 0, MnWw: 1, GdWo: 2, MnPrv: 3, GdPrv: 4 },
};

const ONE_HOT_COLUMNS = [
  "MSZoning","Street","Alley","LotConfig","Condition1","Condition2",
  "BldgType","HouseStyle","RoofStyle","RoofMatl","MasVnrType",
  "Foundation","Heating","Electrical","GarageType","MiscFeature",
  "SaleType","SaleCondition",
];

const TARGET_ENCODED_COLUMNS = ["Exterior1st", "Exterior2nd", "Neighborhood"];

const ONE_HOT_VALUES = {
  MSZoning:       ["C (all)","FV","RH","RL","RM"],
  Street:         ["Grvl","Pave"],
  Alley:          ["Grvl","Pave","unknown"],
  LotConfig:      ["Corner","CulDSac","FR2","FR3","Inside"],
  Condition1:     ["Artery","Feedr","Norm","PosA","PosN","RRAe","RRAn","RRNe","RRNn"],
  Condition2:     ["Artery","Feedr","Norm","PosA","PosN","RRAe","RRAn","RRNn"],
  BldgType:       ["1Fam","2fmCon","Duplex","Twnhs","TwnhsE"],
  HouseStyle:     ["1.5Fin","1.5Unf","1Story","2.5Fin","2.5Unf","2Story","SFoyer","SLvl"],
  RoofStyle:      ["Flat","Gable","Gambrel","Hip","Mansard","Shed"],
  RoofMatl:       ["ClyTile","CompShg","Membran","Metal","Roll","Tar&Grv","WdShake","WdShngl"],
  MasVnrType:     ["BrkCmn","BrkFace","Stone","unknown"],
  Foundation:     ["BrkTil","CBlock","PConc","Slab","Stone","Wood"],
  Heating:        ["Floor","GasA","GasW","Grav","OthW","Wall"],
  Electrical:     ["FuseA","FuseF","FuseP","Mix","SBrkr","unknown"],
  GarageType:     ["2Types","Attchd","Basment","BuiltIn","CarPort","Detchd","unknown"],
  MiscFeature:    ["Gar2","Othr","Shed","TenC","unknown"],
  SaleType:       ["COD","CWD","Con","ConLD","ConLI","ConLw","New","Oth","WD"],
  SaleCondition:  ["Abnorml","AdjLand","Alloca","Family","Normal","Partial"],
};

const EXTERIOR_TA_MEANS = {
  "AsbShng_AsbShng": 11.532365, "AsbShng_BrkFace": 12.323856,
  "AsbShng_VinylSd": 11.715866, "AsbShng_Wd Sdng": 11.314475,
  "AsphShn_AsphShn": 11.512925, "AsphShn_HdBoard": 12.072541,
  "AsphShn_MetalSd": 11.842229, "Brk Cmn_BrkComm": 11.158287,
  "Brk Cmn_Plywood": 11.911482, "BrkFace_BrkFace": 12.075095,
  "BrkFace_Wd Sdng": 11.849398, "CBlock_CBlock": 11.561716,
  "CmentBd_CemntBd": 12.191067, "CmentBd_Stucco": 12.843971,
  "HdBoard_BrkFace": 12.317278, "HdBoard_HdBoard": 11.968136,
  "HdBoard_MetalSd": 11.875114, "HdBoard_Plywood": 11.842475,
  "HdBoard_Stone": 12.567237, "HdBoard_VinylSd": 11.759786,
  "HdBoard_Wd Sdng": 12.317629, "HdBoard_WdShing": 11.868242,
  "ImStucc_HdBoard": 11.558577, "ImStucc_ImStucc": 12.476100,
  "ImStucc_Plywood": 12.031719, "ImStucc_VinylSd": 12.676076,
  "ImStucc_Wd Sdng": 12.678689, "MetalSd_HdBoard": 11.691072,
  "MetalSd_MetalSd": 11.863154, "MetalSd_Wd Sdng": 11.849398,
  "Other_VinylSd": 12.672946, "Plywood_AsbShng": 11.533208,
  "Plywood_BrkFace": 12.135834, "Plywood_HdBoard": 11.871843,
  "Plywood_Plywood": 12.045084, "Plywood_VinylSd": 11.981740,
  "Plywood_Wd Sdng": 11.855378, "Plywood_WdShing": 11.837036,
  "Stone_BrkFace": 11.745735, "Stone_Stone": 12.345835,
  "Stone_Stucco": 11.445717, "Stone_Wd Sdng": 12.209188,
  "Stucco_AsbShng": 11.373663, "Stucco_BrkFace": 12.345835,
  "Stucco_MetalSd": 11.350407, "Stucco_Stucco": 11.866697,
  "Stucco_VinylSd": 11.979385, "Stucco_Wd Sdng": 12.384219,
  "Stucco_WdShing": 11.411446, "VinylSd_VinylSd": 12.211896,
  "VinylSd_Wd Sdng": 11.641002, "Wd Sdng_BrkFace": 12.075183,
  "Wd Sdng_CemntBd": 12.031719, "Wd Sdng_HdBoard": 11.740061,
  "Wd Sdng_MetalSd": 11.749954, "Wd Sdng_Plywood": 12.392995,
  "Wd Sdng_VinylSd": 11.835009, "Wd Sdng_Wd Sdng": 11.819277,
  "Wd Sdng_WdShing": 11.373663, "Wd Shng_BrkFace": 11.774520,
  "Wd Shng_CemntBd": 13.195614, "Wd Shng_HdBoard": 11.798104,
  "Wd Shng_MetalSd": 11.842229, "Wd Shng_Stucco": 11.892050,
  "Wd Shng_VinylSd": 11.810007, "Wd Shng_Wd Sdng": 11.813029,
  "Wd Shng_WdShing": 11.897136,
};
const EXTERIOR_GLOBAL_MEAN = 12.024051;

const NEIGHBORHOOD_TA_MEANS = {
  Blmngtn: 12.169416, Blueste: 11.826536, BrDale: 11.547864,
  BrkSide: 11.679727, ClearCr: 12.239900, CollgCr: 12.163641,
  Crawfor: 12.206659, Edwards: 11.712312, Gilbert: 12.155803,
  IDOTRR: 11.446889, MeadowV: 11.474522, Mitchel: 11.933948,
  NAmes: 11.868045, NPkVill: 11.866477, NWAmes: 12.130609,
  NoRidge: 12.676000, NridgHt: 12.619411, OldTown: 11.703865,
  SWISU: 11.838435, Sawyer: 11.811468, SawyerW: 12.090689,
  Somerst: 12.296495, StoneBr: 12.585486, Timber: 12.363455,
  Veenker: 12.344176,
};
const NEIGHBORHOOD_GLOBAL_MEAN = 12.024051;

const MODEL_FEATURE_ORDER = [
  "MSSubClass","LotFrontage","LotArea","LotShape","LandContour",
  "Utilities","LandSlope","OverallQual","OverallCond","YearBuilt",
  "YearRemodAdd","MasVnrArea","ExterQual","ExterCond","BsmtQual",
  "BsmtCond","BsmtExposure","BsmtFinType1","BsmtFinType2","BsmtUnfSF",
  "TotalBsmtSF","HeatingQC","CentralAir","LowQualFinSF","GrLivArea",
  "BedroomAbvGr","KitchenAbvGr","KitchenQual","TotRmsAbvGrd","Functional",
  "Fireplaces","FireplaceQu","GarageFinish","GarageQual","GarageCond",
  "PavedDrive","WoodDeckSF","OpenPorchSF","EnclosedPorch","3SsnPorch",
  "ScreenPorch","PoolArea","PoolQC","Fence","MiscVal",
  "YearRemodAddp","GarageYrBltp","BsmtFinSF","TotalFlrsf","Totalbath",
  "GarageArePerCar",
  "MSZoning_C (all)","MSZoning_FV","MSZoning_RH","MSZoning_RL","MSZoning_RM",
  "Street_Grvl","Street_Pave",
  "Alley_Grvl","Alley_Pave","Alley_unknown",
  "LotConfig_Corner","LotConfig_CulDSac","LotConfig_FR2","LotConfig_FR3","LotConfig_Inside",
  "Condition1_Artery","Condition1_Feedr","Condition1_Norm","Condition1_PosA","Condition1_PosN",
  "Condition1_RRAe","Condition1_RRAn","Condition1_RRNe","Condition1_RRNn",
  "Condition2_Artery","Condition2_Feedr","Condition2_Norm","Condition2_PosA","Condition2_PosN",
  "Condition2_RRAe","Condition2_RRAn","Condition2_RRNn",
  "BldgType_1Fam","BldgType_2fmCon","BldgType_Duplex","BldgType_Twnhs","BldgType_TwnhsE",
  "HouseStyle_1.5Fin","HouseStyle_1.5Unf","HouseStyle_1Story","HouseStyle_2.5Fin",
  "HouseStyle_2.5Unf","HouseStyle_2Story","HouseStyle_SFoyer","HouseStyle_SLvl",
  "RoofStyle_Flat","RoofStyle_Gable","RoofStyle_Gambrel","RoofStyle_Hip",
  "RoofStyle_Mansard","RoofStyle_Shed",
  "RoofMatl_ClyTile","RoofMatl_CompShg","RoofMatl_Membran","RoofMatl_Metal",
  "RoofMatl_Roll","RoofMatl_Tar&Grv","RoofMatl_WdShake","RoofMatl_WdShngl",
  "MasVnrType_BrkCmn","MasVnrType_BrkFace","MasVnrType_Stone","MasVnrType_unknown",
  "Foundation_BrkTil","Foundation_CBlock","Foundation_PConc","Foundation_Slab",
  "Foundation_Stone","Foundation_Wood",
  "Heating_Floor","Heating_GasA","Heating_GasW","Heating_Grav","Heating_OthW","Heating_Wall",
  "Electrical_FuseA","Electrical_FuseF","Electrical_FuseP","Electrical_Mix",
  "Electrical_SBrkr","Electrical_unknown",
  "GarageType_2Types","GarageType_Attchd","GarageType_Basment","GarageType_BuiltIn",
  "GarageType_CarPort","GarageType_Detchd","GarageType_unknown",
  "MiscFeature_Gar2","MiscFeature_Othr","MiscFeature_Shed","MiscFeature_TenC",
  "MiscFeature_unknown",
  "SaleType_COD","SaleType_CWD","SaleType_Con","SaleType_ConLD","SaleType_ConLI",
  "SaleType_ConLw","SaleType_New","SaleType_Oth","SaleType_WD",
  "SaleCondition_Abnorml","SaleCondition_AdjLand","SaleCondition_Alloca",
  "SaleCondition_Family","SaleCondition_Normal","SaleCondition_Partial",
  "Exterior_ta",
  "Neighborhood_ta",
];

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function _isMissing(val) {
  return val === undefined || val === null || val === "" || val === "NA" || val === "None";
}

function _safeFloat(val, def) {
  if (def === undefined) def = 0.0;
  if (_isMissing(val)) return def;
  const n = Number(val);
  return isNaN(n) ? def : n;
}

function _safeInt(val, def) {
  if (def === undefined) def = 0;
  if (_isMissing(val)) return def;
  const n = Number(val);
  return isNaN(n) ? def : Math.trunc(n);
}

function _resolveOrdinal(val, mapping) {
  if (_isMissing(val)) {
    return mapping["unknown"] !== undefined ? mapping["unknown"] : 0;
  }
  return mapping[val] !== undefined ? mapping[val] : 0;
}

// ---------------------------------------------------------------------------
// Lightweight CSV parser (handles quoted fields with commas/newlines)
// ---------------------------------------------------------------------------

function parseCSV(csvText) {
  const rows = [];
  let i = 0;
  const len = csvText.length;

  // Parse header line
  const headers = _parseLine(csvText);

  while (i < len) {
    // skip blank lines
    while (i < len && csvText[i] === "\n") i++;
    if (i >= len) break;

    const values = _parseLine(csvText);
    const row = {};
    for (let h = 0; h < headers.length; h++) {
      row[headers[h]] = h < values.length ? values[h] : "";
    }
    rows.push(row);
  }
  return rows;

  // inner: parse one CSV line (advances global i)
  function _parseLine(text) {
    const fields = [];
    while (i < text.length && text[i] !== "\n") {
      if (text[i] === '"') {
        // quoted field
        i++; // skip opening quote
        let field = "";
        while (i < text.length) {
          if (text[i] === '"') {
            if (i + 1 < text.length && text[i + 1] === '"') {
              field += '"';
              i += 2;
            } else {
              i++; // skip closing quote
              break;
            }
          } else {
            field += text[i];
            i++;
          }
        }
        fields.push(field);
      } else {
        // unquoted field
        let field = "";
        while (i < text.length && text[i] !== "," && text[i] !== "\n") {
          field += text[i];
          i++;
        }
        fields.push(field);
      }
      // skip comma
      if (i < text.length && text[i] === ",") i++;
      // if we hit \n without comma, line is done
    }
    // skip newline
    if (i < text.length && text[i] === "\n") i++;
    return fields;
  }
}

function toCSV(headers, rows) {
  const lines = [headers.map(_quoteCSV).join(",")];
  for (const row of rows) {
    lines.push(headers.map(h => _quoteCSV(String(row[h] !== undefined ? row[h] : ""))).join(","));
  }
  return lines.join("\n");
}

function _quoteCSV(val) {
  if (val.indexOf(",") !== -1 || val.indexOf('"') !== -1 || val.indexOf("\n") !== -1) {
    return '"' + val.replace(/"/g, '""') + '"';
  }
  return val;
}

// ---------------------------------------------------------------------------
// Main cleaning function
// ---------------------------------------------------------------------------

function cleanCSV(csvText) {
  const rows = parseCSV(csvText);
  const cleaned = [];

  for (const row of rows) {
    const rec = {};

    // 1. Missing value imputation
    for (const col of TRAIN_COLUMNS_NO_ID) {
      const val = row[col];
      if (_isMissing(val)) {
        if (NUMERIC_FILL_ZERO.indexOf(col) !== -1) {
          rec[col] = 0.0;
        } else {
          rec[col] = "unknown";
        }
      } else {
        rec[col] = val;
      }
    }

    // 2. Type coercion — numeric to float
    for (const col of NUMERIC_FILL_ZERO) {
      rec[col] = _safeFloat(rec[col], 0.0);
    }

    // 3. Type coercion — to int
    for (const col of INT_COLUMNS) {
      rec[col] = _safeInt(rec[col], 0);
    }

    // 4. Target encoding — Exterior composite key
    const exteriorKey = String(rec["Exterior2nd"] || "unknown") + "_" + String(rec["Exterior1st"] || "unknown");
    rec["Exterior_ta"] = EXTERIOR_TA_MEANS[exteriorKey] !== undefined
      ? EXTERIOR_TA_MEANS[exteriorKey]
      : EXTERIOR_GLOBAL_MEAN;

    // 5. Target encoding — Neighborhood
    const neighborhoodVal = rec["Neighborhood"] || "unknown";
    rec["Neighborhood_ta"] = NEIGHBORHOOD_TA_MEANS[neighborhoodVal] !== undefined
      ? NEIGHBORHOOD_TA_MEANS[neighborhoodVal]
      : NEIGHBORHOOD_GLOBAL_MEAN;

    // 6. Feature engineering
    rec["YearRemodAddp"] = _safeFloat(rec["YrSold"], 0) - _safeFloat(rec["YearRemodAdd"], 0);
    rec["GarageYrBltp"] = _safeFloat(rec["YrSold"], 0) - _safeFloat(rec["GarageYrBlt"], 0);
    rec["BsmtFinSF"] = _safeFloat(rec["BsmtFinSF1"], 0) + _safeFloat(rec["BsmtFinSF2"], 0);
    rec["TotalFlrsf"] = _safeFloat(rec["1stFlrSF"], 0) + _safeFloat(rec["2ndFlrSF"], 0);
    rec["Totalbath"] = (
      _safeFloat(rec["FullBath"], 0) +
      0.5 * _safeFloat(rec["HalfBath"], 0) +
      0.5 * _safeFloat(rec["BsmtHalfBath"], 0) +
      _safeFloat(rec["BsmtFullBath"], 0)
    );
    const gc = _safeFloat(rec["GarageCars"], 0);
    const ga = _safeFloat(rec["GarageArea"], 0);
    rec["GarageArePerCar"] = gc > 0 ? ga / gc : 0.0;

    // 7. Drop columns used only for engineering / raw exterior / neighborhood
    for (const col of COLUMNS_TO_DROP) {
      delete rec[col];
    }
    delete rec["Exterior1st"];
    delete rec["Exterior2nd"];
    delete rec["Neighborhood"];

    // 8. Ordinal encoding — ORDINAL_2_MAPS
    for (const colName of Object.keys(ORDINAL_2_MAPS)) {
      let rawVal = rec[colName];
      if (typeof rawVal !== "string") rawVal = "unknown";
      rec[colName] = _resolveOrdinal(rawVal, ORDINAL_2_MAPS[colName]);
    }

    // 9. Ordinal encoding — quality columns (ORDINAL_1)
    for (const colName of ORDINAL_1) {
      let rawVal = rec[colName];
      if (typeof rawVal !== "string") rawVal = "unknown";
      if (rawVal === "unknown") {
        rec[colName] = QUAL_MAP["unknown"];
      } else {
        rec[colName] = QUAL_MAP[rawVal] !== undefined
          ? QUAL_MAP[rawVal]
          : (QUAL_MAP_NO_UNK[rawVal] !== undefined ? QUAL_MAP_NO_UNK[rawVal] : 0);
      }
    }

    // 10. One-hot encoding
    for (const colName of ONE_HOT_COLUMNS) {
      let rawVal = rec[colName];
      if (typeof rawVal !== "string") rawVal = "unknown";
      const possibleValues = ONE_HOT_VALUES[colName] || [];
      for (const pv of possibleValues) {
        const oheCol = colName + "_" + pv;
        rec[oheCol] = pv === rawVal ? 1 : 0;
      }
      delete rec[colName];
    }

    // 11. Drop raw target-encoded columns (already replaced by _ta versions)
    for (const col of TARGET_ENCODED_COLUMNS) {
      delete rec[col];
    }

    cleaned.push(rec);
  }

  // 12. Reorder to match MODEL_FEATURE_ORDER
  if (cleaned.length > 0) {
    const present = {};
    for (const k of Object.keys(cleaned[0])) present[k] = true;

    const orderedKeys = [];
    for (const k of MODEL_FEATURE_ORDER) {
      if (present[k]) orderedKeys.push(k);
    }
    // any extra columns not in MODEL_FEATURE_ORDER
    for (const k of Object.keys(cleaned[0])) {
      if (MODEL_FEATURE_ORDER.indexOf(k) === -1) orderedKeys.push(k);
    }

    for (const rec of cleaned) {
      const reordered = {};
      for (const k of orderedKeys) {
        if (rec.hasOwnProperty(k)) reordered[k] = rec[k];
      }
      // clear and reassign
      for (const rk of Object.keys(rec)) delete rec[rk];
      Object.assign(rec, reordered);
    }

    // build output CSV
    return toCSV(orderedKeys, cleaned);
  }

  return "";
}

// ---------------------------------------------------------------------------
// Exports
// ---------------------------------------------------------------------------

if (typeof module !== "undefined" && module.exports) {
  module.exports = { cleanCSV, parseCSV, toCSV };
} else if (typeof window !== "undefined") {
  window.cleanCSV = cleanCSV;
  window.parseCSV = parseCSV;
  window.toCSV = toCSV;
}
